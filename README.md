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
| **GET, PATCH** | `/redfish/v1/Systems/system/SecureBoot/` |
| GET | `/redfish/v1/Systems/system/Processors/` |
| GET | `/redfish/v1/Systems/system/Processors/{id}/` |
| GET | `/redfish/v1/Systems/system/Memory/` |
| GET | `/redfish/v1/Systems/system/Memory/{id}/` |
| GET | `/redfish/v1/Systems/system/Memory/{id}/MemoryMetrics/` |
| GET | `/redfish/v1/Systems/system/Storage/` |
| GET | `/redfish/v1/Systems/system/Storage/{id}/` |
| GET | `/redfish/v1/Systems/system/Storage/{id}/Drive/{driveId}/` |
| GET | `/redfish/v1/Systems/system/EthernetInterfaces/` |
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
| **GET, POST** | `/redfish/v1/Managers/bmc/VirtualMedia/` |
| **GET** | `/redfish/v1/Managers/bmc/VirtualMedia/{id}/` |
| **POST** | `/redfish/v1/Managers/bmc/VirtualMedia/{id}/Actions/VirtualMedia.InsertMedia` |
| **POST** | `/redfish/v1/Managers/bmc/VirtualMedia/{id}/Actions/VirtualMedia.EjectMedia` |
| GET | `/redfish/v1/Managers/bmc/EthernetInterfaces/` |
| GET | `/redfish/v1/Managers/bmc/EthernetInterfaces/{id}/` |
| GET | `/redfish/v1/Managers/bmc/EthernetInterfaces/{id}/VLANs/` |
| GET | `/redfish/v1/Managers/bmc/LogServices/` |
| GET | `/redfish/v1/Managers/bmc/LogServices/RedfishLog/` |
| **POST** | `/redfish/v1/Managers/bmc/LogServices/RedfishLog/Actions/LogService.ClearLog` |
| GET | `/redfish/v1/Managers/bmc/LogServices/RedfishLog/Entries/{id}/` |
| GET | `/redfish/v1/Managers/bmc/ManagerDiagnosticData/` |
| GET | `/redfish/v1/Managers/bmc/ManagerDiagnosticData/GooglegRPCStatistics` |
| GET, PATCH | `/redfish/v1/Managers/bmc/NetworkProtocol/` |
| GET | `/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates/` |
| GET | `/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates/{id}/` |
| GET | `/redfish/v1/Managers/bmc/Truststore/Certificates/` |

### Event Service

| Method | Path |
|---|---|
| GET | `/redfish/v1/EventService/` |
| GET | `/redfish/v1/EventService/Subscriptions/` |
| POST | `/redfish/v1/EventService/Subscriptions/` |
| GET | `/redfish/v1/EventService/Subscriptions/{id}/` |
| DELETE | `/redfish/v1/EventService/Subscriptions/{id}/` |
| POST | `/redfish/v1/EventService/Actions/EventService.SubmitTestEvent` |

### Update Service

| Method | Path |
|---|---|
| GET | `/redfish/v1/UpdateService/` |
| **POST** | `/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate` |
| GET | `/redfish/v1/UpdateService/FirmwareInventory/` |
| GET | `/redfish/v1/UpdateService/FirmwareInventory/{id}/` |

### その他のサービス

| Method | Path |
|---|---|
| GET | `/redfish/v1/TaskService/` |
| GET | `/redfish/v1/TaskService/Tasks/` |
| GET | `/redfish/v1/TelemetryService/` |
| GET | `/redfish/v1/TelemetryService/MetricReportDefinitions/` |
| GET | `/redfish/v1/TelemetryService/MetricReports/` |
| GET | `/redfish/v1/TelemetryService/Triggers/` |
| GET | `/redfish/v1/CertificateService/` |
| GET | `/redfish/v1/CertificateService/CertificateLocations/` |
| GET | `/redfish/v1/JsonSchemas/` |
| GET | `/redfish/v1/JsonSchemas/{id}/` |
| GET | `/redfish/v1/Registries/` |
| GET | `/redfish/v1/Registries/{id}/` |
| GET | `/redfish/v1/Cables/` |
| GET | `/redfish/v1/Cables/{id}/` |
| GET | `/redfish/v1/AggregationService/` |
| GET | `/redfish/v1/AggregationService/AggregationSources` |
| GET | `/redfish/v1/AggregationService/AggregationSources/{id}` |

---

## 使用例

### セッション作成

```bash
curl -s -X POST http://localhost:8008/redfish/v1/SessionService/Sessions/ \
  -H "Content-Type: application/json" \
  -d '{"UserName": "admin", "Password": "password"}' \
  -D -
```

レスポンスヘッダの `X-Auth-Token` を以後のリクエストに使用できます。

### Boot デバイスの変更

```bash
curl -s -X PATCH http://localhost:8008/redfish/v1/Systems/system \
  -H "Content-Type: application/json" \
  -d '{
    "Boot": {
      "BootSourceOverrideTarget": "Pxe",
      "BootSourceOverrideEnabled": "Once"
    }
  }'
```

### ユーザーアカウントの作成

```bash
curl -s -X POST http://localhost:8008/redfish/v1/AccountService/Accounts/ \
  -H "Content-Type: application/json" \
  -d '{
    "UserName": "newuser",
    "Password": "newpassword",
    "RoleId": "ReadOnly"
  }'
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
# 強制電源断
curl -s -X POST http://localhost:8008/redfish/v1/Systems/system/Actions/ComputerSystem.Reset \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "ForceOff"}'

# 電源投入
curl -s -X POST http://localhost:8008/redfish/v1/Systems/system/Actions/ComputerSystem.Reset \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "On"}'
```

#### BMC リセット

`GracefulRestart` または `ForceRestart` を指定します。

```bash
curl -s -X POST http://localhost:8008/redfish/v1/Managers/bmc/Actions/Manager.Reset \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "GracefulRestart"}'
```

#### シャーシリセット

`On` / `ForceOff` / `PowerCycle` を指定します。

```bash
curl -s -X POST http://localhost:8008/redfish/v1/Chassis/chassis1/Actions/Chassis.Reset \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "PowerCycle"}'
```

成功時はいずれも `204 No Content` が返ります。

### BMC 日時設定

`DateTime`（ISO 8601 形式）と `DateTimeLocalOffset`（`+HH:MM` / `-HH:MM` 形式）を個別または同時に変更できます。

```bash
# 日時とタイムゾーンオフセットを同時に変更
curl -s -X PATCH http://localhost:8008/redfish/v1/Managers/bmc/ \
  -H "Content-Type: application/json" \
  -d '{
    "DateTime": "2025-01-15T09:00:00+09:00",
    "DateTimeLocalOffset": "+09:00"
  }'

# DateTime のみ変更（DateTimeLocalOffset は現在値を維持）
curl -s -X PATCH http://localhost:8008/redfish/v1/Managers/bmc/ \
  -H "Content-Type: application/json" \
  -d '{"DateTime": "2025-06-01T00:00:00Z"}'
```

PATCH 後は指定した値が GET のレスポンスに反映されます。  
不正なフォーマットを指定した場合は `400 Bad Request` が返ります。

| フィールド | 形式例 | バリデーション |
|---|---|---|
| `DateTime` | `2025-01-15T09:00:00+09:00` | ISO 8601 準拠 |
| `DateTimeLocalOffset` | `+09:00` / `-05:00` | `+HH:MM` または `-HH:MM` |

### ISO イメージのリモートマウント（VirtualMedia）

BMC の VirtualMedia 機能を使って、HTTP/HTTPS で公開した ISO イメージをリモートマウントできます。  
OS の再インストールや LiveCD 起動に使用します。

初期スロット: `CD`（CD/DVD）と `USB`（USB）の 2 つが登録されています。

#### ISO をマウントする

```bash
curl -s -X POST http://localhost:8008/redfish/v1/Managers/bmc/VirtualMedia/CD/Actions/VirtualMedia.InsertMedia \
  -H "Content-Type: application/json" \
  -d '{
    "Image": "http://192.168.1.10/iso/ubuntu-24.04-server.iso",
    "TransferProtocolType": "HTTP",
    "WriteProtected": true
  }'
```

| フィールド | 必須 | 説明 |
|---|---|---|
| `Image` | 必須 | ISO イメージの URI |
| `TransferProtocolType` | 任意 | `HTTP` / `HTTPS` / `TFTP` など（デフォルト: `HTTP`） |
| `WriteProtected` | 任意 | 書き込み保護（デフォルト: `true`） |

#### マウント状態を確認する

```bash
curl -s http://localhost:8008/redfish/v1/Managers/bmc/VirtualMedia/CD/
```

| フィールド | マウント中 | 未マウント |
|---|---|---|
| `Inserted` | `true` | `false` |
| `ConnectedVia` | `URI` | `NotConnected` |
| `ImageName` | ファイル名 | `""` |

#### ISO をアンマウントする

```bash
curl -s -X POST http://localhost:8008/redfish/v1/Managers/bmc/VirtualMedia/CD/Actions/VirtualMedia.EjectMedia \
  -H "Content-Type: application/json" -d '{}'
```

未マウント状態で EjectMedia を呼ぶと `400 Bad Request` が返ります。

#### スロットを追加する

```bash
curl -s -X POST http://localhost:8008/redfish/v1/Managers/bmc/VirtualMedia/ \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "Virtual DVD",
    "MediaTypes": ["DVD"]
  }'
```

成功時は `201 Created` と新規リソースが返ります。

### ファームウェア更新

`ImageURI`（必須）と `Targets`（対象ファームウェアの `@odata.id`）を指定します。  
`Targets` に指定したファームウェアのバージョンが `ImageURI` の末尾パスで更新されます。

```bash
curl -s -X POST http://localhost:8008/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate \
  -H "Content-Type: application/json" \
  -d '{
    "ImageURI": "http://downloads.example.com/firmware/2.5.0",
    "Targets": ["/redfish/v1/UpdateService/FirmwareInventory/BIOS/"]
  }'
```

成功時は `204 No Content` が返ります。

### ログクリア

各 LogService のログエントリを全件削除します。

```bash
# System EventLog
curl -s -X POST http://localhost:8008/redfish/v1/Systems/system/LogServices/EventLog/Actions/LogService.ClearLog \
  -H "Content-Type: application/json" -d '{}'

# System SEL
curl -s -X POST http://localhost:8008/redfish/v1/Systems/system/LogServices/SEL/Actions/LogService.ClearLog \
  -H "Content-Type: application/json" -d '{}'

# BMC RedfishLog
curl -s -X POST http://localhost:8008/redfish/v1/Managers/bmc/LogServices/RedfishLog/Actions/LogService.ClearLog \
  -H "Content-Type: application/json" -d '{}'
```

成功時はいずれも `204 No Content` が返ります。

### Secure Boot

```bash
# 現在の状態を確認
curl -s http://localhost:8008/redfish/v1/Systems/system/SecureBoot/

# 有効化
curl -s -X PATCH http://localhost:8008/redfish/v1/Systems/system/SecureBoot/ \
  -H "Content-Type: application/json" \
  -d '{"SecureBootEnable": true}'

# 無効化
curl -s -X PATCH http://localhost:8008/redfish/v1/Systems/system/SecureBoot/ \
  -H "Content-Type: application/json" \
  -d '{"SecureBootEnable": false}'
```

### BIOS 設定変更

`Attributes` オブジェクトで変更したいキーのみ指定します（部分更新）。

```bash
# 現在の設定を確認
curl -s http://localhost:8008/redfish/v1/Systems/system/Bios/

# BootMode を Legacy に変更
curl -s -X PATCH http://localhost:8008/redfish/v1/Systems/system/Bios/ \
  -H "Content-Type: application/json" \
  -d '{
    "Attributes": {
      "BootMode": "Legacy",
      "QuietBoot": false
    }
  }'
```

初期の Attributes:

| キー | デフォルト値 |
|---|---|
| `BootMode` | `"Uefi"` |
| `NicBoot1` | `"NetworkBoot"` |
| `NicBoot2` | `"Disabled"` |
| `QuietBoot` | `true` |
| `SriovGlobalEnable` | `"Disabled"` |

### ネットワーク設定変更

`HTTP` / `HTTPS` / `SSH` / `IPMI` / `NTP` のいずれかを指定して部分更新します。

```bash
# 現在の設定を確認
curl -s http://localhost:8008/redfish/v1/Managers/bmc/NetworkProtocol/

# SSH ポートを変更
curl -s -X PATCH http://localhost:8008/redfish/v1/Managers/bmc/NetworkProtocol/ \
  -H "Content-Type: application/json" \
  -d '{"SSH": {"Port": 2222}}'

# NTP サーバーを変更
curl -s -X PATCH http://localhost:8008/redfish/v1/Managers/bmc/NetworkProtocol/ \
  -H "Content-Type: application/json" \
  -d '{"NTP": {"NTPServers": ["ntp1.example.com", "ntp2.example.com"]}}'

# HTTP を無効化
curl -s -X PATCH http://localhost:8008/redfish/v1/Managers/bmc/NetworkProtocol/ \
  -H "Content-Type: application/json" \
  -d '{"HTTP": {"ProtocolEnabled": false}}'
```

### Webhook アラート通知

サブスクリプションを登録すると、イベント発生時に指定した URL へ HTTP POST が送信されます。

#### 1. 受け取り先 URL を登録する

```bash
curl -s -X POST http://localhost:8008/redfish/v1/EventService/Subscriptions/ \
  -H "Content-Type: application/json" \
  -d '{
    "Destination": "http://your-server/webhook",
    "Context": "my-context",
    "EventTypes": ["Alert"]
  }'
```

`EventTypes` を省略すると全種類のイベントを受信します。複数のサブスクリプションを登録することもできます。

#### 2. テストイベントを送信する

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://localhost:8008/redfish/v1/EventService/Actions/EventService.SubmitTestEvent \
  -H "Content-Type: application/json" \
  -d '{
    "EventType": "Alert",
    "Severity": "Critical",
    "Message": "CPU temperature exceeded critical threshold.",
    "MessageId": "ThermalEvents.1.0.TemperatureAboveUpperCriticalThreshold"
  }'
```

`204` が返れば成功です。登録済みのサブスクリプションに対してバックグラウンドで POST が送信されます。

リクエストボディのフィールドはすべて省略可能です。

| フィールド | デフォルト値 |
|---|---|
| `EventType` | `Alert` |
| `Severity` | `OK` |
| `Message` | `This is a test event.` |
| `MessageId` | `Base.1.0.GeneralError` |
| `MessageArgs` | `[]` |
| `Context` | `""` |
| `OriginOfCondition` | `/redfish/v1/` |

#### 3. サブスクリプション一覧・削除

```bash
# 一覧
curl -s http://localhost:8008/redfish/v1/EventService/Subscriptions/ | python3 -m json.tool

# 削除
curl -s -X DELETE http://localhost:8008/redfish/v1/EventService/Subscriptions/{id}/
```

#### Webhook の POST ボディ例

```json
{
  "@odata.type": "#Event.v1_7_0.Event",
  "Id": "a1b2c3d4",
  "Name": "Test Event",
  "Context": "my-context",
  "Events": [
    {
      "EventType": "Alert",
      "EventId": "a1b2c3d4",
      "EventTimestamp": "2026-06-05T06:19:16+00:00",
      "Severity": "Critical",
      "Message": "CPU temperature exceeded critical threshold.",
      "MessageId": "ThermalEvents.1.0.TemperatureAboveUpperCriticalThreshold",
      "MessageArgs": [],
      "OriginOfCondition": { "@odata.id": "/redfish/v1/" }
    }
  ]
}
```

---

## 初期シードデータ

起動時に以下のデータが自動投入されます。

### アカウント

| ユーザー名 | パスワード | ロール |
|---|---|---|
| admin | password | Administrator |
| operator1 | password | Operator |
| readonly1 | password | ReadOnly |

### ハードウェア構成（シミュレート対象）

- **System:** Dell PowerEdge R750
- **CPU:** Intel Xeon Gold 6338 × 2
- **Memory:** 32GB RDIMM × 4 (合計 128GB)
- **Storage:** 480GB SSD × 2 (Storage0/Drive0, Drive1)
- **Manager (BMC):** iDRAC9, FW: 2.71.71.71-711
- **Chassis:** 1U RackMount (chassis1)
- **Firmware:** BMC / BIOS / ME / CPLD
- **温度センサー:** CPU1/CPU2/Inlet/Outlet
- **ファン:** Fan1〜Fan6
- **電源:** PSU1 / PSU2 (750W)

---

## プロジェクト構成

```
redfish-emu/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # 設定 (DB_PATH など)
│   ├── database.py          # SQLite 初期化・マイグレーション・シードデータ
│   ├── helpers.py           # レスポンス共通関数
│   ├── event_dispatcher.py  # Webhook 配信ロジック
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
