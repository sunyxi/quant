from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from autotrade.core.models import Fill, Market, OrderIntent, OrderStyle, Side
from autotrade.execution.ledger import LocalExecutionLedger
from autotrade.execution.oms import OrderState, OrderStateMachine
from autotrade.execution.reconciliation import (
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerStateSnapshot,
    ReconciliationEngine,
    ReconciliationSeverity,
)
from autotrade.risk.manager import RiskConfig, RiskManager


def _intent(client_order_id: str = "client-1", symbol: str = "7203.T") -> OrderIntent:
    return OrderIntent(
        client_order_id=client_order_id,
        strategy_id="test_strategy",
        symbol=symbol,
        market=Market.JP,
        side=Side.BUY,
        quantity=100,
        order_style=OrderStyle.PASSIVE_LIMIT,
        limit_price=1000,
        stop_price=990,
        take_profit_price=1020,
        created_at=datetime(2026, 7, 28, 9, 30, tzinfo=ZoneInfo("Asia/Tokyo")),
    )


def _fill(client_order_id: str = "client-1", symbol: str = "7203.T") -> Fill:
    return Fill(
        client_order_id=client_order_id,
        symbol=symbol,
        side=Side.BUY,
        quantity=100,
        price=1000,
        filled_at=datetime(2026, 7, 28, 9, 31, tzinfo=ZoneInfo("Asia/Tokyo")),
    )


class ReconciliationTests(unittest.TestCase):
    def test_reports_unknown_local_order_state(self) -> None:
        oms = OrderStateMachine()
        record = oms.register(_intent())
        oms.transition(record.client_order_id, OrderState.RISK_APPROVED)
        oms.transition(record.client_order_id, OrderState.SUBMITTED)
        oms.mark_unknown(record.client_order_id, reason="submit timeout")

        report = ReconciliationEngine().check(
            oms=oms,
            ledger=LocalExecutionLedger(),
            broker=BrokerStateSnapshot(),
        )

        self.assertTrue(report.has_critical)
        self.assertEqual(report.discrepancies[0].severity, ReconciliationSeverity.CRITICAL)

    def test_reports_position_quantity_mismatch(self) -> None:
        ledger = LocalExecutionLedger()
        ledger.record_order(_intent())
        ledger.record_fill(_fill())

        report = ReconciliationEngine().check(
            oms=OrderStateMachine(),
            ledger=ledger,
            broker=BrokerStateSnapshot(
                positions=[BrokerPositionSnapshot(symbol="7203.T", quantity=0)]
            ),
        )

        self.assertTrue(report.has_critical)
        self.assertEqual(report.discrepancies[0].kind, "POSITION_MISMATCH")

    def test_reports_broker_order_missing_locally(self) -> None:
        report = ReconciliationEngine().check(
            oms=OrderStateMachine(),
            ledger=LocalExecutionLedger(),
            broker=BrokerStateSnapshot(
                open_orders=[
                    BrokerOrderSnapshot(client_order_id="client-missing", symbol="7203.T")
                ]
            ),
        )

        self.assertTrue(report.has_critical)
        self.assertEqual(report.discrepancies[0].kind, "BROKER_ORDER_MISSING_LOCAL")

    def test_critical_discrepancy_pauses_risk_manager(self) -> None:
        risk = RiskManager(RiskConfig(account_equity=1_000_000))
        report = ReconciliationEngine().check(
            oms=OrderStateMachine(),
            ledger=LocalExecutionLedger(),
            broker=BrokerStateSnapshot(
                open_orders=[
                    BrokerOrderSnapshot(client_order_id="client-missing", symbol="7203.T")
                ]
            ),
            risk_manager=risk,
        )

        self.assertTrue(report.has_critical)
        self.assertTrue(risk.state.is_paused)
        self.assertEqual(risk.state.pause_reason, "reconciliation discrepancy")


if __name__ == "__main__":
    unittest.main()
