from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from autotrade.core.models import OrderIntent


class OrderState(StrEnum):
    CREATED = "CREATED"
    RISK_APPROVED = "RISK_APPROVED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class OrderStateError(ValueError):
    pass


@dataclass(frozen=True)
class OrderRecord:
    intent: OrderIntent
    state: OrderState = OrderState.CREATED
    broker_order_id: str | None = None
    last_reason: str | None = None

    @property
    def client_order_id(self) -> str:
        return self.intent.client_order_id


class OrderStateMachine:
    _ALLOWED: dict[OrderState, set[OrderState]] = {
        OrderState.CREATED: {OrderState.RISK_APPROVED, OrderState.REJECTED},
        OrderState.RISK_APPROVED: {OrderState.SUBMITTED, OrderState.REJECTED},
        OrderState.SUBMITTED: {
            OrderState.ACKNOWLEDGED,
            OrderState.REJECTED,
            OrderState.UNKNOWN,
        },
        OrderState.ACKNOWLEDGED: {
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCEL_PENDING,
            OrderState.UNKNOWN,
        },
        OrderState.PARTIALLY_FILLED: {
            OrderState.FILLED,
            OrderState.CANCEL_PENDING,
            OrderState.UNKNOWN,
        },
        OrderState.CANCEL_PENDING: {
            OrderState.CANCELLED,
            OrderState.FILLED,
            OrderState.UNKNOWN,
        },
        OrderState.UNKNOWN: {
            OrderState.ACKNOWLEDGED,
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.REJECTED,
        },
        OrderState.FILLED: set(),
        OrderState.CANCELLED: set(),
        OrderState.REJECTED: set(),
    }

    def __init__(self) -> None:
        self._records: dict[str, OrderRecord] = {}

    def register(self, intent: OrderIntent) -> OrderRecord:
        existing = self._records.get(intent.client_order_id)
        if existing is not None:
            return existing
        record = OrderRecord(intent=intent)
        self._records[intent.client_order_id] = record
        return record

    def transition(
        self,
        client_order_id: str,
        new_state: OrderState,
        *,
        broker_order_id: str | None = None,
        reason: str | None = None,
    ) -> OrderRecord:
        record = self._require_record(client_order_id)
        if new_state not in self._ALLOWED[record.state]:
            raise OrderStateError(f"cannot transition from {record.state} to {new_state}")

        updated = replace(
            record,
            state=new_state,
            broker_order_id=broker_order_id or record.broker_order_id,
            last_reason=reason,
        )
        self._records[client_order_id] = updated
        return updated

    def mark_unknown(self, client_order_id: str, *, reason: str) -> OrderRecord:
        return self.transition(client_order_id, OrderState.UNKNOWN, reason=reason)

    def get(self, client_order_id: str) -> OrderRecord | None:
        return self._records.get(client_order_id)

    def orders(self) -> list[OrderRecord]:
        return list(self._records.values())

    def _require_record(self, client_order_id: str) -> OrderRecord:
        record = self._records.get(client_order_id)
        if record is None:
            raise KeyError(client_order_id)
        return record
