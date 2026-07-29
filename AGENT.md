# Agent Rules

This repository is built through small, reviewable Issues. Agents must follow these rules before changing code, documentation, generated files, or GitHub state.

## Start of Work

Before starting an Issue:

1. Check the latest GitHub Issues and associated PRs.
2. Check the current branch, working tree, and `main`.
3. Pull the latest approved `main`.
4. Read the relevant assets, CLI documentation, tests, governance docs, and incident guidance.
5. Output a short implementation plan.
6. Start only the first unfinished Issue whose dependencies are satisfied.

If no ready Issue exists, add the next small roadmap task to `docs/task-source.json` and regenerate the catalog from the source of truth.

## Test-first Workflow

Every Issue follows Test-first development:

1. Add a failing test or documentation check first.
2. Confirm the test fails because the target behavior is missing.
3. Implement the smallest complete behavior.
4. Run affected unit, integration, and fixture tests.
5. Run every applicable Repository Gate.

Do not claim unrun checks as passed.

## Repository Gates

Every PR must report each applicable gate as one of:

- `passed`
- `failed`
- `not-run`
- `skipped`

Required gates include:

- Python Unit Tests.
- Documentation Localization.
- Markdown Links/Style.
- Secret Scan.
- Applicable fixture or end-to-end design tests.
- Task Catalog Generation when task metadata changes.

Use `not-run` when a gate could not execute. Use `skipped` only when the PR explains why the gate is not applicable.

## Documentation

When behavior changes, update the relevant documentation:

- English overview.
- Japanese overview.
- Simplified Chinese overview.
- CLI Usage.
- Operations.
- Limitations.
- Rollback.
- Architecture or feature-specific docs when applicable.

Documentation must describe current behavior and limitations. Do not document future live-trading behavior as already available.

## Generated Files

Generated files must be rebuilt only from their Source of Truth.

- `docs/task-catalog.md` is generated from `docs/task-source.json`.
- Run `python scripts/generate_task_catalog.py` after changing task metadata.
- Do not manually edit generated Catalog output.
- Do not manually edit generated Gherkin files if such files are added later.

## Git and PR

Every Issue uses an independent feature branch:

1. Use `feat/issue-...` branch naming.
2. Do not push directly to `main`.
3. Do not bypass Branch Protection.
4. Do not merge PRs.
5. Push the completed feature branch.
6. Create a Draft PR through `.github/workflows/open-pr-as-codex-app.yml`.
7. Use the repository PR template.
8. Confirm the PR author is the configured GitHub App.
9. Wait for CI, independent Review, and Human Code Owner approval.

Do not merge the PR. Stop after the Draft PR is created and CI status is reported.

## Draft PR Body

Every Draft PR must include:

- Requirement Summary.
- Confirmed / Assumed / Unknown / Out of Scope.
- Changed Assets.
- Architecture Decision.
- Test-first Evidence.
- Validation Results.
- Security Considerations.
- License and Compatibility Impact.
- Known Limitations.
- Rollback Plan.
- Traceability.

## Local Safety

- Never revert user changes unless explicitly asked.
- Ignore unrelated dirty working tree files.
- If changes in touched files conflict with the task, work with them instead of discarding them.
- Avoid destructive Git commands.
- Do not store secrets in the repository.
- Do not add broker credentials or live broker calls unless a later approved Issue explicitly requires them.

## Trading Safety

Current implementation is research, replay, and simulation only.

- No live broker order placement is approved.
- Strategies must not call broker APIs directly.
- Risk, OMS, ledger, reconciliation, and simulated broker layers must stay broker-independent until a reviewed adapter Issue approves a live boundary.
- Browser scripting, screen scraping, and private endpoint automation are out of scope.
