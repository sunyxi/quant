# 股票自动交易系统

这是一个面向日内交易研究与后续自动执行的 Python 工程骨架。当前版本只实现研究、信号、风控与简化回测闭环，不包含真实券商下单。

## 当前范围

- 标准化市场快照、交易信号、订单意图与成交记录。
- 开盘区间突破策略。
- VWAP 均值回归策略。
- 单笔风险、日亏损、交易单位与资金占用检查。
- 简化事件驱动回测引擎。
- 面向 kabu Station / IBKR 的执行适配器边界。

## 快速开始

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
PYTHONPATH=src python -m unittest discover -s tests
```

运行示例回测：

```bash
python -m autotrade.backtest.demo
```

## 目录

```text
config/                 市场、风险、策略配置
docs/                   架构与落地说明
src/autotrade/          主代码
tests/                  单元测试
```

## 项目文档

- [Roadmap](docs/roadmap.md)
- [Task Catalog](docs/task-catalog.md)
- [CLI Usage](docs/cli-usage.md)
- [Operations](docs/operations.md)
- [Limitations](docs/limitations.md)
- [Rollback](docs/rollback.md)
- [English overview](docs/locales/en/overview.md)
- [Japanese overview](docs/locales/ja/overview.md)
- [Simplified Chinese overview](docs/locales/zh-CN/overview.md)

`docs/task-catalog.md` 是生成文件，必须从 `docs/task-source.json` 重建：

```bash
python3 scripts/generate_task_catalog.py
```

## 实盘前必须补齐

- 授权行情数据接入与历史数据落库。
- 更真实的 bid/ask、排队位置、部分成交和滑点模型。
- 交易日历、午休、停牌、特别报价、涨跌停等市场规则。
- 券商账本核对、断线恢复、Kill Switch。
- Shadow Mode 与小仓位实盘验证。
