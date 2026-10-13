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
- STRUCTURE：已接收并合并（f35c5806/f8f456a3），47 测试绿
- PROFILES：子代理收尾中（C 节点 + handoff）
- BENCH：子代理收尾中（native 回放 + handoff）

### Phase 2: 生产结构适配 adapter — Status: complete
- `observation_adapter.build_observation`：NarrativeUnit → du-input/1
- 关闭 DU-S-ADAPT-2/4/6；DU-S-ADAPT-1 部分（编号标题可判，无编号需改 parser）

### Phase 3: 统一编排 — Status: complete
- `orchestration.build_dependency_packages`：structure → du-packages/1
- `selection_bridge.dependency_closure`：只增不减，保住必需上下文与否定
- 真实万润 QA 端到端验证：否定被保留

### Phase 4: B 跨层离线节点 — Status: complete
- `tests/unit/document_understanding_root/test_du_root_integration.py` 25 项合成
- 覆盖 adapter 纯函数性/确定性/locator 透传/表头识别/lane 判定/包边界

### Phase 5: C 真实数据节点 — Status: complete
- `test_du_root_real_samples.py` 10 项（-m real_data，bindings 驱动）
- 4 份真实原件：恒锋两期建设跨页保留、万润否定、名创双栏、中微季报
- 原件 SHA/mtime 未变；host-neutral（无硬编码路径）

### Phase 6: 文档与母计划状态 — Status: in_progress
- 更新本计划 progress/findings
- 更新母 PWF 与 docs/ARCHITECTURE

### Phase 7: 三包合并与最终验收 — Status: pending
- 合并 profiles/benchmark lane 到 ROOT
- 全量测试 + ruff
- 母计划状态收口

## Next Step

核验三包 handoff 与测试状态，然后设计 adapter。

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| （暂无） | | |
