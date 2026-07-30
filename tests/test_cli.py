from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from autotrade.cli import main


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


if __name__ == "__main__":
    unittest.main()
