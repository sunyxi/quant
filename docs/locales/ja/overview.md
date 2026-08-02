# 概要

このリポジトリは、研究を先行する日中取引プラットフォームの骨格です。初期対象は日本株であり、リスク管理、注文管理、照合、シャドーモードの検証が完了するまで、実際の証券会社への発注は対象外です。

初期リリースの範囲は、日本株、買いのみ、持ち越しなし、実取引前の Shadow Mode のままです。macOS 上の Moomoo OpenAPI を、口座、米国株機能、日本株相場権限のサニタイズ済み参照専用 PoC として最優先し、実注文は行いません。日本株現物の相場情報は必要な権限があれば利用できますが、Moomoo JP は現在、日本株現物の実取引 API に対応していません。ISSUE-035 は OpenD と `moomoo-api` `>=10.4.6408` を要件とし、依存関係を分離して `unlock_trade` を禁止しています。kabu Station を将来の日本株接続先、IBKR を米国株の代替候補とします。

ISSUE-035 は、任意の `moomoo-api` 境界と `moomoo-readonly-discovery` CLI を実装します。validate-only は SDK を import せず socket も開きません。明示的な `--connect` では、OpenD のグローバル状態、相場権限メタデータ、サニタイズ済み口座一覧形状だけを参照します。任意レポートの保存に失敗してもサニタイズ済み JSON は stdout に残りますが、終了コード `2` はブロッキング扱いです。購読、デモ注文、実注文、取消、取引アンロックは提供しません。

ISSUE-036 は `moomoo-paper-readiness` を追加し、検証済み discovery report をオフラインで評価して不変かつ決定的な `READY` または `BLOCKED` のスナップショットを出力します。ログイン証跡の `null` は未確認、`false` は確認済み未ログインを示します。SDK Context や証券会社への要求は作成しません。`READY` は、後続の審査済み米国株デモ注文 Issue の検討だけを許し、デモ注文、Shadow Mode、実注文、日本株取引を承認しません。

ISSUE-037 は、準備完了した米国株買い指値 intent 向けのオフライン `moomoo-paper-order-dry-run` 契約を追加します。passive/aggressive の元スタイル、8〜64文字の client order ID、BUY のリスク価格関係を検証し、`SIMULATE`、`NORMAL`、`DAY`、`RTH` の固定値と数量・想定元本上限を出力します。SDK の import、口座選択、発注は行わず、デモ取引や実取引を承認しません。

ISSUE-038 は、明示的に接続する参照専用 `moomoo-paper-account-preflight` を追加します。有効な米国 `SIMULATE` `STOCK_AND_OPTION` 口座をメモリ内で一つだけ選び、資金、建玉、注文一覧を最新化して参照します。口座 ID は出力せず、注文を変更せず、デモ取引や実取引を承認しません。

ISSUE-039 は、明示的に確認した米国株 BUY 指値注文一件を `SIMULATE` へ送信する、標準無効の `moomoo-paper-order-submit` 境界を追加します。送信は最大一回で、client order remark を最新化照会し、不明な結果は再試行しません。リポジトリテストは fake SDK のみを使い、実 OpenD のデモ注文は別途の操作者承認を必要とします。

ISSUE-040 は、参照専用の `moomoo-paper-order-reconcile` 境界を追加します。最新化した `SIMULATE` 注文一覧を一回だけ照会し、完全一致する remark の証跡を `UNIQUE`、`ABSENT`、`DUPLICATE`、`BLOCKED`、`UNKNOWN` として、証券会社 ID なしで出力します。`ABSENT` は未送信の証明ではなく、このコマンドは再送信や注文変更を行いません。

ISSUE-041 は、canary と incident の永続的な証跡向けに create-only の schema version 1 照合レポートを追加します。厳格な reader は OpenD や SDK なしでオフライン検証します。レポートはサニタイズ済み結果だけを含み、既存ファイルを上書きせず、Git から除外されたローカルパスに保持されます。注文一覧の照会が完了しなかった場合、指定されたレポートは明示的に exit code `2` で失敗します。

ISSUE-042 は、承認済みの paper `place_order` を一回実行した後に create-only の schema version 1 submission report を作成します。注文パラメータや証券会社 ID なしで、サニタイズ済みの不確定な結果をオフライン確認用に保存します。アカウント選択前のネットワーク失敗は `connection`、送信後の失敗は `verification` として区別されます。送信前のブロックではレポートを作成せず、レポート保存は canary の承認や再送を行いません。

ISSUE-043 は、検証済みローカル 5 分 RTH キャッシュを読み込み、long-only ORB のライフサイクル、PnL、各約定脚の実際名目額に基づくコスト感応度、銘柄別帰属、および重複しない Walk-Forward レポートを追加します。atomic create-only の schema version 2 出力は全期間のデフォルト結果を `default_parameter_full_period` として明示します。データのダウンロード、Moomoo の読み込み、証券会社への接続、取引承認は行いません。

ISSUE-044 は、192 組に制限した nested ORB チューニングに、double-cost、最悪 fold、銘柄集中度、パラメータ近傍の gate を追加します。後半 96 組は、既に確認した期間に対し、90 分のシグナル期限、ブレイクアウト終値位置の閾値、同方向の VWAP 傾きを探索的に追加します。保存キャッシュの結果は引き続き `no-go` で、候補が選択された外側 fold は 4 つ中 1 つのみで、その固定テストも負でした。これは汚染された探索的証拠であり、独立した検証ではありません。

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

詳細は `docs/roadmap.md`、`docs/task-catalog.md`、`docs/scope.md`、`docs/risk-policy.md`、`docs/broker-decision.md`、`docs/implementation-plan.md`、`docs/market-calendar.md`、`docs/order-book-intelligence.md`、`docs/backtest-fill-cost.md`、`docs/historical-orb-backtest.md`、`docs/strategy-market-quality.md`、`docs/oms.md`、`docs/execution-ledger.md`、`docs/risk-paused-state.md`、`docs/reconciliation.md`、`docs/simulated-broker.md`、`docs/replay-execution.md`、`docs/kabu-station-mapper.md`、`docs/moomoo-openapi.md`、`docs/operations.md`、`docs/limitations.md`、`docs/rollback.md` を参照してください。
