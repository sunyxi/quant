from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import StrEnum

from autotrade.core.models import Market, OrderIntent, OrderStyle, Side
from autotrade.execution.moomoo_readiness import MoomooPaperReadinessDecision


MOOMOO_PAPER_ORDER_PLAN_SCHEMA_VERSION = 1
_CLIENT_ORDER_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,63}")
_US_CODE_PATTERN = re.compile(
    r"US\.[A-Z][A-Z0-9]*(?:[.-][A-Z][A-Z0-9]*)*"
)
_NUMERIC_TYPES = frozenset({int, float})
_SUPPORTED_STYLES = frozenset(
    {
        OrderStyle.PASSIVE_LIMIT,
        OrderStyle.AGGRESSIVE_LIMIT,
    }
)


class MoomooPaperOrderPlanReason(StrEnum):
    READINESS_NOT_READY = "READINESS_NOT_READY"
    MARKET_NOT_US = "MARKET_NOT_US"
    SIDE_NOT_BUY = "SIDE_NOT_BUY"
    ORDER_STYLE_UNSUPPORTED = "ORDER_STYLE_UNSUPPORTED"
    SYMBOL_INVALID = "SYMBOL_INVALID"
    QUANTITY_INVALID = "QUANTITY_INVALID"
    QUANTITY_LIMIT_EXCEEDED = "QUANTITY_LIMIT_EXCEEDED"
    NOTIONAL_LIMIT_EXCEEDED = "NOTIONAL_LIMIT_EXCEEDED"
    PRICE_INVALID = "PRICE_INVALID"
    CLIENT_ORDER_ID_INVALID = "CLIENT_ORDER_ID_INVALID"


class MoomooPaperOrderPlanError(ValueError):
    def __init__(self, reason: MoomooPaperOrderPlanReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True)
class MoomooPaperOrderPlan:
    client_order_id: str
    code: str
    quantity: int
    price: float
    source_order_style: str
    stop_price: float
    take_profit_price: float | None
    notional_usd: float
    schema_version: int = MOOMOO_PAPER_ORDER_PLAN_SCHEMA_VERSION
    dry_run: bool = True
    side: str = "BUY"
    order_type: str = "NORMAL"
    trd_env: str = "SIMULATE"
    time_in_force: str = "DAY"
    session: str = "RTH"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "dry_run": self.dry_run,
            "client_order_id": self.client_order_id,
            "code": self.code,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "order_type": self.order_type,
            "trd_env": self.trd_env,
            "time_in_force": self.time_in_force,
            "session": self.session,
            "source_order_style": self.source_order_style,
            "stop_price": self.stop_price,
            "take_profit_price": self.take_profit_price,
            "notional_usd": self.notional_usd,
        }


@dataclass(frozen=True)
class MoomooPaperOrderDryRunPlanner:
    max_quantity: int = 100
    max_notional_usd: float = 25_000.0

    def __post_init__(self) -> None:
        if type(self.max_quantity) is not int or self.max_quantity <= 0:
            raise ValueError("max_quantity must be a positive integer")
        if not _is_positive_finite(self.max_notional_usd):
            raise ValueError("max_notional_usd must be positive and finite")

    def plan(
        self,
        intent: OrderIntent,
        *,
        readiness: MoomooPaperReadinessDecision,
    ) -> MoomooPaperOrderPlan:
        if not readiness.is_ready:
            raise MoomooPaperOrderPlanError(
                MoomooPaperOrderPlanReason.READINESS_NOT_READY
            )
        if intent.market != Market.US:
            raise MoomooPaperOrderPlanError(
                MoomooPaperOrderPlanReason.MARKET_NOT_US
            )
        if intent.side != Side.BUY:
            raise MoomooPaperOrderPlanError(
                MoomooPaperOrderPlanReason.SIDE_NOT_BUY
            )
        if intent.order_style not in _SUPPORTED_STYLES:
            raise MoomooPaperOrderPlanError(
                MoomooPaperOrderPlanReason.ORDER_STYLE_UNSUPPORTED
            )
        if len(intent.symbol) > 20 or not _US_CODE_PATTERN.fullmatch(intent.symbol):
            raise MoomooPaperOrderPlanError(
                MoomooPaperOrderPlanReason.SYMBOL_INVALID
            )
        if type(intent.quantity) is not int or intent.quantity <= 0:
            raise MoomooPaperOrderPlanError(
                MoomooPaperOrderPlanReason.QUANTITY_INVALID
            )
        if intent.quantity > self.max_quantity:
            raise MoomooPaperOrderPlanError(
                MoomooPaperOrderPlanReason.QUANTITY_LIMIT_EXCEEDED
            )
        if not _CLIENT_ORDER_ID_PATTERN.fullmatch(intent.client_order_id):
            raise MoomooPaperOrderPlanError(
                MoomooPaperOrderPlanReason.CLIENT_ORDER_ID_INVALID
            )
        prices = (intent.limit_price, intent.stop_price)
        if intent.take_profit_price is not None:
            prices += (intent.take_profit_price,)
        if not all(_is_positive_finite(price) for price in prices):
            raise MoomooPaperOrderPlanError(
                MoomooPaperOrderPlanReason.PRICE_INVALID
            )
        if intent.stop_price >= intent.limit_price:
            raise MoomooPaperOrderPlanError(
                MoomooPaperOrderPlanReason.PRICE_INVALID
            )
        if (
            intent.take_profit_price is not None
            and intent.take_profit_price <= intent.limit_price
        ):
            raise MoomooPaperOrderPlanError(
                MoomooPaperOrderPlanReason.PRICE_INVALID
            )

        notional_usd = round(intent.quantity * intent.limit_price, 8)
        if notional_usd > self.max_notional_usd:
            raise MoomooPaperOrderPlanError(
                MoomooPaperOrderPlanReason.NOTIONAL_LIMIT_EXCEEDED
            )
        return MoomooPaperOrderPlan(
            client_order_id=intent.client_order_id,
            code=intent.symbol,
            quantity=intent.quantity,
            price=intent.limit_price,
            source_order_style=intent.order_style.value,
            stop_price=intent.stop_price,
            take_profit_price=intent.take_profit_price,
            notional_usd=notional_usd,
        )


def _is_positive_finite(value: object) -> bool:
    return type(value) in _NUMERIC_TYPES and math.isfinite(value) and value > 0
