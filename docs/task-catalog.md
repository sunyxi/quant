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

- Status: `complete`
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

- Status: `complete`
- Phase: `Phase 1`
- Dependencies: ISSUE-002
- Roadmap: see `docs/roadmap.md#phase-1`
- Summary: Implement JP trading day, lunch break, and no-overnight session rules used by research and backtesting.

### Acceptance Criteria

- Calendar rejects non-trading timestamps.
- Lunch break is represented explicitly.
- Close flattening cutoffs are configurable.
- Backtest engine can skip snapshots outside entry-allowed sessions.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/calendar`
- `src/autotrade/backtest/engine.py`
- `tests/test_market_calendar.py`
- `docs/market-calendar.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Disable the calendar integration by reverting the feature branch.

## ISSUE-004: Introduce order book intelligence data model

- Status: `complete`
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
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/market_data`
- `tests/test_order_book.py`
- `docs/order-book-intelligence.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Disable order book filters and revert the added model modules.

## ISSUE-005: Harden backtest fill and cost modeling

- Status: `complete`
- Phase: `Phase 1`
- Dependencies: ISSUE-003
- Roadmap: see `docs/roadmap.md#phase-1`
- Summary: Replace simplified fills with conservative partial-fill, spread, slippage, and participation assumptions.

### Acceptance Criteria

- Limit orders do not assume guaranteed fills from minute lows/highs.
- Costs include commission, half-spread, slippage, and impact placeholders.
- Backtest output reports cost attribution.
- Fill quantity is capped by a participation-rate assumption.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/backtest/fill_model.py`
- `src/autotrade/backtest/cost_model.py`
- `src/autotrade/backtest/engine.py`
- `tests/test_backtest_fill_cost.py`
- `docs/backtest-fill-cost.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the fill model feature branch and restore the previous simplified engine.

## ISSUE-006: Add repository CI gates workflow

- Status: `complete`
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

## ISSUE-007: Add strategy market quality filters

- Status: `complete`
- Phase: `Phase 2`
- Dependencies: ISSUE-003, ISSUE-004, ISSUE-005
- Roadmap: see `docs/roadmap.md#phase-2`
- Summary: Connect P0 spread and stale order book health checks to ORB and VWAP strategy signal generation.

### Acceptance Criteria

- ORB signals are blocked when configured spread limits are exceeded.
- VWAP reversion signals are blocked when configured spread limits are exceeded.
- Strategies can require fresh order book data before producing signals.
- Unhealthy order book flags always block strategy signals.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/strategies/market_quality.py`
- `src/autotrade/strategies/opening_range.py`
- `src/autotrade/strategies/vwap_reversion.py`
- `tests/test_strategies.py`
- `docs/strategy-market-quality.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Disable strategy market quality filters by reverting the feature branch.

## ISSUE-008: Add OMS order state machine

- Status: `complete`
- Phase: `Phase 3`
- Dependencies: ISSUE-005, ISSUE-007
- Roadmap: see `docs/roadmap.md#phase-3`
- Summary: Introduce the broker-independent OMS state machine used to register order intents idempotently and track auditable order lifecycle transitions.

### Acceptance Criteria

- Order intents are registered once by client_order_id.
- Valid lifecycle transitions from CREATED through FILLED are supported.
- Invalid lifecycle transitions raise a domain error.
- Uncertain broker submission can be marked UNKNOWN with a reason.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/oms.py`
- `tests/test_oms.py`
- `docs/oms.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the OMS state machine branch; no broker or live order side effects exist in this change.

## ISSUE-009: Add local execution ledger

- Status: `complete`
- Phase: `Phase 3`
- Dependencies: ISSUE-008
- Roadmap: see `docs/roadmap.md#phase-3`
- Summary: Add an in-memory execution ledger that records approved orders, applies fills idempotently, and maintains position quantity, average price, and realized PnL.

### Acceptance Criteria

- Orders are recorded once by client_order_id.
- Fills referencing unknown orders are rejected.
- Long position average price updates after multiple buys.
- Selling a long position realizes PnL and resets average price when flat.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/ledger.py`
- `tests/test_execution_ledger.py`
- `docs/execution-ledger.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the local execution ledger branch; no broker or persistent state side effects exist in this change.

## ISSUE-010: Add risk paused state

- Status: `complete`
- Phase: `Phase 3`
- Dependencies: ISSUE-008, ISSUE-009
- Roadmap: see `docs/roadmap.md#phase-3`
- Summary: Add explicit risk pause and resume controls so risk review can block all new order approvals after manual or system-triggered incidents.

### Acceptance Criteria

- RiskManager can enter a paused state with a required reason.
- Paused RiskManager rejects new order approvals.
- Pause reason is retained for operations and incident review.
- RiskManager can resume and approve new orders when normal limits pass.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/risk/manager.py`
- `tests/test_risk_manager.py`
- `docs/risk-paused-state.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the risk paused state branch; no broker or persistent state side effects exist in this change.

## ISSUE-011: Add reconciliation discrepancy checks

- Status: `complete`
- Phase: `Phase 3`
- Dependencies: ISSUE-008, ISSUE-009, ISSUE-010
- Roadmap: see `docs/roadmap.md#phase-3`
- Summary: Add broker snapshot reconciliation checks that detect unknown local orders, broker orders missing locally, and position quantity mismatches, with optional risk pause on critical discrepancies.

### Acceptance Criteria

- UNKNOWN local OMS orders are reported as critical discrepancies.
- Broker open orders missing from local OMS are reported as critical discrepancies.
- Local and broker position quantity mismatches are reported as critical discrepancies.
- Critical reconciliation discrepancies can pause the RiskManager.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/reconciliation.py`
- `tests/test_reconciliation.py`
- `docs/reconciliation.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the reconciliation checks branch; no broker or persistent state side effects exist in this change.

## ISSUE-012: Add simulated broker adapter

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-008, ISSUE-009, ISSUE-011
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a broker-interface-compatible simulator that supports idempotent order submission, cancellation, open order queries, and injected fills without live broker side effects.

### Acceptance Criteria

- Submitting the same client_order_id returns the same simulated broker order id.
- Cancelled simulated orders disappear from open order queries.
- Injected full fills are recorded and close the open order.
- Injected partial fills reduce the remaining open order quantity.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/simulated_broker.py`
- `tests/test_simulated_broker.py`
- `docs/simulated-broker.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the simulated broker adapter branch; no live broker side effects exist in this change.

## ISSUE-013: Export simulated broker reconciliation snapshots

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-011, ISSUE-012
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Extend the simulated broker to export broker state snapshots containing open orders and simulated positions for reconciliation fixtures.

### Acceptance Criteria

- Simulated broker state snapshots include open order client ids and symbols.
- Injected fills update simulated broker positions.
- Fully filled simulated orders do not appear in open order snapshots.
- Snapshot output uses the same BrokerStateSnapshot structures consumed by reconciliation checks.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/simulated_broker.py`
- `tests/test_simulated_broker.py`
- `docs/simulated-broker.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the simulated broker snapshot branch; no live broker side effects exist in this change.

## ISSUE-014: Add replay execution engine

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-007, ISSUE-008, ISSUE-011, ISSUE-012, ISSUE-013
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a local replay execution loop that connects strategies, risk approval, OMS transitions, simulated broker submission, conservative fills, and reconciliation reports.

### Acceptance Criteria

- Replay can turn a strategy signal into an approved order intent.
- Approved replay orders flow through OMS and simulated broker submission.
- Marketable replay orders can be filled and marked FILLED in the OMS.
- Replay produces reconciliation reports and respects risk rejection.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/replay.py`
- `src/autotrade/execution/simulated_broker.py`
- `tests/test_replay_execution.py`
- `docs/replay-execution.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the replay execution engine branch; no live broker side effects exist in this change.

## ISSUE-015: Add agent rules document

- Status: `complete`
- Phase: `Phase 0`
- Dependencies: ISSUE-001
- Roadmap: see `docs/roadmap.md#phase-0`
- Summary: Add AGENT.md to capture the repository rules for test-first work, documentation synchronization, generated files, Git and PR workflow, and trading safety.

### Acceptance Criteria

- AGENT.md exists at the repository root.
- AGENT.md documents Test-first workflow and Repository Gates.
- AGENT.md documents Documentation and Generated Files rules.
- AGENT.md documents Git and PR workflow including Draft PR, GitHub App, and Do not merge rules.

### Gates

- Python Unit Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `AGENT.md`
- `tests/test_documentation_catalog.py`
- `docs/task-source.json`
- `docs/task-catalog.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the agent rules document branch.

## ISSUE-016: Address replay execution review findings

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-014
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Harden replay execution after review by making duplicate order handling idempotent, cancelling unfilled simulated orders, failing fast on critical reconciliation discrepancies, isolating default run results, sharing the market calendar protocol, and validating snapshot dates.

### Acceptance Criteria

- Duplicate client_order_id values within a replay run do not trigger invalid OMS transitions.
- Unfilled simulated replay orders are cancelled before reconciliation.
- Critical reconciliation discrepancies raise a replay execution error instead of silently pausing risk for the rest of the run.
- Default replay runs return isolated OMS and broker state objects.
- Replay and backtest share the same MarketCalendar protocol definition.
- Replay rejects snapshots whose calendar date does not match the supplied trading_date.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/calendar/protocols.py`
- `src/autotrade/backtest/engine.py`
- `src/autotrade/execution/replay.py`
- `tests/test_replay_execution.py`
- `docs/replay-execution.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the replay hardening branch to restore ISSUE-014 replay behavior; no live broker side effects exist in this change.

## ISSUE-017: Add kabu Station order request mapper

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-008, ISSUE-014
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a local-only kabu Station order request mapper that translates approved JP OrderIntent objects into adapter-boundary payloads without calling live broker APIs.

### Acceptance Criteria

- JP .T symbols are converted into broker-boundary symbol codes.
- BUY and SELL sides are mapped into stable local payload values.
- Passive and aggressive limit order styles map to limit payloads.
- Non-JP markets are rejected.
- JP equity quantities must use 100-share lots.
- Market-protected order style is rejected until a later adapter issue approves it.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/kabu_station.py`
- `tests/test_kabu_station_mapper.py`
- `docs/kabu-station-mapper.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the kabu Station mapper branch; no live broker API calls or persistent broker side effects exist in this change.

## ISSUE-018: Add kabu Station official request contract

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-017
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add official kabu Station token and cash sendorder request contract helpers using localhost-only URLs and fake-client-testable payloads without sending real requests.

### Acceptance Criteria

- Token payload uses the official APIPassword field.
- Production and test endpoint URLs are localhost-only.
- Cash buy limit payload uses official sendorder field names and enum values.
- Cash sell limit payload uses official sell side, delivery, and fund type values.
- The contract remains local-only and does not authenticate or place orders.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/kabu_station.py`
- `tests/test_kabu_station_mapper.py`
- `docs/kabu-station-mapper.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the kabu Station official contract branch; no live broker API calls or persistent broker side effects exist in this change.

## ISSUE-019: Add kabu Station fake-transport token client

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-018
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a kabu Station token client that posts official token payloads through an injected fake-testable transport, maps common response statuses, and avoids storing credentials or opening real network connections.

### Acceptance Criteria

- Token client posts APIPassword payloads to the configured localhost token endpoint through an injected transport.
- Successful token responses return the Token field.
- Empty passwords are rejected before transport calls.
- 401 and 403 responses map to authentication errors.
- 429 responses map to rate limit errors.
- 5xx responses map to server errors.
- The token client does not store API passwords or create a real HTTP transport.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/kabu_station.py`
- `tests/test_kabu_station_token_client.py`
- `docs/kabu-station-mapper.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the kabu Station token client branch; no live broker API calls or persistent broker side effects exist in this change.

## ISSUE-020: Add kabu Station fake-transport sendorder client

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-018, ISSUE-019
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a kabu Station sendorder client that posts official cash order payloads through an injected fake-testable transport, sets X-API-KEY, maps common response statuses, and avoids real order placement.

### Acceptance Criteria

- Sendorder client posts official cash order payloads to the configured localhost sendorder endpoint through an injected transport.
- Sendorder requests include the X-API-KEY header.
- Successful sendorder responses return the OrderId field.
- Empty API tokens are rejected before transport calls.
- 401 and 403 responses map to authentication errors.
- 429 responses map to rate limit errors.
- 5xx responses map to server errors.
- The sendorder client does not create a real HTTP transport or place live orders.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/kabu_station.py`
- `tests/test_kabu_station_sendorder_client.py`
- `docs/kabu-station-mapper.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the kabu Station sendorder client branch; no live broker API calls or persistent broker side effects exist in this change.

## ISSUE-021: Add kabu Station fake-transport cancelorder client

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-019, ISSUE-020
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a kabu Station cancelorder client that sends official cancel payloads through an injected fake-testable transport, sets X-API-KEY, maps common response statuses, and avoids real order cancellation.

### Acceptance Criteria

- Cancelorder client sends OrderId payloads to the configured localhost cancelorder endpoint through an injected transport.
- Cancelorder requests include the X-API-KEY header.
- Successful cancelorder responses return the OrderId field.
- Empty API tokens are rejected before transport calls.
- Empty order ids are rejected before transport calls.
- 401 and 403 responses map to authentication errors.
- 429 responses map to rate limit errors.
- 5xx responses map to server errors.
- The cancelorder client does not create a real HTTP transport or cancel live orders.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/kabu_station.py`
- `tests/test_kabu_station_cancelorder_client.py`
- `docs/kabu-station-mapper.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the kabu Station cancelorder client branch; no live broker API calls or persistent broker side effects exist in this change.

## ISSUE-022: Add kabu Station fake-transport read-only client

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-019, ISSUE-020, ISSUE-021
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a kabu Station read-only client that queries orders and positions through an injected fake-testable GET transport, sets X-API-KEY, maps common response statuses, validates list payloads, and avoids real broker connections.

### Acceptance Criteria

- Read-only orders requests call the configured localhost orders endpoint through an injected transport.
- Read-only positions requests call the configured localhost positions endpoint through an injected transport.
- Orders and positions requests include the X-API-KEY header.
- Orders requests can pass product, symbol, and details query parameters.
- Positions requests can pass product and symbol query parameters.
- Empty API tokens are rejected before transport calls.
- Successful orders and positions responses must be list payloads.
- 401 and 403 responses map to authentication errors.
- 429 responses map to rate limit errors.
- 5xx responses map to server errors.
- The read-only client does not create a real HTTP transport or connect to kabu Station.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/kabu_station.py`
- `tests/test_kabu_station_readonly_client.py`
- `docs/kabu-station-mapper.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the kabu Station read-only client branch; no live broker API calls or persistent broker side effects exist in this change.

## ISSUE-023: Map kabu Station read-only payloads to broker snapshots

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-011, ISSUE-022
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a local-only mapper that converts kabu Station read-only orders and positions payloads into BrokerStateSnapshot fixtures for reconciliation without querying a real broker.

### Acceptance Criteria

- Open order payloads with positive LeavesQty map to BrokerOrderSnapshot entries.
- Filled or closed order payloads with zero LeavesQty are excluded from open order snapshots.
- Position payloads with positive LeavesQty map to BrokerPositionSnapshot entries.
- Sell-side positions map to negative quantities.
- Flat positions are excluded from position snapshots.
- JP symbol codes are normalized to .T symbols.
- Missing required order or position fields raise local client errors.
- The mapper does not create a real HTTP transport or query kabu Station.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/kabu_station.py`
- `tests/test_kabu_station_snapshot_mapper.py`
- `tests/test_documentation_catalog.py`
- `docs/kabu-station-mapper.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the kabu Station snapshot mapper branch; no live broker API calls or persistent broker side effects exist in this change.

## ISSUE-024: Add kabu Station read-only reconciliation orchestration

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-011, ISSUE-022, ISSUE-023
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a fake-client-testable kabu Station read-only reconciler that fetches orders and positions through an injected client, maps them to broker snapshots, and runs the broker-independent reconciliation engine without live broker side effects.

### Acceptance Criteria

- Read-only reconciliation fetches orders and positions through the injected kabu Station read-only client.
- Fetched payloads are mapped into BrokerStateSnapshot before reconciliation.
- Consistent local and broker state returns no critical discrepancy.
- Broker open orders missing from the local OMS are returned as critical discrepancies.
- Local and broker position quantity mismatches are returned as critical discrepancies.
- Critical discrepancies pause a configured RiskManager.
- Orders and positions requests pass the supplied API token.
- Client and mapper errors propagate to the caller.
- The reconciler does not create a real HTTP transport, query real kabu Station, or call sendorder or cancelorder.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/kabu_station.py`
- `tests/test_kabu_station_readonly_reconciler.py`
- `tests/test_documentation_catalog.py`
- `docs/kabu-station-mapper.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the kabu Station read-only reconciler branch; no live broker API calls or persistent broker side effects exist in this change.

## ISSUE-025: Add local Shadow Mode readiness gate

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-014, ISSUE-024
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a local-only Shadow Mode readiness gate that evaluates replay execution results, reconciliation reports, open orders, and risk pause state before a shadow run is treated as operationally acceptable.

### Acceptance Criteria

- Clean replay results with reconciliation evidence return a passing readiness decision.
- Any critical reconciliation report blocks readiness.
- A paused RiskManager blocks readiness and reports the pause reason.
- Missing reconciliation evidence blocks readiness.
- Remaining open simulated broker orders block readiness.
- The readiness decision reports stable metrics for intents, fills, reconciliation reports, critical reports, and open orders.
- The gate remains local-only and does not connect to market data, query brokers, submit orders, or cancel orders.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/shadow_mode.py`
- `tests/test_shadow_mode.py`
- `tests/test_documentation_catalog.py`
- `docs/replay-execution.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the Shadow Mode readiness gate branch; no live broker API calls or persistent broker side effects exist in this change.

## ISSUE-026: Add local Shadow Mode run summary

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-025
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a local-only Shadow Mode run summary that captures trading date, readiness status, blocking reasons, and readiness metrics from an existing readiness decision for audit-friendly fixture review.

### Acceptance Criteria

- A passing readiness decision produces a passing Shadow Mode run summary.
- A blocked readiness decision produces a blocked Shadow Mode run summary with blocking reasons preserved.
- The summary records the supplied trading date.
- The summary stores a stable copy of readiness metrics.
- The summary exposes a JSON-compatible dictionary representation.
- Mutating the source decision metrics after summary creation does not change the summary.
- The summary builder remains local-only and does not run strategies, connect to market data, query brokers, submit orders, or cancel orders.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/shadow_mode.py`
- `tests/test_shadow_mode.py`
- `tests/test_documentation_catalog.py`
- `docs/replay-execution.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the Shadow Mode run summary branch; no live broker API calls or persistent broker side effects exist in this change.

## ISSUE-027: Add local Shadow Mode summary writer

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-026
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a local-only Shadow Mode summary writer that persists an existing run summary as deterministic JSON for fixture review without running replay or touching broker boundaries.

### Acceptance Criteria

- The writer stores an existing Shadow Mode run summary as JSON.
- The writer creates missing parent directories.
- The writer rejects overwriting an existing summary file by default.
- The written JSON includes trading date, status, reasons, and metrics.
- The written JSON uses stable key ordering and a trailing newline.
- The writer returns the output path.
- The writer remains local-only and does not run strategies, connect to market data, query brokers, submit orders, or cancel orders.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/shadow_mode.py`
- `tests/test_shadow_mode.py`
- `tests/test_documentation_catalog.py`
- `docs/replay-execution.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the Shadow Mode summary writer branch; no live broker API calls or broker side effects exist in this change.

## ISSUE-028: Add local Shadow Mode summary reader

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-027
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a local-only Shadow Mode summary reader that loads deterministic summary JSON back into a run summary with validation for fixture review.

### Acceptance Criteria

- The reader loads a Shadow Mode run summary from JSON written by the summary writer.
- The reader rejects payloads missing trading date, status, reasons, or metrics.
- The reader rejects unknown readiness status values.
- The reader rejects non-list reasons.
- The reader rejects metrics that are not integer values.
- The reader returns a ShadowModeRunSummary with copied reasons and metrics.
- The reader remains local-only and does not run strategies, connect to market data, query brokers, submit orders, or cancel orders.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/shadow_mode.py`
- `tests/test_shadow_mode.py`
- `tests/test_documentation_catalog.py`
- `docs/replay-execution.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the Shadow Mode summary reader branch; no live broker API calls or broker side effects exist in this change.

## ISSUE-029: Add Shadow Mode summary schema version

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-028
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a local Shadow Mode summary schema version so JSON summary artifacts can be validated for compatibility before fixture review.

### Acceptance Criteria

- Shadow Mode run summaries include schema_version 1 by default.
- The JSON-compatible summary representation includes schema_version.
- The summary writer persists schema_version.
- The summary reader requires schema_version.
- The summary reader rejects unsupported schema_version values.
- Existing summary fields still round-trip through writer and reader.
- The schema version support remains local-only and does not run strategies, connect to market data, query brokers, submit orders, or cancel orders.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/shadow_mode.py`
- `tests/test_shadow_mode.py`
- `tests/test_documentation_catalog.py`
- `docs/replay-execution.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the Shadow Mode summary schema version branch; no live broker API calls or broker side effects exist in this change.

## ISSUE-030: Add local Shadow Mode summary review aggregation

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-029
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a local-only Shadow Mode summary review aggregate that counts passing and blocked run summaries plus blocking reasons for fixture review.

### Acceptance Criteria

- The review aggregate rejects empty summary lists.
- The review aggregate reports total, passed, and blocked summary counts.
- The review aggregate reports sorted trading dates.
- The review aggregate counts blocking reasons across blocked summaries.
- The review aggregate exposes a JSON-compatible dictionary representation.
- Passing-only summary lists have no blocking reasons.
- The review aggregate remains local-only and does not run strategies, connect to market data, query brokers, submit orders, or cancel orders.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/execution/shadow_mode.py`
- `tests/test_shadow_mode.py`
- `tests/test_documentation_catalog.py`
- `docs/replay-execution.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the Shadow Mode summary review aggregation branch; no live broker API calls or broker side effects exist in this change.
