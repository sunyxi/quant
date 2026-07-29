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

## Live Trading Rollback

Live trading is not supported yet. Future live rollback must follow this order:

1. Disable new signals.
2. Block new orders.
3. Cancel open orders.
4. Query broker positions and fills.
5. Reconcile local and broker state.
6. Flatten positions only through approved emergency procedures.
7. Lock automatic restart until human review is complete.
