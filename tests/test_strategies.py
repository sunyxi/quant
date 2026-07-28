from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from autotrade.core.models import Market, MarketSnapshot, Side
from autotrade.strategies.opening_range import OpeningRangeBreakout
from autotrade.strategies.vwap_reversion import VwapReversion


class StrategyTests(unittest.TestCase):
    def test_opening_range_breakout_generates_buy_signal(self) -> None:
        strategy = OpeningRangeBreakout(atr=20)
        strategy.set_opening_range(high=1000, low=980)
        snapshot = MarketSnapshot(
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

        signal = strategy.on_snapshot(snapshot)

        self.assertIsNotNone(signal)
        self.assertEqual(signal.side, Side.BUY)

    def test_vwap_reversion_ignores_trending_market(self) -> None:
        strategy = VwapReversion()
        snapshot = MarketSnapshot(
            symbol="7203.T",
            market=Market.JP,
            timestamp=datetime(2026, 7, 28, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            bid=950,
            ask=951,
            last=950,
            volume=100_000,
            vwap=1000,
            features={"ewma_sigma": 10, "trend_score": 0.8},
        )

        self.assertIsNone(strategy.on_snapshot(snapshot))


if __name__ == "__main__":
    unittest.main()
