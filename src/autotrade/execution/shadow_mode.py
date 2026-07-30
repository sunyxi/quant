from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from autotrade.execution.replay import ReplayExecutionResult
from autotrade.risk.manager import RiskManager


class ShadowModeReadinessStatus(StrEnum):
    PASSED = "PASSED"
    BLOCKED = "BLOCKED"


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
            "trading_date": self.trading_date,
            "status": self.status.value,
            "reasons": list(self.reasons),
            "metrics": dict(self.metrics),
        }


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
