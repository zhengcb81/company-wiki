# Native shapes and synthetic examples

All examples are **synthetic and NOT_RUN**. They illustrate current public shapes; they contain no forecasts for 中微/腾讯/微软. A storage handoff and real source-preparation outputs are required for business execution.

## FF request 2.0

Reuse example:

```json
{"schema_version":"2.0","company_query":"SYNTHETIC-CO","document_kind":"annual_report","as_of_date":"2026-10-08","mode":"exact","fiscal_year":2025,"filing_intent":"reuse_only"}
```

Download-intent shape (illustrative bounded caps, not a true missing-period decision):

```json
{"schema_version":"2.0","company_query":"SYNTHETIC-CO","document_kind":"annual_report","as_of_date":"2026-10-08","mode":"exact","fiscal_year":2025,"filing_intent":"fetch_if_missing","acquisition_limits":{"max_bytes":10000000,"timeout_seconds":120,"max_cost_usd":"0.00"}}
```

`max_cost_usd=0.00` forbids incremental paid cost; it does not guarantee that a provider/entitlement is available. Actual caps come from scope. `latest_as_of` mode forbids `fiscal_year`; do not invent a `period_selection` field. Requests take `company_query` and optional market/exchange hints, not invented `entity`/`security_id` inputs. Resolve once; outputs carry the standard identity DTO. `reuse_only` normally forbids acquisition limits, except the documented bounded metadata discovery case for latest-as-of. A notfound catalog result is not proof all local raw/archive copies are missing: consult storage's prepared inventory before true FF download.

`companion_transcript` has its own intent and exact fiscal year/quarter plus acquisition limits for fetch. Year-only is `period_unresolved`; do not invent Q4. Preserve independent transcript status and full FF/ET usage. Known ET402/provider rejection is a named gap, not a valid transcript or zero charge. Unknown usage remains null/unknown; do not automatically retry.

## Public references and reads

`SourceRef` has exactly: `schema_version="2.0"`, `document_id`, `source_id`, `content_sha256`, `byte_size`, `mime_type`. `source_id` binds exactly to `urn:company-wiki:source:sha256:<content_sha256>`. Obtain it from storage/public import, never invent its hash or identity from a filename.

Reference request has exactly `schema_version="narrative-reference-request/1"` and `source_ref`. Returned `NarrativeRef` has exactly `schema_version="narrative-ref/1"`, `artifact_version_id`, `artifact_sha256`, `byte_size`, `source_ref`.

Read request has exactly:

```text
schema_version = narrative-read-request/1
narrative_ref = genuine returned reference
as_of_date = 2026-10-08
expected_source = {
  canonical_entity_id, market, security_id, document_kind, fiscal_year, fiscal_period
}
```

All six constraint keys are present; each value is an actual supplied constraint or null. Do not put physical paths in either reference/read DTO. This narrative read contract currently requires known publication for historical as-of reads; do not pretend source-reader 2.2 automatically adds availability proof to the narrative wire. Preserve a named unknown-publication narrative gap while the raw-source 2.2 path can qualify reliable prior proof.

Bundle/receipt sizes are bounded (RF request16KiB, receipt16KiB, body1,310,720 bytes). One verified selected bundle read can serve multiple spans. Record actual `read_at`, locator/parser versions and selection/source coverage. OCR confidence is not complete recall; omitted lines and table/reading-order limits remain limitations. A partial source can provide individually valid selected business spans without claiming full-source reading.

## Finite configured batch request

Required `narrative-batch-request/1` fields: `run_id`, `sources` (1–100 genuine SourceRefs), `profile` (P1/P2/P4), `max_seconds` (finite >0), `max_tokens` (positive integer), `max_cost_usd` (finite nonnegative micro-USD precision), `model` (object), `pricing` (object).

For the configured CLI, keep `model` limited to caller transport bounds if needed; actual loader overlays model_id/endpoint/api_key_env and generation options before strict validation. Pricing requires `version`, `input_micro_usd_per_million_tokens`, `output_micro_usd_per_million_tokens` (nonnegative integers). Prices are **micro-USD per million tokens**, not USD per token. MAIN supplies matching provider pricing provenance; this package intentionally supplies no invented executable price.

Optional `refresh=false` by default; `max_final_bytes` <=2MiB, default `max_persistent_bytes`1GiB and `max_scratch_bytes`2GiB. Scope may set smaller explicit caps. Preparation/normalization/selection/model/read share the finite batch deadline. Record actual AUTO reservation/usage status; failed/unknown calls do not become free calls. Budget allocation must cover all paid operations for that company, not USD2 for each source or batch.

## RF input assembly

Default native schema is3.7; opt-in3.8 adds the native operating-units extension. Current typed target comparison APIs are supported by the installed target validator; do not guess a schema upgrade from an example. Start from the current installed generator for field names, then replace its sources/captures with genuine public builder results and fill missing sections. The generator's cutoff is `base_year+1-06-30`; override with scope cutoff. Include real `fiscal_year_end`, `forecast_version` and complete `management_targets` (empty only after genuine search/coverage, not because generation omitted it).

Use `sources`, `evidence_claims`, `parameters`, `segments`, `historical_revenue`, `reported_total_revenue_parameter_id`, `base_adjustment_parameter_ids`, `management_communication_coverage`, `management_targets`, `research_coverage`, `growth_driver_tree`, recognition, shared constraints/adjustments and `sensitivity_tests` according to actual installed current references/validator. These are native records, not new side databases. Preserve at least two genuine historical company revenue observations and reconcile external segment revenue + signed base adjustments to reported total before forecasting. Do not copy whole old golden inputs or convert a prior run's forecasts into fresh assumptions.

Every parameter has a unique ID and native kind: `reported_fact`, `derived_fact`, `management_guidance`, `analyst_assumption`, or `scenario_stress`. Distinguish third-party estimates in source/evidence and definition; `third_party_estimate` and `management_target` are not valid native parameter-kind enum values. Preserve period, dimension/time basis, unit/currency/scale and real evidence or transparent rationale. Formula-derived parameters carry input IDs/formula; segment scenario `driver_parameter_ids` reference ordered annual IDs. Select model names/required driver dimensions from `installed_runtime.json`; an unsupported precision or invented product split is not repaired by choosing a complex model.

`research.input_evidence.bind_parameter_evidence(...)` returns updated parameter, emitted claims/new sources/lineage. Its explicit roles keep history, mechanism direction, value range, peer analogy, counter comparison and conversion separate. Directional evidence cannot supply an extracted number. `value_range` requires exact numerical support. `peer_analogy` requires analogical inference distance. Counterevidence belongs on the contrary growth-driver evidence node; recognition-policy claims belong on recognition, not numerical parameter support. Use actual check UTC date for `verified_date`, not `as_of_date`.

Management `checked_scope` uses `management-communication-scope/1`, category/start/end/coverage_complete/items; original business communication differs from discovery index/notice. Item fields identify item_ref/source_id/published_date/content_role/selected/read/skip_reason. Coverage and the latest category must derive from actual bounded search/read, not a prefilled checklist. Catalog `document_kind` and RF communication `source_type`/category are separate truthful classifications; the generic `investor_relations` mapping is not proof a document is the latest presentation.

Targets retain exact wording, raw unit/currency, scope/perimeter, measurement basis/period, commitment strength and treatment. Run-rate needs an evidenced annual-recognized conversion, not quarter×4. An independent benchmark compares all three scenarios with used parameter IDs and checked benchmark claims; ambiguous/mismatched targets remain visible gaps.

## Sensitivity and typed period recipes

Synthetic 5 percentage-point conversion shape:

```python
from research.input_quantities import convert_input_quantity
q = convert_input_quantity(5, input_unit="pp", engine_unit="ratio")
test = {"name":"synthetic-utilization", "parameter_id":"synthetic_used_base_utilization",
        "shock_type":"percentage_point", "shock_value":q["engine_value"], "input_quantity":q}
```

This is a shape example only; no calculation was run. `percentage_point` uses ratio delta0.05 for5pp; `basis_point` divides shock by10,000; `percent` uses proportional change (0.05=5%). `absolute`, `range`, `discrete` are also native; ranges/discrete use ordered finite down_value/up_value. A test must shock an actually used Base parameter at most once; assumptions vs scenario stresses remain explicit. Keep requested/effective/clamped output and dependency effects.

Typed `comparison_basis` uses `management-target-comparison/1`: metric_kind is `annual_revenue_level`, `quarterly_revenue_level` or `year_over_year_growth`, with period and metric-specific fields. Quarterly comparisons need genuine used scenario parameter paths with matching quarter `measurement_period` and annual native ancestry. YoY uses the previous annual `base_period` and explicit `raw_ratio_basis` (`percent`, `fraction`, `level_multiple`); unknown base remains not_comparable. `research.target_measurement` validates these records. `research.timing_bridge.build_quarter_delay_bridge` supports an explicit Q4→nextQ1 synthetic delay/catch-up/cancellation bridge using existing native formulas; it does not calibrate Low or infer quarter amounts. Use these capabilities only where real data supports them; do not add them as mandatory research complexity.
