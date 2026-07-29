from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from autotrade.backtest.fill_model import ConservativeFillModel
from autotrade.core.models import Fill, MarketSnapshot, OrderIntent
from autotrade.execution.oms import OrderState, OrderStateMachine
from autotrade.execution.reconciliation import (
    ReconciliationEngine,
    ReconciliationReport,
)
from autotrade.execution.simulated_broker import SimulatedBrokerAdapter
from autotrade.risk.manager import RiskManager
from autotrade.strategies.base import Strategy


class MarketCalendar(Protocol):
    def accepts_new_entries(self, timestamp: datetime) -> bool:
        ...


@dataclass
class ReplayExecutionResult:
    intents: list[OrderIntent] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)
    oms: OrderStateMachine = field(default_factory=OrderStateMachine)
    broker: SimulatedBrokerAdapter = field(default_factory=SimulatedBrokerAdapter)
    reconciliation_reports: list[ReconciliationReport] = field(default_factory=list)


class ReplayExecutionEngine:
    def __init__(
        self,
        strategies: list[Strategy],
        risk_manager: RiskManager,
        market_calendar: MarketCalendar | None = None,
        fill_model: ConservativeFillModel | None = None,
        oms: OrderStateMachine | None = None,
        broker: SimulatedBrokerAdapter | None = None,
        reconciliation: ReconciliationEngine | None = None,
    ) -> None:
        self.strategies = strategies
        self.risk_manager = risk_manager
        self.market_calendar = market_calendar
        self.fill_model = fill_model or ConservativeFillModel()
        self.oms = oms or OrderStateMachine()
        self.broker = broker or SimulatedBrokerAdapter()
        self.reconciliation = reconciliation or ReconciliationEngine()

    def run(self, snapshots: list[MarketSnapshot], trading_date: str) -> ReplayExecutionResult:
        result = ReplayExecutionResult(oms=self.oms, broker=self.broker)
        for snapshot in snapshots:
            if (
                self.market_calendar is not None
                and not self.market_calendar.accepts_new_entries(snapshot.timestamp)
            ):
                continue
            for strategy in self.strategies:
                intent = self._intent_for(strategy, snapshot, trading_date)
                if intent is None:
                    continue
                result.intents.append(intent)
                fill = self._submit_and_maybe_fill(intent, snapshot)
                if fill is not None:
                    result.fills.append(fill)

            report = self.reconciliation.check(
                oms=self.oms,
                ledger=self.broker.ledger,
                broker=self.broker.state_snapshot(),
                risk_manager=self.risk_manager,
            )
            result.reconciliation_reports.append(report)
        return result

    def _intent_for(
        self,
        strategy: Strategy,
        snapshot: MarketSnapshot,
        trading_date: str,
    ) -> OrderIntent | None:
        signal = strategy.on_snapshot(snapshot)
        if signal is None:
            return None
        return self.risk_manager.approve(signal, trading_date)

    def _submit_and_maybe_fill(
        self,
        intent: OrderIntent,
        snapshot: MarketSnapshot,
    ) -> Fill | None:
        record = self.oms.register(intent)
        if record.state == OrderState.CREATED:
            self.oms.transition(intent.client_order_id, OrderState.RISK_APPROVED)

        broker_order_id = self.broker.submit_order(intent)
        self.oms.transition(
            intent.client_order_id,
            OrderState.SUBMITTED,
            broker_order_id=broker_order_id,
        )
        self.oms.transition(intent.client_order_id, OrderState.ACKNOWLEDGED)

        fill = self.fill_model.try_fill(intent, snapshot)
        if fill is None:
            return None

        self.broker.record_fill(fill)
        next_state = (
            OrderState.FILLED
            if fill.quantity >= intent.quantity
            else OrderState.PARTIALLY_FILLED
        )
        self.oms.transition(intent.client_order_id, next_state)
        return fill
