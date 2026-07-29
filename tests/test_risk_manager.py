from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from autotrade.core.models import Market, Side, Signal
from autotrade.risk.manager import RiskConfig, RiskManager, RiskState


class RiskManagerTests(unittest.TestCase):
    def _signal(self) -> Signal:
        return Signal(
            strategy_id="test",
            symbol="7203.T",
            market=Market.JP,
            side=Side.BUY,
            confidence=0.7,
            entry_price=1000,
            stop_price=990,
            take_profit_price=1020,
            created_at=datetime(2026, 7, 28, 9, 30, tzinfo=ZoneInfo("Asia/Tokyo")),
            reason="unit test",
        )

    def test_jp_quantity_is_rounded_to_lot_size(self) -> None:
        signal = self._signal()

        intent = RiskManager(RiskConfig(account_equity=1_000_000)).approve(signal, "2026-07-28")

        self.assertIsNotNone(intent)
        self.assertEqual(intent.quantity, 100)

    def test_daily_loss_stop_blocks_new_orders(self) -> None:
        signal = self._signal()

        manager = RiskManager(
            RiskConfig(account_equity=1_000_000),
            RiskState(realized_pnl_today=-7_500),
        )

        self.assertIsNone(manager.approve(signal, "2026-07-28"))

    def test_risk_paused_state_blocks_new_orders(self) -> None:
        manager = RiskManager(RiskConfig(account_equity=1_000_000))
        manager.pause("position mismatch")

        self.assertIsNone(manager.approve(self._signal(), "2026-07-28"))
        self.assertTrue(manager.state.is_paused)
        self.assertEqual(manager.state.pause_reason, "position mismatch")

    def test_resume_allows_new_orders_after_pause(self) -> None:
        manager = RiskManager(RiskConfig(account_equity=1_000_000))
        manager.pause("manual review")
        manager.resume()

        intent = manager.approve(self._signal(), "2026-07-28")

        self.assertIsNotNone(intent)
        self.assertFalse(manager.state.is_paused)
        self.assertIsNone(manager.state.pause_reason)


if __name__ == "__main__":
    unittest.main()
