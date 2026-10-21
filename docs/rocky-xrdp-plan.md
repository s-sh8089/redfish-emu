# rocky-server に xrdp でデスクトップを載せる計画

状態: **実装済み(xrdp + Xfce + Guacamole によるブラウザ表示)。検証結果は末尾の「8. 実装結果」。**

## 1. 現状

- `simulator/RockyLinuxServer/Dockerfile`: `rockylinux/rockylinux:9`(Rocky 9.8、aarch64)に sshd だけを入れ、`CMD sshd -D -e`。
- systemd は無く、PID 1 は sshd。電源連携(`docker stop` / `kill` / `start`)は PID 1 の SIGTERM に依存する。
- 公開ポートは `2200:22` のみ。コンテナの上限メモリは設定していない(Docker Desktop の VM は約 3.9GB を、BMC の QEMU 2G と共有する)。

## 2. 調査結果

| 項目 | 結果 |
|---|---|
| xrdp / xorgxrdp | EPEL 9 に aarch64 版がある(xrdp 0.10.6.1、xorgxrdp 0.10.5)。`epel-release` と `crb` の有効化が必要 |
| デスクトップ | EPEL 9 に Xfce 4.18(`xfce4-session` など)の aarch64 版がある。軽量なので第一候補 |
| 代替 | `tigervnc-server`(標準リポジトリ)。xrdp の `Xvnc` バックエンドにもなるが、今回は xorgxrdp を使う |
| インストール可否 | 使い捨てコンテナで、xrdp・xorgxrdp・xfce4-session・xfwm4・xfce4-panel などの依存解決とダウンロードまで成功(実インストールと起動は未確認) |
| systemd | 無い。`xrdp-sesman` と `xrdp` を自前で起動する必要がある |

## 3. 方針

- **systemd は入れない**。`entrypoint.sh` が `xrdp-sesman`、`xrdp`、`sshd` を起動し、SIGTERM で全部を止める(既存の「PID 1 に SIGTERM で電源 Off」を維持する)。
- デスクトップは **Xfce**(`startxfce4`)。ユーザーは一般ユーザー `rocky`(パスワード `rocky`)を追加する。root での xrdp ログインは避ける。
- RDP ポートは `3389`。ホストには `3390:3389` で公開する(Mac 標準の 3389 競合を避ける)。
- Dockerfile は既存の層に追記する。BMC のイメージには触れない(Yocto 再ビルド不要)。

## 4. 実装手順

1. `Dockerfile`: `epel-release` を入れ、`crb` を有効にして、`xrdp xorgxrdp xfce4-session xfwm4 xfce4-panel xfdesktop xfce4-terminal Thunar dbus-x11 xorg-x11-server-Xorg` などを入れる。`useradd rocky`、`~rocky/.xsession` に `startxfce4`、`EXPOSE 3389` を足す。
2. `entrypoint.sh`(新規): `dbus` の machine-id 生成、`xrdp-sesman`、`xrdp` を起動し、`sshd -D` を前面で動かす。`trap` で TERM を受け、子プロセスを停止する。
3. `docker-compose.sim.yml`: `rocky-server` に `3390:3389`、`shm_size: 512m`(Xfce・ブラウザ用)、必要ならメモリ上限を追加する。
4. 日本語環境が必要なら `glibc-langpack-ja` とフォントを追加する。
5. `docs/` に変更点を追記する(`image-changes.md` と本書の実績)。

## 5. 確認項目

- Mac の「Windows App」(Microsoft Remote Desktop)から `localhost:3390` に `rocky` でログインして、Xfce が表示される。
- `docker stop rocky-server` が 10 秒以内に終わる(`stop_grace_period`)。BMC からの `ForceOff` / `On` / `Reset` でデスクトップが落ちて復帰する。
- 既存の sshd(`2200`)と `power-bridge` の連携が壊れていない。
- `/stats` の CPU 値が、デスクトップを動かしたときも妥当(温度・ファン連動に影響するため。デスクトップ起動で CPU が上がり、温度が上がるのは想定どおり)。

## 6. リスクと注意

- **サイズ**: イメージは数百 MB 増える(未計測)。初回ビルドに数分かかる。
- **メモリ**: Xfce で 300〜500MB 程度の見込み(未計測)。Docker Desktop の VM メモリが不足する場合は、設定を増やす必要がある。
- **電源 Off の挙動**: Xfce の「ログアウト・シャットダウン」はコンテナ内では無効。電源操作は BMC 経由のみになる。
- **セッション**: コンテナ再起動でセッションは消える。`/var/run/xrdp` の古い PID ファイルが残らないよう、起動時に削除する。
- **セキュリティ**: パスワード `rocky` は検証用。RDP を公開する場合は `127.0.0.1:3390` に束縛する。
- **GPU / 画面**: ソフトウェア描画(llvmpipe)なので、動画や 3D は重い。サーバー GUI の確認用途には十分な見込み。
- **xrdp の既知の落とし穴**: Wayland は使えない(Xorg のみ)。画面ロックと compositor は無効にしたほうが安定する。

## 7. 未決事項(括弧内は未決のまま進める場合の既定値)

| 項目 | 既定 |
|---|---|
| デスクトップ環境 | Xfce(他に GNOME / MATE も可能だが重い) |
| ログインユーザー | `rocky` / `rocky`(sudo 可) |
| 公開ポート | `127.0.0.1:3390` |
| ブラウザなどの追加アプリ | なし |
| 日本語入力 | なし |

## 8. 実装結果(Guacamole 方式 = 案 A)

### 変更ファイル
- `simulator/RockyLinuxServer/Dockerfile`: EPEL と crb から xrdp / xorgxrdp / Xfce / mesa-dri-drivers / 日本語フォントを追加。一般ユーザー `rocky`(wheel、パスワード `rocky`)と `~rocky/.xsession`(`startxfce4`)を作成。`CMD` は `entrypoint.sh` に変更。
- `simulator/RockyLinuxServer/entrypoint.sh`(新規): `dbus-daemon`、`xrdp-sesman`、`xrdp`、`sshd -D` を起動。前回の pid ファイルを削除。SIGTERM で sshd と xrdp を止めて終了。
- `simulator/Guacamole/user-mapping.xml`・`guacamole.properties`(新規): 認証 `admin` / `admin`、接続 `rocky-server`(RDP、`rocky` / `rocky`)。
- `docker-compose.sim.yml`: `rocky-server` に `127.0.0.1:3390:3389` と `shm_size: 512m`。`guacd`(`guacamole/guacd`)と `guacamole`(`guacamole/guacamole`、`GUACAMOLE_HOME=/config`、`127.0.0.1:8081:8080`)を追加。

### 使い方
- ブラウザ: `http://localhost:8081/guacamole/` に `admin` / `admin` でログインし、`rocky-server` を選ぶ。
- RDP クライアント: `localhost:3390`(`rocky` / `rocky`)。
- ssh(`2200`)と `power-bridge` は従来どおり。

### 検証結果
| 項目 | 結果 |
|---|---|
| 起動 | `dbus`、`xrdp-sesman`、`xrdp`、`sshd` が起動 |
| Guacamole | ログインできる(HTTP 200)。接続 `rocky-server` が一覧に出る |
| RDP セッション | Guacamole の HTTP トンネル(`/tunnel?connect`)で接続すると、`rocky` ユーザーで `Xorg` / `xfce4-session` / `xfce4-panel` が起動(画面の目視確認はしていない) |
| `docker stop rocky-server` | 約 0.2 秒で停止。`docker start` 後、`xrdp` / `xrdp-sesman` / `sshd` が再起動し、ssh も接続できた |
| メモリ | `guacamole` 約 377MiB、`rocky-server` 約 8MiB(セッション無し)、`guacd` 約 13MiB。`ast2700-obmc` は約 1.5GiB。上限 3.8GiB に収まる |
| イメージ | Xfce 一式は 210 パッケージ、ダウンロード 188MB、展開後 539MB(事前計測) |

### 未確認・注意
- ブラウザでの実際の画面表示と操作(日本語入力を含む)は、目視していない。
- BMC からの `ForceOff` / `On` 連携は、`docker stop` / `start` では確認したが、Redfish 経由では再確認していない。
- `admin` / `admin` と `rocky` / `rocky` は検証用。公開先は `127.0.0.1` に限定している。

### 追加検証: BMC の Redfish から電源操作(GUI 連動)
| 手順 | 結果 |
|---|---|
| Guacamole のトンネル API で RDP セッションを開始 | `rocky` ユーザーで `Xorg` / `xfce4-session` が起動 |
| `POST /redfish/v1/Systems/system/Actions/ComputerSystem.Reset`(`{"ResetType":"ForceOff"}`、`root` / `0penBmc`、`https://localhost:2443`) | 4 秒後に `rocky-server` は `Exited (137)`、Redfish の `PowerState` は `Off`。24 秒後まで停止のまま。GUI のプロセスも消滅 |
| 同 `{"ResetType":"On"}` | 約 11 秒で `Up`、`PowerState` は `On`。`xrdp` / `xrdp-sesman` / `sshd` が起動 |

- 再起動後に `Xorg` / `xfce4-session` は動いていない。実機の電源 Off/On と同様、GUI は再ログインが必要(Guacamole で接続を開き直す)。
- `guacamole` / `guacd` は別コンテナで、電源操作の対象外(動いたまま)。
- 未確認: ブラウザを開いたまま電源 Off にしたときの画面表示、`GracefulShutdown` などの他の `ResetType`。

## 9. 確認事項まとめ

| 区分 | 項目 | 状態 |
|---|---|---|
| 確認済み | xrdp / Xfce が起動し、RDP セッションで Xfce のプロセスが立ち上がる | OK |
| 確認済み | Guacamole のログインと接続一覧(`rocky-server`) | OK |
| 確認済み | `docker stop` が約 0.2 秒で終了し、`start` 後に xrdp / sshd が復帰 | OK |
| 確認済み | Redfish `ForceOff` で `rocky-server` と GUI が停止、`On` で起動 | OK |
| 確認済み | メモリが上限 3.8GiB に収まる(`guacamole` 約 377MiB) | OK |
| 未確認 | ブラウザ・RDP クライアントでの実際の画面表示と操作(日本語入力を含む) | 目視していない |
| 未確認 | 電源 Off 時にブラウザ側に出る表示 | 未確認 |
| 未確認 | `GracefulShutdown` など、`ForceOff` 以外の `ResetType` | 未確認 |
| 注意 | `admin` / `admin`、`rocky` / `rocky` は検証用。公開先は `127.0.0.1` | — |
| 注意 | Xfce の「シャットダウン」はコンテナ内では効かない。電源操作は BMC 経由 | — |
| 注意 | 動作確認で Mac の `python3` は Xcode ライセンス未承諾のため使えなかった(`sed` で代替) | — |
