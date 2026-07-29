from __future__ import annotations

from datetime import datetime
from typing import Protocol


class MarketCalendar(Protocol):
    def accepts_new_entries(self, timestamp: datetime) -> bool:
        ...
