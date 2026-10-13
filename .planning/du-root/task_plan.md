# DU-ROOT: 文档理解升级并线

PLAN_ID: du-root
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/root/.planning
Owner: ROOT
Base SHA: 7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8
Branch: codex/du-root-integration-20261013

## Goal

按 implementation.md 第 4/5 步与 INTERFACES 第 6 节 ROOT 职责，把三条已实现 lane
（profiles / structure / benchmark）并成一条可用的生产路径：

- 生产结构适配：现有 parse/normalize units → du-input/1（保留 bbox/heading/DOM/table/role/column）
- route + structure → 候选与原子依赖包的统一编排
- 母 PWF 与 docs/ARCHITECTURE 状态更新
- B 跨层离线节点；C 真实数据节点证据

不并 master、不 push、不安装技能、不改 Dayu/IQS。

## ROOT 允许写

- `src/company_wiki/document_understanding/__init__.py`（上层，不含各包内部）
- 现有 parser/selector/summary/generation 的生产适配
- `docs/ARCHITECTURE*`、母 PWF（`docs/plans/document-understanding-2026-10-13/*`）
- `.planning/du-root/**`
- ROOT 自己的 tests

不允许覆盖 worker 在制文件；不改 profiles/structure/benchmark 包内部实现。

## 阶段

### Phase 1: 三包接收与核验 — Status: in_progress
- 读三份 handoff，核验 base、范围、测试、真实证据
- 确认三包可同时 import 且互不冲突

### Phase 2: 生产结构适配 adapter — Status: pending
- `observation_adapter.py`：现有 NarrativeUnit → du-input/1
- 保留 bbox/pdf_block/heading/DOM/table/role/column/language
- 补 DU-S-ADAPT-1..6：heading_level、column、表头/caption 独立单元、table_id
- 不重编 locator、不重算 SHA、不写盘

### Phase 3: 统一编排 — Status: pending
- route + build_structure → 候选与原子依赖包
- 现有否定/阶段规则接到 semantic unit
- 低价值 skip 只看 administrative_candidate

### Phase 4: B 跨层离线节点 — Status: pending
- 来源 → parse → route → structure → 精选 → summary stub，缓存/失败恢复
- 不向日常 CI 加真实网络/模型

### Phase 5: C 真实数据节点 — Status: pending
- 真实原件跑通；记录真实结果与未证明项
- 需要模型的部分按现有预算执行或明确 NOT_RUN

### Phase 6: 文档与母计划状态 — Status: pending
- 更新本计划 task_plan/progress/findings 与 ARCHITECTURE

## Next Step

核验三包 handoff 与测试状态，然后设计 adapter。

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| （暂无） | | |
