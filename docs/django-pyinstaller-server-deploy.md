# Django アプリの PyInstaller バイナリ化・サーバー配置手順

サーバーサイドで動かす Django アプリ本体を PyInstaller（onedir）で固め、設定を TOML ファイルに外出しして、Linux サーバーに配置・運用するための手順書です。

> **前提と範囲**
> - 対象は Django アプリのみ。MySQL / Redis / rsyslog などはバイナリに含めず、別途用意する。
> - 配備先は Linux（Rocky Linux 9 を想定）。他のディストリビューションでも考え方は同じ。
> - Python 3.11 以上（標準ライブラリの `tomllib` を使うため）。
> - 「**要確認**」と書いた項目は、公式情報で裏取りできていない、または環境依存の項目。実機で必ず確認する。

---

## 1. 全体方針

| 項目 | 方針 | 理由 |
| --- | --- | --- |
| パッケージ形式 | **onedir**（フォルダ配布） | onefile は起動のたびに一時フォルダへ展開される。サーバー用途では起動が遅く、調査もしにくい |
| HTTP サーバー | **Waitress**（純 Python）をバイナリに同梱 | `runserver` は本番向けではない。純 Python なので同梱しやすい |
| 設定 | **外部 TOML ＋ 環境変数** | 設定をバンドルに入れると変更のたびに再ビルドになる。秘密情報も隠せない |
| ビルド環境 | **配備先と同じ OS・同じアーキテクチャ** | PyInstaller はクロスコンパイル非対応。glibc 依存も絡む |
| DB ドライバ | **PyMySQL**（純 Python）を推奨 | mysqlclient は libmysqlclient などの共有ライブラリ依存があり、同梱・配備で詰まりやすい |

---

## 2. ディレクトリ構成（配備先）

```
/opt/dcim/
├── releases/
│   ├── 1.0.0/dcim/          ← PyInstaller の出力（実行ファイル dcim と _internal/）
│   └── 1.0.1/dcim/
└── current -> releases/1.0.1/dcim     ← シンボリックリンクで切替

/etc/dcim/config.toml        ← 設定ファイル（root:dcim, 640）
/var/lib/dcim/static/        ← collectstatic の出力先
/var/lib/dcim/media/         ← アップロード等（使う場合）
/var/log/dcim/               ← ログ（journald のみで運用するなら不要）
```

- 実行ファイル・ライブラリ（`/opt`）、設定（`/etc`）、可変データ（`/var`）を分離する。
- **バンドル内（`_internal` 配下）には書き込まない。** アップデートで消えるうえ、実行ユーザーに書き込み権限も付けたくない。
- `releases/<version>` ＋ `current` リンク方式にすると、切替とロールバックが一瞬で済む。

---

## 3. ビルド手順

### 3.1 ビルド用環境の準備

ビルドは配備先と同じ OS で行う。手元に同じ環境がなければ、Docker で用意するのが簡単。

```dockerfile
# Dockerfile.build  （Rocky Linux 9 上でビルドする例）
FROM rockylinux:9
RUN dnf install -y python3.11 python3.11-pip python3.11-devel gcc && dnf clean all
WORKDIR /src
COPY requirements.txt .
RUN python3.11 -m venv /venv && /venv/bin/pip install -r requirements.txt pyinstaller
COPY . .
CMD ["/venv/bin/pyinstaller", "--noconfirm", "--clean", "dcim.spec"]
```

```bash
docker build -f Dockerfile.build -t dcim-build .
docker run --rm -v "$PWD/dist:/src/dist" dcim-build
# → ./dist/dcim/ に出力
```

- **ビルド専用の venv を使う。** 余計なパッケージが入っていると、バンドルが肥大化する。
- `requirements.txt` には少なくとも次を含める：`Django`, `waitress`, `PyMySQL`（または使用する DB ドライバ）, `whitenoise`（静的ファイル配信に使う場合）。
- バージョンは固定（`==`）しておく。再現性のあるビルドのため。

### 3.2 エントリポイントの作成

`manage.py` 相当のエントリスクリプトを用意し、`serve` サブコマンドだけは自前で処理する（管理コマンドの探索に依存させないため）。

```python
# dcim_main.py
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    # `dcim serve` は Waitress を直接起動する
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        import argparse
        from waitress import serve
        from config.wsgi import application

        p = argparse.ArgumentParser(prog="dcim serve")
        p.add_argument("--host", default="127.0.0.1")
        p.add_argument("--port", type=int, default=8000)
        p.add_argument("--threads", type=int, default=8)
        a = p.parse_args(sys.argv[2:])
        serve(application, host=a.host, port=a.port, threads=a.threads)
        return

    # それ以外は通常の manage.py と同じ（migrate, collectstatic, 自作コマンド等）
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

### 3.3 settings.py を外部 TOML 対応にする

```python
# config/settings.py（抜粋）
import os
import sys
import tomllib
from pathlib import Path

# PyMySQL を MySQLdb として扱わせる（mysqlclient を使う場合は不要）
import pymysql
pymysql.install_as_MySQLdb()


def _config_candidates():
    # 優先順位: 環境変数で指定 > /etc > 実行ファイルの隣 > 開発時のプロジェクト直下
    if p := os.environ.get("DCIM_CONFIG"):
        yield Path(p)
    yield Path("/etc/dcim/config.toml")
    if getattr(sys, "frozen", False):
        yield Path(sys.executable).parent / "config.toml"
    else:
        yield Path(__file__).resolve().parent.parent / "config.toml"


def _load_config() -> dict:
    for c in _config_candidates():
        if c.is_file():
            with c.open("rb") as f:
                return tomllib.load(f)
    return {}


_cfg = _load_config()


def cfg(section, key, default=None):
    """環境変数 DCIM_<SECTION>_<KEY> を最優先し、次に TOML、最後にデフォルト値。"""
    env = os.environ.get(f"DCIM_{section}_{key}".upper())
    if env is not None:
        return env
    return _cfg.get(section, {}).get(key, default)


# ---- 以降、通常の Django 設定 ----
SECRET_KEY = cfg("django", "secret_key")           # 未設定なら起動時に失敗させる（下記参照）
if not SECRET_KEY:
    raise RuntimeError("django.secret_key が未設定です。config.toml を確認してください。")

DEBUG = str(cfg("django", "debug", "false")).lower() in ("1", "true", "yes")
ALLOWED_HOSTS = _cfg.get("django", {}).get("allowed_hosts", [])

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": cfg("database", "host", "127.0.0.1"),
        "PORT": cfg("database", "port", "3306"),
        "NAME": cfg("database", "name", "dcim"),
        "USER": cfg("database", "user", "dcim"),
        "PASSWORD": cfg("database", "password", ""),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

# 可変データはバンドルの外に置く
STATIC_ROOT = cfg("paths", "static_root", "/var/lib/dcim/static")
MEDIA_ROOT = cfg("paths", "media_root", "/var/lib/dcim/media")

# 運用パラメータ（例）
SYSLOG_INGEST_API_KEY = cfg("syslog", "ingest_api_key")
LOG_RETENTION_DAYS = int(cfg("syslog", "retention_days", 60))
```

ポイント：

- `BASE_DIR` や `__file__` を基準に **書き込み先を決めない**（frozen 環境では `_internal` 配下を指す）。
- 設定ファイルの場所の判定には `os.path.dirname(sys.executable)` を使う（PyInstaller 公式の run-time information が案内している方法）。`sys._MEIPASS` はバンドル内部を指すので、外部設定の探索には使わない。
- 必須項目（`SECRET_KEY` など）が無い場合は **起動時に明示的に失敗** させる。空のまま動くより安全。

### 3.4 config.toml の雛形

```toml
# /etc/dcim/config.toml
[django]
secret_key = "ここに十分長いランダム文字列"
debug = false
allowed_hosts = ["dcim.example.local"]

[database]
host = "127.0.0.1"
port = 3306
name = "dcim"
user = "dcim"
password = "ここにDBパスワード"

[paths]
static_root = "/var/lib/dcim/static"
media_root = "/var/lib/dcim/media"

[syslog]
ingest_api_key = "ここに共有シークレット"
retention_days = 60
```

- リポジトリには **`config.example.toml`（ダミー値）だけ** をコミットし、実際の値入りファイルは含めない。
- `SECRET_KEY` の生成例：`python -c "import secrets; print(secrets.token_urlsafe(64))"`

### 3.5 spec ファイル

```python
# dcim.spec
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

hiddenimports = []
hiddenimports += collect_submodules("config")
hiddenimports += collect_submodules("myapp")                    # 自作アプリ（migrations, management/commands を含む）
hiddenimports += collect_submodules("django.db.backends.mysql")
hiddenimports += ["pymysql", "waitress"]
# DRF などを使う場合: collect_submodules("rest_framework") を追加

datas = []
datas += collect_data_files("django")                           # 要確認: 必要なものだけに絞れるなら絞る
datas += [("myapp/templates", "myapp/templates")]               # 自作アプリのテンプレート等の非 Python ファイル
# datas += collect_data_files("rest_framework")                 # DRF の Browsable API を使う場合

a = Analysis(
    ["dcim_main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # onedir
    name="dcim",
    console=True,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="dcim",
    upx=False,
)
```

### 3.6 ビルドの実行

```bash
# プロジェクト直下で（settings モジュールをビルド時にも解決できるようにする）
export DJANGO_SETTINGS_MODULE=config.settings
export DCIM_DJANGO_SECRET_KEY=build-dummy-key    # ビルド時に settings を import するための仮の値

pyinstaller --noconfirm --clean dcim.spec
ls dist/dcim/            # → dcim（実行ファイル） と _internal/
```

- PyInstaller は Django 用のフックを持っており、ビルド時に `DJANGO_SETTINGS_MODULE` を参照して `INSTALLED_APPS` などから取り込み対象を推測する（**要確認**: 利用する PyInstaller のバージョンのフック挙動）。
- ビルド時に `settings.py` が import されるため、必須項目チェックで落ちる場合は上のように仮の環境変数を渡す。**この仮の値はバンドルに残らないが、ビルドログに出ないよう注意する。**
- PyInstaller 6.x 以降の onedir では、ライブラリ類が `dcim/_internal/` 配下に配置される。

### 3.7 ビルド後の確認（配備前に必ずやる）

```bash
# 1. ビルド環境でまず動かす
./dist/dcim/dcim check
./dist/dcim/dcim showmigrations
DCIM_CONFIG=./config.example.toml ./dist/dcim/dcim serve --port 8000 &
curl -i http://127.0.0.1:8000/

# 2. 動的リンクの不足確認
ldd ./dist/dcim/dcim | grep "not found"

# 3. 「素の」Rocky 9 コンテナで動かす（Python も開発ツールも無い状態）
docker run --rm -it -v "$PWD/dist/dcim:/opt/dcim:ro" -v "$PWD/config.example.toml:/etc/dcim/config.toml:ro" \
  rockylinux:9-minimal /opt/dcim/dcim check
```

3 の「素のコンテナでの実行」は、ビルド環境にたまたま入っていた共有ライブラリへの暗黙の依存を見つけるのに有効。

---

## 4. サーバー配置手順

### 4.1 実行ユーザーとディレクトリ

```bash
sudo useradd --system --home-dir /var/lib/dcim --shell /sbin/nologin dcim

sudo mkdir -p /opt/dcim/releases /etc/dcim /var/lib/dcim/static /var/lib/dcim/media /var/log/dcim
sudo chown -R dcim:dcim /var/lib/dcim /var/log/dcim
sudo chown root:dcim /etc/dcim
sudo chmod 750 /etc/dcim
```

### 4.2 バイナリの配置

```bash
VERSION=1.0.0
sudo mkdir -p /opt/dcim/releases/$VERSION
sudo cp -a dist/dcim /opt/dcim/releases/$VERSION/
sudo chown -R root:root /opt/dcim/releases/$VERSION      # 実行ユーザーに書き込ませない
sudo chmod -R go-w /opt/dcim/releases/$VERSION
sudo ln -sfn /opt/dcim/releases/$VERSION/dcim /opt/dcim/current
```

### 4.3 設定ファイルの配置

```bash
sudo install -o root -g dcim -m 640 config.toml /etc/dcim/config.toml
```

- 設定ファイルは **実行ユーザー（dcim）が読めて、他ユーザーは読めない** 状態にする（640）。
- 秘密情報を含むため、バックアップ時の取り扱いにも注意する。

### 4.4 初回セットアップ（DB マイグレーション・静的ファイル）

```bash
sudo -u dcim /opt/dcim/current/dcim migrate --noinput
sudo -u dcim /opt/dcim/current/dcim collectstatic --noinput
```

- マイグレーションは **起動のたびに自動実行せず、デプロイ手順として明示的に実行** するほうが安全（複数台構成や失敗時の切り分けのため）。
- 静的ファイル（admin 等）を配信するなら、WhiteNoise を `MIDDLEWARE` に追加するか、nginx で `/var/lib/dcim/static/` を配信する。Waitress は静的ファイル配信を担当しない。

### 4.5 systemd ユニット

```ini
# /etc/systemd/system/dcim.service
[Unit]
Description=DCIM Django application
After=network-online.target mysqld.service
Wants=network-online.target

[Service]
Type=simple
User=dcim
Group=dcim
Environment=DCIM_CONFIG=/etc/dcim/config.toml
WorkingDirectory=/var/lib/dcim
ExecStart=/opt/dcim/current/dcim serve --host 127.0.0.1 --port 8000 --threads 8
Restart=on-failure
RestartSec=5

# サンドボックス化（必要に応じて調整）
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/dcim /var/log/dcim

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dcim
sudo systemctl status dcim
journalctl -u dcim -f
```

- `WorkingDirectory` はバンドル外（`/var/lib/dcim`）にする。
- 外部公開する場合は、Waitress を `127.0.0.1` にバインドし、**前段に nginx 等のリバースプロキシ（TLS 終端）** を置く構成を推奨。

### 4.6 定期バッチ（ログ削除）を systemd timer で動かす場合

保持期間を過ぎた syslog を削除する管理コマンド（例：`purge_old_syslogs`）を、同じバイナリで実行できる。

```ini
# /etc/systemd/system/dcim-purge.service
[Unit]
Description=DCIM purge old syslogs

[Service]
Type=oneshot
User=dcim
Group=dcim
Environment=DCIM_CONFIG=/etc/dcim/config.toml
ExecStart=/opt/dcim/current/dcim purge_old_syslogs
```

```ini
# /etc/systemd/system/dcim-purge.timer
[Unit]
Description=Daily purge of old syslogs

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable --now dcim-purge.timer
systemctl list-timers dcim-purge.timer
```

- Celery を別用途で導入済みなら Celery beat でもよい。ここでは追加コンポーネントなしで済む方法として timer を挙げた。
- 実行結果・削除件数は journald に残る。

---

## 5. バイナリ化・配置時の注意点

### 5.1 ビルド関連

1. **ビルド OS ＝ 配備先 OS（同系統・同アーキテクチャ）。** Rocky 9 でビルドしたバイナリを Rocky 8 に持っていくと、glibc のバージョン差で動かない可能性がある。複数 OS に配るなら、**最も古い対象 OS** でビルドする。
2. **hidden import 漏れは実行時エラーになる。** ビルドが通っても、起動後に `ModuleNotFoundError` が出ることがある。`--debug=imports` 付きでビルドして確認し、足りないものを `hiddenimports` に追加する。
3. **自作アプリが複数ある場合は全て `collect_submodules` に列挙する。** 一部のアプリだけ見つからない、という報告が Django フォーラムにある。
4. **非 Python ファイル（テンプレート、JSON、SQL など）は `datas` に明示する。** 自動では含まれない。
5. **migrations の `.py` が含まれているか確認する。** `dcim showmigrations` で、全アプリのマイグレーションが表示されること。
6. **管理コマンド（`management/commands/*.py`）が認識されるか確認する。** `dcim help` の一覧に自作コマンドが出ること。出ない場合は `collect_submodules("myapp.management.commands")` を追加する（**要確認**）。
7. **PyInstaller は難読化ツールではない。** バイトコードは取り出して逆コンパイルできる。ソースを守る目的なら、Nuitka などコンパイル方式の検討が別途必要。

### 5.2 設定・秘密情報

8. **秘密情報はバンドルに入れない。** バンドルに含めたパスワードや API キーは、ファイルにアクセスできる人なら取り出せる。
9. **`--add-data` で設定ファイルを入れない。** 変更のたびに再ビルドが必要になり、秘密情報も漏れる。
10. **`sys._MEIPASS` を設定ファイルの探索に使わない。** バンドル内部（PyInstaller 6.x の onedir では `_internal`）を指すため。外部ファイルは `sys.executable` の親か、固定パス（`/etc/dcim/`）で探す。
11. **設定ファイルの権限は 640（root:dcim）。** 全員が読める状態にしない。
12. **必須設定が無い場合は起動時に失敗させる。** デフォルト値で動き続けるほうが危険。

### 5.3 実行・運用

13. **`runserver` を本番で使わない。** 使う場合も `--noreload` が必須（自動リロードは frozen 環境で動かない）。
14. **書き込み先は `/var/lib/dcim` などバンドル外に。** ログ・アップロード・SQLite などをバンドル内に書かない。
15. **実行ユーザーはバイナリを書き換えられないようにする。** `/opt/dcim` 配下は root 所有・実行ユーザーは読み取り＋実行のみ。
16. **Waitress は静的ファイルを配信しない。** WhiteNoise か nginx を用意する。
17. **`DEBUG=False` では `ALLOWED_HOSTS` が必須。** 設定ファイルに忘れずに書く。
18. **SELinux が有効な場合（Rocky 標準）、`/opt` 配下のバイナリ実行や共有ライブラリのロードが拒否されることがある。** `journalctl` や `ausearch -m avc` で確認し、ファイルコンテキストを調整する（**要確認**：環境ごとに必要な対処が異なる）。
    ```bash
    sudo semanage fcontext -a -t bin_t "/opt/dcim/releases(/.*)?"
    sudo restorecon -Rv /opt/dcim
    ```
19. **MySQL ドライバの選択。** mysqlclient を使う場合、`libmysqlclient`（`mariadb-connector-c` など）が配備先にも必要になる。PyMySQL なら不要。
20. **タイムゾーン・ロケールは配備先のものが使われる。** `TIME_ZONE` / `USE_TZ` を settings で明示する。

### 5.4 アップデート・ロールバック

```bash
# アップデート
VERSION=1.0.1
sudo mkdir -p /opt/dcim/releases/$VERSION
sudo cp -a dist/dcim /opt/dcim/releases/$VERSION/
sudo chown -R root:root /opt/dcim/releases/$VERSION
sudo -u dcim /opt/dcim/releases/$VERSION/dcim migrate --noinput        # 先にマイグレーション
sudo ln -sfn /opt/dcim/releases/$VERSION/dcim /opt/dcim/current
sudo systemctl restart dcim

# ロールバック（マイグレーションを戻す必要がない場合）
sudo ln -sfn /opt/dcim/releases/1.0.0/dcim /opt/dcim/current
sudo systemctl restart dcim
```

- 旧バージョンのフォルダは、数世代分残しておく。
- **スキーマ変更を伴うリリースは、ロールバック時に DB を戻せない場合がある。** 後方互換のあるマイグレーション（列追加→後で削除、など）を心がける。

---

## 6. トラブルシュート

| 症状 | 考えられる原因 | 対処 |
| --- | --- | --- |
| 起動時に `ModuleNotFoundError` | hidden import 漏れ | `--debug=imports` でビルドし、該当モジュールを `hiddenimports` / `collect_submodules` に追加 |
| `TemplateDoesNotExist` | テンプレートが `datas` に無い | `datas` にテンプレートのディレクトリを追加 |
| 自作管理コマンドが `Unknown command` | コマンドモジュールが同梱・探索されていない | `collect_submodules("<app>.management.commands")` を追加（要確認） |
| `Permission denied`（実行時、ログに SELinux の拒否） | SELinux のラベル不一致 | `ausearch -m avc` で確認、`semanage fcontext` / `restorecon` |
| `GLIBC_x.xx not found` | ビルド OS より古い OS で実行している | より古い OS でビルドし直す |
| `libmysqlclient.so ... not found` | mysqlclient の共有ライブラリが無い | PyMySQL に切り替える、またはライブラリを導入 |
| 設定が読まれない（デフォルト値で動く） | 設定ファイルの探索パスが想定と違う／権限不足 | 起動時に読み込んだ設定ファイルのパスをログ出力する。`DCIM_CONFIG` を明示指定して切り分け |
| `SECRET_KEY` 関連のエラーでビルド失敗 | ビルド時にも settings を import するため | ビルド時のみ仮の環境変数を渡す（3.6 参照） |
| 静的ファイル（admin の CSS）が出ない | collectstatic 未実行／配信手段が無い | `collectstatic` を実行し、WhiteNoise か nginx で配信 |
| 起動が遅い | onefile で一時展開している | onedir に切り替える |

---

## 7. 配備チェックリスト

**ビルド前**
- [ ] ビルド環境が配備先と同じ OS・アーキテクチャ
- [ ] `requirements.txt` のバージョン固定
- [ ] `config.example.toml` のみをリポジトリに入れ、秘密情報は含めていない

**ビルド後**
- [ ] `dcim check` / `dcim showmigrations` が通る
- [ ] `dcim help` に自作管理コマンドが表示される
- [ ] `ldd` で `not found` が無い
- [ ] 素の Rocky 9 コンテナで `dcim check` が通る
- [ ] `dcim serve` で HTTP 応答が返る

**配備時**
- [ ] `/opt/dcim` は root 所有、`/etc/dcim/config.toml` は 640（root:dcim）
- [ ] `/var/lib/dcim`・`/var/log/dcim` は dcim が書き込み可
- [ ] `migrate` / `collectstatic` を実行済み
- [ ] systemd ユニットが `enable` され、再起動後も自動起動する
- [ ] SELinux 有効環境で `journalctl` / `ausearch` にエラーが出ていない
- [ ] リバースプロキシ（TLS）経由でアクセスできる
- [ ] ロールバック手順を 1 度は試している

---

## 8. 未確認事項（実機で要確認）

- PyInstaller 同梱の Django フックが、使用バージョンで `INSTALLED_APPS` をどこまで自動検出するか
- 自作管理コマンド（`management/commands`）が frozen 環境で自動認識されるか
- `collect_data_files("django")` の範囲を絞れるか（バンドルサイズ）
- SELinux enforcing 下で必要なファイルコンテキストの設定
- gunicorn を使う場合の hidden import（本手順は Waitress 前提）
- Nuitka でのビルド可否（Django フォーラムに、Nuitka 2.4.8 / Django 5.1.2 でビルドに失敗した報告あり。現行版は未検証）

---

## 参考資料

- PyInstaller: Run-time Information（`sys.frozen` / `sys._MEIPASS` / `sys.executable`） — https://pyinstaller.org/en/stable/runtime-information.html
- PyInstaller: When Things Go Wrong（hidden import、FAQ の Django 項目） — https://github.com/pyinstaller/pyinstaller/blob/fbf7948be85177dd44b41217e9f039e1d176de6b/doc/when-things-go-wrong.rst
- django-binary-builder（PyInstaller onedir ＋ Waitress の実装例、秘密情報の注意書き） — https://pypi.org/project/django-binary-builder/0.1.2/
- Django Forum: Can I convert my Django project to a standalone executable file? — https://forum.djangoproject.com/t/can-i-convert-my-django-project-to-a-standalone-executable-file-for-distribution/29976
- Django Forum: Has anyone managed to compile Django with Nuitka? — https://forum.djangoproject.com/t/has-anyone-managed-to-compile-django-with-nuitka/35637
