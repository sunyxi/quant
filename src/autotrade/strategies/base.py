from __future__ import annotations

from abc import ABC, abstractmethod

from autotrade.core.models import MarketSnapshot, Signal


class Strategy(ABC):
    strategy_id: str

    @abstractmethod
    def on_snapshot(self, snapshot: MarketSnapshot) -> Signal | None:
        """Return a signal when the strategy wants risk review."""
