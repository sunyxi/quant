from __future__ import annotations

from dataclasses import dataclass

from autotrade.core.ids import client_order_id
from autotrade.core.models import Market, OrderIntent, OrderStyle, Side, Signal


@dataclass(frozen=True)
class RiskConfig:
    account_equity: float
    single_trade_risk_pct: float = 0.0015
    max_open_risk_pct: float = 0.0075
    daily_loss_stop_pct: float = 0.0075
    max_symbol_notional_pct: float = 0.10
    jp_lot_size: int = 100


@dataclass
class RiskState:
    open_risk: float = 0.0
    realized_pnl_today: float = 0.0


class RiskManager:
    def __init__(self, config: RiskConfig, state: RiskState | None = None) -> None:
        self.config = config
        self.state = state or RiskState()

    def approve(self, signal: Signal, trading_date: str) -> OrderIntent | None:
        if self.state.realized_pnl_today <= -self.config.account_equity * self.config.daily_loss_stop_pct:
            return None

        risk_per_share = abs(signal.entry_price - signal.stop_price)
        if risk_per_share <= 0:
            return None

        risk_budget = self.config.account_equity * self.config.single_trade_risk_pct
        max_open_risk = self.config.account_equity * self.config.max_open_risk_pct
        available_risk = max_open_risk - self.state.open_risk
        allowed_risk = min(risk_budget, available_risk)
        if allowed_risk <= 0:
            return None

        quantity = int(allowed_risk // risk_per_share)
        quantity = self._apply_lot_size(signal.market, quantity)
        max_notional = self.config.account_equity * self.config.max_symbol_notional_pct
        quantity = min(quantity, self._apply_lot_size(signal.market, int(max_notional // signal.entry_price)))

        if quantity <= 0:
            return None

        return OrderIntent(
            client_order_id=client_order_id(
                signal.strategy_id,
                signal.symbol,
                signal.side,
                trading_date,
                signal.created_at.isoformat(),
            ),
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            market=signal.market,
            side=signal.side,
            quantity=quantity,
            order_style=self._order_style(signal.side),
            limit_price=signal.entry_price,
            stop_price=signal.stop_price,
            take_profit_price=signal.take_profit_price,
            created_at=signal.created_at,
        )

    def _apply_lot_size(self, market: Market, quantity: int) -> int:
        if market == Market.JP:
            return quantity // self.config.jp_lot_size * self.config.jp_lot_size
        return quantity

    @staticmethod
    def _order_style(side: Side) -> OrderStyle:
        return OrderStyle.PASSIVE_LIMIT if side in {Side.BUY, Side.SELL} else OrderStyle.AGGRESSIVE_LIMIT
