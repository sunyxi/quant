from __future__ import annotations

import math
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from pathlib import Path

from autotrade.core.models import Market, OrderIntent, OrderStyle, Side
from autotrade.execution.moomoo_paper_order import (
    MoomooPaperOrderDryRunPlanner,
    MoomooPaperOrderPlanError,
    MoomooPaperOrderPlanReason,
)
from autotrade.execution.moomoo_readiness import MoomooPaperReadinessGate
from tests.test_moomoo_readiness import ready_discovery


REPO_ROOT = Path(__file__).resolve().parents[1]


def ready_decision():
    return MoomooPaperReadinessGate().evaluate(ready_discovery())


def order_intent(
    *,
    market: Market = Market.US,
    side: Side = Side.BUY,
    symbol: str = "US.AAPL",
    quantity: int = 10,
    order_style: OrderStyle = OrderStyle.PASSIVE_LIMIT,
    limit_price: float = 150.25,
    client_order_id: str = "paper-dry-run-001",
) -> OrderIntent:
    return OrderIntent(
        client_order_id=client_order_id,
        strategy_id="us_paper_validation",
        symbol=symbol,
        market=market,
        side=side,
        quantity=quantity,
        order_style=order_style,
        limit_price=limit_price,
        stop_price=148.0,
        take_profit_price=154.0,
        created_at=datetime(2026, 8, 1, 14, 30, tzinfo=UTC),
    )


class MoomooPaperOrderDryRunPlannerTests(unittest.TestCase):
    def test_maps_ready_us_buy_limit_to_sanitized_simulate_plan(self) -> None:
        plan = MoomooPaperOrderDryRunPlanner().plan(
            order_intent(),
            readiness=ready_decision(),
        )

        self.assertEqual(
            {
                "schema_version": 1,
                "dry_run": True,
                "client_order_id": "paper-dry-run-001",
                "code": "US.AAPL",
                "side": "BUY",
                "quantity": 10,
                "price": 150.25,
                "order_type": "NORMAL",
                "trd_env": "SIMULATE",
                "time_in_force": "DAY",
                "session": "RTH",
                "source_order_style": "PASSIVE_LIMIT",
                "stop_price": 148.0,
                "take_profit_price": 154.0,
                "notional_usd": 1502.5,
            },
            plan.to_dict(),
        )

    def test_aggressive_limit_maps_to_normal_limit_contract(self) -> None:
        plan = MoomooPaperOrderDryRunPlanner().plan(
            order_intent(order_style=OrderStyle.AGGRESSIVE_LIMIT),
            readiness=ready_decision(),
        )

        self.assertEqual("NORMAL", plan.order_type)
        self.assertEqual("AGGRESSIVE_LIMIT", plan.source_order_style)

    def test_blocked_readiness_is_rejected_first(self) -> None:
        blocked = MoomooPaperReadinessGate().evaluate(
            replace(ready_discovery(), us_market_authorized=False)
        )

        self._assert_blocked(
            MoomooPaperOrderPlanReason.READINESS_NOT_READY,
            order_intent(),
            readiness=blocked,
        )

    def test_rejects_unsupported_market_side_style_and_symbol(self) -> None:
        cases = [
            (
                order_intent(market=Market.JP, symbol="JP.7203"),
                MoomooPaperOrderPlanReason.MARKET_NOT_US,
            ),
            (
                order_intent(side=Side.SELL),
                MoomooPaperOrderPlanReason.SIDE_NOT_BUY,
            ),
            (
                order_intent(order_style=OrderStyle.MARKET_PROTECTED),
                MoomooPaperOrderPlanReason.ORDER_STYLE_UNSUPPORTED,
            ),
            (
                order_intent(symbol="AAPL"),
                MoomooPaperOrderPlanReason.SYMBOL_INVALID,
            ),
            (
                order_intent(symbol="US.aapl"),
                MoomooPaperOrderPlanReason.SYMBOL_INVALID,
            ),
        ]

        for intent, reason in cases:
            with self.subTest(reason=reason):
                self._assert_blocked(reason, intent, readiness=ready_decision())

    def test_rejects_invalid_or_excessive_quantity(self) -> None:
        invalid_quantity = replace(order_intent(), quantity=True)

        self._assert_blocked(
            MoomooPaperOrderPlanReason.QUANTITY_INVALID,
            invalid_quantity,
            readiness=ready_decision(),
        )
        self._assert_blocked(
            MoomooPaperOrderPlanReason.QUANTITY_LIMIT_EXCEEDED,
            order_intent(quantity=101),
            readiness=ready_decision(),
        )

    def test_rejects_notional_over_default_limit(self) -> None:
        self._assert_blocked(
            MoomooPaperOrderPlanReason.NOTIONAL_LIMIT_EXCEEDED,
            order_intent(quantity=100, limit_price=250.01),
            readiness=ready_decision(),
        )

    def test_rejects_non_finite_price_and_unsafe_client_id(self) -> None:
        non_finite = replace(order_intent(), limit_price=math.nan)

        self._assert_blocked(
            MoomooPaperOrderPlanReason.PRICE_INVALID,
            non_finite,
            readiness=ready_decision(),
        )
        with self.assertRaises(MoomooPaperOrderPlanError) as caught:
            MoomooPaperOrderDryRunPlanner().plan(
                order_intent(client_order_id="sensitive id with spaces"),
                readiness=ready_decision(),
            )
        self.assertEqual(
            MoomooPaperOrderPlanReason.CLIENT_ORDER_ID_INVALID,
            caught.exception.reason,
        )
        self.assertNotIn("sensitive", str(caught.exception))

    def test_plan_is_immutable_hashable_and_contains_no_sensitive_fields(self) -> None:
        plan = MoomooPaperOrderDryRunPlanner().plan(
            order_intent(),
            readiness=ready_decision(),
        )

        with self.assertRaises(FrozenInstanceError):
            plan.quantity = 99
        self.assertIsInstance(hash(plan), int)
        payload = plan.to_dict()
        for forbidden in [
            "acc_id",
            "account_id",
            "password",
            "token",
            "REAL",
            "raw",
        ]:
            self.assertNotIn(forbidden, str(payload))

    def test_runtime_source_has_no_sdk_or_order_call(self) -> None:
        source = (
            REPO_ROOT / "src/autotrade/execution/moomoo_paper_order.py"
        ).read_text(encoding="utf-8")

        for forbidden in [
            "import moomoo",
            "MoomooApiSdk",
            "OpenSecTradeContext",
            "place_order(",
            "unlock_trade",
            "subscribe(",
        ]:
            self.assertNotIn(forbidden, source)

    def _assert_blocked(self, reason, intent, *, readiness) -> None:
        with self.assertRaises(MoomooPaperOrderPlanError) as caught:
            MoomooPaperOrderDryRunPlanner().plan(intent, readiness=readiness)
        self.assertEqual(reason, caught.exception.reason)


if __name__ == "__main__":
    unittest.main()
