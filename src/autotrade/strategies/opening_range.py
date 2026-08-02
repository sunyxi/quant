from __future__ import annotations

from dataclasses import dataclass

from autotrade.core.models import MarketSnapshot, Side, Signal
from autotrade.strategies.base import Strategy
from autotrade.strategies.market_quality import MarketQualityFilter


@dataclass
class OpeningRangeBreakout(Strategy):
    strategy_id: str = "jp_orb_v1"
    opening_range_high: float | None = None
    opening_range_low: float | None = None
    atr: float = 1.0
    min_relative_volume: float = 1.5
    opening_range_stop_fraction: float = 0.5
    long_only: bool = True
    max_spread_bps: float | None = None
    require_fresh_order_book: bool = False

    def set_opening_range(self, high: float, low: float) -> None:
        if high <= low:
            raise ValueError("opening range high must be greater than low")
        self.opening_range_high = high
        self.opening_range_low = low

    def on_snapshot(self, snapshot: MarketSnapshot) -> Signal | None:
        quality_filter = MarketQualityFilter(
            max_spread_bps=self.max_spread_bps,
            require_fresh_order_book=self.require_fresh_order_book,
        )
        if not quality_filter.allows(snapshot):
            return None

        if self.opening_range_high is None or self.opening_range_low is None:
            return None

        relative_volume = snapshot.features.get("relative_volume", 0.0)
        if relative_volume < self.min_relative_volume:
            return None

        breakout_buffer = 0.05 * self.atr
        if snapshot.last > self.opening_range_high + breakout_buffer:
            if snapshot.vwap is not None and snapshot.last < snapshot.vwap:
                return None
            stop_distance = min(
                0.6 * self.atr,
                self.opening_range_stop_fraction
                * (self.opening_range_high - self.opening_range_low),
            )
            stop = snapshot.last - stop_distance
            target = snapshot.last + 1.5 * stop_distance
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                market=snapshot.market,
                side=Side.BUY,
                confidence=0.6,
                entry_price=snapshot.ask,
                stop_price=stop,
                take_profit_price=target,
                created_at=snapshot.timestamp,
                reason="opening range upside breakout",
            )

        if (
            not self.long_only
            and snapshot.last < self.opening_range_low - breakout_buffer
        ):
            if snapshot.vwap is not None and snapshot.last > snapshot.vwap:
                return None
            stop_distance = min(
                0.6 * self.atr,
                self.opening_range_stop_fraction
                * (self.opening_range_high - self.opening_range_low),
            )
            stop = snapshot.last + stop_distance
            target = snapshot.last - 1.5 * stop_distance
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                market=snapshot.market,
                side=Side.SELL,
                confidence=0.6,
                entry_price=snapshot.bid,
                stop_price=stop,
                take_profit_price=target,
                created_at=snapshot.timestamp,
                reason="opening range downside breakout",
            )

        return None
