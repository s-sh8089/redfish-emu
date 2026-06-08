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
bcrypt (パスワードハッシュ化)
Flask-Limiter (レート制限)

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
- **認証:** 全エンドポイントに認証が必要（`app/auth.py` の `verify_auth()` を `before_request` で適用）。
- **パスワード:** 新規作成・更新は必ず `auth.hash_password()` で bcrypt ハッシュ化する。
- **タスク生成:** ファームウェア更新など非同期操作は `task_service.create_task()` でタスクを生成する。

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
│   ├── __init__.py          # Flask app factory (create_app)、Blueprint登録、認証・レート制限・CORSミドルウェア
│   ├── auth.py              # 認証ミドルウェア (verify_auth)、RBAC、ロックアウト、bcrypt検証
│   ├── config.py            # 設定クラス (DB_PATH = /data/redfish.db)
│   ├── database.py          # SQLite 初期化 (init_db)、get_db()、シードデータ、パスワードマイグレーション
│   ├── event_dispatcher.py  # Webhook 配信ロジック、SSE クライアント管理
│   ├── helpers.py           # json_response / etag_response / apply_odata_params / odata_context 等の共通関数
│   └── routes/              # Flask Blueprint (リソース単位で1ファイル)
│       ├── __init__.py
│       ├── service_root.py       # GET /redfish/v1/
│       ├── account_service.py    # AccountService / Accounts (bcrypt対応) / Roles
│       ├── session_service.py    # SessionService / Sessions (タイムアウト対応)
│       ├── systems.py            # Systems / Processors / Memory / Storage (Controller・Volume) / EthernetInterfaces / LogServices
│       ├── chassis.py            # Chassis / Thermal / Power / PowerSubsystem / Sensors / PCIeSlots
│       ├── managers.py           # Managers/bmc / EthernetInterfaces / HostInterfaces / SerialInterfaces / LogServices / NetworkProtocol
│       ├── event_service.py      # EventService / Subscriptions (PATCH対応) / SSE
│       ├── update_service.py     # UpdateService / FirmwareInventory / SoftwareInventory / HTTP Push
│       ├── task_service.py       # TaskService / Tasks (個別GET/DELETE・create_task関数)
│       ├── telemetry_service.py  # TelemetryService / MetricReports / Triggers
│       ├── certificate_service.py# CertificateService / GenerateCSR / ReplaceCertificate / POST証明書
│       ├── json_schemas.py       # JsonSchemas
│       ├── registries.py         # Registries
│       ├── cables.py             # Cables
│       └── aggregation_service.py# AggregationService / AggregationSources
├── data/                    # SQLite DB 保存先 (コンテナ volume mount: ./data:/data)
│   └── redfish.db           # 自動生成される。git管理対象外
├── docs/                    # ドキュメント置き場
├── Dockerfile               # python:3.11-slim ベース、port 8008
├── docker-compose.yml       # port 8008:8008、./data:/data ボリューム
├── requirements.txt         # Flask==3.0.3, Flask-Limiter==3.5.0, bcrypt==4.1.2, python-dotenv==1.0.1
├── README.md                # 環境構築・使用方法
└── CLAUDE.md                # このファイル
```

## 重要ファイル

| ファイル | 役割 |
|---|---|
| `app/__init__.py` | `create_app()` 内で全 Blueprint を登録する。CORS・レート制限・認証 `before_request` も定義。 |
| `app/auth.py` | `verify_auth()` で X-Auth-Token / Basic Auth を検証。`hash_password()` で bcrypt ハッシュ生成。`_increment_failure()` でロックアウト管理。 |
| `app/database.py` | `_create_tables()` でテーブル定義、`_seed_data()` で初期データ投入（bcryptハッシュ済み）。`_migrate_passwords()` で既存平文パスワードをハッシュ化。`get_db()` は Flask の `g` オブジェクト経由で接続管理。 |
| `app/helpers.py` | `json_response` / `etag_response` / `not_found_response` / `bad_request_response` / `created_response` / `no_content_response` / `apply_odata_params` / `odata_context` を提供。 |
| `app/event_dispatcher.py` | `dispatch_event()` で Webhook 非同期配信。`add_sse_client()` / `remove_sse_client()` で SSE クライアント管理。 |
| `app/routes/task_service.py` | `create_task(db, messages)` / `complete_task(db, task_id, ...)` を他ルートからインポート可能な形で提供。 |
| `app/config.py` | `DB_PATH` は環境変数 `DB_PATH` で上書き可能。`CORS_ORIGINS` 環境変数で CORS オリジン制限が可能。 |

## 認証ルール

| エンドポイント | 認証要否 |
|---|---|
| `GET /redfish/v1/` | 不要 |
| `POST /redfish/v1/SessionService/Sessions/` | 不要（ログイン） |
| `GET /redfish/v1/JsonSchemas/*` | 不要 |
| `GET /redfish/v1/Registries/*` | 不要 |
| その他全エンドポイント | 必要（X-Auth-Token または Basic Auth） |

セッションタイムアウト: 30分。ロックアウト閾値: 3回連続失敗。

## 禁止事項

- `data/redfish.db` を git にコミットしない（シードデータは `database.py` で管理する）。
- `jsonify` を routes 内で直接使用しない（必ず `helpers.py` の関数を使う）。
- テーブルの直接 DROP / TRUNCATE を行わない（データリセットはコンテナ外から `redfish.db` を削除して再起動する）。
- `flask run` を Docker 外でそのまま実行しない（`DB_PATH` が未設定になりパスが変わる）。
- パスワードを平文で DB に保存しない（必ず `auth.hash_password()` を使う）。

## Git運用

- `data/redfish.db` は `.gitignore` に追加する。
- コミットメッセージは日本語可。変更内容が分かる簡潔な記述にする。
- ブランチ戦略は未定義（現状 main 直コミット）。
