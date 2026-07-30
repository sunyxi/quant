from __future__ import annotations

import unittest
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from autotrade.core.models import Fill, Market, OrderIntent, OrderStyle, Side
from autotrade.execution.kabu_station import (
    KabuStationClientError,
    KabuStationReadOnlyReconciler,
)
from autotrade.execution.ledger import LocalExecutionLedger
from autotrade.execution.oms import OrderState, OrderStateMachine
from autotrade.execution.reconciliation import ReconciliationSeverity
from autotrade.risk.manager import RiskConfig, RiskManager


class FakeReadOnlyClient:
    def __init__(
        self,
        *,
        orders: list[dict[str, Any]] | Exception | None = None,
        positions: list[dict[str, Any]] | Exception | None = None,
    ) -> None:
        self.orders = [] if orders is None else orders
        self.positions = [] if positions is None else positions
        self.calls: list[dict[str, Any]] = []

    def get_orders(
        self,
        api_token: str,
        product: str | None = None,
        symbol: str | None = None,
        details: bool | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "operation": "orders",
                "api_token": api_token,
                "product": product,
                "symbol": symbol,
                "details": details,
            }
        )
        if isinstance(self.orders, Exception):
            raise self.orders
        return self.orders

    def get_positions(
        self,
        api_token: str,
        product: str | None = None,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "operation": "positions",
                "api_token": api_token,
                "product": product,
                "symbol": symbol,
            }
        )
        if isinstance(self.positions, Exception):
            raise self.positions
        return self.positions


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


class KabuStationReadOnlyReconcilerTests(unittest.TestCase):
    def test_matching_local_and_broker_state_has_no_critical_discrepancy(self) -> None:
        oms = OrderStateMachine()
        intent = _intent()
        oms.register(intent)
        oms.transition(intent.client_order_id, OrderState.RISK_APPROVED)
        oms.transition(intent.client_order_id, OrderState.SUBMITTED)
        oms.transition(intent.client_order_id, OrderState.ACKNOWLEDGED)
        ledger = LocalExecutionLedger()
        ledger.record_order(intent)
        ledger.record_fill(_fill())
        client = FakeReadOnlyClient(
            orders=[{"ID": intent.client_order_id, "Symbol": "7203", "LeavesQty": 100}],
            positions=[
                {
                    "ExecutionID": "position-1",
                    "Symbol": "7203",
                    "Side": "2",
                    "LeavesQty": 100,
                }
            ],
        )

        report = KabuStationReadOnlyReconciler(client=client).reconcile(
            api_token="token-123",
            oms=oms,
            ledger=ledger,
        )

        self.assertFalse(report.has_critical)

    def test_broker_open_order_missing_from_oms_is_critical(self) -> None:
        client = FakeReadOnlyClient(
            orders=[{"ID": "broker-only", "Symbol": "7203", "LeavesQty": 100}],
            positions=[],
        )

        report = KabuStationReadOnlyReconciler(client=client).reconcile(
            api_token="token-123",
            oms=OrderStateMachine(),
            ledger=LocalExecutionLedger(),
        )

        self.assertTrue(report.has_critical)
        self.assertEqual(report.discrepancies[0].severity, ReconciliationSeverity.CRITICAL)
        self.assertEqual(report.discrepancies[0].kind, "BROKER_ORDER_MISSING_LOCAL")

    def test_position_quantity_mismatch_is_critical(self) -> None:
        intent = _intent()
        ledger = LocalExecutionLedger()
        ledger.record_order(intent)
        ledger.record_fill(_fill())
        client = FakeReadOnlyClient(
            orders=[],
            positions=[
                {
                    "ExecutionID": "position-1",
                    "Symbol": "7203",
                    "Side": "2",
                    "LeavesQty": 200,
                }
            ],
        )

        report = KabuStationReadOnlyReconciler(client=client).reconcile(
            api_token="token-123",
            oms=OrderStateMachine(),
            ledger=ledger,
        )

        self.assertTrue(report.has_critical)
        self.assertEqual(report.discrepancies[0].kind, "POSITION_MISMATCH")

    def test_critical_discrepancy_pauses_configured_risk_manager(self) -> None:
        risk = RiskManager(RiskConfig(account_equity=1_000_000))
        client = FakeReadOnlyClient(
            orders=[{"ID": "broker-only", "Symbol": "7203", "LeavesQty": 100}],
            positions=[],
        )

        report = KabuStationReadOnlyReconciler(client=client).reconcile(
            api_token="token-123",
            oms=OrderStateMachine(),
            ledger=LocalExecutionLedger(),
            risk_manager=risk,
        )

        self.assertTrue(report.has_critical)
        self.assertTrue(risk.state.is_paused)
        self.assertEqual(risk.state.pause_reason, "reconciliation discrepancy")

    def test_orders_and_positions_requests_pass_supplied_token_and_filters(self) -> None:
        client = FakeReadOnlyClient()

        KabuStationReadOnlyReconciler(client=client).reconcile(
            api_token="token-123",
            oms=OrderStateMachine(),
            ledger=LocalExecutionLedger(),
            product="1",
            symbol="7203",
            details=True,
        )

        self.assertEqual(
            client.calls,
            [
                {
                    "operation": "orders",
                    "api_token": "token-123",
                    "product": "1",
                    "symbol": "7203",
                    "details": True,
                },
                {
                    "operation": "positions",
                    "api_token": "token-123",
                    "product": "1",
                    "symbol": "7203",
                },
            ],
        )

    def test_client_error_propagates(self) -> None:
        client = FakeReadOnlyClient(orders=KabuStationClientError("orders failed"))

        with self.assertRaisesRegex(KabuStationClientError, "orders failed"):
            KabuStationReadOnlyReconciler(client=client).reconcile(
                api_token="token-123",
                oms=OrderStateMachine(),
                ledger=LocalExecutionLedger(),
            )

    def test_mapper_error_propagates(self) -> None:
        client = FakeReadOnlyClient(
            orders=[{"Symbol": "7203", "LeavesQty": 100}],
            positions=[],
        )

        with self.assertRaises(KabuStationClientError):
            KabuStationReadOnlyReconciler(client=client).reconcile(
                api_token="token-123",
                oms=OrderStateMachine(),
                ledger=LocalExecutionLedger(),
            )


if __name__ == "__main__":
    unittest.main()
