from __future__ import annotations

from abc import ABC, abstractmethod

from autotrade.core.models import Fill, OrderIntent


class BrokerAdapter(ABC):
    @abstractmethod
    def submit_order(self, intent: OrderIntent) -> str:
        """Submit an approved order and return broker order id."""

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> None:
        """Cancel an open order."""

    @abstractmethod
    def open_orders(self) -> list[OrderIntent]:
        """Return currently open orders known by the broker."""

    @abstractmethod
    def fills(self) -> list[Fill]:
        """Return fills from the broker."""
