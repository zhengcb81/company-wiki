# W06 — source facts, request relevance and finite discovery

Status: read-only diagnosis completed; **implementation and acceptance are not yet run**.

## Proven conclusions

### RC28 is a composition defect, not a missing-title or FY26-publication defect

The isolated US catalog has five annual source versions, FY2021–FY2025. The requested source is FY2026/10-K/as-of 2026-10-08. `us_annual_candidate_replay.json` reopens actual registered originals and runs the current source-owned proof function without writing the catalog:

- FY2023/FY2024/FY2025 explicitly return no matching period.
- FY2021 and FY2022 contain unambiguous DEI CIK789019, FY2021/FY2022, FY and 10-K, but use the actual older transformation `ixt:datemonthdayyearen` for `DocumentPeriodEndDate`. `_inline_date` does not support that transformation and aborts full primary extraction before request relevance can be decided.
- `local_reconcile._prepare_local_source` catches every candidate proof failure, sets `targeted=True`, then returns `local_metadata_gap` with `blocks_download=True`. The two obsolete annuals incorrectly veto discovery of the requested absent annual.
- `_discover_source_groups` has a second independent composition defect: the raw-candidate limit, default 16, is also used to count **all** company filing directories before narrowing them. The real MSFT portfolio contains 26 filing directories, including unrelated 8-K/proxy/quarterly groups; this creates `local_source_group_limit` even when the original five annual candidates have been properly excluded.

`annual_gap_replay.json` uses three exclusive TEMP catalog copies and the real protected originals. Actual current product returns the precise two old-source diagnostics. A diagnostic process-only legacy transformation alias moves the failure to the real 26-versus-16 enumeration limit. A second diagnostic run with 64 metadata-group headroom reaches `no_matching_local_period`, `blocks_download=False`. These experiments isolate causal stages; they are **not implemented GREEN fixes**, and the production limits were not changed. All network/download/model counts are zero. Original/catalog/config SHA, size and mtime are unchanged, and all three TEMP roots are absent after cleanup.

The scope of the physical absence observation is explicit: five registered annual versions plus the current issuer-specific Dayu filing directory and observed company annual directory. It is not proof that no other unindexed file exists anywhere under arbitrary Dropbox folders. A production fix must complete bounded storage-owned discovery before a genuine fetch. This investigation does not claim that the later configured provider can currently retrieve FY2026.

### RC11 is a true omission in the source-fact contract

`sec_title_observations.json` contains actual public reads of all three current FY26 10-Q SourceRefs. Each is byte-valid and correctly identified by DEI, yet the public manifest title is null. Their actual HTML `<title>` is **`10-Q`**; the database display titles are filename stems (`msft-20250930`, etc.).

The existing facts service rejects a title correction because `SOURCE_FACT_FIELDS` omits title. It also omits `form_type`, although the assertion table/builder and reader already have a form column. The public reader intentionally projects only explicit `source_title`, which is correct: a filename stem must not become an authoritative report title. The source-owned correction and projection vocabulary is incomplete, and RF's nonempty-title check exposed it. Do not relax the RF consumer or synthesize `MSFT FY2026 Q1 report` from the request.

### RC10 remains a real primary-publication evidence gap

`publication_original_observations.json` establishes current exact hashes and physical data, without attributing a guessed public date:

- CN FY24 raw SHA3273711f… is intact. PDF metadata names the real report and has creation/modification on 2025-04-17; these are document-production timestamps, not exchange publication proof. The sealed preparation explicitly records a legacy April17 versus secondary April18 lead and no verified primary publication event.
- Tencent H1 raw SHA4170f80e… is intact, 122 pages. PDF creation is August22 and modification August24, whereas the separately published H1 results communication is dated August12. These are distinct documents; the August12 event must not be assigned to this later PDF without a primary listing/receipt tied to its bytes.
- Tencent overview raw SHAa9b0a5d6… says `Sep 2026` on page1. A month, PDF-production time and URL month do not supply an exact public day. Current source-fact patches explicitly preserve publication and filing date null.

The byte reader is functioning. Historical as-of qualification correctly distinguishes known eligible dates from unknown publication. This is source accuracy, not a private/public or per-document approval gate. Current sources may be read and summarized with explicit unknown-date provenance, but must not be silently promoted into a historical forecast at 2026-10-08.

## Exclusive implementation write set

| File | Responsibility |
|---|---|
| `src/company_wiki/source_catalog/assertion_service.py` | Add truthful title and form_type corrections to the existing evidence-bound append-only facts service; preserve idempotence, supersession, atomic projection and rescan replay. Store title in the existing source_fact_patch/evidence JSON; do not add a second registry or require a schema migration merely for title. |
| `src/company_wiki/source_catalog/resolver.py` | Map the title fact to the existing internal `source_title` projection, preserving explicit unknown and correction priority over legacy capture; public manifest shape stays unchanged. |
| `src/company_wiki/source_catalog/dayu_fiscal_metadata.py` | Separate unambiguous DEI request-scope observations (CIK/year/period/form) from period-end/date normalization; add the actually observed older named transformation conservatively. One parsed observation model should serve both scope and complete facts. |
| `src/company_wiki/source_catalog/local_reconcile.py` | Establish relevance before unrelated full-proof errors become blockers; derive a genuine original title/form from source bytes; finite issuer/group discovery and relevant candidate classification. No download/adaptor/consumer-specific title workaround. |
| `src/company_wiki/source_catalog/local_inventory.py` | Separate metadata/directory enumeration ceilings from verified-original candidate count while sharing the existing total byte/time budget. Default original candidate cap16 and current raw byte cap stay bounded. |
| `src/company_wiki/source_catalog/source_group_scope.py` and/or `registration_scope.py` | Only if required: centralize finite storage-owned issuer prefix/group enumeration so directory layout knowledge stays below SourceRef consumers. Reuse the existing registration orchestration; no provider code moves into RF/FF. |
| Related `tests/contract/`, `tests/integration/test_legacy_local_reconcile.py`, fiscal metadata unit tests | TDD cases listed below; isolated fixtures only. |

No changes are required in `official_source_flow.py`, narrative parsers, W05 files, FF, ET, RF, Dayu, production config, raw originals, shared CI/pre-push lists or the frozen root matrix. MAIN owns shared gate membership and integration. If investigation during implementation proves another file necessary, communicate its concrete dependency before writing it.

## Required implementation order

1. Write title/form correction tests and candidate relevance/discovery RED cases first. Keep exact failure output in the lane's own PWF. No need to run the full project suite for every edit.
2. Extend the existing facts vocabulary and visible projection. Map public fact `title` to internal `source_title`; ignore it when passing SQL-column kwargs into `_build_assertion`, because title already resides in the existing JSON patch. `form_type` uses the existing column. `documents.title` is a lexical/display column with a NOT NULL constraint: a proven nonnull title may update it; an explicit unknown title must clear the authoritative patch without writing SQL NULL into that display column. Include title in `apply_source_fact_projection` rescan replay. Preserve existing generic matching field evidence and real SHA check; a source-generated title must retain the actual locator/value/SHA evidence.
3. Extract source title from the actual HTML head `<title>` (the three real reports say `10-Q`) or a supported exact cover-title locator. Require nonempty trimmed bounded source text. Reject conflicting/unreadable evidence honestly. Do not generate a ticker/year label, borrow a title from another version, or copy the request's document kind into a missing report title. Add form_type using `dei:DocumentType`, not a request form guess.
4. Refactor SEC primary observations into independently validated scope and complete facts. Unambiguous CIK/year/period/form can show a document is out of scope even if its irrelevant period-end transform is unsupported. Full import/repair still requires the proper period-end/publication evidence. Add the observed `datemonthdayyearen` transformation as an explicit alias of its correct English month/day/year ordering. Retain unknown-transform refusal, date validity, conflicts and report-period-form coherence.
5. Make candidate outcomes explicit and safe: **proven_out_of_scope**, **potential_target_with_gap**, **proven_target**, **resource/unavailable**. An out-of-scope decision must come from actual verified source bytes or an already validated source-owned exact-version fact; do not use raw filename, request year, stale provider fiscal_year or a conflicted declaration to skip a candidate. The old actual Q2 provider cache incorrectly says FY2025 while DEI says FY2026, so cache-year prefiltering would recreate the original problem.
6. Only a proven out-of-scope candidate may avoid blocking discovery. A same-issuer/same-period version with bad SHA, unreadable body, ambiguous identity, missing publication proof, genuine withdrawal, changed current root, or conflicting primary facts still blocks reuse and automatic replacement. Its diagnosis cannot be converted to not_found. Unknown relevance must remain an honest gap; the absence of a successful query is not byte absence.
7. Run finite discovery before declaring true absence. Enumerating bounded metadata entries is a distinct operation from opening at most16 original candidates. Use explicit separate ceilings (proposed metadata groups256 and directory entries4096, both under the same total deadline/byte budget; verify these fit existing limits before choosing final defaults). Exceeding any limit yields a named unavailable result and `blocks_download=True`, never a claim of absence. If discovery yields a matching existing SHA, return through the unchanged public reader; no provider call. If it yields no target and no unresolved potentially relevant version, configured acquisition can proceed once under the original intent and budget.
8. Grouped focused GREEN + actual original replay + independent review at M2. Commit via ordinary hooks; MAIN integrates/publishes and exact remote CI, then M3 retries the real configured annual request and the three current 10-Q preparation flows. M3 failures retain measured/unknown usage; no broad retry or false source availability claim.

## Bounded storage discovery design

Directory details belong to the storage layer. Use current configured roots, identity aliases and known source-to-location anchors to form a finite list of issuer prefixes; root kind is configuration, not a hardcoded project path. Existing `SourceRegistrationScope` validates relative paths and groups and `register_catalog_sources` routes through the one scanner transaction.

- Dayu: enumerate only `ticker/filings/` and bounded meta.json groups. Never modify Dayu code or its cache. Cached primary filename is only an enumeration hint; current byte SHA and DEI decide identity/period.
- Company roots: include root-level files as specified by current AGENTS and optional legacy `raw/` subdirectories. The existing implementation only enumerates `company/raw/`, so an unindexed original directly under `companies/{company}/` is currently missed. Suffix coverage must use the configured/shared document format vocabulary; do not create an independent hardcoded PDF/TXT-only list that misses W05 DOCX.
- Generic directory/Dropbox: derive finite prefixes from existing matched document-location anchors and configured/verified issuer aliases. Do not recursively search the entire Dropbox root. If no finite issuer mapping exists, leave that discovery scope explicitly unknown or require an explicit storage registration scope; never claim universal absence. This is a data-location hint, not an authorization file.
- Exclude placeholders before opening, do not follow a reparse/symlink escape, and charge metadata reads, registration and original verification to one deadline/byte budget. Stable ordering makes the finite coverage receipt reproducible.
- Record counts, covered root IDs and source-group/period exclusion reasons without physical paths in consumer DTOs. Keep technical paths only in local engineering receipts. No new database, daemon, scan canary or review license.

## Planned TDD package and expected assertions

These tests are **planned**, not reported passing.

### Title/form facts (`tests/contract/test_title_source_fact.py`)

1. Intact SEC HTML with title-null source facts and actual `<title>10-Q</title>`: source-owned correction makes public title `10-Q`, preserves raw bytes/provenance/old assertions and gets a new metadata version. No ticker/year construction.
2. Title-only and form_type-only corrections through the common facts API; repeat with a new observed_at is unchanged; a genuine changed value appends a superseding assertion. Rescan/registration replays the same authoritative title without restoring a filename guess.
3. Empty/trimmed-invalid/overlong title, absent locator, evidence value mismatch, wrong supplied SHA and ambiguous source title are named failures with no partial write. Explicit null remains unknown and does not violate documents.title NOT NULL.
4. Old assertions without title remain readable; current source reader keys/schema are unchanged. Existing recorded title still works; body title does not imply publication or fiscal period.
5. An old SourceRef still reads the same raw after title correction; the exact read metadata fingerprint responds as designed. Changing metadata does not assign a new source byte ID or rewrite a sealed RF attempt.

### Relevance and true absence (`tests/contract/test_local_request_relevance.py`)

6. Requested FY2026 annual, only old FY2021/FY2022 originals with unambiguous old-year DEI and unsupported period-end transformation: no requested local source, no metadata veto from those obsolete versions, no raw rewrite, provider path remains possible only with explicit fetch intent.
7. Same issuer **same FY2026** with unsupported/ambiguous end date, absent publication or contradictory form: named gap, blocks_download=True, no provider HTTP. This prevents exclusion logic from hiding a genuinely damaged target.
8. Same-period original bytes change but catalog SHA does not: no reuse/no refetch, no false absence. Wrong or conflicted current issuer/period facts cannot be silently converted to a foreign historical exclusion.
9. Mixed old unrelated failure + intact actual target: target is returned via current public SourceRef/open; measured download count0. Two distinct target originals remain ambiguous under existing rules.
10. Known wrong provider cache FY2025 with actual target FY2026 DEI: repair and reuse actual source, never pre-exclude by that cache/filename.
11. Unknown/missing/duplicate DEI scope: potential target gap. True absence is reported only after finite discovery returns no matching candidate and no unresolved potentially relevant one.
12. Legacy transform names normalize actual 2021/2022 report ends; unsupported transform, impossible date, contradictory dates, 10-Q/FY mismatch and issuer conflicts retain failures. An uninvolved issuer/year fixture must also pass.

### Finite discovery (`tests/contract/test_local_discovery_limits.py`)

13. At least26 unrelated issuer filing directories + at most16 candidate originals: metadata enumeration does not consume the original candidate count. A truly absent exact annual returns no_matching_local_period; configured adapter discovery happens once, no repeated full-PDF download.
14. Existing target original in an initially unregistered matching group: finite registration yields same SHA and public verified read, provider HTTP0. Test company-root direct file and legacy raw/, and a generic directory source prefix with a verified alias.
15. More than configured metadata group/entry/original candidates, deadline, bytes, placeholder and escape each stop by typed bounded outcome; they do not become not_found or permit a second fetch. No global full-root traversal.
16. Unknown generic-root issuer mapping is represented as incomplete discovery, not falsely complete. Keep source/consumer DTOs pathless and current schema-compatible.

### Major integration and protected-state receipts

17. Real current original copy/replay: all three 10-Q actual HTML head titles and existing SourceRefs remain byte-identical; the real old annual scope/date transforms cannot veto FY26, and real26-group enumeration is covered under finite metadata limits. Original mFresh/production raw, production config and source catalog hashes/mtime unchanged; each owned TEMP restored.
18. SourceCatalog/acquisition→FF→RF local preparation contract: title correction is visible at the RF boundary; metadata repair never fetches a duplicate; a true absent annual permits exactly one bounded acquisition; a genuine target metadata/SHA gap still yields a safe cause with zero provider start. MAIN coordinates FF/RF changes only if an actual unchanged public contract failure is demonstrated.

Use existing integration/contract suites for adjacent source-facts, active/retired restoration, byte verification, scoped read policy and single-intent acquisition. Run a focused group once after implementation and an independent major review; do not add per-function human signatures or full-suite runs to each commit.

## Publication evidence follow-up at M3

CN FY24 and HK H1/overview require a bounded primary listing/issuer/exchange event retrieval, preferably metadata-only, before correction. A valid correction binds exact source SHA, real publication event URL/identifier, exact quoted field locator/value, observation time and any acquired metadata-original hash. If bytes cannot be tied to that exact event, keep publication null and explain the historical scope gap. A timestamp proving availability **today** cannot prove availability at 2026-10-08; do not reuse a later current event as a historical day.

Once valid evidence is obtained, append through the same source facts API and retry normal historical selection. Do not download the intact financial PDF again merely to repair metadata. Do not overwrite frozen source ledgers/reports; corrected attempts use new receipts and additive supersession links.

## Output interface to MAIN

`annual_gap_replay.json`, `us_annual_candidate_replay.json`, `legacy_annual_inline_dei.json`, `sec_title_observations.json`, `publication_original_observations.json`, this handoff and lane PWF are the retained diagnosis. MAIN can assign this write set to the now-clean reusable W06 worktree, coordinate shared CI membership and preserve W05 parser ownership. Current engineering diagnosis is complete; source/research M3 acceptance is not.
