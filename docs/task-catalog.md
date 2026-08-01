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

## ISSUE-031: Add local Shadow Mode review writer

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-030
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a local-only Shadow Mode review writer that persists an existing summary review aggregate as deterministic JSON for fixture review.

### Acceptance Criteria

- The writer stores an existing Shadow Mode summary review as JSON.
- The writer creates missing parent directories.
- The writer rejects overwriting an existing review file by default.
- The written JSON includes total, passed, blocked, trading dates, and blocking reasons.
- The written JSON uses stable key ordering and a trailing newline.
- The writer returns the output path.
- The writer remains local-only and does not discover files, run strategies, connect to market data, query brokers, submit orders, or cancel orders.

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

Rollback: Revert the Shadow Mode review writer branch; no live broker API calls or broker side effects exist in this change.

## ISSUE-032: Complete the Mac-side kabu Station localhost integration boundary

- Status: `complete`
- Phase: `Phase 5`
- Dependencies: ISSUE-024, ISSUE-031
- Roadmap: see `docs/roadmap.md#phase-5`
- Summary: Complete the localhost-only kabu Station authentication and read-only query boundary that can be built and tested on Mac before Windows kabu Station runtime validation.

### Acceptance Criteria

- The concrete JSON HTTP transport supports GET, POST, and PUT, accepts an injected opener for tests, preserves HTTP status and parsed payload, and maps connection failures, timeouts, invalid JSON, and empty responses into local domain errors.
- The transport accepts only loopback HTTP URLs, rejects userinfo URLs, remote hosts, non-HTTP schemes, and remote redirects, and does not leak API passwords, API tokens, request headers, or authentication payloads in errors.
- The default localhost policy allows only token authentication and read-only orders/positions queries while rejecting sendorder and cancelorder endpoints.
- The read-only probe chains the token client, orders client, positions client, and snapshot mapper, then returns sanitized statuses, counts, timestamp, endpoint, environment, and failure category only.
- The CLI defaults to validate-only mode, requires an explicit connect flag for localhost probing, accepts the API password only from an environment variable or secure prompt, and exposes no sendorder/cancelorder commands.
- The probe report writer/reader use deterministic schema-versioned JSON, exclude secrets and raw account data, and reject unknown schemas.
- Tests use fake transports/openers only and do not depend on Windows, real kabu Station, real accounts, or external network access.
- Documentation explains Mac-side completion, fake-only tests, Windows-only real validation, sanitized output review, credential exposure handling, rollback, and the continued prohibition on real sendorder/cancelorder.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `.gitignore`
- `src/autotrade/cli.py`
- `src/autotrade/execution/kabu_station.py`
- `tests/test_cli.py`
- `tests/test_kabu_station_http_transport.py`
- `tests/test_kabu_station_readonly_probe.py`
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

Rollback: Revert the kabu Station localhost boundary branch; clients will continue using injected fake transports, generated probe reports can be deleted, and no live order side effects exist in this change.

## ISSUE-033: Harden the kabu Station localhost read-only boundary

- Status: `complete`
- Phase: `Phase 5`
- Dependencies: ISSUE-032
- Roadmap: see `docs/roadmap.md#phase-5`
- Summary: Address post-merge review findings in the localhost transport, read-only probe, and CLI so redirects and encoded paths cannot bypass policy and operational failures retain accurate sanitized classifications.

### Acceptance Criteria

- Redirect targets are validated against both loopback URL and read-only endpoint policy before they are followed.
- Percent-encoded endpoint paths cannot bypass the read-only policy.
- Empty or non-JSON HTTP error bodies preserve status-based typed client errors.
- Empty or non-JSON successful HTTP response bodies retain a response-failure category instead of being reported as authentication failures.
- Connection and timeout failures during orders or positions reads retain transport failure categories without erasing successful authentication evidence.
- Policy and operating-system failures retain configuration and system categories during every probe stage.
- Pre-connection validation failures do not report a successful connection.
- Probe report conflicts and filesystem write failures produce a clean CLI error without a traceback.
- The default HTTP opener is constructed once per transport instance.
- Task Catalog output is regenerated only from docs/task-source.json.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/cli.py`
- `src/autotrade/execution/kabu_station.py`
- `tests/test_cli.py`
- `tests/test_kabu_station_http_transport.py`
- `tests/test_kabu_station_readonly_probe.py`
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

Rollback: Revert the ISSUE-033 hardening branch to restore the ISSUE-032 localhost boundary; no live broker order or cancellation side effects exist in this change.

## ISSUE-034: Prioritize Moomoo OpenAPI proof of concept

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-033
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Change the broker integration priority so the first real API proof of concept uses Moomoo OpenAPI on macOS for sanitized read-only account, US capability, and JP quote-entitlement discovery, while retaining kabu Station for later JP cash-equity execution and IBKR as a US fallback.

### Acceptance Criteria

- The broker decision prioritizes Moomoo OpenAPI as the first API proof of concept on macOS.
- The proof of concept is limited to sanitized read-only US account and market capability discovery, followed only by separately approved paper-trading work.
- Documentation states that Moomoo JP currently supports US stock and ETF API trading but not live JP cash-equity API trading.
- JP equity market data support is documented separately from JP trading support and remains quote-entitlement-dependent.
- The next implementation baseline records OpenD and moomoo-api version 10.4.6408 or newer, loopback endpoint 127.0.0.1:11111, isolated protobuf compatibility, and a prohibition on SDK unlock_trade calls.
- kabu Station remains the later JP execution candidate and existing kabu Station assets are not removed.
- IBKR remains a later US fallback.
- CLI, operations, limitations, rollback, architecture, roadmap, implementation plan, README, and all localized overviews reflect the decision.
- The next implementation task is an explicit macOS-capable read-only Moomoo OpenD discovery boundary with fake-SDK tests and no live orders.
- The Task Catalog is regenerated only from docs/task-source.json.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `README.md`
- `docs/architecture.md`
- `docs/broker-decision.md`
- `docs/scope.md`
- `docs/roadmap.md`
- `docs/implementation-plan.md`
- `docs/task-source.json`
- `docs/task-catalog.md`
- `docs/cli-usage.md`
- `docs/operations.md`
- `docs/limitations.md`
- `docs/rollback.md`
- `docs/locales/en/overview.md`
- `docs/locales/ja/overview.md`
- `docs/locales/zh-CN/overview.md`
- `tests/test_issue_034_moomoo_broker_decision.py`

### Test-first Evidence

- Red: required before implementation starts.
- Green: required after implementation.
- Refactor: optional, but must keep gates accurate.

Rollback: Revert the ISSUE-034 decision branch, remove dependent ISSUE-035 from the Source of Truth, and regenerate the Task Catalog; no SDK, authenticated connection, paper order, or live order side effects exist.

## ISSUE-035: Add Moomoo OpenD read-only discovery boundary

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-034
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a macOS-capable read-only Moomoo OpenD discovery boundary with an injected fake moomoo-api SDK for tests and sanitized compatibility evidence without placing paper or live orders.

### Acceptance Criteria

- A broker-specific boundary checks configurable loopback OpenD reachability at 127.0.0.1:11111 without coupling strategy code to the Moomoo SDK.
- OpenD and the moomoo-api Python distribution must be version 10.4.6408 or newer; the distribution is imported as moomoo.
- The moomoo-api dependency is isolated as an optional extra or dedicated environment so its resolved protobuf compatibility can be verified without changing unrelated dependencies.
- The discovery boundary reads only API version, sanitized account-list shape, US market capability, JP equity market data and quote-entitlement metadata, and paper-account availability needed for compatibility decisions.
- The discovery boundary does not unlock trading, place paper orders, place live orders, cancel orders, or subscribe to paid data automatically.
- Repository code never calls unlock_trade; any future real-trading unlock requires separate approval and manual action in the OpenD GUI.
- SDK and OpenD failures map to sanitized domain errors without exposing credentials, account identifiers, tokens, or raw account payloads.
- Unit and fixture tests use an injected fake SDK and do not require OpenD, a Moomoo account, authentication, or external network access.
- An explicit CLI connect flag is required before any localhost OpenD call; validate-only mode creates no SDK context or socket.
- A successful report is documented as compatibility evidence only and cannot authorize Shadow Mode or trading.
- English, Japanese, Simplified Chinese, CLI, operations, limitations, rollback, and generated Task Catalog documentation are synchronized.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `.gitignore`
- `README.md`
- `pyproject.toml`
- `src/autotrade/cli.py`
- `src/autotrade/execution/moomoo.py`
- `tests/test_moomoo_discovery.py`
- `tests/test_cli.py`
- `tests/test_documentation_catalog.py`
- `tests/test_issue_034_moomoo_broker_decision.py`
- `docs/task-source.json`
- `docs/task-catalog.md`
- `docs/moomoo-openapi.md`
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

Rollback: Revert the ISSUE-035 branch, remove the optional Moomoo SDK dependency if introduced, and delete sanitized local discovery reports after review; no paper or live order side effects are allowed.

## ISSUE-036: Add Moomoo paper-trading readiness gate

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-035
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add an offline, broker-independent readiness gate that consumes a sanitized Moomoo discovery report and determines whether a separately approved US paper-trading experiment may be designed, without connecting to OpenD or placing orders.

### Acceptance Criteria

- The gate consumes only a validated Moomoo discovery schema version 1 report and creates no SDK context, socket, subscription, account selection, or broker request.
- Readiness requires successful quote and trade discovery, logged-in quote and trade contexts, at least one paper account, US market authorization, and a known non-NO US quote entitlement.
- Missing or incompatible evidence produces deterministic fixed reason codes and a BLOCKED result without exposing account identifiers or raw broker payloads.
- The decision contains only status, fixed reason codes, sanitized aggregate evidence, and schema versions needed for auditability.
- A CLI command evaluates an explicit discovery report path offline, emits deterministic JSON, and returns zero only for READY; invalid reports fail cleanly without a traceback.
- The command and gate do not call unlock_trade, place paper orders, place live orders, cancel orders, or subscribe to market data.
- READY means only that a later US paper-order adapter Issue may be considered; it does not authorize Shadow Mode, paper orders, live orders, or JP cash-equity trading.
- Unit and fixture tests cover READY, each blocking condition, malformed reports, deterministic ordering, and the no-SDK/no-network CLI boundary.
- English, Japanese, Simplified Chinese, CLI, operations, limitations, rollback, feature documentation, and generated Task Catalog output are synchronized.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/cli.py`
- `src/autotrade/execution/moomoo.py`
- `src/autotrade/execution/moomoo_readiness.py`
- `tests/test_cli.py`
- `tests/test_moomoo_readiness.py`
- `tests/test_documentation_catalog.py`
- `docs/task-source.json`
- `docs/task-catalog.md`
- `docs/moomoo-openapi.md`
- `docs/implementation-plan.md`
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

Rollback: Revert the ISSUE-036 branch and remove the offline readiness command and decision model; discovery reports remain sanitized local evidence and no broker, paper-order, live-order, subscription, or position side effects require reconciliation.

## ISSUE-037: Add Moomoo US paper-order dry-run contract

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-036
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add an offline dry-run planner that maps an approved broker-independent US long limit OrderIntent and READY discovery evidence into a sanitized Moomoo paper-order plan without selecting an account or calling the SDK.

### Acceptance Criteria

- The planner accepts the existing OrderIntent only after an ISSUE-036 readiness decision is READY and rejects BLOCKED evidence with a fixed reason code.
- The first contract supports only Market.US, Side.BUY, US.<ticker> symbols, positive whole-share quantity, and PASSIVE_LIMIT or AGGRESSIVE_LIMIT order styles.
- Default safety limits cap dry-run quantity at 100 shares and notional at 25000 USD; exceeding either limit is blocked before a plan is created.
- The immutable deterministic plan uses sanitized plain values equivalent to TrdEnv.SIMULATE, OrderType.NORMAL, TimeInForce.DAY, Session.RTH, and the Moomoo US.<ticker> code format.
- The plan includes client order traceability and risk prices but excludes account identifiers, credentials, tokens, SDK objects, raw payloads, and live-environment options.
- The planner and CLI do not import the external moomoo distribution, create an SDK context or socket, select an account, call place_order, unlock trading, subscribe, cancel, or modify an order.
- An offline CLI consumes a validated discovery report plus explicit order fields, emits deterministic dry-run JSON, returns zero only when a plan is created, and fails cleanly for invalid evidence or policy violations.
- A successful dry run is design evidence only and does not authorize or place a paper order, Shadow Mode order, live order, or JP cash-equity order.
- Unit and fixture tests cover supported mapping, readiness blocking, every market/side/style/symbol/quantity/notional policy, sanitization, immutability, deterministic output, and the no-SDK/no-network/no-order boundary.
- English, Japanese, Simplified Chinese, CLI, operations, limitations, rollback, feature documentation, implementation plan, and generated Task Catalog output are synchronized.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/cli.py`
- `src/autotrade/execution/moomoo_paper_order.py`
- `tests/test_cli.py`
- `tests/test_moomoo_paper_order.py`
- `tests/test_documentation_catalog.py`
- `docs/task-source.json`
- `docs/task-catalog.md`
- `docs/moomoo-openapi.md`
- `docs/implementation-plan.md`
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

Rollback: Revert the ISSUE-037 branch and remove the offline dry-run planner and CLI; no SDK, account, broker, paper-order, live-order, subscription, order, fill, or position side effects require cancellation or reconciliation.

## ISSUE-038: Add Moomoo US paper-account read-only preflight

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-037
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add an explicitly connected, read-only Moomoo preflight that selects exactly one eligible US SIMULATE stock-and-option account in memory and checks funds, positions, and order-query compatibility without placing, changing, or cancelling orders.

### Acceptance Criteria

- The preflight requires an ISSUE-036 READY decision before creating a trade context and fails closed when readiness evidence is blocked or invalid.
- Only an ACTIVE US-authorized account with trd_env SIMULATE and sim_acc_type STOCK_AND_OPTION is eligible; zero or multiple eligible accounts block the preflight.
- The selected acc_id is used only in memory for read-only SDK calls and is never included in results, reports, logs, errors, tests, or documentation examples.
- The preflight calls accinfo_query, position_list_query, and order_list_query with TrdEnv.SIMULATE, the selected account ID, and refresh_cache=True.
- The immutable schema-versioned result contains only sanitized compatibility statuses, account classification, aggregate counts, refresh-cache evidence, endpoint, SDK version, and a fixed failure category.
- The trade context is closed on success and every failure path; SDK exceptions and raw broker response payloads are not exposed.
- The CLI validates configuration without loading the SDK by default and requires both --connect and a validated discovery report for a real localhost preflight.
- The CLI emits sanitized deterministic JSON, optionally writes a create-only ignored report, returns zero only for a successful preflight, and fails cleanly without a traceback.
- The implementation does not call unlock_trade, place_order, modify_order, subscribe, create a quote subscription, or expose any REAL trading-environment option.
- Unit, integration, and fixture tests use fake SDK/context objects to cover account selection, every read query, refresh_cache, sanitization, context closure, error categories, report validation, and no-order boundaries.
- English, Japanese, Simplified Chinese, CLI, operations, limitations, rollback, feature documentation, implementation plan, ignore rules, and generated Task Catalog output are synchronized.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `.gitignore`
- `src/autotrade/cli.py`
- `src/autotrade/execution/moomoo.py`
- `tests/test_cli.py`
- `tests/test_moomoo_preflight.py`
- `tests/test_documentation_catalog.py`
- `docs/task-source.json`
- `docs/task-catalog.md`
- `docs/moomoo-openapi.md`
- `docs/implementation-plan.md`
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

Rollback: Revert the ISSUE-038 branch and remove the read-only connected preflight, CLI, report artifacts, and task metadata; no order, cancellation, fill, subscription, or position side effect requires broker reconciliation.

## ISSUE-039: Add explicit Moomoo US paper-order submission boundary

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-038
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add a disabled-by-default boundary that can submit exactly one reviewed US BUY limit order to an eligible Moomoo SIMULATE account, then verifies it through a fresh read without exposing broker identifiers or enabling live trading.

### Acceptance Criteria

- Submission requires an ISSUE-036 READY decision, a successful schema version 1 ISSUE-038 preflight result, and an ISSUE-037 dry-run plan.
- Only US BUY NORMAL limit orders in TrdEnv.SIMULATE with DAY and RTH settings are supported; REAL, SELL, market, extended-hours, options, JP orders, unlock, modify, cancel, and subscription paths are absent.
- The service creates one US trade context, reselects exactly one eligible ACTIVE US STOCK_AND_OPTION SIMULATE account, and keeps its positive integer acc_id in memory only.
- place_order is called at most once with the reviewed plan fields and client_order_id as a broker remark; submission exceptions or malformed responses become UNKNOWN and are never retried automatically.
- After an accepted response, order_list_query runs with TrdEnv.SIMULATE, the selected acc_id, and refresh_cache=True to verify exactly one matching client-order remark.
- The immutable sanitized result reports submitted, verified, rejected, blocked, or unknown status and fixed failure categories without account IDs, broker order IDs, raw payloads, credentials, or SDK exception text.
- The trade context closes on every path and duplicate service invocation is not made internally.
- The CLI remains preview-only by default and requires explicit connection, paper submission, and side-effect acknowledgement flags before loading the SDK.
- Unit and fixture tests use fake SDK/context objects and prove exact request mapping, one-call behavior, no retry, verification, sanitization, closure, and forbidden-operation boundaries.
- No real OpenD paper order is submitted by repository validation; an operator must separately approve concrete canary order parameters before a real fixture run.
- English, Japanese, Simplified Chinese, CLI, operations, limitations, rollback, feature documentation, implementation plan, and generated Task Catalog output are synchronized.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/cli.py`
- `src/autotrade/execution/moomoo.py`
- `src/autotrade/execution/moomoo_paper_submit.py`
- `tests/test_cli.py`
- `tests/test_moomoo_paper_submit.py`
- `tests/test_documentation_catalog.py`
- `docs/task-source.json`
- `docs/task-catalog.md`
- `docs/moomoo-openapi.md`
- `docs/implementation-plan.md`
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

Rollback: Disable the command, inspect the sanitized result, and reconcile the paper account manually before reverting ISSUE-039; an accepted paper order may require manual cancellation in the Moomoo app even though live capital is never involved.

## ISSUE-040: Add Moomoo US paper-order read-only reconciliation

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-039
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add an explicitly connected, read-only reconciliation boundary that re-queries an eligible Moomoo SIMULATE account by client-order remark and emits sanitized absent, unique, duplicate, or unknown evidence without submitting, changing, or cancelling an order.

### Acceptance Criteria

- Reconciliation requires an ISSUE-036 READY decision and a successful schema version 1 ISSUE-038 preflight result before creating a trade context.
- The service accepts only a validated 8-64 character client_order_id and reselects exactly one eligible ACTIVE US STOCK_AND_OPTION SIMULATE account while keeping acc_id in memory only.
- The service calls order_list_query exactly once with TrdEnv.SIMULATE, the selected acc_id, refresh_cache=True, and no automatic retry.
- Matching uses the exact broker remark and returns deterministic ABSENT, UNIQUE, DUPLICATE, BLOCKED, or UNKNOWN status with match count and fixed failure category only.
- ABSENT is evidence that the order was not visible in that query, not proof that no submission occurred; UNKNOWN and DUPLICATE block automatic resubmission.
- The immutable schema-versioned result excludes account IDs, broker order IDs, raw payloads, credentials, tokens, symbols, prices, quantities, SDK objects, and exception text.
- The trade context closes on success and every failure path; query exceptions and malformed responses are sanitized and never trigger place_order, modify_order, cancel_order, unlock_trade, subscription, or live trading.
- The CLI validates inputs and retained reports without loading the SDK by default and requires --connect for the single read-only localhost query.
- Unit and fixture tests use fake SDK/context objects to cover every status, account selection, exact query mapping, no retry, sanitization, context closure, and forbidden-operation boundaries.
- English, Japanese, Simplified Chinese, CLI, operations, limitations, rollback, feature documentation, implementation plan, and generated Task Catalog output are synchronized.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `src/autotrade/cli.py`
- `src/autotrade/execution/moomoo_paper_order.py`
- `src/autotrade/execution/moomoo_paper_reconcile.py`
- `tests/test_cli.py`
- `tests/test_moomoo_paper_reconcile.py`
- `tests/test_documentation_catalog.py`
- `docs/task-source.json`
- `docs/task-catalog.md`
- `docs/moomoo-openapi.md`
- `docs/implementation-plan.md`
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

Rollback: Disable the reconciliation command and inspect the Moomoo paper account manually before reverting ISSUE-040; the command creates no order mutation, but an earlier submitted paper order may still require manual handling.

## ISSUE-041: Persist sanitized Moomoo paper-order reconciliation evidence

- Status: `complete`
- Phase: `Phase 4`
- Dependencies: ISSUE-040
- Roadmap: see `docs/roadmap.md#phase-4`
- Summary: Add create-only deterministic report persistence and strict offline reading for sanitized Moomoo paper-order reconciliation results so canary and incident evidence can survive process restart without storing raw broker data.

### Acceptance Criteria

- A reconciliation report writer persists schema version 1 result JSON deterministically, creates parent directories, and never overwrites an existing file.
- A report reader accepts only UTF-8 JSON with the exact schema version 1 field set and reconstructs the immutable reconciliation result offline without loading the SDK or connecting to OpenD.
- Validation rejects unknown schemas, unknown fields, missing fields, invalid enums, invalid localhost endpoints, invalid SDK versions, invalid client-order IDs, booleans used as counts, inconsistent status/failure combinations, and malformed JSON.
- Reports contain only the existing sanitized reconciliation result and never include account IDs, broker order IDs, symbols, prices, quantities, credentials, tokens, raw payloads, SDK objects, or exception text.
- The reconciliation CLI accepts --report-output only with --connect, writes only after a completed query result, and returns exit code 2 on conflict or filesystem failure without a traceback.
- Report directories and matching report filenames are ignored by Git.
- Unit and fixture tests cover deterministic round trip, all validation boundaries, create-only conflicts, write failures, CLI no-write validation mode, and no-SDK offline reading.
- English, Japanese, Simplified Chinese, CLI, operations, limitations, rollback, feature documentation, implementation plan, ignore rules, and generated Task Catalog output are synchronized.

### Gates

- Python Unit Tests
- Fixture Tests
- Documentation Localization
- Markdown Links/Style
- Secret Scan
- Task Catalog Generation

### Changed Assets

- `.gitignore`
- `src/autotrade/cli.py`
- `src/autotrade/execution/moomoo.py`
- `src/autotrade/execution/moomoo_paper_reconcile.py`
- `tests/test_cli.py`
- `tests/test_moomoo_paper_reconcile.py`
- `tests/test_documentation_catalog.py`
- `docs/task-source.json`
- `docs/task-catalog.md`
- `docs/moomoo-openapi.md`
- `docs/implementation-plan.md`
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

Rollback: Disable report output, inspect retained reconciliation artifacts for sanitized fields, and delete local report files before reverting ISSUE-041 through a reviewed PR; report persistence creates no broker side effect.
