# W08 context worker

Status: **local context implementation complete; real-document content remains partial**.

## Actual changes

- `narrative_reading.py` retains the exact declared own-section ancestor headings. Missing, cyclic, duplicate or foreign-source parent trees remain deferred. Anonymous legacy local sections retain their explicit headings without receiving invented IDs.
- Prose/background labels no longer discard an explicitly declared typed table's original header, unit/period, note and row-anchor dependencies. Next-page reuse of a local table index cannot prove continuity.
- The verified original p14 had no business child scope. `structure/sections.py` now declares a source numbered-list scope only from a numeric-parenthesis opener, same native box with colon introduction, and indented bullet blocks. It is bounded to the same source/page/column and existing 24-unit limit, restores the parent at the next non-bullet block, and leaves insufficient geometry, inline lists, table/footnote and DOM structures alone.
- Public citation views keep actual row/body support separate from context; identical 30% text retains distinct original IDs/locators.

## Evidence

Before implementation, `red.stdout.txt/red.xml` recorded **4 pytest failures** for explicit ancestry and background table context. After correcting an initial test-fixture mappingproxy deepcopy error, `red-native-structure.stdout.txt/.xml` recorded **2 real structure failures, 1 negative-control pass**. The earlier fixture error remains recorded separately.

Final directly affected regression (`green-compatible.stdout.txt/.xml`): **185 passed**, including the 2 anonymous-section regressions found by the parent broader run. Read-only `git diff --check` passed for the 5 owned paths. Every run uses mother venv Python `-B`, explicit worktree `PYTHONPATH`; the initial RED verified module `__file__` before and after collection. Source and artifact hashes are in `context-worker.json`.

## Existing real original, offline observation

Source SHA `7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2`, 1,608,226 bytes, opened through the existing SourceVersionReader with `purpose=preview`; no PDF copy. Config and isolated catalog SQLite byte hashes stayed unchanged across probes.

Before: p14 Testing/Biology statements were both s52 body. After: native s54/s55 scopes retain each 30% target's own revenue-intro/colon and original ancestors. No sibling business was borrowed. This is shown in `native-baseline.json` and `native-after-final.json`.

The unchanged public **96 spans / 48,000 chars** planner still omitted both 30% targets: **1,459 candidates, 96 selected, 8,433 chars, budget_full=206, status=partial**. Testing's native carrier remains `description`; Biology is `meaningful_fact`. Neither the p13 native header/first-row block nor its typed first revenue row entered a candidate package in this bounded diagnostic. Therefore there is **no real-document content/table admission PASS** claim.

This read used bounded fine table pages [13,14] with all coarse pages read; it is not a sealed generation replay or all-page table/semantic acceptance. No budget was increased, source fact scorer duplicated, v5/store changed, network/model called, production config/DB written, or Git commit/checkout/install performed.

## Diagnostic errors and cleanup

A private `_understand` probe without the existing public document WorkBudget deferred and the probe incorrectly assumed `reading_plan`, causing KeyError. The public selector with its existing configured WorkBudget succeeded as partial above. A later probe accidentally printed the full deferred pipeline: the parent explicitly authorized removing that newly created 14,152,230-byte stdout after retaining SHA-256 `ee0474dbb90f3d2b4e48ab4180eab23c0be22b92d73c21ddea87104a6fa4752c` and the bounded reason/status summary in `context-worker.json`. Only that exact self-created file was removed after its resolved absolute path was checked. No sealed or pre-existing evidence was removed.

## Type convergence follow-up

Only type convergence was applied: proven bbox tuple coordinates replace equivalent optional property accesses; source-scope collections receive concrete annotations. The unchanged behavior passed 185 relevant pytest cases; full src mypy passed all 366 source files; Ruff passed both affected source files. Evidence is under `context-worker/types-fix-*`; refreshed file hashes are in the JSON ledger.

## Freeze handoff

ROOT requested freeze after the type fix. The non-author review is **incomplete and stopped**. Before that instruction arrived, one source-diff read and one eight-input pure-memory probe had occurred; its command, neutral inputs and captured raw output are retained in `context-worker/readonly-review-probe.json`. Two adjacent numeric identifier false-positive observations are **OPEN, unfixed**: “项目1在本节作介绍，具体内容另述。” and “客户2号账户的余额为172万元。” each became meaningful_fact with financial exemption. No new test, source fix or follow-up probe was performed after freeze. Existing real-document partial status remains.
