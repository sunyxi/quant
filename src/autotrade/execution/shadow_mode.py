from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from autotrade.execution.replay import ReplayExecutionResult
from autotrade.risk.manager import RiskManager


SHADOW_MODE_SUMMARY_SCHEMA_VERSION = 1


class ShadowModeReadinessStatus(StrEnum):
    PASSED = "PASSED"
    BLOCKED = "BLOCKED"


class ShadowModeSummaryError(ValueError):
    pass


@dataclass(frozen=True)
class ShadowModeReadinessDecision:
    status: ShadowModeReadinessStatus
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, int] = field(default_factory=dict)

    @property
    def is_passed(self) -> bool:
        return self.status == ShadowModeReadinessStatus.PASSED


@dataclass(frozen=True)
class ShadowModeRunSummary:
    trading_date: str
    status: ShadowModeReadinessStatus
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, int] = field(default_factory=dict)
    schema_version: int = SHADOW_MODE_SUMMARY_SCHEMA_VERSION

    @classmethod
    def from_readiness_decision(
        cls,
        *,
        trading_date: str,
        decision: ShadowModeReadinessDecision,
    ) -> ShadowModeRunSummary:
        return cls(
            trading_date=trading_date,
            status=decision.status,
            reasons=list(decision.reasons),
            metrics=dict(decision.metrics),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "trading_date": self.trading_date,
            "status": self.status.value,
            "reasons": list(self.reasons),
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True)
class ShadowModeSummaryReview:
    total_runs: int
    passed_runs: int
    blocked_runs: int
    trading_dates: list[str] = field(default_factory=list)
    blocking_reasons: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_summaries(
        cls,
        summaries: list[ShadowModeRunSummary],
    ) -> ShadowModeSummaryReview:
        if not summaries:
            raise ShadowModeSummaryError("empty Shadow Mode summary review")

        passed_runs = sum(
            1 for summary in summaries if summary.status == ShadowModeReadinessStatus.PASSED
        )
        blocked_runs = sum(
            1
            for summary in summaries
            if summary.status == ShadowModeReadinessStatus.BLOCKED
        )
        blocking_reasons: dict[str, int] = {}
        for summary in summaries:
            if summary.status != ShadowModeReadinessStatus.BLOCKED:
                continue
            for reason in summary.reasons:
                blocking_reasons[reason] = blocking_reasons.get(reason, 0) + 1

        return cls(
            total_runs=len(summaries),
            passed_runs=passed_runs,
            blocked_runs=blocked_runs,
            trading_dates=sorted({summary.trading_date for summary in summaries}),
            blocking_reasons=dict(sorted(blocking_reasons.items())),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "total_runs": self.total_runs,
            "passed_runs": self.passed_runs,
            "blocked_runs": self.blocked_runs,
            "trading_dates": list(self.trading_dates),
            "blocking_reasons": dict(self.blocking_reasons),
        }


@dataclass(frozen=True)
class ShadowModeReviewWriter:
    def write(self, review: ShadowModeSummaryReview, path: Path) -> Path:
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(review.to_dict(), sort_keys=True)
        path.write_text(f"{payload}\n", encoding="utf-8")
        return path


@dataclass(frozen=True)
class ShadowModeSummaryWriter:
    def write(self, summary: ShadowModeRunSummary, path: Path) -> Path:
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(summary.to_dict(), sort_keys=True)
        path.write_text(f"{payload}\n", encoding="utf-8")
        return path


@dataclass(frozen=True)
class ShadowModeSummaryReader:
    def read(self, path: Path) -> ShadowModeRunSummary:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ShadowModeSummaryError("summary payload must be an object")

        schema_version = payload.get("schema_version")
        if schema_version != SHADOW_MODE_SUMMARY_SCHEMA_VERSION:
            raise ShadowModeSummaryError(
                "summary payload schema_version must be 1"
            )

        trading_date = payload.get("trading_date")
        if not isinstance(trading_date, str) or not trading_date:
            raise ShadowModeSummaryError("summary payload missing trading_date")

        status_value = payload.get("status")
        if not isinstance(status_value, str):
            raise ShadowModeSummaryError("summary payload missing status")
        try:
            status = ShadowModeReadinessStatus(status_value)
        except ValueError as exc:
            raise ShadowModeSummaryError(
                f"unknown Shadow Mode readiness status: {status_value}"
            ) from exc

        reasons = payload.get("reasons")
        if not isinstance(reasons, list) or not all(
            isinstance(reason, str) for reason in reasons
        ):
            raise ShadowModeSummaryError("summary payload reasons must be a string list")

        metrics = payload.get("metrics")
        if not isinstance(metrics, dict) or not all(
            isinstance(key, str) and isinstance(value, int)
            for key, value in metrics.items()
        ):
            raise ShadowModeSummaryError("summary payload metrics must be integer values")

        return ShadowModeRunSummary(
            trading_date=trading_date,
            status=status,
            reasons=list(reasons),
            metrics=dict(metrics),
            schema_version=schema_version,
        )


@dataclass(frozen=True)
class ShadowModeReadinessGate:
    require_reconciliation_evidence: bool = True
    require_no_open_orders: bool = True

    def evaluate(
        self,
        result: ReplayExecutionResult,
        *,
        risk_manager: RiskManager | None = None,
    ) -> ShadowModeReadinessDecision:
        reports = result.reconciliation_reports
        critical_reports = sum(1 for report in reports if report.has_critical)
        open_orders = len(result.broker.open_orders())
        metrics = {
            "intents": len(result.intents),
            "fills": len(result.fills),
            "reconciliation_reports": len(reports),
            "critical_reports": critical_reports,
            "open_orders": open_orders,
        }
        reasons: list[str] = []

        if self.require_reconciliation_evidence and not reports:
            reasons.append("missing reconciliation evidence")
        if critical_reports:
            reasons.append("critical reconciliation discrepancy")
        if self.require_no_open_orders and open_orders:
            reasons.append("open simulated broker orders remain")
        if risk_manager is not None and risk_manager.state.is_paused:
            pause_reason = risk_manager.state.pause_reason or "unknown"
            reasons.append(f"risk paused: {pause_reason}")

        status = (
            ShadowModeReadinessStatus.BLOCKED
            if reasons
            else ShadowModeReadinessStatus.PASSED
        )
        return ShadowModeReadinessDecision(
            status=status,
            reasons=reasons,
            metrics=metrics,
        )
