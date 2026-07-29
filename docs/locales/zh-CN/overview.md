# 概览

本仓库是研究优先的日内交易平台骨架。首期目标是日股研究与模拟闭环；在风控、订单管理、对账和 Shadow Mode 验证通过前，不接入真实券商下单。

首期范围是日股、只做多、不隔夜，并在任何实盘前先通过 Shadow Mode。日股未来执行目标是 kabu Station，美股 IBKR 留到后续阶段。

当前日历层已覆盖日股普通交易时段、午休、周末过滤、手工假日和收盘前停止新开仓 cutoff，用于研究和回测过滤。

当前板情报层已覆盖不可变订单簿快照、价差、可见深度、OBI、microprice、数据新鲜度和 stale book health，用于研究 fixture。

当前回测层会记录保守成交，并对手续费、半价差、滑点和冲击成本进行归因。

当前策略层可以在价差超过限制，或盘口新鲜度、健康状态不合格时，阻断 ORB 和 VWAP 信号。

当前执行层已有独立于券商的 OMS 状态机，用于幂等登记本地订单并审计订单生命周期转换。

当前执行层也有内存账本，用于研究 fixture 中记录本地订单、成交、持仓、平均价格和已实现 PnL。

当前风控层可以带原因进入暂停状态，并在恢复前拒绝所有新订单审批。

当前执行层可以比较本地 OMS、账本状态与券商快照，并在严重对账差异时暂停风控审批。

当前执行层也包含模拟券商 adapter，可在不连接真实券商的情况下测试幂等下单、撤单、开放订单查询和 fixture 驱动成交。

模拟券商可以导出券商状态快照，用于对账测试。

当前执行层已有本地回放执行循环，可连接策略、风控、OMS、模拟券商成交和对账。

仓库 Agent 工作规则记录在 `AGENT.md`。

回放执行现在会跳过同一次运行内重复的客户端订单ID，在严重对账差异时快速失败，隔离默认运行结果，并拒绝与指定交易日不一致的快照。

当前执行层也包含本地专用的 kabu Station 订单 mapper，用于未来 adapter 边界测试；它不会发送真实订单。

该 mapper 也包含本地官方请求 contract helper，用于 token 和现物下单 payload；仍不会认证或联网。

kabu Station token client 可使用 fake transport 测试，并在不连接 kabu Station 的情况下映射认证、限流和服务器错误。

仓库 CI 会在 PR 和推送到 `main` 时运行 Python 单元测试、Task Catalog 漂移检查、Markdown 链接/样式检查和基础密钥扫描。

请阅读 `docs/roadmap.md`、`docs/task-catalog.md`、`docs/scope.md`、`docs/risk-policy.md`、`docs/broker-decision.md`、`docs/implementation-plan.md`、`docs/market-calendar.md`、`docs/order-book-intelligence.md`、`docs/backtest-fill-cost.md`、`docs/strategy-market-quality.md`、`docs/oms.md`、`docs/execution-ledger.md`、`docs/risk-paused-state.md`、`docs/reconciliation.md`、`docs/simulated-broker.md`、`docs/replay-execution.md`、`docs/kabu-station-mapper.md`、`docs/operations.md`、`docs/limitations.md` 和 `docs/rollback.md`。
