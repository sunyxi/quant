# 概要

このリポジトリは、研究を先行する日中取引プラットフォームの骨格です。初期対象は日本株であり、リスク管理、注文管理、照合、シャドーモードの検証が完了するまで、実際の証券会社への発注は対象外です。

初期リリースの範囲は、日本株、買いのみ、持ち越しなし、実取引前の Shadow Mode です。日本株の将来の接続先は kabu Station、米国株は後続フェーズの IBKR とします。

現在のカレンダー層は、日本株の通常取引時間、昼休み、週末除外、手動祝日、引け前の新規エントリー停止時刻を研究用フィルターとして扱います。

現在の板情報層は、研究用フィクスチャとして不変スナップショット、スプレッド、可視深度、OBI、microprice、鮮度、STALE 判定を扱います。

現在のバックテスト層は、保守的な約定と、手数料、半スプレッド、スリッページ、インパクトのコスト帰属を記録します。

現在の戦略層は、スプレッド上限を超えた場合、または板情報の鮮度・健全性フラグが不利な場合に、ORB と VWAP のシグナルを抑止できます。

現在の実行層は、証券会社に依存しない OMS 状態機械を持ち、ローカル注文登録の冪等性と監査可能なライフサイクル遷移を扱います。

現在の実行層は、研究用フィクスチャ向けにローカル注文、約定、ポジション、平均価格、実現損益を扱うメモリ内台帳も持ちます。

現在のリスク層は、理由付きの一時停止状態に入り、再開されるまで新規注文承認を拒否できます。

現在の実行層は、ローカル OMS・台帳状態と証券会社スナップショットを比較し、重大な照合差異でリスクを停止できます。

現在の実行層は、ライブ証券会社に接続せず、冪等な注文送信、取消、未約定注文照会、フィクスチャ主導の約定を扱うシミュレート証券会社アダプターも含みます。

シミュレート証券会社は、照合テスト向けの証券会社状態スナップショットを出力できます。

現在の実行層は、戦略、リスク、OMS、シミュレート約定、照合を接続するローカル回放実行ループも持ちます。

現在の実行層は、実ブローカーへ接続せずにリプレイ結果、照合証跡、未解消のシミュレート注文、リスク停止状態を評価するローカル Shadow Mode readiness gate も持ちます。

Shadow Mode readiness decision は、fixture レビュー向けに取引日、状態、ブロック理由、メトリクスを含むローカル run summary へ変換できます。

Shadow Mode run summary は、fixture レビュー向けに決定的なローカル JSON ファイルとして書き出せます。

Shadow Mode run summary の JSON ファイルは、ローカルのスキーマ検証付きで読み戻せます。

Shadow Mode run summary JSON は、互換性チェック向けにローカル `schema_version` 1 を持ちます。

Shadow Mode run summary は、fixture 実行の passed と blocked の件数レビュー向けにローカル集計できます。

Shadow Mode summary review は、fixture レビュー向けに決定的なローカル JSON ファイルとして書き出せます。

リポジトリのエージェント規則は `AGENT.md` に記録されています。

リプレイ実行は、1回の実行内の重複したクライアント注文IDをスキップし、重大な照合差異で即時失敗し、標準実行結果を分離し、指定された取引日と一致しないスナップショットを拒否します。

現在の実行層は、将来のアダプター境界テスト向けにローカル専用の kabu Station 注文マッパーも含みます。これは実注文を発注しません。

このマッパーには、トークンと現物注文ペイロード向けのローカル公式リクエスト契約ヘルパーもありますが、認証やネットワーク通信は行いません。

kabu Station トークンクライアントは fake transport でテストでき、kabu Station に接続せずに認証、流量制限、サーバー失敗をローカルエラーへ変換します。

kabu Station localhost HTTP transport は、localhost 専用の JSON transport テストと Windows の参照専用 probe 向けに明示的に構築できます。標準ポリシーはトークン認証と参照専用の注文・建玉照会だけを許可し、実際の sendorder と cancelorder は引き続きブロックします。

localhost 境界は、リダイレクトにも loopback と参照専用ポリシーを再適用し、エンコードされた endpoint path を拒否します。空または JSON でない HTTP エラー本文でも status 別エラーを保持し、configuration、connection、timeout、OS エラーを区別しながら、成功した認証の証跡を保持します。

kabu Station 参照専用 probe と report writer は、状態と件数だけを含むサニタイズ済みの schema version 付き JSON 証跡を出力します。Mac 側テストは fake transport/opener のみを使います。実認証と実レスポンス互換性の確認には、kabu Station を起動した Windows がまだ必要です。

kabu Station 発注クライアントも fake transport でテストでき、実注文は発注しません。

kabu Station 取消クライアントも fake transport でテストでき、実注文は取消しません。

kabu Station 参照専用クライアントも fake transport でテストでき、実際の注文や建玉は照会しません。

kabu Station スナップショットマッパーは、ローカルの参照専用ペイロード fixture を実口座へ照会せずに照合テスト用のブローカースナップショットへ変換します。

kabu Station 参照専用リコンサイラーは、注入された参照専用クライアントデータ、OMS 状態、台帳状態に対して、実 transport の作成や証券会社副作用なしにローカル照合を実行できます。

リポジトリ CI は、プルリクエストと `main` への push に対して Python 単体テスト、Task Catalog の差分チェック、Markdown リンク・スタイルチェック、基本的なシークレットスキャンを実行します。

詳細は `docs/roadmap.md`、`docs/task-catalog.md`、`docs/scope.md`、`docs/risk-policy.md`、`docs/broker-decision.md`、`docs/implementation-plan.md`、`docs/market-calendar.md`、`docs/order-book-intelligence.md`、`docs/backtest-fill-cost.md`、`docs/strategy-market-quality.md`、`docs/oms.md`、`docs/execution-ledger.md`、`docs/risk-paused-state.md`、`docs/reconciliation.md`、`docs/simulated-broker.md`、`docs/replay-execution.md`、`docs/kabu-station-mapper.md`、`docs/operations.md`、`docs/limitations.md`、`docs/rollback.md` を参照してください。
