# Operations

## Daily Research Run

1. Pull the latest approved `main`.
2. Confirm no local secrets or untracked production files exist.
3. Run the applicable unit tests.
4. Run research or demo commands against non-live data.
5. Record gate results as `passed`, `failed`, `not-run`, or `skipped`.

## Strategy Research Run

When evaluating ORB or VWAP signals, include spread and order book health fields in fixtures. A stale or unhealthy book should suppress signals before any risk or execution decision is built.

For ISSUE-043 historical ORB research, retain gzip CSV bars and their manifest under ignored `historical-data/`. Run validate-only first and stop on any required-schema, hash, row-count, date-range, or symbol-set mismatch; additive manifest metadata is permitted. Use `--run` only after validation, preserve atomic create-only schema version 2 reports under `historical-backtest-reports/`, and review `default_parameter_full_period`, baseline and doubled cost scenarios, per-symbol attribution, and every Walk-Forward test fold. Require `test_days <= step_days <= train_days`. Keep the default training promotion gates at non-negative Sharpe and Profit Factor `>= 1.0`; a fold with no eligible candidate is a No-Go, not permission to select the least negative parameter. A positive aggregate result does not override a failed fold or authorize paper submission.

For ISSUE-044 tuning, record the complete CLI and thresholds before execution. Review all rejection reasons, robustness ranks, selected-fold count, aggregate outer-test metrics, symbol concentration, and double-cost scenario. Treat `no-go` as final for that parameter search. The 192-candidate schema version 4 extension includes 96 exploratory structure-filter candidates and reused dates already observed by the project; its 1-of-4 selected-fold result is contaminated evidence, not an independent validation. Do not rerun with weaker gates after reading outer-test output; changing the grid, filters, objective, or gates requires a new Issue and a newly reserved test period. A `candidate` decision still requires independent review and does not authorize paper or live trading.

## OMS State Handling

Treat `UNKNOWN` as a blocking operational state. It means the system cannot safely infer whether the broker accepted, rejected, filled, or cancelled an order until reconciliation confirms the broker state.

## Ledger Handling

Use the local ledger only for research, replay, and simulation. A fill that references an unknown local order should be treated as an operational error until reconciliation explains it.

## Risk Pause Handling

Use `RiskManager.pause(reason)` when an incident requires blocking all new order approvals. Resume only after the reason has been reviewed and any required reconciliation is complete.

## Reconciliation Handling

Treat critical reconciliation discrepancies as blocking. A broker order missing from the local OMS, an `UNKNOWN` local order, or a position mismatch should pause new approvals until the discrepancy is explained.

## Simulated Broker Handling

Use the simulated broker only for tests, replay, and simulation. Fills must be injected by fixtures or replay orchestration; the simulator does not independently match against live market data.

Use `state_snapshot()` when reconciliation fixtures need broker-shaped open orders and positions from the simulator.

## Replay Execution Handling

Use replay execution only with local market snapshots and simulated broker state. Replay results are for fixture validation and must not be treated as live execution evidence.

Critical reconciliation discrepancies during replay should fail fast and be investigated from the replay fixture, OMS records, simulated broker state, and local ledger before the fixture is trusted.

## Shadow Mode Readiness Handling

Use `ShadowModeReadinessGate` only on local replay results. A blocked decision means the replay evidence is not operationally clean enough for later Shadow Mode review; inspect critical reconciliation reports, risk pause state, missing reconciliation evidence, and remaining simulated broker open orders before proceeding.

Use `ShadowModeRunSummary` when a local readiness decision needs an audit-friendly summary of trading date, status, reasons, and metrics. Treat it as local review output only; it is not persistence and does not authorize live trading.

Use `ShadowModeSummaryWriter` when a run summary needs a local JSON artifact for fixture review. Do not overwrite an existing summary file unless a later reviewed change adds explicit replacement semantics.

Use `ShadowModeSummaryReader` only for local summary JSON artifacts. A reader validation error means the summary file is not usable as review evidence until the file source and schema are inspected.

Treat `schema_version` as part of the local summary review contract. A summary with a missing or unsupported schema version should be regenerated or reviewed before it is used as evidence.

Use `ShadowModeSummaryReview` to aggregate already-loaded local run summaries for fixture review. Empty review inputs are invalid because they provide no operational evidence.

Use `ShadowModeReviewWriter` when a summary review needs a local JSON artifact. Do not overwrite an existing review file unless a later reviewed change adds explicit replacement semantics.

## kabu Station Mapper Handling

Use the kabu Station mapper only for local adapter-boundary tests. It must not be treated as a live broker client, and its payload shape must stay behind the broker adapter boundary until a later reviewed issue approves real API calls.

Official kabu Station contract helpers may construct token and sendorder payloads, but they must not store passwords, open network connections, or place orders until a later adapter issue explicitly approves those behaviors.

The kabu Station token client must use an injected transport in tests and must not create a real HTTP client until a later localhost probe issue explicitly approves that boundary.

`KabuStationLocalhostHttpTransport` may be explicitly constructed for localhost-only adapter tests and the Windows read-only probe. Use it only with `http://localhost`, `http://127.0.0.1`, or `http://[::1]` URLs. Unit tests inject fake openers or fake transports and must not access the network. Existing clients must still receive a transport through dependency injection.

The default localhost transport policy allows only POST `/kabusapi/token` for authentication and GET `/kabusapi/orders` plus GET `/kabusapi/positions` for read-only checks. It rejects `sendorder`, `cancelorder`, remote hosts, remote redirects, userinfo URLs, non-HTTP schemes, empty responses, invalid JSON responses, connection failures, and timeouts as local domain errors. Real sendorder and cancelorder remain prohibited and require a later independent issue plus Human Code Owner approval.

Redirected requests must pass the same loopback and read-only endpoint policy as their original request. Percent-encoded endpoint paths are invalid. Treat `configuration` as a URL or policy failure at any probe stage, and treat `system` as a local operating-system failure such as denied socket access. A `connection` or `timeout` category during orders or positions means the authenticated connection failed later; `connection_status` remains `ok` to preserve evidence that authentication had already connected successfully.

Use `python -m autotrade.cli kabu-readonly-probe --environment test` for validate-only mode. This mode must not construct a runtime transport or connect to localhost. After kabu Station is available on Windows, use `--connect` with `KABU_STATION_API_PASSWORD` or `--prompt-password` to run only the read-only probe. A failed probe means Shadow Mode or live trading must not continue.

Probe reports are deterministic JSON evidence files with schema version 1. Store them outside Git, for example under `kabu-probe-reports/`. Before sharing a report, confirm it contains only statuses, counts, timestamp, localhost endpoint, environment, schema version, and sanitized failure category.

Probe report files are create-only. If the requested path exists, review the existing artifact and select a new path or remove it intentionally; the CLI returns exit code `2` and does not overwrite it.

The kabu Station sendorder client must use an injected transport in tests. Treat it as contract plumbing only; no real order submission is approved by this issue.

The kabu Station cancelorder client must use an injected transport in tests. Treat it as contract plumbing only; no real order cancellation is approved by this issue.

The kabu Station read-only client must use an injected transport in tests. Treat orders and positions responses as fake-transport contract data only; no real account query is approved by this issue.

The kabu Station snapshot mapper may convert fake or read-only payloads into reconciliation fixtures. Treat the result as broker-shaped local data only; it is not live reconciliation evidence without a separately approved real read path.

The kabu Station read-only reconciler may orchestrate an injected read-only client, snapshot mapper, OMS, ledger, reconciliation engine, and optional `RiskManager`. Treat its reports as local reconciliation results over supplied fake-client data only; it must not construct a real transport, query a live account, submit orders, or cancel orders.

## Moomoo OpenAPI Discovery Handling

Moomoo OpenAPI is now the first broker API proof of concept because OpenD and the Python SDK can run on macOS. ISSUE-035 provides `moomoo-readonly-discovery` using OpenD and the optional `moomoo-api` dependency `>=10.4.6408`, imported as `moomoo`, for configurable loopback reachability at `127.0.0.1:11111`, version, sanitized account-list shape, US capability, JP equity market-data entitlement metadata, and paper-account availability.

The discovery path must make no live orders, must not call `unlock_trade`, must not log account identifiers or credentials, and must fail closed when OpenD, authentication, account capability, or response compatibility is unknown. Trading must not be unlocked through SDK code in any environment. Any future real-trading unlock requires a separately approved workflow and manual action in the OpenD GUI. A successful discovery report is compatibility evidence only; it does not authorize Shadow Mode, paper orders, or live orders.

Install the SDK only as an isolated optional dependency or in a dedicated virtual environment. Verify the resolved `protobuf` dependency without silently changing unrelated runtime packages; the tested `moomoo-api` 10.9.6908 environment resolved `protobuf` 7.35.1 successfully.

Run validate-only mode before installing or importing the SDK. Use `--connect` only after OpenD is running and logged in. Store reports under `moomoo-discovery-reports/`, inspect only sanitized fields, and treat any nonzero exit as blocking. Discovery JSON is emitted before the optional report write, so exit code `2` means persistence failed even when stdout contains a successful result. Do not use a successful discovery as permission to enable paper or live order code.

Run `moomoo-paper-readiness --discovery-report PATH` only against a retained sanitized schema version 1 report. The command is offline and must not require OpenD to be running. Treat login `null` as "not checked" and `false` as "checked but not logged in" during triage. Invalid encoding fails cleanly with exit code `2`. Archive the deterministic immutable `READY` or `BLOCKED` JSON with research evidence if needed, but do not treat `READY` as approval to select an account, unlock trading, subscribe to data, or place an order. A paper-order path requires a new reviewed Issue.

Run `moomoo-paper-order-dry-run` only after reviewing a retained `READY` discovery report. Verify the explicit code, 8-64 character client order ID, order style, quantity, finite prices, timestamp, USD 25,000 notional cap, and 100-share cap. For BUY, require `stop < limit < take-profit` when take-profit is present. The result must remain `SIMULATE` / `NORMAL` / `DAY` / `RTH` and contain no account identifier. Archive it only as local design evidence. It neither selects an account nor sends a paper order, so there is no broker order to reconcile or cancel.

Run `moomoo-paper-account-preflight` in validate-only mode first. Use `--connect` only while OpenD is logged in and only with a retained report that evaluates to `READY`. The command must find exactly one active US `SIMULATE` `STOCK_AND_OPTION` account and run fresh funds, positions, and order-list reads. Treat zero or multiple eligible accounts, any failed read, or any nonzero exit as blocking. Store create-only reports under `moomoo-preflight-reports/` and confirm they contain classifications and counts only. Never paste an account ID or raw SDK payload into an incident, log, or PR. A passed preflight proves read compatibility only and does not authorize a paper order.

Run `moomoo-paper-order-submit` without confirmation flags first and review the preview. A real paper canary requires separate approval of symbol, quantity, limit, stop, timestamp, retained discovery evidence, and retained preflight evidence. Only then add all three confirmation flags. The command can call `place_order` once and has a simulated broker side effect. If the result is `UNKNOWN`, `submitted`, nonzero, or interrupted after connection, stop and inspect the Moomoo app/order list by client-order remark. Do not rerun the command, change the client order ID, or assume rejection until reconciliation is complete.

For ISSUE-042 durable evidence, add `--report-output` under `moomoo-submission-reports/` only to an already approved, fully confirmed submission command. A report is written only after exactly one `place_order` attempt. Preserve `rejected`, `unknown`, `submitted`, and `verified` artifacts as create-only schema version 1 files; never replace one with a later result. Treat `connection` as a pre-account-selection transport or response failure, while `verification` after one submission attempt remains an uncertain broker-side outcome. If submission is blocked before the call or persistence fails, expect exit code `2` and record that stdout is transient only. Read reports offline and pair uncertain outcomes with fresh reconciliation and manual app inspection.

Run `moomoo-paper-order-reconcile` without `--connect` first to validate the retained READY discovery report, successful schema version 1 preflight report, loopback endpoint, and client order ID. Then use `--connect` for one fresh `SIMULATE` order-list query with `refresh_cache=True`. Archive only the sanitized result. `unique` confirms one visible exact remark match. `ABSENT` is not proof that no submission occurred; `duplicate` and `unknown` are ambiguous. None of these results authorizes automatic resubmission, modification, or cancellation. Inspect the Moomoo app and escalate before any further paper-order command.

For durable ISSUE-041 evidence, add `--report-output` under `moomoo-reconciliation-reports/` only to the connected reconciliation command. Reports are create-only and schema version 1; never delete or replace an existing artifact before incident review. Confirm the file contains only the client order ID, sanitized states, counts, endpoint, SDK/schema versions, refresh evidence, and a fixed failure category. Use the strict reader for offline restart review. If the query does not run or persistence fails, expect exit code `2`, treat stdout as transient, and record that no durable artifact was created.

## Issue Workflow

0. Read `AGENT.md`.
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

## Credential Exposure Handling

If an API password, API token, complete authentication response, request header, account identifier, order payload, or position payload is exposed in logs, terminal output, reports, commits, screenshots, or chat:

1. Stop the probe and do not continue Shadow Mode or live trading.
2. Revoke or rotate the affected Moomoo or kabu Station credential/token using the broker-supported procedure.
3. Remove the exposed artifact from local report directories and any PR or issue comment.
4. Run the secret scan and inspect generated probe reports before retrying.
5. Record the incident and only resume with sanitized evidence.
