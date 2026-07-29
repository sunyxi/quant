from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from autotrade.core.models import Market, MarketSnapshot
from autotrade.execution.oms import OrderState, OrderStateMachine
from autotrade.execution.reconciliation import (
    ReconciliationDiscrepancy,
    ReconciliationReport,
    ReconciliationSeverity,
)
from autotrade.execution.replay import ReplayExecutionEngine, ReplayExecutionError
from autotrade.execution.simulated_broker import SimulatedBrokerAdapter
from autotrade.risk.manager import RiskConfig, RiskManager
from autotrade.strategies.opening_range import OpeningRangeBreakout


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="7203.T",
        market=Market.JP,
        timestamp=datetime(2026, 7, 28, 9, 16, tzinfo=ZoneInfo("Asia/Tokyo")),
        bid=1001,
        ask=1002,
        last=1002,
        volume=100_000,
        vwap=995,
        features={"relative_volume": 2.0},
    )


def _strategy() -> OpeningRangeBreakout:
    strategy = OpeningRangeBreakout(atr=20)
    strategy.set_opening_range(high=1000, low=980)
    return strategy


def _engine(
    *,
    risk_manager: RiskManager | None = None,
    oms: OrderStateMachine | None = None,
    broker: SimulatedBrokerAdapter | None = None,
    reconciliation: object | None = None,
) -> ReplayExecutionEngine:
    return ReplayExecutionEngine(
        strategies=[_strategy()],
        risk_manager=risk_manager or RiskManager(RiskConfig(account_equity=2_000_000)),
        oms=oms,
        broker=broker,
        reconciliation=reconciliation,
    )


class AlwaysCriticalReconciliation:
    def check(self, **_: object) -> ReconciliationReport:
        return ReconciliationReport(
            discrepancies=[
                ReconciliationDiscrepancy(
                    kind="TEST_CRITICAL",
                    severity=ReconciliationSeverity.CRITICAL,
                    message="fixture critical discrepancy",
                )
            ]
        )


class ReplayExecutionEngineTests(unittest.TestCase):
    def test_replay_submits_fills_and_reconciles_cleanly(self) -> None:
        engine = _engine()

        result = engine.run([_snapshot()], trading_date="2026-07-28")

        self.assertEqual(len(result.intents), 1)
        self.assertEqual(len(result.fills), 1)
        self.assertEqual(result.oms.orders()[0].state, OrderState.FILLED)
        self.assertEqual(result.broker.open_orders(), [])
        self.assertFalse(result.reconciliation_reports[-1].has_critical)

    def test_replay_does_not_submit_when_risk_rejects(self) -> None:
        risk = RiskManager(RiskConfig(account_equity=1_000_000))
        risk.pause("manual review")
        engine = _engine(risk_manager=risk)

        result = engine.run([_snapshot()], trading_date="2026-07-28")

        self.assertEqual(result.intents, [])
        self.assertEqual(result.fills, [])
        self.assertEqual(result.broker.open_orders(), [])

    def test_duplicate_client_order_id_does_not_crash_replay(self) -> None:
        engine = _engine()

        result = engine.run([_snapshot(), _snapshot()], trading_date="2026-07-28")

        self.assertEqual(len(result.intents), 1)
        self.assertEqual(len(result.fills), 1)
        self.assertEqual(result.oms.orders()[0].state, OrderState.FILLED)

    def test_unfilled_order_is_cancelled_before_reconciliation(self) -> None:
        snapshot = MarketSnapshot(
            symbol="7203.T",
            market=Market.JP,
            timestamp=datetime(2026, 7, 28, 9, 16, tzinfo=ZoneInfo("Asia/Tokyo")),
            bid=1001,
            ask=1002,
            last=1002,
            volume=0,
            vwap=995,
            features={"relative_volume": 2.0},
        )
        engine = _engine()

        result = engine.run([snapshot], trading_date="2026-07-28")

        self.assertEqual(result.fills, [])
        self.assertEqual(result.broker.open_orders(), [])
        self.assertEqual(result.oms.orders()[0].state, OrderState.CANCELLED)

    def test_critical_reconciliation_raises_instead_of_silent_pause(self) -> None:
        engine = _engine(reconciliation=AlwaysCriticalReconciliation())

        with self.assertRaises(ReplayExecutionError):
            engine.run([_snapshot()], trading_date="2026-07-28")

    def test_run_results_do_not_share_oms_or_broker_state(self) -> None:
        engine = _engine()

        first = engine.run([_snapshot()], trading_date="2026-07-28")
        second_snapshot = MarketSnapshot(
            symbol="6758.T",
            market=Market.JP,
            timestamp=datetime(2026, 7, 29, 9, 16, tzinfo=ZoneInfo("Asia/Tokyo")),
            bid=1001,
            ask=1002,
            last=1002,
            volume=100_000,
            vwap=995,
            features={"relative_volume": 2.0},
        )
        second = engine.run([second_snapshot], trading_date="2026-07-29")

        self.assertEqual(len(first.oms.orders()), 1)
        self.assertEqual(first.oms.orders()[0].intent.symbol, "7203.T")
        self.assertEqual(len(second.oms.orders()), 1)
        self.assertEqual(second.oms.orders()[0].intent.symbol, "6758.T")

    def test_trading_date_must_match_snapshot_date(self) -> None:
        engine = _engine()

        with self.assertRaises(ValueError):
            engine.run([_snapshot()], trading_date="2026-07-29")


if __name__ == "__main__":
    unittest.main()
