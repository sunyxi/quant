from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import date
from itertools import product
from typing import Callable, Mapping, Sequence

from autotrade.backtest.historical import (
    HistoricalBacktestResult,
    HistoricalBar,
    HistoricalOrbBacktester,
    HistoricalTrade,
    OrbResearchParameters,
    PerformanceMetrics,
    WalkForwardConfig,
    WalkForwardFold,
    build_walk_forward_folds,
    calculate_performance_metrics,
)


HISTORICAL_TUNING_REPORT_SCHEMA_VERSION = 3
MAX_BOUNDED_ORB_CANDIDATES = 96


@dataclass(frozen=True)
class OrbTuningConfig:
    outer_walk_forward: WalkForwardConfig = WalkForwardConfig()
    inner_train_days: int = 60
    inner_validation_days: int = 20
    inner_step_days: int = 20
    min_validation_trades: int = 20
    min_validation_sharpe: float = 0.0
    min_validation_profit_factor: float = 1.0
    min_double_cost_mean_net_bps: float = 0.0
    min_worst_fold_mean_net_bps: float = 0.0
    max_positive_symbol_share: float = 0.6
    min_positive_neighbors: int = 1
    min_outer_test_trades: int = 20
    min_outer_test_sharpe: float = 0.8
    min_outer_test_profit_factor: float = 1.1
    min_outer_double_cost_mean_net_bps: float = 0.0
    require_all_outer_folds_positive: bool = True
    max_candidates: int = MAX_BOUNDED_ORB_CANDIDATES

    def __post_init__(self) -> None:
        if min(
            self.inner_train_days,
            self.inner_validation_days,
            self.inner_step_days,
        ) <= 0:
            raise ValueError("inner tuning windows must be positive")
        if self.inner_step_days < self.inner_validation_days:
            raise ValueError("inner tuning validation windows must not overlap")
        if self.inner_step_days > self.inner_train_days:
            raise ValueError("inner tuning training coverage must not contain gaps")
        if (
            self.inner_train_days + self.inner_validation_days
            > self.outer_walk_forward.train_days
        ):
            raise ValueError("inner tuning windows must fit inside outer training")
        if min(
            self.min_validation_trades,
            self.min_positive_neighbors,
            self.min_outer_test_trades,
        ) < 0:
            raise ValueError("tuning count thresholds must be non-negative")
        thresholds = (
            self.min_validation_sharpe,
            self.min_validation_profit_factor,
            self.min_double_cost_mean_net_bps,
            self.min_worst_fold_mean_net_bps,
            self.max_positive_symbol_share,
            self.min_outer_test_sharpe,
            self.min_outer_test_profit_factor,
            self.min_outer_double_cost_mean_net_bps,
        )
        if any(not math.isfinite(value) for value in thresholds):
            raise ValueError("tuning thresholds must be finite")
        if min(
            self.min_validation_profit_factor,
            self.min_outer_test_profit_factor,
        ) < 0:
            raise ValueError("tuning profit factor must be non-negative")
        if not 0 < self.max_positive_symbol_share <= 1:
            raise ValueError("positive symbol share must be in (0, 1]")
        if type(self.max_candidates) is not int or not 0 < self.max_candidates <= 512:
            raise ValueError("tuning candidate limit must be between 1 and 512")
        if type(self.require_all_outer_folds_positive) is not bool:
            raise ValueError("outer fold positivity setting must be boolean")


@dataclass(frozen=True)
class OrbCandidateEvaluation:
    parameters: OrbResearchParameters
    validation_metrics: PerformanceMetrics
    double_cost_metrics: PerformanceMetrics
    worst_fold_mean_net_bps: float
    max_positive_symbol_share: float
    positive_neighbor_count: int
    robustness_rank: int
    eligible: bool
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "parameters": asdict(self.parameters),
            "validation_metrics": asdict(self.validation_metrics),
            "double_cost_metrics": asdict(self.double_cost_metrics),
            "worst_fold_mean_net_bps": self.worst_fold_mean_net_bps,
            "max_positive_symbol_share": self.max_positive_symbol_share,
            "positive_neighbor_count": self.positive_neighbor_count,
            "robustness_rank": self.robustness_rank,
            "eligible": self.eligible,
            "rejection_reasons": list(self.rejection_reasons),
        }


@dataclass(frozen=True)
class OrbTuningFoldResult:
    fold: WalkForwardFold
    candidate_evaluations: tuple[OrbCandidateEvaluation, ...]
    selected_parameters: OrbResearchParameters | None
    selected_validation_metrics: PerformanceMetrics | None
    outer_test_result: HistoricalBacktestResult | None

    def to_dict(self) -> dict[str, object]:
        return {
            "train_start": self.fold.train_start.isoformat(),
            "train_end": self.fold.train_end.isoformat(),
            "test_start": self.fold.test_start.isoformat(),
            "test_end": self.fold.test_end.isoformat(),
            "candidate_evaluations": [
                item.to_dict() for item in self.candidate_evaluations
            ],
            "selected_parameters": (
                asdict(self.selected_parameters)
                if self.selected_parameters is not None
                else None
            ),
            "selected_validation_metrics": (
                asdict(self.selected_validation_metrics)
                if self.selected_validation_metrics is not None
                else None
            ),
            "outer_test_result": (
                self.outer_test_result.to_dict()
                if self.outer_test_result is not None
                else None
            ),
        }


@dataclass(frozen=True)
class OrbTuningAggregateResult:
    trades: tuple[HistoricalTrade, ...]
    trading_date_count: int
    metrics: PerformanceMetrics
    by_symbol: Mapping[str, PerformanceMetrics]
    cost_scenarios: Mapping[str, PerformanceMetrics]

    def to_dict(self) -> dict[str, object]:
        return {
            "trades": [trade.to_dict() for trade in self.trades],
            "trading_date_count": self.trading_date_count,
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
class OrbTuningResult:
    config: OrbTuningConfig
    candidate_count: int
    folds: tuple[OrbTuningFoldResult, ...]
    aggregate_outer_test: OrbTuningAggregateResult
    decision: str
    decision_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        config = asdict(self.config)
        return {
            "config": config,
            "candidate_count": self.candidate_count,
            "folds": [fold.to_dict() for fold in self.folds],
            "aggregate_outer_test": self.aggregate_outer_test.to_dict(),
            "decision": self.decision,
            "decision_reasons": list(self.decision_reasons),
        }


def bounded_orb_candidates(
    side_cost_bps: float = 2.5,
) -> tuple[OrbResearchParameters, ...]:
    candidates = tuple(
        OrbResearchParameters(
            opening_range_minutes=opening_range_minutes,
            min_relative_volume=min_relative_volume,
            breakout_buffer_atr=breakout_buffer_atr,
            opening_range_stop_fraction=opening_range_stop_fraction,
            target_r_multiple=target_r_multiple,
            max_holding_minutes=max_holding_minutes,
            side_cost_bps=side_cost_bps,
        )
        for (
            opening_range_minutes,
            min_relative_volume,
            breakout_buffer_atr,
            opening_range_stop_fraction,
            target_r_multiple,
            max_holding_minutes,
        ) in product(
            (15, 30),
            (1.2, 1.5, 2.0),
            (0.0, 0.05),
            (0.35, 0.5),
            (1.0, 1.5),
            (30, 60),
        )
    )
    if len(candidates) != MAX_BOUNDED_ORB_CANDIDATES:
        raise AssertionError("bounded ORB candidate count changed")
    return candidates


class HistoricalOrbParameterTuner:
    def __init__(self, backtester: HistoricalOrbBacktester | None = None) -> None:
        self.backtester = backtester or HistoricalOrbBacktester()

    def run(
        self,
        bars: Sequence[HistoricalBar],
        candidates: Sequence[OrbResearchParameters],
        config: OrbTuningConfig,
    ) -> OrbTuningResult:
        ordered_candidates = tuple(sorted(candidates, key=lambda item: item.key))
        self._validate_candidates(ordered_candidates, config)
        symbols = tuple(sorted({item.symbol for item in bars}))
        symbol_count = max(len(symbols), 1)
        side_cost_bps = ordered_candidates[0].side_cost_bps
        bars_by_date: dict[date, list[HistoricalBar]] = defaultdict(list)
        for item in bars:
            bars_by_date[item.timestamp.date()].append(item)

        def bars_for(dates: Sequence[date]) -> list[HistoricalBar]:
            return [item for day in dates for item in bars_by_date.get(day, ())]

        outer_folds = build_walk_forward_folds(
            bars_by_date, config.outer_walk_forward
        )
        fold_results = []
        aggregate_trades = []
        aggregate_dates = []
        for outer_fold in outer_folds:
            aggregate_dates.extend(outer_fold.test_dates)
            inner_config = WalkForwardConfig(
                train_days=config.inner_train_days,
                test_days=config.inner_validation_days,
                step_days=config.inner_step_days,
                min_trades=0,
                min_train_sharpe=-1_000_000.0,
                min_train_profit_factor=0.0,
            )
            inner_folds = build_walk_forward_folds(
                outer_fold.train_dates, inner_config
            )
            evaluations = [
                self._evaluate_candidate(
                    candidate,
                    inner_folds,
                    bars_for,
                    symbols,
                    config,
                )
                for candidate in ordered_candidates
            ]
            evaluations = self._apply_neighbor_gate(evaluations, config)
            eligible = [item for item in evaluations if item.eligible]
            selected = max(eligible, key=self._ranking) if eligible else None
            outer_test_result = None
            if selected is not None:
                outer_test_result = self.backtester.run(
                    bars_for(outer_fold.test_dates), selected.parameters
                )
                aggregate_trades.extend(outer_test_result.trades)
            fold_results.append(
                OrbTuningFoldResult(
                    fold=outer_fold,
                    candidate_evaluations=tuple(evaluations),
                    selected_parameters=(
                        selected.parameters if selected is not None else None
                    ),
                    selected_validation_metrics=(
                        selected.validation_metrics if selected is not None else None
                    ),
                    outer_test_result=outer_test_result,
                )
            )

        aggregate = self._aggregate(
            tuple(sorted(aggregate_trades, key=lambda item: item.entry_at)),
            symbols,
            side_cost_bps,
            symbol_count,
            tuple(aggregate_dates),
        )
        decision_reasons = self._decision_reasons(
            fold_results, aggregate, config
        )
        return OrbTuningResult(
            config=config,
            candidate_count=len(ordered_candidates),
            folds=tuple(fold_results),
            aggregate_outer_test=aggregate,
            decision="no-go" if decision_reasons else "candidate",
            decision_reasons=decision_reasons,
        )

    def _evaluate_candidate(
        self,
        candidate: OrbResearchParameters,
        inner_folds: Sequence[WalkForwardFold],
        bars_for: Callable[[Sequence[date]], list[HistoricalBar]],
        symbols: Sequence[str],
        config: OrbTuningConfig,
    ) -> OrbCandidateEvaluation:
        validation_trades = []
        fold_mean_bps = []
        validation_dates = []
        for fold in inner_folds:
            validation_dates.extend(fold.test_dates)
            result = self.backtester.run(bars_for(fold.test_dates), candidate)
            validation_trades.extend(result.trades)
            fold_mean_bps.append(result.metrics.mean_net_bps)
        trades = tuple(sorted(validation_trades, key=lambda item: item.entry_at))
        symbol_count = max(len(symbols), 1)
        metrics = calculate_performance_metrics(
            trades,
            candidate.side_cost_bps,
            symbol_count,
            trading_dates=validation_dates,
        )
        double_cost_metrics = calculate_performance_metrics(
            trades,
            candidate.side_cost_bps * 2,
            symbol_count,
            trading_dates=validation_dates,
        )
        by_symbol = {
            symbol: calculate_performance_metrics(
                tuple(item for item in trades if item.symbol == symbol),
                candidate.side_cost_bps,
                1,
                trading_dates=validation_dates,
            )
            for symbol in symbols
        }
        positive_pnls = [
            item.total_net_pnl for item in by_symbol.values() if item.total_net_pnl > 0
        ]
        max_positive_symbol_share = (
            max(positive_pnls) / sum(positive_pnls) if positive_pnls else 1.0
        )
        reasons = []
        if metrics.trade_count < config.min_validation_trades:
            reasons.append("validation_trade_count")
        if metrics.daily_sharpe < config.min_validation_sharpe:
            reasons.append("validation_sharpe")
        if (
            metrics.profit_factor is not None
            and metrics.profit_factor < config.min_validation_profit_factor
        ):
            reasons.append("validation_profit_factor")
        if (
            double_cost_metrics.mean_net_bps
            < config.min_double_cost_mean_net_bps
        ):
            reasons.append("double_cost_mean_net_bps")
        worst_fold_mean_net_bps = min(fold_mean_bps, default=0.0)
        if worst_fold_mean_net_bps < config.min_worst_fold_mean_net_bps:
            reasons.append("worst_inner_fold_mean_net_bps")
        if max_positive_symbol_share > config.max_positive_symbol_share:
            reasons.append("positive_symbol_concentration")
        return OrbCandidateEvaluation(
            parameters=candidate,
            validation_metrics=metrics,
            double_cost_metrics=double_cost_metrics,
            worst_fold_mean_net_bps=worst_fold_mean_net_bps,
            max_positive_symbol_share=round(max_positive_symbol_share, 6),
            positive_neighbor_count=0,
            robustness_rank=0,
            eligible=False,
            rejection_reasons=tuple(reasons),
        )

    @staticmethod
    def _apply_neighbor_gate(
        evaluations: Sequence[OrbCandidateEvaluation],
        config: OrbTuningConfig,
    ) -> list[OrbCandidateEvaluation]:
        base_eligible = [item for item in evaluations if not item.rejection_reasons]
        output = []
        for evaluation in evaluations:
            neighbor_count = sum(
                _are_parameter_neighbors(
                    evaluation.parameters, candidate.parameters
                )
                for candidate in base_eligible
                if candidate.parameters != evaluation.parameters
            )
            reasons = list(evaluation.rejection_reasons)
            if neighbor_count < config.min_positive_neighbors:
                reasons.append("positive_parameter_neighbors")
            output.append(
                replace(
                    evaluation,
                    positive_neighbor_count=neighbor_count,
                    eligible=not reasons,
                    rejection_reasons=tuple(reasons),
                )
            )
        ranked = sorted(output, key=HistoricalOrbParameterTuner._ranking, reverse=True)
        ranks = {
            item.parameters.key: rank
            for rank, item in enumerate(ranked, start=1)
        }
        return [
            replace(item, robustness_rank=ranks[item.parameters.key])
            for item in output
        ]

    @staticmethod
    def _ranking(evaluation: OrbCandidateEvaluation) -> tuple[object, ...]:
        return (
            evaluation.worst_fold_mean_net_bps,
            evaluation.double_cost_metrics.daily_sharpe,
            evaluation.validation_metrics.daily_sharpe,
            evaluation.validation_metrics.mean_net_bps,
            -evaluation.max_positive_symbol_share,
            evaluation.parameters.key,
        )

    @staticmethod
    def _aggregate(
        trades: tuple[HistoricalTrade, ...],
        symbols: Sequence[str],
        side_cost_bps: float,
        symbol_count: int,
        trading_dates: Sequence[date],
    ) -> OrbTuningAggregateResult:
        metrics = calculate_performance_metrics(
            trades,
            side_cost_bps,
            symbol_count,
            trading_dates=trading_dates,
        )
        return OrbTuningAggregateResult(
            trades=trades,
            trading_date_count=len(set(trading_dates)),
            metrics=metrics,
            by_symbol={
                symbol: calculate_performance_metrics(
                    tuple(item for item in trades if item.symbol == symbol),
                    side_cost_bps,
                    1,
                    trading_dates=trading_dates,
                )
                for symbol in symbols
            },
            cost_scenarios={
                "zero": calculate_performance_metrics(
                    trades, 0.0, symbol_count, trading_dates=trading_dates
                ),
                "baseline": metrics,
                "double": calculate_performance_metrics(
                    trades,
                    side_cost_bps * 2,
                    symbol_count,
                    trading_dates=trading_dates,
                ),
            },
        )

    @staticmethod
    def _decision_reasons(
        folds: Sequence[OrbTuningFoldResult],
        aggregate: OrbTuningAggregateResult,
        config: OrbTuningConfig,
    ) -> tuple[str, ...]:
        reasons = []
        if not folds:
            reasons.append("outer_folds_missing")
        if any(fold.selected_parameters is None for fold in folds):
            reasons.append("outer_fold_without_candidate")
        if aggregate.metrics.trade_count < config.min_outer_test_trades:
            reasons.append("outer_test_trade_count")
        if aggregate.metrics.daily_sharpe < config.min_outer_test_sharpe:
            reasons.append("outer_test_sharpe")
        if (
            aggregate.metrics.profit_factor is not None
            and aggregate.metrics.profit_factor
            < config.min_outer_test_profit_factor
        ):
            reasons.append("outer_test_profit_factor")
        if (
            aggregate.cost_scenarios["double"].mean_net_bps
            < config.min_outer_double_cost_mean_net_bps
        ):
            reasons.append("outer_double_cost_mean_net_bps")
        positive_pnls = [
            item.total_net_pnl
            for item in aggregate.by_symbol.values()
            if item.total_net_pnl > 0
        ]
        positive_share = (
            max(positive_pnls) / sum(positive_pnls) if positive_pnls else 1.0
        )
        if positive_share > config.max_positive_symbol_share:
            reasons.append("outer_positive_symbol_concentration")
        if config.require_all_outer_folds_positive and any(
            fold.outer_test_result is None
            or fold.outer_test_result.metrics.mean_net_bps <= 0
            for fold in folds
        ):
            reasons.append("non_positive_outer_fold")
        return tuple(reasons)

    @staticmethod
    def _validate_candidates(
        candidates: Sequence[OrbResearchParameters],
        config: OrbTuningConfig,
    ) -> None:
        if not candidates:
            raise ValueError("ORB tuning requires at least one candidate")
        if len(candidates) > config.max_candidates:
            raise ValueError("ORB tuning candidate limit exceeded")
        if len({item.key for item in candidates}) != len(candidates):
            raise ValueError("ORB tuning candidates must have unique keys")
        if len({item.side_cost_bps for item in candidates}) != 1:
            raise ValueError("ORB tuning candidates must use one side-cost assumption")


def _are_parameter_neighbors(
    left: OrbResearchParameters,
    right: OrbResearchParameters,
) -> bool:
    fixed_equal = (
        left.side_cost_bps == right.side_cost_bps
        and left.notional_per_trade == right.notional_per_trade
        and left.long_only == right.long_only
    )
    if not fixed_equal:
        return False
    dimensions = (
        "opening_range_minutes",
        "min_relative_volume",
        "breakout_buffer_atr",
        "daily_atr_stop_multiple",
        "opening_range_stop_fraction",
        "target_r_multiple",
        "max_holding_minutes",
    )
    return sum(getattr(left, field) != getattr(right, field) for field in dimensions) == 1
