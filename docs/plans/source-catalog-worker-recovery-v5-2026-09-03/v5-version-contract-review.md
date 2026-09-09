# V5 版本合同：独立设计审查（2026-09-09）
审查者：independent design review agent（非作者）
范围：v5-version-contract.md + 两份 JSON（v5-version-reference-inventory.json/.md、v5-baseline-equivalence.json）；交叉核对 import_manifest.v5.json、baseline/history/v4-freeze-integrity-incident-2026-09-03.md、task_plan.md、README.md、findings.md。
结论：**rejected**（2×P0、4×P1、4×P2）。P0/P1 阻断 V5-2 冻结。
复算基线：baseline/** = 54 文件；v5 目录 = 69 文件（12 根 + 54 baseline + 3 reviews）；git tracked（v5 目录）= 64。
## 发现
|ID|级别|证据|说明|
|---|---|---|---|
|F1|P0|`baseline/plan/plan_manifest.schema.json:6,20-30,33-39,58-68`（`additionalProperties:false`；`required` 含 `plan_revision`；`plan_revision const "v4"`；`schema_version const 2`；`plan_directory const "…2026-08-22"`；`investigation_source.path const "docs/worker-investigation-2026-08-20.md"`；`pre_freeze_check.command const <旧目录 checker>`）vs 合同 `:23-25,66,79`|合同既要求 manifest 新增 `protocol_revision`/`freeze_generation` 且 N4 要求 `schema_version=3`，又规定 schema「保持导入值」；导入 schema 同时禁止新增字段、要求 `plan_revision`、并锁死旧目录常量。合同未说明 v5 manifest 由哪个 schema 校验，二者不可同时成立。|
|F2|P0|`docs/plans/source-catalog-worker-recovery-2026-08-22/` 现存 38 文件，`git ls-files`=38，`git status --porcelain` 为空（clean），全部 mtime=2026-09-07T18:08:52Z；字节既不等于 v4 冻结值（raw 0/38、LF 归一化 3/38）也不等于 v5 基线（0/38，如 task_plan.md 55,272B vs 基线 57,300B）|合同 `:64-65` 把旧目录同名文件标为「已退役」，README:6、findings.md:51、progress.md:24-26 称旧路径已回收/absent；实际旧目录已复活且被 Git 跟踪，取代关系的前提不成立。|
|F3|P1|`grep "11 份\|16 份"` 命中 findings.md:9、task_plan.md:41、baseline/history/progress.v4.md:35；progress.md 无任何更正记录|合同 `:40` 称 16/11 笔误「已在 progress.md 记录」不实；v5 权威文档仍写 11 份，未随合同更正。|
|F4|P1|按 v5-version-reference-inventory.json 自身 `totals.distinct_ids`（29 项）统计：`:v4`=14、`:v1`=12、`:v5`=2、`:v2`=1；独立重算同值|合同 `:34` 写「`:v4` 的 15 个、`:v1` 的 11 个」，与自身 JSON 矛盾（结论不受影响，但证据数字错误）。|
|F5|P1|合同 `:74-83`（N1–N8）|负例不覆盖：manifest 自哈希/自排除/不可覆盖与 `supersedes`（事故报告 §8.5 明确要求）、`investigation_source.path`（N2 只管 `plan_directory`/`pre_freeze_check.command`）、normative 集合完备性（漏列/多列文件、`normative_file_count` 与 `coverage_counts` 复算）、`.gitattributes` 必须进入冻结集（事故报告 `:168`）；且全部负例无 validator/测试 ID 载体，§5 的 v5 checker 入口仍为 TBD。|
|F6|P1|合同 `:61-68` 表覆盖 54 个现存文件 + 1 个待生成文件；v5 目录实有 69 文件|未列入表的现存文件含 `baseline/plan/plan_consistency_check.py`（10 份 unproven 之一、v5 唯一 checker 副本，既未定为候选也未定为退役）、`.gitattributes`、`import_manifest.v5.json`、`verify_import.py`、`reviews/`×3、`baseline/investigation/worker-investigation-2026-08-20.md`、`baseline/history/`×3、两份枚举/等价 JSON。|
|F7|P2|独立重算：baseline/**=54；59 = 54 + 根目录 5 文件（.gitattributes、README.md、findings.md、progress.md、task_plan.md）|合同 `:13,31` 称「59 个基线文件」，与 README:38「54 份基线文件」不一致；枚举 .md `:3` 声明范围 `baseline/**` 却含根文件。|
|F8|P2|README:27、findings.md:19,39、progress.md:46 仍写「未被 Git 跟踪 / tracked=0」；git ls-files v5 目录=64|合同 `:70` 已发现边界变化，但未要求更新这些仍是权威的规划文档。|
|F9|P2|`git status --porcelain`：v5-version-contract.md、两份 JSON、inventory.md、本审查均为 `??`|合同 `:88` 称「审查绑定本页与两份 JSON 的哈希」，但这 3 份未入 Git，无锚且审查期可变。|
|F10|P2|import_manifest.v5.json 用 `capture_generation`/`source_protocol_revision`；合同 `:23-24` 用 `freeze_generation`/`protocol_revision`|两条 generation 命名无映射说明；`plan_freeze_git_head` 在 v5 语境下锚定哪个提交（f23ad1b 或后续）未定义。|
## D1 方案选择
方案 B（拆分）**方向正确**，三项证据经复核成立：(a) 59 文件范围内 29 个不同 `$id`，版本后缀为 `:v1`×12、`:v2`×1、`:v4`×14、`:v5`×2（重算值，非合同的 15/11）；(b) import_manifest.v5.json 确已使用 `capture_generation: v5` + `source_protocol_revision: v4`；(c) v4 manifest 的 `immutability_policy` 原文为「Do not overwrite or append to this file. A semantic plan change requires a new plan_manifest.vN.json filename and independent re-review.」（plan_manifest.v4.json / schema `:69`），合同转述准确。
**整体升 v5 确会撞名**：已存在 `journal-manifest:v5` 与 `validator-fixture-manifest:v5`，且 14 个 `:v4` artifact 会被错误统一。
但拆分方案未闭合自身前提（F1）：新增 `protocol_revision`/`freeze_generation` 必然要求改动 `plan_manifest.schema.json`，而合同 §5 又规定 schema「保持导入值」，N7 又禁止 `:v5` 后缀。→ 方案选择可接受，落地合同不可接受。

## D2 三轴定义
三轴**不满足**非重叠/可测：
- 协议轴（`$id` 后缀）可机械检测；generation 轴仅存在于文件名与单个字段，无 validator 载体，且与导入侧 `capture_generation` 无映射（F10）。
- 第三轴自相矛盾：§2 称 artifact `schema_version`「不随 generation 变动」，N4 却要求 v5 manifest 的 `schema_version` 从导入值 2 变为 3（F1）。对 manifest 这一 artifact，第三轴**随**第二轴变动。
- 仍含糊的字段：`plan_freeze_git_head`（v5 锚定提交未定义）、`normative_file_count`/`coverage_counts`（是否沿用 48/115/315/18/140/29/60/44/105，还是按新基线重算）、`excluded_dynamic_or_historical_paths`（是否新增 `.gitattributes`、`reviews/`）、`investigation_source.path`（旧 const 已指向不存在的路径）、`supersedes*`（完全缺失）。

## D3 引用枚举
独立重算（`os.walk` over `baseline/**`，排除 reviews/、import_manifest.v5.json、verify_import.py 及两份新 JSON）：
- baseline 文件数 **54**（合同/枚举 .md 称 59；59 = 54 + 根目录 5 文件，见 F7）；
- 含 `v4` 的文件 **44**、含 `v3` 的 **13**（与 JSON 一致）；
- 引用退役目录 `source-catalog-worker-recovery-2026-08-22` 的 **10**、引用旧 checker `plan_consistency_check.py` 的 **9**（与 JSON 一致）；
- 不同 `$id` **29**，后缀 `:v4`=**14**、`:v1`=**12**、`:v5`=**2**、`:v2`=**1**（合同 `:34` 的 15/11 错误，见 F4）；`plan_revision` ∈ {v3,v4}、`schema_version` ∈ {1,2} 与 JSON 一致。
结论：文件级计数全部可复现；仅「59 个基线文件」的命名与 `$id` 后缀分布两处不符。

## D4 10份不可证等价清单
独立复算（逐件 `sha256(raw)`、`sha256(LF-normalized)` 对 `historical_v4_sha256`）：48 份 `prior_plan_current_content` → **exact 21 / crlf_only 17 / unproven 10**，与 v5-baseline-equivalence.json 的 `counts` 及三组清单**逐项相同**；合同 `:44-55` 的 10 份清单与复算集合**完全一致**（无多、无缺）。
事故报告：§4 表格机械解析 = **27 行、True 17 / False 10**，且 27 行的冻结哈希、当前哈希、LF 可复现三列与我的独立复算 **0 处不符**；正文 `:11-12` 的「16 份 / 11 份」确为笔误。合同 `:40`「以表格与本次复算为准」判断正确，但「已在 progress.md 记录」不实（F3），且 findings.md:9、task_plan.md:41、progress.v4.md:35 仍写 11 份。

## D5 入口取代映射
不完整且一处失效：
- 失效：旧目录**仍然存在且被 Git 跟踪**（38 文件、clean、2026-09-07T18:08:52Z 批量写入），字节既非 v4 冻结值也非 v5 基线；合同却把旧目录同名文件标为「已退役」（F2）。
- 缺漏：`plan_consistency_check.py`（v5 唯一 checker 副本，10 份 unproven 之一）未归入任何角色；`.gitattributes`（事故报告 `:168` 要求进入冻结集）未列；`import_manifest.v5.json`、`verify_import.py`、两份枚举/等价 JSON、`reviews/`×3、`baseline/investigation/`、`baseline/history/` 的 3 份未列（F6）。
- 表内 `plan_manifest.v5.json` 尚不存在，属计划项而非现存权威文件，表述无误但需与「待生成」区分。

## D6 负例充分性
8 条负例覆盖了旧 manifest、错路径、轴混用、schema、字节、等价类别、`$id` 冲突、旧 checker 输出，方向正确，但不足以约束拆分模型（F5）：缺 manifest 自哈希/自排除/不可覆盖与 `supersedes`（事故报告 §8.5 明确要求新 generation manifest 记录 supersedes hash）、缺 `investigation_source.path` 负例、缺 normative 集合完备性（漏列/多列、counts 复算）、缺 `.gitattributes` 入集、缺 `capture_generation` 与 `freeze_generation` 一致性；且 N1–N8 均为 prose，无 schema/validator/测试 ID 载体，§5 的 v5 checker 入口仍 TBD，当前**不可执行**。

## D7 Git 边界
边界变化被**正确识别**：`git ls-files docs/plans/source-catalog-worker-recovery-v5-2026-09-03` = **64**；最后一次触碰该目录的提交为 `f23ad1b chore(planning): track the R4 planning corpus in git`（2026-09-09 20:01:29 +0100），与合同 `:70` 一致；`git check-attr text eol` 对目录内文件返回 unset（`.gitattributes: * -text -eol -filter -working-tree-encoding` 生效）。V5-2 重验要求已显式写明（`:70`「V5-2 必须先重验 index/属性/并发写边界，再冻结」）。
不足：(i) 未覆盖旧目录复活这一同类风险（F2），V5-2 重验必须包含「退役目录是否存在/是否被跟踪」；(ii) 合同自身与两份 JSON 未被跟踪（F9）；(iii) README/findings/progress 的未跟踪表述未要求同步（F8）。

## 声明
本审查为只读独立设计审查，未修改合同、两份 JSON、baseline、manifest 或任何产品代码；未提交、未运行旧 checker/worker/测试套件，未联网。除本文件外无写入。证据均来自本次机械复算（Python 3 / git 只读命令）与上述 file:line。审查者非合同作者；本合同在 F1、F2 关闭前不得作为 V5-2 冻结依据。
