from __future__ import annotations

import argparse
import getpass
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence, TextIO

from autotrade.core.models import Market, OrderIntent, OrderStyle, Side

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
    MoomooDiscoveryReportReader,
    MoomooDiscoveryReportWriter,
    MoomooEndpoint,
    MoomooPaperAccountPreflight,
    MoomooPaperAccountPreflightReportReader,
    MoomooPaperAccountPreflightReportWriter,
    MoomooReadOnlyDiscovery,
)
from autotrade.execution.moomoo_readiness import (
    MoomooPaperReadinessDecision,
    MoomooPaperReadinessGate,
)
from autotrade.execution.moomoo_paper_order import (
    MoomooPaperOrderDryRunPlanner,
    MoomooPaperOrderPlanError,
)
from autotrade.execution.moomoo_paper_submit import (
    MoomooPaperOrderSubmissionStatus,
    MoomooPaperOrderSubmitter,
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
    if args.command == "moomoo-paper-readiness":
        return _run_moomoo_paper_readiness(
            args,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    if args.command == "moomoo-paper-account-preflight":
        return _run_moomoo_paper_account_preflight(
            args,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    if args.command == "moomoo-paper-order-dry-run":
        return _run_moomoo_paper_order_dry_run(
            args,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    if args.command == "moomoo-paper-order-submit":
        return _run_moomoo_paper_order_submit(
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
    readiness = subparsers.add_parser(
        "moomoo-paper-readiness",
        description="Evaluate a sanitized Moomoo discovery report offline.",
    )
    readiness.add_argument(
        "--discovery-report",
        type=Path,
        required=True,
        help="Path to a sanitized Moomoo discovery schema version 1 report.",
    )
    preflight = subparsers.add_parser(
        "moomoo-paper-account-preflight",
        description="Validate or run the read-only Moomoo US paper-account preflight.",
    )
    preflight.add_argument("--discovery-report", type=Path, required=True)
    preflight.add_argument(
        "--host",
        default="127.0.0.1",
        help="Loopback Moomoo OpenD host. Defaults to 127.0.0.1.",
    )
    preflight.add_argument(
        "--port",
        type=int,
        default=11111,
        help="Moomoo OpenD port. Defaults to 11111.",
    )
    preflight.add_argument(
        "--connect",
        action="store_true",
        help="Explicitly load moomoo-api and run the read-only account preflight.",
    )
    preflight.add_argument(
        "--report-output",
        type=Path,
        help="Optional path for a sanitized create-only preflight report.",
    )
    paper_order = subparsers.add_parser(
        "moomoo-paper-order-dry-run",
        description="Build a sanitized Moomoo US paper-order plan offline.",
    )
    _add_moomoo_order_arguments(paper_order)
    submit = subparsers.add_parser(
        "moomoo-paper-order-submit",
        description="Preview or explicitly submit one Moomoo US paper order.",
    )
    _add_moomoo_order_arguments(submit)
    submit.add_argument("--preflight-report", type=Path, required=True)
    submit.add_argument("--host", default="127.0.0.1")
    submit.add_argument("--port", type=int, default=11111)
    submit.add_argument("--connect", action="store_true")
    submit.add_argument("--submit-paper-order", action="store_true")
    submit.add_argument(
        "--acknowledge-paper-order-side-effect",
        action="store_true",
    )
    return parser


def _add_moomoo_order_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--discovery-report", type=Path, required=True)
    command.add_argument("--client-order-id", required=True)
    command.add_argument("--strategy-id", required=True)
    command.add_argument("--code", required=True)
    command.add_argument(
        "--order-style",
        choices=[
            OrderStyle.PASSIVE_LIMIT.value,
            OrderStyle.AGGRESSIVE_LIMIT.value,
        ],
        default=OrderStyle.PASSIVE_LIMIT.value,
    )
    command.add_argument("--quantity", type=int, required=True)
    command.add_argument("--limit-price", type=float, required=True)
    command.add_argument("--stop-price", type=float, required=True)
    command.add_argument("--take-profit-price", type=float)
    command.add_argument("--created-at", required=True)


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


def _run_moomoo_paper_readiness(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    try:
        decision = _read_moomoo_paper_readiness(args.discovery_report)
    except MoomooConfigurationError as exc:
        print(f"error: {exc}", file=stderr)
        return 2

    print(json.dumps(decision.to_dict(), sort_keys=True), file=stdout)
    return 0 if decision.is_ready else 1


def _run_moomoo_paper_account_preflight(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    try:
        endpoint = MoomooEndpoint(host=args.host, port=args.port)
        readiness = _read_moomoo_paper_readiness(args.discovery_report)
    except MoomooConfigurationError as exc:
        print(f"error: {exc}", file=stderr)
        return 2

    if not readiness.is_ready:
        print("error: READINESS_NOT_READY", file=stderr)
        return 1

    if not args.connect:
        print(
            json.dumps(
                {
                    "mode": "validate-only",
                    "probe": "Moomoo US paper-account read-only preflight",
                    "localhost_endpoint": endpoint.display,
                    "readiness_status": "READY",
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
        print("error: Moomoo paper-account preflight failed (dependency)", file=stderr)
        return 1

    result = MoomooPaperAccountPreflight(endpoint=endpoint, sdk=sdk).run(
        readiness=readiness
    )
    print(json.dumps(result.to_dict(), sort_keys=True), file=stdout)
    if args.report_output is not None:
        try:
            MoomooPaperAccountPreflightReportWriter().write(
                args.report_output,
                result,
            )
        except MoomooConfigurationError as exc:
            print(f"error: {exc}", file=stderr)
            return 2
    return 0 if result.sanitized_failure_category is None else 1


def _run_moomoo_paper_order_dry_run(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    prepared = _prepare_moomoo_paper_order(args, stderr=stderr)
    if isinstance(prepared, int):
        return prepared
    _, plan = prepared
    print(json.dumps(plan.to_dict(), sort_keys=True), file=stdout)
    return 0


def _prepare_moomoo_paper_order(
    args: argparse.Namespace,
    *,
    stderr: TextIO,
):
    try:
        created_at = datetime.fromisoformat(args.created_at)
    except ValueError:
        print("error: created-at must be an ISO 8601 timestamp", file=stderr)
        return 2
    if created_at.tzinfo is None:
        print("error: created-at must include a timezone offset", file=stderr)
        return 2

    prices = [args.limit_price, args.stop_price]
    if args.take_profit_price is not None:
        prices.append(args.take_profit_price)
    if not all(math.isfinite(price) for price in prices):
        print("error: invalid paper-order fields", file=stderr)
        return 2

    try:
        readiness = _read_moomoo_paper_readiness(args.discovery_report)
    except MoomooConfigurationError as exc:
        print(f"error: {exc}", file=stderr)
        return 2

    try:
        intent = OrderIntent(
            client_order_id=args.client_order_id,
            strategy_id=args.strategy_id,
            symbol=args.code,
            market=Market.US,
            side=Side.BUY,
            quantity=args.quantity,
            order_style=OrderStyle(args.order_style),
            limit_price=args.limit_price,
            stop_price=args.stop_price,
            take_profit_price=args.take_profit_price,
            created_at=created_at,
        )
    except ValueError:
        print("error: invalid paper-order fields", file=stderr)
        return 2

    try:
        plan = MoomooPaperOrderDryRunPlanner().plan(
            intent,
            readiness=readiness,
        )
    except MoomooPaperOrderPlanError as exc:
        print(f"error: {exc.reason.value}", file=stderr)
        return 1
    return readiness, plan


def _run_moomoo_paper_order_submit(
    args: argparse.Namespace,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    prepared = _prepare_moomoo_paper_order(args, stderr=stderr)
    if isinstance(prepared, int):
        return prepared
    readiness, plan = prepared
    try:
        endpoint = MoomooEndpoint(host=args.host, port=args.port)
        preflight = MoomooPaperAccountPreflightReportReader().read(
            args.preflight_report
        )
    except MoomooConfigurationError as exc:
        print(f"error: {exc}", file=stderr)
        return 2

    confirmations = (
        args.connect,
        args.submit_paper_order,
        args.acknowledge_paper_order_side_effect,
    )
    if not any(confirmations):
        print(
            json.dumps(
                {
                    "mode": "preview-only",
                    "submission_status": "not-run",
                    "plan": plan.to_dict(),
                    "preflight_schema_version": preflight.schema_version,
                },
                sort_keys=True,
            ),
            file=stdout,
        )
        return 0
    if not all(confirmations):
        print(
            "error: --connect, --submit-paper-order, and "
            "--acknowledge-paper-order-side-effect are all required",
            file=stderr,
        )
        return 2
    try:
        sdk = MoomooApiSdk.load()
    except MoomooClientError:
        print("error: Moomoo paper-order submission failed (dependency)", file=stderr)
        return 1

    result = MoomooPaperOrderSubmitter(endpoint=endpoint, sdk=sdk).submit(
        plan,
        readiness=readiness,
        preflight=preflight,
        acknowledged=True,
    )
    print(json.dumps(result.to_dict(), sort_keys=True), file=stdout)
    return (
        0
        if result.status == MoomooPaperOrderSubmissionStatus.VERIFIED
        else 1
    )


def _read_moomoo_paper_readiness(
    report_path: Path,
) -> MoomooPaperReadinessDecision:
    discovery = MoomooDiscoveryReportReader().read(report_path)
    return MoomooPaperReadinessGate().evaluate(discovery)


if __name__ == "__main__":
    raise SystemExit(main())
