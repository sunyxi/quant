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

当前执行层也有本地 Shadow Mode readiness gate，可在不连接真实券商的情况下评估回放结果、对账证据、未平模拟订单和风控暂停状态。

Shadow Mode readiness decision 可以转换成本地 run summary，记录交易日、状态、阻断原因和指标，用于 fixture 审阅。

Shadow Mode run summary 可以写成本地确定性 JSON 文件，用于 fixture 审阅。

Shadow Mode run summary JSON 文件可以通过本地 schema 校验读回。

Shadow Mode run summary JSON 现在带有本地 `schema_version` 1，用于兼容性检查。

Shadow Mode run summary 可以在本地聚合为 passed 和 blocked fixture run 的审阅计数。

Shadow Mode summary review 可以写成本地确定性 JSON 文件，用于 fixture 审阅。

仓库 Agent 工作规则记录在 `AGENT.md`。

回放执行现在会跳过同一次运行内重复的客户端订单ID，在严重对账差异时快速失败，隔离默认运行结果，并拒绝与指定交易日不一致的快照。

当前执行层也包含本地专用的 kabu Station 订单 mapper，用于未来 adapter 边界测试；它不会发送真实订单。

该 mapper 也包含本地官方请求 contract helper，用于 token 和现物下单 payload；仍不会认证或联网。

kabu Station token client 可使用 fake transport 测试，并在不连接 kabu Station 的情况下映射认证、限流和服务器错误。

kabu Station localhost HTTP transport 可以被显式构造，用于 localhost-only JSON transport 测试和 Windows 只读 probe。默认策略只允许 token 认证以及只读 orders/positions 查询；真实 sendorder 和 cancelorder 仍被阻断。

localhost 边界现在会对重定向目标重新执行 loopback 和只读策略检查，并拒绝编码后的 endpoint path。空或非 JSON HTTP 错误体仍保留按状态分类的错误，并区分 configuration、connection、timeout 和操作系统错误，同时保留已成功认证的证据。

kabu Station 只读 probe 和 report writer 会生成带 schema version 的脱敏 JSON 证据，只包含状态和计数。Mac 侧测试只使用 fake transport/opener；真实认证和真实响应兼容性仍需要在运行 kabu Station 的 Windows 上验证。

kabu Station sendorder client 也可以使用 fake transport 测试，不会发送真实订单。

kabu Station cancelorder client 也可以使用 fake transport 测试，不会取消真实订单。

kabu Station read-only client 也可以使用 fake transport 测试，不会查询真实订单或真实持仓。

kabu Station snapshot mapper 会把本地只读 payload fixture 转成对账测试用的券商快照，不会查询真实账户。

kabu Station read-only reconciler 可以基于注入的只读 client 数据、OMS 状态和账本状态运行本地对账，不创建真实 transport，也不产生券商副作用。

仓库 CI 会在 PR 和推送到 `main` 时运行 Python 单元测试、Task Catalog 漂移检查、Markdown 链接/样式检查和基础密钥扫描。

请阅读 `docs/roadmap.md`、`docs/task-catalog.md`、`docs/scope.md`、`docs/risk-policy.md`、`docs/broker-decision.md`、`docs/implementation-plan.md`、`docs/market-calendar.md`、`docs/order-book-intelligence.md`、`docs/backtest-fill-cost.md`、`docs/strategy-market-quality.md`、`docs/oms.md`、`docs/execution-ledger.md`、`docs/risk-paused-state.md`、`docs/reconciliation.md`、`docs/simulated-broker.md`、`docs/replay-execution.md`、`docs/kabu-station-mapper.md`、`docs/operations.md`、`docs/limitations.md` 和 `docs/rollback.md`。
