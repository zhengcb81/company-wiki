# Worker v5 — 进度日志

## 2026-09-09：V5-1 版本合同（rev2，待独立复审）

- 交付 [v5-version-contract.md](v5-version-contract.md)（rev2）、[版本引用枚举](v5-version-reference-inventory.json)、[基线等价性](v5-baseline-equivalence.json)：
  - **方案裁决**：拆分 `protocol_revision`（v4）与 `freeze_generation`（v5）两轴，不整体升 v5——依据 29 个 `$id` 的后缀分布 `:v4`=14/`:v1`=12/`:v5`=2/`:v2`=1（整体升版会与既有 `journal-manifest:v5` 撞名）。
  - **引用枚举**：59 个文件（baseline 54 + v5 根 5）；44 份含 `v4`、13 份含 `v3`；10 份引用已退役旧目录、9 份引用旧 checker。
  - **基线等价**：**21 exact / 17 crlf_only / 10 unproven**。本页与 `findings.md`、`task_plan.md` 原写的「16/11」为笔误，已更正；`baseline/history/progress.v4.md` 属冻结历史，保留原字并在此披露。
  - **v5 manifest schema**：新建 `plan_manifest.schema.v5.json`（`$id …:plan-manifest:v5`、`schema_version 3`），字段见合同 §5；导入的 v4 manifest schema 不校验 v5。
  - **负例**：N1–N15，待 V5-2 以机器检查 + 测试 ID 实现。
- 独立设计审查 rev1 结论 **rejected**（2×P0、4×P1、4×P2），审查文件 [v5-version-contract-review.md](v5-version-contract-review.md)；rev2 已逐条修订，待复审。
- **两项现状更正（实测）**：
  1. 本目录已随 R4 语料入库（wiki `f23ad1b`）；README/findings 的「未被 Git 跟踪/tracked=0」不再成立（精确 tracked 数以 `git ls-files` 实时查询为准，本页不写死），V5-2 必须先重验 Git/index/属性/并发写边界。
  2. **旧目录 `source-catalog-worker-recovery-2026-08-22/` 已复活**：38 文件、tracked、clean、mtime `2026-09-07T18:08:52Z` UTC（本地 19:08:52+01:00），字节与 v4 冻结 0/38、与 v5 基线 0/38 相同——与「已移入回收站」表述不符，按合同 N9 处理（并列权威风险）。
- **rev3（同日）**：按 rev2 复审的 G1 修订**冻结集合定义**（`normative_files` = 48 导入 + 3 个 v5 自有治理件 `plan_manifest.schema.v5.json`/v5 checker/`.gitattributes` = **51**；`frozen_set_composition` 显式记录；证据工具记入 `evidence_tools[]` 而非 normative；新增 N16/N17），并统一 `equivalence` 枚举为 `v4_exact/crlf_only/unproven_new_baseline/v5_own`（证据 JSON 同步重生成）、把旧目录 mtime 改为 UTC、不再在正文写死 tracked 数（G2–G4）。
- 本轮只写 v5 目录文档：未改协议语义、未生成正式 manifest、未运行旧 checker、未触碰 worker/配置/数据库/任务。

> 2026-09-06文档同步记录：只更新本目录活动README及三件套的跨计划路由，baseline54份/import manifest/reviews保持原字节；没有新增正式plan_manifest，没有推进V5-1/2/3或实施worker。当前统一依赖见[整改总计划](../painpoint-outcome-audit-2026-09-05/remediation-plan.md)。

## 2026-09-03：用户授权退役旧 v1–v4 目录（已完成）

- 用户明确要求v5启用后删除原v1–v4计划。本轮精确候选仅为平行旧目录
  `docs/plans/source-catalog-worker-recovery-2026-08-22/`；保留v5及其已核验基线、原调查报告，
  不碰源码/配置/主线计划/worker。
- 正在做路径、reparse、逐文件副本和引用预检；计划优先移入Windows回收站，不执行不可恢复擦除。
- 首次库存核对fail closed：旧目录现有54个文件，导入manifest映射旧目录文件为53个。尚未删除，
  下一步只读定位额外文件及其来源，不能直接跳过数量差异。
- 已派独立agent进行删除范围与副本完整性预检；只有范围明确、所有内容有可恢复保障后才执行。
- 差异已定位为`__pycache__/plan_consistency_check.cpython-313.pyc`（88831 bytes，SHA-256
  `43400901a8c84470a3cb70ed220eb4382249d5b2a2eed4537cf39d1ba208f669`）；它是生成缓存，不是新增
  计划正文。53份计划/审查文件均在v5有精确副本，缓存明确列为`DERIVED_CACHE_RECYCLE_ONLY`，
  随完整旧目录进入回收站，不永久擦除，也不改导入manifest/已核验baseline来塞入缓存。
- 独立预检确认v5校验器只读取新目录，旧source路径只是历史字段；移除旧目录不会破坏校验器。
  初次BLOCK仅因53/54副本差异，已明确上述生成缓存例外并提交复核。
- 已保存精确54文件清单、hash/size、53份v5副本映射与缓存例外至
  `reviews/old-plan-retirement-inventory.json`；清单状态PREPARED_NOT_EXECUTED，不表示已经删除。
- 独立reviewer复核后返回SAFE_TO_RECYCLE，关闭唯一缓存BLOCK；库存SHA-256为
  `68a039b59dee1a8ad452c0214166f75b10254bb5194da705f4d4bd4642d3632b`。
- 已执行严格路径/54文件hash副本再核验后的Windows SendToRecycleBin；API成功、旧路径absent，
  回收站同名目录及原位置匹配已确认。没有改为永久擦除，没有清空回收站。
- 删除后verify_import.py仍54/54 PASS；原报告及v5 import manifest hash未变。38个原tracked文件
  在Git呈删除状态，没有代用户stage/commit；v5仍独立保留。
- 已更新README/task_plan/findings并新增`reviews/old-plan-retirement-result.md`，明确v5是唯一活动
  目录，历史source路径无需存在。本节早先PREPARED清单保留原样，实际结果以该result记录为准。
- 本次未改项目实现、生产配置/数据库、主线计划、Git设置/hook或worker；下一步仍为V5-1版本合同。

## 2026-09-03：新目录创建

- 已读取 planning-with-files 技能全文。
- 已确认新目录不存在、没有 tracked 路径；仅创建本目录的 README、task_plan、findings、progress
  和局部 .gitattributes。
- 当前：V5_BASELINE_IMPORT_IN_PROGRESS；尚未复制基线，尚未创建正式 v5 manifest。
- 下一步：精确名单复制、前后 raw hash 验证、保存导入清单、独立只读导入审查。
- 原 v4、项目实现、生产配置、数据库、主线计划、Git 设置/hook 和 worker 均不改动。

## 2026-09-03：导入完成，独立复核待完成

- 已逐字节复制54份明确文件，无递归目录复制或旧文件移动；所有源前/源后/副本SHA-256相等。
- 固定导入manifest SHA-256：`da7d116e8c692d6311411c7390bec4278b59666a771823672f53e9b0f6567e4a`。
- 已添加仅访问新目录文件的verify_import.py；两次运行均54/54 PASS，明确输出IMPORT_ONLY。
- 61路径/244项有效Git属性全部unset，tracked=0；未运行git add/commit/stash/checkout/hook。
- 更新README的一次多文件patch因无关末尾上下文不匹配而整体拒绝；只读确认没有部分写入后
  缩小上下文重试成功。后续校验通过。
- 当前阶段：V5_BASELINE_CAPTURED / IMPORT_REVIEW_PENDING；正式v5版本迁移和三路复审尚未开始。
- 下一步：独立agent核验同一导入manifest、54份副本、只读检查器、原目录边界与活动/历史标记。

## 2026-09-03：V5-0完成

- 额外20项纯内存helper检查通过：有效/非法路径、类型错误和duplicate JSON；没有fixture或生产写入。
- 独立reviewer `/root/v4_test_dag_review`完成54/54副本、54/54当前来源、路径/reparse、精确集合、
  旧manifest对应、属性/未跟踪状态与检查器核验，返回唯一`IMPORT_REVIEW_PASS`。
- 已保存`reviews/import-review-2026-09-03.md`，同一reviewer回读后返回`FAITHFUL`，报告SHA-256为
  `baa64f7b4749c13b4f8188e4982a9e3fa907f692e776c37014f4dd2e57490e43`；确认后不再修改该报告。
- V5-0标记completed；当前为`V5_BASELINE_READY / VERSION_CONTRACT_PENDING`。V5-1/V5-2尚未开始，
  没有正式plan_manifest.v5.json，没有三路正式技术审查PASS，更没有实施或worker恢复授权。
- 本轮写入全部在新v5目录；原v4目录/manifest/报告、项目源码/配置/数据库、主线计划与worker不动。
- 下一次从本目录README→task_plan→findings→progress恢复；先运行verify_import.py，再进入V5-1。
