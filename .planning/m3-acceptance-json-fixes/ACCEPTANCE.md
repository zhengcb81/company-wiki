# M3-JSON acceptance root fixes — 2026-10-10

## Result

External delivery runtime commit: `8abfad074057ff8d5c89e01aea8f87a73be5405f`; final delivered branch HEAD: `4fc9ee1b1623901807fb2d69509f138a94df64eb`. Its existing responsibility/compatibility suite was independently rerun: **280 passed in 111.40s**. That engineering result did not cover persisted consumer lookup, multi-page export, derivative semantic validation, or revised answers before an as-of cutoff.

Acceptance counterexamples were written before implementation: **15 failed**, then **20 failed** with object/array token SHA checks. Logs: `red.log`, `red-with-container-sha.log`. Repairs plus the existing 107 responsibility tests and additional compatibility/control coverage: **133 passed in 16.17s** (`green-restored.log`). Ruff passes; mypy passes for the two modified runtime modules. One intermediate mypy error is preserved in `mypy.log`, corrected result in `mypy-final.log`.

## Actual roots fixed

1. Persist wrote only the identity payload, omitting projection ID/SHA, while load required the full DTO. Persist now stores the full immutable DTO; public CLI replay/export by projection ID passes.
2. Object/array nodes calculated the SHA before the final byte range existed and never recalculated it. Final container SHA now binds actual bytes at every close, including empty and nested/root containers. The structure parser version is **1.0.1**.
3. Multi-page records lacked an explicit parent, replay searched ambiguous pointer/empty hashes across all pages, and every EvidenceSpan used the first parent. Each record now carries `parent_content_sha256`; consumers bind source and lexical ordinal to that exact page.
4. Replay/export accepted metadata that merely self-hashed, without proving role/issuer/time/selection/coverage against the parent. Both consumers open raw once, reconstruct the projection with its recorded adapter/issuer/cutoff, and require the full derived semantics to match. This is data correctness at the consuming responsibility layer; no human permission, canary, review receipt, or new task database was added.
5. Creation time alone admitted answers edited after the cutoff. The latest parseable record create/update/audit date determines availability; future revisions are excluded, opaque revision dates stay unknown, and precollected answers with no known answer revision/availability stay unknown. First answer publication is still explicitly unknown; no capture date is substituted.
6. Distinct activity/question/answer issuer IDs were unioned into an ownership proof. Such record-level conflicts remain raw observations and cannot produce an issuer's business projection until field-level attribution is known. Other frozen issuer records remain unchanged.

## Version / compatibility matrix

| Object | Supported behavior |
|---|---|
| SourceRef 2.0 whole original / SourceExport 1 and 2.0 / manifest 1.0.0 | Unchanged; previous responsibility/compatibility tests green |
| source-projection-ref/1 + structure parser 1.0.1 + official parser cwp_official_json/1.0.1 | Requires per-record parent_content_sha256; full DTO persistence, reconstruct-and-verify replay/export |
| Sealed source-projection-ref/1 + structure parser 1.0.0 | Typed `unsupported_parser_version`, never silently reinterpreted as 1.0.1; raw remains independently readable; sealed DTO is not rewritten |
| Original broken persisted payload missing projection_id/SHA | Typed `invalid_projection_payload`; no fabricated identity or destructive upgrade |
| Unknown declared layout | Existing typed unsupported behavior and original retention remain |
| Unknown answer first-publication / provider timezone | Remain unknown; no inferred answer date, UTC conversion, or human approval workflow |

The projection /1 contract has not previously been published on main. The new field completes this unreleased contract. MAIN must bind AUTO generation to adapter/parser identity and each record's parent SHA; it must not treat old 1.0.0 as a current replay success. Packaged compatibility registration and AUTO consumers remain MAIN-owned.

## Isolation

No production configs or originals modified. No external provider/model calls, paid tokens, or fees. Final acceptance explicitly uses a test-owned TEMP basetemp and mypy cache; the repository's short-basetemp relocation hook reports its relocated TEMP removed, and the wrapper confirms its own TEMP removed. `verification.json` records exact commands, UTC, exits, and log SHA. The old delivered branch/handoff remains unchanged. Changes are in the separate MAIN integration worktree only and are intentionally uncommitted for MAIN's combined commit.

## MAIN integration still required

- Wire `official_json` AUTO select/replay/summary/public CLI through projection identity; use each record's `parent_content_sha256`, not parent_source_refs[0].
- Register the current parser/projection/export compatibility policy without mutating old sealed manifests.
- Run the shared major contract node and subsequent real-company research reruns. This acceptance is source/engineering PASS, not revenue research PASS.


## Independent review follow-up: pagination and numeric identity (2026-10-10 20:00 UTC)

Two additional shared roots were reproduced and fixed before MAIN commit:

- Pagination metadata was checked against only page 1. All pages must now have exact integer page/count/size values, consistent pages/total/size, unique contiguous current-page numbers (input order can vary), an observed record count matching the total, and no missing/overlapping/conflicting record IDs before `pagination_complete=true`. Metadata drift retains both original pages and their full observed page metadata, marks partial coverage, and emits a fixed, bounded diagnostic list.
- Adjacent-page overlap is transparent: `total_records` counts all raw occurrences; `unique_record_ids`, `duplicate_record_occurrences`, `conflicting_record_ids`, and `missing_record_ids` are separate. An identical provider ID/body is selected only once. Conflicting bodies under one ID are both retained but neither is selected as an arbitrary version. This changes data selection/completeness, never original retention or permission.
- Provider issuer/record numeric IDs previously used `int(float)` and could turn `org_id=1.9` into issuer 1. Only lexical integers parsed as `type(value) is int` now prove numeric identity, preserving exact large integers such as `9007199254740993` and `2**100`. Bool, decimals, exponent forms, and huge floating numeric forms remain raw observations without identity promotion. Fractional/exponent pagination cannot prove full coverage.

Additional TDD evidence: `pagination-red.log` = **6 failed**; `numeric-red.log` = **7 failed, 6 passed** (the passes are existing bool/large-float rejection and valid integer controls). After repair, final responsibility suite = **152 passed in 16.30s**, three-module mypy and ruff pass. See `pagination-verification.json` for commands/UTC/log SHA. The owned wrapper TEMP and pytest's relocated short TEMP were both removed. Calls/tokens/fees remain zero; old unknowns and all originals remain unchanged.

Additional runtime file modified: `src/company_wiki/source_catalog/official_json_layout.py`. Current write set therefore has 3 runtime modules plus the dedicated acceptance test. No root PWF, automation, public gate, or old handoff was changed; all source is still uncommitted for MAIN's combined publication.
