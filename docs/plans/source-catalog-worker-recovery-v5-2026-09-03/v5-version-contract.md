# V5 版本合同（V5-1，rev2）

日期：2026-09-09（rev2 依据独立设计审查 [F1–F10](v5-version-contract-review.md) 修订）。状态：**PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED**。本页是 [task_plan.md](task_plan.md) Phase V5-1 的交付：给出**一致方案**、枚举全部版本引用、界定新基线与活动入口、定义必须被拒绝的版本一致性负例，并**显式定义 v5 manifest 的 schema**。本页不是 `plan_manifest.v5.json`，不授权实施、运行或 worker 恢复。

依据：`import_manifest.v5.json`、`baseline/**`、[v4 冻结漂移事故报告](baseline/history/v4-freeze-integrity-incident-2026-09-03.md)、[R4 迁移表](../painpoint-outcome-audit-2026-09-05/r4-transition.md)、[独立设计审查](v5-version-contract-review.md)。

## 1. 决策：拆分「协议 revision」与「冻结 generation」

**方案 B：拆分**（不把整套计划整体改名为 v5）。

证据（本次机械复核，见 [引用枚举](v5-version-reference-inventory.json)、[基线等价性](v5-baseline-equivalence.json)）：

1. **协议命名空间逐件版本化**：基线出现 **29 个不同 `$id`**，后缀为 **`:v4`=14、`:v1`=12、`:v5`=2、`:v2`=1**（`:v5` 为 `journal-manifest:v5`、`validator-fixture-manifest:v5`；`:v2` 为 `validator-release-manifest:v2`）。整体升 v5 会与既有 `:v5` 撞名并抹平各 artifact 独立版本线。
2. **内容是 v4 线的字节副本**：48 份计划输入中 **21 份与 v4 冻结哈希逐字节相同**、**17 份 LF 归一化后精确复现冻结哈希**、**10 份无法证明等价**。内容是「v4 协议 + 待审新基线」，不是协议改版。
3. **v4 manifest 的不可变策略**要求语义变更新开 `plan_manifest.vN.json` 并独立复审——本方案以 `plan_manifest.v5.json`（**新 schema，见 §5**）满足，同时用 `protocol_revision: v4` 如实标注协议线。

> **两轴 + 一轴**：`protocol_revision`（协议线，本次 v4）与 `freeze_generation`（冻结代次，本次 v5）由 manifest 记录；每个 artifact 的 `$id`/`schema_version` 保持导入原值，**不整体改名**。

## 2. 版本轴与命名映射

| 轴 | 取值 | 载体 | 变更条件 |
|---|---|---|---|
| 协议 revision | `v4` | manifest `protocol_revision`；各 artifact 的 `$id` 后缀 | 仅实际修改协议语义才升版；升版须新 manifest + 独立复审 |
| 冻结 generation | `v5` | manifest `freeze_generation` + 文件名 `plan_manifest.v5.json` | 每次在新基线上冻结递增；不表示协议变更 |
| artifact schema_version | 逐件（1/2/4/5…） | 各 schema `$id`/`schema_version` | 由该 artifact 自身演进决定，不随 generation 变动 |

**命名映射（F10）**：`import_manifest.v5.json` 的 `capture_generation: "v5"` 与 `source_protocol_revision: "v4"` 即本次两轴的**来源**；v5 manifest 的 `freeze_generation` 必须等于该 `capture_generation`（`v5`），`protocol_revision` 必须等于该 `source_protocol_revision`（`v4`），且 `capture_manifest` 字段绑定该文件的 sha256（见 §5）。`plan_freeze_git_head` 定义为：**生成 `plan_manifest.v5.json` 时的仓库 HEAD**（V5-2 记录，不用旧值）。

## 3. 版本引用枚举（V5-1 第 2 项）

机器明细 [JSON](v5-version-reference-inventory.json) / [MD](v5-version-reference-inventory.md)。

- 扫描 **59 个文件 = `baseline/**` 54 份 + v5 根目录 5 份**（不含 `reviews/`、`import_manifest.v5.json`、`verify_import.py`）；其中 **44 份含 `v4` token、13 份含 `v3`**；
- **10 份引用已退役旧目录** `docs/plans/source-catalog-worker-recovery-2026-08-22`；**9 份引用旧 checker** `plan_consistency_check.py`；
- `plan_revision` 取值 `v3`/`v4`；`schema_version` 取值 `1`/`2`；
- 29 个 `$id` 的后缀分布：`:v4`=14、`:v1`=12、`:v5`=2、`:v2`=1。

**处置**：正文/命令中的旧目录与旧 checker 引用只作历史线索；新活动入口一律指向 v5 目录内路径；照抄旧目录常量的 manifest 由 §7 负例拒绝。

## 4. 新基线：10 份不可证等价文件（V5-1 第 3 项）

方法：以 `import_manifest.v5.json` 的 `historical_v4_sha256` 为锚，比较当前字节与 LF 归一化字节。**独立复算 = 事故报告表格 = 21 exact / 17 crlf_only / 10 unproven**；事故报告**正文**所写的「16/11」与其自身表格矛盾，属笔误（该更正已记入 [progress.md](progress.md)）。

10 份**不能声称与 v4 字节等价**（须从零内容审查，不得继承 v4 审查结论）：

`baseline/plan/README.md`、`authorization_manifest.schema.json`、`evidence_manifest.schema.json`、`findings.md`、`operation_contract.schema.json`、`operation_contracts.schema.json`、`operation_contracts.v4.json`、`operation_intent_manifest.schema.json`、`operation_intent_template.schema.json`、`plan_consistency_check.py`。

处理约定：manifest 逐件标注 `equivalence`（`v4_exact` / `crlf_only` / `unproven_new_baseline`），保留 `historical_v4_sha256` 作来源锚；`unproven_new_baseline` 在 V5-2 独立审查中单独列出，审查范围不得因「只差换行」缩小。

## 5. v5 manifest 的 schema（F1：显式定义，不由导入 schema 管辖）

**关键裁决**：导入的 `baseline/plan/plan_manifest.schema.json` 是 **v4 的冻结 manifest schema**（`additionalProperties: false`、`schema_version const 2`、`plan_revision const v4`、`plan_directory` 指向已退役目录），**不能校验 v5 manifest**。因此 V5-2 必须新建一份 **v5 自有 schema**：

- 文件：`plan_manifest.schema.v5.json`（v5 目录根）
- `$id`：`urn:company-wiki:source-catalog-worker-recovery:plan-manifest:v5`
- `schema_version`：**3**（`const`）
- `additionalProperties`：`false`
- 必填字段：

| 字段 | 约束 | 说明 |
|---|---|---|
| `schema_version` | `const 3` | 与导入 schema（const 2）区分 |
| `protocol_revision` | `const "v4"` | 协议线，来自 `source_protocol_revision` |
| `freeze_generation` | `const "v5"` | 冻结代次，等于 `capture_generation` |
| `capture_manifest` | `{path, sha256}`，`path const "import_manifest.v5.json"` | 导入快照锚 |
| `frozen_at` | UTC | 冻结时刻 |
| `plan_directory` | `const "docs/plans/source-catalog-worker-recovery-v5-2026-09-03"` | v5 目录 |
| `plan_freeze_git_head` | 40hex | 生成时的仓库 HEAD（§2） |
| `review_state_at_freeze` | `const "FROZEN_FOR_INDEPENDENT_REVIEW"` | 同 v4 语义 |
| `supersedes` | 数组，含 `plan_manifest.v4.json`/`v3.json` 的 `{path, sha256}` | 明确取代链 |
| `investigation_source` | `{path const "baseline/investigation/worker-investigation-2026-08-20.md", sha256}` | v5 内路径 |
| `normative_file_count` / `normative_files` | 计数一致；每项 `{path, sha256, size_bytes, equivalence}` | 48 份计划输入 |
| `equivalence_summary` | `{v4_exact: 21, crlf_only: 17, unproven_new_baseline: 10}` | 与 §4 复算一致 |
| `coverage_counts` | 同 v4 的 8 个键 | V5-2 复算 |
| `excluded_dynamic_or_historical_paths` | 数组 | 同 v4 语义 + v5 自有文件 |
| `pre_freeze_check` | `{command, exit_code, reported_check_count, stdout_sha256, read_only_confirmed}`；`command` 必须指向 **v5 checker 入口** | 不得用旧目录 checker |
| `self_exclusion` | `const "plan_manifest.v5.json"` | manifest 自身不进 normative set |
| `immutability_policy` | 文本 | 同 v4 语义：语义变更须新文件名 + 独立复审 |

**N7 的澄清**：§7 的 N7 约束的是「**导入的** artifact 不得被 generation 改名/改 `$id`」；v5 manifest schema 是**新增的 v5 自有 artifact**（不是把 v4 manifest schema 改名），因此其 `:v5` 后缀与 N7 不冲突。

## 6. 活动入口、取代关系与旧目录复活（V5-1 第 4 项；F2/F6/F8/F9）

### 6.1 目录现状（2026-09-09 实测）

| 事实 | 证据 |
|---|---|
| v5 目录**已被 Git 跟踪**（64 个 tracked） | `git ls-files` = 64；随 R4 语料入库 wiki `f23ad1b` |
| 本页与两份 JSON、审查文件**尚未跟踪**（5 个） | `git status` = `??` → 本次提交后消除，使 §8 的哈希绑定有 git 锚 |
| **旧目录 `source-catalog-worker-recovery-2026-08-22/` 已复活** | 存在、38 个文件、`git ls-files`=38、`git status` clean、mtime 均为 `2026-09-07T19:08:52Z`（09-03 退役之后的一次整目录工作树写入）；其字节与 v4 冻结 0/38 相同、与 v5 基线 0/38 相同 |

**结论**：README/findings/progress 中「旧目录已回收/不存在」的表述**与当前树不符**；旧目录是一个**独立于 v5 基线的第三份副本**（tracked、clean、内容漂移）。V5-2 必须把它当作**并列权威风险**处理（见 §7 N9）。

### 6.2 角色映射（完整 69 文件，F6）

| 角色 | 文件 | 权威性 |
|---|---|---|
| 冻结 manifest（待生成） | `plan_manifest.v5.json` + `plan_manifest.schema.v5.json` | **唯一权威** |
| v5 自有规划/记录 | `README.md`、`task_plan.md`、`findings.md`、`progress.md`、`v5-version-contract.md`、`v5-version-contract-review.md`、`v5-version-reference-inventory.{json,md}`、`v5-baseline-equivalence.json` | v5 活动，可更新 |
| 导入元数据 | `import_manifest.v5.json`、`verify_import.py`、`.gitattributes` | 只证明导入；**不改字节** |
| 导入审查记录 | `reviews/import-review-2026-09-03.md`、`reviews/old-plan-retirement-{inventory.json,result.md}` | 历史记录；**不改字节** |
| normative 候选（48） | `baseline/plan/**`（29 schema + 11 prose + findings/plan_review_findings + 4 个 `.v4.json` 实例 + `plan_consistency_check.py` + `plan_freeze_check.v4.txt`） | 待 V5-2 冻结 |
| 历史输入 | `baseline/history/**`（`plan_manifest.v3.json`、`plan_manifest.v4.json`、`plan_review_revision.v4.md`、`progress.v4.md`、`v4-freeze-integrity-incident-2026-09-03.md`） | **只读历史**，不得并列权威 |
| 原调查报告 | `baseline/investigation/worker-investigation-2026-08-20.md` | 历史来源 |
| 已退役旧目录 | `docs/plans/source-catalog-worker-recovery-2026-08-22/**`（38 文件） | **非权威**；复活事实见 §6.1，处置见 N9 |
| 旧 checker 输出 | `baseline/plan/plan_freeze_check.v4.txt` | 历史；不得冒充 v5 预冻结检查 |

### 6.3 取代链

`plan_manifest.v5.json` → supersedes → `plan_manifest.v4.json` → supersedes → `plan_manifest.v3.json`（后两者仅历史输入，不得作为活动权威）。旧目录任何文件都不在取代链内。

## 7. 版本一致性负例（V5-1 第 5 项；F5 扩充）

每条都必须在 V5-2 的 v5 checker 中以**机器检查 + 测试 ID** 实现（不得只写散文）。

| ID | 负例 | 期望 |
|---|---|---|
| N1 | 把 `plan_manifest.v4.json` 当作当前活动 manifest | 拒绝 |
| N2 | `plan_directory`/`pre_freeze_check.command` 指向已退役旧目录 | 拒绝 |
| N3 | 版本轴混用：`freeze_generation=v5` 但 `protocol_revision≠v4`，或声称 v4 却指向 v5 目录 | 拒绝 |
| N4 | `schema_version≠3`，或缺 §5 任一必填字段，或 `additionalProperties` 出现未知字段 | 拒绝 |
| N5 | normative 文件 sha256/size 与冻结记录不符 | 拒绝 |
| N6 | `equivalence` 类别与复算不符（`crlf_only` 标成 `v4_exact` 或反之） | 拒绝 |
| N7 | **导入的** artifact 被 generation 改名/改 `$id` 后缀 | 拒绝（v5 自有新 artifact 除外，见 §5） |
| N8 | 用旧目录 checker 的输出冒充 v5 预冻结检查 | 拒绝 |
| N9 | 旧目录（`source-catalog-worker-recovery-2026-08-22/**`）存在且被当作并列权威 | 拒绝；除非记录显式处置（重新退役或标记 `non_authoritative_copy`） |
| N10 | manifest 自身进入 `normative_files`，或缺 `self_exclusion`，或对既有 manifest 覆盖写 | 拒绝 |
| N11 | 缺 `supersedes` 或取代链不指向 v4/v3 manifest | 拒绝 |
| N12 | `investigation_source.path` 不在 v5 目录内或 sha256 不符 | 拒绝 |
| N13 | normative 集合不完整（缺/多文件、计数与 `normative_file_count` 不符、coverage 复算不符） | 拒绝 |
| N14 | `.gitattributes` 未纳入冻结集合或冻结期间被改动 | 拒绝 |
| N15 | `freeze_generation` ≠ `capture_manifest.capture_generation`，或 `protocol_revision` ≠ `source_protocol_revision` | 拒绝 |

## 8. 边界与下一步

- 本页只做规划与合同：未改协议语义、未生成 `plan_manifest.v5.json`、未运行旧 checker、未触碰 worker/配置/数据库/任务。
- 本页 + 两份 JSON + 审查文件随本次提交进入 Git，使 §5/§7 的哈希绑定有版本锚（F9）。
- **V5-2 顺序**：重验 Git/index/属性/并发写边界（含旧目录复活事实）→ 新建 v5 checker（含 N1–N15 机器检查）→ 跑全套一致性检查（schema/实例/DAG/测试 registry/vectors/prose）→ 生成 `plan_manifest.v5.json` 与 `plan_freeze_check.v5.txt` → 三路独立审查（SQL/性能、生命周期/安全、测试/DAG）→ P0/P1 全关。
- rev2 需再次独立设计审查确认 P0/P1 已闭；未通过前不得进入 V5-2 冻结。
