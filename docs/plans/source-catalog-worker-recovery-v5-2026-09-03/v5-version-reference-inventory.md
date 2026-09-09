# V5 版本引用枚举（V5-1 第 2 项）

日期：2026-09-09。状态：PLAN_ONLY。范围：`baseline/**`（54 份）＋ v5 根目录规划文档（5 份）＝ **59 份**；排除 `reviews/`、`tools/`、`import_manifest.v5.json`、`verify_import.py` 与 v5 自有元数据。
机器明细见 [v5-version-reference-inventory.json](v5-version-reference-inventory.json)；可用 [tools/v5_version_reference_scan.py](tools/v5_version_reference_scan.py) 复现。

## 汇总

- 扫描文件：**59**（baseline 54 + 根 5）
- 含 `v4` token：**44**；含 `v3`：**14**
- 引用已退役旧目录 `source-catalog-worker-recovery-2026-08-22`：**11**
- 引用旧 checker `plan_consistency_check.py`：**9**
- `$id` 总数：**29**；后缀分布：`:v1`=12、`:v2`=1、`:v4`=14、`:v5`=2
- `plan_revision`：['v3', 'v4']；`schema_version`：['1', '2']

## 需要版本合同裁决的引用面

| 类别 | 现状 | 影响 |
|---|---|---|
| 冻结 manifest 常量 | `plan_revision: "v4"`、`plan_directory: 旧目录`、`investigation_source.path` 旧路径、`pre_freeze_check.command` 旧目录 checker | 照抄会指向已退役目录；由合同 §5 的 v5 schema 定义新取值 |
| schema `$id` | 29 个，后缀 `:v4`=14、`:v1`=12、`:v5`=2、`:v2`=1 | 新 manifest schema 必须自带 `:v5` 且不与既有 `:v5` 撞名 |
| 文件名内嵌版本 | `gate_dag.v4.json`、`operation_contracts.v4.json`、`test_id_registry.v4.json`、`gate_ledger_validator_vectors.v4.json`、`plan_freeze_check.v4.txt` | 命名即版本声明；合同裁定**不改名**（协议线标识） |
| 正文/命令引用旧目录 | 见上表计数 | 合同 §6 给出取代映射；旧引用只作历史 |
| 机器实例内版本字段 | 4 个 `.v4.json` 实例的内部 `$id`/`schema_version` | 只改 manifest 不改实例即构成混合版本，由 N3/N7 拒绝 |

## 明细（按旧目录引用数降序，前 20）

| 文件 | v4 | v3 | 旧目录引用 | checker 引用 | plan_revision |
|---|---|---|---|---|---|
| `baseline/history/progress.v4.md` | 40 | 15 | 41 | 3 | - |
| `baseline/history/plan_manifest.v4.json` | 7 | 1 | 2 | 2 | v4 |
| `baseline/plan/implementation_agent_prompts.md` | 3 | 0 | 2 | 0 | - |
| `baseline/plan/plan_manifest.schema.json` | 3 | 0 | 2 | 1 | - |
| `baseline/plan/README.md` | 12 | 2 | 2 | 2 | - |
| `progress.md` | 8 | 1 | 2 | 0 | - |
| `README.md` | 5 | 1 | 2 | 0 | - |
| `baseline/history/plan_manifest.v3.json` | 0 | 2 | 1 | 0 | v3 |
| `baseline/plan/schema_registry.schema.json` | 1 | 0 | 1 | 0 | - |
| `baseline/plan/task_plan.md` | 8 | 0 | 1 | 0 | - |
| `findings.md` | 2 | 0 | 1 | 0 | - |
| `.gitattributes` | 0 | 0 | 0 | 0 | - |
| `baseline/history/plan_review_revision.v4.md` | 8 | 5 | 0 | 1 | - |
| `baseline/history/v4-freeze-integrity-incident-2026-09-03.md` | 20 | 0 | 0 | 1 | - |
| `baseline/investigation/worker-investigation-2026-08-20.md` | 0 | 0 | 0 | 0 | - |
| `baseline/plan/acceptance_thresholds.md` | 3 | 0 | 0 | 0 | - |
| `baseline/plan/agent_review_gates.md` | 3 | 0 | 0 | 0 | - |
| `baseline/plan/authorization_manifest.schema.json` | 1 | 1 | 0 | 0 | - |
| `baseline/plan/authorization_revalidation_receipt.schema.json` | 0 | 0 | 0 | 0 | - |
| `baseline/plan/bootstrap_verifier_manifest.schema.json` | 0 | 0 | 0 | 0 | - |
