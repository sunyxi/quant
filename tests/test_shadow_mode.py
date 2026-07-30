from __future__ import annotations

import unittest
import json
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from autotrade.core.models import Fill, Market, OrderIntent, OrderStyle, Side
from autotrade.execution.reconciliation import (
    ReconciliationDiscrepancy,
    ReconciliationReport,
    ReconciliationSeverity,
)
from autotrade.execution.replay import ReplayExecutionResult
from autotrade.execution.shadow_mode import (
    ShadowModeSummaryError,
    ShadowModeSummaryReader,
    ShadowModeReadinessGate,
    ShadowModeReadinessStatus,
    ShadowModeSummaryWriter,
    ShadowModeRunSummary,
)
from autotrade.execution.simulated_broker import SimulatedBrokerAdapter
from autotrade.risk.manager import RiskConfig, RiskManager


def _intent(client_order_id: str = "client-1") -> OrderIntent:
    return OrderIntent(
        client_order_id=client_order_id,
        strategy_id="test_strategy",
        symbol="7203.T",
        market=Market.JP,
        side=Side.BUY,
        quantity=100,
        order_style=OrderStyle.PASSIVE_LIMIT,
        limit_price=1000,
        stop_price=990,
        take_profit_price=1020,
        created_at=datetime(2026, 7, 28, 9, 30, tzinfo=ZoneInfo("Asia/Tokyo")),
    )


def _fill(client_order_id: str = "client-1") -> Fill:
    return Fill(
        client_order_id=client_order_id,
        symbol="7203.T",
        side=Side.BUY,
        quantity=100,
        price=1000,
        filled_at=datetime(2026, 7, 28, 9, 31, tzinfo=ZoneInfo("Asia/Tokyo")),
    )


def _clean_result() -> ReplayExecutionResult:
    intent = _intent()
    broker = SimulatedBrokerAdapter()
    broker.submit_order(intent)
    fill = _fill()
    broker.record_fill(fill)
    return ReplayExecutionResult(
        intents=[intent],
        fills=[fill],
        broker=broker,
        reconciliation_reports=[ReconciliationReport()],
    )


class ShadowModeReadinessGateTests(unittest.TestCase):
    def test_clean_replay_result_passes_readiness(self) -> None:
        decision = ShadowModeReadinessGate().evaluate(_clean_result())

        self.assertEqual(decision.status, ShadowModeReadinessStatus.PASSED)
        self.assertEqual(decision.reasons, [])
        self.assertEqual(decision.metrics["intents"], 1)
        self.assertEqual(decision.metrics["fills"], 1)
        self.assertEqual(decision.metrics["reconciliation_reports"], 1)
        self.assertEqual(decision.metrics["critical_reports"], 0)
        self.assertEqual(decision.metrics["open_orders"], 0)

    def test_critical_reconciliation_report_blocks_readiness(self) -> None:
        result = _clean_result()
        result.reconciliation_reports = [
            ReconciliationReport(
                discrepancies=[
                    ReconciliationDiscrepancy(
                        kind="POSITION_MISMATCH",
                        severity=ReconciliationSeverity.CRITICAL,
                        message="local quantity differs from broker quantity",
                    )
                ]
            )
        ]

        decision = ShadowModeReadinessGate().evaluate(result)

        self.assertEqual(decision.status, ShadowModeReadinessStatus.BLOCKED)
        self.assertIn("critical reconciliation discrepancy", decision.reasons)
        self.assertEqual(decision.metrics["critical_reports"], 1)

    def test_paused_risk_manager_blocks_readiness_with_reason(self) -> None:
        risk = RiskManager(RiskConfig(account_equity=1_000_000))
        risk.pause("manual incident review")

        decision = ShadowModeReadinessGate().evaluate(
            _clean_result(),
            risk_manager=risk,
        )

        self.assertEqual(decision.status, ShadowModeReadinessStatus.BLOCKED)
        self.assertIn("risk paused: manual incident review", decision.reasons)

    def test_missing_reconciliation_evidence_blocks_readiness(self) -> None:
        result = _clean_result()
        result.reconciliation_reports = []

        decision = ShadowModeReadinessGate().evaluate(result)

        self.assertEqual(decision.status, ShadowModeReadinessStatus.BLOCKED)
        self.assertIn("missing reconciliation evidence", decision.reasons)

    def test_remaining_open_orders_block_readiness(self) -> None:
        intent = _intent()
        broker = SimulatedBrokerAdapter()
        broker.submit_order(intent)
        result = ReplayExecutionResult(
            intents=[intent],
            broker=broker,
            reconciliation_reports=[ReconciliationReport()],
        )

        decision = ShadowModeReadinessGate().evaluate(result)

        self.assertEqual(decision.status, ShadowModeReadinessStatus.BLOCKED)
        self.assertIn("open simulated broker orders remain", decision.reasons)
        self.assertEqual(decision.metrics["open_orders"], 1)

    def test_passing_readiness_decision_builds_passing_run_summary(self) -> None:
        decision = ShadowModeReadinessGate().evaluate(_clean_result())

        summary = ShadowModeRunSummary.from_readiness_decision(
            trading_date="2026-07-28",
            decision=decision,
        )

        self.assertEqual(summary.trading_date, "2026-07-28")
        self.assertEqual(summary.status, ShadowModeReadinessStatus.PASSED)
        self.assertEqual(summary.reasons, [])
        self.assertEqual(summary.metrics["intents"], 1)
        self.assertEqual(
            summary.to_dict(),
            {
                "trading_date": "2026-07-28",
                "status": "PASSED",
                "reasons": [],
                "metrics": {
                    "intents": 1,
                    "fills": 1,
                    "reconciliation_reports": 1,
                    "critical_reports": 0,
                    "open_orders": 0,
                },
            },
        )

    def test_blocked_readiness_decision_builds_blocked_run_summary(self) -> None:
        result = _clean_result()
        result.reconciliation_reports = []
        decision = ShadowModeReadinessGate().evaluate(result)

        summary = ShadowModeRunSummary.from_readiness_decision(
            trading_date="2026-07-28",
            decision=decision,
        )

        self.assertEqual(summary.status, ShadowModeReadinessStatus.BLOCKED)
        self.assertEqual(summary.reasons, ["missing reconciliation evidence"])

    def test_run_summary_copies_readiness_metrics(self) -> None:
        decision = ShadowModeReadinessGate().evaluate(_clean_result())
        summary = ShadowModeRunSummary.from_readiness_decision(
            trading_date="2026-07-28",
            decision=decision,
        )

        decision.metrics["intents"] = 99

        self.assertEqual(summary.metrics["intents"], 1)

    def test_summary_writer_stores_json_and_returns_path(self) -> None:
        summary = ShadowModeRunSummary.from_readiness_decision(
            trading_date="2026-07-28",
            decision=ShadowModeReadinessGate().evaluate(_clean_result()),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "shadow" / "summary.json"

            written_path = ShadowModeSummaryWriter().write(summary, output_path)

            self.assertEqual(written_path, output_path)
            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf-8")),
                summary.to_dict(),
            )
            self.assertTrue(output_path.read_text(encoding="utf-8").endswith("\n"))

    def test_summary_writer_rejects_existing_file_by_default(self) -> None:
        summary = ShadowModeRunSummary.from_readiness_decision(
            trading_date="2026-07-28",
            decision=ShadowModeReadinessGate().evaluate(_clean_result()),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "summary.json"
            output_path.write_text("existing\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                ShadowModeSummaryWriter().write(summary, output_path)

            self.assertEqual(output_path.read_text(encoding="utf-8"), "existing\n")

    def test_summary_reader_loads_writer_output(self) -> None:
        summary = ShadowModeRunSummary.from_readiness_decision(
            trading_date="2026-07-28",
            decision=ShadowModeReadinessGate().evaluate(_clean_result()),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "summary.json"
            ShadowModeSummaryWriter().write(summary, output_path)

            loaded = ShadowModeSummaryReader().read(output_path)

            self.assertEqual(loaded, summary)

    def test_summary_reader_rejects_missing_required_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "summary.json"
            output_path.write_text(
                json.dumps({"status": "PASSED", "reasons": [], "metrics": {}}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ShadowModeSummaryError, "trading_date"):
                ShadowModeSummaryReader().read(output_path)

    def test_summary_reader_rejects_unknown_status(self) -> None:
        payload = {
            "trading_date": "2026-07-28",
            "status": "UNKNOWN",
            "reasons": [],
            "metrics": {},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "summary.json"
            output_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ShadowModeSummaryError, "status"):
                ShadowModeSummaryReader().read(output_path)

    def test_summary_reader_rejects_non_list_reasons(self) -> None:
        payload = {
            "trading_date": "2026-07-28",
            "status": "PASSED",
            "reasons": "none",
            "metrics": {},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "summary.json"
            output_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ShadowModeSummaryError, "reasons"):
                ShadowModeSummaryReader().read(output_path)

    def test_summary_reader_rejects_non_integer_metrics(self) -> None:
        payload = {
            "trading_date": "2026-07-28",
            "status": "PASSED",
            "reasons": [],
            "metrics": {"intents": "1"},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "summary.json"
            output_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ShadowModeSummaryError, "metrics"):
                ShadowModeSummaryReader().read(output_path)


if __name__ == "__main__":
    unittest.main()
