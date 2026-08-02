from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from autotrade.backtest.historical import (
    HistoricalBar,
    OrbResearchParameters,
    WalkForwardConfig,
)
from autotrade.backtest.tuning import (
    HistoricalOrbParameterTuner,
    OrbTuningConfig,
    bounded_orb_candidates,
)


def bar(
    minute: int,
    *,
    day: int,
    symbol: str = "US.TEST",
    open_price: float = 95.0,
    high: float = 99.0,
    low: float = 91.0,
    close: float = 95.0,
    atr: float = 10.0,
    vwap: float = 95.0,
    rvol: float = 2.0,
) -> HistoricalBar:
    return HistoricalBar(
        symbol=symbol,
        timestamp=datetime(2026, 1, day, 9, 35) + timedelta(minutes=minute),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=1_000,
        turnover=95_000.0,
        atr=atr,
        vwap=vwap,
        relative_volume=rvol,
    )


def winning_day(
    day: int,
    *,
    symbol: str = "US.TEST",
    rvol: float = 2.0,
) -> list[HistoricalBar]:
    return [
        bar(0, day=day, symbol=symbol, high=98, low=90, close=95, rvol=rvol),
        bar(5, day=day, symbol=symbol, high=100, low=92, close=98, rvol=rvol),
        bar(10, day=day, symbol=symbol, high=99, low=93, close=97, rvol=rvol),
        bar(
            15,
            day=day,
            symbol=symbol,
            open_price=100,
            high=102,
            low=99,
            close=101,
            vwap=98,
            rvol=rvol,
        ),
        bar(
            20,
            day=day,
            symbol=symbol,
            open_price=102,
            high=103,
            low=101,
            close=102,
            rvol=rvol,
        ),
        bar(
            25,
            day=day,
            symbol=symbol,
            open_price=102,
            high=110,
            low=101,
            close=109,
            rvol=rvol,
        ),
    ]


def tuning_config(**overrides: object) -> OrbTuningConfig:
    values: dict[str, object] = {
        "outer_walk_forward": WalkForwardConfig(
            train_days=4,
            test_days=2,
            step_days=2,
            min_trades=0,
        ),
        "inner_train_days": 2,
        "inner_validation_days": 1,
        "inner_step_days": 1,
        "min_validation_trades": 2,
        "min_validation_sharpe": -100.0,
        "min_validation_profit_factor": 0.0,
        "min_double_cost_mean_net_bps": -1000.0,
        "min_worst_fold_mean_net_bps": -1000.0,
        "max_positive_symbol_share": 1.0,
        "min_positive_neighbors": 0,
        "min_outer_test_trades": 0,
        "min_outer_test_sharpe": -100.0,
        "min_outer_test_profit_factor": 0.0,
        "min_outer_double_cost_mean_net_bps": -1000.0,
        "require_all_outer_folds_positive": False,
    }
    values.update(overrides)
    return OrbTuningConfig(**values)


class CandidateGridTests(unittest.TestCase):
    def test_bounded_grid_is_deterministic_unique_and_long_only(self) -> None:
        first = bounded_orb_candidates(side_cost_bps=2.5)
        second = bounded_orb_candidates(side_cost_bps=2.5)

        self.assertEqual(first, second)
        self.assertEqual(96, len(first))
        self.assertEqual(96, len({candidate.key for candidate in first}))
        self.assertTrue(all(candidate.long_only for candidate in first))


class NestedTuningTests(unittest.TestCase):
    def test_outer_test_behavior_cannot_select_a_candidate(self) -> None:
        bars = []
        for day in range(1, 9):
            bars.extend(winning_day(day, rvol=2.0 if day <= 4 else 3.0))
        training_candidate = OrbResearchParameters(min_relative_volume=1.5)
        outer_test_only_candidate = OrbResearchParameters(min_relative_volume=2.5)

        result = HistoricalOrbParameterTuner().run(
            bars,
            [training_candidate, outer_test_only_candidate],
            tuning_config(),
        )

        first = result.folds[0]
        self.assertEqual(training_candidate, first.selected_parameters)
        self.assertEqual(0, first.candidate_evaluations[1].validation_metrics.trade_count)
        self.assertEqual(2, first.outer_test_result.metrics.trade_count)

    def test_double_cost_gate_rejects_an_expensive_candidate(self) -> None:
        bars = [item for day in range(1, 7) for item in winning_day(day)]
        expensive = OrbResearchParameters(side_cost_bps=500.0)

        result = HistoricalOrbParameterTuner().run(
            bars,
            [expensive],
            tuning_config(min_double_cost_mean_net_bps=0.0),
        )

        evaluation = result.folds[0].candidate_evaluations[0]
        self.assertIn("double_cost_mean_net_bps", evaluation.rejection_reasons)
        self.assertFalse(evaluation.eligible)
        self.assertIsNone(result.folds[0].selected_parameters)

    def test_symbol_concentration_gate_rejects_single_symbol_profit(self) -> None:
        bars = []
        for day in range(1, 7):
            bars.extend(winning_day(day))
            bars.extend(winning_day(day, symbol="US.NO_SIGNAL", rvol=0.5))

        result = HistoricalOrbParameterTuner().run(
            bars,
            [OrbResearchParameters()],
            tuning_config(max_positive_symbol_share=0.6),
        )

        evaluation = result.folds[0].candidate_evaluations[0]
        self.assertEqual(1.0, evaluation.max_positive_symbol_share)
        self.assertIn("positive_symbol_concentration", evaluation.rejection_reasons)

    def test_neighbor_stability_requires_an_adjacent_positive_candidate(self) -> None:
        bars = [item for day in range(1, 7) for item in winning_day(day)]
        first = OrbResearchParameters(min_relative_volume=1.5)
        neighbor = OrbResearchParameters(min_relative_volume=1.75)

        result = HistoricalOrbParameterTuner().run(
            bars,
            [first, neighbor],
            tuning_config(min_positive_neighbors=1),
        )

        evaluations = result.folds[0].candidate_evaluations
        self.assertTrue(all(item.positive_neighbor_count == 1 for item in evaluations))
        self.assertTrue(all(item.eligible for item in evaluations))
        self.assertEqual({1, 2}, {item.robustness_rank for item in evaluations})

    def test_aggregate_contains_only_non_overlapping_outer_test_trades(self) -> None:
        bars = [item for day in range(1, 9) for item in winning_day(day)]

        result = HistoricalOrbParameterTuner().run(
            bars,
            [OrbResearchParameters()],
            tuning_config(),
        )

        self.assertEqual(4, result.aggregate_outer_test.metrics.trade_count)
        self.assertEqual(
            {5, 6, 7, 8},
            {trade.trading_date.day for trade in result.aggregate_outer_test.trades},
        )
        self.assertEqual(
            {"zero", "baseline", "double"},
            set(result.aggregate_outer_test.cost_scenarios),
        )
        self.assertEqual("candidate", result.decision)
        self.assertEqual((), result.decision_reasons)

    def test_no_selected_fold_produces_explicit_no_go_decision(self) -> None:
        bars = [item for day in range(1, 7) for item in winning_day(day)]

        result = HistoricalOrbParameterTuner().run(
            bars,
            [OrbResearchParameters(side_cost_bps=500.0)],
            tuning_config(min_double_cost_mean_net_bps=0.0),
        )

        self.assertEqual("no-go", result.decision)
        self.assertIn("outer_fold_without_candidate", result.decision_reasons)


if __name__ == "__main__":
    unittest.main()
