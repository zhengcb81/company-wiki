# MAIN projection publication and terminal compaction handoff

## Scope and ownership

Implemented only four source files, one new integration test, and this evidence directory. `store.py` edits are limited to `_compact_terminal_narrative`, plus the parent-authorized private `_IdempotencyModel` protocol for the existing idempotency helper. No commits, no shared PWF changes, no production/source originals, no external/model/provider calls. The other adapter/catalog/replay/batch/transport files remain owned by their assigned agents.

## Frozen interfaces

- `NarrativeEffectDispatcher(automation, artifacts, *, allowed_job_ids=None, generation_manifests=None, projection_loader=None)`; loader is `Callable[[NarrativeSubject], VerifiedProjectionView]`.
- Projection generation manifests are keyed by `bundle.item_key`. Required manifest schema `narrative-generation/2` and full `subject_binding` must match the bundle. If provided, generation source metadata must match the actual bundle metadata. Semantic SHA is `canonical_json_hash(manifest)`; target is `publication_target(bundle.subject, generation_sha)`.
- `NarrativeBundleReader(artifacts, *, projection_loader=None).read_subject(*, subject, generation_sha256, artifact_version_id=None)` uses actual source artifact `visible_subject_generation_candidates` and `read_current_subject`, then strict canonical bundle and one fresh verified projection replay. `read()` raw behavior remains.
- `compact_terminal_narrative_jobs(..., projection_loader=None)` uses that exact subject reader before the short catalog lock, then rechecks visible artifact/current parents and runs the existing transactional AUTO compaction.
- `FinalArtifactPin` preserves the original seven positional fields and raw wire. Added optional `subject_binding: NarrativeSubject | None` and `generation_sha256: str | None`. A projected pin's original internal anchor fields must equal the actual first raw parent for existing foreign-key checks; they never serve as the subject identity.
- Projected public pin wire has exactly `effect_id`, `artifact_version_id`, `artifact_sha256`, `byte_size`, `subject_binding`, `generation_sha256`. Raw public pin has exactly the seven original fields.
- New terminal schema constant `PROJECTED_TERMINAL_RECEIPT_SCHEMA = narrative-terminal-receipt/2.0`. Original `TERMINAL_RECEIPT_SCHEMA = narrative-terminal-receipt/1.0` remains. `is_terminal_receipt` recognizes both.

## Publication, recovery, and performance

Projection draft metadata includes full subject binding, the generation manifest and SHA, schema, and summary status. Existing artifact `policy_sha256` stores the actual generation SHA for projections, without introducing permission semantics or a new table. Work-key/3 binds full subject, generation, producer, role, and effect; raw work keys remain.

Prepared objects are invisible. Preparing and activating retain the source artifact store's current-parent SQL validation. Outbox ACK is only the existing internal durable state transition and performs no source parsing. At actual activation inside `CatalogOperationLock`, the dispatcher obtains one fresh current source view and calls shared `replay_verified_projection(view, bundle)`. Reconciliation obtains one fresh view on each activation attempt and checks acknowledged result/bundle/generation/target, so it cannot turn a stale view into a visible artifact. No second replay algorithm, additional manual gate, or second task database was added.

Projection reuse and source-loader construction remain MAIN batch responsibilities. Public callers must provide the actual source-port loader. Without it, a prepared projection remains invisible/activation pending and can be recovered when correctly configured. This retains durable ACK state rather than redoing model work.

## Terminal compaction proof

The existing three-job DAG must already be fully terminal and acknowledged. The event must be strict event/3 with full matching subject binding and input hash. All three jobs share that same event subject/input/policy and use the projection item key; the final effect target binds full subject and generation. A compacted receipt never replaces a nonterminal or mismatching DAG. Metrics, edge/run/attempt/effect facts remain; repeated compaction is idempotent. Nested frozen receipt bodies are thawed through `result.to_dict()` before comparing full subject bindings.

## TDD evidence and regressions

- Real aligned RED: 14 FAIL / 1 PASS, confirming missing new APIs and preserving old raw pin wire before implementation. An earlier fixture-only RED is retained separately, clearly labeled; it lacked projection persistence and is not implementation evidence.
- First implementation attempt: 35 PASS / 1 FAIL. All 21 existing raw terminal receipt tests passed; the remaining owned test used an invalid fault injection (changed job subject without matching deterministic job key). The corrected fixture changes both and now tests compaction's own wrong-subject rejection.
- Final: **61 PASS**: 15 new real isolated import/publication/compaction tests, 30 store tests, 15 atomic store tests, and one legacy prepared-publication recovery test. Together with the prior 21 raw receipt tests, 82 distinct tests passed. Final command and timing are in `green-final.json`; no deselection.
- Ruff exact four sources + new test: **0**. Mypy exact four sources: **0**. Logs in `ruff-final.log`, `mypy-final.log`, `static-final.json`.
- Final owned TEMP and pytest's own relocated Windows TEMP were removed. Every original fixture byte hash was checked on context exit, and corruption tests restore bytes in `finally`. External calls: **0**.
- After shared contracts made the raw-policy property Optional for the projected variant, the raw draft now explicitly rejects `None` and uses a narrowed local SHA. No cast/default bypass. The final integrated run again passed **16/16** (15 new + legacy recovery), Ruff 0, mypy 0; see `integrated-final.json`.
- Static invocation's first automatic approval review timed out; the tool allowed one retry, which completed. No channel change or bypass was used.
- One known `asyncio_mode` warning is due to intentionally disabled plugin autoload, unrelated to execution behavior. No global pytest configuration was changed.

## New integration coverage

Tests use actual immutable official JSON source imports, actual two-parent projection persistence/export, real SQLite AUTO/catalog state, real artifact objects, and the shared replay function, with only model-free fixture summaries. They cover: raw/projected pin wire; source metadata and generation binding; missing/mismatching manifests with no object writes; two issuers sharing the same raw parents without identity/publication/compaction collision; ACK followed by interruption and fresh reconciliation; wrong current source view; invented field text rejection; non-anchor raw byte corruption; wrong subject/generation/job subject/nonterminal DAG refusal without result writes; and exact-generation reading.

## Parent integration work

1. Provide actual `projection_loader` when dispatching, reading, and compacting; bind actual item-key generation manifests from current profile/model/prompt/schema/source metadata.
2. Construct projected pins with the real internal anchor plus explicit full subject and generation. Expose only `pin.to_dict()` or the same six-field public wire.
3. Use `read_subject` rather than raw anchor reads for projected reuse; never use an anchor to substitute issuer/as-of/view identity.
4. Run MAIN's whole transport/batch suite after other agents' files settle; no private overrides or deselections required by this lane.

## Residual boundaries

Generation manifest construction/strict finite pathless option binding belongs to `narrative_generation`; this lane validates its subject/source metadata and exact canonical SHA at publication/read. Source-port current-byte/parser/layout/issuer/as-of proof belongs to the injected verified view and shared replay, not a duplicated publisher parser. Storage current-parent checks remain the source artifact layer's responsibility. No P7 projection leaf, RF, audit, raw originals, provider, or production configuration was modified.
