# W21 ROOT independent reception review

Status: COMPLETE — ENGINEERING_ACCEPTABLE / CANONICAL_C2_OPEN. ROOT independent reception review, 2026-10-30. No source files were modified by this reviewer.

## Scope and plan

1. Freeze author delivery and read card/handoff/reviews.
2. Inspect production diff, tests, probes, ROOT compatibility and path-length counterexample.
3. Write engineering acceptance scope, remaining C2 work and bounded integration checks.

## Evidence and progress

- Author target: `f6c2b9d420f4b78a4fb825eb2f77bc1c912c9e9d`; base: `bb5d09c056ca36bba8061d761b5469d87aa6e5e0`.
- Normal sandbox Git read of author checkout returned Permission denied. Approved read-only host Git reads succeeded; no author checkout/index write, SDK execution, downloads or keys.
- Card and supplied handoff distinguish canonical C2 `native_fallback` from ASCII alias diagnostic `unaligned_native_fallback`; no accepted aligned groups were demonstrated.
- Production diff is confined to narrative_pdf_enhancement.py: isolated Python launch flags, allowlisted child environment, repo-local bytecode and temporary roots.

## Frozen evidence

- Author HEAD `f6c2b9d420f4b78a4fb825eb2f77bc1c912c9e9d`, tree `7dc3106ffa2cc12ba402284158ae94f2ad902ff5`; author worktree independently read as clean.
- Author final review targets `eab239d93560efe6f1eb974b547be0bd9e93b3e7`. `eab239d9..f6c2b9d4` changes only handoff/final review/PWF/path-length receipt, with no production/test/probe source change. Full allowlist and SHA-256 are in review.json.
- ROOT before integration observed at `97e8a290fcfaea4335aad3e5e058f2b8850d287b`. The production owner is unchanged from W21 base at that ROOT commit; therefore this patch does not overwrite ROOT's newer native parser 0.1.2/QA cell-range work.
- Frozen production SHA-256, LF-normalized (also equals the Git blob bytes SHA-256): `d697d4e34b2579c5be10651b7c3eb79807c46250ac07fc5dac88bc94b007064b`.
- ROOT runtime profile independently hashed as `bcc427114955f6d045c5848b1885b24f1ec1666d1397bfb60ba4f404a225ff2a`, matching delivery. No SDK launch, model download, key read, original-company document read, author checkout/index mutation or global write occurred in this review.

## Engineering acceptance scope

No blocking defect found in the bounded engineering diff. Accept the following six engineering files at the frozen target, plus the documentary allowlist in review.json:

1. `src/company_wiki/source_catalog/narrative_pdf_enhancement.py`
2. `tests/unit/test_w21_pdf_runtime_launch.py`
3. `tests/unit/test_w21_pdf_runtime_probe_guard.py`
4. `tools/pdf_runtime_probe/cold_runtime_probe.py`
5. `tools/pdf_runtime_probe/run_cold_probe.py`
6. `tools/pdf_runtime_probe/synthetic_e2e.py`

The production change adds isolated interpreter flags (`-I -X utf8`), a bounded child environment allowlist, explicit first-party worker binding, and repo-local bytecode/scratch placement. Parent environment mutation is absent. Existing resource ceilings, one-deadline bounded runner, page checkpoint decoder, source SHA binding, native fallback, alignment and public PdfReading schema remain intact. The guard and revision-attempt marker live only in diagnostic tools; they are not new production approval gates.

The existing recipe's `orchestration_sha256` already binds this file, so the launch change produces a new recipe without changing the schema or borrowing old execution identity. Current runs/recovery must use the new exact recipe; historical publications retain their frozen recipe and native replay behavior. W21 changes no cache store, publication writer, native parser/version, source reader/proof, EvidenceSpan locator/role or QA range implementation. ROOT's parser 0.1.2 stays authoritative. No old recipe should be rewritten to force a cache hit.

All 42 changed files total 942,380 Git blob bytes; the largest is 183,020 bytes. There is no env/model/PDF/image/database/per-file SDK inventory in this delivery. Rev2/rev3 receipts duplicate verbose event evidence but are bounded historical diagnostic material (~642 KiB across four JSON/JSONL blobs), not a large runtime payload. The ~160 MiB bytecode cache is untracked runtime overhead described in the handoff, not committed content.

## Actual completion limits

Canonical C2 remains OPEN, despite the author's final review saying 0 engineering blockers. Direct receipt parsing confirms:

| Observation | Actual outcome | Acceptance meaning |
|---|---|---|
| rev5 no-document SDK startup | completed, 16.222824s / 30s, 0 guard rejections | import/constructor and launch path observed; no PDF conversion proof |
| canonical configured Chinese-path env | `native_fallback`, `ChildFailed` at PAGE_1, completed pages [], accepted groups 0 | real entry preserves source text and fails honestly; canonical SDK conversion unavailable |
| same env through temporary ASCII alias | `unaligned_native_fallback`, completed [1,2], stream complete, rejected groups 2, accepted 0, 3,250,298,880 B peak / 4 GiB | bounded diagnostic conversion proof only; no aligned enhancement or business recall acceptance |

Both E2Es selected 0 evidence spans and replayed 0. Those receipts do not independently prove nontrivial replay/source-proof/cache behavior. Existing mock-runner integration covers the interface, and ROOT's separate source/cache acceptance remains separate evidence.

The retained stderr and fopen comparison support the docling-parse 6.2.0 non-ASCII resource-path failure under ACP 936; this reviewer inspected that evidence but did not rerun the SDK or fopen experiment. The environment-path remedy is still an unsolved deployment/interface task, outside this production-file-only patch. A permanent supported path/configuration and a fresh bounded canonical run are needed before claiming C2 success. An ASCII junction diagnostic is not a deployment change or canonical acceptance. Alignment quality and real-summary body-quality OPEN items are not signed by this review. No new human approval step is introduced.

Repo-local scratch assumes the integrity-limited child can write that deployment tree. `mkdir` success is not a universal MIC/writability proof, and an unwritable tree can still yield native fallback. The fallback `-B` slow path and first-run compile cost remain explicit deployment limitations; resource bounds must not be raised to make a receipt green.

## Push-gate path-length counterexample

The counterexample is technically credible and independently reproduced with a small ROOT-owned NamedTemporaryFile probe using the same 82-character staging basename: LongPathsEnabled=0; 254 characters created successfully; 270 characters raised FileNotFoundError/errno 2. Owned scratch was deleted. No SDK or production original was involved.

Read-only code inspection confirms `_run_pytest_gate` roots TEMP/TMP/basetemp below `PROJECT_ROOT/cwpp-*`, while `atomic_output` stages using the destination basename plus random suffix. The longer worktree therefore exposes an infrastructure path-budget limitation. This is primarily a test/gate portability trigger, plus a genuine shared atomic-write limitation for similarly deep real storage roots. It is not evidence of a PDF runtime regression or a broken source-proof semantic assertion; the test fails during projection fixture persistence before that assertion.

The receipt's stronger label “persist_projection product defect” is not uniquely established: the shared writer and gate layout are both contributing owners, and no supported production-root contract is shown to be violated. Prefer a separate bounded gate/atomic-path fix that preserves the semantic test. Adding a named refusal to persist_projection alone would not make the contract smoke pass or establish support for long paths. Do not disable the pre-push gate, alter global ACL/MIC or machine-wide long-path settings as part of W21 reception.

## Validation and remaining bounded checks

ROOT integrated this exact frozen patch without conflicts and provided review-local receipts. This reviewer read those receipts (did not rerun them): 8 modules, **198 passed in 18.69s**; mypy **397 source files clean**. The modules are W21 launch/guard, paragraph runtime/environment/page checkpoints, QA cell-range locators, native ranges, and PDF production. ROOT separately reported ruff PASS. This already covers the narrow merge's critical boundary and the new parser 0.1.2, so repeating it adds no current evidence.

If extending acceptance beyond engineering integration, use only the next relevant bounded module: `test_pdf_paragraph_reading_integration.py` (source-exact membership and replay without model restart); an existing reading-recipe/cache recovery focused module if that boundary changes; and a fresh two-page synthetic canonical E2E only after the supported deployment-path remedy, with current recipe/parser/version and an owned new receipt directory. Do not run the historical probe defaults against their already-recorded rev5 or overwrite receipts; do not launch a large SDK/whole-company batch for merge acceptance.

Nonblocking handoff metadata debt: final JSON still has `reviewed_commits.final_review_target=null` and a stale “fields pending final review” generator string. The exact final-review target and documentation-only suffix are independently frozen above, so these do not block engineering reception. Preserve `pushed_to_remote=false`/push-blocked provenance until the actual publishing state changes.

## Conclusion

Engineering patch is acceptable to merge with current ROOT. W21 as a complete canonical SDK C2 acceptance is PARTIAL/OPEN. ROOT's native MiMo summary/cache/source proofs and its separate 4 body-quality OPEN items retain their own scope; none are upgraded by these W21 receipts.
