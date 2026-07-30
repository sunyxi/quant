from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

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
