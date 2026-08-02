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

    def test_opening_range_breakout_blocks_wide_spread(self) -> None:
        strategy = OpeningRangeBreakout(atr=20, max_spread_bps=5)
        strategy.set_opening_range(high=1000, low=980)
        snapshot = MarketSnapshot(
            symbol="7203.T",
            market=Market.JP,
            timestamp=datetime(2026, 7, 28, 9, 16, tzinfo=ZoneInfo("Asia/Tokyo")),
            bid=1000,
            ask=1002,
            last=1002,
            volume=100_000,
            vwap=995,
            features={"relative_volume": 2.0},
        )

        self.assertIsNone(strategy.on_snapshot(snapshot))

    def test_opening_range_breakout_blocks_stale_order_book(self) -> None:
        strategy = OpeningRangeBreakout(atr=20, require_fresh_order_book=True)
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
            features={"relative_volume": 2.0, "order_book_stale": 1.0},
        )

        self.assertIsNone(strategy.on_snapshot(snapshot))

    def test_opening_range_breakout_blocks_unhealthy_order_book(self) -> None:
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
            features={"relative_volume": 2.0, "order_book_unhealthy": 1.0},
        )

        self.assertIsNone(strategy.on_snapshot(snapshot))

    def test_opening_range_breakout_is_long_only_by_default(self) -> None:
        strategy = OpeningRangeBreakout(atr=20)
        strategy.set_opening_range(high=1000, low=980)
        snapshot = MarketSnapshot(
            symbol="7203.T",
            market=Market.JP,
            timestamp=datetime(2026, 7, 28, 9, 16, tzinfo=ZoneInfo("Asia/Tokyo")),
            bid=975,
            ask=976,
            last=975,
            volume=100_000,
            vwap=990,
            features={"relative_volume": 2.0},
        )

        self.assertIsNone(strategy.on_snapshot(snapshot))

    def test_opening_range_stop_is_capped_by_opening_range_width(self) -> None:
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
        self.assertEqual(992.0, signal.stop_price)
        self.assertEqual(1017.0, signal.take_profit_price)

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

    def test_vwap_reversion_blocks_wide_spread(self) -> None:
        strategy = VwapReversion(max_spread_bps=5)
        snapshot = MarketSnapshot(
            symbol="7203.T",
            market=Market.JP,
            timestamp=datetime(2026, 7, 28, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            bid=948,
            ask=951,
            last=950,
            volume=100_000,
            vwap=1000,
            features={"ewma_sigma": 10, "trend_score": 0.1},
        )

        self.assertIsNone(strategy.on_snapshot(snapshot))

    def test_vwap_reversion_blocks_stale_order_book(self) -> None:
        strategy = VwapReversion(require_fresh_order_book=True)
        snapshot = MarketSnapshot(
            symbol="7203.T",
            market=Market.JP,
            timestamp=datetime(2026, 7, 28, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            bid=950,
            ask=951,
            last=950,
            volume=100_000,
            vwap=1000,
            features={
                "ewma_sigma": 10,
                "trend_score": 0.1,
                "order_book_stale": 1.0,
            },
        )

        self.assertIsNone(strategy.on_snapshot(snapshot))


if __name__ == "__main__":
    unittest.main()
