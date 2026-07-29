from __future__ import annotations

from dataclasses import dataclass, field

from autotrade.backtest.fill_model import ConservativeFillModel
from autotrade.calendar.protocols import MarketCalendar
from autotrade.core.models import Fill, MarketSnapshot, OrderIntent
from autotrade.execution.oms import OrderState, OrderStateMachine
from autotrade.execution.reconciliation import (
    ReconciliationEngine,
    ReconciliationReport,
)
from autotrade.execution.simulated_broker import SimulatedBrokerAdapter
from autotrade.risk.manager import RiskManager
from autotrade.strategies.base import Strategy


class ReplayExecutionError(RuntimeError):
    pass


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
        self._oms = oms
        self._broker = broker
        self.reconciliation = reconciliation or ReconciliationEngine()

    def run(self, snapshots: list[MarketSnapshot], trading_date: str) -> ReplayExecutionResult:
        self._validate_trading_date(snapshots, trading_date)
        oms = self._oms or OrderStateMachine()
        broker = self._broker or SimulatedBrokerAdapter()
        result = ReplayExecutionResult(oms=oms, broker=broker)
        submitted_client_ids: set[str] = set()
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
                if intent.client_order_id in submitted_client_ids:
                    continue
                submitted_client_ids.add(intent.client_order_id)
                result.intents.append(intent)
                fill = self._submit_and_maybe_fill(intent, snapshot, oms, broker)
                if fill is not None:
                    result.fills.append(fill)

            report = self.reconciliation.check(
                oms=oms,
                ledger=broker.ledger,
                broker=broker.state_snapshot(),
            )
            result.reconciliation_reports.append(report)
            if report.has_critical:
                raise ReplayExecutionError("critical reconciliation discrepancy")
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
        oms: OrderStateMachine,
        broker: SimulatedBrokerAdapter,
    ) -> Fill | None:
        record = oms.register(intent)
        if record.state in {
            OrderState.ACKNOWLEDGED,
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.REJECTED,
        }:
            return None

        if record.state == OrderState.CREATED:
            oms.transition(intent.client_order_id, OrderState.RISK_APPROVED)

        broker_order_id = broker.submit_order(intent)
        oms.transition(
            intent.client_order_id,
            OrderState.SUBMITTED,
            broker_order_id=broker_order_id,
        )
        oms.transition(intent.client_order_id, OrderState.ACKNOWLEDGED)

        fill = self.fill_model.try_fill(intent, snapshot)
        if fill is None:
            oms.transition(intent.client_order_id, OrderState.CANCEL_PENDING)
            broker.cancel_order(broker_order_id)
            oms.transition(intent.client_order_id, OrderState.CANCELLED)
            return None

        broker.record_fill(fill)
        next_state = (
            OrderState.FILLED
            if fill.quantity >= intent.quantity
            else OrderState.PARTIALLY_FILLED
        )
        oms.transition(intent.client_order_id, next_state)
        return fill

    @staticmethod
    def _validate_trading_date(
        snapshots: list[MarketSnapshot],
        trading_date: str,
    ) -> None:
        mismatched_dates = {
            snapshot.timestamp.date().isoformat()
            for snapshot in snapshots
            if snapshot.timestamp.date().isoformat() != trading_date
        }
        if mismatched_dates:
            raise ValueError(
                f"snapshot dates {sorted(mismatched_dates)} do not match trading_date {trading_date}"
            )
