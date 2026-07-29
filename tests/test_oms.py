from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from autotrade.core.models import Market, OrderIntent, OrderStyle, Side
from autotrade.execution.oms import (
    OrderState,
    OrderStateError,
    OrderStateMachine,
)


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


class OrderStateMachineTests(unittest.TestCase):
    def test_registers_intent_once_by_client_order_id(self) -> None:
        oms = OrderStateMachine()
        first = oms.register(_intent())
        second = oms.register(_intent())

        self.assertIs(first, second)
        self.assertEqual(first.state, OrderState.CREATED)
        self.assertEqual(len(oms.orders()), 1)

    def test_order_lifecycle_reaches_filled(self) -> None:
        oms = OrderStateMachine()
        record = oms.register(_intent())

        oms.transition(record.client_order_id, OrderState.RISK_APPROVED)
        oms.transition(record.client_order_id, OrderState.SUBMITTED, broker_order_id="broker-1")
        oms.transition(record.client_order_id, OrderState.ACKNOWLEDGED)
        oms.transition(record.client_order_id, OrderState.PARTIALLY_FILLED)
        filled = oms.transition(record.client_order_id, OrderState.FILLED)

        self.assertEqual(filled.state, OrderState.FILLED)
        self.assertEqual(filled.broker_order_id, "broker-1")

    def test_rejects_invalid_state_transition(self) -> None:
        oms = OrderStateMachine()
        record = oms.register(_intent())

        with self.assertRaises(OrderStateError):
            oms.transition(record.client_order_id, OrderState.FILLED)

    def test_marks_unknown_after_submit_uncertainty(self) -> None:
        oms = OrderStateMachine()
        record = oms.register(_intent())

        oms.transition(record.client_order_id, OrderState.RISK_APPROVED)
        oms.transition(record.client_order_id, OrderState.SUBMITTED)
        unknown = oms.mark_unknown(record.client_order_id, reason="submit timeout")

        self.assertEqual(unknown.state, OrderState.UNKNOWN)
        self.assertEqual(unknown.last_reason, "submit timeout")


if __name__ == "__main__":
    unittest.main()
