from __future__ import annotations

from dataclasses import replace

from autotrade.core.ids import client_order_id
from autotrade.core.models import Fill, OrderIntent
from autotrade.execution.broker import BrokerAdapter


class SimulatedBrokerAdapter(BrokerAdapter):
    def __init__(self) -> None:
        self._orders_by_client_id: dict[str, OrderIntent] = {}
        self._client_by_broker_id: dict[str, str] = {}
        self._broker_by_client_id: dict[str, str] = {}
        self._fills: list[Fill] = []

    def submit_order(self, intent: OrderIntent) -> str:
        existing = self._broker_by_client_id.get(intent.client_order_id)
        if existing is not None:
            return existing

        broker_order_id = client_order_id("sim", intent.client_order_id)
        self._orders_by_client_id[intent.client_order_id] = intent
        self._client_by_broker_id[broker_order_id] = intent.client_order_id
        self._broker_by_client_id[intent.client_order_id] = broker_order_id
        return broker_order_id

    def cancel_order(self, broker_order_id: str) -> None:
        client_id = self._client_by_broker_id.pop(broker_order_id, None)
        if client_id is None:
            return
        self._orders_by_client_id.pop(client_id, None)
        self._broker_by_client_id.pop(client_id, None)

    def open_orders(self) -> list[OrderIntent]:
        return list(self._orders_by_client_id.values())

    def fills(self) -> list[Fill]:
        return list(self._fills)

    def record_fill(self, fill: Fill) -> None:
        order = self._orders_by_client_id.get(fill.client_order_id)
        if order is None:
            return

        self._fills.append(fill)
        remaining_quantity = order.quantity - fill.quantity
        if remaining_quantity <= 0:
            broker_order_id = self._broker_by_client_id.get(fill.client_order_id)
            if broker_order_id is not None:
                self.cancel_order(broker_order_id)
            return

        self._orders_by_client_id[fill.client_order_id] = replace(
            order,
            quantity=remaining_quantity,
        )
