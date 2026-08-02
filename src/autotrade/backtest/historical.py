from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import os
import tempfile
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from pathlib import Path
from statistics import mean, stdev
from typing import Iterable, Mapping, Sequence


HISTORICAL_CACHE_SCHEMA_VERSION = 1
HISTORICAL_REPORT_SCHEMA_VERSION = 2
HISTORICAL_CACHE_COLUMNS = (
    "timestamp",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "turnover",
    "atr",
    "vwap",
    "relative_volume",
)


class HistoricalCacheError(ValueError):
    pass


@dataclass(frozen=True)
class HistoricalBar:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    turnover: float
    atr: float
    vwap: float
    relative_volume: float

    def __post_init__(self) -> None:
        prices = (self.open, self.high, self.low, self.close, self.vwap)
        if not self.symbol or any(not math.isfinite(value) or value <= 0 for value in prices):
            raise ValueError("historical bar symbol and prices must be valid")
        if self.high < max(self.open, self.close, self.low) or self.low > min(
            self.open, self.close, self.high
        ):
            raise ValueError("historical bar OHLC values are inconsistent")
        if type(self.volume) is not int or self.volume < 0:
            raise ValueError("historical bar volume must be a non-negative integer")
        if not math.isfinite(self.turnover) or self.turnover < 0:
            raise ValueError("historical bar turnover must be non-negative")
        if not math.isfinite(self.atr) or self.atr <= 0:
            raise ValueError("historical bar ATR must be positive")
        if not math.isfinite(self.relative_volume) or self.relative_volume < 0:
            raise ValueError("historical bar relative volume must be non-negative")


@dataclass(frozen=True)
class HistoricalDataset:
    bars: tuple[HistoricalBar, ...]
    symbols: tuple[str, ...]
    bar_size: str
    session: str
    date_start: date
    date_end: date
    sha256: str


@dataclass(frozen=True)
class OrbResearchParameters:
    opening_range_minutes: int = 15
    min_relative_volume: float = 1.5
    breakout_buffer_atr: float = 0.05
    daily_atr_stop_multiple: float = 0.6
    opening_range_stop_fraction: float = 0.5
    target_r_multiple: float = 1.5
    max_holding_minutes: int = 30
    side_cost_bps: float = 2.5
    notional_per_trade: float = 10_000.0
    long_only: bool = True

    def __post_init__(self) -> None:
        if self.opening_range_minutes <= 0 or self.opening_range_minutes % 5:
            raise ValueError("opening range minutes must be a positive multiple of five")
        if self.max_holding_minutes <= 0 or self.max_holding_minutes % 5:
            raise ValueError("holding minutes must be a positive multiple of five")
        positive = (
            self.min_relative_volume,
            self.daily_atr_stop_multiple,
            self.opening_range_stop_fraction,
            self.target_r_multiple,
            self.notional_per_trade,
        )
        if any(not math.isfinite(value) or value <= 0 for value in positive):
            raise ValueError("ORB research parameters must be positive")
        if (
            not math.isfinite(self.breakout_buffer_atr)
            or self.breakout_buffer_atr < 0
            or not math.isfinite(self.side_cost_bps)
            or self.side_cost_bps < 0
        ):
            raise ValueError("ORB buffer and costs must be non-negative")

    @property
    def key(self) -> str:
        direction = "long" if self.long_only else "both"
        return (
            f"or{self.opening_range_minutes}-rv{self.min_relative_volume:g}"
            f"-buf{self.breakout_buffer_atr:g}-atr{self.daily_atr_stop_multiple:g}"
            f"-orstop{self.opening_range_stop_fraction:g}-r{self.target_r_multiple:g}"
            f"-hold{self.max_holding_minutes}-{direction}"
        )


@dataclass(frozen=True)
class HistoricalTrade:
    symbol: str
    trading_date: date
    side: str
    entry_at: datetime
    exit_at: datetime
    entry_price: float
    exit_price: float
    stop_price: float
    target_price: float
    quantity: int
    exit_reason: str
    gross_pnl: float
    cost: float
    net_pnl: float
    gross_return: float
    net_return: float

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["trading_date"] = self.trading_date.isoformat()
        payload["entry_at"] = self.entry_at.isoformat()
        payload["exit_at"] = self.exit_at.isoformat()
        return payload


@dataclass(frozen=True)
class PerformanceMetrics:
    trade_count: int
    win_rate: float
    mean_net_bps: float
    profit_factor: float | None
    daily_sharpe: float
    max_drawdown_pct: float
    total_return_pct: float
    total_net_pnl: float


@dataclass(frozen=True)
class HistoricalBacktestResult:
    parameters: OrbResearchParameters
    trades: tuple[HistoricalTrade, ...]
    metrics: PerformanceMetrics
    by_symbol: Mapping[str, PerformanceMetrics]
    cost_scenarios: Mapping[str, PerformanceMetrics]

    def to_dict(self) -> dict[str, object]:
        return {
            "parameters": asdict(self.parameters),
            "trades": [trade.to_dict() for trade in self.trades],
            "metrics": asdict(self.metrics),
            "by_symbol": {
                symbol: asdict(metrics)
                for symbol, metrics in sorted(self.by_symbol.items())
            },
            "cost_scenarios": {
                name: asdict(metrics)
                for name, metrics in self.cost_scenarios.items()
            },
        }


@dataclass(frozen=True)
class WalkForwardConfig:
    train_days: int = 100
    test_days: int = 20
    step_days: int = 20
    min_trades: int = 20
    min_train_sharpe: float = 0.0
    min_train_profit_factor: float = 1.0

    def __post_init__(self) -> None:
        if min(self.train_days, self.test_days, self.step_days) <= 0:
            raise ValueError("walk-forward windows must be positive")
        if self.step_days < self.test_days:
            raise ValueError(
                "walk-forward step_days must be >= test_days to avoid "
                "overlapping test windows"
            )
        if self.step_days > self.train_days:
            raise ValueError(
                "walk-forward step_days must be <= train_days to preserve "
                "training coverage"
            )
        if self.min_trades < 0:
            raise ValueError("walk-forward minimum trades must be non-negative")
        if (
            not math.isfinite(self.min_train_sharpe)
            or not math.isfinite(self.min_train_profit_factor)
            or self.min_train_profit_factor < 0
        ):
            raise ValueError("walk-forward promotion thresholds must be valid")


@dataclass(frozen=True)
class WalkForwardFold:
    train_dates: tuple[date, ...]
    test_dates: tuple[date, ...]

    @property
    def train_start(self) -> date:
        return self.train_dates[0]

    @property
    def train_end(self) -> date:
        return self.train_dates[-1]

    @property
    def test_start(self) -> date:
        return self.test_dates[0]

    @property
    def test_end(self) -> date:
        return self.test_dates[-1]


@dataclass(frozen=True)
class WalkForwardFoldResult:
    fold: WalkForwardFold
    evaluated_candidate_count: int
    eligible_candidate_count: int
    best_observed_parameters: OrbResearchParameters | None
    best_observed_train_metrics: PerformanceMetrics | None
    selected_parameters: OrbResearchParameters | None
    train_metrics: PerformanceMetrics | None
    test_metrics: PerformanceMetrics | None

    def to_dict(self) -> dict[str, object]:
        return {
            "train_start": self.fold.train_start.isoformat(),
            "train_end": self.fold.train_end.isoformat(),
            "test_start": self.fold.test_start.isoformat(),
            "test_end": self.fold.test_end.isoformat(),
            "evaluated_candidate_count": self.evaluated_candidate_count,
            "eligible_candidate_count": self.eligible_candidate_count,
            "best_observed_parameters": (
                asdict(self.best_observed_parameters)
                if self.best_observed_parameters is not None
                else None
            ),
            "best_observed_train_metrics": (
                asdict(self.best_observed_train_metrics)
                if self.best_observed_train_metrics is not None
                else None
            ),
            "selected_parameters": (
                asdict(self.selected_parameters)
                if self.selected_parameters is not None
                else None
            ),
            "train_metrics": (
                asdict(self.train_metrics) if self.train_metrics is not None else None
            ),
            "test_metrics": (
                asdict(self.test_metrics) if self.test_metrics is not None else None
            ),
        }


@dataclass(frozen=True)
class WalkForwardResult:
    folds: tuple[WalkForwardFoldResult, ...]

    def to_dict(self) -> dict[str, object]:
        return {"folds": [fold.to_dict() for fold in self.folds]}


def build_walk_forward_folds(
    dates: Iterable[date], config: WalkForwardConfig
) -> tuple[WalkForwardFold, ...]:
    ordered = sorted(set(dates))
    folds = []
    test_start = config.train_days
    while test_start + config.test_days <= len(ordered):
        train_start = test_start - config.train_days
        folds.append(
            WalkForwardFold(
                train_dates=tuple(ordered[train_start:test_start]),
                test_dates=tuple(
                    ordered[test_start : test_start + config.test_days]
                ),
            )
        )
        test_start += config.step_days
    return tuple(folds)


class HistoricalOrbBacktester:
    def run(
        self,
        bars: Sequence[HistoricalBar],
        parameters: OrbResearchParameters,
    ) -> HistoricalBacktestResult:
        grouped: dict[tuple[str, date], list[HistoricalBar]] = defaultdict(list)
        for item in sorted(bars, key=lambda value: (value.symbol, value.timestamp)):
            grouped[(item.symbol, item.timestamp.date())].append(item)

        trades = []
        for (symbol, trading_date), day_bars in grouped.items():
            trade = self._run_day(symbol, trading_date, day_bars, parameters)
            if trade is not None:
                trades.append(trade)
        trades_tuple = tuple(sorted(trades, key=lambda item: item.entry_at))
        symbols = sorted({item.symbol for item in bars})
        metrics = _calculate_metrics(
            trades_tuple, parameters.side_cost_bps, max(len(symbols), 1)
        )
        by_symbol = {
            symbol: _calculate_metrics(
                tuple(item for item in trades_tuple if item.symbol == symbol),
                parameters.side_cost_bps,
                1,
            )
            for symbol in symbols
        }
        cost_scenarios = {
            "zero": _calculate_metrics(trades_tuple, 0.0, max(len(symbols), 1)),
            "baseline": metrics,
            "double": _calculate_metrics(
                trades_tuple, parameters.side_cost_bps * 2, max(len(symbols), 1)
            ),
        }
        return HistoricalBacktestResult(
            parameters=parameters,
            trades=trades_tuple,
            metrics=metrics,
            by_symbol=by_symbol,
            cost_scenarios=cost_scenarios,
        )

    @staticmethod
    def _run_day(
        symbol: str,
        trading_date: date,
        bars: Sequence[HistoricalBar],
        parameters: OrbResearchParameters,
    ) -> HistoricalTrade | None:
        opening_count = parameters.opening_range_minutes // 5
        if len(bars) <= opening_count + 1:
            return None
        opening = bars[:opening_count]
        opening_high = max(item.high for item in opening)
        opening_low = min(item.low for item in opening)
        opening_width = opening_high - opening_low
        if opening_width <= 0:
            return None

        direction = 0
        signal_index = None
        for index in range(opening_count, len(bars) - 1):
            item = bars[index]
            buffer = parameters.breakout_buffer_atr * item.atr
            if (
                item.relative_volume >= parameters.min_relative_volume
                and item.close > opening_high + buffer
                and item.close >= item.vwap
            ):
                direction = 1
                signal_index = index
                break
            if (
                not parameters.long_only
                and item.relative_volume >= parameters.min_relative_volume
                and item.close < opening_low - buffer
                and item.close <= item.vwap
            ):
                direction = -1
                signal_index = index
                break
        if signal_index is None:
            return None

        entry_index = signal_index + 1
        entry_bar = bars[entry_index]
        entry_price = entry_bar.open
        stop_distance = min(
            parameters.daily_atr_stop_multiple * bars[signal_index].atr,
            parameters.opening_range_stop_fraction * opening_width,
        )
        if stop_distance <= 0:
            return None
        stop_price = entry_price - direction * stop_distance
        target_price = (
            entry_price + direction * parameters.target_r_multiple * stop_distance
        )
        quantity = int(parameters.notional_per_trade // entry_price)
        if quantity <= 0 or min(stop_price, target_price) <= 0:
            return None

        max_bars = parameters.max_holding_minutes // 5
        last_exit_index = min(entry_index + max_bars - 1, len(bars) - 1)
        exit_index = last_exit_index
        exit_price = bars[exit_index].close
        exit_reason = (
            "time" if last_exit_index < len(bars) - 1 else "session_close"
        )
        for index in range(entry_index, last_exit_index + 1):
            item = bars[index]
            stop_hit = item.low <= stop_price if direction == 1 else item.high >= stop_price
            target_hit = (
                item.high >= target_price if direction == 1 else item.low <= target_price
            )
            if stop_hit:
                exit_index = index
                exit_price = stop_price
                exit_reason = "stop"
                break
            if target_hit:
                exit_index = index
                exit_price = target_price
                exit_reason = "target"
                break

        gross_pnl = direction * (exit_price - entry_price) * quantity
        cost = _trade_cost(
            entry_price,
            exit_price,
            quantity,
            parameters.side_cost_bps,
        )
        entry_notional = entry_price * quantity
        return HistoricalTrade(
            symbol=symbol,
            trading_date=trading_date,
            side="BUY" if direction == 1 else "SELL",
            entry_at=entry_bar.timestamp,
            exit_at=bars[exit_index].timestamp,
            entry_price=entry_price,
            exit_price=exit_price,
            stop_price=stop_price,
            target_price=target_price,
            quantity=quantity,
            exit_reason=exit_reason,
            gross_pnl=gross_pnl,
            cost=cost,
            net_pnl=gross_pnl - cost,
            gross_return=gross_pnl / entry_notional,
            net_return=(gross_pnl - cost) / entry_notional,
        )


class HistoricalOrbWalkForward:
    def __init__(self, backtester: HistoricalOrbBacktester | None = None) -> None:
        self.backtester = backtester or HistoricalOrbBacktester()

    def run(
        self,
        bars: Sequence[HistoricalBar],
        candidates: Sequence[OrbResearchParameters],
        config: WalkForwardConfig,
    ) -> WalkForwardResult:
        folds = build_walk_forward_folds(
            (item.timestamp.date() for item in bars), config
        )
        results = []
        for fold in folds:
            train_dates = set(fold.train_dates)
            test_dates = set(fold.test_dates)
            train_bars = [
                item for item in bars if item.timestamp.date() in train_dates
            ]
            test_bars = [item for item in bars if item.timestamp.date() in test_dates]
            evaluated = []
            eligible = []
            for candidate in candidates:
                result = self.backtester.run(train_bars, candidate)
                evaluated.append(result)
                profit_factor = result.metrics.profit_factor
                if (
                    result.metrics.trade_count >= config.min_trades
                    and result.metrics.daily_sharpe >= config.min_train_sharpe
                    and (
                        profit_factor is None
                        or profit_factor >= config.min_train_profit_factor
                    )
                ):
                    eligible.append(result)
            ranking = lambda result: (
                result.metrics.daily_sharpe,
                result.metrics.mean_net_bps,
                result.parameters.key,
            )
            best_observed = max(evaluated, key=ranking) if evaluated else None
            if not eligible:
                results.append(
                    WalkForwardFoldResult(
                        fold=fold,
                        evaluated_candidate_count=len(evaluated),
                        eligible_candidate_count=0,
                        best_observed_parameters=(
                            best_observed.parameters if best_observed is not None else None
                        ),
                        best_observed_train_metrics=(
                            best_observed.metrics if best_observed is not None else None
                        ),
                        selected_parameters=None,
                        train_metrics=None,
                        test_metrics=None,
                    )
                )
                continue
            selected = max(eligible, key=ranking)
            test_result = self.backtester.run(test_bars, selected.parameters)
            results.append(
                WalkForwardFoldResult(
                    fold=fold,
                    evaluated_candidate_count=len(evaluated),
                    eligible_candidate_count=len(eligible),
                    best_observed_parameters=(
                        best_observed.parameters if best_observed is not None else None
                    ),
                    best_observed_train_metrics=(
                        best_observed.metrics if best_observed is not None else None
                    ),
                    selected_parameters=selected.parameters,
                    train_metrics=selected.metrics,
                    test_metrics=test_result.metrics,
                )
            )
        return WalkForwardResult(tuple(results))


class VerifiedHistoricalCsvLoader:
    def read(self, manifest_path: str | Path) -> HistoricalDataset:
        manifest_file = Path(manifest_path)
        try:
            payload = json.loads(manifest_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise HistoricalCacheError("could not read historical cache manifest") from exc
        required = {
            "schema_version",
            "artifact",
            "format",
            "sha256",
            "row_count",
            "bar_size",
            "session",
            "rehab",
            "date_start",
            "date_end",
            "symbols",
            "columns",
        }
        if not isinstance(payload, dict) or not required.issubset(payload):
            raise HistoricalCacheError("invalid historical cache manifest fields")
        self._validate_manifest(payload)

        artifact_name = payload["artifact"]
        artifact = manifest_file.parent / artifact_name
        if artifact.parent != manifest_file.parent or artifact.is_symlink():
            raise HistoricalCacheError("historical cache artifact must be adjacent")
        digest = _sha256(artifact)
        if digest != payload["sha256"]:
            raise HistoricalCacheError("historical cache SHA-256 mismatch")

        try:
            with gzip.open(artifact, "rt", encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                if tuple(reader.fieldnames or ()) != HISTORICAL_CACHE_COLUMNS:
                    raise HistoricalCacheError("invalid historical cache columns")
                bars = tuple(_parse_bar(row) for row in reader)
        except HistoricalCacheError:
            raise
        except (OSError, UnicodeError, ValueError) as exc:
            raise HistoricalCacheError("could not read historical cache artifact") from exc

        if len(bars) != payload["row_count"]:
            raise HistoricalCacheError("historical cache row count mismatch")
        symbols = tuple(sorted({item.symbol for item in bars}))
        if symbols != tuple(payload["symbols"]):
            raise HistoricalCacheError("historical cache symbol set mismatch")
        dates = [item.timestamp.date() for item in bars]
        if not dates or min(dates).isoformat() != payload["date_start"] or max(
            dates
        ).isoformat() != payload["date_end"]:
            raise HistoricalCacheError("historical cache date range mismatch")
        return HistoricalDataset(
            bars=tuple(sorted(bars, key=lambda item: (item.symbol, item.timestamp))),
            symbols=symbols,
            bar_size=payload["bar_size"],
            session=payload["session"],
            date_start=min(dates),
            date_end=max(dates),
            sha256=digest,
        )

    @staticmethod
    def _validate_manifest(payload: Mapping[str, object]) -> None:
        artifact = payload["artifact"]
        if (
            type(payload["schema_version"]) is not int
            or payload["schema_version"] != HISTORICAL_CACHE_SCHEMA_VERSION
            or not isinstance(artifact, str)
            or Path(artifact).name != artifact
            or not artifact.endswith(".csv.gz")
            or payload["format"] != "gzip-csv"
            or not isinstance(payload["sha256"], str)
            or len(payload["sha256"]) != 64
            or type(payload["row_count"]) is not int
            or payload["row_count"] <= 0
            or payload["bar_size"] != "5m"
            or payload["session"] != "RTH"
            or payload["rehab"] != "none"
            or payload["columns"] != list(HISTORICAL_CACHE_COLUMNS)
        ):
            raise HistoricalCacheError("invalid historical cache manifest payload")
        try:
            int(payload["sha256"], 16)
            start = date.fromisoformat(payload["date_start"])
            end = date.fromisoformat(payload["date_end"])
        except (TypeError, ValueError) as exc:
            raise HistoricalCacheError("invalid historical cache manifest payload") from exc
        symbols = payload["symbols"]
        if (
            start > end
            or not isinstance(symbols, list)
            or not symbols
            or any(not isinstance(symbol, str) or not symbol for symbol in symbols)
            or symbols != sorted(set(symbols))
        ):
            raise HistoricalCacheError("invalid historical cache manifest payload")


class HistoricalOrbReportWriter:
    def write(self, path: str | Path, report: Mapping[str, object]) -> Path:
        output = Path(path)
        temporary: Path | None = None
        try:
            content = json.dumps(
                report, sort_keys=True, indent=2, allow_nan=False
            ) + "\n"
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=output.parent,
                prefix=f".{output.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, output)
        except FileExistsError as exc:
            raise HistoricalCacheError(
                f"historical ORB report already exists: {output}"
            ) from exc
        except (OSError, TypeError, ValueError) as exc:
            raise HistoricalCacheError("could not write historical ORB report") from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        return output


def default_orb_candidates(
    side_cost_bps: float = 2.5,
) -> tuple[OrbResearchParameters, ...]:
    base = OrbResearchParameters(side_cost_bps=side_cost_bps)
    return (
        base,
        replace(base, opening_range_minutes=30),
        replace(base, min_relative_volume=1.2),
        replace(base, min_relative_volume=2.0),
        replace(base, breakout_buffer_atr=0.0),
        replace(base, breakout_buffer_atr=0.1),
        replace(base, opening_range_stop_fraction=0.35),
        replace(base, opening_range_stop_fraction=0.75),
        replace(base, target_r_multiple=1.0),
        replace(base, target_r_multiple=2.0),
        replace(base, max_holding_minutes=60),
    )


def _parse_bar(row: Mapping[str, str]) -> HistoricalBar:
    try:
        volume = int(row["volume"])
        return HistoricalBar(
            symbol=row["symbol"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=volume,
            turnover=float(row["turnover"]),
            atr=float(row["atr"]),
            vwap=float(row["vwap"]),
            relative_volume=float(row["relative_volume"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HistoricalCacheError("invalid historical cache row") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise HistoricalCacheError("could not read historical cache artifact") from exc
    return digest.hexdigest()


def _trade_cost(
    entry_price: float,
    exit_price: float,
    quantity: int,
    side_cost_bps: float,
) -> float:
    return (entry_price + exit_price) * quantity * side_cost_bps / 10_000


def _calculate_metrics(
    trades: Sequence[HistoricalTrade],
    side_cost_bps: float,
    symbol_count: int,
) -> PerformanceMetrics:
    if not trades:
        return PerformanceMetrics(0, 0.0, 0.0, None, 0.0, 0.0, 0.0, 0.0)
    net_pnls = []
    net_returns = []
    daily_returns: dict[date, float] = defaultdict(float)
    for trade in trades:
        cost = _trade_cost(
            trade.entry_price, trade.exit_price, trade.quantity, side_cost_bps
        )
        net_pnl = trade.gross_pnl - cost
        net_return = net_pnl / (trade.entry_price * trade.quantity)
        net_pnls.append(net_pnl)
        net_returns.append(net_return)
        daily_returns[trade.trading_date] += net_return / symbol_count

    wins = [value for value in net_pnls if value > 0]
    losses = [value for value in net_pnls if value < 0]
    profit_factor = sum(wins) / -sum(losses) if losses else None
    ordered_daily = [daily_returns[item] for item in sorted(daily_returns)]
    daily_sharpe = 0.0
    if len(ordered_daily) > 1 and stdev(ordered_daily) > 0:
        daily_sharpe = math.sqrt(252) * mean(ordered_daily) / stdev(ordered_daily)
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in ordered_daily:
        equity *= 1 + value
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1)
    return PerformanceMetrics(
        trade_count=len(trades),
        win_rate=round(len(wins) / len(trades), 6),
        mean_net_bps=round(mean(net_returns) * 10_000, 6),
        profit_factor=(round(profit_factor, 6) if profit_factor is not None else None),
        daily_sharpe=round(daily_sharpe, 6),
        max_drawdown_pct=round(max_drawdown * 100, 6),
        total_return_pct=round((equity - 1) * 100, 6),
        total_net_pnl=round(sum(net_pnls), 6),
    )
