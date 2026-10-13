# syslog 集積基盤の計画(概略)

`rocky-server` が出力する syslog を集積・管理する DB / データウェアハウスの構築計画。
状態: **計画のみ(未実装)**。

## 1. 前提

- 現在の `rocky-server` は sshd だけを `-D -e` で動かしており、systemd も rsyslog も無い。syslog はまだ出ていない。
- 電源操作は `docker stop` / `kill` / `start` なので、停止時にログ送信が途切れる。送信側にバッファが必要。
- 既存の `docker-compose.sim.yml` にサービスを追加する形で構築する。

## 2. 構成案

```
rocky-server (rsyslog) --RELP/TCP--> log-collector (Vector) --> ClickHouse --> Grafana
        (sshd, auth, cron など)        パース・正規化          保管・集計        検索・可視化
```

| 層 | 候補 | 推奨 |
|---|---|---|
| 送信 | rsyslog(omfwd / omrelp) | rsyslog。ディスクキューで停止時の取りこぼしを減らす |
| 収集・変換 | Vector / rsyslog / Fluent Bit | Vector。RFC5424 のパースと ClickHouse への書き込みが標準機能 |
| 保管 | ClickHouse / Loki / OpenSearch / PostgreSQL | **ClickHouse**。DWH 用途で、時系列の集計に強く、圧縮と TTL が使える |
| 可視化 | Grafana | Grafana。ClickHouse プラグインがある |

軽さ優先なら ClickHouse の代わりに Loki も選べる。ラベル検索が中心で、SQL 集計は弱くなる。
「DB か DWH」という要望から、SQL で集計できる ClickHouse を推奨とした。

## 3. テーブル設計(ClickHouse)

- `syslog_raw`: 受信した生ログ。`received_at`、`host`、`facility`、`severity`、`app`、`pid`、`message`、`raw`。
- `ORDER BY (host, timestamp)`、日単位でパーティション、TTL は 30 日などから始める。
- 後から `sshd` の認証失敗や `sudo` などを抽出する集計ビュー(Materialized View)を追加する。

## 4. フェーズ

1. **送信側の用意**: `rocky-server` に rsyslog を入れ、sshd と rsyslog を同時に動かせるようにする。`/dev/log` と `auth` ログを出す設定にする。
2. **収集・保管**: `log-collector`(Vector)と `clickhouse` を compose に追加する。まずは受信した生ログをそのまま保存する。
3. **可視化**: Grafana を追加し、ホスト別、重大度別、時系列のダッシュボードを作る。
4. **電源連携との結び付け**: `power-bridge` の操作履歴(on / off / reset)も同じ DB に入れる。BMC の journal も送れば、「電源操作の前後にサーバーで何が起きたか」を同じ画面で追える。
5. **運用面**: 保持期間、ディスク上限、認証(ClickHouse のユーザー分離)、停止時の再送を確認する。

## 5. 確認用のテスト

- ログを 1 件出して、数秒以内に ClickHouse に入ることを確認する。
- 電源操作の ForceOff と On を行い、停止中のログが欠けないか(キューの再送)を確認する。
- 10 万件程度を流して、検索と集計の速度を確認する。

## 6. 未決事項(括弧内は未決のまま進める場合の既定値)

| 項目 | 既定 |
|---|---|
| 保管先を ClickHouse か、軽い Loki か | ClickHouse |
| BMC 側のログも集めるか | 最初は Rocky のみ、フェーズ 4 で追加 |
| 保持期間と想定ログ量 | 30 日、小規模のサンプル用 |
| Rocky を systemd 化するか | しない(rsyslog と sshd の同時起動だけで済ませる) |

## 7. 関連ドキュメント

- [power-integration.md](power-integration.md): BMC の電源操作と `rocky-server` の連携
- [image-changes.md](image-changes.md): BMC イメージへの変更点
