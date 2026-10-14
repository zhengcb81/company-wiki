# DU3-GEOMETRY independent PWF
PLAN_ID: du3-geometry
PWF_PLAN_ROOT: C:\Users\郑曾波\Projects\_harness_worktrees\shared-reading-completion-20261014\geometry/.planning
Owner: geometry harness
base_sha: 195aba20b0aecc2d661d7d04c5ba72f982bc02d0
branch: codex/du3-geometry-20261014

## Goal
Complete docs/plans/document-understanding-2026-10-13/parallel/du3-2026-10-14/cards/DU3-GEOMETRY.md in this checkout only. Use frozen DU3/1 and exact owned paths. No original/config writes, no model/provider calls, no master merge.

## Phases
1. [completed] A: read card/interface, record baseline, TDD RED and frozen fixtures. RED receipt in evidence/a-red-receipt.md.
2. [completed] B: implement owned component (layout_snapshots), concentrated unit/integration + limits; layout_hints read-only consumer regression (42 pass).
3. [completed] C: bounded real snapshots (4 originals via PyMuPDF dict/words/find_tables), original/tmp restoration, commit and handoff.

## Status
IMPLEMENTED / TESTED / NOT WIRED TO PRODUCTION. Public `project_layout_snapshot` only; no production entry calls it.

## Next Step
STOP after package handoff; ROOT integrates master (DEPENDENCIES -> GEOMETRY -> QUALITY). Independent agent review requested by user before final STOP. ROOT will pass the original parser's same snapshot/table read explicitly and connect observation_adapter/layout_hints to consume the fine metadata.
