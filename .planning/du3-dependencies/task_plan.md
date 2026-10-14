# DU3-DEPENDENCIES independent PWF
PLAN_ID: du3-dependencies
PWF_PLAN_ROOT: C:\Users\郑曾波\Projects\_harness_worktrees\shared-reading-completion-20261014\dependencies/.planning
Owner: dependencies harness
base_sha: 195aba20b0aecc2d661d7d04c5ba72f982bc02d0
branch: codex/du3-dependencies-20261014
worktree: C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/dependencies
frozen_interface: DU3/1 (../INTERFACES.md section "决策依赖组件")

## Goal
Complete docs/plans/document-understanding-2026-10-13/parallel/du3-2026-10-14/cards/DU3-DEPENDENCIES.md
in this checkout only. One pure component: source-local decision-dependency identity and
difference. No router/selector, no catalog/file reads, no Store/CAS, no model/provider calls,
no master merge.

## Owned write scope (exclusive)
- src/company_wiki/document_understanding/decision_dependencies/**
- tests/unit/document_understanding_decision_dependencies/**
- tests/fixtures/document_understanding_decision_dependencies/**
- .planning/du3-dependencies/**

Not touched: parent `__init__`, profiles/registry/router, structure, selection_bridge,
summary_input, source_catalog, automation/generation, Store/SQL, ROOT PWF, other tests,
dependencies/CI/config/install. The package imports neither of the other two DU3 packages.

## Frozen public surface (DU3/1)
```python
def freeze_decision_dependencies(trace: Mapping, *, limits: Mapping | None = None) -> dict
def compare_decision_dependencies(frozen: Mapping, current: Mapping, *, limits: Mapping | None = None) -> dict
```
Wire: `du-decision-trace/1` in; `du-decision-dependencies/1` and `du-decision-comparison/1` out.

## Phases
1. [complete] A: read card/interface, record baseline, TDD RED first, then the full
   dependency mutation matrix with reversed controls. RED recorded:
   `51 failed in 1.80s`, `ModuleNotFoundError`, `evidence/a_red.json`.
2. [complete] B: implement the owned component on the frozen DU3/1 wire; concentrated
   unit/limits/identity tests incl. cross-process digest stability, closed manifest key
   set, budget enforcement, AST import guard and the 100-source size report.
3. [complete] C: read-only replay against the real installed `reading_catalog.json`
   (SHA-256 `29bfefbe...e18b46c`, unchanged) with synthetic legal scopes; relevant /
   irrelevant / ordering / whole-catalog matrix; small receipts; commit; handoff.

4. [complete] Independent review: two agents that did not write this code reviewed the
   committed state against the card and adversarially against the source. 17 findings,
   all fixed and pinned with counter-examples; see findings.md section 8.

Node runs after the fix round (`.planning/du3-dependencies/evidence/nodes.json`):
A 55 passed / exit 0 / 2.743s, B 64 passed / exit 0 / 4.154s,
C 19 passed / exit 0 / 2.557s, ALL 138 passed / exit 0 / 5.337s.
ruff exit 0, mypy exit 0. Regression over the five pre-existing DU packages:
496 passed, 17 skipped (634 passed / 17 skipped combined with this lane).

Implementation commit `bc63a74eac1f73e6184a87a4b1bb65044840c1ad`;
ledger commit `e430945fa8a536bac589be8ad6ddf3708379557c`.

## Next Step
None for this lane. Handoff written (`handoff.md` / `handoff.json`). STOP waiting for
ROOT: it instruments the real router/registry/selection to record a complete
`du-decision-trace/1` per source, supplies the current same-domain inventory, wires the
two frozen functions into the existing AUTO two-stage generation CAS, and accepts real
0POST/recovery in its own B node. No master merge and no production default change here.
