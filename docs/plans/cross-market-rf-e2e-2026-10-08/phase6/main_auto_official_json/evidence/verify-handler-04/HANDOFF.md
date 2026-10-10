# MAIN official JSON verify/runtime/factory — TDD handoff

## Owned changes (no commit)

Worktree: `C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki`.

| File | SHA256 |
| --- | --- |
| src/company_wiki/automation/narrative_verify.py | 28c3ffdd41ccc9da8dd924e7a7ea550ba38b23b844ad020d7a92749f538a0f99 |
| src/company_wiki/automation/narrative_runtime.py | 4fde54ea255ccf9dbe37fae6d90c4e850cd76ecbda8d7cffd9da784ed7286eb1 |
| src/company_wiki/automation/narrative_worker_factory.py | acd65734952912eeae2280a4b7f6f505b90a3a004bc49165934c091899f21c32 |
| tests/integration/test_official_json_verify_handler.py | f34f35bea1ab81070cdadbd612676d782c6bd225040e5c01b02e2c0de2920901 |

Only these owned files and this evidence directory were changed in this node. Source parser/layout/projection leaves, root PWF, contracts, batch and transport remain owned by their other agents. ROOT stages integration.

## Frozen actual APIs

`NarrativeVerifyHandler(*, reader, pdf_replayer=None, normalization=None, projection_catalog: Any | None = None, generation_sha256: Callable[[NarrativeSubject], str] | None = None)`.

`NarrativeRuntimeDependencies(reader, model, model_caller=None, normalization=None, projection_catalog=None, generation_sha256=None)` passes the same child-local source catalog into selection and verification; only verification consumes the frozen generation resolver.

Official subjects alone call `open_verified_projection(catalog, projection_id=subject.item_key, expected_projection_sha256=subject.subject_sha256)` and actual `automation.narrative_replay.replay_verified_projection(view, selected) -> int`. The source port opens and verifies each real parent once; the handler does not replay+export twice, read direct source paths, query SQL, or substitute first-parent anchor identity. It checks the complete requested/dependency/verified subject, actual source span parser identity, active selector and projection-specific `official-json/1.0.0` prompt before building the exact public narrative-bundle/3.0. Prompt review remains diagnostic and is not a new receipt gate.

Effect target uses existing neutral `publication_target(bundle.subject, generation_sha256)`: `urn:company-wiki:narrative-projection-bundle:{projection_sha256}:{generation_sha256}`. The SHA is injected from run binding, never guessed or replaced with source/anchor SHA. Missing/invalid resolver output gives typed DEPENDENCY_INVALID with no effect. Raw bundle2 and legacy raw target are unchanged.

Factory reads the coordinator-frozen `run.binding_json`: binding/4 execution_versions.projection_prompt, projection_model_request_schema and official_json_adapter must match current implemented constants; it copies `generation_manifests[item_key].generation_sha256` into the child resolver. It does not re-sign wrappers, parse parents or repeat coordinator manifest semantics. Current adapter version is 1.0.1 after native whitespace repair. Old raw runs with no binding remain compatible.

## Config issue found during MAIN integration

HTTPModel already accepted configured reasoning_effort (low/high/max/omitted), while factory _MODEL_FIELDS rejected it. Seven constructor-level controls first all failed at _options (reasoning-red.log). The factory now accepts this existing option unchanged. Actual HTTPModel keeps validation responsibility: invalid medium/bool/number settings fail NARRATIVE_MODEL_CONFIG_INVALID; valid configured values and model identity reach the real model object unchanged. No default model/config override and no request was sent. Test credentials are synthetic and do not enter production.

## Actual evidence

- Original verify/runtime/factory RED: 18 expected failures. Real importer/parser/catalog/projection/selected evidence and actual local model prompt/decode succeeded; old verify rejected projection via old component assumptions and new source/generation injection was absent.
- First implementation: 55 PASS (18 new, 20 old verify, 17 old worker factory), pytest14.30s.
- Added one necessary real transport replay test for the just-discovered native whitespace/source NFC boundary; added seven configured reasoning-effort controls with their own actual RED before the field fix.
- Final GREEN: **63 PASS** (26 new responsibilities plus 37 unchanged legacy responsibilities), pytest17.95s. Exact saved stdout SHA256 `3d97715fe26fb7be8081e0e0c49922d08904db56c36b7f161f84cb70262959eb`.
- Ruff final exit0; mypy final exit0 for 3 source files, 24.241s. See static-final.json.
- Runner-owned TEMP and repository Windows path-budget TEMP both removed. Every source fixture catalog lives in an owned restored directory, with byte mutation restored in finally. 0 external API/LLM requests and $0 cost. Existing factory regression includes a spawned compute worker with no network/credential access.

## Test responsibilities and limits

New tests cover real source→select→deterministic local model→decode/summary→verify contracts, two parents opened once, parser and projection prompt identity, strict public bundle3 shape, selected-field replay, second-parent bytes/state changes, issuer rebinding despite identical raw anchor, parser/prompt/text/role tampering, generation absence or changed target, shared runtime source-port wiring, true factory config/catalog plus frozen binding snapshot, valid/invalid reasoning config, and whitespace/NFC replay.

Factory composition tests explicitly fake only RunStore retrieval; source config/catalog and handlers are real. They are seam tests, not claimed full production run-store E2E. ROOT owns the combined batch/4 execution and terminal/outbox acceptance suite. The local model is a deterministic zero-transport fixture, not a paid LLM quality check. P7 final producer versions still need the final combined major-node run. This handoff completes the owned handler/composition slice, not all AUTO or the entire project.
