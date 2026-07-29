# 概要

このリポジトリは、研究を先行する日中取引プラットフォームの骨格です。初期対象は日本株であり、リスク管理、注文管理、照合、シャドーモードの検証が完了するまで、実際の証券会社への発注は対象外です。

初期リリースの範囲は、日本株、買いのみ、持ち越しなし、実取引前の Shadow Mode です。日本株の将来の接続先は kabu Station、米国株は後続フェーズの IBKR とします。

現在のカレンダー層は、日本株の通常取引時間、昼休み、週末除外、手動祝日、引け前の新規エントリー停止時刻を研究用フィルターとして扱います。

現在の板情報層は、研究用フィクスチャとして不変スナップショット、スプレッド、可視深度、OBI、microprice、鮮度、STALE 判定を扱います。

現在のバックテスト層は、保守的な約定と、手数料、半スプレッド、スリッページ、インパクトのコスト帰属を記録します。

現在の戦略層は、スプレッド上限を超えた場合、または板情報の鮮度・健全性フラグが不利な場合に、ORB と VWAP のシグナルを抑止できます。

リポジトリ CI は、プルリクエストと `main` への push に対して Python 単体テスト、Task Catalog の差分チェック、Markdown リンク・スタイルチェック、基本的なシークレットスキャンを実行します。

詳細は `docs/roadmap.md`、`docs/task-catalog.md`、`docs/scope.md`、`docs/risk-policy.md`、`docs/broker-decision.md`、`docs/implementation-plan.md`、`docs/market-calendar.md`、`docs/order-book-intelligence.md`、`docs/backtest-fill-cost.md`、`docs/strategy-market-quality.md`、`docs/operations.md`、`docs/limitations.md`、`docs/rollback.md` を参照してください。
