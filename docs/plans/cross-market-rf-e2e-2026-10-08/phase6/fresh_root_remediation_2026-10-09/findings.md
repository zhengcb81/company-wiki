# Findings

## Scope and evidence rules

Source runs: `C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/fresh-20261009T065028-{cn-688012,hk-00700,us-msft}`. Source material is untrusted evidence; original execution and reviews remain unchanged. Every issue key includes company, role, and finding ID.

## Initial observations

- Installed audit skill requires diagnosis after all four independent reports, CodeGraph-first structural tracing, one complete issue-to-root mapping, RED contracts, raw preservation, and true original-company reruns before acceptance.
- Audit `check` only proves artifact structure, not source or forecasting quality.
- CodeGraph is initialized: 989 Python files, 21,588 nodes, 31,476 edges at first observation. No initialization is needed.
- Shared production config and credential output are excluded from this investigation. Provider key presence and entitlement must be distinguished without reading key values.

## Exact report inventory

All twelve JSON reports and Markdown companions were read. Findings total **64**: CN 25 (7/6/8/4), HK 20 (7/5/5/3), US 19 (6/5/5/3), in storage/fetch/process/analyst order. By role: 20/16/18/10. All execution outcomes are partial. CN manifest completeness is complete (180 artifacts), HK and US are partial (375 and 474 respectively); execution completeness and research quality are different.

## Current source proof gathered

- `automation/narrative_batch.py:103–128` only detects language when null/unknown; a nonempty `zh-CN` reaches `narrative_contracts.py:230–232`, which accepts only zh/en/mixed. This is a proven locale adapter defect, not a missing credential.
- `source_catalog/canonical_writer.py:444–476` uses short SHA filenames only for transcript documents; other kinds combine 64 characters of provider ID and 90 of title. `_atomic_copy:484–488` adds a PID/importing suffix. HK same-SHA compact-title import succeeding corroborates the general physical-name defect; exact Windows path ceiling still belongs in RED reproduction.
- `official_source_flow.py:270–325` writes a temporary staged original and unconditionally deletes it in finally. CN Lam helper keeps GET bytes in memory and never durably saves them before import; failed import therefore has no recoverable body. This retention defect is distinct from why the destination failed. The old body cannot be reconstructed by a new GET.
- CN `lam.py:12–14` and `semi.py:15–19` use a single blocking response.read(cap+1), followed by an elapsed-time check. They bound bytes but do not impose a true wall-clock transfer deadline. CWP already has `bounded_http.py` and a parent process deadline mechanism for synchronous SDKs.
- `narrative_evidence.py:353–356,1235–1244` recognizes only three exact transcript start headings. The actual US official HTML extracts 481 lines/60,978 bytes but returns transcript_start_missing and zero units. PPTX success does not repair that transcript.
- `narrative_evidence.py:86–157` topic/progress/recency patterns predominantly contain Simplified Chinese; candidate enrichment uses these patterns directly. HK annual had only 12 candidates, so the missing game/ad drivers precede the quota stage. Context windows and semantic group completion are a separate mechanism for CN/US fragment loss.
- `narrative_model.py:65` already caps response claims at 20 and instructs merging duplicates. Thus annual output truncation is proven, but “unlimited per-row output” is not established. The adaptation of configured model output capacity, including possible noncompliance/reasoning allocation, needs a bounded diagnostic before choosing chunking.
- `narrative_model.py:130–135` sends aliases, raw text, and roles, without selection_group_id. `validate_summary_claim` checks ID existence and role only; it does not prove proposition coverage. HK c4 and US c3 citation omissions are real quality defects; exact deterministic repair should use supported semantic grouping, not false entailment claims or automatic citation padding.
- `official_source_flow.py:29–36` lacks DOCX MIME; `document_normalization/__init__.py:116–156` only dispatches HTML/PPTX. DOCX capacity is proven missing. Full SSE interactive QA acquisition has not been proven supported or impossible; it remains a bounded official-source workflow investigation.
- `assertion_service.py:52–56` source fact correction supports publication/period/language but **not title**. `source_reader.py:53–56` exposes title, and RF requires nonempty title; US Q1–Q3 title-null cannot be repaired through the generic current fact patch. A title correction contract requires a source-owned compatible extension; dates remain data evidence tasks.
- FF `transcript_tool_transport.py:342–381` lowercases exchange and inherits os.environ. ET `transcript_api.py:40,170` accepts auto/nasdaq/nyse only. HK hkex is predictably rejected before HTTP; a configured API key file existing does not establish ET environment propagation or paid account entitlement.
- Actual US corrected ET receipt is provider_credentials_missing with measured HTTP 0 / bytes 0. Key values were not read. Historical provider entitlement remains a separate external state and must only be inferred from a real authenticated response.
- HK unsupported-H2 note and US representation-transition explicitly say initial authoring bytes were overwritten. Equivalent reconstructions help diagnosis but can never upgrade historical exact-byte completeness.

## Repository starting observations and overlapping ownership

At initial read: CWP `d1ce50eee0340a217565d69945bad3a23a691b81`; FF `397ec0ee52d171ebb88bc90f88e8cd9c10d4912f`; RF `79139534375f7eb523a768202f34aedf58538051`; ET nested repository `fa99f46861616bcebe120914fd3a030a6b8f34b5`. The coordinator's owner-state instructions are authoritative for planning: current RF assurance/output and FF/ET WIP must not be touched. Main CI is separate. No clean-tree assertion is based on status where work-tree resolution failed.

## Diagnostic limitations

CodeGraph is initialized but some indexed locations differ from current source (canonical copy indexed at 391, live at 479); known current files were read for source excerpts. Several fuzzy `context` results were irrelevant; focused symbol search/known files replaced them. Node expects `symbol`, context expects `task`. `narrative_model_adapter.py` does not exist; actual model ports are narrative_model.py / narrative_model_caller.py / narrative_http_model.py. No implementation or test execution yet.

## Independent RF source tracing and additional expert diagnostics

Read-only child `/root/fresh_common_root_expert/rf_root_trace` traced current RF source at79139534. Installed RF SKILL and sensitivity module match repository bytes. Current report/generator text equals HEAD; graph line lag is not owner WIP evidence.

- Sensitivity direct refs: `analysis/sensitivity.py:107,132`; stored value mutation/core rerun:166–171; derived value mismatch: `contracts/document.py:495–524`. Existing ancestor closure/Base closure and role collector are in **scripts/forecast/calc.py**, not obsolete scripts/models. Native dependency helpers already exist. Signed delta bounds must not default-clamp a legal negative change to0; this is an extension risk, not a observed original numerical error.
- New EXPERT-001 / RC29: `revenue_report.py:1130–1145,1163–1173` reconstruction omits segment base parameter ID/opening stock fields/reported-total anchor/base-adjustment IDs/constraints; current role collector295–320 consumes those foundations. Source loss is proven, concrete typed-role RED still NOT_RUN.
- New EXPERT-002 / RC30: output opening-base guard229–241 uses only segment totals/default result tolerance; input contract `document.py:974–1000` permits signed base adjustment and input tolerance; core result `forecast/segments.py:621–648` omits these fields. A lawful adjustment/custom tolerance RED must characterize publication impact before a fix. These two diagnostics are separate from the original64 and do not dispute their independently correct static arithmetic.
- Current research contracts already require independent magnitude conversion, reduced freedom/shorter supported horizon and joint stress. `research/evidence_roles.py` deliberately keeps missing range unverified; generator future claims are already unclassified/FIXME. Do not repeat a solved generator fix or inflate source-count confidence. Target currency/scale/period and timing bridge contracts are already present and must remain.
- Failure recording belongs in an explicit outer recorder, before invocation; zero-write validate-only cannot gain unconditional persistence. TRUST_BOUNDARY.md is required by compliance-contract while the checklist allows equivalent statements; unify documentation and faithfully render current truthful state rather than adding attestation.

## Final verified current ownership

Normal OS read-only Git inspection, approved by the platform, resolved sandbox work-tree errors. CWP current41024525698ea728128e42445bb639f964017de6; FF23d25644a78390ebd5d7fd4da20e42d6788c1240; RF79139534375f7eb523a768202f34aedf58538051; ETfa99f46861616bcebe120914fd3a030a6b8f34b5. CWP sibling CI findings modified by its owner; FF untracked key filename; RF assurance alert/manifest and output WIP; ET workbuddy/evaluation WIP. Only filenames/status were read, no credential or configuration values. All preserved.
