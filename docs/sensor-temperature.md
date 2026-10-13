# 温度センサーの調査(AST2700 / QEMU)

状態: **選択肢 A で解決。温度を Redfish から取得でき、`qom-set` で動的に変更できる(検証済み)。**

## 1. 目的

ファン回転数・温度をリアルタイムに取得できるようにする。最初に温度から着手した。

## 2. 現状の確認結果

Redfish `Chassis/AST2700_EVB/Sensors` に 12 個のセンサーがある。

| センサー | 値 | 動くか |
|---|---|---|
| `voltage_ADC0_12V` / `ADC8_12V` | 約 11〜15 V | 動く(QEMU の ADC モデルが生成する値) |
| `voltage_Battery` | 3.528 V | 固定 |
| `fantach_Fan_0〜3` | 0 RPM | 動かない |
| `fanpwm_Pwm_0〜3` | 100% | 固定 |
| `temperature_Ambient_Temp` | 0.0 ℃(`Health: Critical`) | 動かない |

## 3. 温度センサーの経路

```
QEMU tmp105 (i2c bus 0, 0x4d) --I2C--> Linux lm75a (hwmon12) --> hwmontempsensor --> D-Bus Ambient_Temp --> Redfish
```

- QEMU の `ast2700-evb` は、`aspeed.i2c.bus.0` のアドレス 0x4d に `tmp105` を最初から接続している
  (`hw/arm/aspeed_ast27x0_evb.c`、`ast2700_evb_i2c_init`)。**デバイスを足す必要は無い。**
- QEMU 側のデバイスは QOM パス `/machine/unattached/device[51]`(`tmp105`)。
  `temperature` プロパティ(ミリ℃)は `qom-set` で変更でき、`qom-get` で値が保持されていることを確認した。
- Linux 側は `0-004d` に `lm75a` がバインドされ、`hwmon12/temp1_input` が温度になる。

## 4. 試したこと

| 試行 | 結果 |
|---|---|
| `-device tmp105,bus=aspeed.i2c.bus.0,address=0x4d` を `entrypoint.sh` に追加 | 同じアドレスに 2 台目ができるだけで、効果なし。**元に戻した** |
| `device_add` でホットプラグ | `Bus 'aspeed.i2c.bus.0' does not support hotplugging` で失敗 |
| `qom-set` で既存の tmp105 に 31500 / 45000 を設定 | QEMU 側は保持されるが、BMC の `temp1_input` は 0 のまま |
| BMC から `i2cget` / `i2ctransfer` で直接アクセス | アドレス 0x4d は ACK する(0x30 は失敗)が、読み出しは常に 0。設定レジスタへの書き込みも反映されない |

## 5. 原因の切り分け

QEMU のトレース(`trace-event aspeed_i2c* on`、`tmp105_* on`)で、次を確認した。

- BMC は温度レジスタ(ポインタ 0x00)を指定して読むが、QEMU の tmp105 には **ポインタ 0x1f** が届いている
  (`aspeed_i2c_bus_send DMA send 0/0 0x1f`、`tmp105_read ... addr: 0x1f`)。
- 0x1f は `& 3` で 3 番(`T_HIGH`)になり、既定値 0x5000 の `0x50 0x00` が返っている。
  ドライバが受け取る側のバッファには正しい値が入らず、0 になる。
- コマンドは `start|rxdma|rx|last|stop` で、QEMU は **DMA 経路**として処理している。
  一方 BMC のカーネルログは `mode [1]`(= BUFF モード)と表示している。

つまり、**この QEMU(11.1.2)の AST2700 I2C モデルと、SDK のカーネルドライバ(`i2c-ast2600.c`、BUFF モード)の
間で、転送データの受け渡しが合っていない**。tmp105 のモデル自体は正しく、設定の問題ではない。
ドライバの転送モードは dtb の `aspeed,transfer-mode`(`dma` / `byte` / 既定 `buffer`)で選べるが、
AST2700 では `byte` が使えず `dma` に切り替わる。

この問題が QEMU 側かドライバ側かは未特定。

## 6. 解決: dtb で I2C の転送モードを DMA に指定(選択肢 A)

`i2c-bus@100`(`/soc@14000000/bus@14c0f000/i2c-bus@100`、Linux の `i2c-0`)に
`aspeed,transfer-mode = "dma"` を追加した。ドライバのログが `mode [1]`(BUFF)から `mode [2]`(DMA)に変わり、
`hwmon12/temp1_input` が QEMU 側の値を返すようになった。

実装: `simulator/OpenBmc/patch_gpio_names.py`(GPIO 名のパッチと同じ dtb に追加、FIT のハッシュも再計算)。
環境変数 `I2C_TRANSFER_MODE` で上書きでき、空文字にするとこの変更をしない(ビルド時のみ)。

### 検証結果
| 手順 | 結果 |
|---|---|
| `set_temp.sh 31.5` | BMC の `temp1_input` = 31500、Redfish `Reading` = 31.5、`Health: OK` |
| `set_temp.sh 47.25` | Redfish `Reading` = 47.0(tmp105 の分解能による丸め)、`Health: Critical`(閾値超過) |

BMC の起動直後から、再起動なしで値が追従する(反映まで数秒)。

### 温度の設定方法
```sh
docker exec ast2700-obmc set_temp.sh 42.5
```
`set_temp.sh`(`simulator/OpenBmc/set_temp.sh`)は QMP で QEMU の `tmp105` の `temperature` を設定する。
無名デバイスの QOM パス(今は `/machine/unattached/device[51]`)は QEMU 依存のため、型 `tmp105` で探している。

## 7. 未対応

- **ファン回転数**: QEMU に回転を模擬するモデルが無く、`aspeed_tach` は 0 のまま。I2C の問題とは別。hwmon ファイルの差し替え(C')で動かせることを確認済み([sensor-fan.md](sensor-fan.md))。
- **他の I2C バス**: DMA 指定は i2c0 のみ。他のバスのデバイスは QEMU 側にも無いため不要。

## 8. 温度の自動更新(実装済み)

`post_boot.sh` が `temp_sim.sh` をバックグラウンドで起動し、`TEMP_INTERVAL`(既定 5 秒)ごとに QEMU の tmp105 へ温度を書き込む。
モードは `/run/temp_mode` で決まり、実行中に `temp_ctl.sh` で切り替えられる。

```
rocky-server --docker stats--> power-bridge GET /stats --> temp_sim.sh --set_temp.sh(QMP)--> tmp105 --I2C--> BMC --> Redfish
```

| モード | コマンド | 温度 |
|---|---|---|
| auto | `temp_ctl.sh auto` | `TEMP_BASE + CPU使用率 × TEMP_PER_CPU`(1 コア = 100%)。前回値との移動平均で急変を抑える。停止中は `TEMP_BASE` |
| fixed | `temp_ctl.sh fixed 45` | 指定値 |
| warn | `temp_ctl.sh warn` | `TEMP_WARN + 1` = 39℃(UpperCaution 超え、Redfish `Health: Warning`) |
| over | `temp_ctl.sh over` | `TEMP_CRIT + TEMP_OVER_MARGIN` = 43℃(UpperCritical 超え、`Health: Critical`) |
| ramp | `temp_ctl.sh ramp 60 120` | 今の温度から 60℃ へ 120 秒かけて直線的に上昇し、以降は維持 |
| status | `temp_ctl.sh status` | 現在のモードと温度を表示 |

```sh
docker exec ast2700-obmc temp_ctl.sh over      # わざと閾値超過
docker exec ast2700-obmc temp_ctl.sh auto      # 負荷連動に戻す
docker exec rocky-server sh -c 'while :; do :; done' &   # 負荷をかける (auto で温度が上がる)
```

### 設定(`docker-compose.sim.yml` の `ast2700-obmc.environment`)
| 変数 | 既定 | 説明 |
|---|---|---|
| `TEMP_MODE` | `auto` | 起動時のモード(`auto` / `warn` / `over` / `fixed 45`) |
| `TEMP_BASE` | `28` | 無負荷時の温度 ℃ |
| `TEMP_PER_CPU` | `0.1` | CPU 1 コア使用あたりの上昇 ℃(0.1 なら 1 コアで +10℃) |
| `TEMP_MAX` | `90` | 上限 ℃ |
| `TEMP_WARN` / `TEMP_CRIT` | `38` / `40` | BMC の UpperCaution / UpperCritical に合わせた値(BMC 側の閾値は変えていない) |
| `TEMP_OVER_MARGIN` | `3` | `over` で `TEMP_CRIT` に足す値 |
| `TEMP_INTERVAL` | `5` | 更新間隔(秒) |

### 検証結果
| 操作 | Redfish `Ambient_Temp` |
|---|---|
| 無負荷(auto) | 28.0 / OK |
| `rocky-server` で 2 コア負荷(CPU 192.9%) | 46.0 / Critical |
| `fixed 33` | 33.0 / OK |
| `warn` | 39.0 / Warning |
| `over` | 43.0 / Critical |
| `ramp 60 60`(30 秒時点) | 約 44 / Critical(上昇中) |
| 負荷停止後に `auto` | 約 40 秒で 28.0 / OK に復帰 |

### 注意
- 温度の閾値は BMC 側の値(Caution 38 / Critical 40)。ここの `TEMP_WARN` / `TEMP_CRIT` は `warn` / `over` の目標値の計算にだけ使い、BMC の閾値は変更しない。
- tmp105 の分解能で、Redfish の値は 0.5℃ 刻みに丸められる。
- 反映は更新間隔 + hwmon のポーリング分(数秒〜十数秒)遅れる。
- 電源連携の QMP 呼び出しと衝突しないよう、`/run/qmp.lock` を共有している。

## 9. 変更履歴

- `simulator/OpenBmc/patch_gpio_names.py`: i2c0 に `aspeed,transfer-mode` を追加。
- `simulator/OpenBmc/set_temp.sh`: 新規。QOM パスをキャッシュし、`/run/qmp.lock` で排他。
- `simulator/OpenBmc/temp_sim.sh` / `temp_ctl.sh`: 新規。自動更新とモード切替。
- `simulator/OpenBmc/post_boot.sh`: `temp_sim.sh` を起動。
- `simulator/PowerBridge/bridge.py`: `GET /stats`(CPU 使用率)を追加。
- `docker-compose.sim.yml`: `TEMP_*` 環境変数を追加。
- `simulator/OpenBmc/Dockerfile`: `set_temp.sh` を `/usr/local/bin/` にコピー。
- 試行用の `-device tmp105` は `entrypoint.sh` に残していない。
