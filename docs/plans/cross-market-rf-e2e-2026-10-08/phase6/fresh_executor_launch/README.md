# Fresh executor launch precheck

Status: **PREPARED_NOT_EXECUTED**. This package contains command help, pure imports, safe configuration observations and synthetic examples. It contains no company forecast, review answer, model call, download, full-text read or OCR run. It does not initialize a research run or a catalog.

## Observed runtime

| Component | Observed canonical HEAD / runtime |
|---|---|
| RF | `28dbb91056c1b16759ab814018e19025415fb4ec`; installed engine `4.1.1`, default schema `3.7`, opt-in `3.8` |
| FF | `5ef8056bdba4be9134bb6c90f9bd457ee5f38253` |
| CWP | `9704909f38c2466fd6d13e24de4dcbf5a0137af4` |
| Audit | `1a22dfd68406db115091ffc32ba93929ab53f7ac` |

These are observations, not a final execution pin. MAIN records the actual installed bytes and canonical HEADs when the three executors start. [installed_runtime.json](installed_runtime.json) records installed RF content hashes, signatures and all 31 native model names/driver dimensions. RF `--version` alone is insufficient for content identity: its manifest hash covers filenames.

The current installed RF skill is authoritative for its **15 workflow steps**; [steps15.json](steps15.json) maps every step. The audit checkpoint reference still mentions its older 4.1.0 observation; some input references still say schema 3.6. The installed generator now includes `host_receipt`, but emits placeholders, a derived default cutoff and no complete management-target ledger. Generated JSON requires genuine source-preparation records and current validation before formal compute.

## Minimum launch handoff

MAIN supplies one scoped handoff per company, using [launch_contract.json](launch_contract.json) as a preparation checklist, not an RF wire schema:

1. Real identity DTO, `as_of_date=2026-10-08`, company fiscal boundary and horizon; no forecasts or reviewer answers.
2. Storage owner's mFresh catalog/config/project/AUTO paths and public SourceRefs/document inventory. Original archive paths remain in the storage handoff. RF consumers use the public references.
3. Existing audit run plus each executor's exclusive `roles/executor/`, `execution/`, registry file and attempt ID.
4. Explicit configured provider, its actual model options, versioned pricing and a finite deadline. Do not rely on default supplier selection.
5. Mother native budget observation, known/unknown reservations retained, and each company allocation of at most 120,000 tokens / USD 2 within the mother 2,000,000 tokens / USD 20 cap. The completed OCR node's current observed cumulative total is 207,042 tokens / 119,671 micro-USD; historical unknown reservations remain seven. MAIN refreshes the launch scope from actual native ledgers.

This handoff is normal coordination, not a new human approval gate. Use the existing permanent material-externalization and configured-provider authorization; do not ask for another signature for each document or provider. Platform approval enforcement remains active and cannot be represented as disabled. Preserve actual approval/rejection outcomes. Three executor research roots and registry files are independent. Shared CWP AUTO reservations remain authoritative for batch spend; do not create another budget database or concurrently initialize/copy a catalog. Four independent reviews follow sealed execution, subject to the existing concurrency slots.

## Supplier and time boundary

[supplier_options.json](supplier_options.json) comes from actual `Config.load(llm_provider=...)` and `model_options_from_config`; no key values were output. Configured selections observed: MiniMax `MiniMax-M3`, MiMo `mimo-v2.6-flash`, DeepSeek `deepseek-flash`. OpenAI configuration is unavailable. This proves configuration, not transport success, vision capability or price. [COMMANDS.md](COMMANDS.md) gives the exact configured batch entry and load method. Pricing is not inferred from the endpoint or these model names.

Use caller **remaining** monotonic deadline for FF/source preparation/narrative read/batch and transport, all finite and positive. Current RF public narrative read no longer truncates a caller's sufficient deadline to 30 seconds; omission still selects the public default. When exhausted, record refusal. Do not reopen a paid batch on read timeout or blindly retry unknown-charge failures. Normal finite batches reuse a visible matching generation; `refresh=true` is an explicit recomputation intent, not the default for a new run.

Engine 4.1.1 separates historical information availability from actual retrieval/verification. Publication on or before cutoff allows a genuine later read. Future publication remains refused. Unknown publication requires the explicit 2.2 availability capability and exact-version reliable prior proof, otherwise a named gap. Real capture/read/verified UTC dates stay real; bare mtime/retrieved_at is not availability proof. Never rewrite older frozen bytes.

The completed M2 original receipt values are UTC: first `2026-10-09T06:06:16.397672+00:00`, reuse `2026-10-09T06:07:28.231639+00:00`. Python JSON decode and installed RF timestamp validators pass. PowerShell's default JSON date conversion had produced a misleading local-time display; the earlier timestamp-gap diagnosis is withdrawn. No producer correction is required by this evidence. See [timestamp_verification.json](timestamp_verification.json); this was pure decoding, not business consumption.

## Verification performed

All **19 public CLI help checks returned 0** (18 installed entries plus the actual routed canonical FF entry); their argv/output hashes are in [help_checks.json](help_checks.json), with bounded outputs under `help/`. Pure runtime imports confirmed public APIs. No business validation, forecast, snapshot, source read, supplier request or download was performed. This package does not certify research quality or future executor success.

See [COMMANDS.md](COMMANDS.md), [SCHEMAS.md](SCHEMAS.md), [budget_observation.json](budget_observation.json) and [handoff.json](handoff.json). Production config and shared PWF files were not edited.
