# 概览

本仓库是研究优先的日内交易平台骨架。首期目标是日股研究与模拟闭环；在风控、订单管理、对账和 Shadow Mode 验证通过前，不接入真实券商下单。

首期范围是日股、只做多、不隔夜，并在任何实盘前先通过 Shadow Mode。日股未来执行目标是 kabu Station，美股 IBKR 留到后续阶段。

仓库 CI 会在 PR 和推送到 `main` 时运行 Python 单元测试、Task Catalog 漂移检查、Markdown 链接/样式检查和基础密钥扫描。

请阅读 `docs/roadmap.md`、`docs/task-catalog.md`、`docs/scope.md`、`docs/risk-policy.md`、`docs/broker-decision.md`、`docs/implementation-plan.md`、`docs/operations.md`、`docs/limitations.md` 和 `docs/rollback.md`。
