from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from autotrade.cli import main
from autotrade.execution.kabu_station import KabuStationClientError
from autotrade.execution.moomoo import (
    MoomooDiscoveryReportWriter,
    MoomooDiscoveryResult,
)
from tests.test_moomoo_discovery import FakeSdk


class KabuStationCliTests(unittest.TestCase):
    def test_validate_only_probe_does_not_construct_runtime_transport(self) -> None:
        stdout = io.StringIO()
        with patch(
            "autotrade.cli.KabuStationLocalhostHttpTransport",
            side_effect=AssertionError("network transport constructed"),
        ):
            with redirect_stdout(stdout):
                exit_code = main(["kabu-readonly-probe", "--environment", "test"])

        self.assertEqual(exit_code, 0)
        self.assertIn("read-only", stdout.getvalue())
        self.assertIn("validate-only", stdout.getvalue())

    def test_connect_probe_requires_password_without_cli_password_argument(self) -> None:
        stderr = io.StringIO()
        with patch.dict("os.environ", {}, clear=True):
            with redirect_stderr(stderr):
                exit_code = main(
                    ["kabu-readonly-probe", "--environment", "test", "--connect"]
                )

        self.assertEqual(exit_code, 2)
        self.assertIn("password", stderr.getvalue().lower())

    def test_invalid_environment_fails_fast(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(["kabu-readonly-probe", "--environment", "prod"])

        self.assertEqual(exit_code, 2)
        self.assertIn("environment", stderr.getvalue().lower())

    def test_report_write_failure_returns_clean_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "probe.json"
            with patch.dict(
                "os.environ",
                {"KABU_STATION_API_PASSWORD": "secret-password"},
                clear=True,
            ), patch(
                "autotrade.cli.KabuStationReadOnlyProbe.run",
            ), patch(
                "autotrade.cli.KabuStationProbeReportWriter.write",
                side_effect=KabuStationClientError(
                    "kabu Station probe report already exists"
                ),
            ), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "kabu-readonly-probe",
                        "--environment",
                        "test",
                        "--connect",
                        "--report-output",
                        str(report_path),
                    ]
                )

        self.assertEqual(exit_code, 2)
        self.assertIn("already exists", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_report_filesystem_failure_returns_clean_error_without_traceback(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            parent_file = Path(tmpdir) / "not-a-directory"
            parent_file.write_text("occupied", encoding="utf-8")
            with patch.dict(
                "os.environ",
                {"KABU_STATION_API_PASSWORD": "secret-password"},
                clear=True,
            ), patch(
                "autotrade.cli.KabuStationReadOnlyProbe.run",
            ), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "kabu-readonly-probe",
                        "--environment",
                        "test",
                        "--connect",
                        "--report-output",
                        str(parent_file / "probe.json"),
                    ]
                )

        self.assertEqual(exit_code, 2)
        self.assertIn("could not write", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


class MoomooDiscoveryCliTests(unittest.TestCase):
    def test_validate_only_does_not_load_sdk_or_connect(self) -> None:
        stdout = io.StringIO()
        with patch(
            "autotrade.cli.MoomooApiSdk.load",
            side_effect=AssertionError("SDK loaded"),
        ), redirect_stdout(stdout):
            exit_code = main(["moomoo-readonly-discovery"])

        self.assertEqual(0, exit_code)
        self.assertIn("validate-only", stdout.getvalue())
        self.assertIn("127.0.0.1:11111", stdout.getvalue())

    def test_remote_host_is_rejected_before_sdk_load(self) -> None:
        stderr = io.StringIO()
        with patch(
            "autotrade.cli.MoomooApiSdk.load",
            side_effect=AssertionError("SDK loaded"),
        ), redirect_stderr(stderr):
            exit_code = main(
                ["moomoo-readonly-discovery", "--host", "192.168.1.20"]
            )

        self.assertEqual(2, exit_code)
        self.assertIn("loopback", stderr.getvalue())

    def test_connect_runs_sanitized_read_only_discovery(self) -> None:
        stdout = io.StringIO()
        with patch("autotrade.cli.MoomooApiSdk.load", return_value=FakeSdk()), redirect_stdout(stdout):
            exit_code = main(["moomoo-readonly-discovery", "--connect"])

        self.assertEqual(0, exit_code)
        output = stdout.getvalue()
        self.assertIn('"paper_account_available": true', output)
        self.assertNotIn("sensitive", output)

    def test_cli_exposes_no_trade_unlock_option(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(
                ["moomoo-readonly-discovery", "--unlock-trade"]
            )

        self.assertEqual(2, exit_code)
        self.assertIn("unrecognized arguments", stderr.getvalue())

    def test_report_conflict_returns_clean_error(self) -> None:
        stderr = io.StringIO()
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.json"
            report_path.write_text("existing", encoding="utf-8")
            with patch(
                "autotrade.cli.MoomooApiSdk.load", return_value=FakeSdk()
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "moomoo-readonly-discovery",
                        "--connect",
                        "--report-output",
                        str(report_path),
                    ]
                )

        self.assertEqual(2, exit_code)
        self.assertIn('"paper_account_available": true', stdout.getvalue())
        self.assertNotIn("sensitive", stdout.getvalue())
        self.assertIn("already exists", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


class MoomooPaperReadinessCliTests(unittest.TestCase):
    def test_ready_report_is_evaluated_offline_without_sdk_load(self) -> None:
        stdout = io.StringIO()
        discovery = MoomooDiscoveryResult(
            endpoint="127.0.0.1:11111",
            sdk_version="10.9.6908",
            server_version="1009",
            quote_connection_status="ok",
            trade_connection_status="ok",
            qot_logged_in=True,
            trd_logged_in=True,
            us_quote_entitlement="LV1",
            account_count=1,
            paper_account_count=1,
            paper_account_available=True,
            us_market_authorized=True,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "discovery.json"
            MoomooDiscoveryReportWriter().write(report_path, discovery)
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                side_effect=AssertionError("SDK loaded"),
            ), redirect_stdout(stdout):
                exit_code = main(
                    [
                        "moomoo-paper-readiness",
                        "--discovery-report",
                        str(report_path),
                    ]
                )

        self.assertEqual(0, exit_code)
        self.assertIn('"status": "READY"', stdout.getvalue())
        self.assertNotIn("acc_id", stdout.getvalue())

    def test_blocked_report_returns_one(self) -> None:
        stdout = io.StringIO()
        discovery = MoomooDiscoveryResult(
            endpoint="127.0.0.1:11111",
            sdk_version="10.9.6908",
            server_version="1009",
            quote_connection_status="ok",
            trade_connection_status="ok",
            qot_logged_in=True,
            trd_logged_in=True,
            us_quote_entitlement="UNKNOWN",
            account_count=1,
            paper_account_count=1,
            paper_account_available=True,
            us_market_authorized=True,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "discovery.json"
            MoomooDiscoveryReportWriter().write(report_path, discovery)
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "moomoo-paper-readiness",
                        "--discovery-report",
                        str(report_path),
                    ]
                )

        self.assertEqual(1, exit_code)
        self.assertIn("US_QUOTE_ENTITLEMENT_UNAVAILABLE", stdout.getvalue())

    def test_invalid_report_fails_cleanly_without_traceback(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "invalid.json"
            report_path.write_text("not-json", encoding="utf-8")
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "moomoo-paper-readiness",
                        "--discovery-report",
                        str(report_path),
                    ]
                )

        self.assertEqual(2, exit_code)
        self.assertIn("could not read", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_non_utf8_report_fails_cleanly_without_traceback(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "invalid-utf8.json"
            report_path.write_bytes(b"\xff\xfe\xfa")
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "moomoo-paper-readiness",
                        "--discovery-report",
                        str(report_path),
                    ]
                )

        self.assertEqual(2, exit_code)
        self.assertIn("could not read", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


class MoomooPaperOrderDryRunCliTests(unittest.TestCase):
    def test_creates_offline_dry_run_without_sdk_or_order_call(self) -> None:
        stdout = io.StringIO()
        discovery = MoomooDiscoveryResult(
            endpoint="127.0.0.1:11111",
            sdk_version="10.9.6908",
            server_version="1009",
            quote_connection_status="ok",
            trade_connection_status="ok",
            qot_logged_in=True,
            trd_logged_in=True,
            us_quote_entitlement="LV1",
            account_count=1,
            paper_account_count=1,
            paper_account_available=True,
            us_market_authorized=True,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "discovery.json"
            MoomooDiscoveryReportWriter().write(report_path, discovery)
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                side_effect=AssertionError("SDK loaded"),
            ), redirect_stdout(stdout):
                exit_code = main(
                    [
                        "moomoo-paper-order-dry-run",
                        "--discovery-report",
                        str(report_path),
                        "--client-order-id",
                        "paper-dry-run-001",
                        "--strategy-id",
                        "us_paper_validation",
                        "--code",
                        "US.AAPL",
                        "--quantity",
                        "10",
                        "--limit-price",
                        "150.25",
                        "--stop-price",
                        "148.0",
                        "--take-profit-price",
                        "154.0",
                        "--created-at",
                        "2026-08-01T14:30:00+00:00",
                    ]
                )

        self.assertEqual(0, exit_code)
        self.assertIn('"dry_run": true', stdout.getvalue())
        self.assertIn('"trd_env": "SIMULATE"', stdout.getvalue())
        self.assertNotIn("acc_id", stdout.getvalue())

    def test_blocked_readiness_and_invalid_timestamp_fail_cleanly(self) -> None:
        blocked = MoomooDiscoveryResult(
            endpoint="127.0.0.1:11111",
            sdk_version="10.9.6908",
            server_version="1009",
            quote_connection_status="ok",
            trade_connection_status="ok",
            qot_logged_in=True,
            trd_logged_in=True,
            us_quote_entitlement="UNKNOWN",
            account_count=1,
            paper_account_count=1,
            paper_account_available=True,
            us_market_authorized=True,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "discovery.json"
            MoomooDiscoveryReportWriter().write(report_path, blocked)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                blocked_exit = main(self._args(report_path))
            self.assertEqual(1, blocked_exit)
            self.assertIn("READINESS_NOT_READY", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

            stderr = io.StringIO()
            invalid_args = self._args(report_path)
            invalid_args[-1] = "not-a-timestamp"
            with redirect_stderr(stderr):
                invalid_exit = main(invalid_args)
            self.assertEqual(2, invalid_exit)
            self.assertIn("created-at", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    @staticmethod
    def _args(report_path: Path) -> list[str]:
        return [
            "moomoo-paper-order-dry-run",
            "--discovery-report",
            str(report_path),
            "--client-order-id",
            "paper-dry-run-001",
            "--strategy-id",
            "us_paper_validation",
            "--code",
            "US.AAPL",
            "--quantity",
            "10",
            "--limit-price",
            "150.25",
            "--stop-price",
            "148.0",
            "--created-at",
            "2026-08-01T14:30:00+00:00",
        ]

if __name__ == "__main__":
    unittest.main()
