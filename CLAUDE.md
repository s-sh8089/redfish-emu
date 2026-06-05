# カスタマイズ

## 基本ルール

- 必ず日本語で応答すること。
- 必ず計画を立てて文書化すること。
- 変更完了後は必ず結果に関するレポートを作成すること。

## プロジェクト概要

下記のリンクに記載されたRedfishAPIのリクエスト、レスポンス、エンドポイントを再現するためのシミュレータ。
https://gbmc.googlesource.com/gbmcweb/+/a69453c76f4b2c81cd5d354c40dd6d5f7d64dc15/Redfish.md


## 技術スタック

Python
Flask
SQLite3
Docker
Docker compose

## 開発環境
コンテナを使い、localhost:8008でHTTP通信をする。

## アーキテクチャルール

- エンドポイントはリソース単位で **Flask Blueprint** に分割し、`app/routes/` 配下に配置する。
- 新しいエンドポイント追加時は `app/routes/<resource>.py` を作成し、`app/__init__.py` の `create_app()` に `app.register_blueprint()` で登録する。
- データアクセスは必ず `app/database.py` の `get_db()` を経由する（直接 `sqlite3.connect` を呼ばない）。
- レスポンスは必ず `app/helpers.py` の関数を使って返す（`jsonify` を直接使わない）。
- 全レスポンスに `OData-Version: 4.0` ヘッダを含める（`json_response` が自動付与）。
- `@odata.id` は必ずリソースの URL パスと一致させる。
- コレクションリソースは `Members` と `Members@odata.count` を必ず含める。

## コーディング規約

- **言語:** Python 3.11
- **フレームワーク:** Flask 3.0.3
- **Blueprint 命名:** ファイル名と同じ snake_case（例: `account_service.py` → `bp = Blueprint('account_service', __name__)`）
- **ルート関数名:** リソースを表す簡潔な snake_case（例: `def account_service():`, `def accounts():`）
- **DB アクセス:** `db = get_db()` を関数先頭で取得し、以後再利用する。
- **JSON 格納フィールド:** SQLite に JSON 配列・オブジェクトを保存する列は `json.loads()` / `json.dumps()` で変換する。
- **エラー:** 存在しないリソースは `not_found_response()` を返す。不正リクエストは `bad_request_response(message)` を返す。
- **コメント:** 原則不要。処理の意図が自明でない箇所のみ 1 行で記述する。

## ディレクトリ構成

```
redfish-emu/
├── app/
│   ├── __init__.py          # Flask app factory (create_app)、Blueprint登録、エラーハンドラ
│   ├── config.py            # 設定クラス (DB_PATH = /data/redfish.db)
│   ├── database.py          # SQLite 初期化 (init_db)、get_db()、シードデータ
│   ├── helpers.py           # json_response / not_found_response 等の共通関数
│   └── routes/              # Flask Blueprint (リソース単位で1ファイル)
│       ├── __init__.py
│       ├── service_root.py       # GET /redfish/v1/
│       ├── account_service.py    # AccountService / Accounts / Roles
│       ├── session_service.py    # SessionService / Sessions
│       ├── systems.py            # Systems / Processors / Memory / Storage / LogServices
│       ├── chassis.py            # Chassis / Thermal / Power / Sensors / PCIeSlots
│       ├── managers.py           # Managers/bmc / EthernetInterfaces / LogServices / NetworkProtocol
│       ├── event_service.py      # EventService / Subscriptions
│       ├── update_service.py     # UpdateService / FirmwareInventory
│       ├── task_service.py       # TaskService / Tasks
│       ├── telemetry_service.py  # TelemetryService / MetricReports / Triggers
│       ├── certificate_service.py# CertificateService / CertificateLocations
│       ├── json_schemas.py       # JsonSchemas
│       ├── registries.py         # Registries
│       ├── cables.py             # Cables
│       └── aggregation_service.py# AggregationService / AggregationSources
├── data/                    # SQLite DB 保存先 (コンテナ volume mount: ./data:/data)
│   └── redfish.db           # 自動生成される。git管理対象外
├── docs/                    # ドキュメント置き場
├── Dockerfile               # python:3.11-slim ベース、port 8008
├── docker-compose.yml       # port 8008:8008、./data:/data ボリューム
├── requirements.txt         # Flask==3.0.3, python-dotenv==1.0.1
├── README.md                # 環境構築・使用方法
└── CLAUDE.md                # このファイル
```

## 重要ファイル

| ファイル | 役割 |
|---|---|
| `app/__init__.py` | `create_app()` 内で全 Blueprint を登録する。新規 Blueprint 追加時は必ずここに追記する。404/405/500 エラーハンドラも定義。 |
| `app/database.py` | `_create_tables()` でテーブル定義、`_seed_data()` で初期データ投入。テーブル追加時は両関数を編集する。`get_db()` は Flask の `g` オブジェクト経由でリクエストごとに接続を管理する。 |
| `app/helpers.py` | `json_response(data, status)` / `not_found_response()` / `bad_request_response(msg)` / `created_response(data, location)` / `no_content_response()` を提供する。 |
| `app/config.py` | `DB_PATH` は環境変数 `DB_PATH` で上書き可能。デフォルトは `data/redfish.db`。 |

## 禁止事項

- `data/redfish.db` を git にコミットしない（シードデータは `database.py` で管理する）。
- `jsonify` を routes 内で直接使用しない（必ず `helpers.py` の関数を使う）。
- テーブルの直接 DROP / TRUNCATE を行わない（データリセットはコンテナ外から `redfish.db` を削除して再起動する）。
- `flask run` を Docker 外でそのまま実行しない（`DB_PATH` が未設定になりパスが変わる）。

## Git運用

- `data/redfish.db` は `.gitignore` に追加する。
- コミットメッセージは日本語可。変更内容が分かる簡潔な記述にする。
- ブランチ戦略は未定義（現状 main 直コミット）。

