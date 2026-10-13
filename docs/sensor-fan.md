# ファン回転数センサーの調査(C' 案の確認)

状態: **C'(hwmon ファイルの差し替え)を確認し、コンテナへ組み込み済み(温度に連動、故障の再現も可能)。**

## 1. 背景

QEMU の `aspeed_tach` は回転を模擬しないため、`fantach_Fan_0〜3` が常に 0 RPM / `Critical` になる
([sensor-temperature.md](sensor-temperature.md))。
BMC 内に D-Bus サービスを作る案(C)の代わりに、`fansensor` が読む hwmon ファイルを差し替える案(C')を確認した。

## 2. 仕組み

```
/sys/class/hwmon/hwmon0/fanN_input --read--> fansensor (dbus-sensors) --> D-Bus fan_tach/Fan_(N-1) --> bmcweb --> Redfish
        ^ bind mount で通常ファイルに差し替え
/run/fakefan/fanN_input  (値を書くだけ)
```

- 対応: エンティティ設定 `ast2700-evb.json` の `AspeedFan`(`Tachs: [n]`)により、`Fan_n` は `fan{n+1}_input` を読む。
  (`Fan_0` ← `fan1_input`、`Fan_1` ← `fan2_input`、…)
- `fansensor` は起動時に `fanN_input` を開いたままにして読み直す。**bind mount の後に `fansensor` を再起動する必要がある**
  (すでに開いているファイルは差し替わらない)。
- D-Bus・Redfish は標準のまま。閾値・`Health` の判定も本物の `fansensor` がそのまま行う。

## 3. 確認手順と結果(BMC 内、手動)

```sh
mkdir -p /run/fakefan; H=/sys/class/hwmon/hwmon0
echo 3000 > /run/fakefan/fan1_input; echo 4500 > /run/fakefan/fan2_input
for n in 1 2; do mount --bind /run/fakefan/fan${n}_input $H/fan${n}_input; done
systemctl restart xyz.openbmc_project.fansensor.service
```

| 操作 | Redfish `fantach_Fan_N` |
|---|---|
| 差し替え後(fan1=3000, fan2=4500) | Fan 0 = 3000 / OK、Fan 1 = 4500 / OK、Fan 2 = 0 / Critical(未差し替え) |
| `echo 1200 > fan1_input`(再起動なし) | Fan 0 = 1200 / OK(約 8 秒以内に追従) |
| `echo 300 > fan1_input` | Fan 0 = 300 / **Critical**(LowerCritical 360 を下回った) |

- sysfs のファイルに `mount --bind` が効く。
- 値の変更は `fansensor` の再起動なしで追従する。
- 低回転の閾値(LowerCaution 480 / LowerCritical 360)による警告・異常の再現ができる。

## 4. コンテナへの組み込み(実装済み)

`post_boot.sh` が `fan_sim.sh` を起動する。BMC への SSH が上がると、1 本の SSH 接続に次を流し込む。

1. `/run/fakefan/fanN_input` を作り、`/sys/class/hwmon/hwmon0/fanN_input` へ `mount --bind`(マウント済みならスキップ)。
2. `fansensor` を再起動(最初の 1 回だけ)。
3. `FAN_INTERVAL`(既定 5 秒)ごとに、計算した回転数を各ファイルへ書き込む。

接続が切れたら再接続し、BMC を再起動した場合も自動でやり直す。

### 回転数の決まり方
- `auto`: `/run/temp_cur`(`temp_sim.sh` が更新する温度)に比例。`FAN_T_MIN`(30℃)以下で `FAN_RPM_MIN`(2000)、
  `FAN_T_MAX`(45℃)以上で `FAN_RPM_MAX`(12000)。ファンごとに少しずつ差を付け、±2% のゆらぎを加える。
- `fixed <rpm>`: 全ファンを固定。
- 個別指定(`fail` / `slow` / `set`)はモードより優先される。

### 操作
```sh
docker exec ast2700-obmc fan_ctl.sh fail 1       # ファン1停止 (0 RPM → Critical)
docker exec ast2700-obmc fan_ctl.sh slow 2       # ファン2低回転 (420 RPM → Warning)
docker exec ast2700-obmc fan_ctl.sh set 0 800    # ファン0を 800 RPM に
docker exec ast2700-obmc fan_ctl.sh fixed 5000   # 全ファン固定
docker exec ast2700-obmc fan_ctl.sh heal         # 故障・個別指定を解除
docker exec ast2700-obmc fan_ctl.sh auto         # 温度連動に戻す
docker exec ast2700-obmc fan_ctl.sh status
```
`all` を指定すると全ファンに適用する(`fail all`、`slow all`、`heal all`)。

### 設定(`docker-compose.sim.yml` の `ast2700-obmc.environment`)
| 変数 | 既定 | 説明 |
|---|---|---|
| `FAN_MODE` | `auto` | 起動時のモード(`auto` / `fixed 5000`) |
| `FAN_RPM_MIN` / `FAN_RPM_MAX` | `2000` / `12000` | 温度範囲の下端・上端での回転数 |
| `FAN_T_MIN` / `FAN_T_MAX` | `30` / `45` | 回転数を変化させる温度範囲 ℃ |
| `FAN_INTERVAL` | `5` | 更新間隔(秒) |
| `FAN_COUNT` | `4` | ファン数 |
| `FAN_SLOW_RPM` | `420` | `slow` の回転数(LowerCaution 480 未満、LowerCritical 360 以上) |

### 検証結果(組み込み後、BMC 起動直後から自動)
| 操作 | Redfish `fantach_Fan_N` |
|---|---|
| 起動直後(温度 28℃) | 約 2000 RPM / OK |
| `temp_ctl.sh over`(43℃) | 約 10600〜11300 RPM / OK |
| `fan_ctl.sh fail 1` | Fan 1 = 0 / **Critical**、他は継続 |
| `fan_ctl.sh slow 2` | Fan 2 = 420 / **Warning** |
| `fan_ctl.sh heal` + `temp_ctl.sh auto` | 全ファン 約 2000 RPM / OK に復帰 |
| `fan_ctl.sh fixed 5000` | 全ファン 5000 / OK |

## 5. 注意・制約

- 回転数の値は模擬。実機の温度に応じた制御ループ(`phosphor-pid-control`)は動いていない。回転数は温度から直接計算している。
- 温度シミュレーション(`temp_sim.sh`)が動いていないと、温度は 28℃ 固定扱いになる。
- PWM センサー(`fanpwm_Pwm_N`)は、回転数に比例した値を `pwm1` の差し替えで設定している(第 7 節)。
- `ThermalSubsystem/Fans` は第 7 節の `fanobj` で対応済み。
- 反映は更新間隔 + `fansensor` のポーリング分(数秒〜十数秒)遅れる。

## 6. Redfish `ThermalSubsystem/Fans`(Fan リソース)

標準構成では `Members: []` だった。bmcweb のソース(`redfish-core/lib/fan.hpp`、`fan_utils.hpp`)から、次が必要と分かった。

| bmcweb が探すもの | 標準構成 | 対応 |
|---|---|---|
| `chassis/cooled_by` の関連付け先で、`Inventory.Item.Fan` を持つオブジェクト | 無い(entity-manager は `Item.Fan` を作らない) | `fanobj` が作る |
| `fan/sensors` の関連付け先の `Sensor.Value`(Percent 単位) | 無い | `fanobj` が PWM センサーへの関連付けを作る |
| `Decorator.Asset` / `Decorator.LocationCode`(無いと内部エラー) | 無い | `fanobj` が模擬値を出す |
| `State.Decorator.OperationalStatus.Functional`(`Health` になる) | 無い | `fanobj` が出し、`fan_sim.sh` が回転数に応じて更新する |

BMC の Python には D-Bus ライブラリが無く、`busctl` はオブジェクトを公開できない。
そのため **Go 製の小さな D-Bus サービス `fanobj`**(`simulator/OpenBmc/fanobj/`)を作った。

- `Dockerfile` の `fanobj` ステージで、arm64 の静的バイナリとして Docker 内でクロスコンパイルする(Yocto は使わない)。
- `fan_sim.sh` が BMC に接続するたびに、`/tmp/fanobj` へ転送して起動する(起動済みならスキップ)。
- D-Bus サービス名は `xyz.openbmc_project.VirtualFan`、オブジェクトは
  `/xyz/openbmc_project/inventory/system/board/AST2700_EVB/Chassis_Fan_{0..3}`。
- センサー値そのものは標準の `fansensor` が出す。`fanobj` は在庫オブジェクトと関連付けを足すだけ。
- PWM と tach の 2 センサーを関連付けると、bmcweb が優先度なしの複数センサーとして `SpeedPercent` をスキップする。
  そのため PWM センサーのみ関連付けている(Redfish の `Fan` は `SpeedPercent` だけを持ち、RPM は `Sensors/fantach_Fan_N` で見る)。

## 7. PWM の連動

`SpeedPercent` の元になる PWM センサー(`fanpwm_Pwm_N`)も、回転数に比例させた。
`pwm-fan<N>` の hwmon を探して `pwm1`(0〜255)を `/run/fakefan/pwmN` で `bind mount` し、
`pwm = 回転数 / FAN_RPM_MAX × 255` を書き込む。

## 8. Fan リソースの検証結果

| 操作 | `Fans/Chassis_Fan_N` |
|---|---|
| `Fans` コレクション | 4 件(`Chassis_Fan_0〜3`) |
| 無負荷(約 2000 RPM) | `SpeedPercent` 約 16.5〜17.6%、`Health: OK` |
| `temp_ctl.sh over`(約 11000 RPM) | `SpeedPercent` 約 88〜93% |
| `fan_ctl.sh fail 1` | Fan 1 = 0%、**`Health: Critical`**(`ThermalSubsystem` は OK のまま) |
| `fan_ctl.sh slow 2`(420 RPM) | Fan 2 = 3.5%、`Health: OK`(`fantach` センサー側は Warning) |
| `fan_ctl.sh heal` | 全ファン復帰、`Health: OK` |

各 `Fan` には `Manufacturer`(`Simulated`)、`Model`、`PartNumber`、`SerialNumber`、`Location.PartLocation.ServiceLabel`(`FAN0` など)が模擬値で付く。
`Functional` を false にする基準は、回転数が `FAN_LOWER_CRIT`(既定 360 RPM)未満のとき。

## 9. 変更履歴

- `simulator/OpenBmc/fan_sim.sh`: 新規。
- `simulator/OpenBmc/fan_ctl.sh`: 新規。
- `simulator/OpenBmc/post_boot.sh`: `fan_sim.sh` を起動。
- `simulator/OpenBmc/fanobj/`(`main.go`、`go.mod`、`go.sum`): 新規。Fan 在庫の D-Bus サービス。
- `simulator/OpenBmc/fan_sim.sh`: `fanobj` の転送・起動、PWM の差し替え、`Functional` の更新を追加。
- `simulator/OpenBmc/Dockerfile`: 2 つのスクリプトをコピー。`fanobj` ステージ(Go のクロスコンパイル)を追加し、バイナリを `/opt/obmc/fanobj` に置く。
- `docker-compose.sim.yml`: `FAN_*` 環境変数を追加。
