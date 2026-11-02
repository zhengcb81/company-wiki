# 工具门禁与历史真实拒绝专项审计

基线 `4990df805de77604ee67db5a1b53b9d0c0408f1e`。本报告在修复前冻结；原失败不改写成通过。

结论：过去确实存在合法真实来源结果、已付费成功材料被观察器/版本合同错误拒绝的记录；但真实语义、来源、单位、费用与研究缺陷须单独保留。新确认两处仍生效的同根日志门禁，按ROOT授权同owner修复。

## 历史分类（不把所有红测归作门禁）

- **H01 · REAL_SOURCE_OBSERVER_FALSE_REJECTION**：Real H1 source processing 37.394s reached canonical result; byte-identical SHM mtime was reported as mutation. CLOSED: comparator accepts only same-byte SHM mtime change; raw/DB/WAL changes still reject. 证据：`C-source-v1.md`。
- **H02 · REAL_SOURCE_WIRE_INTEGRATION_FAILURE**：Real H1 23.170s stopped on valid producer source_processing_complete unknown to public reading_context consumer. CLOSED ENGINEERING: actual handler/golden strict bool/legacy tests and RF wire sync; this was version skew, not missing approval. 证据：`C-source-v2.md`。
- **H03 · REAL_SOURCE_OBSERVER_FALSE_REJECTION**：Canonical source owner returned, but observer refused record >300000B before persistence; exact original outcome then unknown. Later real output 388583B persisted. CLOSED SIZE GATE; genuine v4 semantic parent P2/real work exhaustion remain OPEN, not gate failures. 证据：`C-source-v3-observer-failure.md;C-source-v4-independent.md`。
- **H04 · REAL_PAID_SUCCESS_OBSERVER_FAILURE**：Actual configured MiMo POST:10236 tokens/1885 microUSD; 485241B artifact. Observer activation_run_id KeyError after native prepare persisted. Native paid/cache recovery later used same artifact with zero extra POST. CLOSED OBSERVER FIELD INTEGRATION; four-review research/actor/source defects are separate and remain tracked. 证据：`../progress.md R4 2026-11-01;R4-context-investigation.md;AUDIT reports/r1-remediation-04/process.md`。
- **H05 · REAL_REGISTERED_RESULT_AUDIT_FALSE_REJECTION**：Registry audit actual CLI exit1 falsely unregistered a valid result: string anchor compared to tuple generation keys; actual input/forecast/snapshot/registry hashes unchanged after fix. CLOSED; later R7 removes registry permission entirely while preserving actual content/hash validation. 证据：`docs/plans/cross-market-rf-e2e-2026-10-08/reviews/HK-00700/review.md`。
- **H06 · INITIAL_REAL_LOOP_LEGAL_FAILURE_ENVELOPE_REJECTED**：FF rejected valid CWP blocked/local_preparation envelope under stale schema; proper unavailable JSON exit2 was hidden as generic transport failure. Local discovery charged 17 irrelevant old documents before latest-period fetch with max_candidates16. R1/R4 remediation engineering closed; this does not prove download or model success. Real relevant-population accounting and public error DTO needed fixing, not deleting actual resource budgets. 证据：`AUDIT runs/r1-20261021-cn-wuxi-apptec/reports/fetch.md`。
- **H07 · REAL_PAID_RECOVERY_POSITIVE_AND_TRUE_RESOURCE_STOP**：Pure preflight81880 exceeded remaining60974:0POST, actual resource stop. After configured allocation within mother budget, real DeepSeek1POST17329tokens/6701microUSD; recovery/replay/cache0 extra POST. Earlier injected nonexistent retry-code was tool bug, fixed to legitimate IO_TRANSIENT. KEEP real fee/token bounds and native error classification. Intentional test pause is not supplier permission. 证据：`review/r1-w07-live-20261022.md;review/r1-w07-live-independent-20261022.md;review/r1-w07-controller-independent-20261022.md`。
- **H08 · GENUINE_RESEARCH_OR_PROVIDER_FAILURE_NOT_PERMISSION**：Initial RF numeric arithmetic passed but Q1/TIDES target omitted, future growth assumptions not calibrated, one ratio tagged CNY, stale annual selector. MiMo401 left unknown accounting. Real index GET had no business attachment URLs. Do not relabel genuine research/units/provider/discovery gaps as gates or claim clean company acceptance. 证据：`AUDIT runs/r1-20261021-cn-wuxi-apptec/reports/process.md;storage.md;fetch.md;review/r1-w11-actual-recovery-20261024.md`。
- **H09 · SYNTHETIC_LEGAL_DTO_OR_PROCESS_REPRO**：Large legal DTO/deep recipe/optional diagnostics/PhaseC successful capture >128KiB and transport log caps were proven on isolated synthetic inputs; current engineering has fixes and reviews. CLOSED ENGINEERING; not evidence that every such gate caused a historical real-company paid rejection. 证据：`R7-core-implementation.md;R7-tooling-implementation.md;R7-final-sweep-core-independent-r3.md;R7-phase-c-observation-independent.md;checklist-verification-20261102/checklist.md`。
- **H10 · OLD_ORACLE_OR_FIXTURE_FAILURE_NOT_CURRENT_PERMISSION**：v2 independent publication rows tested as v1 chain; fake legacy schema/engine pair and unattested receipt tagged signed; old daily35/CI=PUSH inventory assertions. Correct behavior was stopped by tests/fixtures. CLOSED test/fixture roots; compatible version matrix/source/numeric checks were not relaxed. 证据：`R7-RF-publication-followup.md;R7-invest-CI-followup.md;R7-invest-E2E-implementation.md;R7-CWP-CI-policy-test-consolidation.md`。

历史路径默认相对于本implementation-results；review/相对于所选du11计划；AUDIT为 `C:/Users/郑曾波/Projects/revenue-forecast-audit/`。只引用实际报告，没有重跑原公司/收费。

## 当前实际入口逐项

- **T-NEW-LOG · MISSING_CONFIRMED_REPAIR_AUTHORIZED** · `holdout_acceptance._process`：main --spec -> run_controller.call -> _process -> actual launcher -> native CLI Actual exit0 plus stderr>max_log_bytes or stdout>max(max_log_bytes,2MiB) Raises before full native receipt/stage observation is saved; diagnostic count becomes success permission. Use existing process lifetime owner; complete protocol stdout separate from diagnostic stderr tail; preserve nonzero/timeout/tree ownership.
- **T-NEW-EVENT · MISSING_CONFIRMED_REPAIR_AUTHORIZED** · `holdout_acceptance_observer.install.event`：observed_http before original request; observed_generate after original native generate; observed_recover/replay after owner success Cumulative events.jsonl+new event exceeds max_log_bytes, or append/fsync OSError Size throws after post-once latch or after native paid success; observer may mask native status or prevent actual send. No cumulative diagnostic allowance as permission; full event data once, explicit incomplete observation on I/O failure; no resend/latch bypass, keep explicit fault injection and true native failures.
- **T-PREP-MTIME · ROOT_DESIGN_RECOMMENDATION** · `phase_c_runner.verify_preparation`：Same SHA/bytes but changed mtime against old preparation; also snapshots old mother native database. Touch-only current synthetic source refused before run; old code/sample baseline can act as admission gate. Separate ground-truth/source proof/current runtime observation from old receipt equality. Same content mtime is diagnostic; actual changed originals/config/source binding must be accounted honestly. Native history compare should reconcile authoritative cumulative accounting, not require unchanged unrelated bytes. No code change in this repair scope.
- **T-FROZEN-FLAG · ROOT_DESIGN_RECOMMENDATION** · `holdout_replay.manifest.load_manifest`：False/missing frozen_before_candidate_output, including development sample No replay accepted regardless of actual source identity. Keep clean-holdout claim unproven for nonfrozen/development data, but permit ordinary measured replay with explicit classification; flag is not source/runtime approval. Do not change gold to hide outcome. No code change this scope.
- **T-COMMIT-PIN · KEPT_BY_REASON** · `holdout_replay.producer.verify_producer`：Explicit --producer-commit differs from actually checked out producer HEAD or loaded implementation identity differs. Protects truth of specifically requested measurement revision; no old manifest commit or unrelated dirty-tree permission. A new engine can be chosen explicitly. May simplify ergonomics by default observing actual revision, not reusing stale gold pin.
- **T-REVIEW · KEPT_BY_REASON** · `checkers.check_semantics_entailment/review.validate_review`：Missing or incomplete semantic evidence review Marks NOT_EVALUATED/PARTIAL; does not prevent raw/source retrieval or paid native execution. Quality completeness cannot be silently PASS.
- **T-ROOT-TEXT · NO_RUNTIME_PERMISSION** · `holdout_acceptance.run_controller result.rf_consumption.reason`：Text says ROOT must bind public read to actual used RF formula. No approval input/branch. status passed is possible while RF adoption honestly not_consumed. Wording can say actual adoption unproven without ROOT role.
- **T-NATIVE-BOUNDARY · KEPT_BY_REASON** · `holdout native/store/model caller`：Second actual POST, changed request/source/artifact, unknown paid status, missing durable paid pin, real timeout/byte/fee/token bound, native fault outcome wrong. Actual fee/resource/source/recovery truth, not artificial permission. Preserve durable latch, exact model input, actual IO_TRANSIENT pause and unknown holds.

## 修复前合成实证

```json
{
  "quiet": {
    "code": 0,
    "receipt": {
      "status": "completed"
    },
    "stderr_bytes": 0
  },
  "noisy": {
    "error_type": "ControllerError",
    "error": "HOLDOUT_CLI_LOG_BOUND_EXCEEDED",
    "command": {
      "command": [
        "C:\\Miniconda\\python.exe",
        "-B",
        "-c",
        "import sys;sys.stderr.write('x'*8193);print('{\"status\":\"completed\"}')"
      ],
      "exit": 0,
      "stdout_bytes": 24,
      "stdout_sha256": "00c0ea9b8c7f1700639c82440c0812dd41a6cb6429b131ee5fb3bd59b2bc5113",
      "stderr_bytes": 8193,
      "stderr_truncated": true
    }
  },
  "event_limit": {
    "error_type": "RuntimeError",
    "error": "HOLDOUT_EVENT_BYTES_EXCEEDED",
    "transport_calls": 0,
    "post_once_exists": true
  },
  "mtime_only": {
    "error": "PREPARATION_FINGERPRINT_CHANGED: C:\\Users\\郑曾波\\Projects\\company-wiki\\tmp\\gf7\\prepared.json",
    "same_sha": true
  },
  "freeze_flag": {
    "error": "manifest is not marked frozen_before_candidate_output",
    "development_sample": true
  }
}
```

探针只创建 `tmp/gf7`（初态不存在），HTTP original_request以进程内计数替身替代，无socket/外部调用；准备mtime探针只读自建文件。原探针完整源码与源SHA在同名JSON。此处证据先封存，最终清理收据在独立tools-repair报告；不把临时目录默认声称已删除。

## 本次修复边界

只修holdout controller/observer、既有_bounded_process唯一进程owner与专用测试。默认严格payload资源合同不退；完整JSON协议与诊断tail区分。计数/磁盘观察故障不得覆盖native paid事实，也不得重发。mtime/holdout资格建议交ROOT，不扩大本轮工程；无主PWF、Git/index、生产配置、原件变更。真实新版摘要/缓存/RF实际采用仍OPEN。
