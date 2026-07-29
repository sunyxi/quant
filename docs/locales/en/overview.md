# Overview

This repository implements a research-first intraday trading platform skeleton. The initial target is JP equities, with live broker execution explicitly out of scope until risk, order management, reconciliation, and shadow trading gates pass.

The first release scope is JP equities, long-only, no overnight, and Shadow Mode before live trading. kabu Station is the future JP broker target; IBKR is reserved for a later US phase.

Repository CI runs Python unit tests, Task Catalog drift checks, Markdown link/style checks, and a basic secret scan for pull requests and pushes to `main`.

See `docs/roadmap.md`, `docs/task-catalog.md`, `docs/scope.md`, `docs/risk-policy.md`, `docs/broker-decision.md`, `docs/implementation-plan.md`, `docs/operations.md`, `docs/limitations.md`, and `docs/rollback.md`.
