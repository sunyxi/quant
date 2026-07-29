from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from autotrade.core.models import Fill, MarketSnapshot, OrderIntent, Side
from autotrade.risk.manager import RiskManager
from autotrade.strategies.base import Strategy


class MarketCalendar(Protocol):
    def accepts_new_entries(self, timestamp: datetime) -> bool:
        ...


@dataclass
class BacktestResult:
    intents: list[OrderIntent] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)


class BacktestEngine:
    def __init__(
        self,
        strategies: list[Strategy],
        risk_manager: RiskManager,
        market_calendar: MarketCalendar | None = None,
    ) -> None:
        self.strategies = strategies
        self.risk_manager = risk_manager
        self.market_calendar = market_calendar

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
                result.fills.append(self._fill_immediately(intent, snapshot))
        return result

    @staticmethod
    def _fill_immediately(intent: OrderIntent, snapshot: MarketSnapshot) -> Fill:
        price = snapshot.ask if intent.side == Side.BUY else snapshot.bid
        return Fill(
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=intent.quantity,
            price=price,
            filled_at=snapshot.timestamp,
        )
