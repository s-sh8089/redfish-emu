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
FastAPI
SQLite3
Docker
Docker compose
uvicorn (ASGI サーバー)
slowapi (レート制限)
sse-starlette (SSE ストリーミング)
bcrypt (パスワードハッシュ化)

## 開発環境
コンテナを使い、localhost:8008でHTTP通信をする。

## アーキテクチャルール

- エンドポイントはリソース単位で **FastAPI APIRouter** に分割し、`app/routes/` 配下に配置する。
- 新しいエンドポイント追加時は `app/routes/<resource>.py` を作成し、`app/main.py` の `app.include_router()` で登録する。
- データアクセスは必ず `app/database.py` の `get_db()` を `Depends(get_db)` 経由で使う（直接 `sqlite3.connect` を呼ばない）。
- レスポンスは必ず `app/helpers.py` の関数を使って返す（`JSONResponse` を直接使わない）。
- 全レスポンスに `OData-Version: 4.0` ヘッダを含める（`json_response` が自動付与）。
- `@odata.id` は必ずリソースの URL パスと一致させる。
- コレクションリソースは `Members` と `Members@odata.count` を必ず含める。
- **認証:** 全ルーターに `APIRouter(dependencies=[Depends(verify_auth)])` で認証を適用する。`verify_auth()` が公開ルートを内部で免除する。
- **パスワード:** 新規作成・更新は必ず `auth.hash_password()` で bcrypt ハッシュ化する。
- **タスク生成:** ファームウェア更新など非同期操作は `task_service.create_task()` でタスクを生成する。

## コーディング規約

- **言語:** Python 3.11
- **フレームワーク:** FastAPI 0.111.1
- **Router 命名:** ファイル名と同じ snake_case（例: `account_service.py` → `router = APIRouter(...)`）
- **ルート関数名:** `<method>_<resource>` 形式の snake_case（例: `def accounts():`、`def accounts_post():`）
- **DB アクセス:** `db: sqlite3.Connection = Depends(get_db)` を関数引数で受け取り、以後再利用する。
- **リクエストボディ:** `body: dict | None = Body(default=None)` で受け取り、`data = body or {}` で使う。
- **JSON 格納フィールド:** SQLite に JSON 配列・オブジェクトを保存する列は `json.loads()` / `json.dumps()` で変換する。
- **エラー:** 存在しないリソースは `not_found_response()` を返す。不正リクエストは `bad_request_response(message)` を返す。
- **コメント:** 原則不要。処理の意図が自明でない箇所のみ 1 行で記述する。

## ディレクトリ構成

```
redfish-emu/
├── app/
│   ├── __init__.py          # 空ファイル（パッケージ宣言のみ）
│   ├── main.py              # FastAPI インスタンス生成、Router 登録、ミドルウェア・lifespan 定義
│   ├── auth.py              # verify_auth() Depends 関数、RBAC、ロックアウト、bcrypt検証
│   ├── config.py            # 設定クラス (DB_PATH = /data/redfish.db)
│   ├── database.py          # SQLite 初期化 (init_db)、get_db() Depends generator、シードデータ
│   ├── event_dispatcher.py  # asyncio.Queue ベース SSE クライアント管理・Webhook 非同期配信
│   ├── helpers.py           # json_response / etag_response / apply_odata_params / odata_context 等
│   └── routes/              # FastAPI APIRouter (リソース単位で1ファイル)
│       ├── __init__.py
│       ├── service_root.py       # GET /redfish/v1/
│       ├── account_service.py    # AccountService / Accounts (bcrypt対応) / Roles
│       ├── session_service.py    # SessionService / Sessions (タイムアウト対応)
│       ├── systems.py            # Systems / Processors / Memory / Storage (Controller・Volume) / EthernetInterfaces / LogServices
│       ├── chassis.py            # Chassis / Thermal / Power / PowerSubsystem / Sensors / PCIeSlots
│       ├── managers.py           # Managers/bmc / EthernetInterfaces / HostInterfaces / SerialInterfaces / LogServices / NetworkProtocol
│       ├── event_service.py      # EventService / Subscriptions (PATCH対応) / SSE (EventSourceResponse)
│       ├── update_service.py     # UpdateService / FirmwareInventory / SoftwareInventory / HTTP Push (UploadFile)
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
├── Dockerfile               # python:3.11-slim ベース、port 8008、uvicorn で起動
├── docker-compose.yml       # port 8008:8008、./data:/data ボリューム
├── requirements.txt         # fastapi==0.111.1, uvicorn[standard]==0.30.1, slowapi==0.1.9, sse-starlette==1.8.2, bcrypt==4.1.2
├── README.md                # 環境構築・使用方法
└── CLAUDE.md                # このファイル
```

## 重要ファイル

| ファイル | 役割 |
|---|---|
| `app/main.py` | FastAPI インスタンス生成。全 APIRouter を `include_router()` で登録。CORS・`SlowAPIMiddleware`・ログ middleware・lifespan（DB 初期化）も定義。 |
| `app/auth.py` | `verify_auth(request, db)` で X-Auth-Token / Basic Auth を検証する FastAPI Depends 関数。公開ルートは内部で免除。`hash_password()` で bcrypt ハッシュ生成。`_increment_failure()` でロックアウト管理。 |
| `app/database.py` | `_create_tables()` でテーブル定義、`_seed_data()` で初期データ投入（bcryptハッシュ済み）。`get_db()` は Depends generator（リクエストスコープで接続を管理し、レスポンス後に close）。`init_db()` はアプリ起動時（lifespan）に呼ばれる。 |
| `app/helpers.py` | `json_response` / `etag_response` / `not_found_response` / `bad_request_response` / `created_response` / `no_content_response` / `apply_odata_params(members, request)` / `odata_context` を提供。すべて `JSONResponse`/`Response` ベース。 |
| `app/event_dispatcher.py` | `dispatch_event(event_data)` async 関数で SSE broadcast + Webhook 配信（asyncio.create_task で非同期）。`add_sse_client()` / `remove_sse_client()` で asyncio.Queue ベースの SSE クライアント管理。 |
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

公開ルートの免除は `app/auth.py` の `verify_auth()` 内で `_PUBLIC_EXACT` / `_PUBLIC_PREFIXES` により判定する。ルーター側での分離は不要。

セッションタイムアウト: 30分。ロックアウト閾値: 3回連続失敗。

## 禁止事項

- `data/redfish.db` を git にコミットしない（シードデータは `database.py` で管理する）。
- `JSONResponse` を routes 内で直接使用しない（必ず `helpers.py` の関数を使う）。
- テーブルの直接 DROP / TRUNCATE を行わない（データリセットはコンテナ外から `redfish.db` を削除して再起動する）。
- Docker 外で `uvicorn` を直接実行しない（`DB_PATH` が未設定になりパスが変わる）。
- パスワードを平文で DB に保存しない（必ず `auth.hash_password()` を使う）。
- `get_db()` を `Depends()` 経由以外で呼ばない（generator なので直接呼ぶと接続が close されない）。

## Git運用

- `data/redfish.db` は `.gitignore` に追加する。
- コミットメッセージは日本語可。変更内容が分かる簡潔な記述にする。
- ブランチ戦略は未定義（現状 main 直コミット）。
