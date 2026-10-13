# DU-STRUCTURE: 跨页章节与语义单元

PLAN_ID: du-structure
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/structure/.planning
Owner: DU-STRUCTURE lane
Base SHA: 7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8
Branch: codex/du-structure-20261013

## Goal

实现纯函数 `build_structure(observation, *, limits=None) -> dict`，把 du-input/1 的既有 locator 单位
组织成 sections / 六类 semantic_units / relations / coverage / diagnostics，输出 du-structure/1。
不改生产解析器、不重做 PDF 读取、不接 LLM、不导入 profiles 包。W04 句子/主体完整性不得破坏。

## 独占范围

- `src/company_wiki/document_understanding/structure/**`
- `tests/unit/document_understanding_structure/**`
- `tests/fixtures/document_understanding_structure/**`
- `.planning/du-structure/**`

不创建父包 `document_understanding/__init__.py`；不改 profiles/benchmark/source_catalog/document_normalization。
parser 缺 heading/bbox/table 字段时记录 ROOT 适配需求，不越界改 parser。

## 阶段

### Phase 1: 契约冻结与 RED — Status: complete

- 冻结 du-input/1 → du-structure/1 夹具（合成，纯 JSON）：8 份输入
- RED 反例全部落地并通过：目录与正文同标题；p62 末项目建设期续 63；两项目相邻；
  一个项目多小节；双语双栏；题目在前页答案在后页；业务表单位/年份/脚注；扫描缺页；
  人工 bad layout
- 已锁住跨页/角色/单位完整性（22 项）

### Phase 2: 章节栈与正文序列 — Status: complete

- 章节栈、父子层级、body 序列、TOC/重复页眉排除为 furniture
- 跨页延续有上限（MAX_CONTINUATION_PAGES=2 / MAX_CONTINUATION_UNITS=24）
- 遇新同级 heading 停止；不因换页清空上下文

### Phase 3: 六类语义单元与关系 — Status: complete

- project / qa_exchange / operating_table / paragraph_event / risk / background
- QA 保留否定与跨页问句尾巴；未答问题标 partial + ANSWER_MISSING
- relations 6 类，去重、存在性校验、依赖环检测

### Phase 4: 语言 lane — Status: complete

- layout.column 左右栏 + DOM 同父路径两种证据
- 仅当语言不同且结构对齐才输出 language_parallel；不翻译、不删 unit

### Phase 5: 预算、partial、deferred — Status: complete

- max_group_members 超限保留成员 + partial + GROUP_BUDGET_EXCEEDED
- 缺页/opaque/deferred 页 → complete=False 且 diagnostics 说明
- complete 仅表示构建过程完成

### Phase 6: B 节点 — Status: complete

- 45 项测试通过；纯函数不修改 input；相同输入相同输出
- 规模趋势 1k/10k/50k 记录；log-log 斜率 1.14（近线性）
- 人工 bad layout 降到 low（LAYOUT_INCONSISTENT），不再硬标 high

### Phase 7: C 节点 — Status: in_progress

- 名创双栏、恒锋跨页、万润 QA 少量真实规范化单位复核
- 保留来源 locators，摘录 ≤8KiB/文档，不复制原件
- 交接范围检查

### Phase 8: 交接 — Status: pending

- `.planning/du-structure/handoff.{md,json}` 按 INTERFACES 第 7 节
- 提交本分支，不并主线

## 命令

- `python -X utf8 -m pytest tests/unit/document_understanding_structure -q`
- 本包 ruff

## Next Step

C 节点：用三份真实规范化单位（名创双栏 / 恒锋跨页 / 万润 QA）复核结构，保留 locators，不复制原件。

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| A 夹具 `qa_question_page_then_answer_page` 中 q2 未识别为问句尾巴 | 1 | 先判 `_tail_open` 再做新问句判定，跨页未完结问句保留尾巴 |
| `a3`/`a5` 子小节被当成新项目 | 1 | 引入 `_starts_new_project`：heading 深于当前项目则为子小节 |
| `question_answer` 关系被误判为环 | 1 | 环判定方向写反；改为「to 是否已可达 from」 |
| bad layout 仍标 high | 1 | 增加 `layout_inconsistent` 证据与 `LAYOUT_INCONSISTENT`，降到 low |
| 规模夹具 10k→50k 耗时 38×（O(n²)） | 1 | `_layout_inconsistency`/`_dominant_language` 每 section 重建全量索引；改为单次 by_id |
| 同上（第二处） | 2 | 脚注关系对每个脚注扫描全部 units；改为按页预索引 |
