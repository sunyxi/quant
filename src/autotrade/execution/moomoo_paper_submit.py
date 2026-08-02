from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Mapping

from autotrade.execution.moomoo import (
    MIN_MOOMOO_API_VERSION,
    MoomooConfigurationError,
    MoomooEndpoint,
    MoomooPaperAccountPreflightResult,
    MoomooResponseError,
    MoomooSdkSource,
    MoomooTradeContext,
    close_moomoo_context,
    is_moomoo_paper_preflight_successful,
    is_moomoo_version_at_least,
    is_moomoo_us_paper_account_eligible,
    is_valid_moomoo_report_endpoint,
    moomoo_field,
    moomoo_records,
    normalize_moomoo_version,
    parse_moomoo_response_records,
    write_moomoo_create_only_report,
)
from autotrade.execution.moomoo_paper_order import (
    MoomooPaperOrderPlan,
    is_valid_moomoo_client_order_id,
)
from autotrade.execution.moomoo_readiness import MoomooPaperReadinessDecision


MOOMOO_PAPER_ORDER_SUBMISSION_SCHEMA_VERSION = 1
_REFRESH_CACHE = True


class MoomooPaperOrderSubmissionStatus(StrEnum):
    BLOCKED = "blocked"
    REJECTED = "rejected"
    UNKNOWN = "unknown"
    SUBMITTED = "submitted"
    VERIFIED = "verified"


@dataclass(frozen=True)
class MoomooPaperOrderSubmissionResult:
    client_order_id: str
    status: MoomooPaperOrderSubmissionStatus
    schema_version: int = MOOMOO_PAPER_ORDER_SUBMISSION_SCHEMA_VERSION
    endpoint: str = "127.0.0.1:11111"
    sdk_version: str = "UNKNOWN"
    readiness_schema_version: int = 0
    preflight_schema_version: int = 0
    plan_schema_version: int = 0
    account_selection_status: str = "not-run"
    eligible_account_count: int = 0
    place_order_call_count: int = 0
    verification_query_status: str = "not-run"
    verification_match_count: int = 0
    refresh_cache: bool = _REFRESH_CACHE
    sanitized_failure_category: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


class MoomooPaperOrderSubmissionReportWriter:
    def write(
        self,
        path: str | Path,
        result: MoomooPaperOrderSubmissionResult,
    ) -> Path:
        return write_moomoo_create_only_report(
            path,
            result.to_dict(),
            "paper-order submission",
        )


class MoomooPaperOrderSubmissionReportReader:
    def read(self, path: str | Path) -> MoomooPaperOrderSubmissionResult:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise MoomooConfigurationError(
                "could not read the Moomoo paper-order submission report"
            ) from exc
        required = set(MoomooPaperOrderSubmissionResult.__dataclass_fields__)
        if not isinstance(payload, dict) or set(payload) != required:
            raise MoomooConfigurationError(
                "invalid Moomoo paper-order submission report fields"
            )
        payload["status"] = _validate_submission_report_payload(payload)
        return MoomooPaperOrderSubmissionResult(**payload)


@dataclass(frozen=True)
class MoomooPaperOrderSubmitter:
    endpoint: MoomooEndpoint
    sdk: MoomooSdkSource

    def submit(
        self,
        plan: MoomooPaperOrderPlan,
        *,
        readiness: MoomooPaperReadinessDecision,
        preflight: MoomooPaperAccountPreflightResult,
        acknowledged: bool,
    ) -> MoomooPaperOrderSubmissionResult:
        base = {
            "client_order_id": plan.client_order_id,
            "status": MoomooPaperOrderSubmissionStatus.BLOCKED,
            "endpoint": self.endpoint.display,
            "readiness_schema_version": readiness.schema_version,
            "preflight_schema_version": preflight.schema_version,
            "plan_schema_version": plan.schema_version,
        }
        failure = self._evidence_failure(plan, readiness, preflight, acknowledged)
        if failure is not None:
            return MoomooPaperOrderSubmissionResult(
                **base,
                sanitized_failure_category=failure,
            )

        sdk_version = normalize_moomoo_version(self.sdk.version)
        if not is_moomoo_version_at_least(sdk_version, MIN_MOOMOO_API_VERSION):
            return MoomooPaperOrderSubmissionResult(
                **base,
                sdk_version=sdk_version,
                sanitized_failure_category="version",
            )
        base["sdk_version"] = sdk_version

        context: MoomooTradeContext | None = None
        state: dict[str, object] = dict(base)
        try:
            context = self.sdk.create_us_trade_context(self.endpoint)
            accounts = parse_moomoo_response_records(
                context.get_acc_list(),
                ret_ok=self.sdk.ret_ok,
            )
            eligible = [
                row for row in accounts if is_moomoo_us_paper_account_eligible(row)
            ]
            state["eligible_account_count"] = len(eligible)
            if len(eligible) != 1:
                state["account_selection_status"] = "blocked"
                return MoomooPaperOrderSubmissionResult(
                    **state,
                    sanitized_failure_category="account",
                )
            account_id = moomoo_field(eligible[0], "acc_id")
            if not (
                isinstance(account_id, int)
                and not isinstance(account_id, bool)
                and account_id > 0
            ):
                state["account_selection_status"] = "blocked"
                return MoomooPaperOrderSubmissionResult(
                    **state,
                    sanitized_failure_category="account",
                )
            state["account_selection_status"] = "unique"
            try:
                order_kwargs = {
                    "price": plan.price,
                    "qty": plan.quantity,
                    "code": plan.code,
                    "trd_side": self.sdk.buy_trade_side,
                    "order_type": self.sdk.normal_order_type,
                    "trd_env": self.sdk.simulate_trade_environment,
                    "acc_id": account_id,
                    "remark": plan.client_order_id,
                    "time_in_force": self.sdk.day_time_in_force,
                    "fill_outside_rth": False,
                    "session": self.sdk.rth_session,
                }
            except Exception:
                return MoomooPaperOrderSubmissionResult(
                    **state,
                    sanitized_failure_category="dependency",
                )
            state["place_order_call_count"] = 1
            try:
                response = context.place_order(**order_kwargs)
            except Exception:
                state["status"] = MoomooPaperOrderSubmissionStatus.UNKNOWN
                return MoomooPaperOrderSubmissionResult(
                    **state,
                    sanitized_failure_category="submission",
                )
            submission_outcome = self._submission_outcome(response)
            if submission_outcome == "unknown":
                state["status"] = MoomooPaperOrderSubmissionStatus.UNKNOWN
                return MoomooPaperOrderSubmissionResult(
                    **state,
                    sanitized_failure_category="submission",
                )
            if submission_outcome == "rejected":
                state["status"] = MoomooPaperOrderSubmissionStatus.REJECTED
                return MoomooPaperOrderSubmissionResult(
                    **state,
                    sanitized_failure_category="rejection",
                )

            state["status"] = MoomooPaperOrderSubmissionStatus.SUBMITTED
            query_response = context.order_list_query(
                trd_env=self.sdk.simulate_trade_environment,
                acc_id=account_id,
                refresh_cache=_REFRESH_CACHE,
            )
            orders = parse_moomoo_response_records(
                query_response,
                ret_ok=self.sdk.ret_ok,
            )
            state["verification_query_status"] = "ok"
            matches = [
                row
                for row in orders
                if moomoo_field(row, "remark") == plan.client_order_id
            ]
            state["verification_match_count"] = len(matches)
            if len(matches) != 1:
                return MoomooPaperOrderSubmissionResult(
                    **state,
                    sanitized_failure_category="verification",
                )
            state["status"] = MoomooPaperOrderSubmissionStatus.VERIFIED
            return MoomooPaperOrderSubmissionResult(**state)
        except (OSError, MoomooResponseError):
            if state.get("place_order_call_count") == 1:
                state["status"] = MoomooPaperOrderSubmissionStatus.SUBMITTED
                category = "verification"
            else:
                category = "connection"
            return MoomooPaperOrderSubmissionResult(
                **state,
                sanitized_failure_category=category,
            )
        except Exception:
            if state.get("place_order_call_count") == 1:
                state["status"] = MoomooPaperOrderSubmissionStatus.SUBMITTED
                category = "verification"
            else:
                category = "account"
            return MoomooPaperOrderSubmissionResult(
                **state,
                sanitized_failure_category=category,
            )
        finally:
            close_moomoo_context(context)

    def _evidence_failure(
        self,
        plan: MoomooPaperOrderPlan,
        readiness: MoomooPaperReadinessDecision,
        preflight: MoomooPaperAccountPreflightResult,
        acknowledged: bool,
    ) -> str | None:
        if acknowledged is not True:
            return "acknowledgement"
        if not readiness.is_ready:
            return "readiness"
        if not is_moomoo_paper_preflight_successful(preflight, self.endpoint):
            return "preflight"
        if not (
            plan.dry_run is True
            and plan.side == "BUY"
            and plan.order_type == "NORMAL"
            and plan.trd_env == "SIMULATE"
            and plan.time_in_force == "DAY"
            and plan.session == "RTH"
        ):
            return "plan"
        return None

    def _submission_outcome(self, response: tuple[int, object]) -> str:
        if not isinstance(response, tuple) or len(response) != 2:
            return "unknown"
        if response[0] != self.sdk.ret_ok:
            return "rejected"
        try:
            return "accepted" if moomoo_records(response[1]) else "unknown"
        except MoomooResponseError:
            return "unknown"


def _validate_submission_report_payload(
    payload: Mapping[str, object],
) -> MoomooPaperOrderSubmissionStatus:
    if (
        type(payload["schema_version"]) is not int
        or payload["schema_version"]
        != MOOMOO_PAPER_ORDER_SUBMISSION_SCHEMA_VERSION
    ):
        raise MoomooConfigurationError(
            "unsupported Moomoo paper-order submission report schema"
        )
    if not is_valid_moomoo_client_order_id(payload["client_order_id"]):
        raise MoomooConfigurationError(
            "invalid Moomoo paper-order submission report payload"
        )
    if not is_valid_moomoo_report_endpoint(payload["endpoint"]):
        raise MoomooConfigurationError(
            "invalid Moomoo paper-order submission report payload"
        )
    sdk_version = payload["sdk_version"]
    if not isinstance(sdk_version, str) or (
        sdk_version != "UNKNOWN"
        and normalize_moomoo_version(sdk_version) != sdk_version
    ):
        raise MoomooConfigurationError(
            "invalid Moomoo paper-order submission report payload"
        )
    try:
        status = MoomooPaperOrderSubmissionStatus(payload["status"])
    except (TypeError, ValueError) as exc:
        raise MoomooConfigurationError(
            "invalid Moomoo paper-order submission report status"
        ) from exc
    if payload["account_selection_status"] not in {
        "not-run",
        "blocked",
        "unique",
    } or payload["verification_query_status"] not in {"not-run", "ok"}:
        raise MoomooConfigurationError(
            "invalid Moomoo paper-order submission report payload"
        )
    count_fields = {
        "readiness_schema_version",
        "preflight_schema_version",
        "plan_schema_version",
        "eligible_account_count",
        "verification_match_count",
    }
    if any(
        type(payload[field]) is not int or payload[field] < 0
        for field in count_fields
    ):
        raise MoomooConfigurationError(
            "invalid Moomoo paper-order submission report payload"
        )
    place_order_call_count = payload["place_order_call_count"]
    if (
        type(place_order_call_count) is not int
        or place_order_call_count not in {0, 1}
    ):
        raise MoomooConfigurationError(
            "invalid Moomoo paper-order submission report payload"
        )
    if payload["refresh_cache"] is not _REFRESH_CACHE:
        raise MoomooConfigurationError(
            "invalid Moomoo paper-order submission report payload"
        )
    valid_failures = {
        None,
        "acknowledgement",
        "readiness",
        "preflight",
        "plan",
        "version",
        "account",
        "connection",
        "dependency",
        "submission",
        "rejection",
        "verification",
    }
    valid_state = _is_consistent_submission_report_state(payload, status)
    if (
        payload["sanitized_failure_category"] not in valid_failures
        or not valid_state
    ):
        raise MoomooConfigurationError(
            "invalid Moomoo paper-order submission report state"
        )
    return status


def _is_consistent_submission_report_state(
    payload: Mapping[str, object],
    status: MoomooPaperOrderSubmissionStatus,
) -> bool:
    account_status = payload["account_selection_status"]
    eligible_count = payload["eligible_account_count"]
    place_calls = payload["place_order_call_count"]
    query_status = payload["verification_query_status"]
    match_count = payload["verification_match_count"]
    failure = payload["sanitized_failure_category"]
    no_verification = query_status == "not-run" and match_count == 0
    account_ready = account_status == "unique" and eligible_count == 1

    if status == MoomooPaperOrderSubmissionStatus.VERIFIED:
        return (
            account_ready
            and place_calls == 1
            and query_status == "ok"
            and match_count == 1
            and failure is None
        )
    if status == MoomooPaperOrderSubmissionStatus.REJECTED:
        return (
            account_ready
            and place_calls == 1
            and no_verification
            and failure == "rejection"
        )
    if status == MoomooPaperOrderSubmissionStatus.UNKNOWN:
        return (
            account_ready
            and place_calls == 1
            and no_verification
            and failure == "submission"
        )
    if status == MoomooPaperOrderSubmissionStatus.SUBMITTED:
        return (
            account_ready
            and place_calls == 1
            and failure == "verification"
            and (no_verification or (query_status == "ok" and match_count != 1))
        )
    if failure == "account":
        return (
            account_status in {"not-run", "blocked"}
            and (account_status != "not-run" or eligible_count == 0)
            and place_calls == 0
            and no_verification
        )
    if failure == "connection":
        return (
            account_status == "not-run"
            and eligible_count == 0
            and place_calls == 0
            and no_verification
        )
    if failure == "dependency":
        return account_ready and place_calls == 0 and no_verification
    return (
        failure
        in {
            "acknowledgement",
            "readiness",
            "preflight",
            "plan",
            "version",
        }
        and account_status == "not-run"
        and eligible_count == 0
        and place_calls == 0
        and no_verification
    )
