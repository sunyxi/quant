from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from autotrade.backtest.cost_model import CostBreakdown, CostModel
from autotrade.backtest.fill_model import ConservativeFillModel
from autotrade.core.models import Fill, MarketSnapshot, OrderIntent
from autotrade.risk.manager import RiskManager
from autotrade.strategies.base import Strategy


class MarketCalendar(Protocol):
    def accepts_new_entries(self, timestamp: datetime) -> bool:
        ...


@dataclass
class BacktestResult:
    intents: list[OrderIntent] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)
    costs: dict[str, CostBreakdown] = field(default_factory=dict)


class BacktestEngine:
    def __init__(
        self,
        strategies: list[Strategy],
        risk_manager: RiskManager,
        market_calendar: MarketCalendar | None = None,
        fill_model: ConservativeFillModel | None = None,
        cost_model: CostModel | None = None,
    ) -> None:
        self.strategies = strategies
        self.risk_manager = risk_manager
        self.market_calendar = market_calendar
        self.fill_model = fill_model or ConservativeFillModel()
        self.cost_model = cost_model or CostModel()

    def run(self, snapshots: list[MarketSnapshot], trading_date: str) -> BacktestResult:
        result = BacktestResult()
        for snapshot in snapshots:
            if (
                self.market_calendar is not None
                and not self.market_calendar.accepts_new_entries(snapshot.timestamp)
            ):
                continue
            for strategy in self.strategies:
                signal = strategy.on_snapshot(snapshot)
                if signal is None:
                    continue
                intent = self.risk_manager.approve(signal, trading_date)
                if intent is None:
                    continue
                result.intents.append(intent)
                fill = self.fill_model.try_fill(intent, snapshot)
                if fill is None:
                    continue
                result.fills.append(fill)
                result.costs[intent.client_order_id] = self.cost_model.estimate(
                    intent,
                    snapshot,
                )
        return result
