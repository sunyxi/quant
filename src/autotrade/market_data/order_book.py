from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from autotrade.core.models import Market


@dataclass(frozen=True)
class BookLevel:
    price: float
    quantity: int

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError("book level price must be positive")
        if self.quantity < 0:
            raise ValueError("book level quantity must be non-negative")


@dataclass(frozen=True)
class OrderBookSnapshot:
    symbol: str
    market: Market
    timestamp: datetime
    bids: tuple[BookLevel, ...]
    asks: tuple[BookLevel, ...]

    def __post_init__(self) -> None:
        if not self.bids:
            raise ValueError("order book requires at least one bid")
        if not self.asks:
            raise ValueError("order book requires at least one ask")
        self._validate_bid_order()
        self._validate_ask_order()
        if self.best_bid.price >= self.best_ask.price:
            raise ValueError("best bid must be lower than best ask")

    @property
    def best_bid(self) -> BookLevel:
        return self.bids[0]

    @property
    def best_ask(self) -> BookLevel:
        return self.asks[0]

    @property
    def mid_price(self) -> float:
        return (self.best_bid.price + self.best_ask.price) / 2

    @property
    def relative_spread_bps(self) -> float:
        return (self.best_ask.price - self.best_bid.price) / self.mid_price * 10_000

    @property
    def microprice(self) -> float:
        bid_qty = self.best_bid.quantity
        ask_qty = self.best_ask.quantity
        total_qty = bid_qty + ask_qty
        if total_qty <= 0:
            return self.mid_price
        return (
            self.best_ask.price * bid_qty + self.best_bid.price * ask_qty
        ) / total_qty

    def bid_depth(self, levels: int = 5) -> int:
        return sum(level.quantity for level in self.bids[:levels])

    def ask_depth(self, levels: int = 5) -> int:
        return sum(level.quantity for level in self.asks[:levels])

    def order_book_imbalance(self, levels: int = 5) -> float:
        bid_depth = self.bid_depth(levels)
        ask_depth = self.ask_depth(levels)
        total_depth = bid_depth + ask_depth
        if total_depth <= 0:
            return 0.0
        return (bid_depth - ask_depth) / total_depth

    def is_fresh(self, now: datetime, max_age: timedelta) -> bool:
        return now - self.timestamp <= max_age

    def health_status(self, now: datetime, max_age: timedelta = timedelta(seconds=2)) -> str:
        return "NORMAL" if self.is_fresh(now, max_age) else "STALE"

    def _validate_bid_order(self) -> None:
        for previous, current in zip(self.bids, self.bids[1:]):
            if current.price >= previous.price:
                raise ValueError("bid levels must be sorted descending by price")

    def _validate_ask_order(self) -> None:
        for previous, current in zip(self.asks, self.asks[1:]):
            if current.price <= previous.price:
                raise ValueError("ask levels must be sorted ascending by price")
