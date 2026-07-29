# Overview

This repository implements a research-first intraday trading platform skeleton. The initial target is JP equities, with live broker execution explicitly out of scope until risk, order management, reconciliation, and shadow trading gates pass.

The first release scope is JP equities, long-only, no overnight, and Shadow Mode before live trading. kabu Station is the future JP broker target; IBKR is reserved for a later US phase.

The current calendar layer covers JP regular sessions, lunch break, weekend rejection, manual holidays, and close-entry cutoff for research filtering.

See `docs/roadmap.md`, `docs/task-catalog.md`, `docs/scope.md`, `docs/risk-policy.md`, `docs/broker-decision.md`, `docs/implementation-plan.md`, `docs/market-calendar.md`, `docs/operations.md`, `docs/limitations.md`, and `docs/rollback.md`.
