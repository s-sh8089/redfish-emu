# BMC の電源操作と rocky-server の連携

AST2700 BMC(QEMU 上)への電源操作(Redfish / IPMI)を、`rocky-server` コンテナの起動・停止に結び付ける仕組み。
イメージ側の変更は [image-changes.md](image-changes.md) を参照。

## 1. 全体像

```
 Redfish / IPMI
      |
      v
 [BMC: bmcweb / ipmid] -> D-Bus State.Host0 / Chassis0 -> [x86-power-control]
                                                              |  ログ出力 / GPIO 出力・入力
        +-----------------------------------------------------+
        |                                          ^
        v (ssh で journalctl -f)                   | (QMP: qom-set で GPIO 入力を操作)
 [ast2700-obmc コンテナ: power_sync.sh] ----> [power-bridge] ---- docker.sock ----> [rocky-server]
        BMC 要求 -> /power/{on,off,shutdown,reset}
        コンテナ状態 (/power/status) -> PS_PWROK などの GPIO
```

BMC にはホストが存在しないため、`x86-power-control` が見る GPIO 入力(電源良好信号)を
QEMU の QMP から操作して「ホストが動いている / 止まっている」を作り出している。

## 2. 構成要素

| 要素 | ファイル | 役割 |
|---|---|---|
| `rocky-server` | `simulator/RockyLinuxServer/Dockerfile` | 監視対象の Rocky Linux 9(sshd)。コンテナの稼働 = 電源オン |
| `power-bridge` | `simulator/PowerBridge/bridge.py` | `rocky-server` 1 つだけを docker API(unix socket)で start / stop / kill / restart する HTTP API |
| 電源同期 | `simulator/OpenBmc/power_sync.sh` | BMC 要求の検知とコンテナ状態の GPIO 反映 |
| 起動処理 | `simulator/OpenBmc/post_boot.sh` | `power_sync.sh` を起動 |
| QMP | `simulator/OpenBmc/entrypoint.sh` | `-qmp unix:/run/qemu-qmp.sock,server,nowait` |
| dtb パッチ | `simulator/OpenBmc/patch_gpio_names.py` | `power-control` が使う GPIO 名を dtb に追加 |

## 3. BMC 要求 → コンテナ操作

`power_sync.sh` は、BMC 上で `journalctl -f -u xyz.openbmc_project.Chassis.Control.Power@0.service`
を SSH 経由で読み、`power-control` の次のログ行で動作する。

| ログ(部分一致) | 発生する要求 | power-bridge | docker |
|---|---|---|---|
| `Moving to "Wait for Power OK" state` | 電源オン、電源サイクル復帰 | `POST /power/on` | `start` |
| `graceful power-off request` | GracefulShutdown | `POST /power/shutdown` | `stop`(SIGTERM、10 秒) |
| `graceful power-cycle request` | GracefulRestart | `POST /power/shutdown` | `stop` |
| `power-off request` | ForceOff | `POST /power/off` | `kill` |
| `power-cycle request` | PowerCycle | `POST /power/off` | `kill` |
| `reset request` | ForceRestart | `POST /power/reset` | `kill` + `start` |

サイクル系は、停止後に `power-control` 自身が一定時間待って電源オン動作へ進み、
`Wait for Power OK` に入る。そこで `on` が呼ばれてコンテナが再起動する。

## 4. コンテナ状態 → BMC(GPIO)

`/power/status` を 2 秒間隔(`POWER_POLL_SEC`)で取得し、QEMU の GPIO 入力を操作する。

| GPIO 名 | gpiochip1 | QOM プロパティ | 稼働時 | 停止時 |
|---|---|---|---|---|
| `SIO_POWER_GOOD` | 74 | `gpioJ2` | 1 | 0 |
| `PS_PWROK` | 65 | `gpioI1` | 1 | 0 |
| `SIO_S5` | 75 | `gpioJ3` | 1(非アサート) | 0(アサート) |

- 対応規則: オフセット `n` は、バンク `A…Z, AA` の `n / 8` 番目 + `n % 8` ビット。
- 3 本は 1 つの QMP 接続でまとめて設定する(`SIO_POWER_GOOD` を 1 秒以内に上げないと
  `power-control` が `VR failure` として Off に戻すため)。
- 停止は 2 回連続で確認してから反映する(reset の `kill` → `start` の瞬断で落とさないため)。
- BMC 要求の処理直後は、ポーリングを待たず即時に反映する(後述の競合対策)。
- `docker stop/start rocky-server` など、BMC 以外からの操作にも追従する。
- 起動時は、BMC の電源制御サービスを開始する**前**にコンテナの現状を GPIO に反映する
  (`power-control` は起動時の `PowerOk` で初期状態を決めるため)。

## 5. 動作確認結果

| 操作 | 結果 |
|---|---|
| Redfish `GracefulShutdown` | コンテナ停止、`PowerState: Off` |
| Redfish `On` | コンテナ起動、`PowerState: On` |
| Redfish `ForceOff` | コンテナ強制停止、`Off` |
| Redfish `ForceRestart` | コンテナ再起動(起動時刻が変わる)、`On` のまま |
| Redfish `GracefulRestart` | 停止 → 起動、`Off` → `On` |
| Redfish `PowerCycle` | 停止 → 約 10 秒後に起動、`Off` → `On` |
| IPMI `chassis power off` / `on` / `status` | コンテナ停止・起動、`status` が追従 |
| `docker stop` / `docker start`(外部) | `PowerState` が `Off` / `On` に追従 |
| 起動時 | `rocky-server` 稼働中なら BMC は `On` で立ち上がる |

## 6. 既知の制限

- **直前の電源オフと同時の電源オン**: `ForceOff` の直後(待ち時間なし)に `On` を送ると、
  `power-control` が停止処理中(`TransitionToOff`)で要求を無視し、`On` が失われる。
  数秒空ければ正常。BMC 側の仕様で、この連携では回避できない。
- **ホスト経由の IPMI(UDP 623)**: Mac のホストから `localhost:2623` 経由の接続は、
  RMCP+ セッションが確立できなかった。Docker Desktop の UDP 転送が原因と思われる。
  コンテナネットワーク内(`-H ast2700-obmc`)からは動作する。
- **永続化**: BMC 側の変更は起動のたびに再実行する。`systemctl enable` はしていない。
- **起動時間**: BMC の起動に数分かかる。その間は電源要求を受け付けない。
- **グレースフル停止**: `rocky-server` に ACPI の仕組みは無く、`docker stop`(SIGTERM)で代用している。
- **`guestfwd`**: ゲストの `10.0.2.100:8080` から `power-bridge` への経路は残っているが、
  現在の連携では使っていない(`power_sync.sh` がコンテナ側から直接 `power-bridge` を呼ぶ)。

## 7. 設定

| 環境変数 | 既定 | 説明 |
|---|---|---|
| `POWER_BRIDGE` | `power-bridge:8080` | `power-bridge` の宛先 |
| `POWER_POLL_SEC` | `2` | コンテナ状態の確認間隔(秒) |
| `BMC_PASSWORD` | `0penBmc` | BMC の root パスワード(SSH) |
| `TARGET_CONTAINER`(`power-bridge`) | `rocky-server` | 操作対象のコンテナ名 |
| `STOP_TIMEOUT`(`power-bridge`) | `10` | `docker stop` の待ち時間(秒) |
