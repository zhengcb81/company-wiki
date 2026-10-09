# W08 native source refusal follow-up handoff

## Scope and exact source

- Owned RF worktree: `C:/Users/郑曾波/AppData/Local/Temp/rf-fresh-dag-20261009`.
- Branch: `codex/fresh-typed-cause-20261009`.
- Parent: `1a0608026c0f5c1419642078461c033b111e7a07`.
- Normal fix commit: `3c3c03792b189734aac5a0c8900b67b2c6f73ca5`.
- Commit hooks: ruff, public-contract mypy and host-assumption guard all passed; worktree clean afterward.
- This worker did not merge, push or install. MAIN owns independent follow-up review, integration and the normal push gate. This is not M3 acceptance.

## Root cause and repair

The normal RF pre-push blocked two existing negative cases before upload: a mismatched fiscal year and an actually corrupted raw document. Both rejections were still enforced, but W08's safe wrapper discarded the finite native diagnostic. This was real diagnostic semantic loss, not a reason to remove the negative tests or weaken byte/period predicates.

The repair adds optional finite `source_failure_reason` to the existing public observation projection. `company_wiki_source_reader_v2.py` attaches approved metadata after native byte/period checks or a validated native refusal; the common projector carries the same field across RF client and preparation CLIs. Original six-field provider cause, observed usage/counts, failure exit codes and existing SHA/period/as-of acceptance conditions remain intact. Unknown or malformed diagnostics are not echoed. Source-reader stage remains an honest composite stage.

Candidate kind/year/period mismatches now carry typed finite metadata before opening. The public message keeps useful stable wording (e.g. `fiscal_year mismatch` or `source reader refused: no_verified_location`) derived from that metadata. It does not copy raw exception text. Missing observation counts remain null, not fabricated zero.

Adjacent RED fixtures demonstrated that list-valued native schema/status fields caused TypeError before safe refusal handling. Only two string type guards were added before existing membership checks; malformed receipts still refuse, and no validation predicate was relaxed.

## Evidence and tests

All evidence is in RF `docs/plans/fresh-typed-cause-2026-10-09/`; earlier captures are preserved.

- `reader-cause-red.txt/json`: exact two original failures, 2 FAIL / 6.24 seconds.
- `native-reason-red.txt`: six finite native-refusal REDs, with unknown-body controls passing.
- `native-wire-red.txt`: one public optional-field propagation RED.
- `native-shape-red.txt`: two malformed-native-shape REDs.
- `native-final.txt/json`: **159 PASS, 1 existing Windows-inapplicable POSIX skip, 33.06 seconds**. All 49 current failure-observation cases ran, including every previous 36-case W08 control.
- Final changed-file ruff passed; public-contract mypy passed for eight files; diff whitespace check passed.
- Network/paid calls: 0. Synthetic originals/config only. Owned TEMP removed and absent after test completion. Production original documents and actual input/capture records were not modified.

The final responsibility set contains both P5 modules caught by pre-push, native reader byte/period/as-of checks, failure observations/causes, filing client, source preparation, complete-result/deadline and narrative transport tests. The corrupt/refuse/heal case still changes actual fixture bytes, checks exit 3, actual calls=2/downloads=0 and no raw-path echo, restores exact original bytes, then verifies same-SHA reuse and zero downloads. Bad candidate negatives now exercise kind/year/period and assert no verified open.

## Write set and install handoff

Runtime changes are exactly:

1. `scripts/company_wiki_source_reader_v2.py`
2. `scripts/filing_upstream_cause.py`
3. `scripts/filing_fetch_client.py`
4. `scripts/source_preparation.py`

Four matching test files and this lane's own PWF/evidence accompany them. No CWP/FF producers, accounting ledger, CI/hooks, installed runtime, configuration, keys or production originals were changed.

`runtime-install-delta.json` records four code files across three logical install locations: 12 observed logical differences, eight currently resolved physical paths, zero missing files. MAIN must re-resolve parent junctions and deduplicate physical targets before targeted synchronization. This is not twelve independent physical files. Configuration/output/unknown installed paths remain outside this worker's scope.

## Acceptance limit and next action

Earlier independent W08 acceptance predates this follow-up; it does not sign off these new changes. MAIN should independently review the finite native projection and actual refusal/heal behavior, then integrate and run the ordinary RF pre-push responsibility suite. Existing historical FF diagnostic channels outside the frozen W08 write set are not claimed globally safe. No unknown historical usage/costs were reconstructed, no new human approval/permission chain was introduced, and no stage precision beyond available native evidence is claimed.

The coverage improvement is a responsibility mapping: native-wrapper changes include existing P5 default-v2, real CLI corruption/heal and native-reader verification suites at the implementation boundary. Static pre-commit remains fast; broader normal pre-push protects integration. No per-small-step review gate was added.
