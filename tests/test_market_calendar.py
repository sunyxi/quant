from __future__ import annotations

import unittest
from datetime import datetime, time
from zoneinfo import ZoneInfo

from autotrade.calendar.jp import JPTradingCalendar, TradingSession
from autotrade.core.models import Market, MarketSnapshot, Side
from autotrade.backtest.engine import BacktestEngine
from autotrade.risk.manager import RiskConfig, RiskManager
from autotrade.strategies.opening_range import OpeningRangeBreakout


TOKYO = ZoneInfo("Asia/Tokyo")


class JPTradingCalendarTests(unittest.TestCase):
    def test_regular_session_accepts_morning_and_afternoon(self) -> None:
        calendar = JPTradingCalendar()

        self.assertTrue(
            calendar.is_open(datetime(2026, 7, 29, 9, 1, tzinfo=TOKYO))
        )
        self.assertTrue(
            calendar.is_open(datetime(2026, 7, 29, 12, 31, tzinfo=TOKYO))
        )

    def test_lunch_break_and_weekends_are_closed(self) -> None:
        calendar = JPTradingCalendar()

        self.assertFalse(
            calendar.is_open(datetime(2026, 7, 29, 11, 45, tzinfo=TOKYO))
        )
        self.assertFalse(
            calendar.is_open(datetime(2026, 8, 1, 10, 0, tzinfo=TOKYO))
        )

    def test_close_flattening_cutoff_is_configurable(self) -> None:
        calendar = JPTradingCalendar(close_flattening_cutoff=time(15, 20))

        self.assertFalse(
            calendar.accepts_new_entries(datetime(2026, 7, 29, 15, 21, tzinfo=TOKYO))
        )
        self.assertTrue(
            calendar.requires_flattening(datetime(2026, 7, 29, 15, 21, tzinfo=TOKYO))
        )

    def test_custom_sessions_represent_lunch_break_explicitly(self) -> None:
        calendar = JPTradingCalendar(
            sessions=(
                TradingSession(start=time(9, 0), end=time(11, 30)),
                TradingSession(start=time(12, 30), end=time(15, 30)),
            )
        )

        self.assertEqual(2, len(calendar.sessions))
        self.assertFalse(
            calendar.is_open(datetime(2026, 7, 29, 12, 0, tzinfo=TOKYO))
        )


class BacktestCalendarTests(unittest.TestCase):
    def test_backtest_skips_snapshots_outside_trading_session(self) -> None:
        strategy = OpeningRangeBreakout(atr=20)
        strategy.set_opening_range(high=1000, low=980)
        engine = BacktestEngine(
            strategies=[strategy],
            risk_manager=RiskManager(RiskConfig(account_equity=2_000_000)),
            market_calendar=JPTradingCalendar(),
        )

        lunch_snapshot = MarketSnapshot(
            symbol="7203.T",
            market=Market.JP,
            timestamp=datetime(2026, 7, 29, 11, 45, tzinfo=TOKYO),
            bid=1001,
            ask=1002,
            last=1002,
            volume=100_000,
            vwap=995,
            features={"relative_volume": 2.0},
        )
        open_snapshot = MarketSnapshot(
            symbol="7203.T",
            market=Market.JP,
            timestamp=datetime(2026, 7, 29, 12, 31, tzinfo=TOKYO),
            bid=1001,
            ask=1002,
            last=1002,
            volume=100_000,
            vwap=995,
            features={"relative_volume": 2.0},
        )

        result = engine.run([lunch_snapshot, open_snapshot], "2026-07-29")

        self.assertEqual(1, len(result.intents))
        self.assertEqual(Side.BUY, result.intents[0].side)


if __name__ == "__main__":
    unittest.main()
