from __future__ import annotations

import unittest

from autotrade.execution.kabu_station import (
    KabuStationClientError,
    KabuStationSnapshotMapper,
)


class KabuStationSnapshotMapperTests(unittest.TestCase):
    def test_maps_open_orders_and_non_flat_positions_to_broker_snapshot(self) -> None:
        snapshot = KabuStationSnapshotMapper().to_broker_state_snapshot(
            orders=[
                {
                    "ID": "broker-order-1",
                    "Symbol": "7203",
                    "LeavesQty": 100,
                    "State": 2,
                },
                {
                    "ID": "filled-order",
                    "Symbol": "6758",
                    "LeavesQty": 0,
                    "State": 5,
                },
            ],
            positions=[
                {
                    "ExecutionID": "position-1",
                    "Symbol": "7203",
                    "Side": "2",
                    "LeavesQty": 100,
                },
                {
                    "ExecutionID": "position-2",
                    "Symbol": "6758",
                    "Side": "1",
                    "LeavesQty": 200,
                },
                {
                    "ExecutionID": "flat-position",
                    "Symbol": "9984",
                    "Side": "2",
                    "LeavesQty": 0,
                },
            ],
        )

        self.assertEqual(len(snapshot.open_orders), 1)
        self.assertEqual(snapshot.open_orders[0].client_order_id, "broker-order-1")
        self.assertEqual(snapshot.open_orders[0].symbol, "7203.T")
        self.assertEqual(len(snapshot.positions), 2)
        self.assertEqual(snapshot.positions[0].symbol, "7203.T")
        self.assertEqual(snapshot.positions[0].quantity, 100)
        self.assertEqual(snapshot.positions[1].symbol, "6758.T")
        self.assertEqual(snapshot.positions[1].quantity, -200)

    def test_rejects_order_without_id(self) -> None:
        with self.assertRaises(KabuStationClientError):
            KabuStationSnapshotMapper().to_broker_state_snapshot(
                orders=[{"Symbol": "7203", "LeavesQty": 100}],
                positions=[],
            )

    def test_rejects_position_without_side(self) -> None:
        with self.assertRaises(KabuStationClientError):
            KabuStationSnapshotMapper().to_broker_state_snapshot(
                orders=[],
                positions=[{"Symbol": "7203", "LeavesQty": 100}],
            )


if __name__ == "__main__":
    unittest.main()
