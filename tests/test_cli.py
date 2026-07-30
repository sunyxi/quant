from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from autotrade.cli import main
from autotrade.execution.kabu_station import KabuStationClientError


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


if __name__ == "__main__":
    unittest.main()
