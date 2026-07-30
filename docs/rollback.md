# Rollback

## Code Rollback

For an unmerged feature branch, revert by closing the Draft PR and deleting the branch after review.

For a merged change, create a new revert PR. Do not rewrite protected branch history.

## Generated Files

Generated catalogs must be rebuilt from their Source of Truth. Do not manually edit generated catalog output.

```bash
python3 scripts/generate_task_catalog.py
```

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

## kabu Station Mapper Rollback

The kabu Station mapper has no live broker side effects. Revert the ISSUE-017 branch if adapter-boundary payload mapping needs to be removed.

## kabu Station Contract Rollback

The kabu Station official request contract helpers have no live broker side effects. Revert the ISSUE-018 branch if token or sendorder payload construction needs to be removed.

## kabu Station Token Client Rollback

The kabu Station fake-transport token client has no live broker side effects. Revert the ISSUE-019 branch if token response handling needs to be removed.

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
