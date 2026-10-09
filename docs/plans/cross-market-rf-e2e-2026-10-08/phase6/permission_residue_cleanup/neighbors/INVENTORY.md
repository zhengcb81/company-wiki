# Neighbor permission residue inventory

The inspected current routes are FF filing fetch/local-prepare/transcript companion, RF source_preparation, ET nested transcript_tool/API, StockWiki source/narrative readers and scheduler UI, plus canonical/installed audit skill. This is an activity-entry inventory, not a claim that every historical file has been rewritten.

“Blocks” distinguishes an actual runtime prerequisite from wording that can induce agent pauses. HTTP credentials, source identity/SHA/as-of facts, resource budgets and the user's four independent reviews are retained. Current FF/RF/ET single network intent fields represent the task request, not another human sign-off.

| Repository / current path and line | Active or historical | Blocking finding | Action / responsibility |
|---|---|---|---|
| FF `SKILL.md:3` | active skill routing | text could cause repeated permission prompt | changed: Routes the authorized task through current intent/configuration/limits. |
| FF `scripts/fetch_filing.py:6` | active module explanation | text could cause repeated permission prompt | changed docstring only: Execution AST unchanged excluding module docstring. |
| FF `SKILL.md:371` | historical receipts linked from active skill | text could demand a new canary/observation window | reframed as historical: Preserves WU-1303/902/1304 evidence; current source eligibility owns reuse. |
| FF `SKILL.md:355` | active storage eligibility guidance | old text implied separate reusable-root permission | clarified: Root registration locates storage; identity/period/asof/bytes still validated, metadata-only gaps can reconcile. |
| FF `SKILL.md:385` | legacy request compatibility | No duplicate permission gate | preserved: Optional provider/accession/cap scope is not a signed permission receipt; no expiry/policy/gap/canary gate. |
| FF `scripts/filing_contracts.py:128` | legacy runtime compatibility | No duplicate permission gate | preserved: Existing optional target scope remains strict if supplied; schema2.0 excludes it. |
| FF `scripts/fetch_filing.py:1147` | legacy runtime transport | No duplicate permission gate | preserved: Generated temporary legacy scope is transport data, not a human authorization file. |
| FF `scripts/fetch_filing.py:1505` | active v2 vs legacy compatibility | No duplicate permission gate | preserved: Legacy path containment remains separate; v2 does not require caller root-policy approval. |
| RF `SKILL.md:147` | active skill acquisition | old comment could require repeated download approval | changed: Schema2.0 example now uses one filing_intent; legacy flag remains an intent flag. |
| RF `SKILL.md:179` | active storage eligibility guidance | old text implied separate reusable-root permission | clarified: CWP owns current eligibility/local reconcile and exact public read; honest gaps remain. |
| RF `SKILL.md:41` | active source facts contract | No duplicate permission gate | preserved: As-of/source availability/SHA checks verify information facts, not human permission. |
| RF `SKILL.md:45` | active machine publication provenance | No duplicate permission gate | preserved: Machine publication receipts are integrity/consumer contracts, not per-document human sign-off. |
| RF `scripts/source_preparation.py:355` | active public entry | No duplicate permission gate | no runtime change: Delegates intent to FF and reads SourceRef publicly with current config/deadline. |
| ET `README.md:365` | active provider workflow | old text asked for both gates/discover-policy then candidate approval | changed: Same task network intent and unchanged limits across provider-supported phases. |
| ET `README.md:402` | active configuration/producer explanation | old text implied an independent rights-approval pass | clarified: Disabled capability and account limits remain real; source intake facts have one owner. |
| ET `README.md:406` | historical observation in active README | old pending integration/canary language could block current requests | reframed as historical: Past HTTP402 and producer/consumer mismatch facts retained without recurring canary license. |
| ET `transcript_tool.py:148` | active CLI | No duplicate permission gate | preserved: Legacy CLI allow-download is inert; request boolean is the one network intent. |
| ET `transcript_api.py:787` | active exact/discovery/candidate runtime intent | No duplicate permission gate | preserved: False explicit network intent returns not_authorized before provider session; no human receipt/private/public/canary gate. |
| ET `README.md:408` | active provider capability/resource contract | No duplicate permission gate | preserved: Credential absence, actual entitlement rejection, unsupported operation and fee/response/time caps remain honest outcomes. |
| StockWiki `README.md:55` | active developer UI instructions | previous token blocked scheduler start | changed: Click requests one configured bounded scheduler cycle. |
| StockWiki `stockwiki/ui_jobs.py:168` | active UI backend | previous confirm comparison raised before scheduling | removed duplicate token gate: Legacy confirm values are ignored; existing bounds/bools/scheduler/error flow intact. |
| StockWiki `stockwiki/ui_static/app.js:1371` | active UI frontend | previous window.prompt could cancel before POST | removed prompt and confirm payload: Actual action posts current controls directly; same API path/result/error handling. |
| StockWiki `stockwiki/ui.py:237` | active HTTP dispatcher | No duplicate permission gate | preserved: POST route delegates the same request and retains 400 error formatting. |
| StockWiki `stockwiki/runtime.py:83` | active scheduler execution | No duplicate permission gate | preserved: Existing queued command/job-state mutex/dependency/timeouts retained; no production jobs run. |
| StockWiki `stockwiki/cli_parsers/quick_scan.py:147` | active CLI help referring to historical owner batch | No duplicate permission gate | preserved: Frozen identity-preview report is source/provenance input; no new human token gate identified. |
| StockWiki `stockwiki/review_workflow.py:266` | active research quality decisions | No duplicate permission gate | preserved: Human or LLM decisions and configured auto-accept are research-quality states, not source-fetch permissions. |
| StockWiki `stockwiki/backup.py:211` | explicit backup restore execution mode | No duplicate permission gate | preserved outside this repair: Confirm selects applying a destructive restore instead of preview; unrelated to source/scheduler repetitive authorization. |
| audit `skills/revenue-forecast-audit/SKILL.md:52` | active skill | No duplicate permission gate | no change: Already prohibits duplicate source permission chains; four requested independent reviews remain quality review. |
| audit `skills/revenue-forecast-audit/references/workflow.md:8` | active workflow | No duplicate permission gate | no change: Carries existing authorization; truly missing configuration/budget stays a gap. |
| audit `skills/revenue-forecast-audit/references/artifact-contract.md:59` | active evidence contract | No duplicate permission gate | no change: Hashes identify artifacts; no per-layer repeated raw hashing/human receipt. |

## Actual scheduler chain

`app.js` start-button click → `runSchedulerCycleAction` POST `/api/scheduler/cycle` → `ui.py` handler → `ui_jobs.run_scheduler_cycle_from_ui` → existing `runtime.run_scheduler_cycle` → due/retry/recovery selection → `run_due_jobs` → `run_job` → queued `subprocess.run(job.command, cwd=paths.root, timeout=...)`. No email/Slack destination field was found on this request. External actions arise from already configured queued commands (the current pipeline describes DeepSeek/Tavily API jobs). No production cycle or external job was executed here.

The old backend rejected missing/wrong/null token before reaching that chain; the old frontend prompted before POST. Both duplicate steps are removed. Legacy `confirm` is accepted and ignored. Current controls, bounds, job mutex/state, dependencies, timeout, failed-job reporting and HTTP error formatting remain on their original paths.

## History and remaining ownership

Past canary/402/limited-integration receipts remain facts about those runs; they are not a recurring authorization prerequisite. Audit hash records and four independent requested reviews remain intact. Installed skills were read but not modified; MAIN owns scoped merges and targeted installation. Source facts and legacy request compatibility are not loosened by these commits. Production source/forecast stores and Dayu were not written. Fresh cohort storage scopes remain unchanged.
