from __future__ import annotations

from dataclasses import dataclass

from autotrade.core.models import MarketSnapshot


@dataclass(frozen=True)
class MarketQualityFilter:
    max_spread_bps: float | None = None
    require_fresh_order_book: bool = False

    def allows(self, snapshot: MarketSnapshot) -> bool:
        if self.max_spread_bps is not None and snapshot.spread_bps > self.max_spread_bps:
            return False
        if self.require_fresh_order_book and snapshot.features.get("order_book_stale", 0.0) > 0:
            return False
        if snapshot.features.get("order_book_unhealthy", 0.0) > 0:
            return False
        return True
