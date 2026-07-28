from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class Market(StrEnum):
    JP = "JP"
    US = "US"


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStyle(StrEnum):
    PASSIVE_LIMIT = "PASSIVE_LIMIT"
    AGGRESSIVE_LIMIT = "AGGRESSIVE_LIMIT"
    MARKET_PROTECTED = "MARKET_PROTECTED"


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    market: Market
    timestamp: datetime
    bid: float
    ask: float
    last: float
    volume: int
    vwap: float | None = None
    features: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.bid <= 0 or self.ask <= 0 or self.last <= 0:
            raise ValueError("prices must be positive")
        if self.ask < self.bid:
            raise ValueError("ask must be greater than or equal to bid")
        if self.volume < 0:
            raise ValueError("volume must be non-negative")
        if self.vwap is not None and self.vwap <= 0:
            raise ValueError("vwap must be positive")

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread_bps(self) -> float:
        return (self.ask - self.bid) / self.mid * 10_000


@dataclass(frozen=True)
class Signal:
    strategy_id: str
    symbol: str
    market: Market
    side: Side
    confidence: float
    entry_price: float
    stop_price: float
    take_profit_price: float | None
    created_at: datetime
    reason: str

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.entry_price <= 0 or self.stop_price <= 0:
            raise ValueError("entry and stop prices must be positive")
        if self.take_profit_price is not None and self.take_profit_price <= 0:
            raise ValueError("take profit price must be positive")


@dataclass(frozen=True)
class OrderIntent:
    client_order_id: str
    strategy_id: str
    symbol: str
    market: Market
    side: Side
    quantity: int
    order_style: OrderStyle
    limit_price: float
    stop_price: float
    take_profit_price: float | None
    created_at: datetime

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.limit_price <= 0 or self.stop_price <= 0:
            raise ValueError("limit and stop prices must be positive")
        if self.take_profit_price is not None and self.take_profit_price <= 0:
            raise ValueError("take profit price must be positive")


@dataclass(frozen=True)
class Fill:
    client_order_id: str
    symbol: str
    side: Side
    quantity: int
    price: float
    filled_at: datetime

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.price <= 0:
            raise ValueError("price must be positive")
