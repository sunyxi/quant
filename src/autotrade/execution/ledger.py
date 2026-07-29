from __future__ import annotations

from dataclasses import dataclass, replace

from autotrade.core.models import Fill, OrderIntent, Side


class LedgerError(ValueError):
    pass


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: int = 0
    average_price: float = 0.0
    realized_pnl: float = 0.0


class LocalExecutionLedger:
    def __init__(self) -> None:
        self._orders: dict[str, OrderIntent] = {}
        self._fills: list[Fill] = []
        self._fill_keys: set[tuple[str, str, int, float]] = set()
        self._positions: dict[str, Position] = {}

    def record_order(self, intent: OrderIntent) -> OrderIntent:
        existing = self._orders.get(intent.client_order_id)
        if existing is not None:
            return existing
        self._orders[intent.client_order_id] = intent
        return intent

    def record_fill(self, fill: Fill) -> Position:
        if fill.client_order_id not in self._orders:
            raise LedgerError(f"fill references unknown order {fill.client_order_id}")

        fill_key = (
            fill.client_order_id,
            fill.filled_at.isoformat(),
            fill.quantity,
            fill.price,
        )
        if fill_key in self._fill_keys:
            return self._positions.get(fill.symbol, Position(symbol=fill.symbol))

        self._fill_keys.add(fill_key)
        self._fills.append(fill)
        position = self._positions.get(fill.symbol, Position(symbol=fill.symbol))
        updated = self._apply_fill(position, fill)
        self._positions[fill.symbol] = updated
        return updated

    def orders(self) -> list[OrderIntent]:
        return list(self._orders.values())

    def fills(self) -> list[Fill]:
        return list(self._fills)

    def position(self, symbol: str) -> Position | None:
        return self._positions.get(symbol)

    def positions(self) -> list[Position]:
        return list(self._positions.values())

    def _apply_fill(self, position: Position, fill: Fill) -> Position:
        if fill.side == Side.BUY:
            return self._apply_buy(position, fill)
        return self._apply_sell(position, fill)

    @staticmethod
    def _apply_buy(position: Position, fill: Fill) -> Position:
        if position.quantity >= 0:
            new_quantity = position.quantity + fill.quantity
            new_average = (
                (position.average_price * position.quantity + fill.price * fill.quantity)
                / new_quantity
            )
            return replace(position, quantity=new_quantity, average_price=new_average)

        cover_quantity = min(fill.quantity, abs(position.quantity))
        realized = (position.average_price - fill.price) * cover_quantity
        remaining_short = position.quantity + cover_quantity
        extra_long = fill.quantity - cover_quantity
        if extra_long > 0:
            return Position(
                symbol=position.symbol,
                quantity=extra_long,
                average_price=fill.price,
                realized_pnl=position.realized_pnl + realized,
            )
        return replace(
            position,
            quantity=remaining_short,
            average_price=position.average_price if remaining_short else 0.0,
            realized_pnl=position.realized_pnl + realized,
        )

    @staticmethod
    def _apply_sell(position: Position, fill: Fill) -> Position:
        if position.quantity <= 0:
            new_quantity = position.quantity - fill.quantity
            short_quantity = abs(position.quantity)
            new_average = (
                (position.average_price * short_quantity + fill.price * fill.quantity)
                / abs(new_quantity)
            )
            return replace(position, quantity=new_quantity, average_price=new_average)

        close_quantity = min(fill.quantity, position.quantity)
        realized = (fill.price - position.average_price) * close_quantity
        remaining_long = position.quantity - close_quantity
        extra_short = fill.quantity - close_quantity
        if extra_short > 0:
            return Position(
                symbol=position.symbol,
                quantity=-extra_short,
                average_price=fill.price,
                realized_pnl=position.realized_pnl + realized,
            )
        return replace(
            position,
            quantity=remaining_long,
            average_price=position.average_price if remaining_long else 0.0,
            realized_pnl=position.realized_pnl + realized,
        )
