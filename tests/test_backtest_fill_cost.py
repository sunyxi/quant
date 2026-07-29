from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from autotrade.backtest.cost_model import CostBreakdown, CostModel
from autotrade.backtest.fill_model import ConservativeFillModel
from autotrade.core.models import Market, MarketSnapshot, OrderIntent, OrderStyle, Side


TOKYO = ZoneInfo("Asia/Tokyo")


def order_intent(quantity: int = 100, limit_price: float = 1002) -> OrderIntent:
    return OrderIntent(
        client_order_id="test-order",
        strategy_id="test",
        symbol="7203.T",
        market=Market.JP,
        side=Side.BUY,
        quantity=quantity,
        order_style=OrderStyle.PASSIVE_LIMIT,
        limit_price=limit_price,
        stop_price=990,
        take_profit_price=1030,
        created_at=datetime(2026, 7, 29, 9, 1, tzinfo=TOKYO),
    )


def snapshot(volume: int = 1_000, bid: float = 1000, ask: float = 1002) -> MarketSnapshot:
    return MarketSnapshot(
        symbol="7203.T",
        market=Market.JP,
        timestamp=datetime(2026, 7, 29, 9, 1, tzinfo=TOKYO),
        bid=bid,
        ask=ask,
        last=1002,
        volume=volume,
        vwap=1001,
    )


class CostModelTests(unittest.TestCase):
    def test_cost_breakdown_sums_components(self) -> None:
        breakdown = CostBreakdown(
            commission=10,
            spread=100,
            slippage=25,
            impact=5,
        )

        self.assertEqual(140, breakdown.total)

    def test_cost_model_reports_attribution(self) -> None:
        breakdown = CostModel(
            commission_per_share=0.01,
            slippage_bps=1.0,
            impact_bps=0.5,
        ).estimate(order_intent(quantity=100), snapshot())

        self.assertGreater(breakdown.spread, 0)
        self.assertGreater(breakdown.slippage, 0)
        self.assertGreater(breakdown.impact, 0)
        self.assertAlmostEqual(
            breakdown.total,
            breakdown.commission + breakdown.spread + breakdown.slippage + breakdown.impact,
        )


class ConservativeFillModelTests(unittest.TestCase):
    def test_limit_buy_does_not_fill_when_limit_is_below_ask(self) -> None:
        fill = ConservativeFillModel().try_fill(order_intent(limit_price=1001), snapshot())

        self.assertIsNone(fill)

    def test_fill_quantity_is_capped_by_participation_rate(self) -> None:
        fill = ConservativeFillModel(max_participation_rate=0.10).try_fill(
            order_intent(quantity=500),
            snapshot(volume=1_000),
        )

        self.assertIsNotNone(fill)
        self.assertEqual(100, fill.quantity)


if __name__ == "__main__":
    unittest.main()
