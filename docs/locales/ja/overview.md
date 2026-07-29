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

リポジトリ CI は、プルリクエストと `main` への push に対して Python 単体テスト、Task Catalog の差分チェック、Markdown リンク・スタイルチェック、基本的なシークレットスキャンを実行します。

詳細は `docs/roadmap.md`、`docs/task-catalog.md`、`docs/scope.md`、`docs/risk-policy.md`、`docs/broker-decision.md`、`docs/implementation-plan.md`、`docs/market-calendar.md`、`docs/order-book-intelligence.md`、`docs/backtest-fill-cost.md`、`docs/strategy-market-quality.md`、`docs/oms.md`、`docs/execution-ledger.md`、`docs/risk-paused-state.md`、`docs/reconciliation.md`、`docs/simulated-broker.md`、`docs/operations.md`、`docs/limitations.md`、`docs/rollback.md` を参照してください。
