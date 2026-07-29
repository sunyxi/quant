from __future__ import annotations

from dataclasses import dataclass

from autotrade.core.models import MarketSnapshot, OrderIntent


@dataclass(frozen=True)
class CostBreakdown:
    commission: float = 0.0
    spread: float = 0.0
    slippage: float = 0.0
    impact: float = 0.0

    @property
    def total(self) -> float:
        return self.commission + self.spread + self.slippage + self.impact


@dataclass(frozen=True)
class CostModel:
    commission_per_share: float = 0.0
    slippage_bps: float = 0.0
    impact_bps: float = 0.0

    def estimate(self, intent: OrderIntent, snapshot: MarketSnapshot) -> CostBreakdown:
        notional = intent.quantity * intent.limit_price
        spread_per_share = max(snapshot.ask - snapshot.bid, 0) / 2
        return CostBreakdown(
            commission=intent.quantity * self.commission_per_share,
            spread=intent.quantity * spread_per_share,
            slippage=notional * self.slippage_bps / 10_000,
            impact=notional * self.impact_bps / 10_000,
        )
