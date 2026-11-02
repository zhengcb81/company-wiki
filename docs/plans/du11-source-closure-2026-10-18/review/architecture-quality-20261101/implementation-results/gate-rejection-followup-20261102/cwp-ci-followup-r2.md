# CWP CI helper R2 — strict current input binding

**Test-only freeze, pending non-author incremental review.** Original cwp-ci-followup and exactCI7F history remain unchanged. Recipe independently found a real test-contract weakening: visible request fields could be correct while arbitraryf*64input SHA was accepted. New pure test reproduces1F/4.03s before repair.

The real input hash binds more than the four displayed request fields: citation/group mappings, source selection and subject, plus scoped task context. The sole helper now requires actual selected/version context from every one of its7call sites and asks existing runtime.build_model_request to reconstruct the current request, including captured output-budget retarget when present. It strictly compares prompt/instruction/data/inputSHA to that owner. No hash algorithm/frame copied and no decoder patched. The narrow old-quota/instruction/advisory comparison remains after this identity check, and all old capture SHA stay unchanged.

**32P /7.65s**:12new controls and exact7caller parameter closures. Genuine legacy None/1/2/3 initial and8192budgeted identities pass; forged hashes fail. Scoped4/6 genuine/forged pairs covered. A hidden selection source_units change with identical displayed data_json still rejects, showing the full source binding is active. All old raw/request/HTTP/input/data/instruction/draft and canonical hashes remain their original values.

Ruff10cumulative files PASS. Product source/decoder/fixture changes0; prior4source plus frozen atomic fixture SHA unchanged. No77/fullUnit/model/company rerun. The helper reconstructs these actual archived forms (initial or one HTTP output-budget retarget), not arbitrary invented retarget histories.

Exact9delta/10cumulative path SHA, RED/GREEN log/JUnit, original-source checks and own initially absent temp cleanup: [cwp-ci-followup-r2.json](cwp-ci-followup-r2.json). ROOT/recipe should incrementally verify and publish normally; no Git/index/mainPWF/original/config/key/paid/network operations by author.
