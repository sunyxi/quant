from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from autotrade.execution.moomoo import (
    MOOMOO_VALID_ENTITLEMENTS,
    MoomooDiscoveryResult,
)


MOOMOO_PAPER_READINESS_SCHEMA_VERSION = 1


class MoomooPaperReadinessStatus(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class MoomooPaperReadinessReason(StrEnum):
    DISCOVERY_FAILED = "DISCOVERY_FAILED"
    QUOTE_CONNECTION_NOT_OK = "QUOTE_CONNECTION_NOT_OK"
    TRADE_CONNECTION_NOT_OK = "TRADE_CONNECTION_NOT_OK"
    QUOTE_NOT_LOGGED_IN = "QUOTE_NOT_LOGGED_IN"
    TRADE_NOT_LOGGED_IN = "TRADE_NOT_LOGGED_IN"
    PAPER_ACCOUNT_UNAVAILABLE = "PAPER_ACCOUNT_UNAVAILABLE"
    US_MARKET_UNAUTHORIZED = "US_MARKET_UNAUTHORIZED"
    US_QUOTE_ENTITLEMENT_UNAVAILABLE = "US_QUOTE_ENTITLEMENT_UNAVAILABLE"


@dataclass(frozen=True)
class MoomooPaperReadinessEvidence:
    discovery_schema_version: int
    quote_connection_ok: bool
    trade_connection_ok: bool
    qot_logged_in: bool | None
    trd_logged_in: bool | None
    paper_account_count: int
    paper_account_available: bool
    us_market_authorized: bool
    us_quote_entitlement: str

    def to_dict(self) -> dict[str, object]:
        return {
            "discovery_schema_version": self.discovery_schema_version,
            "quote_connection_ok": self.quote_connection_ok,
            "trade_connection_ok": self.trade_connection_ok,
            "qot_logged_in": self.qot_logged_in,
            "trd_logged_in": self.trd_logged_in,
            "paper_account_count": self.paper_account_count,
            "paper_account_available": self.paper_account_available,
            "us_market_authorized": self.us_market_authorized,
            "us_quote_entitlement": self.us_quote_entitlement,
        }


@dataclass(frozen=True)
class MoomooPaperReadinessDecision:
    status: MoomooPaperReadinessStatus
    reason_codes: tuple[MoomooPaperReadinessReason, ...]
    evidence: MoomooPaperReadinessEvidence
    schema_version: int = MOOMOO_PAPER_READINESS_SCHEMA_VERSION

    @property
    def is_ready(self) -> bool:
        return self.status == MoomooPaperReadinessStatus.READY

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "evidence": self.evidence.to_dict(),
        }


@dataclass(frozen=True)
class MoomooPaperReadinessGate:
    def evaluate(
        self,
        discovery: MoomooDiscoveryResult,
    ) -> MoomooPaperReadinessDecision:
        us_quote_entitlement = (
            discovery.us_quote_entitlement
            if discovery.us_quote_entitlement in MOOMOO_VALID_ENTITLEMENTS
            else "UNKNOWN"
        )
        evidence = MoomooPaperReadinessEvidence(
            discovery_schema_version=discovery.schema_version,
            quote_connection_ok=discovery.quote_connection_status == "ok",
            trade_connection_ok=discovery.trade_connection_status == "ok",
            qot_logged_in=discovery.qot_logged_in,
            trd_logged_in=discovery.trd_logged_in,
            paper_account_count=discovery.paper_account_count,
            paper_account_available=discovery.paper_account_available,
            us_market_authorized=discovery.us_market_authorized,
            us_quote_entitlement=us_quote_entitlement,
        )

        if discovery.sanitized_failure_category is not None:
            return self._blocked(
                evidence,
                (MoomooPaperReadinessReason.DISCOVERY_FAILED,),
            )

        reasons: list[MoomooPaperReadinessReason] = []
        if discovery.quote_connection_status != "ok":
            reasons.append(MoomooPaperReadinessReason.QUOTE_CONNECTION_NOT_OK)
        if discovery.trade_connection_status != "ok":
            reasons.append(MoomooPaperReadinessReason.TRADE_CONNECTION_NOT_OK)
        if discovery.qot_logged_in is not True:
            reasons.append(MoomooPaperReadinessReason.QUOTE_NOT_LOGGED_IN)
        if discovery.trd_logged_in is not True:
            reasons.append(MoomooPaperReadinessReason.TRADE_NOT_LOGGED_IN)
        if (
            not discovery.paper_account_available
            or discovery.paper_account_count < 1
        ):
            reasons.append(MoomooPaperReadinessReason.PAPER_ACCOUNT_UNAVAILABLE)
        if not discovery.us_market_authorized:
            reasons.append(MoomooPaperReadinessReason.US_MARKET_UNAUTHORIZED)
        if us_quote_entitlement in {"NO", "UNKNOWN"}:
            reasons.append(
                MoomooPaperReadinessReason.US_QUOTE_ENTITLEMENT_UNAVAILABLE
            )

        if reasons:
            return self._blocked(evidence, tuple(reasons))
        return MoomooPaperReadinessDecision(
            status=MoomooPaperReadinessStatus.READY,
            reason_codes=(),
            evidence=evidence,
        )

    def _blocked(
        self,
        evidence: MoomooPaperReadinessEvidence,
        reasons: tuple[MoomooPaperReadinessReason, ...],
    ) -> MoomooPaperReadinessDecision:
        return MoomooPaperReadinessDecision(
            status=MoomooPaperReadinessStatus.BLOCKED,
            reason_codes=reasons,
            evidence=evidence,
        )
