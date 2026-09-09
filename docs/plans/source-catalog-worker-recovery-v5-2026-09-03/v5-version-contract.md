# V5 版本合同（V5-1，rev3）

日期：2026-09-09。状态：**PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED**。本页是 [task_plan.md](task_plan.md) Phase V5-1 的交付：给出**一致方案**、枚举版本引用、界定新基线与活动入口、定义**冻结集合的精确成员与条目类型**、定义必须被拒绝的版本一致性负例，并**显式定义 v5 manifest 的 schema**。本页不是 `plan_manifest.v5.json`，不授权实施、运行或 worker 恢复。

修订依据：[rev1 独立设计审查](v5-version-contract-review.md)（rejected，F1–F10）、[rev2 独立复审](v5-version-contract-review-rev2.md)（accepted_with_findings；G1 阻断冻结、G2–G4 为 P3）。

## 1. 决策：拆分「协议 revision」与「冻结 generation」

**方案 B：拆分**（不整体改名 v5）。证据（[引用枚举](v5-version-reference-inventory.json)、[基线等价性](v5-baseline-equivalence.json)）：

1. **协议命名空间逐件版本化**：29 个不同 `$id`，后缀 **`:v4`=14、`:v1`=12、`:v5`=2、`:v2`=1**（`:v5` 为 `journal-manifest:v5`、`validator-fixture-manifest:v5`）。整体升 v5 会撞名并抹平各 artifact 独立版本线。
2. **内容是 v4 线的字节副本**：48 份计划输入中 **21 份 v4_exact、17 份 crlf_only、10 份 unproven_new_baseline**。
3. **v4 manifest 的不可变策略**要求语义变更新开 manifest 并独立复审——本方案以 `plan_manifest.v5.json`（§5 新 schema）满足，并以 `protocol_revision: v4` 标注协议线。

## 2. 版本轴与命名映射

| 轴 | 取值 | 载体 | 变更条件 |
|---|---|---|---|
| 协议 revision | `v4` | manifest `protocol_revision`；各 artifact `$id` 后缀 | 仅实际修改协议语义才升版 |
| 冻结 generation | `v5` | manifest `freeze_generation` + 文件名 `plan_manifest.v5.json` | 每次在新基线上冻结递增 |
| artifact schema_version | 逐件（1/2/4/5…） | 各 schema `$id`/`schema_version` | 由 artifact 自身演进决定 |

**映射（F10）**：`freeze_generation` ≡ `import_manifest.v5.json` 的 `capture_generation`（`v5`）；`protocol_revision` ≡ 其 `source_protocol_revision`（`v4`）；`capture_manifest` 绑定该文件 sha256（当前 `da7d116e8c692d6311411c7390bec4278b59666a771823672f53e9b0f6567e4a`）。`plan_freeze_git_head` = **生成 `plan_manifest.v5.json` 时的仓库 HEAD**。

## 3. 版本引用枚举（V5-1 第 2 项）

机器明细 [JSON](v5-version-reference-inventory.json) / [MD](v5-version-reference-inventory.md)；可用 [tools/v5_version_reference_scan.py](tools/v5_version_reference_scan.py) 复现。

扫描范围：`baseline/**`（54）＋ v5 根目录活动文档与 `.gitattributes`（5）＝ **59 份**；排除 `reviews/`、`tools/`、`import_manifest.v5.json`、`verify_import.py`、本页与两份审查/证据文件（避免自指）。

- **44 份含 `v4`、14 份含 `v3`**（含本轮更正文本）；**11 份引用已退役旧目录**；**9 份引用旧 checker**；
- `$id` 后缀分布 `:v4`=14、`:v1`=12、`:v5`=2、`:v2`=1；`plan_revision` ∈ {v3,v4}；`schema_version` ∈ {1,2}。

> 计数随活动文档编辑漂移，**以扫描时点为准**；V5-2 冻结前重新生成并与 manifest 绑定。

## 4. 新基线：10 份不可证等价文件（V5-1 第 3 项）

方法：以 `historical_v4_sha256` 为锚比较当前字节与 LF 归一化字节。**独立复算 = 事故报告表格 = 21 v4_exact / 17 crlf_only / 10 unproven_new_baseline**；事故报告正文「16/11」与其表格矛盾，属笔误（更正已记入 [progress.md](progress.md)）。

10 份须从零内容审查：`baseline/plan/` 下 `README.md`、`authorization_manifest.schema.json`、`evidence_manifest.schema.json`、`findings.md`、`operation_contract.schema.json`、`operation_contracts.schema.json`、`operation_contracts.v4.json`、`operation_intent_manifest.schema.json`、`operation_intent_template.schema.json`、`plan_consistency_check.py`。

条目类型 `equivalence` 枚举（**统一为四个值，与证据 JSON 一致**）：`v4_exact` / `crlf_only` / `unproven_new_baseline` / **`v5_own`**（v5 自有新增件，无 `historical_v4_sha256`）。

## 5. v5 manifest：schema 与**冻结集合**（F1 + G1）

### 5.1 为什么必须新建 schema

导入的 `baseline/plan/plan_manifest.schema.json` 是 **v4 的**冻结 manifest schema（`additionalProperties:false`、`schema_version const 2`、`plan_revision const v4`、`plan_directory` 指向已退役目录），**不能校验 v5 manifest**。故 V5-2 新建：

- 文件 `plan_manifest.schema.v5.json`；`$id` `urn:company-wiki:source-catalog-worker-recovery:plan-manifest:v5`（已核实不在现有 29 个 `$id` 中）；`schema_version` **const 3**；`additionalProperties` **false**。
- 必填字段 17 项：`schema_version`、`protocol_revision`(const v4)、`freeze_generation`(const v5)、`capture_manifest{path,sha256}`、`frozen_at`、`plan_directory`(const v5 目录)、`plan_freeze_git_head`、`review_state_at_freeze`、`supersedes[]`、`investigation_source{path,sha256}`、`normative_file_count`、`normative_files[]`、`frozen_set_composition`、`equivalence_summary`、`coverage_counts`、`pre_freeze_check`、`self_exclusion`、`immutability_policy`。
- **N7 的适用边界**：N7 只约束**导入的** artifact（不得被 generation 改名/改 `$id`）；v5 manifest schema 与 v5 checker 是**新增的 v5 自有件**（`v5_own`），其 `:v5` 后缀不冲突。

### 5.2 冻结集合的精确组成（G1 修正）

`normative_files` **= 51 项**，分三类，每项 `{path, sha256, size_bytes, equivalence}`：

| 类 | 数量 | 成员 | `equivalence` |
|---|---|---|---|
| 导入的计划输入 | 48 | `baseline/plan/**`（29 schema + 11 prose + `findings.md` + `plan_review_findings.md` + 4 个 `.v4.json` 实例 + `plan_consistency_check.py` + `plan_freeze_check.v4.txt`） | `v4_exact`(21) / `crlf_only`(17) / `unproven_new_baseline`(10) |
| v5 自有治理件 | 3 | `plan_manifest.schema.v5.json`、**v5 checker 入口**（V5-2 定名，落在 `tools/`）、`.gitattributes` | `v5_own` |
| 冻结 manifest 自身 | 0（排除） | `plan_manifest.v5.json` | `self_exclusion` |

- `frozen_set_composition` 字段显式记录 `{imported: 48, v5_own_governing: 3, total: 51, self_excluded: 1}`，并与 `normative_file_count` 一致。
- **证据工具不进入 normative 集**：`tools/v5_version_reference_scan.py`、`tools/v5_equivalence_check.py` 记为 `evidence_tools[]`（各自 hash 绑定），只复现证据，不是计划输入。
- `plan_manifest.schema.v5.json` 与 v5 checker 必须**同时**出现在 normative 集与 `pre_freeze_check.command` 中，避免「治理件无哈希锚」的空档。
- `N13` 判据改为：`normative_files` 必须**恰好等于**上述 51 项集合（缺/多/重复/casefold 冲突即拒绝）；`N14` 判据改为：`.gitattributes` 必须在集合内且其哈希与冻结记录一致。

## 6. 活动入口、取代关系与旧目录复活

### 6.1 目录现状（2026-09-09 实测）

| 事实 | 证据 |
|---|---|
| v5 目录**已被 Git 跟踪** | 随 R4 语料入库 wiki `f23ad1b`；本页/证据/审查文件随后提交；精确 tracked 数由 `git ls-files` 实时查询（不写死，避免 G2 类陈旧计数） |
| **旧目录已复活** | `docs/plans/source-catalog-worker-recovery-2026-08-22/` 存在、38 文件、`git ls-files`=38、`git status` clean、mtime `2026-09-07T18:08:52Z`（UTC；本地为 19:08:52+01:00）；字节与 v4 冻结 0/38、与 v5 目录任意文件 0/38 相同 |

**结论**：README/findings/progress 原「已回收/未被跟踪」表述与当前树不符，已在原处更正；旧目录是**独立第三份副本**，V5-2 必须按 N9 处理。

### 6.2 角色映射（v5 目录 71 文件 = 12 根 + 54 baseline + 3 reviews + 2 tools）

| 角色 | 文件 | 权威性 |
|---|---|---|
| 冻结 manifest（待生成） | `plan_manifest.v5.json` + `plan_manifest.schema.v5.json` | **唯一权威** |
| v5 自有规划/记录 | `README.md`、`task_plan.md`、`findings.md`、`progress.md`、本页、两份审查记录 | 活动，可更新 |
| 证据工具 | `tools/v5_version_reference_scan.py`、`tools/v5_equivalence_check.py` | 复现证据；hash 绑定但非 normative |
| 导入元数据 | `import_manifest.v5.json`、`verify_import.py` | 只证明导入；不改字节 |
| 导入审查记录 | `reviews/`（3 份） | 历史；不改字节 |
| normative 候选（51） | 见 §5.2 | 待 V5-2 冻结 |
| 历史输入 | `baseline/history/**`（5 份） | 只读历史，不得并列权威 |
| 原调查报告 | `baseline/investigation/worker-investigation-2026-08-20.md` | 历史来源 |
| 已退役旧目录 | 旧目录 38 文件 | 非权威（N9） |

### 6.3 取代链

`plan_manifest.v5.json` → supersedes → `plan_manifest.v4.json` → supersedes → `plan_manifest.v3.json`（后两者仅历史输入）。旧目录任何文件都不在取代链内。

## 7. 版本一致性负例（V5-1 第 5 项）

每条必须在 V5-2 的 v5 checker 中以**机器检查 + 测试 ID** 实现。

| ID | 负例 | 期望 |
|---|---|---|
| N1 | 把 `plan_manifest.v4.json` 当作当前活动 manifest | 拒绝 |
| N2 | `plan_directory`/`pre_freeze_check.command` 指向已退役旧目录 | 拒绝 |
| N3 | 版本轴混用（generation v5 却 protocol≠v4，或反之） | 拒绝 |
| N4 | `schema_version≠3`、缺必填字段或出现未知字段 | 拒绝 |
| N5 | normative 文件 sha256/size 与冻结记录不符 | 拒绝 |
| N6 | `equivalence` 类别与复算不符 | 拒绝 |
| N7 | **导入的** artifact 被 generation 改名/改 `$id`（v5_own 除外） | 拒绝 |
| N8 | 用旧目录 checker 输出冒充 v5 预冻结检查 | 拒绝 |
| N9 | 旧目录存在且被当作并列权威（无显式处置） | 拒绝 |
| N10 | manifest 自身进入 normative 集、缺 `self_exclusion`，或覆盖写既有 manifest | 拒绝 |
| N11 | 缺 `supersedes` 或取代链不指向 v4/v3 manifest | 拒绝 |
| N12 | `investigation_source.path` 不在 v5 目录内或 sha256 不符 | 拒绝 |
| N13 | normative 集 ≠ §5.2 的 51 项（缺/多/重复/casefold 冲突/计数或 coverage 不符） | 拒绝 |
| N14 | `.gitattributes` 不在冻结集内，或冻结期间其哈希变化 | 拒绝 |
| N15 | `freeze_generation`≠`capture_generation` 或 `protocol_revision`≠`source_protocol_revision` | 拒绝 |
| N16 | `plan_manifest.schema.v5.json` 或 v5 checker 不在 normative 集/无哈希绑定 | 拒绝 |
| N17 | `evidence_tools[]` 缺失或哈希不符 | 拒绝 |

## 8. 边界与下一步

- 本页只做规划与合同：未改协议语义、未生成 `plan_manifest.v5.json`、未运行旧 checker、未触碰 worker/配置/数据库/任务。
- 本页、两份证据、两个证据工具、两份审查记录随本次提交进入 Git，使 §5/§7 的哈希绑定有版本锚。
- **V5-2 顺序**：重验 Git/index/属性/并发写边界（含旧目录复活）→ 新建 v5 checker（实现 N1–N17）→ 跑全套一致性检查（schema/实例/DAG/测试 registry/vectors/prose）→ 生成 `plan_manifest.v5.json` 与 `plan_freeze_check.v5.txt` → 三路独立审查（SQL/性能、生命周期/安全、测试/DAG）→ P0/P1 全关。
- rev3 需再次独立确认 G1 已闭（G2–G4 为 P3，已在本页修正：计数不写死、mtime 用 UTC、枚举统一）；未确认前不进入 V5-2 冻结。
