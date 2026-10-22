# W07 controller: one acceptance entry

Status: isolated engineering candidate. ROOT owns non-author review, integration, live execution and RF consumption. The runtime is production code from the branch base; this lane changes test tools only.

## Run entry

Use this checkout as the code root and the already configured Python environment. Set PYTHONPATH to this checkout, src and scripts, then:

```powershell
python -m tools.document_understanding_benchmark.holdout_acceptance --spec <absolute-spec.json> --stop-after preflight
python -m tools.document_understanding_benchmark.holdout_acceptance --spec <same-spec.json> --stop-after after_paid
python -m tools.document_understanding_benchmark.holdout_acceptance --spec <same-spec.json> --stop-after activation_pending
python -m tools.document_understanding_benchmark.holdout_acceptance --spec <same-spec.json>
```

`preflight_ready` is a pure, explicitly non-native preview, not a completed summary or lease. It neither initializes AUTO nor creates generation owners. Its actual UTF-8 body, configured output limit and conservative bound are saved in preflight.json/model-input.json. The body must be byte-identical at the real formal caller and HTTP boundary. If the preview exceeds remaining company/mother tokens, stop: never reduce configured output or release existing UNKNOWN to make it fit. A new preview before the formal run is safe and recomputes current inputs; a preview against an already created formal run is rejected explicitly. Preview does not claim a frozen generation; the formal native run owns the actual generation, pin and fee.

`paused_for_test` means the requested real paid/activation boundary was observed. Continue with the same spec/run; the worker fence may legitimately advance. `passed` means native paid replay, activation recovery, same-artifact cross-run cache and verified public read all ran. It still reports RF `not_consumed`. Native CLI error codes are retained in native_causes. Never treat this controller observation as another fee ledger.

## Explicit spec fields

All paths are absolute and supplied by ROOT. Existing input files are required; do not construct another source lake, register arbitrary data or download through this tool.

| Field | Value / owner |
|---|---|
| schema_version | holdout-acceptance-request/1 |
| company | Display label; no company-specific code |
| audit_run_id, audit_attempt_id, batch_run_id | Explicit finite IDs, ASCII letters/digits/underscore/dot/dash, up to100 characters |
| project_root, catalog_config | Existing isolated source setup owned by ROOT |
| source_ref | Exact public SourceRef: document_id, source_id, content_sha256, byte_size, mime_type, schema_version |
| automation_db | Same scoped native AUTO; do not reset it or old usage |
| work_root, receipt_dir | Distinct owned test-output roots, outside raw/config/catalog ancestors |
| llm_config, llm_provider | Existing Config loader owns model/options; provider deepseek/mimo/minimax/openai |
| as_of_date | Frozen ISO information date |
| limits | max_seconds, max_tokens, max_cost_usd, max_final_bytes, max_persistent_bytes, max_scratch_bytes, max_log_bytes |
| pricing | version, input_micro_usd_per_million_tokens, output_micro_usd_per_million_tokens; use current native pricing |
| expected_source | Optional existing public reader constraints; unspecified nullable keys stay null |
| allow_local_model_http | Optional loopback-only transport for offline E2E; omitted for real configured HTTPS |

The request explicitly selects 0.9.0 and reading-model-input/5. The actual wire is narrative-model-request/6, prompt reading-source-extractive/5.0.0, original source cards and ranking decisions. There is no gold-conditioned response expectation or old free-form summary contract. No keys/headers/environment values are written to observations.

## Budget and outputs

Before a live call ROOT must recompute current mother/company totals using existing append_native/mother_totals, retaining MiMo UNKNOWN and historical native attempts. Supply the smaller remaining native limits. Preview computes len(actual body)+128+actual configured output. After the actual after_paid pause, ROOT appends native usage through that existing owner before continuing. No independent budget database or refund is introduced.

Outputs are controller-result.json, native stage/CLI receipts, bounded stderr/command metadata, event observations, one secret-free actual model-input.json, and public-read request/receipt. Native generation/paid pin/source reference remain available for downstream binding. Do not copy full raw/paid-response DBs into handoff. The public artifact can be read by its exact versioned NarrativeRef; ROOT must then use RF consume_narrative_input and bind a genuinely used parameter and formula before claiming RF consumption.

## Tests and acceptance

Fast units: tests/unit/test_holdout_acceptance_controller.py (actual UTF-8 bytes, both configured output field names, spec refusal). Run with the four named native pin/lease/replay controls listed in handoff.json.

Slow major-node E2E: tests/integration/test_holdout_acceptance_controller_e2e.py. Ten cases start actual configured CLI subprocesses and real loopback HTTP, native stores, paid pins/outbox/cache. Normal run under concurrent load took101.20s; it is intentionally outside fast unit CI. No CI/hook change or permission flag was added. Every fixture owns its root, verifies raw bytes and removes only its own temporary run tree. evidence/cleanup.json records final lane cleanup.

Two exploratory nonpaid native preview designs failed honestly and were replaced by pure preview. Their RED XML is kept as investigation evidence, not current open production defects. The earlier invalid SourceRef.to_dict setup failure was not accepted as behavioral RED; five corrected valid-input failures are the initial implementation RED. Full accepted results and exact source/test fingerprints are in evidence/. ROOT non-author review remains pending until its own report is recorded.
