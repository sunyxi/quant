from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path
from typing import Sequence, TextIO

from autotrade.execution.kabu_station import (
    KabuStationClientError,
    KabuStationEnvironment,
    KabuStationLocalhostHttpTransport,
    KabuStationProbeReportWriter,
    KabuStationReadOnlyClient,
    KabuStationReadOnlyProbe,
    KabuStationTokenClient,
)
from autotrade.execution.moomoo import (
    MoomooApiSdk,
    MoomooClientError,
    MoomooConfigurationError,
    MoomooDiscoveryReportWriter,
    MoomooEndpoint,
    MoomooReadOnlyDiscovery,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    if args.command == "kabu-readonly-probe":
        return _run_kabu_readonly_probe(args, stdout=sys.stdout, stderr=sys.stderr)
    if args.command == "moomoo-readonly-discovery":
        return _run_moomoo_readonly_discovery(
            args,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    parser.error("unknown command")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autotrade")
    subparsers = parser.add_subparsers(dest="command", required=True)
    probe = subparsers.add_parser(
        "kabu-readonly-probe",
        description="Validate or execute the read-only kabu Station localhost probe.",
    )
    probe.add_argument(
        "--environment",
        required=True,
        choices=["test", "production"],
        help="kabu Station environment to validate or probe.",
    )
    probe.add_argument(
        "--connect",
        action="store_true",
        help="Explicitly connect to localhost and run the read-only probe.",
    )
    probe.add_argument(
        "--prompt-password",
        action="store_true",
        help="Read the API password from a secure interactive prompt.",
    )
    probe.add_argument(
        "--report-output",
        type=Path,
        help="Optional path for a sanitized deterministic probe report JSON file.",
    )
    moomoo = subparsers.add_parser(
        "moomoo-readonly-discovery",
        description="Validate or execute sanitized read-only Moomoo OpenD discovery.",
    )
    moomoo.add_argument(
        "--host",
        default="127.0.0.1",
        help="Loopback Moomoo OpenD host. Defaults to 127.0.0.1.",
    )
    moomoo.add_argument(
        "--port",
        type=int,
        default=11111,
        help="Moomoo OpenD port. Defaults to 11111.",
    )
    moomoo.add_argument(
        "--connect",
        action="store_true",
        help="Explicitly load moomoo-api and run read-only discovery.",
    )
    moomoo.add_argument(
        "--report-output",
        type=Path,
        help="Optional path for a sanitized create-only discovery report.",
    )
    return parser


def _run_kabu_readonly_probe(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    environment = _environment_from_name(args.environment)
    try:
        KabuStationLocalhostHttpTransport.validate_localhost_url(environment.base_url)
    except KabuStationClientError as exc:
        print(str(exc), file=stderr)
        return 2

    if not args.connect:
        print(
            json.dumps(
                {
                    "mode": "validate-only",
                    "probe": "kabu Station read-only localhost probe",
                    "environment": args.environment,
                    "localhost_endpoint": environment.base_url,
                    "connection_status": "not-run",
                },
                sort_keys=True,
            ),
            file=stdout,
        )
        return 0

    api_password = os.environ.get("KABU_STATION_API_PASSWORD")
    if not api_password and args.prompt_password:
        api_password = getpass.getpass("kabu Station API password: ")
    if not api_password:
        print(
            "KABU_STATION_API_PASSWORD is required for --connect; password command-line arguments are not supported.",
            file=stderr,
        )
        return 2

    transport = KabuStationLocalhostHttpTransport()
    probe = KabuStationReadOnlyProbe(
        environment_name=args.environment,
        environment=environment,
        token_client=KabuStationTokenClient(
            environment=environment,
            transport=transport,
        ),
        readonly_client=KabuStationReadOnlyClient(
            environment=environment,
            transport=transport,
        ),
    )
    result = probe.run(api_password=api_password)
    if args.report_output is not None:
        try:
            KabuStationProbeReportWriter().write(args.report_output, result)
        except KabuStationClientError as exc:
            print(f"error: {exc}", file=stderr)
            return 2
    print(json.dumps(result.to_dict(), sort_keys=True), file=stdout)
    return 0 if result.sanitized_failure_category is None else 1


def _environment_from_name(name: str) -> KabuStationEnvironment:
    if name == "test":
        return KabuStationEnvironment.test()
    if name == "production":
        return KabuStationEnvironment.production()
    raise KabuStationClientError(f"unsupported kabu Station environment: {name}")


def _run_moomoo_readonly_discovery(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    try:
        endpoint = MoomooEndpoint(host=args.host, port=args.port)
    except MoomooConfigurationError as exc:
        print(f"error: {exc}", file=stderr)
        return 2

    if not args.connect:
        print(
            json.dumps(
                {
                    "mode": "validate-only",
                    "probe": "Moomoo OpenAPI read-only discovery",
                    "localhost_endpoint": endpoint.display,
                    "connection_status": "not-run",
                },
                sort_keys=True,
            ),
            file=stdout,
        )
        return 0

    try:
        sdk = MoomooApiSdk.load()
    except MoomooClientError:
        print("error: Moomoo discovery failed (dependency)", file=stderr)
        return 1

    result = MoomooReadOnlyDiscovery(endpoint=endpoint, sdk=sdk).run()
    print(json.dumps(result.to_dict(), sort_keys=True), file=stdout)
    if args.report_output is not None:
        try:
            MoomooDiscoveryReportWriter().write(args.report_output, result)
        except MoomooConfigurationError as exc:
            print(f"error: {exc}", file=stderr)
            return 2
    return 0 if result.sanitized_failure_category is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
