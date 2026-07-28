from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from autotrade.core.models import Market, Side, Signal
from autotrade.risk.manager import RiskConfig, RiskManager, RiskState


class RiskManagerTests(unittest.TestCase):
    def test_jp_quantity_is_rounded_to_lot_size(self) -> None:
        signal = Signal(
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

        intent = RiskManager(RiskConfig(account_equity=1_000_000)).approve(signal, "2026-07-28")

        self.assertIsNotNone(intent)
        self.assertEqual(intent.quantity, 100)

    def test_daily_loss_stop_blocks_new_orders(self) -> None:
        signal = Signal(
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

        manager = RiskManager(
            RiskConfig(account_equity=1_000_000),
            RiskState(realized_pnl_today=-7_500),
        )

        self.assertIsNone(manager.approve(signal, "2026-07-28"))


if __name__ == "__main__":
    unittest.main()
