# 概要

このリポジトリは、研究を先行する日中取引プラットフォームの骨格です。初期対象は日本株であり、リスク管理、注文管理、照合、シャドーモードの検証が完了するまで、実際の証券会社への発注は対象外です。

初期リリースの範囲は、日本株、買いのみ、持ち越しなし、実取引前の Shadow Mode です。日本株の将来の接続先は kabu Station、米国株は後続フェーズの IBKR とします。

現在のカレンダー層は、日本株の通常取引時間、昼休み、週末除外、手動祝日、引け前の新規エントリー停止時刻を研究用フィルターとして扱います。

詳細は `docs/roadmap.md`、`docs/task-catalog.md`、`docs/scope.md`、`docs/risk-policy.md`、`docs/broker-decision.md`、`docs/implementation-plan.md`、`docs/market-calendar.md`、`docs/operations.md`、`docs/limitations.md`、`docs/rollback.md` を参照してください。
