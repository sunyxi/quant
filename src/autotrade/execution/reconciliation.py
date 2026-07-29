from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from autotrade.execution.ledger import LocalExecutionLedger
from autotrade.execution.oms import OrderState, OrderStateMachine
from autotrade.risk.manager import RiskManager


class ReconciliationSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class BrokerOrderSnapshot:
    client_order_id: str
    symbol: str


@dataclass(frozen=True)
class BrokerPositionSnapshot:
    symbol: str
    quantity: int


@dataclass(frozen=True)
class BrokerStateSnapshot:
    open_orders: list[BrokerOrderSnapshot] = field(default_factory=list)
    positions: list[BrokerPositionSnapshot] = field(default_factory=list)


@dataclass(frozen=True)
class ReconciliationDiscrepancy:
    kind: str
    severity: ReconciliationSeverity
    message: str
    symbol: str | None = None
    client_order_id: str | None = None


@dataclass(frozen=True)
class ReconciliationReport:
    discrepancies: list[ReconciliationDiscrepancy] = field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        return any(
            item.severity == ReconciliationSeverity.CRITICAL
            for item in self.discrepancies
        )


class ReconciliationEngine:
    def check(
        self,
        *,
        oms: OrderStateMachine,
        ledger: LocalExecutionLedger,
        broker: BrokerStateSnapshot,
        risk_manager: RiskManager | None = None,
    ) -> ReconciliationReport:
        discrepancies: list[ReconciliationDiscrepancy] = []
        discrepancies.extend(self._unknown_local_orders(oms))
        discrepancies.extend(self._missing_local_broker_orders(oms, broker))
        discrepancies.extend(self._position_mismatches(ledger, broker))

        report = ReconciliationReport(discrepancies=discrepancies)
        if report.has_critical and risk_manager is not None:
            risk_manager.pause("reconciliation discrepancy")
        return report

    @staticmethod
    def _unknown_local_orders(
        oms: OrderStateMachine,
    ) -> list[ReconciliationDiscrepancy]:
        discrepancies: list[ReconciliationDiscrepancy] = []
        for record in oms.orders():
            if record.state == OrderState.UNKNOWN:
                discrepancies.append(
                    ReconciliationDiscrepancy(
                        kind="UNKNOWN_LOCAL_ORDER",
                        severity=ReconciliationSeverity.CRITICAL,
                        message="local order state is unknown and requires broker reconciliation",
                        symbol=record.intent.symbol,
                        client_order_id=record.client_order_id,
                    )
                )
        return discrepancies

    @staticmethod
    def _missing_local_broker_orders(
        oms: OrderStateMachine,
        broker: BrokerStateSnapshot,
    ) -> list[ReconciliationDiscrepancy]:
        discrepancies: list[ReconciliationDiscrepancy] = []
        local_ids = {record.client_order_id for record in oms.orders()}
        for broker_order in broker.open_orders:
            if broker_order.client_order_id not in local_ids:
                discrepancies.append(
                    ReconciliationDiscrepancy(
                        kind="BROKER_ORDER_MISSING_LOCAL",
                        severity=ReconciliationSeverity.CRITICAL,
                        message="broker reports an open order missing from local OMS",
                        symbol=broker_order.symbol,
                        client_order_id=broker_order.client_order_id,
                    )
                )
        return discrepancies

    @staticmethod
    def _position_mismatches(
        ledger: LocalExecutionLedger,
        broker: BrokerStateSnapshot,
    ) -> list[ReconciliationDiscrepancy]:
        discrepancies: list[ReconciliationDiscrepancy] = []
        local_positions = {
            position.symbol: position.quantity
            for position in ledger.positions()
            if position.quantity != 0
        }
        broker_positions = {
            position.symbol: position.quantity
            for position in broker.positions
            if position.quantity != 0
        }
        symbols = set(local_positions) | set(broker_positions)
        for symbol in sorted(symbols):
            local_quantity = local_positions.get(symbol, 0)
            broker_quantity = broker_positions.get(symbol, 0)
            if local_quantity != broker_quantity:
                discrepancies.append(
                    ReconciliationDiscrepancy(
                        kind="POSITION_MISMATCH",
                        severity=ReconciliationSeverity.CRITICAL,
                        message=(
                            f"local quantity {local_quantity} differs from "
                            f"broker quantity {broker_quantity}"
                        ),
                        symbol=symbol,
                    )
                )
        return discrepancies
