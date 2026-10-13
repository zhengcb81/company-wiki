# Task Plan: DU2-FACETS 业务关注点、经营机制和必要上下文

PLAN_ID=du2-facets；PWF_PLAN_ROOT=<本worktree>/.planning。
base_sha=5a297244549d54c34f382835b876ec3d181fcd24（分支 codex/du2-facets-20261013）。
卡片：docs/plans/document-understanding-2026-10-13/review/cards/DU2-FACETS.md

## Goal

产出各类文档共用的业务语义数据策略（du2-facet-spec/1 + du2-reading-case/1）：八个共用面、
四类可组合经营模式、两份A级语义规格（第二曲线阶段、产能项目）及其正反配对case与结构不变量
测试；不做投资模型、不代替revenue-forecast、不抽全套财务报表、不调用LLM生产答案。

## Next Step

已交接，本lane停止；后续由 ROOT 按 handoff 的 next_root_action 接收（本包不再改动）。

## Current Phase

Phase 5（验证与交接）

## Phases

### Phase 0: 规格阅读与真实锚点核实

- [x] 读 AGENTS.md 职责边界、review/report.md、strategy_matrix.md、INTERFACES.md、sample_manifest
- [x] 确认工作目录/分支/独占路径；base_sha 记录
- [x] 核对5个真实锚点原件存在且 SHA 与 sample_manifest 一致（恒锋/金禾/万润/名创/微软）
- [x] C节点引文逐条对照原文（fitz/文本规范化匹配），21条全部命中
- **Status:** complete

### Phase 1: A 语义规格（第二曲线阶段、产能项目）

- [x] records/semantic_stage_progression.json（第二曲线阶段语义规格+反例引用）
- [x] records/semantic_capacity_project.json（产能项目语义规格+反例引用）
- [x] 合法空值规则并入 absence_rules
- **Status:** complete

### Phase 2: 结构不变量测试（RED先行）

- [x] tests/：记录schema/枚举/条件式required_context/支持组/引用/引文预算/机制不覆盖
- [x] 先跑 pytest 记录 RED（308 failed / 3 passed，空包防线生效）
- **Status:** complete

### Phase 3: B 八面+四机制+cases

- [x] records/：八个共用面 facet_*.json
- [x] records/：四类机制 mechanism_*.json（只写通用机制，无公司产品名单）
- [x] cases/：6个真实锚点 case + 合成正反配对 case（含语义反例 NOT_RUN_ROOT_INTEGRATION）
- [x] cases/：低信息/无业务/无回答合法退出例 + 纯财务 correctness_if_emitted 例
- **Status:** complete

### Phase 4: 汇总交付

- [x] index.json（du2-facet-index/1）、coverage_matrix.md、acquisition_requests.json
- [x] c_verification/real_excerpt_checks.json（人工对照原文记录单列）
- [x] README.md
- **Status:** complete

### Phase 5: 验证与交接

- [x] GREEN：python -B -X utf8 -m pytest .../facets/tests -q（311 passed）
- [x] 资源核算（0模型/0付费/196,871B持久）、scratch 清理恢复、git status 可解释
- [x] handoff.json + handoff.md，正常提交本分支，不并主线
- **Status:** complete

## Decisions Made

- 语义反例（缺否定/错项目/未来当实际）只交输入与期望给 ROOT，execution_status=NOT_RUN_ROOT_INTEGRATION。
- required_context 全部条件式（always_for_assertion / quantity_emitted / project_emitted /
  explicit_condition_present），数量断言才要求 unit/denominator，定性进度不强制补数字。
- 真实 case 引用 sample_id+sha+local_binding_key，locator=null 时用页码+exact_quote 供 ROOT 解析。
- 机制记录 applicable_mechanisms 两两不交叠作为“组合不互相覆盖”的结构代理断言。

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| PowerShell ConvertFrom-Json 拒绝 sample_manifest 的转义 | 1 | 改用 python -B -X utf8 解析 |
| GzipStream 构造在受限 PS 下失败 | 1 | 改用 python gzip 模块读取 sample_observations |
| 引文探针 "to \$678 billion" MISS | 1 | shell 转义残留反斜杠所致；原文措辞本身逐字命中，正式校验21/21 |
