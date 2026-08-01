from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Protocol

from autotrade.execution.moomoo import (
    MIN_MOOMOO_API_VERSION,
    MoomooEndpoint,
    MoomooPaperAccountPreflightResult,
    MoomooResponseError,
    _field,
    _records,
    _safe_close,
    _safe_version,
    _version_at_least,
    is_moomoo_us_paper_account_eligible,
)
from autotrade.execution.moomoo_paper_order import MoomooPaperOrderPlan
from autotrade.execution.moomoo_readiness import MoomooPaperReadinessDecision


MOOMOO_PAPER_ORDER_SUBMISSION_SCHEMA_VERSION = 1
_REFRESH_CACHE = True


class MoomooPaperOrderSubmissionStatus(StrEnum):
    BLOCKED = "blocked"
    REJECTED = "rejected"
    UNKNOWN = "unknown"
    SUBMITTED = "submitted"
    VERIFIED = "verified"


class MoomooPaperSubmitContext(Protocol):
    def get_acc_list(self) -> tuple[int, object]: ...

    def place_order(self, **kwargs: object) -> tuple[int, object]: ...

    def order_list_query(self, **kwargs: object) -> tuple[int, object]: ...

    def close(self) -> None: ...


class MoomooPaperSubmitSdk(Protocol):
    version: str
    ret_ok: int
    simulate_trade_environment: object
    buy_trade_side: object
    normal_order_type: object
    day_time_in_force: object
    rth_session: object

    def create_us_trade_context(
        self,
        endpoint: MoomooEndpoint,
    ) -> MoomooPaperSubmitContext: ...


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


@dataclass(frozen=True)
class MoomooPaperOrderSubmitter:
    endpoint: MoomooEndpoint
    sdk: MoomooPaperSubmitSdk

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

        sdk_version = _safe_version(self.sdk.version)
        if not _version_at_least(sdk_version, MIN_MOOMOO_API_VERSION):
            return MoomooPaperOrderSubmissionResult(
                **base,
                sdk_version=sdk_version,
                sanitized_failure_category="version",
            )
        base["sdk_version"] = sdk_version

        context: MoomooPaperSubmitContext | None = None
        state: dict[str, object] = dict(base)
        try:
            context = self.sdk.create_us_trade_context(self.endpoint)
            accounts = self._read_records(context.get_acc_list())
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
            account_id = _field(eligible[0], "acc_id")
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
            orders = self._read_records(query_response)
            state["verification_query_status"] = "ok"
            matches = [
                row
                for row in orders
                if _field(row, "remark") == plan.client_order_id
            ]
            state["verification_match_count"] = len(matches)
            if len(matches) != 1:
                return MoomooPaperOrderSubmissionResult(
                    **state,
                    sanitized_failure_category="verification",
                )
            state["status"] = MoomooPaperOrderSubmissionStatus.VERIFIED
            return MoomooPaperOrderSubmissionResult(**state)
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
            _safe_close(context)

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
        if not (
            preflight.sanitized_failure_category is None
            and preflight.connection_status == "ok"
            and preflight.account_selection_status == "unique"
            and preflight.eligible_account_count == 1
            and preflight.funds_query_status == "ok"
            and preflight.positions_query_status == "ok"
            and preflight.orders_query_status == "ok"
            and preflight.endpoint == self.endpoint.display
        ):
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

    def _read_records(self, response: tuple[int, object]) -> list[object]:
        if not isinstance(response, tuple) or len(response) != 2:
            raise ValueError("invalid response")
        status, payload = response
        if status != self.sdk.ret_ok:
            raise ValueError("request failed")
        return _records(payload)

    def _submission_outcome(self, response: tuple[int, object]) -> str:
        if not isinstance(response, tuple) or len(response) != 2:
            return "unknown"
        if response[0] != self.sdk.ret_ok:
            return "rejected"
        try:
            return "accepted" if _records(response[1]) else "unknown"
        except MoomooResponseError:
            return "unknown"
