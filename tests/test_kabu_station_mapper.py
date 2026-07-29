from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from autotrade.core.models import Market, OrderIntent, OrderStyle, Side
from autotrade.execution.kabu_station import (
    KabuStationMappingError,
    KabuStationOrderMapper,
)


def _intent(
    *,
    symbol: str = "7203.T",
    market: Market = Market.JP,
    side: Side = Side.BUY,
    quantity: int = 100,
    order_style: OrderStyle = OrderStyle.PASSIVE_LIMIT,
) -> OrderIntent:
    return OrderIntent(
        client_order_id="client-1",
        strategy_id="test_strategy",
        symbol=symbol,
        market=market,
        side=side,
        quantity=quantity,
        order_style=order_style,
        limit_price=1000,
        stop_price=990,
        take_profit_price=1020,
        created_at=datetime(2026, 7, 28, 9, 30, tzinfo=ZoneInfo("Asia/Tokyo")),
    )


class KabuStationOrderMapperTests(unittest.TestCase):
    def test_maps_jp_buy_limit_order_to_local_payload(self) -> None:
        payload = KabuStationOrderMapper().to_order_payload(_intent())

        self.assertEqual(
            payload,
            {
                "symbol": "7203",
                "exchange": "TSE",
                "side": "BUY",
                "quantity": 100,
                "order_type": "LIMIT",
                "limit_price": 1000,
                "client_order_id": "client-1",
            },
        )

    def test_maps_sell_aggressive_limit_order_to_limit_payload(self) -> None:
        payload = KabuStationOrderMapper().to_order_payload(
            _intent(side=Side.SELL, order_style=OrderStyle.AGGRESSIVE_LIMIT)
        )

        self.assertEqual(payload["side"], "SELL")
        self.assertEqual(payload["order_type"], "LIMIT")

    def test_rejects_non_jp_market(self) -> None:
        with self.assertRaises(KabuStationMappingError):
            KabuStationOrderMapper().to_order_payload(_intent(market=Market.US))

    def test_rejects_non_100_share_lot_quantity(self) -> None:
        with self.assertRaises(KabuStationMappingError):
            KabuStationOrderMapper().to_order_payload(_intent(quantity=50))

    def test_rejects_unknown_jp_symbol_suffix(self) -> None:
        with self.assertRaises(KabuStationMappingError):
            KabuStationOrderMapper().to_order_payload(_intent(symbol="7203"))

    def test_rejects_market_protected_until_adapter_issue_approves_it(self) -> None:
        with self.assertRaises(KabuStationMappingError):
            KabuStationOrderMapper().to_order_payload(
                _intent(order_style=OrderStyle.MARKET_PROTECTED)
            )


if __name__ == "__main__":
    unittest.main()
