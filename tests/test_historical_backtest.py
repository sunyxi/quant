from __future__ import annotations

import csv
import gzip
import hashlib
import json
import tempfile
import unittest
import io
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, timedelta
from pathlib import Path

from autotrade.backtest.historical import (
    HistoricalBar,
    HistoricalCacheError,
    HistoricalOrbBacktester,
    HistoricalOrbReportWriter,
    HistoricalOrbWalkForward,
    OrbResearchParameters,
    VerifiedHistoricalCsvLoader,
    WalkForwardConfig,
    build_walk_forward_folds,
)
from autotrade.cli import main
from unittest.mock import patch


def bar(
    minute: int,
    *,
    symbol: str = "US.TEST",
    day: int = 1,
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


def target_fixture(
    *, ambiguous: bool = False, day: int = 1, rvol: float = 2.0
) -> list[HistoricalBar]:
    bars = [
        bar(0, day=day, high=98, low=90, close=95, rvol=rvol),
        bar(5, day=day, high=100, low=92, close=98, rvol=rvol),
        bar(10, day=day, high=99, low=93, close=97, rvol=rvol),
        bar(
            15,
            day=day,
            open_price=100,
            high=102,
            low=99,
            close=101,
            vwap=98,
            rvol=rvol,
        ),
        bar(20, day=day, open_price=102, high=103, low=101, close=102, rvol=rvol),
    ]
    if ambiguous:
        bars.append(
            bar(25, day=day, open_price=102, high=110, low=96, close=105, rvol=rvol)
        )
    else:
        bars.append(
            bar(25, day=day, open_price=102, high=110, low=101, close=109, rvol=rvol)
        )
    return bars


def short_target_fixture() -> list[HistoricalBar]:
    return [
        bar(0, high=98, low=90, close=95),
        bar(5, high=100, low=92, close=98),
        bar(10, high=99, low=93, close=97),
        bar(15, open_price=90, high=91, low=88, close=89, vwap=95),
        bar(20, open_price=88, high=89, low=80, close=81, vwap=90),
    ]


class HistoricalOrbLifecycleTests(unittest.TestCase):
    def test_next_bar_entry_and_target_exit_produce_net_pnl(self) -> None:
        result = HistoricalOrbBacktester().run(
            target_fixture(), OrbResearchParameters(side_cost_bps=2.5)
        )

        self.assertEqual(1, len(result.trades))
        trade = result.trades[0]
        self.assertEqual(datetime(2026, 1, 1, 9, 55), trade.entry_at)
        self.assertEqual("target", trade.exit_reason)
        self.assertEqual(102.0, trade.entry_price)
        self.assertEqual(109.5, trade.exit_price)
        self.assertGreater(trade.gross_pnl, trade.net_pnl)
        self.assertGreater(trade.net_pnl, 0)

    def test_same_bar_stop_and_target_uses_stop_first(self) -> None:
        result = HistoricalOrbBacktester().run(
            target_fixture(ambiguous=True), OrbResearchParameters()
        )

        self.assertEqual("stop", result.trades[0].exit_reason)
        self.assertEqual(97.0, result.trades[0].exit_price)

    def test_last_bar_signal_has_no_lookahead_entry(self) -> None:
        self.assertEqual(
            (),
            HistoricalOrbBacktester().run(
                target_fixture()[:4], OrbResearchParameters()
            ).trades,
        )

    def test_time_and_session_close_exit_every_open_position(self) -> None:
        base = target_fixture()[:5]
        base.extend(
            [
                bar(25, open_price=102, high=103, low=101, close=102.5),
                bar(30, open_price=102.5, high=103, low=101, close=102.25),
            ]
        )
        timed = HistoricalOrbBacktester().run(
            base, OrbResearchParameters(max_holding_minutes=10)
        )
        closed = HistoricalOrbBacktester().run(
            base[:6], OrbResearchParameters(max_holding_minutes=60)
        )

        self.assertEqual("time", timed.trades[0].exit_reason)
        self.assertEqual("session_close", closed.trades[0].exit_reason)

    def test_cost_sensitivity_and_symbol_attribution_are_reported(self) -> None:
        bars = target_fixture() + [
            HistoricalBar(
                **{
                    **item.__dict__,
                    "symbol": "US.OTHER",
                }
            )
            for item in target_fixture()
        ]
        bars.extend(
            HistoricalBar(
                **{
                    **item.__dict__,
                    "symbol": "US.NO_SIGNAL",
                    "relative_volume": 0.5,
                }
            )
            for item in target_fixture()
        )
        result = HistoricalOrbBacktester().run(bars, OrbResearchParameters())

        self.assertEqual({"US.NO_SIGNAL", "US.OTHER", "US.TEST"}, set(result.by_symbol))
        self.assertEqual(0, result.by_symbol["US.NO_SIGNAL"].trade_count)
        self.assertEqual(2, result.metrics.trade_count)
        self.assertGreater(
            result.cost_scenarios["zero"].mean_net_bps,
            result.cost_scenarios["baseline"].mean_net_bps,
        )
        self.assertGreater(
            result.cost_scenarios["baseline"].mean_net_bps,
            result.cost_scenarios["double"].mean_net_bps,
        )

    def test_side_cost_uses_each_execution_legs_actual_notional(self) -> None:
        result = HistoricalOrbBacktester().run(
            target_fixture(), OrbResearchParameters(side_cost_bps=2.5)
        )
        trade = result.trades[0]

        expected = (
            (trade.entry_price + trade.exit_price)
            * trade.quantity
            * 2.5
            / 10_000
        )

        self.assertAlmostEqual(expected, trade.cost)

    def test_stop_uses_signal_bar_atr_without_entry_bar_lookahead(self) -> None:
        bars = target_fixture()
        bars[3] = HistoricalBar(**{**bars[3].__dict__, "atr": 1.0})
        bars[4] = HistoricalBar(**{**bars[4].__dict__, "atr": 100.0})

        result = HistoricalOrbBacktester().run(bars, OrbResearchParameters())

        self.assertAlmostEqual(101.4, result.trades[0].stop_price)

    def test_opted_in_short_trade_uses_short_stop_target_and_pnl(self) -> None:
        result = HistoricalOrbBacktester().run(
            short_target_fixture(), OrbResearchParameters(long_only=False)
        )

        self.assertEqual(1, len(result.trades))
        trade = result.trades[0]
        self.assertEqual("SELL", trade.side)
        self.assertEqual(93.0, trade.stop_price)
        self.assertEqual(80.5, trade.target_price)
        self.assertEqual("target", trade.exit_reason)
        self.assertGreater(trade.gross_pnl, 0)

    def test_sharpe_includes_market_dates_without_a_trade(self) -> None:
        bars = target_fixture(day=1) + target_fixture(day=2, rvol=0.5)

        result = HistoricalOrbBacktester().run(bars, OrbResearchParameters())

        self.assertEqual(1, result.metrics.trade_count)
        self.assertGreater(result.metrics.daily_sharpe, 0.0)


class WalkForwardTests(unittest.TestCase):
    def test_config_rejects_overlapping_test_windows(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlapping test windows"):
            WalkForwardConfig(train_days=100, test_days=20, step_days=10)

    def test_config_rejects_training_coverage_gaps(self) -> None:
        with self.assertRaisesRegex(ValueError, "training coverage"):
            WalkForwardConfig(train_days=20, test_days=10, step_days=40)

    def test_rolling_folds_are_ordered_and_non_overlapping(self) -> None:
        dates = [date(2026, 1, day) for day in range(1, 13)]

        folds = build_walk_forward_folds(
            dates,
            WalkForwardConfig(train_days=5, test_days=2, step_days=2),
        )

        self.assertEqual(3, len(folds))
        for fold in folds:
            self.assertLess(fold.train_end, fold.test_start)
            self.assertEqual(5, len(fold.train_dates))
            self.assertEqual(2, len(fold.test_dates))
        self.assertEqual(date(2026, 1, 6), folds[0].test_start)
        self.assertEqual(date(2026, 1, 8), folds[1].test_start)

    def test_parameter_selection_uses_training_dates_only(self) -> None:
        bars = []
        for day in range(1, 9):
            bars.extend(target_fixture(day=day, rvol=2.0 if day <= 4 else 3.0))
        conservative = OrbResearchParameters(min_relative_volume=1.5)
        test_only_candidate = OrbResearchParameters(min_relative_volume=2.5)

        result = HistoricalOrbWalkForward().run(
            bars,
            [conservative, test_only_candidate],
            WalkForwardConfig(train_days=4, test_days=2, step_days=2, min_trades=2),
        )

        first = result.folds[0]
        self.assertEqual(1.5, first.selected_parameters.min_relative_volume)
        self.assertEqual(date(2026, 1, 5), first.fold.test_start)
        self.assertEqual(2, first.test_metrics.trade_count)

    def test_negative_training_candidates_are_not_promoted(self) -> None:
        bars = []
        for day in range(1, 9):
            bars.extend(target_fixture(day=day, ambiguous=True))

        result = HistoricalOrbWalkForward().run(
            bars,
            [OrbResearchParameters()],
            WalkForwardConfig(
                train_days=4,
                test_days=2,
                step_days=2,
                min_trades=2,
                min_train_sharpe=0.0,
                min_train_profit_factor=1.0,
            ),
        )

        self.assertIsNone(result.folds[0].selected_parameters)
        self.assertIsNone(result.folds[0].test_metrics)
        self.assertEqual(1, result.folds[0].evaluated_candidate_count)
        self.assertEqual(0, result.folds[0].eligible_candidate_count)
        self.assertIsNotNone(result.folds[0].best_observed_parameters)
        self.assertLess(result.folds[0].best_observed_train_metrics.profit_factor, 1.0)


class HistoricalCacheTests(unittest.TestCase):
    fields = [
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
    ]

    def write_cache(self, root: Path) -> tuple[Path, Path]:
        cache = root / "bars.csv.gz"
        with gzip.open(cache, "wt", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.fields)
            writer.writeheader()
            for item in target_fixture():
                writer.writerow(
                    {
                        "timestamp": item.timestamp.isoformat(),
                        "symbol": item.symbol,
                        "open": item.open,
                        "high": item.high,
                        "low": item.low,
                        "close": item.close,
                        "volume": item.volume,
                        "turnover": item.turnover,
                        "atr": item.atr,
                        "vwap": item.vwap,
                        "relative_volume": item.relative_volume,
                    }
                )
        digest = hashlib.sha256(cache.read_bytes()).hexdigest()
        manifest = root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "artifact": cache.name,
                    "format": "gzip-csv",
                    "sha256": digest,
                    "row_count": len(target_fixture()),
                    "bar_size": "5m",
                    "session": "RTH",
                    "rehab": "none",
                    "date_start": "2026-01-01",
                    "date_end": "2026-01-01",
                    "symbols": ["US.TEST"],
                    "columns": self.fields,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return manifest, cache

    def test_verified_loader_reads_exact_manifest_and_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest, _ = self.write_cache(Path(tmpdir))

            dataset = VerifiedHistoricalCsvLoader().read(manifest)

        self.assertEqual(6, len(dataset.bars))
        self.assertEqual(("US.TEST",), dataset.symbols)
        self.assertEqual("5m", dataset.bar_size)

    def test_manifest_allows_additive_metadata_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest, _ = self.write_cache(Path(tmpdir))
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["created_at"] = "2026-08-02T00:00:00Z"
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            dataset = VerifiedHistoricalCsvLoader().read(manifest)

        self.assertEqual(6, len(dataset.bars))

    def test_hash_mismatch_and_artifact_escape_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest, cache = self.write_cache(Path(tmpdir))
            cache.write_bytes(cache.read_bytes() + b"tampered")
            with self.assertRaises(HistoricalCacheError):
                VerifiedHistoricalCsvLoader().read(manifest)

            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["artifact"] = "../outside.csv.gz"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(HistoricalCacheError):
                VerifiedHistoricalCsvLoader().read(manifest)

    def test_symlink_artifact_is_rejected_before_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest, cache = self.write_cache(Path(tmpdir))
            target = Path(tmpdir) / "actual.csv.gz"
            cache.rename(target)
            cache.symlink_to(target.name)

            with self.assertRaises(HistoricalCacheError):
                VerifiedHistoricalCsvLoader().read(manifest)

    def test_report_writer_is_create_only(self) -> None:
        result = HistoricalOrbBacktester().run(
            target_fixture(), OrbResearchParameters()
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "reports" / "report.json"
            HistoricalOrbReportWriter().write(output, result.to_dict())
            with self.assertRaises(HistoricalCacheError):
                HistoricalOrbReportWriter().write(output, result.to_dict())

    def test_report_serialization_failure_leaves_no_partial_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "reports" / "report.json"

            with self.assertRaises(HistoricalCacheError):
                HistoricalOrbReportWriter().write(output, {"invalid": float("nan")})

            self.assertFalse(output.exists())

    def test_report_publish_failure_leaves_no_output_or_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "reports" / "report.json"
            with patch(
                "autotrade.backtest.historical.os.link",
                side_effect=OSError("simulated publish failure"),
            ):
                with self.assertRaises(HistoricalCacheError):
                    HistoricalOrbReportWriter().write(output, {"valid": True})

            self.assertFalse(output.exists())
            self.assertEqual([], list(output.parent.glob(".report.json.*.tmp")))

    def test_cli_validate_and_run_never_load_moomoo_sdk(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest, _ = self.write_cache(Path(tmpdir))
            report = Path(tmpdir) / "orb-report.json"
            validate_stdout = io.StringIO()
            run_stdout = io.StringIO()
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                side_effect=AssertionError("SDK loaded"),
            ), redirect_stdout(validate_stdout):
                validate_exit = main(
                    ["historical-orb-backtest", "--manifest", str(manifest)]
                )
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                side_effect=AssertionError("SDK loaded"),
            ), redirect_stdout(run_stdout):
                run_exit = main(
                    [
                        "historical-orb-backtest",
                        "--manifest",
                        str(manifest),
                        "--run",
                        "--report-output",
                        str(report),
                    ]
                )
            report_content = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(0, validate_exit)
        self.assertIn('"mode": "validate-only"', validate_stdout.getvalue())
        self.assertEqual(0, run_exit)
        self.assertIn('"mode": "completed"', run_stdout.getvalue())
        self.assertEqual(2, report_content["schema_version"])
        self.assertIn("default_parameter_full_period", report_content)
        self.assertNotIn("baseline", report_content)
        self.assertEqual(
            1,
            report_content["default_parameter_full_period"]["metrics"]["trade_count"],
        )

    def test_cli_report_conflict_returns_two_without_traceback(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest, _ = self.write_cache(Path(tmpdir))
            report = Path(tmpdir) / "occupied.json"
            report.write_text("occupied", encoding="utf-8")
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "historical-orb-backtest",
                        "--manifest",
                        str(manifest),
                        "--run",
                        "--report-output",
                        str(report),
                    ]
                )

        self.assertEqual(2, exit_code)
        self.assertIn("already exists", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_tuning_requires_run_and_writes_schema_three(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest, _ = self.write_cache(Path(tmpdir))
            report = Path(tmpdir) / "tuning.json"
            with redirect_stderr(stderr):
                blocked_exit = main(
                    ["historical-orb-backtest", "--manifest", str(manifest), "--tune"]
                )
            completed_exit = main(
                [
                    "historical-orb-backtest",
                    "--manifest",
                    str(manifest),
                    "--run",
                    "--tune",
                    "--train-days",
                    "4",
                    "--test-days",
                    "2",
                    "--step-days",
                    "2",
                    "--inner-train-days",
                    "2",
                    "--inner-validation-days",
                    "1",
                    "--inner-step-days",
                    "1",
                    "--tuning-min-positive-neighbors",
                    "0",
                    "--report-output",
                    str(report),
                ]
            )
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(2, blocked_exit)
        self.assertIn("--tune requires --run", stderr.getvalue())
        self.assertEqual(0, completed_exit)
        self.assertEqual(3, payload["schema_version"])
        self.assertEqual("tuning-completed", payload["mode"])
        self.assertEqual(96, payload["tuning"]["candidate_count"])
        self.assertEqual("no-go", payload["tuning"]["decision"])
        self.assertIn(
            "outer_folds_missing", payload["tuning"]["decision_reasons"]
        )
        self.assertNotIn("walk_forward", payload)


if __name__ == "__main__":
    unittest.main()
