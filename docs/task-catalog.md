# Task Catalog

<!-- GENERATED FILE: rebuild with `python3 scripts/generate_task_catalog.py`. -->

Catalog version: `0.1.0`
Source of Truth: `docs/task-source.json`

## Repository Gates

Every Issue reports each applicable gate as `passed`, `failed`, `not-run`, or `skipped`.
A gate that did not execute must never be reported as passed.

## ISSUE-001: Document roadmap, task catalog, and contribution gates

- Status: `complete`
- Phase: `Phase 0`
- Dependencies: None
- Roadmap: see `docs/roadmap.md#phase-0`
- Summary: Create the initial implementation roadmap, task catalog, operational documents, rollback guidance, localization entry points, PR template, and GitHub App PR workflow.

### Acceptance Criteria

- Roadmap defines the phased path from research skeleton to shadow trading and live pilot.
- Task Catalog is generated from docs/task-source.json.
- Repository Gates list passed, failed, not-run, and skipped reporting rules.
- English, Japanese, and Simplified Chinese overview pages exist.
- CLI usage, operations, limitations, and rollback documents exist.
- PR template contains the required governance sections.

### Gates

- Python Unit Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `docs/roadmap.md`
- `docs/task-source.json`
- `docs/task-catalog.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `.github/pull_request_template.md`
- `.github/workflows/open-pr-as-codex-app.yml`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the documentation and GitHub workflow/template changes from this branch.

## ISSUE-002: Define project scope and risk policy assets

- Status: `in-progress`
- Phase: `Phase 0`
- Dependencies: ISSUE-001
- Roadmap: see `docs/roadmap.md#phase-0`
- Summary: Write the formal project scope, broker decision, risk policy, and implementation plan before expanding implementation.

### Acceptance Criteria

- Scope fixes JP equities as the first automated market.
- Risk policy defines pre-trade, in-trade, and post-trade controls.
- Broker decision records kabu Station as the JP execution target and IBKR as later US target.
- Implementation plan maps early iterations to task IDs and Go / No-Go evidence.

### Gates

- Python Unit Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `docs/scope.md`
- `docs/risk-policy.md`
- `docs/broker-decision.md`
- `docs/implementation-plan.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Remove the newly added policy documents or revert to the previous approved version.

## ISSUE-003: Add market calendar and JP trading session rules

- Status: `blocked`
- Phase: `Phase 1`
- Dependencies: ISSUE-002
- Roadmap: see `docs/roadmap.md#phase-1`
- Summary: Implement JP trading day, lunch break, and no-overnight session rules used by research and backtesting.

### Acceptance Criteria

- Calendar rejects non-trading timestamps.
- Lunch break is represented explicitly.
- Close flattening cutoffs are configurable.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Secret Scan

### Changed Assets

- `src/autotrade/calendar`
- `tests`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Disable the calendar integration by reverting the feature branch.

## ISSUE-004: Introduce order book intelligence data model

- Status: `blocked`
- Phase: `Phase 1.5`
- Dependencies: ISSUE-003
- Roadmap: see `docs/roadmap.md#phase-15`
- Summary: Add P0 board information structures for best bid/ask, five-level depth, spread, imbalance, microprice, freshness, and health checks.

### Acceptance Criteria

- Order book snapshots validate bid/ask ordering.
- Relative spread, depth, OBI, and microprice are computed from immutable snapshots.
- Stale book data blocks signal confirmation.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Secret Scan

### Changed Assets

- `src/autotrade/market_data`
- `src/autotrade/features`
- `tests`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Disable order book filters and revert the added model modules.

## ISSUE-005: Harden backtest fill and cost modeling

- Status: `blocked`
- Phase: `Phase 1`
- Dependencies: ISSUE-003
- Roadmap: see `docs/roadmap.md#phase-1`
- Summary: Replace simplified fills with conservative partial-fill, spread, slippage, and participation assumptions.

### Acceptance Criteria

- Limit orders do not assume guaranteed fills from minute lows/highs.
- Costs include commission, half-spread, slippage, and impact placeholders.
- Backtest output reports cost attribution.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Secret Scan

### Changed Assets

- `src/autotrade/backtest`
- `tests`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the fill model feature branch and restore the previous simplified engine.

## ISSUE-006: Add repository CI gates workflow

- Status: `in-progress`
- Phase: `Phase 0`
- Dependencies: ISSUE-001, ISSUE-002
- Roadmap: see `docs/roadmap.md#phase-0`
- Summary: Add a GitHub Actions workflow that runs the repository gates for pull requests and pushes to main.

### Acceptance Criteria

- CI runs Python unit tests on Python 3.12.
- CI checks Markdown links and whitespace style.
- CI rebuilds the generated Task Catalog and fails on drift.
- CI runs a basic secret scan.

### Gates

- Python Unit Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `.github/workflows/ci.yml`
- `scripts/check_secrets.py`
- `tests/test_ci_workflow.py`
- `docs/operations.md`
- `docs/cli-usage.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Remove .github/workflows/ci.yml and the workflow catalog test.
