# Rollback

## Code Rollback

For an unmerged feature branch, revert by closing the Draft PR and deleting the branch after review.

For a merged change, create a new revert PR. Do not rewrite protected branch history.

## Generated Files

Generated catalogs must be rebuilt from their Source of Truth. Do not manually edit generated catalog output.

```bash
python3 scripts/generate_task_catalog.py
```

## Moomoo Broker Priority Rollback

ISSUE-034 changes requirements and documentation only. It adds no Moomoo OpenAPI SDK, connection, credential, paper order, `unlock_trade` call, or live order capability. Revert the ISSUE-034 branch through a reviewed PR to restore kabu Station as the next runtime validation target and IBKR as the only planned US adapter. Remove the dependent ISSUE-035 task from the Source of Truth and regenerate the Task Catalog; do not manually edit the generated catalog. There are no live orders to cancel or broker state to reconcile from this decision change.

## Moomoo Read-only Discovery Rollback

ISSUE-035 has no order or market-data subscription side effects. Revert its branch through a reviewed PR, remove the `moomoo` optional dependency, and delete local `moomoo-discovery-reports/` artifacts after confirming they contain only sanitized schema version 1 fields. Transient stdout output requires no cleanup, but a report write failure must not be mistaken for a persisted artifact. Stop OpenD manually if it is no longer needed. No orders require cancellation and no positions require reconciliation.

## Moomoo Paper Readiness Rollback

ISSUE-036 is offline and has no SDK, broker, subscription, order, or position side effects. Revert its branch through a reviewed PR and remove the readiness CLI and immutable decision model. Tri-state readiness output is transient and needs no cleanup. Existing sanitized discovery reports remain valid ISSUE-035 evidence and require no broker reconciliation.

## Moomoo Paper-order Dry-run Rollback

ISSUE-037 is offline and has no SDK, account-selection, broker, subscription, order, fill, or position side effects. Revert its branch through a reviewed PR and remove the planner, shared readiness reader, CLI command, and validation rules. Dry-run stdout is transient design evidence; no order requires cancellation and no broker state requires reconciliation.

## Moomoo Paper-account Preflight Rollback

ISSUE-038 performs read-only account, funds, position-list, and order-list calls only. Revert its branch through a reviewed PR, remove the preflight service and CLI, and delete local `moomoo-preflight-reports/` artifacts after checking that they contain only sanitized schema version 1 fields. No order was placed, modified, or cancelled, so no broker order or position reconciliation is required.

## Moomoo Paper-order Submission Rollback

Disable ISSUE-039 invocation first. Inspect the Moomoo paper account for every attempted client-order remark and manually cancel any unwanted open paper order in the Moomoo app before reverting through a reviewed PR. Do not infer that an exception means no order exists. No live-capital order is possible because the implementation exposes `SIMULATE` only.

## Moomoo Paper-order Reconciliation Rollback

Disable the ISSUE-040 reconciliation command and inspect every previously queried client-order remark in the Moomoo app before reverting through a reviewed PR. The command itself is read-only and creates no new broker side effect, but removing it does not remove or cancel an order submitted earlier through ISSUE-039. Treat retained `absent`, `duplicate`, and `unknown` evidence as unresolved until manually reviewed.

## Moomoo Reconciliation Report Rollback

Disable ISSUE-041 `--report-output` first. Inspect every retained file under `moomoo-reconciliation-reports/` for sanitized schema version 1 fields, preserve any artifact needed by an incident review, and delete local reports only after approval. Revert the writer, reader, CLI option, and ignore rules through a reviewed PR. Report persistence is local and read-only, so it creates no broker order to cancel.

## Moomoo Submission Report Rollback

Disable ISSUE-042 submission `--report-output` first, but do not assume removing local persistence reverses a paper order. Preserve canary and incident artifacts, inspect the Moomoo paper account for every attempted client order ID, and resolve `unknown` or `submitted` outcomes before deleting reports under `moomoo-submission-reports/`. Revert the writer, reader, CLI option, and ignore rules only through a reviewed PR.

## Strategy Filter Rollback

If market quality filters suppress expected research signals, remove `max_spread_bps` and `require_fresh_order_book` from strategy configuration first. If the issue is code-level behavior, revert the ISSUE-007 branch in a new PR.

## OMS Rollback

The current OMS has no broker side effects. Revert the ISSUE-008 branch if state transitions need to return to the previous execution skeleton.

## Ledger Rollback

The current local ledger has no broker or persistent side effects. Revert the ISSUE-009 branch if accounting behavior needs to return to the previous execution skeleton.

## Risk Pause Rollback

The current paused state has no broker side effects. Revert the ISSUE-010 branch if approval behavior needs to return to the previous risk skeleton.

## Reconciliation Rollback

The current reconciliation checks have no broker or persistent side effects. Revert the ISSUE-011 branch if comparison behavior needs to return to the previous execution skeleton.

## Simulated Broker Rollback

The simulated broker has no live broker side effects. Revert the ISSUE-012 branch if simulator behavior needs to return to the previous adapter skeleton.

## Simulated Broker Snapshot Rollback

The simulated broker snapshots have no live broker side effects. Revert the ISSUE-013 branch if simulator reconciliation output needs to be removed.

## Replay Execution Rollback

The replay execution loop has no live broker side effects. Revert the ISSUE-014 branch if replay orchestration needs to return to the previous execution skeleton.

## Shadow Mode Readiness Gate Rollback

The Shadow Mode readiness gate has no live broker side effects. Revert the ISSUE-025 branch if local readiness decisions need to be removed from replay review.

## Shadow Mode Run Summary Rollback

The Shadow Mode run summary has no live broker side effects. Revert the ISSUE-026 branch if local readiness summary output needs to be removed.

## Shadow Mode Summary Writer Rollback

The Shadow Mode summary writer has no live broker side effects. Revert the ISSUE-027 branch if local summary JSON output needs to be removed.

## Shadow Mode Summary Reader Rollback

The Shadow Mode summary reader has no live broker side effects. Revert the ISSUE-028 branch if local summary JSON loading needs to be removed.

## Shadow Mode Summary Schema Version Rollback

The Shadow Mode summary schema version has no live broker side effects. Revert the ISSUE-029 branch if local summary schema version checks need to be removed.

## Shadow Mode Summary Review Rollback

The Shadow Mode summary review aggregate has no live broker side effects. Revert the ISSUE-030 branch if local summary review counts need to be removed.

## Shadow Mode Review Writer Rollback

The Shadow Mode review writer has no live broker side effects. Revert the ISSUE-031 branch if local summary review JSON output needs to be removed.

## kabu Station Mapper Rollback

The kabu Station mapper has no live broker side effects. Revert the ISSUE-017 branch if adapter-boundary payload mapping needs to be removed.

## kabu Station Contract Rollback

The kabu Station official request contract helpers have no live broker side effects. Revert the ISSUE-018 branch if token or sendorder payload construction needs to be removed.

## kabu Station Token Client Rollback

The kabu Station fake-transport token client has no live broker side effects. Revert the ISSUE-019 branch if token response handling needs to be removed.

## kabu Station Localhost HTTP Transport Rollback

The kabu Station localhost HTTP transport has no default client wiring and no live broker side effects in tests. Revert the ISSUE-032 branch if explicit localhost HTTP transport support needs to be removed.

## kabu Station Read-only Probe Rollback

The kabu Station read-only probe, CLI, and report reader/writer have no live order side effects and are limited to token authentication plus read-only orders and positions queries. Revert the ISSUE-032 localhost boundary branch if the runtime probe path needs to be removed. Delete any local `kabu-probe-reports/` files after confirming they contain no credentials or raw account data.

## kabu Station Localhost Hardening Rollback

The redirect, encoded-path, error-classification, opener-lifecycle, and CLI report-write hardening has no live order side effects. Revert the ISSUE-033 branch only through a reviewed PR; doing so restores the weaker ISSUE-032 boundary and must not be used for a Windows probe until security review is repeated.

## kabu Station Sendorder Client Rollback

The kabu Station fake-transport sendorder client has no live broker side effects. Revert the ISSUE-020 branch if sendorder response handling needs to be removed.

## kabu Station Cancelorder Client Rollback

The kabu Station fake-transport cancelorder client has no live broker side effects. Revert the ISSUE-021 branch if cancelorder response handling needs to be removed.

## kabu Station Read-only Client Rollback

The kabu Station fake-transport read-only client has no live broker side effects. Revert the ISSUE-022 branch if orders or positions response handling needs to be removed.

## kabu Station Snapshot Mapper Rollback

The kabu Station snapshot mapper has no live broker side effects. Revert the ISSUE-023 branch if broker snapshot conversion needs to be removed.

## kabu Station Read-only Reconciler Rollback

The kabu Station read-only reconciler has no live broker side effects. Revert the ISSUE-024 branch if local read-only reconciliation orchestration needs to be removed.

## Agent Rules Rollback

Revert the ISSUE-015 branch if the root agent rules document needs to be removed or replaced.

## Live Trading Rollback

Live trading is not supported yet. Future live rollback must follow this order:

1. Disable new signals.
2. Block new orders.
3. Cancel open orders.
4. Query broker positions and fills.
5. Reconcile local and broker state.
6. Flatten positions only through approved emergency procedures.
7. Lock automatic restart until human review is complete.

## Historical ORB Backtest Rollback

Disable `historical-orb-backtest`, preserve any local schema version 1 or 2 report needed for research review, and remove ignored cache, temporary, or report artifacts only after confirming they are no longer required. Revert ISSUE-043 through a reviewed PR. Do not reinterpret an older `baseline` key as the schema version 2 `default_parameter_full_period` key. This rollback has no broker order, account, or position side effect.

## ORB Parameter Tuning Rollback

Disable `historical-orb-backtest --tune`, preserve schema version 3 tuning reports required for research audit, and revert ISSUE-044 through a reviewed PR. Removing the tuner does not restore the prior Sharpe values because ISSUE-044 also corrects zero-trade date accounting; explicitly revert that metrics change only if reviewers accept the older biased calculation. No broker order, account, or position side effect exists.
