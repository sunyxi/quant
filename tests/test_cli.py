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
    MoomooPaperAccountPreflightReportWriter,
)
from tests.test_moomoo_discovery import FakeSdk
from tests.test_moomoo_readiness import ready_discovery
from tests.test_moomoo_preflight import FakePreflightSdk
from tests.test_moomoo_paper_reconcile import FakeReconcileSdk
from tests.test_moomoo_paper_submit import FakeSubmitSdk, successful_preflight


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


class MoomooPaperAccountPreflightCliTests(unittest.TestCase):
    def test_validate_only_does_not_load_sdk_or_connect(self) -> None:
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery_path = Path(tmpdir) / "discovery.json"
            MoomooDiscoveryReportWriter().write(
                discovery_path,
                ready_discovery(),
            )
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                side_effect=AssertionError("SDK loaded"),
            ), redirect_stdout(stdout):
                exit_code = main(
                    [
                        "moomoo-paper-account-preflight",
                        "--discovery-report",
                        str(discovery_path),
                    ]
                )

        self.assertEqual(0, exit_code)
        self.assertIn('"mode": "validate-only"', stdout.getvalue())
        self.assertIn('"connection_status": "not-run"', stdout.getvalue())

    def test_remote_host_is_rejected_before_sdk_load(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery_path = Path(tmpdir) / "discovery.json"
            MoomooDiscoveryReportWriter().write(discovery_path, ready_discovery())
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                side_effect=AssertionError("SDK loaded"),
            ), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "moomoo-paper-account-preflight",
                        "--discovery-report",
                        str(discovery_path),
                        "--host",
                        "example.com",
                    ]
                )

        self.assertEqual(2, exit_code)
        self.assertIn("loopback", stderr.getvalue())

    def test_validate_only_blocked_discovery_does_not_load_sdk(self) -> None:
        stderr = io.StringIO()
        stdout = io.StringIO()
        blocked = MoomooDiscoveryResult(
            paper_account_count=0,
            paper_account_available=False,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery_path = Path(tmpdir) / "discovery.json"
            MoomooDiscoveryReportWriter().write(discovery_path, blocked)
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                side_effect=AssertionError("SDK loaded"),
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "moomoo-paper-account-preflight",
                        "--discovery-report",
                        str(discovery_path),
                    ]
                )

        self.assertEqual(1, exit_code)
        self.assertEqual("", stdout.getvalue())
        self.assertIn("READINESS_NOT_READY", stderr.getvalue())

    def test_connect_runs_sanitized_preflight_and_writes_report(self) -> None:
        stdout = io.StringIO()
        sdk = FakePreflightSdk()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery_path = Path(tmpdir) / "discovery.json"
            report_path = Path(tmpdir) / "preflight.json"
            MoomooDiscoveryReportWriter().write(
                discovery_path,
                ready_discovery(),
            )
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                return_value=sdk,
            ), redirect_stdout(stdout):
                exit_code = main(
                    [
                        "moomoo-paper-account-preflight",
                        "--discovery-report",
                        str(discovery_path),
                        "--connect",
                        "--report-output",
                        str(report_path),
                    ]
                )

            report = report_path.read_text(encoding="utf-8")

        self.assertEqual(0, exit_code)
        self.assertIn('"sanitized_failure_category": null', stdout.getvalue())
        self.assertIn('"refresh_cache": true', report)
        self.assertNotIn("acc_id", stdout.getvalue())
        self.assertNotIn("sensitive", stdout.getvalue())
        self.assertTrue(sdk.context.closed)

    def test_blocked_discovery_prevents_sdk_load(self) -> None:
        stderr = io.StringIO()
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
            discovery_path = Path(tmpdir) / "discovery.json"
            MoomooDiscoveryReportWriter().write(discovery_path, blocked)
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                side_effect=AssertionError("SDK loaded"),
            ), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "moomoo-paper-account-preflight",
                        "--discovery-report",
                        str(discovery_path),
                        "--connect",
                    ]
                )

        self.assertEqual(1, exit_code)
        self.assertIn("READINESS_NOT_READY", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_report_write_failure_returns_two_without_traceback(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery_path = Path(tmpdir) / "discovery.json"
            report_path = Path(tmpdir) / "existing.json"
            report_path.write_text("occupied", encoding="utf-8")
            MoomooDiscoveryReportWriter().write(
                discovery_path,
                ready_discovery(),
            )
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                return_value=FakePreflightSdk(),
            ), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "moomoo-paper-account-preflight",
                        "--discovery-report",
                        str(discovery_path),
                        "--connect",
                        "--report-output",
                        str(report_path),
                    ]
                )

        self.assertEqual(2, exit_code)
        self.assertIn("already exists", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


class MoomooPaperOrderDryRunCliTests(unittest.TestCase):
    def test_creates_offline_dry_run_without_sdk_or_order_call(self) -> None:
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "discovery.json"
            MoomooDiscoveryReportWriter().write(report_path, ready_discovery())
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


    def test_accepts_aggressive_limit_order_style(self) -> None:
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "discovery.json"
            MoomooDiscoveryReportWriter().write(
                report_path,
                ready_discovery(),
            )
            args = self._args(report_path)
            args[1:1] = ["--order-style", "AGGRESSIVE_LIMIT"]
            with redirect_stdout(stdout):
                exit_code = main(args)

        self.assertEqual(0, exit_code)
        self.assertIn(
            '"source_order_style": "AGGRESSIVE_LIMIT"',
            stdout.getvalue(),
        )
        self.assertIn('"take_profit_price": null', stdout.getvalue())

    def test_non_finite_price_is_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "discovery.json"
            MoomooDiscoveryReportWriter().write(report_path, ready_discovery())
            for price_flag in [
                "--limit-price",
                "--stop-price",
                "--take-profit-price",
            ]:
                for invalid_price in ["nan", "inf"]:
                    args = self._args(report_path, include_take_profit=True)
                    args[args.index(price_flag) + 1] = invalid_price
                    stderr = io.StringIO()
                    with self.subTest(
                        price_flag=price_flag,
                        invalid_price=invalid_price,
                    ), redirect_stderr(stderr):
                        exit_code = main(args)
                    self.assertEqual(2, exit_code)
                    self.assertIn("invalid paper-order fields", stderr.getvalue())
                    self.assertNotIn("Traceback", stderr.getvalue())

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
            created_at_index = invalid_args.index("--created-at") + 1
            invalid_args[created_at_index] = "not-a-timestamp"
            with redirect_stderr(stderr):
                invalid_exit = main(invalid_args)
            self.assertEqual(2, invalid_exit)
            self.assertIn("created-at", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    @staticmethod
    def _args(
        report_path: Path,
        *,
        include_take_profit: bool = False,
    ) -> list[str]:
        args = [
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
        ]
        if include_take_profit:
            args.extend(["--take-profit-price", "154.0"])
        args.extend(["--created-at", "2026-08-01T14:30:00+00:00"])
        return args


class MoomooPaperOrderSubmitCliTests(unittest.TestCase):
    def _reports(self, tmpdir: str) -> tuple[Path, Path]:
        discovery_path = Path(tmpdir) / "discovery.json"
        preflight_path = Path(tmpdir) / "preflight.json"
        MoomooDiscoveryReportWriter().write(discovery_path, ready_discovery())
        MoomooPaperAccountPreflightReportWriter().write(
            preflight_path,
            successful_preflight(),
        )
        return discovery_path, preflight_path

    def _args(self, discovery_path: Path, preflight_path: Path) -> list[str]:
        return [
            "moomoo-paper-order-submit",
            "--discovery-report", str(discovery_path),
            "--preflight-report", str(preflight_path),
            "--client-order-id", "paper-dry-run-001",
            "--strategy-id", "us_paper_validation",
            "--code", "US.AAPL",
            "--quantity", "10",
            "--limit-price", "150.25",
            "--stop-price", "148.0",
            "--take-profit-price", "154.0",
            "--created-at", "2026-08-01T14:30:00+00:00",
        ]

    def test_default_is_preview_only_without_sdk_load(self) -> None:
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery, preflight = self._reports(tmpdir)
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                side_effect=AssertionError("SDK loaded"),
            ), redirect_stdout(stdout):
                exit_code = main(self._args(discovery, preflight))

        self.assertEqual(0, exit_code)
        self.assertIn('"mode": "preview-only"', stdout.getvalue())
        self.assertIn('"submission_status": "not-run"', stdout.getvalue())

    def test_partial_confirmation_fails_before_sdk_load(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery, preflight = self._reports(tmpdir)
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                side_effect=AssertionError("SDK loaded"),
            ), redirect_stderr(stderr):
                exit_code = main(
                    self._args(discovery, preflight)
                    + ["--connect", "--submit-paper-order"]
                )

        self.assertEqual(2, exit_code)
        self.assertIn("acknowledge", stderr.getvalue())

    def test_explicit_confirmation_submits_with_fake_sdk(self) -> None:
        stdout = io.StringIO()
        sdk = FakeSubmitSdk()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery, preflight = self._reports(tmpdir)
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                return_value=sdk,
            ), redirect_stdout(stdout):
                exit_code = main(
                    self._args(discovery, preflight)
                    + [
                        "--connect",
                        "--submit-paper-order",
                        "--acknowledge-paper-order-side-effect",
                    ]
                )

        self.assertEqual(0, exit_code)
        self.assertIn('"status": "verified"', stdout.getvalue())
        self.assertEqual(1, len(sdk.context.place_calls))


class MoomooPaperOrderReconcileCliTests(unittest.TestCase):
    def _reports(self, tmpdir: str) -> tuple[Path, Path]:
        discovery_path = Path(tmpdir) / "discovery.json"
        preflight_path = Path(tmpdir) / "preflight.json"
        MoomooDiscoveryReportWriter().write(discovery_path, ready_discovery())
        MoomooPaperAccountPreflightReportWriter().write(
            preflight_path,
            successful_preflight(),
        )
        return discovery_path, preflight_path

    @staticmethod
    def _args(discovery_path: Path, preflight_path: Path) -> list[str]:
        return [
            "moomoo-paper-order-reconcile",
            "--discovery-report", str(discovery_path),
            "--preflight-report", str(preflight_path),
            "--client-order-id", "paper-dry-run-001",
        ]

    def test_default_is_validate_only_without_sdk_load(self) -> None:
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery, preflight = self._reports(tmpdir)
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                side_effect=AssertionError("SDK loaded"),
            ), redirect_stdout(stdout):
                exit_code = main(self._args(discovery, preflight))

        self.assertEqual(0, exit_code)
        self.assertIn('"mode": "validate-only"', stdout.getvalue())
        self.assertIn('"reconciliation_status": "not-run"', stdout.getvalue())
        self.assertNotIn("acc_id", stdout.getvalue())

    def test_validate_only_rejects_report_output_without_writing(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery, preflight = self._reports(tmpdir)
            output = Path(tmpdir) / "reconciliation.json"
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                side_effect=AssertionError("SDK loaded"),
            ), redirect_stderr(stderr):
                exit_code = main(
                    self._args(discovery, preflight)
                    + ["--report-output", str(output)]
                )

            self.assertFalse(output.exists())

        self.assertEqual(2, exit_code)
        self.assertIn("--connect", stderr.getvalue())

    def test_connect_runs_one_sanitized_read_only_query(self) -> None:
        stdout = io.StringIO()
        sdk = FakeReconcileSdk()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery, preflight = self._reports(tmpdir)
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                return_value=sdk,
            ), patch(
                "autotrade.cli.validate_moomoo_paper_reconciliation_evidence",
                side_effect=AssertionError("CLI duplicated service validation"),
            ), redirect_stdout(stdout):
                exit_code = main(
                    self._args(discovery, preflight) + ["--connect"]
                )

        self.assertEqual(0, exit_code)
        self.assertIn('"status": "unique"', stdout.getvalue())
        self.assertNotIn("acc_id", stdout.getvalue())
        self.assertNotIn('"order_id":', stdout.getvalue())
        self.assertEqual(1, len(sdk.context.order_query_calls))
        self.assertEqual([], sdk.context.place_calls)

    def test_connect_writes_create_only_sanitized_report(self) -> None:
        stdout = io.StringIO()
        sdk = FakeReconcileSdk()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery, preflight = self._reports(tmpdir)
            output = Path(tmpdir) / "reports" / "reconciliation.json"
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                return_value=sdk,
            ), redirect_stdout(stdout):
                exit_code = main(
                    self._args(discovery, preflight)
                    + ["--connect", "--report-output", str(output)]
                )
            report = output.read_text(encoding="utf-8")

        self.assertEqual(0, exit_code)
        self.assertIn('"status": "unique"', report)
        self.assertNotIn("acc_id", report)
        self.assertNotIn('"order_id":', report)

    def test_report_conflict_returns_two_without_traceback(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery, preflight = self._reports(tmpdir)
            output = Path(tmpdir) / "reconciliation.json"
            output.write_text("occupied", encoding="utf-8")
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                return_value=FakeReconcileSdk(),
            ), redirect_stderr(stderr):
                exit_code = main(
                    self._args(discovery, preflight)
                    + ["--connect", "--report-output", str(output)]
                )

        self.assertEqual(2, exit_code)
        self.assertIn("already exists", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_report_request_fails_cleanly_when_query_did_not_run(self) -> None:
        stderr = io.StringIO()
        sdk = FakeReconcileSdk()
        sdk.version = "10.5"
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery, preflight = self._reports(tmpdir)
            output = Path(tmpdir) / "reconciliation.json"
            with patch(
                "autotrade.cli.MoomooApiSdk.load",
                return_value=sdk,
            ), redirect_stderr(stderr):
                exit_code = main(
                    self._args(discovery, preflight)
                    + ["--connect", "--report-output", str(output)]
                )

            self.assertFalse(output.exists())

        self.assertEqual(2, exit_code)
        self.assertIn("query_status", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
