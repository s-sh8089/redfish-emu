# Redfish API Emulator

OpenBMC の bmcweb Redfish API 仕様に基づいたシミュレータです。  
Docker + Flask + SQLite で構成されており、`localhost:8008` でアクセスできます。

---

## 必要条件

| ソフトウェア | 推奨バージョン |
|---|---|
| Docker | 24.0 以上 |
| Docker Compose | v2.0 以上 (Compose V2 プラグイン) |

> `docker compose version` でバージョンを確認できます。

---

## クイックスタート

### 1. リポジトリをクローン

```bash
git clone <repository-url>
cd redfish-emu
```

### 2. コンテナをビルド・起動

```bash
docker compose up --build
```

初回起動時は Python イメージのダウンロードとパッケージインストールが行われます（2〜3分程度）。

### 3. 動作確認

```bash
curl http://localhost:8008/redfish/v1/
```

以下のような JSON レスポンスが返れば起動成功です。

```json
{
    "@odata.id": "/redfish/v1/",
    "@odata.type": "#ServiceRoot.v1_13_0.ServiceRoot",
    "Id": "RootService",
    "Name": "Root Service",
    ...
}
```

### バックグラウンドで起動する場合

```bash
docker compose up --build -d
```

### コンテナの停止

```bash
docker compose down
```

---

## 認証

全エンドポイント（サービスルート `GET /redfish/v1/` とログイン `POST /redfish/v1/SessionService/Sessions/` を除く）は認証が必要です。

### 認証方式

| 方式 | ヘッダー / 方法 |
|---|---|
| セッショントークン | `X-Auth-Token: <token>` |
| Basic 認証 | `Authorization: Basic <base64>` |

セッションタイムアウトは **30 分**。タイムアウト後はセッションが自動削除されます。

### アカウントロックアウト

ログイン失敗が **3 回** を超えるとアカウントがロックされます。  
管理者が `PATCH /redfish/v1/AccountService/Accounts/{id}/` で `{"Locked": false}` を送信するとリセットできます。

### 初期アカウント

| ユーザー名 | パスワード | ロール |
|---|---|---|
| admin | password | Administrator |
| operator1 | password | Operator |
| readonly1 | password | ReadOnly |

> パスワードは bcrypt でハッシュ化されて保存されます。

---

## データの永続化

SQLite データベースはホストの `./data/` ディレクトリに保存されます。  
コンテナを再起動してもデータは保持されます。

データをリセットしたい場合は以下を実行してください。

```bash
docker compose down
rm -f data/redfish.db
docker compose up --build
```

---

## 環境変数

| 変数名 | デフォルト | 説明 |
|---|---|---|
| `DB_PATH` | `data/redfish.db` | SQLite DBファイルパス |
| `SECRET_KEY` | `redfish-emu-secret-key` | Flask シークレットキー |
| `CORS_ORIGINS` | `*` | 許可する CORS オリジン（カンマ区切り） |

---

## 実装済みエンドポイント一覧

ベース URL: `http://localhost:8008`

### Service Root

| Method | Path |
|---|---|
| GET | `/redfish/v1/` |

### Account Service

| Method | Path |
|---|---|
| GET | `/redfish/v1/AccountService/` |
| GET | `/redfish/v1/AccountService/Accounts/` |
| POST | `/redfish/v1/AccountService/Accounts/` |
| GET | `/redfish/v1/AccountService/Accounts/{id}/` |
| PATCH | `/redfish/v1/AccountService/Accounts/{id}/` |
| DELETE | `/redfish/v1/AccountService/Accounts/{id}/` |
| GET | `/redfish/v1/AccountService/Roles/` |
| GET | `/redfish/v1/AccountService/Roles/{id}/` |
| GET | `/redfish/v1/AccountService/LDAP/Certificates/` |

### Session Service

| Method | Path |
|---|---|
| GET | `/redfish/v1/SessionService/` |
| GET | `/redfish/v1/SessionService/Sessions/` |
| POST | `/redfish/v1/SessionService/Sessions/` |
| GET | `/redfish/v1/SessionService/Sessions/{id}/` |
| DELETE | `/redfish/v1/SessionService/Sessions/{id}/` |

### Systems

| Method | Path |
|---|---|
| GET | `/redfish/v1/Systems/` |
| GET, PATCH | `/redfish/v1/Systems/system` |
| **POST** | `/redfish/v1/Systems/system/Actions/ComputerSystem.Reset` |
| GET, PATCH | `/redfish/v1/Systems/system/Bios/` |
| **POST** | `/redfish/v1/Systems/system/Bios/Actions/Bios.ResetBios` |
| **POST** | `/redfish/v1/Systems/system/Bios/Actions/Bios.ChangePassword` |
| **GET, PATCH** | `/redfish/v1/Systems/system/SecureBoot/` |
| GET | `/redfish/v1/Systems/system/Processors/` |
| GET | `/redfish/v1/Systems/system/Processors/{id}/` |
| GET | `/redfish/v1/Systems/system/Memory/` |
| GET | `/redfish/v1/Systems/system/Memory/{id}/` |
| GET | `/redfish/v1/Systems/system/Memory/{id}/MemoryMetrics/` |
| GET | `/redfish/v1/Systems/system/Storage/` |
| GET | `/redfish/v1/Systems/system/Storage/{id}/` |
| GET | `/redfish/v1/Systems/system/Storage/{id}/Drive/{driveId}/` |
| **GET** | `/redfish/v1/Systems/system/Storage/{id}/Controllers/` |
| **GET** | `/redfish/v1/Systems/system/Storage/{id}/Controllers/{ctrlId}/` |
| **GET** | `/redfish/v1/Systems/system/Storage/{id}/Volumes/` |
| GET | `/redfish/v1/Systems/system/EthernetInterfaces/` |
| **GET** | `/redfish/v1/Systems/system/EthernetInterfaces/{id}/` |
| GET | `/redfish/v1/Systems/system/FabricAdapters/` |
| GET | `/redfish/v1/Systems/system/FabricAdapters/{id}/` |
| GET | `/redfish/v1/Systems/system/PCIeDevices/` |
| GET | `/redfish/v1/Systems/system/PCIeDevices/{id}/` |
| GET | `/redfish/v1/Systems/system/LogServices/` |
| GET | `/redfish/v1/Systems/system/LogServices/EventLog/` |
| **POST** | `/redfish/v1/Systems/system/LogServices/EventLog/Actions/LogService.ClearLog` |
| GET | `/redfish/v1/Systems/system/LogServices/EventLog/Entries/` |
| GET | `/redfish/v1/Systems/system/LogServices/EventLog/Entries/{id}/` |
| GET | `/redfish/v1/Systems/system/LogServices/SEL/` |
| **POST** | `/redfish/v1/Systems/system/LogServices/SEL/Actions/LogService.ClearLog` |
| GET | `/redfish/v1/Systems/system/LogServices/SEL/Entries/` |
| GET | `/redfish/v1/Systems/system/LogServices/SEL/Entries/{id}/` |

### Chassis

| Method | Path |
|---|---|
| GET | `/redfish/v1/Chassis/` |
| GET | `/redfish/v1/Chassis/{id}/` |
| **POST** | `/redfish/v1/Chassis/{id}/Actions/Chassis.Reset` |
| GET | `/redfish/v1/Chassis/{id}/Assembly/` |
| GET | `/redfish/v1/Chassis/{id}/Drive/` |
| GET | `/redfish/v1/Chassis/{id}/Drive/{driveId}/` |
| GET | `/redfish/v1/Chassis/{id}/EnvironmentMetrics/` |
| GET | `/redfish/v1/Chassis/{id}/Thermal/` |
| GET | `/redfish/v1/Chassis/{id}/Power/` |
| GET | `/redfish/v1/Chassis/{id}/Sensors/` |
| GET | `/redfish/v1/Chassis/{id}/Sensors/{sensorId}/` |
| GET | `/redfish/v1/Chassis/{id}/ThermalSubsystem` |
| GET | `/redfish/v1/Chassis/{id}/ThermalSubsystem/Fans` |
| GET | `/redfish/v1/Chassis/{id}/ThermalSubsystem/Fans/{fanName}/` |
| **GET** | `/redfish/v1/Chassis/{id}/PowerSubsystem/` |
| GET | `/redfish/v1/Chassis/{id}/PowerSubsystem/PowerSupplies` |
| GET | `/redfish/v1/Chassis/{id}/PowerSubsystem/PowerSupplies/{psuId}` |
| GET | `/redfish/v1/Chassis/{id}/PCIeSlots/` |
| GET | `/redfish/v1/Chassis/{id}/PCIeSlots/{slotName}` |

### Managers

| Method | Path |
|---|---|
| GET | `/redfish/v1/Managers/` |
| **GET, PATCH** | `/redfish/v1/Managers/bmc/` |
| **POST** | `/redfish/v1/Managers/bmc/Actions/Manager.Reset` |
| **POST** | `/redfish/v1/Managers/bmc/Actions/Manager.ForceFailover` |
| **GET, POST** | `/redfish/v1/Managers/bmc/VirtualMedia/` |
| **GET** | `/redfish/v1/Managers/bmc/VirtualMedia/{id}/` |
| **POST** | `/redfish/v1/Managers/bmc/VirtualMedia/{id}/Actions/VirtualMedia.InsertMedia` |
| **POST** | `/redfish/v1/Managers/bmc/VirtualMedia/{id}/Actions/VirtualMedia.EjectMedia` |
| GET | `/redfish/v1/Managers/bmc/EthernetInterfaces/` |
| GET | `/redfish/v1/Managers/bmc/EthernetInterfaces/{id}/` |
| GET | `/redfish/v1/Managers/bmc/EthernetInterfaces/{id}/VLANs/` |
| **GET** | `/redfish/v1/Managers/bmc/HostInterfaces/` |
| **GET** | `/redfish/v1/Managers/bmc/HostInterfaces/{id}/` |
| **GET** | `/redfish/v1/Managers/bmc/SerialInterfaces/` |
| **GET** | `/redfish/v1/Managers/bmc/SerialInterfaces/{id}/` |
| GET | `/redfish/v1/Managers/bmc/LogServices/` |
| GET | `/redfish/v1/Managers/bmc/LogServices/RedfishLog/` |
| **POST** | `/redfish/v1/Managers/bmc/LogServices/RedfishLog/Actions/LogService.ClearLog` |
| GET | `/redfish/v1/Managers/bmc/LogServices/RedfishLog/Entries/{id}/` |
| GET | `/redfish/v1/Managers/bmc/ManagerDiagnosticData/` |
| GET | `/redfish/v1/Managers/bmc/ManagerDiagnosticData/GooglegRPCStatistics` |
| GET, PATCH | `/redfish/v1/Managers/bmc/NetworkProtocol/` |
| GET | `/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates/` |
| **POST** | `/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates/` |
| GET | `/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates/{id}/` |
| GET | `/redfish/v1/Managers/bmc/Truststore/Certificates/` |

### Event Service

| Method | Path |
|---|---|
| GET | `/redfish/v1/EventService/` |
| GET | `/redfish/v1/EventService/Subscriptions/` |
| POST | `/redfish/v1/EventService/Subscriptions/` |
| GET | `/redfish/v1/EventService/Subscriptions/{id}/` |
| **PATCH** | `/redfish/v1/EventService/Subscriptions/{id}/` |
| DELETE | `/redfish/v1/EventService/Subscriptions/{id}/` |
| POST | `/redfish/v1/EventService/Actions/EventService.SubmitTestEvent` |
| **GET** | `/redfish/v1/EventService/SSE` |

### Update Service

| Method | Path |
|---|---|
| GET | `/redfish/v1/UpdateService/` |
| **POST** | `/redfish/v1/UpdateService/update` |
| **POST** | `/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate` |
| GET | `/redfish/v1/UpdateService/FirmwareInventory/` |
| GET | `/redfish/v1/UpdateService/FirmwareInventory/{id}/` |
| **GET** | `/redfish/v1/UpdateService/SoftwareInventory/` |
| **GET** | `/redfish/v1/UpdateService/SoftwareInventory/{id}/` |

### Task Service

| Method | Path |
|---|---|
| GET | `/redfish/v1/TaskService/` |
| GET | `/redfish/v1/TaskService/Tasks/` |
| **GET** | `/redfish/v1/TaskService/Tasks/{id}/` |
| **DELETE** | `/redfish/v1/TaskService/Tasks/{id}/` |

### Certificate Service

| Method | Path |
|---|---|
| GET | `/redfish/v1/CertificateService/` |
| GET | `/redfish/v1/CertificateService/CertificateLocations/` |
| **POST** | `/redfish/v1/CertificateService/Actions/CertificateService.GenerateCSR` |
| **POST** | `/redfish/v1/CertificateService/Actions/CertificateService.ReplaceCertificate` |

### その他のサービス

| Method | Path |
|---|---|
| GET | `/redfish/v1/TelemetryService/` |
| GET | `/redfish/v1/TelemetryService/MetricReportDefinitions/` |
| GET | `/redfish/v1/TelemetryService/MetricReports/` |
| GET | `/redfish/v1/TelemetryService/Triggers/` |
| GET | `/redfish/v1/JsonSchemas/` |
| GET | `/redfish/v1/JsonSchemas/{id}/` |
| GET | `/redfish/v1/Registries/` |
| GET | `/redfish/v1/Registries/{id}/` |
| GET | `/redfish/v1/Cables/` |
| GET | `/redfish/v1/Cables/{id}/` |
| GET | `/redfish/v1/AggregationService/` |
| GET | `/redfish/v1/AggregationService/AggregationSources` |
| GET | `/redfish/v1/AggregationService/AggregationSources/{id}` |

> **太字** は今回追加または更新されたエンドポイントです。

---

## 使用例

### セッション作成

```bash
TOKEN=$(curl -s -X POST http://localhost:8008/redfish/v1/SessionService/Sessions/ \
  -H "Content-Type: application/json" \
  -d '{"UserName": "admin", "Password": "password"}' \
  -D - | grep -i x-auth-token | awk '{print $2}' | tr -d '\r')

echo "Token: $TOKEN"
```

以降のリクエストは `-H "X-Auth-Token: $TOKEN"` を付加します。

### Basic 認証

```bash
curl -s -u admin:password http://localhost:8008/redfish/v1/Systems/system
```

### Boot デバイスの変更

```bash
curl -s -X PATCH http://localhost:8008/redfish/v1/Systems/system \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{
    "Boot": {
      "BootSourceOverrideTarget": "Pxe",
      "BootSourceOverrideEnabled": "Once"
    }
  }'
```

### ユーザーアカウントの作成

パスワードは 8〜20 文字で指定してください。bcrypt でハッシュ化されて保存されます。

```bash
curl -s -X POST http://localhost:8008/redfish/v1/AccountService/Accounts/ \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{
    "UserName": "newuser",
    "Password": "newpassword",
    "RoleId": "ReadOnly"
  }'
```

### ロックアウト解除

```bash
curl -s -X PATCH http://localhost:8008/redfish/v1/AccountService/Accounts/admin/ \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{"Locked": false}'
```

### 電源・リセット操作

`ResetType` で操作の種類を指定します。

#### サーバー電源操作

| ResetType | 結果 |
|---|---|
| `On` / `ForceOn` / `GracefulRestart` / `ForceRestart` / `Nmi` | PowerState → `On` |
| `ForceOff` / `GracefulShutdown` | PowerState → `Off` |
| `PushPowerButton` | 現在の状態をトグル |

```bash
curl -s -X POST http://localhost:8008/redfish/v1/Systems/system/Actions/ComputerSystem.Reset \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{"ResetType": "ForceOff"}'
```

#### BMC リセット

```bash
curl -s -X POST http://localhost:8008/redfish/v1/Managers/bmc/Actions/Manager.Reset \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{"ResetType": "GracefulRestart"}'
```

#### シャーシリセット

```bash
curl -s -X POST http://localhost:8008/redfish/v1/Chassis/chassis1/Actions/Chassis.Reset \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{"ResetType": "PowerCycle"}'
```

### ファームウェア更新

#### HTTP Push（ファイルアップロード）

```bash
curl -s -X POST http://localhost:8008/redfish/v1/UpdateService/update \
  -H "X-Auth-Token: $TOKEN" \
  -F "file=@/path/to/firmware.bin"
```

成功時は `201 Created` とタスクへのリンクが返ります。

#### SimpleUpdate

```bash
curl -s -X POST http://localhost:8008/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{
    "ImageURI": "http://downloads.example.com/firmware/2.5.0",
    "Targets": ["/redfish/v1/UpdateService/FirmwareInventory/BIOS/"]
  }'
```

成功時は `202 Accepted` とタスクへの参照が返ります。

### タスク管理

```bash
# タスク一覧
curl -s -H "X-Auth-Token: $TOKEN" http://localhost:8008/redfish/v1/TaskService/Tasks/

# タスク詳細
curl -s -H "X-Auth-Token: $TOKEN" http://localhost:8008/redfish/v1/TaskService/Tasks/{taskId}/

# タスク削除
curl -s -X DELETE -H "X-Auth-Token: $TOKEN" http://localhost:8008/redfish/v1/TaskService/Tasks/{taskId}/
```

### CSR 生成

```bash
curl -s -X POST http://localhost:8008/redfish/v1/CertificateService/Actions/CertificateService.GenerateCSR \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{
    "CommonName": "bmc.example.com",
    "Organization": ["Example Corp"],
    "CertificateCollection": {"@odata.id": "/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates/"}
  }'
```

### 証明書アップロード

```bash
curl -s -X POST http://localhost:8008/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates/ \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{
    "CertificateString": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
    "CertificateType": "PEM"
  }'
```

### SSE（Server-Sent Events）

```bash
curl -s -N -H "X-Auth-Token: $TOKEN" http://localhost:8008/redfish/v1/EventService/SSE
```

接続後、`SubmitTestEvent` を呼ぶとリアルタイムでイベントが届きます。

### Subscription PATCH

```bash
curl -s -X PATCH http://localhost:8008/redfish/v1/EventService/Subscriptions/{id}/ \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{"EventTypes": ["Alert", "StatusChange"]}'
```

### Webhook アラート通知

#### 1. 受け取り先 URL を登録する

```bash
curl -s -X POST http://localhost:8008/redfish/v1/EventService/Subscriptions/ \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{
    "Destination": "http://your-server/webhook",
    "Context": "my-context",
    "EventTypes": ["Alert"]
  }'
```

#### 2. テストイベントを送信する

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://localhost:8008/redfish/v1/EventService/Actions/EventService.SubmitTestEvent \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{
    "EventType": "Alert",
    "Severity": "Critical",
    "Message": "CPU temperature exceeded critical threshold.",
    "MessageId": "ThermalEvents.1.0.TemperatureAboveUpperCriticalThreshold"
  }'
```

### BMC 日時設定

```bash
curl -s -X PATCH http://localhost:8008/redfish/v1/Managers/bmc/ \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{
    "DateTime": "2025-01-15T09:00:00+09:00",
    "DateTimeLocalOffset": "+09:00"
  }'
```

### ISO イメージのリモートマウント（VirtualMedia）

```bash
# ISO をマウントする
curl -s -X POST http://localhost:8008/redfish/v1/Managers/bmc/VirtualMedia/CD/Actions/VirtualMedia.InsertMedia \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{
    "Image": "http://192.168.1.10/iso/ubuntu-24.04-server.iso",
    "TransferProtocolType": "HTTP",
    "WriteProtected": true
  }'

# ISO をアンマウントする
curl -s -X POST http://localhost:8008/redfish/v1/Managers/bmc/VirtualMedia/CD/Actions/VirtualMedia.EjectMedia \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{}'
```

### BIOS 設定変更

```bash
# BootMode を Legacy に変更
curl -s -X PATCH http://localhost:8008/redfish/v1/Systems/system/Bios/ \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{
    "Attributes": {
      "BootMode": "Legacy",
      "QuietBoot": false
    }
  }'

# BIOS をデフォルトにリセット
curl -s -X POST http://localhost:8008/redfish/v1/Systems/system/Bios/Actions/Bios.ResetBios \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{}'
```

---

## OData クエリパラメータ

コレクションエンドポイントは `$top` と `$skip` をサポートします。

```bash
# 最初の2件
curl -s -H "X-Auth-Token: $TOKEN" "http://localhost:8008/redfish/v1/TaskService/Tasks/?$top=2"

# 3件目以降
curl -s -H "X-Auth-Token: $TOKEN" "http://localhost:8008/redfish/v1/TaskService/Tasks/?$skip=2"
```

---

## レート制限

デフォルトで **600 リクエスト/分** の制限が設定されています。  
超過した場合は `429 Too Many Requests` が返ります。

---

## 初期シードデータ

### ハードウェア構成（シミュレート対象）

- **System:** Dell PowerEdge R750
- **CPU:** Intel Xeon Gold 6338 × 2
- **Memory:** 32GB RDIMM × 4 (合計 128GB)
- **Storage:** 480GB SSD × 2 (Storage0/Drive0, Drive1) + StorageController 0
- **Manager (BMC):** iDRAC9, FW: 2.71.71.71-711
- **Chassis:** 1U RackMount (chassis1)
- **Firmware:** BMC / BIOS / ME / CPLD
- **温度センサー:** CPU1/CPU2/Inlet/Outlet
- **ファン:** Fan1〜Fan6
- **電源:** PSU1 / PSU2 (750W)
- **HostInterface:** KCS (0)
- **SerialInterface:** RS232 (1)

---

## プロジェクト構成

```
redfish-emu/
├── app/
│   ├── __init__.py          # Flask app factory (CORS・レート制限・認証ミドルウェア)
│   ├── auth.py              # 認証・RBAC・ロックアウトロジック
│   ├── config.py            # 設定 (DB_PATH など)
│   ├── database.py          # SQLite 初期化・マイグレーション・シードデータ
│   ├── helpers.py           # レスポンス共通関数 (ETag・ODataクエリ対応)
│   ├── event_dispatcher.py  # Webhook 配信ロジック・SSE クライアント管理
│   └── routes/              # Blueprint (リソース単位)
│       ├── service_root.py
│       ├── account_service.py
│       ├── session_service.py
│       ├── systems.py
│       ├── chassis.py
│       ├── managers.py
│       ├── event_service.py
│       ├── update_service.py
│       ├── task_service.py
│       ├── telemetry_service.py
│       ├── certificate_service.py
│       ├── json_schemas.py
│       ├── registries.py
│       ├── cables.py
│       └── aggregation_service.py
├── data/                    # SQLite DB 保存先 (volume mount)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 参考仕様

[OpenBMC bmcweb Redfish API ドキュメント](https://gbmc.googlesource.com/gbmcweb/+/a69453c76f4b2c81cd5d354c40dd6d5f7d64dc15/Redfish.md)
