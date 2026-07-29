# Operations

## Daily Research Run

1. Pull the latest approved `main`.
2. Confirm no local secrets or untracked production files exist.
3. Run the applicable unit tests.
4. Run research or demo commands against non-live data.
5. Record gate results as `passed`, `failed`, `not-run`, or `skipped`.

## Strategy Research Run

When evaluating ORB or VWAP signals, include spread and order book health fields in fixtures. A stale or unhealthy book should suppress signals before any risk or execution decision is built.

## OMS State Handling

Treat `UNKNOWN` as a blocking operational state. It means the system cannot safely infer whether the broker accepted, rejected, filled, or cancelled an order until reconciliation confirms the broker state.

## Ledger Handling

Use the local ledger only for research, replay, and simulation. A fill that references an unknown local order should be treated as an operational error until reconciliation explains it.

## Issue Workflow

1. Select the first ready task from `docs/task-catalog.md`.
2. Create a branch named `feat/issue-...`.
3. Add a failing test or documentation check first.
4. Implement the smallest complete change.
5. Rebuild generated outputs only from their Source of Truth.
6. Run applicable Repository Gates.
7. Push the feature branch.
8. Create a Draft PR through `.github/workflows/open-pr-as-codex-app.yml`.
9. Stop and wait for CI, independent review, and human code owner approval.

## Repository Gates

Each PR must report:

- Python Unit Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Applicable fixture or end-to-end design tests
- Task Catalog Generation, when task metadata changes

Use `not-run` when a gate could not execute. Use `skipped` only when the PR explains why the gate is not applicable.

## Continuous Integration

`.github/workflows/ci.yml` runs on pull requests, pushes to `main`, and manual dispatch. It executes:

- Python Unit Tests
- Task Catalog Generation drift check
- Markdown Links/Style
- Secret Scan

CI results supplement, but do not replace, the PR body validation table. If CI does not run, the PR must report it as `not-run`.

## Incident Handling

Any live-trading incident must stop new orders first, then reconcile broker state, local orders, fills, positions, cash, and PnL. The system should not resume live trading from a failed state without a written review.
