# Rollback

## Code Rollback

For an unmerged feature branch, revert by closing the Draft PR and deleting the branch after review.

For a merged change, create a new revert PR. Do not rewrite protected branch history.

## Generated Files

Generated catalogs must be rebuilt from their Source of Truth. Do not manually edit generated catalog output.

```bash
python3 scripts/generate_task_catalog.py
```

## Live Trading Rollback

Live trading is not supported yet. Future live rollback must follow this order:

1. Disable new signals.
2. Block new orders.
3. Cancel open orders.
4. Query broker positions and fills.
5. Reconcile local and broker state.
6. Flatten positions only through approved emergency procedures.
7. Lock automatic restart until human review is complete.
