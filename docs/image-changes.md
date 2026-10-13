# OpenBMC イメージに対する変更点

元のイメージは `ast2700-default-obmc.tar.gz`(Aspeed SDK `v11.03`、2026-07-24 ビルド、`ast2700-default`)。
このドキュメントは、そのイメージに対して **何を変更したか** と、**何を変更していないか** をまとめる。

## 1. 変更の全体像

| # | 区分 | 変更対象 | 内容 | 永続性 |
|---|---|---|---|---|
| 1 | イメージ(バイナリ) | `image-bmc` 内の FIT の dtb | `gpio-line-names` を追加 | ビルド時に焼き込み(永続) |
| 1b | イメージ(バイナリ) | 同じ dtb の `i2c-bus@100` | `aspeed,transfer-mode = "dma"` を追加(温度センサー用。[sensor-temperature.md](sensor-temperature.md)) | ビルド時に焼き込み(永続) |
| 2 | イメージ(取り出し) | tar.gz の内容 | `image-bmc` と `qemuboot.conf` のみ使用 | - |
| 3 | 実行時(BMC 内) | systemd サービス | `xyz.openbmc_project.Chassis.Control.Power@0` を起動 | 起動のたびに実行(永続しない) |
| 4 | 実行環境(QEMU 側) | ブートROM 他 | vbootrom 追加、QEMU 11.x 使用 | - |

ルートファイルシステム(ROFS/RWFS)、カーネル、U-Boot、TF-A、OP-TEE、initramfs、
`power-config-host0.json` は **一切変更していない**。

---

## 2. `image-bmc` の変更(dtb パッチ)

実装: `simulator/OpenBmc/patch_gpio_names.py`(Dockerfile の `extract` ステージで実行)

### 2.1 変更の理由
BMC に入っている `x86-power-control`(`/usr/bin/power-control`)は、`State.Host` / `State.Chassis` の
D-Bus サービスを提供するが、GPIO を **名前(`LineName`)でのみ** 検索する。
元の `ast2700-evb` の dtb には名前付き GPIO が 1 つも無く(1,252 行すべて `unnamed`)、
起動時に `Failed to find the PS_PWROK line` で失敗していた。
設定ファイルの差し替えでは回避できず(出力側の `POWER_OUT` などにも名前が必要)、
カーネルに `gpio-sim` / aggregator も無いため、dtb に名前を足す方法を採った。

### 2.2 変更内容
- 対象: `image-bmc` のフラッシュオフセット `0x420000`(`FLASH_KERNEL_OFFSET` = 4224 KiB)にある FIT イメージ。
- FIT 内の `fdt-ast2700-evb.dtb`(`flat_dt`)の `data` を差し替え。
  - dtb の `gpio@14c0b000`(`gpiochip1`、216 行)に `gpio-line-names` プロパティを追加。
- 同じ FIT 内の dtb の `hash` ノード(`sha256`)の `value` を再計算して更新。
- FIT のサイズ: 9,189,168 → 9,189,188 バイト(上限 `0xC00000` に収まる)。
- FIT は署名なし(sha256 ハッシュのみ)なので、U-Boot の検証は通る。

kernel / ramdisk の `data` とハッシュは変更していない。

### 2.3 追加した GPIO 名
`gpiochip1`(`14c0b000.gpio`)のオフセット 64〜75。

| オフセット | 名前 | `power-config-host0.json` 上の用途 |
|---|---|---|
| 64 | `POWER_BUTTON` | PowerButton(入力) |
| 65 | `PS_PWROK` | PowerOk(入力) |
| 66 | `POWER_OUT` | PowerOut(出力) |
| 67 | `RESET_BUTTON` | ResetButton(入力) |
| 68 | `RESET_OUT` | ResetOut(出力) |
| 69 | `ID_BUTTON` | IdButton(入力) |
| 70 | `NMI_BUTTON` | NMIButton(入力) |
| 71 | `NMI_OUT` | NMIOut(出力) |
| 72 | `POST_COMPLETE` | PostComplete(入力) |
| 73 | `SIO_ONCONTROL` | SioOnControl |
| 74 | `SIO_POWER_GOOD` | SioPowerGood |
| 75 | `SIO_S5` | SIOS5 |

名前は、イメージに元から入っている `/usr/share/x86-power-control/power-config-host0.json` の
`LineName` と一致させてある。**設定ファイル自体は変更していない。**

### 2.4 行番号の選定理由
最初に 0〜11 番を使ったが、これらのピンは SD コントローラ(`14080100.sdhci`)に pinmux で
取られており、`power-control` のイベント要求が `Invalid argument` で失敗した
(`pin C14 already requested by 14080100.sdhci`)。
そのため BMC 上で `gpiochip1` の 12〜195 番を `gpioget` で総当たりし、取得できた行の中から
連続する 64〜75 番を選んだ。取得できた行は次のとおり:

`32-48, 56-57, 64-95, 107-108, 110-111, 115-116, 118-119, 124-129, 135, 150-151, 186-189`

これは **QEMU のモデル上の結果**。実機の EVB では pinmux の状況が異なる可能性がある。

---

## 3. tar.gz から取り出すファイル

`ast2700-default-obmc.tar.gz`(約 530MB)は、展開すると次のようなファイル群を含む。
最終イメージに入れるのは次の 2 つだけ。

| ファイル | 用途 |
|---|---|
| `image-bmc`(128MB、dtb パッチ済み) | QEMU に `-drive if=mtd` で渡すフラッシュイメージ |
| `obmc-phosphor-image-ast2700-default.qemuboot.conf` | 参考用(QEMU の起動オプションの元情報) |

U-Boot、TF-A、OP-TEE、SSP、TSP などは `image-bmc` に内包されており、vbootrom が読み込むため、
個別ファイルを `-device loader` で渡す必要は無い。
`static.mtd`、`ecdsa384/`、`ecdsa384-lms/`、`.elf`、ライセンス情報などは使っていない。

---

## 4. 実行時の変更(BMC 内)

実装: `simulator/OpenBmc/post_boot.sh` → `simulator/OpenBmc/power_sync.sh`(コンテナ起動時にバックグラウンドで実行)

BMC の SSH が上がるのを待ち、次を実行する(電源連携の詳細は [power-integration.md](power-integration.md))。

```sh
systemctl start xyz.openbmc_project.Chassis.Control.Power@0.service
```

- イメージ側ではこのサービスは `disabled` のため、`systemctl enable` はしていない(起動のたびに開始する)。
- 結果として D-Bus に `xyz.openbmc_project.State.Host0` / `State.Chassis0` /
  `Chassis.Buttons0` / `Control.Host.NMI0` / `Control.Host.RestartCause0` などが現れる。
- Redfish の `Systems/system` に `PowerState`(現状は `Off`)と `ComputerSystem.Reset` が見える。

### 変更前後の比較
| 項目 | 元のイメージ | 変更後 |
|---|---|---|
| 名前付き GPIO | なし | 12 行(64〜75) |
| `State.Host0` / `State.Chassis0` | なし | あり |
| Redfish `Systems/system` の `PowerState` | なし | `Off` |
| Redfish `ComputerSystem.Reset` の実行 | `ResourceNotFound` | 動作する(`rocky-server` の起動・停止に連動) |

---

## 5. 実行環境側の変更(イメージ自体ではない)

| 項目 | 内容 |
|---|---|
| QEMU | Debian `forky` の `qemu-system-arm` 11.1.2。`ast2700-evb` は A2 として動く。Debian trixie の 10.0 は U-Boot の DRAM 初期化で停止した |
| vbootrom | `ast27x0_bootrom.bin` を QEMU 本体と同じタグ(`v11.1.2`)のソースから取得し `/usr/share/qemu/` に配置(Debian パッケージに含まれない) |
| 起動オプション | `-machine ast2700-evb -m 2G -drive file=image-bmc,if=mtd,format=raw -net nic,netdev=net0 -nographic`。ローダ指定は不要 |
| ネットワーク | ユーザーモード。ホスト転送: 22 / 443 / 80 / 623(UDP)。ゲスト→ブリッジ: `10.0.2.100:8080` を `guestfwd=...-cmd:nc <ブリッジ>` で転送 |
| QMP | `-qmp unix:/run/qemu-qmp.sock,server,nowait`。`power_sync.sh` が GPIO 入力(`PS_PWROK` など)の操作に使う |
| 追加パッケージ | `netcat-openbsd`、`openssh-client`、`sshpass`、`curl`、`util-linux`(`flock`)(`power_sync.sh` と `guestfwd` 用) |

---

## 6. 未検証・未実施の事項

- **`rocky-server` との連携**: 実装・検証済み([power-integration.md](power-integration.md))。
  既知の制限(電源オフ直後の同時電源オン、ホスト経由の IPMI など)も同文書にある。
- **永続化**: `systemctl enable` は行っていない。電源制御サービスは起動のたびに `power_sync.sh` が開始する。
  コンテナを作り直すと `image-bmc` はイメージ内の元の状態に戻る(`docker compose down` で変更は消える)。
- **実機への適用**: dtb パッチは QEMU 上での検証のみ。実機では GPIO の pinmux が異なるため、そのまま使えない。
- **Yocto の再ビルド**: 行っていない(最終手段として保留)。

## 7. 関連ファイル

| ファイル | 役割 |
|---|---|
| `simulator/OpenBmc/Dockerfile` | tar.gz の展開、dtb パッチ、QEMU・vbootrom の導入 |
| `simulator/OpenBmc/patch_gpio_names.py` | `image-bmc` の dtb へ `gpio-line-names` と i2c0 の転送モードを追加 |
| `simulator/OpenBmc/set_temp.sh` | 温度センサー(QEMU tmp105)の値を設定 |
| `simulator/OpenBmc/temp_sim.sh` / `temp_ctl.sh` | 温度の自動更新(rocky-server の CPU 連動)とモード切替 |
| `simulator/OpenBmc/fan_sim.sh` / `fan_ctl.sh` | ファン回転数の模擬(温度連動、故障の再現)。[sensor-fan.md](sensor-fan.md) |
| `simulator/OpenBmc/fanobj/` | Redfish `ThermalSubsystem/Fans` 用の D-Bus 在庫サービス(Go、BMC 起動時に転送して実行) |
| `simulator/OpenBmc/entrypoint.sh` | QEMU の起動と `post_boot.sh` の呼び出し |
| `simulator/OpenBmc/post_boot.sh` | 起動後に `power_sync.sh` を実行 |
| `simulator/OpenBmc/power_sync.sh` | 電源サービスの開始、BMC 要求とコンテナ状態の同期 |
| `simulator/PowerBridge/bridge.py` | 電源操作を docker 操作へ変換する HTTP API |
| `simulator/RockyLinuxServer/Dockerfile` | 監視対象の Rocky Linux |
| `docker-compose.sim.yml` | `ast2700-obmc` / `rocky-server` / `power-bridge` の定義 |
