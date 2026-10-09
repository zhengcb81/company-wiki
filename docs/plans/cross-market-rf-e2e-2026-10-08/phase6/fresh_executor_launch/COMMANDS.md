# Exact entrypoints and execution order

**Templates only; not run.** MAIN supplies real scope paths and storage configuration. `$Scope` below denotes those assigned values; it is not an existing public scope-loader API. Examples below use synthetic `SYNTHETIC-CO`, a synthetic segment and hypothetical years. They are not inputs for the original three companies. Do not execute placeholders. Preserve wire date/timestamp strings with Python `json.loads`; PowerShell's default `ConvertFrom-Json` can convert them to DateTime and reserialize a different timezone.

## 1. Process environment and logs

```powershell
$Py = 'C:/Miniconda/python.exe'
$RF = 'C:/Users/郑曾波/.agents/skills/revenue-forecast'
$FF = 'C:/Users/郑曾波/Projects/filing-fetch' # installed RF routing config selects this canonical root
$Audit = 'C:/Users/郑曾波/.agents/skills/revenue-forecast-audit/scripts/audit_run.py'
$CWP = 'C:/Users/郑曾波/Projects/company-wiki'
# Values below come from MAIN/storage's one-company scope, never guessed/defaulted.
$Run = $Scope.audit_run
$Exec = $Scope.execution_dir
$Catalog = $Scope.storage.catalog_config
$FFConfig = $Scope.storage.filing_fetch_config
$Project = $Scope.storage.project_root
$AutoDB = $Scope.storage.automation_db
$BatchWork = $Scope.storage.batch_work_dir
$Provider = $Scope.supplier.provider
$Remaining = $Scope.remaining_seconds # recompute from the actual monotonic deadline before each operation
# Set only inside this executor process (or child env); restore if using a reused shell.
$env:PYTHONPATH = "$CWP/src"
$env:REVENUE_PUBLICATION_REGISTRY = $Scope.rf_registry_file
```

The registry override must be an explicit **file path** under this executor's assigned root. The registry interprets a non-existing directory string as a file. Formal compute and snapshot create can write the registry; never let either use the installed skill's default artifact directory.

In an executor-owned Python orchestration invocation, establish `deadline = time.monotonic() + assigned_total_seconds` once. Before each operation, compute `remaining = deadline - time.monotonic()`; if `remaining <= 0`, record refusal instead of calling. Pass that positive remaining value to the relevant public API/CLI and bounded subprocess timeout. Resuming a call is not permission to manufacture a new unrestricted deadline. These variables are caller bookkeeping, not new RF fields or a new budget store.

CLI recording wrapper (use the remaining outer deadline, sufficient for the inner operation and finite cleanup):

```powershell
& $Py -X utf8 -B $Audit capture --run $Run --role executor `
  --timeout-seconds $Remaining --max-log-bytes $Scope.max_log_bytes -- `
  $Py -X utf8 -B "$RF/scripts/source_preparation.py" --help
```

This example is a synthetic help call. Replace its child argv with the actual operation below. `capture` records actual argv/time/exit/output in `roles/executor/commands/`. For native tools, store the actual call ID via:

```powershell
& $Py -X utf8 -B $Audit event --run $Run --role executor `
  --kind tool_call --data-file "$Exec/native-event.json"
```

The event JSON refers to the real tool call and attempt/step/input/output; do not manually append fabricated JSONL success. Default capture limits are 1 MiB per stream / 600 seconds; pass explicit finite scope limits when required. Do not pipe raw binary source-reader stdout through a text logger. `capture` is not a system-wide process-tree cancellation service; cleanup belongs to the actual scoped caller.

## 2. Filing acquisition/reuse and verified source construction

Financial sources use the real RF→FF→CWP chain. Preferred FF request is schema `2.0`, with one `filing_intent`. Storage supplies safe config that routes writes to mFresh. Passing catalog alone does not redirect a default FF writer.

```powershell
& $Py -X utf8 -B "$RF/scripts/source_preparation.py" `
  --request-file "$Exec/filing-request.json" --result-envelope `
  --company-wiki-catalog-config $Catalog --company-wiki-config $FFConfig `
  --filing-fetch-root $FF --source-reader-receipt-version 2.2 `
  --timeout-seconds $Remaining
```

Receipt version **2.1** is the unchanged default; known publication works through it. Choose **2.2** explicitly when MAIN's capability scope permits the new producer and prior-availability proof is needed. The full `source-preparation-result/1` envelope retains `source`, `filing_fetch` and optional `narrative`; keep FF/companion usage/gaps instead of saving only a source. A `SourceRef` candidate is not yet a verified raw capture. Copy the public builder's returned source record unchanged into RF `sources`; do not synthesize its capture/receipt fields.

Direct FF CLI exists for a specifically assigned fetch checkpoint:

```powershell
& $Py -X utf8 -B "$FF/scripts/fetch_filing.py" --config $FFConfig `
  --request-file "$Exec/filing-request.json" --source-ref-v2 --timeout-seconds $Remaining
```

Normally source preparation already invokes it, so do not fetch the same request twice for a checkpoint. Schema 2.0 intent is authoritative; do not add the legacy `--allow-download` flag as a second permission rule.

Already registered official presentations, prospectuses or other non-filing documents can use the installed **public Python API** in an executor-owned invocation:

```python
from pathlib import Path
from source_preparation import prepare_registered_source_result
result = prepare_registered_source_result(
    candidate=real_source_candidate, as_of_date=scope_as_of_date,
    company_wiki_catalog_config=Path(storage_catalog_config),
    timeout_seconds=remaining_seconds, source_reader_receipt_version="2.2")
```

Use storage's genuine candidate/identity metadata, not a raw-path join or a fabricated SourceRef. This path reports `filing_fetch=None` honestly and does not satisfy an actual FF invocation checkpoint. Archive objects without extensions require storage's official local import preparation; executors do not guess MIME, publication, year or rename original bytes.

## 3. Finite narrative batch, public read and real consumption

Model composition uses the actual config loader. The following command **can incur real spend when launched**; this precheck did not execute it:

```powershell
& $Py -X utf8 -B "$CWP/scripts/narrative_batch_configured.py" `
  --llm-provider $Provider --project-root $Project --catalog-config $Catalog `
  --automation-db $AutoDB --work-dir $BatchWork --request "$Exec/narrative-batch.json"
```

MAIN may supply `--llm-config <actual managed config>` explicitly; doing so disables the loader's default dotenv auto-load, so the child credential environment must already be supplied. Do not print Config or the environment. Configuration-only safe inspection is `model_options_from_config(Config.load(llm_provider=provider).llm)`; serialize only endpoint/model/non-secret options and credential-presence booleans. The configured entry overlays actual model/generation fields; request `model` may set finite `timeout_seconds`, `max_request_bytes`, `max_response_bytes`. Do not silently switch providers, invent vision support or guess pricing.

Use SourceRefs from the scoped catalog, finite caps, a versioned supplier pricing record and default `refresh=false`. P1 is one mixed worker; P2 has one compute + one model worker; P4 has three compute + one model worker. Each worker owns its client. Separate company execution does not authorize multiplying the mother spend cap.

Public narrative CLI operations are:

```text
python <RF>/scripts/narrative_source_preparation.py --company-wiki-catalog-config <catalog> --operation reference --timeout-seconds <remaining>
python <RF>/scripts/narrative_source_preparation.py --company-wiki-catalog-config <catalog> --operation read --timeout-seconds <remaining>
python -m company_wiki.source_catalog.narrative_transport_cli --config <catalog> --operation reference
python -m company_wiki.source_catalog.narrative_transport_cli --config <catalog> --operation read
```

These commands require strict UTF-8 JSON **stdin**, not a nonexistent `--request-file` option. Use an executor-owned subprocess wrapper with `input=request_path.read_bytes()`, bounded `timeout=remaining`, exact argv and actual audit capture; do not rely on PowerShell's default native pipeline encoding. CWP transport read writes bundle bytes to stdout and a one-line JSON receipt to stderr. RF preparation consumes this wire safely. `--reader-executable` is one executable path, not a quoted whole argv; default module + scoped `PYTHONPATH` is appropriate here.

For actual parameter consumption, call once for the selected bundle, not once per span:

```python
from pathlib import Path
from source_narrative_context import consume_narrative_input
updated_input, consumption_receipt = consume_narrative_input(
    native_input, request=real_narrative_read_request,
    bindings=[{"span_id": real_selected_span_id, "claim_id": "synthetic_unique_claim",
               "parameter_id": existing_used_parameter_id,
               "support_type": "rationale_support"}],
    source_id=real_registered_source_id, catalog_config=Path(storage_catalog_config),
    timeout_seconds=remaining_seconds, verified_by=executor_name)
```

The synthetic claim label above illustrates shape only. Bindings have exactly these four keys; all IDs must be genuine/unique/used in the actual input. This API does not infer a numeric assumption, rerun a paid batch or treat a summary as a checked numerical fact. Store the returned dependency receipt (span/locator/parser/source SHA/claim/parameter/formula refs). Merely listing an artifact is `not_consumed`. Reuse/read failure stays named; a selected exact replay does not imply complete OCR recall for the source.

## 4. Native input, lint, hashes, validation, compute and render

Synthetic skeleton example:

```powershell
& $Py -X utf8 -B "$RF/scripts/generate_input_template.py" --name SYNTHETIC-CO `
  --base-year 2025 --forecast-years 2026 2027 --segments SYNTHETIC-SERVICE `
  --currency USD --unit million --segment-model SYNTHETIC-SERVICE=services `
  --output "$Exec/synthetic-input-draft.json"
```

For actual execution, pick native models from [installed_runtime.json](installed_runtime.json) based on evidence, then fill identity/as-of/fiscal boundary/horizon/version, genuine sources/captures, historical reconciliation, parameters/claims, management communication/targets, recognition, scenarios/driver tree and sensitivity. Replace every FIXME/placeholder and generated cutoff. Do not use this synthetic draft as a business input. Current schema and semantics are described in [SCHEMAS.md](SCHEMAS.md); current validator is the final field authority.

Run the following on the actual completed input in this order, through audit capture:

```powershell
& $Py -X utf8 -B "$RF/scripts/lint_input.py" "$Exec/input-draft.json" --check-conclusion-facts --check-sensitivity-propagation
& $Py -X utf8 -B "$RF/scripts/fix_hashes.py" "$Exec/input-draft.json" --output "$Exec/input.json"
& $Py -X utf8 -B "$RF/scripts/fix_hashes.py" "$Exec/input.json" --check
& $Py -X utf8 -B "$RF/scripts/revenue_forecast.py" "$Exec/input.json" --validate-only --verbose
& $Py -X utf8 -B "$RF/scripts/revenue_forecast.py" "$Exec/input.json" --output "$Exec/forecast/forecast.json" --markdown "$Exec/forecast/forecast.md"
```

Lint exit 2 means findings; fix actual problems rather than bypassing gates. Hash fixing repairs input-side derived hashes, not source bytes, evidence truth, unsupported values or date conflicts. `--validate-only` performs draft validation/calculation without publication/registry writes. Formal compute validates the published result against input, then registers and produces JSON + Markdown from the same result. Independent strong read API is `revenue_report.validate_published_forecast(result, data)`. Renderer API is `revenue_report.render_markdown(result)`; never hand-edit the formal numerical report after rendering.

There is **no separate sensitivity CLI**. Place `sensitivity_tests` in native input; the engine calls `analysis.sensitivity.calculate_sensitivities(data, result)` and publishes results. Recompute the model for legitimate joint stresses in a new versioned research input; do not sum nonlinear single-shock results. Do not invent target-price/valuation artifacts in CWP.

## 5. Snapshot, registry, later backtest and sealing

Set `input.forecast_version` to the same actual version passed below **before** formal compute. Snapshot create formally recomputes and registers; it is not a mere file copy. It refuses overwrite.

```powershell
& $Py -X utf8 -B "$RF/scripts/revenue_backtest.py" create "$Exec/input.json" --version $Scope.forecast_version --output "$Exec/forecast/snapshot.json"
& $Py -X utf8 -B "$RF/scripts/publication_registry.py" lookup --input-sha $ActualInputSHA
& $Py -X utf8 -B "$RF/scripts/publication_registry.py" audit --result "$Exec/forecast/forecast.json"
# Only later, when genuine actuals are available:
& $Py -X utf8 -B "$RF/scripts/revenue_backtest.py" evaluate "$Exec/forecast/snapshot.json" "$Exec/actuals.json" --output "$Exec/forecast/backtest.json"
& $Py -X utf8 -B $Audit check --run $Run
```

Until actuals exist, mark backtest N/A/not_run with reason; never manufacture one. Registry audit checks native receipt/hash lineage; audit `check` checks artifact integrity and never certifies research quality. Seal execution manifest/step ledger/document/source matrix/fact→parameter→formula index and actual new tool logs after complete/partial/failed outcome. Preserve unknown usage and unresolved gaps. A repair after sealing uses another attempt; review answers remain independent.
