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
| GET | `/redfish/v1/Systems/system/Bios/` |
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
| GET | `/redfish/v1/Systems/system/LogServices/EventLog/Entries/` |
| GET | `/redfish/v1/Systems/system/LogServices/EventLog/Entries/{id}/` |
| GET | `/redfish/v1/Systems/system/LogServices/SEL/` |
| GET | `/redfish/v1/Systems/system/LogServices/SEL/Entries/` |
| GET | `/redfish/v1/Systems/system/LogServices/SEL/Entries/{id}/` |

### Chassis

| Method | Path |
|---|---|
| GET | `/redfish/v1/Chassis/` |
| GET | `/redfish/v1/Chassis/{id}/` |
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
| GET | `/redfish/v1/Managers/bmc/` |
| GET | `/redfish/v1/Managers/bmc/EthernetInterfaces/` |
| GET | `/redfish/v1/Managers/bmc/EthernetInterfaces/{id}/` |
| GET | `/redfish/v1/Managers/bmc/EthernetInterfaces/{id}/VLANs/` |
| GET | `/redfish/v1/Managers/bmc/LogServices/` |
| GET | `/redfish/v1/Managers/bmc/LogServices/RedfishLog/` |
| GET | `/redfish/v1/Managers/bmc/LogServices/RedfishLog/Entries/{id}/` |
| GET | `/redfish/v1/Managers/bmc/ManagerDiagnosticData/` |
| GET | `/redfish/v1/Managers/bmc/ManagerDiagnosticData/GooglegRPCStatistics` |
| GET | `/redfish/v1/Managers/bmc/NetworkProtocol/` |
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

### Update Service

| Method | Path |
|---|---|
| GET | `/redfish/v1/UpdateService/` |
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

### イベントサブスクリプションの登録

```bash
curl -s -X POST http://localhost:8008/redfish/v1/EventService/Subscriptions/ \
  -H "Content-Type: application/json" \
  -d '{
    "Destination": "http://your-server/webhook",
    "Context": "my-context",
    "EventTypes": ["Alert", "StatusChange"]
  }'
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
│   ├── database.py          # SQLite 初期化・シードデータ
│   ├── helpers.py           # レスポンス共通関数
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
