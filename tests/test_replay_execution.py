from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from autotrade.core.models import Market, MarketSnapshot, Side
from autotrade.execution.oms import OrderState
from autotrade.execution.replay import ReplayExecutionEngine
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


class ReplayExecutionEngineTests(unittest.TestCase):
    def test_replay_submits_fills_and_reconciles_cleanly(self) -> None:
        strategy = OpeningRangeBreakout(atr=20)
        strategy.set_opening_range(high=1000, low=980)
        engine = ReplayExecutionEngine(
            strategies=[strategy],
            risk_manager=RiskManager(RiskConfig(account_equity=2_000_000)),
        )

        result = engine.run([_snapshot()], trading_date="2026-07-28")

        self.assertEqual(len(result.intents), 1)
        self.assertEqual(len(result.fills), 1)
        self.assertEqual(result.oms.orders()[0].state, OrderState.FILLED)
        self.assertEqual(result.broker.open_orders(), [])
        self.assertFalse(result.reconciliation_reports[-1].has_critical)

    def test_replay_does_not_submit_when_risk_rejects(self) -> None:
        strategy = OpeningRangeBreakout(atr=20)
        strategy.set_opening_range(high=1000, low=980)
        risk = RiskManager(RiskConfig(account_equity=1_000_000))
        risk.pause("manual review")
        engine = ReplayExecutionEngine(strategies=[strategy], risk_manager=risk)

        result = engine.run([_snapshot()], trading_date="2026-07-28")

        self.assertEqual(result.intents, [])
        self.assertEqual(result.fills, [])
        self.assertEqual(result.broker.open_orders(), [])


if __name__ == "__main__":
    unittest.main()
