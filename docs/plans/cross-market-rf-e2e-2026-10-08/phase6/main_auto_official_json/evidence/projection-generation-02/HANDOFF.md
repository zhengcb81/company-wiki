# projection-generation-02 — MAIN generation helper

## Status and exact write ownership

Implemented only `src/company_wiki/automation/narrative_generation.py`, new `tests/unit/test_official_json_projection_generation.py`, and this evidence directory. No commit. No P7 leaf, contracts, adapters, catalog, public transport, or shared PWF edits. Existing five raw generation/reuse function bodies retain their pre-change SHA256. The fixed legacy raw contract still binds selective_narrative_parser/0.1.1 and bundle_producer/1.0.0; no silent old generation change.

## API

```python
projection_generation_manifest(
    request,
    subject: company_wiki.narrative_subject.NarrativeSubject,
    *, language: str,
    execution_versions: Mapping[str, Any],
    bundle_producer: str,
    narrative_adapter_version: str,
) -> dict[str, Any]
```

`subject.kind` must be `official_json`. `subject_binding` is the complete detached neutral compact identity, including issuer, cutoff, every real parent ref, source adapter and coverage. It contains no record bodies and is not evidence of current-byte verification.

Caller supplies actual projection selector/model adapter/prompt (required), optional model_request_schema and actual handler versions. It must not substitute raw-global prompt. Raw parser/document_normalization entries are omitted because the real source parser/layout come from `subject.to_dict()['adapter']`. Other supplied actual component versions remain bound. Caller owns current-byte/issuer/layout semantic verification.

Manifest is `narrative-generation/2`, with explicit `narrative-bundle/3.0`, `narrative-select-result/3.0`, `narrative-summary-result/3.0`. `parser_component` splits the actual source adapter producer/version. `source_adapter` preserves the actual adapter including structure parser, layout ID/version/fingerprint. `language`, `profile`, explicit bundle producer and explicit narrative adapter version are causal inputs.

Model semantic fields exactly cover the present HTTP adapter: model_id, endpoint, max_output_tokens, output_token_field, thinking, reasoning_effort, temperature, reasoning_split. Null optional generation options equal omission because HTTP omits them. Missing output_token_field uses the existing HTTP adapter's max_tokens default. No inference/default for model_id/endpoint/max_output_tokens. Credential env names/values, timing/bytes/fee/token budgets, run IDs, refresh and other batch membership never enter the manifest. URLs containing login credentials/query/fragment are refused; no actual URL opening occurs.

All snapshots are detached recursively finite UTF-8 JSON. Physical Windows/UNC/file URLs and Unix filesystem path values, full record arrays and secret-keyed component metadata are refused. Numeric coverage page `records` counts remain legitimate. No human permission/receipt/policy/canary was added.

## TDD and evidence

- `red.log` / `red.json`: real missing-API RED, 48 failed + 1 existing raw compatibility passed; exit 1.
- `green.log` / `green.json`: final 54 new + 11 existing raw tests = 65 passed, exit 0; old function bodies SHA unchanged.
- `ruff.log`: final Ruff exit 0 for only assigned source/new test.
- `mypy.log`: final mypy exit 0 for only assigned source.
- Initial style failure and first GREEN are retained separately; the style errors were in new test formatting only.

Pytest emitted one existing configuration warning: plugin autoload was disabled for isolation and pytest.ini still contains asyncio_mode, although this synchronous unit package needs only pytest_timeout. It is not a test failure. No unrelated pytest configuration was changed.

All pytest/mypy owned TEMP directories were removed; repository basetemp relocation cleanup explicitly reported removed=true. No catalogs or original document copies were created. External provider calls=0, external model calls=0, new cost USD0.

Ruff format used its default cache once and updated the existing ignored `.ruff_cache/0.15.18/4368123618240361633` cache containing several other MAIN tests. Its newly added entry is this unit test; the shared cache was not deleted/restored because it belongs to concurrent MAIN activity. All verification Ruff commands use --no-cache. This small cache is not a product/config/source artifact.

## Remaining MAIN work

This helper does not implement new reuse_pin, public transport/reference/read, Worker projection events, source publication/current-parent checks, or actual LLM quality. MAIN must integrate it with projection-specific actual execution versions, exact subject artifact index/metadata, and the common handler chain; use the root concentrated offline E2E/recovery/compatibility review before publication. Unit green does not accept real company forecasts or claim whole PWF completion.
