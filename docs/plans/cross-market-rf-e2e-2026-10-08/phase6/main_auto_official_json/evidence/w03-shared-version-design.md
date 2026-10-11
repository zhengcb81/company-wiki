# W03 shared selector version wiring — MAIN readonly design

2026-10-11. Scope: isolated CWP MAIN; read only, no tests/model/provider/download. This continues W03_CONTINUATION.md and does not change W03/W04 delivery reports or root PWF.

## 1. Actual current chain and precise gaps

| Layer / exact source location at this read | Actual behavior | Minimal responsibility correction |
|---|---|---|
| `source_catalog/narrative_evidence.py:77–90,1589–1701` | Supported0.6.0/0.7.0 pure dispatch exists; default0.6.0. Package has no selector-version field. | Keep real policy dispatch. After shared wiring GREEN, switch default once to0.7.0. Pure owner must ensure every subsidiary rule uses effective_version. |
| `automation/narrative_batch_request.py:317–345` | New request execution_versions and input identity already include selector global. request_sha256 is version-independent intent. | Existing field is enough; do not add request schema, permission file, second policy hash or new generation schema. New request freezes0.7.0 after default switch. |
| `automation/narrative_batch.py:255–309,316–361,739–775` | `_execution_versions` adds handler versions; `_frozen_binding` stores exact versions. Generation1 raw and generation2 official already receive those versions; frozen settings reconstruct per-item manifests. | Reuse this authority. Frozen `execution_versions.selector` is worker policy, not a fresh import-global. Do not regenerate frozen manifests on resume. |
| `automation/narrative_worker_factory.py:90–118,152–175` | Reads frozen binding/generation SHA, checks projected prompt/adapter, but does not pass selector version into handlers. | Decode existing frozen snapshot once and carry selector to runtime composition together with generation values. Validate policy capability with existing resolver, not new signing. Preserve no-binding compatibility only for genuinely new direct-runtime use; a declared malformed/unknown frozen version must not fall back to current. |
| `automation/narrative_runtime.py:33–41,50–62` | No selector-policy dependency; select and verify use their own globals. | Add one optional pinned selector version/declaration to the dependency object and pass the same resolved policy to select and verify. |
| `automation/narrative_select.py:216,320–322,360,506–515,564–566` | Pure calls omit selector_version; raw/official result metadata stamps global. | One central binding/invocation adapter for raw PDF/TXT/normalized and official projection. Built-in call executes the effective version; both result forms stamp that same effective version. Do not put version into EvidenceSpan locator/source identity. |
| `automation/narrative_official_json.py:232–257` | Selector protocol has only title/existing_kind; native fields call same callable, no version. Empty fast path avoids selector entirely. | Accept the centrally bound callable/policy. Nonempty fields execute that policy, empty package still reports runtime's pinned version. Resolve unknown policy before empty bypass. Preserve whole-field JSON locators, source role, native whitespace, actual parent and partial coverage. |
| `automation/narrative_verify.py:142–176,389–402` | Dependency validator compares selector to installed global; bundle correctly copies selected.selector. | Compare select result against runtime's frozen expected version, after supported-policy dispatch. Keep bundle copying selected version. Do not retag0.6 to0.7 or add repeated source identity checks. |
| `source_catalog/narrative_retrieval.py:496–525,618–623` | Resolver accepts only current-global replay contract, then reruns pure selection without its recorded version. | Resolve the contract's actual selector_version against supported executable policies, pass it explicitly to select_narrative_evidence. Wrap unknown in existing NarrativeEvidenceResolveError. Keep recorded parser contract, max_selected/title/kind and full ordered group/ID/locator/text checks. |
| `automation/narrative_replay.py:143–174,201–247` | Source-byte/locator replay, not selector-policy rerun. Official compares source identities ignoring only selection annotations. | Usually **no runtime change** needed. Do not add policy-known/current-global gates to a byte-only reader: it does not execute the algorithm and existing old artifacts may legitimately retain older descriptive selector tags. Actual policy reselection belongs to resolver, executable version rejection to runtime. |
| `automation/narrative_generation.py:28–92,223–319,337–432` | Manifest already includes supplied selector; exact generation candidates/pins and bundle selector equality exist. | Usually **no change** needed: wiring actual policy to these supplied versions makes new0.7 SHA distinct without new hash layer. Old generation/pins remain exact. |

Source-owned parser version is separate from selector version. W03 does not change transcript0.3.1/0.3.0, PDF, normalization or official JSON parser/layout/producer identities.

## 2. Frozen resume semantics already available — preserve them

`narrative_batch.py:_resume_binding` uses frozen versions at512 and recomputes the same manifest with them at668–679. Binding4 `_resume_item_binding` uses frozen versions809/895–905. Both preserve saved parser_component, bundle_producer and material_extractor interpretations, with the existing completed-history omitted-reasoning-effort compatibility kept narrow.

`_run_prepared:1412–1452` performs finished/idle history reads before the version mismatch execution rejection at1453–1454. Keep that ordering: a finished0.6 run may read its frozen pin under installed0.7 without workers or model calls; an unfinished run must not silently reinterpret remaining jobs as0.7. Keep the existing `BATCH_EXECUTION_VERSION_UNAVAILABLE_NEW_RUN_REQUIRED` behavior unless a deliberate old-runtime execution path is separately designed. No new approval is involved.

`_run_owned:1275–1293` currently computes current manifests for coordination locks even before resuming frozen history. This does not mean the frozen generation is replaced. Tests should distinguish harmless coordination lock observations from authoritative DB/jobs/attempts/outbox/artifact/generation/usage mutations; do not claim whole-filesystem zero writes. Optional cleanup can choose frozen generation lock digests after normal validation, but it is not needed to add another gate or broaden W03.

For unknown execution-policy versions use the existing typed component/dispatch errors at coordinator/factory, before scheduling/model construction. Do not rely on nonempty strings alone and do not label the error a budget/permission issue. Known0.6 remains executable for deterministic resolver replay. Old byte-only artifact reads retain their existing contract.

## 3. Custom selector contract — no fake global tag, no catch-TypeError retry

Today `NarrativeSelector` (select85–92) and `ProjectionSelector` (official48–50) accept only parsed/title/existing_kind; tests and integrations can inject such callables. Changing every invocation to pass a new keyword and then retrying on TypeError is unsafe: an internal custom-selector TypeError could cause a second execution and conceal a real fault.

Use one explicit bound policy adapter owned by composition/select, rather than parallel raw/official wrappers:

- Built-in selector: resolve its effective version once and bind `select_narrative_evidence(..., selector_version=effective)`; expose the effective version to result metadata and verify.
- Existing custom injection: preserve its old three-keyword call shape only through an explicitly declared fixed-policy compatibility adapter. Do not infer0.6 merely because a callable lacks the new keyword: a wrapper may itself delegate to the changed global default. Its implementation/caller must pin the real legacy0.6 call (or explicitly declare its actual current policy). If caller also requests a conflicting frozen0.7 policy, reject a typed contract mismatch rather than stamp0.7 without that declaration.
- New/custom version-aware policy: require an explicit adapter/version declaration at injection; it executes the declared version and metadata uses that declaration. The caller/implementation owns its algorithm contract, not inferred from callable name or output text. A recording callable should prove that the declared0.7 was actually supplied/executed. No signature guessing or broad TypeError fallback.
- Direct default built-in construction uses current default; production batch factory always supplies frozen version. One adapter can be handed to official JSON without official re-resolving globals.

This is programming interface/version capability, not material authorization or a new identity verification. No new persisted selector registry/DB/table/schema is required. An effective-version field on NarrativeEvidencePackage is unnecessary unless it simplifies the chosen adapter; if added as non-wire metadata it must not alter old summary_input/span fingerprint.

## 4. Pure-layer default leak requiring owner fix

At `narrative_evidence.py:1679`, fundraising-project dropped_financial adjustment still calls `_candidate_rules()` without effective_version. Once global default flips0.7, explicit0.6 would consult new business rules at this substep. This can break complete legacy result metadata even if selected text appears unchanged. ROOT has already notified the pure W03 owner; do not duplicate source edits/tests here. The repair should pass effective_version, and the owner should prove explicit0.6 under installed/default0.7 keeps full ordered legacy fingerprint, including source/package counts, reasons/group IDs and locators; not merely tag or span count.

## 5. Eight TDD anchors, grouped into the shared big node

1. **Pure historical dispatch**: installed/default0.7 with explicit0.6 reproduces frozen full real TXT ordered fingerprint and fundraising fixture metadata; explicit0.7 has actual new policy results, source bytes/parser unchanged. Pure owner owns this test.
2. **Raw public AUTO new generation**: new raw TXT/PDF/normalized run freezes0.7, select/bundle report0.7, manifest SHA differs from otherwise identical0.6; an old0.6 artifact is not reused as new0.7. Real source/read locator chain and existing budgets stay intact.
3. **Mixed raw+official AUTO**: same frozen selector feeds both subjects; actual native JSON field locators/roles/parents survive; complete empty and partial empty behaviors remain correct. No copied records, fabricated anchor or mixed-role question support.
4. **Worker snapshot/current drift**: construct runtime with known frozen0.6 while installed default0.7; recording selector sees0.6 and both raw/official metadata say0.6, verify checks frozen0.6. Unfinished historical batch still takes existing typed new-run-required path, no silent mixed execution/model call.
5. **Finished history resume**: binding3 raw and binding4 mixed finished0.6 run under default0.7 returns existing pins and frozen manifest/old receipt interpretation, zero model POST/new attempts/usage, no DB/artifact/outbox rewrites. Test source and generation hashes unchanged; permit only existing coordination lock side effects.
6. **Unknown policy**: pure/runtime/frozen-policy resolver/record-reselection reject unsupported version with typed version/input errors before model/worker/publication; complete-empty official cannot bypass this. Do not reject old byte-only readable artifacts merely for descriptive legacy tags.
7. **Custom injection**: legacy custom receives original call shape and declares0.6; declared version-aware0.7 receives the correct policy; raw and official metadata agree. An intentional internal TypeError is surfaced once, never triggers fallback retry. Explicit incompatible version declaration yields typed contract error rather than forged tag.
8. **Resolver real old/new contract**: stored0.6 selection bundle under default0.7 reruns actual0.6, preserving complete ordered EvidenceSpan/group/reason/locator fingerprint;0.7 contract reruns0.7; unsupported policy errors. Parser/material/source-byte contracts are not loosened.

Use focused responsibility tests and one shared public raw/official AUTO/read/reuse/resume E2E node after wiring. Do not repeat broad tests at every helper or call paid models solely to test plumbing.

## 6. Minimal write set for ROOT

Required shared source: `automation/narrative_worker_factory.py`, `narrative_runtime.py`, `narrative_select.py`, `narrative_official_json.py`, `narrative_verify.py`, `source_catalog/narrative_retrieval.py`; optionally one small centralized selector-binding helper if needed. `automation/narrative_batch.py` only for typed frozen-policy capability validation / narrow existing resume integration; request/generation code already carries selector identity and ordinarily needs no new algorithm/schema. Pure owner handles `narrative_evidence.py` effective subrules; ROOT switches its default after shared GREEN.

No automatic changes to narrative_replay, budgets/store/leases/outbox, parser leaves, LLM prompt/request schema, source catalog production config, original documents, RF/AUDIT, or original reports are justified by this wiring. Tests should go in existing shared select/verify/runtime/batch/retrieval responsibility files or one focused integration file; keep W03/W04 responsibility separation.

## 7. This investigation's limits

CodeGraph canonical context was consulted first; its indexed line positions are older than this isolated worktree, so the specified current files and their known coordinator dependencies were read directly. Findings are source review and test design, not executed test results. No source, test, config, original, DB, PWF or prior evidence was changed; only this unique design file is written. Provider/model/download/test calls0, cost0.
