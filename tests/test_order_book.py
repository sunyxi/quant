from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from autotrade.core.models import Market
from autotrade.market_data.order_book import BookLevel, OrderBookSnapshot


TOKYO = ZoneInfo("Asia/Tokyo")


class OrderBookSnapshotTests(unittest.TestCase):
    def test_rejects_crossed_or_misordered_book(self) -> None:
        with self.assertRaises(ValueError):
            OrderBookSnapshot(
                symbol="7203.T",
                market=Market.JP,
                timestamp=datetime(2026, 7, 29, 9, 1, tzinfo=TOKYO),
                bids=(BookLevel(price=1001, quantity=100),),
                asks=(BookLevel(price=1000, quantity=100),),
            )

        with self.assertRaises(ValueError):
            OrderBookSnapshot(
                symbol="7203.T",
                market=Market.JP,
                timestamp=datetime(2026, 7, 29, 9, 1, tzinfo=TOKYO),
                bids=(
                    BookLevel(price=1000, quantity=100),
                    BookLevel(price=1001, quantity=100),
                ),
                asks=(BookLevel(price=1002, quantity=100),),
            )

    def test_spread_depth_obi_and_microprice_are_computed(self) -> None:
        book = OrderBookSnapshot(
            symbol="7203.T",
            market=Market.JP,
            timestamp=datetime(2026, 7, 29, 9, 1, tzinfo=TOKYO),
            bids=(
                BookLevel(price=1000, quantity=300),
                BookLevel(price=999, quantity=200),
            ),
            asks=(
                BookLevel(price=1002, quantity=100),
                BookLevel(price=1003, quantity=100),
            ),
        )

        self.assertEqual(1000, book.best_bid.price)
        self.assertEqual(1002, book.best_ask.price)
        self.assertAlmostEqual(19.98001998, book.relative_spread_bps, places=6)
        self.assertEqual(500, book.bid_depth(levels=5))
        self.assertEqual(200, book.ask_depth(levels=5))
        self.assertAlmostEqual(0.4285714286, book.order_book_imbalance(levels=5))
        self.assertAlmostEqual(1001.5, book.microprice)

    def test_freshness_and_health_flag_stale_books(self) -> None:
        book = OrderBookSnapshot(
            symbol="7203.T",
            market=Market.JP,
            timestamp=datetime(2026, 7, 29, 9, 1, tzinfo=TOKYO),
            bids=(BookLevel(price=1000, quantity=100),),
            asks=(BookLevel(price=1001, quantity=100),),
        )

        self.assertTrue(
            book.is_fresh(
                datetime(2026, 7, 29, 9, 1, 1, tzinfo=TOKYO),
                max_age=timedelta(seconds=2),
            )
        )
        self.assertFalse(
            book.is_fresh(
                datetime(2026, 7, 29, 9, 1, 3, tzinfo=TOKYO),
                max_age=timedelta(seconds=2),
            )
        )
        self.assertEqual("STALE", book.health_status(datetime(2026, 7, 29, 9, 1, 3, tzinfo=TOKYO)))


if __name__ == "__main__":
    unittest.main()
