from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from autotrade.core.models import Fill, Market, OrderIntent, OrderStyle, Side
from autotrade.execution.ledger import LedgerError, LocalExecutionLedger


def _intent(client_order_id: str = "client-1", side: Side = Side.BUY) -> OrderIntent:
    return OrderIntent(
        client_order_id=client_order_id,
        strategy_id="test_strategy",
        symbol="7203.T",
        market=Market.JP,
        side=side,
        quantity=100,
        order_style=OrderStyle.PASSIVE_LIMIT,
        limit_price=1000,
        stop_price=990,
        take_profit_price=1020,
        created_at=datetime(2026, 7, 28, 9, 30, tzinfo=ZoneInfo("Asia/Tokyo")),
    )


def _fill(
    client_order_id: str = "client-1",
    side: Side = Side.BUY,
    quantity: int = 100,
    price: float = 1000,
) -> Fill:
    return Fill(
        client_order_id=client_order_id,
        symbol="7203.T",
        side=side,
        quantity=quantity,
        price=price,
        filled_at=datetime(2026, 7, 28, 9, 31, tzinfo=ZoneInfo("Asia/Tokyo")),
    )


class LocalExecutionLedgerTests(unittest.TestCase):
    def test_records_order_once_by_client_order_id(self) -> None:
        ledger = LocalExecutionLedger()
        first = ledger.record_order(_intent())
        second = ledger.record_order(_intent())

        self.assertIs(first, second)
        self.assertEqual(len(ledger.orders()), 1)

    def test_rejects_fill_without_registered_order(self) -> None:
        ledger = LocalExecutionLedger()

        with self.assertRaises(LedgerError):
            ledger.record_fill(_fill())

    def test_updates_long_position_average_price(self) -> None:
        ledger = LocalExecutionLedger()
        ledger.record_order(_intent())
        ledger.record_order(_intent("client-2"))

        ledger.record_fill(_fill(price=1000))
        ledger.record_fill(_fill("client-2", price=1010))

        position = ledger.position("7203.T")
        self.assertIsNotNone(position)
        self.assertEqual(position.quantity, 200)
        self.assertEqual(position.average_price, 1005)
        self.assertEqual(position.realized_pnl, 0)

    def test_realizes_pnl_when_selling_long_position(self) -> None:
        ledger = LocalExecutionLedger()
        ledger.record_order(_intent())
        ledger.record_order(_intent("client-2", side=Side.SELL))

        ledger.record_fill(_fill(price=1000))
        ledger.record_fill(_fill("client-2", side=Side.SELL, price=1020))

        position = ledger.position("7203.T")
        self.assertIsNotNone(position)
        self.assertEqual(position.quantity, 0)
        self.assertEqual(position.average_price, 0)
        self.assertEqual(position.realized_pnl, 2000)


if __name__ == "__main__":
    unittest.main()
