# Market Calendar

The first calendar implementation covers JP equity regular sessions for research and backtest filtering.

## JP Regular Sessions

The default JP calendar uses Asia/Tokyo time:

| Session | Start | End |
|---|---:|---:|
| Morning | 09:00 | 11:30 |
| Afternoon | 12:30 | 15:30 |

The lunch break is explicit. Timestamps from 11:30 through 12:29 are treated as closed.

## Entry Cutoff

`JPTradingCalendar` has a configurable `close_flattening_cutoff`, defaulting to 15:20. After this cutoff:

- `accepts_new_entries()` returns false.
- `requires_flattening()` returns true while the market is still open.

This does not yet flatten positions by itself. It gives later OMS and risk work a clear rule to enforce.

## Backtest Behavior

`BacktestEngine` can receive a market calendar. When present, it skips snapshots for timestamps where `accepts_new_entries()` is false. This prevents strategies from creating new order intents during lunch, weekends, holidays configured in the calendar, or close-flattening time.

## Current Limitations

- Holiday handling is explicit but manual; no official JP holiday data source is integrated yet.
- Special quotes, halts, limit-up and limit-down states remain future market-rule work.
- Forced position flattening is not implemented in OMS yet.
