from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo


TOKYO = ZoneInfo("Asia/Tokyo")


@dataclass(frozen=True)
class TradingSession:
    start: time
    end: time

    def contains(self, timestamp: datetime) -> bool:
        local_time = timestamp.astimezone(TOKYO).time()
        return self.start <= local_time < self.end


class JPTradingCalendar:
    def __init__(
        self,
        sessions: tuple[TradingSession, ...] | None = None,
        close_flattening_cutoff: time = time(15, 20),
        holidays: frozenset[str] | None = None,
    ) -> None:
        self.sessions = sessions or (
            TradingSession(start=time(9, 0), end=time(11, 30)),
            TradingSession(start=time(12, 30), end=time(15, 30)),
        )
        self.close_flattening_cutoff = close_flattening_cutoff
        self.holidays = holidays or frozenset()

    def is_trading_day(self, timestamp: datetime) -> bool:
        local_date = timestamp.astimezone(TOKYO).date()
        if local_date.weekday() >= 5:
            return False
        return local_date.isoformat() not in self.holidays

    def is_open(self, timestamp: datetime) -> bool:
        if not self.is_trading_day(timestamp):
            return False
        return any(session.contains(timestamp) for session in self.sessions)

    def accepts_new_entries(self, timestamp: datetime) -> bool:
        if not self.is_open(timestamp):
            return False
        local_time = timestamp.astimezone(TOKYO).time()
        return local_time < self.close_flattening_cutoff

    def requires_flattening(self, timestamp: datetime) -> bool:
        if not self.is_open(timestamp):
            return False
        local_time = timestamp.astimezone(TOKYO).time()
        return local_time >= self.close_flattening_cutoff
