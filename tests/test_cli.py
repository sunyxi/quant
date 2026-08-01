from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from autotrade.cli import main
from autotrade.execution.kabu_station import KabuStationClientError
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

if __name__ == "__main__":
    unittest.main()
