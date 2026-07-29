from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from autotrade.core.models import Fill, Market, OrderIntent, OrderStyle, Side
from autotrade.execution.simulated_broker import SimulatedBrokerAdapter


def _intent(client_order_id: str = "client-1") -> OrderIntent:
    return OrderIntent(
        client_order_id=client_order_id,
        strategy_id="test_strategy",
        symbol="7203.T",
        market=Market.JP,
        side=Side.BUY,
        quantity=100,
        order_style=OrderStyle.PASSIVE_LIMIT,
        limit_price=1000,
        stop_price=990,
        take_profit_price=1020,
        created_at=datetime(2026, 7, 28, 9, 30, tzinfo=ZoneInfo("Asia/Tokyo")),
    )


def _fill(client_order_id: str = "client-1") -> Fill:
    return Fill(
        client_order_id=client_order_id,
        symbol="7203.T",
        side=Side.BUY,
        quantity=100,
        price=1000,
        filled_at=datetime(2026, 7, 28, 9, 31, tzinfo=ZoneInfo("Asia/Tokyo")),
    )


class SimulatedBrokerAdapterTests(unittest.TestCase):
    def test_submit_order_is_idempotent_by_client_order_id(self) -> None:
        broker = SimulatedBrokerAdapter()
        first_id = broker.submit_order(_intent())
        second_id = broker.submit_order(_intent())

        self.assertEqual(first_id, second_id)
        self.assertEqual(len(broker.open_orders()), 1)

    def test_cancel_order_removes_open_order(self) -> None:
        broker = SimulatedBrokerAdapter()
        broker_order_id = broker.submit_order(_intent())

        broker.cancel_order(broker_order_id)

        self.assertEqual(broker.open_orders(), [])

    def test_records_fills_and_closes_open_order_when_fully_filled(self) -> None:
        broker = SimulatedBrokerAdapter()
        broker.submit_order(_intent())

        broker.record_fill(_fill())

        self.assertEqual(len(broker.fills()), 1)
        self.assertEqual(broker.open_orders(), [])

    def test_partial_fill_keeps_remaining_order_open(self) -> None:
        broker = SimulatedBrokerAdapter()
        broker.submit_order(_intent())

        broker.record_fill(Fill(
            client_order_id="client-1",
            symbol="7203.T",
            side=Side.BUY,
            quantity=40,
            price=1000,
            filled_at=datetime(2026, 7, 28, 9, 31, tzinfo=ZoneInfo("Asia/Tokyo")),
        ))

        open_orders = broker.open_orders()
        self.assertEqual(len(open_orders), 1)
        self.assertEqual(open_orders[0].quantity, 60)


if __name__ == "__main__":
    unittest.main()
