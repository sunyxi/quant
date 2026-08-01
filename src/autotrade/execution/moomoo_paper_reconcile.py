from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from autotrade.execution.moomoo import (
    MIN_MOOMOO_API_VERSION,
    MoomooEndpoint,
    MoomooPaperAccountPreflightResult,
    MoomooSdkSource,
    MoomooTradeContext,
    close_moomoo_context,
    is_moomoo_paper_preflight_successful,
    is_moomoo_us_paper_account_eligible,
    is_moomoo_version_at_least,
    moomoo_field,
    normalize_moomoo_version,
    parse_moomoo_response_records,
)
from autotrade.execution.moomoo_paper_order import (
    is_valid_moomoo_client_order_id,
)
from autotrade.execution.moomoo_readiness import MoomooPaperReadinessDecision


MOOMOO_PAPER_ORDER_RECONCILIATION_SCHEMA_VERSION = 1
_REFRESH_CACHE = True


class MoomooPaperOrderReconciliationStatus(StrEnum):
    BLOCKED = "blocked"
    UNKNOWN = "unknown"
    ABSENT = "absent"
    UNIQUE = "unique"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class MoomooPaperOrderReconciliationResult:
    client_order_id: str
    status: MoomooPaperOrderReconciliationStatus
    schema_version: int = MOOMOO_PAPER_ORDER_RECONCILIATION_SCHEMA_VERSION
    endpoint: str = "127.0.0.1:11111"
    sdk_version: str = "UNKNOWN"
    readiness_schema_version: int = 0
    preflight_schema_version: int = 0
    account_selection_status: str = "not-run"
    eligible_account_count: int = 0
    query_status: str = "not-run"
    match_count: int = 0
    refresh_cache: bool = _REFRESH_CACHE
    sanitized_failure_category: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


def validate_moomoo_paper_reconciliation_evidence(
    client_order_id: object,
    *,
    endpoint: MoomooEndpoint,
    readiness: MoomooPaperReadinessDecision,
    preflight: MoomooPaperAccountPreflightResult,
) -> str | None:
    if not is_valid_moomoo_client_order_id(client_order_id):
        return "client_order_id"
    if not readiness.is_ready:
        return "readiness"
    if not is_moomoo_paper_preflight_successful(preflight, endpoint):
        return "preflight"
    return None


@dataclass(frozen=True)
class MoomooPaperOrderReconciler:
    endpoint: MoomooEndpoint
    sdk: MoomooSdkSource

    def reconcile(
        self,
        client_order_id: str,
        *,
        readiness: MoomooPaperReadinessDecision,
        preflight: MoomooPaperAccountPreflightResult,
    ) -> MoomooPaperOrderReconciliationResult:
        state: dict[str, object] = {
            "client_order_id": client_order_id,
            "status": MoomooPaperOrderReconciliationStatus.BLOCKED,
            "endpoint": self.endpoint.display,
            "readiness_schema_version": readiness.schema_version,
            "preflight_schema_version": preflight.schema_version,
        }
        failure = validate_moomoo_paper_reconciliation_evidence(
            client_order_id,
            endpoint=self.endpoint,
            readiness=readiness,
            preflight=preflight,
        )
        if failure is not None:
            return MoomooPaperOrderReconciliationResult(
                **state,
                sanitized_failure_category=failure,
            )

        try:
            sdk_version = normalize_moomoo_version(self.sdk.version)
        except Exception:
            return MoomooPaperOrderReconciliationResult(
                **state,
                sanitized_failure_category="dependency",
            )
        if not is_moomoo_version_at_least(sdk_version, MIN_MOOMOO_API_VERSION):
            return MoomooPaperOrderReconciliationResult(
                **state,
                sdk_version=sdk_version,
                sanitized_failure_category="version",
            )
        state["sdk_version"] = sdk_version

        context: MoomooTradeContext | None = None
        query_attempted = False
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
                return MoomooPaperOrderReconciliationResult(
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
                return MoomooPaperOrderReconciliationResult(
                    **state,
                    sanitized_failure_category="account",
                )
            state["account_selection_status"] = "unique"

            query_attempted = True
            response = context.order_list_query(
                trd_env=self.sdk.simulate_trade_environment,
                acc_id=account_id,
                refresh_cache=_REFRESH_CACHE,
            )
            rows = parse_moomoo_response_records(
                response,
                ret_ok=self.sdk.ret_ok,
            )
            state["query_status"] = "ok"
            matches = [
                row
                for row in rows
                if moomoo_field(row, "remark") == client_order_id
            ]
            state["match_count"] = len(matches)
            if not matches:
                state["status"] = MoomooPaperOrderReconciliationStatus.ABSENT
                state["sanitized_failure_category"] = "not_visible"
            elif len(matches) == 1:
                state["status"] = MoomooPaperOrderReconciliationStatus.UNIQUE
            else:
                state["status"] = MoomooPaperOrderReconciliationStatus.DUPLICATE
                state["sanitized_failure_category"] = "ambiguous"
            return MoomooPaperOrderReconciliationResult(**state)
        except Exception:
            state["status"] = MoomooPaperOrderReconciliationStatus.UNKNOWN
            if query_attempted:
                state["query_status"] = "failed"
                category = "query"
            elif context is None:
                category = "connection"
            else:
                category = "account"
            return MoomooPaperOrderReconciliationResult(
                **state,
                sanitized_failure_category=category,
            )
        finally:
            close_moomoo_context(context)
