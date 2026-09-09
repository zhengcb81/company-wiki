# V5 版本引用枚举（V5-1 第 2 项）

日期：2026-09-09。状态：PLAN_ONLY。范围：v5 目录内 `baseline/**`（不含 `reviews/`、`import_manifest.v5.json`、`verify_import.py` 等 v5 自有元数据）。
机器明细见 [v5-version-reference-inventory.json](v5-version-reference-inventory.json)。

## 汇总

- 扫描文件：**59**
- 含 `v4` token 的文件：**44**；含 `v3`：**13**
- 引用已退役旧目录 `source-catalog-worker-recovery-2026-08-22` 的文件：**10**
- 引用旧 checker `plan_consistency_check.py` 的文件：**9**
- 出现的 `$id` 值：`urn:company-wiki:source-catalog-worker-recovery:authorization-manifest:v4`, `urn:company-wiki:source-catalog-worker-recovery:authorization-revalidation-receipt:v1`, `urn:company-wiki:source-catalog-worker-recovery:bootstrap-verifier-manifest:v1`, `urn:company-wiki:source-catalog-worker-recovery:budget-reservation-bundle:v1`, `urn:company-wiki:source-catalog-worker-recovery:budget-settlement-receipt:v1`, `urn:company-wiki:source-catalog-worker-recovery:evidence-manifest:v4`, `urn:company-wiki:source-catalog-worker-recovery:gate-dag-instance:v4`, `urn:company-wiki:source-catalog-worker-recovery:gate-ledger-transcript:v1`, `urn:company-wiki:source-catalog-worker-recovery:gate-ledger:v4`, `urn:company-wiki:source-catalog-worker-recovery:journal-manifest:v5`, `urn:company-wiki:source-catalog-worker-recovery:journal-record:v1`, `urn:company-wiki:source-catalog-worker-recovery:ledger-head-anchor:v1`, `urn:company-wiki:source-catalog-worker-recovery:operation-contract:v4`, `urn:company-wiki:source-catalog-worker-recovery:operation-execution-receipt:v1`, `urn:company-wiki:source-catalog-worker-recovery:operation-intent-manifest:v4`, `urn:company-wiki:source-catalog-worker-recovery:operation-intent-template:v4`, `urn:company-wiki:source-catalog-worker-recovery:operation-policy-instance:v4`, `urn:company-wiki:source-catalog-worker-recovery:parser-route-manifest:v4`, `urn:company-wiki:source-catalog-worker-recovery:plan-manifest:v4`, `urn:company-wiki:source-catalog-worker-recovery:review-result:v4`, `urn:company-wiki:source-catalog-worker-recovery:review-storage-confirmation:v4`, `urn:company-wiki:source-catalog-worker-recovery:schema-registry:v1`, `urn:company-wiki:source-catalog-worker-recovery:test-id-registry-instance:v4`, `urn:company-wiki:source-catalog-worker-recovery:user-approval-receipt:v1`, `urn:company-wiki:source-catalog-worker-recovery:validator-fixture-manifest:v5`, `urn:company-wiki:source-catalog-worker-recovery:validator-release-manifest:v2`, `urn:company-wiki:source-catalog-worker-recovery:validator-request:v1`, `urn:company-wiki:source-catalog-worker-recovery:validator-scenario-fixture:v1`, `urn:company-wiki:source-catalog-worker-recovery:validator-vectors-instance:v4`
- 出现的 `plan_revision` 值：`v3`, `v4`
- 出现的 `schema_version` 值：1, 2

## 需要 v5 版本合同裁决的引用面

| 类别 | 现状 | 影响 |
|---|---|---|
| 冻结 manifest 常量 | `plan_revision: "v4"`、`plan_directory: 旧目录`、`investigation_source.path` 为旧路径、`pre_freeze_check.command` 为旧目录 checker | 直接照抄会指向已退役目录；必须由合同定义 v5 取值 |
| schema `$id` | `urn:...:plan-manifest:v4` 等 | 新 manifest 的 `$id` 必须与 `plan_revision` 自洽 |
| 文件名内嵌版本 | `gate_dag.v4.json`、`operation_contracts.v4.json`、`test_id_registry.v4.json`、`gate_ledger_validator_vectors.v4.json`、`plan_freeze_check.v4.txt` | 命名即版本声明；改名或保留须在合同中二选一并说明理由 |
| 正文/命令引用旧目录 | 见上表计数 | 合同须给出「新活动入口取代旧入口」的映射，旧引用只作历史 |
| 机器实例内版本字段 | `gate_dag.v4.json` 等的内部 `schema_version`/`plan_revision` | 若只改 manifest 不改实例，即构成「混合版本」，须被负例拒绝 |

## 明细（按旧目录引用数降序，前 20）

| 文件 | v4 | v3 | 旧目录引用 | checker 引用 | plan_revision |
|---|---|---|---|---|---|
| `baseline/history/progress.v4.md` | 40 | 15 | 41 | 3 | - |
| `baseline/history/plan_manifest.v4.json` | 7 | 1 | 2 | 2 | v4 |
| `baseline/plan/implementation_agent_prompts.md` | 3 | 0 | 2 | 0 | - |
| `baseline/plan/plan_manifest.schema.json` | 3 | 0 | 2 | 1 | - |
| `baseline/plan/README.md` | 12 | 2 | 2 | 2 | - |
| `baseline/history/plan_manifest.v3.json` | 0 | 2 | 1 | 0 | v3 |
| `baseline/plan/schema_registry.schema.json` | 1 | 0 | 1 | 0 | - |
| `baseline/plan/task_plan.md` | 8 | 0 | 1 | 0 | - |
| `progress.md` | 2 | 0 | 1 | 0 | - |
| `README.md` | 5 | 1 | 1 | 0 | - |
| `.gitattributes` | 0 | 0 | 0 | 0 | - |
| `baseline/history/plan_review_revision.v4.md` | 8 | 5 | 0 | 1 | - |
| `baseline/history/v4-freeze-integrity-incident-2026-09-03.md` | 20 | 0 | 0 | 1 | - |
| `baseline/investigation/worker-investigation-2026-08-20.md` | 0 | 0 | 0 | 0 | - |
| `baseline/plan/acceptance_thresholds.md` | 3 | 0 | 0 | 0 | - |
| `baseline/plan/agent_review_gates.md` | 3 | 0 | 0 | 0 | - |
| `baseline/plan/authorization_manifest.schema.json` | 1 | 1 | 0 | 0 | - |
| `baseline/plan/authorization_revalidation_receipt.schema.json` | 0 | 0 | 0 | 0 | - |
| `baseline/plan/bootstrap_verifier_manifest.schema.json` | 0 | 0 | 0 | 0 | - |
| `baseline/plan/budget_reservation_bundle.schema.json` | 0 | 0 | 0 | 0 | - |
