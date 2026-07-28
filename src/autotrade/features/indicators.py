from __future__ import annotations


def zscore(value: float, mean: float, sigma: float) -> float:
    if sigma <= 0:
        return 0.0
    return (value - mean) / sigma


def order_book_imbalance(bid_depth: float, ask_depth: float) -> float:
    total = bid_depth + ask_depth
    if total <= 0:
        return 0.0
    return (bid_depth - ask_depth) / total


def relative_volume(current_volume: float, historical_same_time_median: float) -> float:
    if historical_same_time_median <= 0:
        return 0.0
    return current_volume / historical_same_time_median
