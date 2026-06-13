# Flask → FastAPI リライト計画

作成日: 2026-06-13

---

## 1. 目的・背景

現在の実装は Flask 3.0.3 ベース（WSGI）。  
FastAPI（ASGI）へ移行することで以下を得る。

- 自動 OpenAPI ドキュメント（`/docs`）によるエンドポイント可視化
- Pydantic による型安全なリクエスト/レスポンス検証
- `async def` 対応による I/O 効率向上の余地
- WSGI → ASGI でロングポーリング・SSE のスレッド消費削減

---

## 2. 技術スタック変更

### 削除するパッケージ

| パッケージ | 理由 |
|---|---|
| `Flask==3.0.3` | FastAPI に置き換え |
| `Flask-Cors==4.0.0` | Starlette の `CORSMiddleware` で代替 |
| `Flask-Limiter==3.5.0` | `slowapi` で代替 |

### 追加するパッケージ

| パッケージ | 役割 |
|---|---|
| `fastapi>=0.111` | Web フレームワーク（ASGI） |
| `uvicorn[standard]>=0.29` | ASGI サーバー |
| `slowapi>=0.1.9` | FastAPI 向けレート制限（Limits ベース） |
| `sse-starlette>=1.6` | SSE ストリーミングレスポンス |

### 据え置くパッケージ

| パッケージ | 理由 |
|---|---|
| `bcrypt==4.1.2` | そのまま使用可 |
| `python-dotenv==1.0.1` | そのまま使用可 |
| `sqlite3`（標準ライブラリ） | 同期 I/O のまま継続（後述） |

---

## 3. アーキテクチャ変更方針

### 3-1. 同期 vs 非同期 DB の方針

SQLite は読み書きの競合が少なくシンプルな用途のため、**同期 `sqlite3` を維持**する。  
FastAPI は `def`（同期）のルート関数をスレッドプールで自動実行するため、既存の DB アクセスコードをほぼそのまま移植できる。

> `aiosqlite` への移行は将来の最適化フェーズとする。

### 3-2. Flask 概念と FastAPI 概念の対応表

| Flask | FastAPI | 備考 |
|---|---|---|
| `Blueprint` | `APIRouter` | ほぼ 1:1 対応 |
| `Flask.g` | `Depends()` + generator | DB 接続をリクエストスコープで管理 |
| `@app.before_request` | `Depends()` または Middleware | 認証は `Depends(verify_auth)` |
| `current_app` | `Request.app.state` または DI | event_dispatcher で使用 |
| `request.get_json()` | `body: SomeModel` または `Request.json()` | Pydantic モデル推奨 |
| `request.args` | `Query(...)` パラメータ | |
| `request.headers` | `Request.headers` | |
| `make_response(jsonify(...), N)` | `JSONResponse(content, status_code=N)` | |
| `Response(stream_with_context(...))` | `EventSourceResponse(...)` | sse-starlette |
| `@app.errorhandler(404)` | `@app.exception_handler(404)` | |

---

## 4. ファイル別変更計画

### 4-1. `app/__init__.py` → `app/main.py`

```
create_app() を廃止し FastAPI インスタンスを直接生成。

変更点:
- `Flask(__name__)` → `FastAPI()`
- `CORS(app, ...)` → `app.add_middleware(CORSMiddleware, ...)`
- `limiter.init_app(app)` → `Limiter(app, ...)` (slowapi 方式)
- `app.register_blueprint(bp)` → `app.include_router(router)`
- `@app.before_request` authenticate → `Depends(verify_auth)` を各ルーターに設定
- `@app.before_request` log_request → Middleware に移動
- `@app.errorhandler(N)` → `@app.exception_handler(N)`
- `app.teardown_appcontext(close_db)` → DB 接続は Depends の generator で管理
```

### 4-2. `app/database.py`

```
変更点:
- `from flask import g, current_app` を削除
- get_db() を FastAPI の Depends generator に書き換え

移行後のイメージ:
  def get_db():
      db = sqlite3.connect(DB_PATH, detect_types=...)
      db.row_factory = sqlite3.Row
      db.execute('PRAGMA journal_mode=WAL')
      try:
          yield db
      finally:
          db.close()

- init_db() はアプリ起動時の @app.on_event("startup") または lifespan で呼ぶ
- close_db() は不要（generator の finally で管理）
```

### 4-3. `app/auth.py`

```
変更点:
- Flask の request/g を fastapi の Request に置き換え
- verify_auth() を FastAPI の依存関数として書き換え

移行後のイメージ:
  def verify_auth(request: Request, db: sqlite3.Connection = Depends(get_db)):
      # 公開ルートチェック
      # X-Auth-Token / Basic Auth 検証
      # username を返す（認証失敗時は HTTPException(401) を raise）
      return username

- ルーター側では router = APIRouter(dependencies=[Depends(verify_auth)]) とすることで
  Blueprint 全体に認証を一括適用できる
- 公開ルート（/redfish/v1/, /SessionService/Sessions/, JsonSchemas/*, Registries/*）は
  dependencies を付けない別ルーターに分離する
```

### 4-4. `app/helpers.py`

```
変更点:
- Flask の make_response/jsonify を削除
- 全関数を fastapi.responses.JSONResponse / Response を使うよう書き換え

対応表:
  json_response(data, status) → JSONResponse(content=data, status_code=status, headers={OData-Version: 4.0})
  etag_response(data, status) → JSONResponse + ETag ヘッダ
  not_found_response() → JSONResponse 404
  bad_request_response(msg) → JSONResponse 400
  created_response(data, location) → JSONResponse 201 + Location ヘッダ
  no_content_response() → Response(status_code=204, headers={OData-Version: 4.0})
  apply_odata_params(members) → Request を引数で受け取るか Query パラメータで受け取る
  odata_context / now_iso / log_entry_to_dict → 変更不要
```

### 4-5. `app/event_dispatcher.py`

```
最大の変更箇所。Flask の app_context に依存した _send_to_subscribers を書き換える。

変更点:
- `with app.app_context():` を削除
- DB 接続を直接 sqlite3.connect() で取得するか、引数として渡す
- SSE の Queue ベース実装は asyncio.Queue + asyncio generator に書き換え
  (sse-starlette の EventSourceResponse が async generator を期待するため)

移行後のイメージ:
  - _sse_clients: list[asyncio.Queue] に変更
  - add_sse_client() / remove_sse_client() に asyncio.Lock を使用
  - dispatch_event() を async def に変更、asyncio.create_task() で実行
  - event_service.py の SSE エンドポイントは EventSourceResponse(generator()) を返す
```

### 4-6. `app/routes/*.py`（全 Blueprint → APIRouter）

全ファイル共通の変更:

```python
# Before (Flask)
from flask import Blueprint, request
bp = Blueprint('xxx', __name__)

@bp.route('/redfish/v1/Xxx/', methods=['GET', 'POST'])
def xxx():
    db = get_db()
    data = request.get_json()
    ...
    return json_response({...})

# After (FastAPI)
from fastapi import APIRouter, Request, Depends
router = APIRouter()

@router.get('/redfish/v1/Xxx/')
def get_xxx(db=Depends(get_db)):
    ...
    return json_response({...})

@router.post('/redfish/v1/Xxx/')
def post_xxx(body: XxxRequest, db=Depends(get_db)):
    ...
    return created_response({...})
```

各ファイルの個別注意点:

| ファイル | 注意点 |
|---|---|
| `session_service.py` | POST /Sessions/ は認証不要 → public_router に配置 |
| `event_service.py` | SSE エンドポイントを `EventSourceResponse` に書き換え |
| `update_service.py` | ファイルアップロードは `UploadFile` を使用 |
| `task_service.py` | `create_task()` / `complete_task()` は DB を引数で受け取るよう変更不要（既存シグネチャ維持） |
| `systems.py` / `managers.py` / `chassis.py` | 行数が多いが変換パターンは同一 |

---

## 5. ディレクトリ構成（変更後）

```
redfish-emu/
├── app/
│   ├── main.py              # FastAPI インスタンス生成、ルーター登録、ミドルウェア設定
│   ├── auth.py              # verify_auth() Depends 関数
│   ├── config.py            # 変更なし
│   ├── database.py          # get_db() generator Depends 関数
│   ├── event_dispatcher.py  # asyncio.Queue ベースに書き換え
│   ├── helpers.py           # JSONResponse ベースに書き換え
│   └── routes/              # Blueprint → APIRouter
│       └── (各ファイル同名で維持)
├── Dockerfile               # CMD を uvicorn app.main:app --host 0.0.0.0 --port 8008 に変更
├── docker-compose.yml       # 変更なし（ポート設定のみ）
└── requirements.txt         # fastapi / uvicorn[standard] / slowapi / sse-starlette に更新
```

---

## 6. Dockerfile / 起動コマンド変更

```dockerfile
# Before
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8008"]

# After
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8008"]
```

---

## 7. 移行フェーズ

| フェーズ | 作業内容 | 規模 |
|---|---|---|
| **Phase 1** | `requirements.txt` 更新、`app/main.py` 骨格作成、`app/database.py` Depends 化 | 小 |
| **Phase 2** | `app/helpers.py` JSONResponse 化、`app/auth.py` Depends 化 | 小 |
| **Phase 3** | 全 Blueprint → APIRouter 変換（15 ファイル） | 大 |
| **Phase 4** | `app/event_dispatcher.py` asyncio 化、SSE エンドポイント書き換え | 中 |
| **Phase 5** | Dockerfile / docker-compose.yml 更新、動作確認 | 小 |
| **Phase 6** | CLAUDE.md 更新（技術スタック・アーキテクチャルール） | 小 |

---

## 8. 移行時の注意点・リスク

### strict_slashes
Flask では `app.url_map.strict_slashes = False` で末尾スラッシュを無視していた。  
FastAPI は **デフォルトで strict**。  
→ 全ルートパスの末尾スラッシュを統一するか、`redirect_slashes=False` を FastAPI に設定する。

### `request.path` の取得
Flask の `request.path` → FastAPI では `request.url.path`。

### `g.current_user` の伝搬
Flask の `g` オブジェクトはリクエストスコープのグローバル。  
FastAPI では `verify_auth` の戻り値（username）をルート関数の引数として受け取る。  
ルート関数が username を必要とする箇所は引数に `current_user: str = Depends(verify_auth)` を追加する。

### event_dispatcher の app_context 廃止
`_send_to_subscribers` 内の `with app.app_context()` を削除し、DB 接続を直接生成するよう変更が必要。

### レート制限
`slowapi` は Flask-Limiter とほぼ同じ `@limiter.limit(...)` デコレータ API を提供するが、  
`Limiter` のセットアップ方法が異なる（`app.state.limiter` に設定し exception handler を追加）。

### テスト
既存のテストコードがある場合は `TestClient` を `httpx` ベースの `fastapi.testclient.TestClient` に差し替える。

---

## 9. 完了基準

- [ ] `docker compose up` で起動し、`localhost:8008` に応答する
- [ ] `GET /redfish/v1/` が認証なしで 200 を返す
- [ ] Basic Auth / X-Auth-Token による認証が通る
- [ ] 全 Blueprint に相当するルートが 200/201/204 を返す
- [ ] SSE (`GET /redfish/v1/EventService/SSE`) が接続を維持しハートビートを送信する
- [ ] レート制限超過時に 429 を返す
- [ ] `GET /docs` で自動生成 OpenAPI ドキュメントが表示される
