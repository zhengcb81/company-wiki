# N6-CANDIDATE: 唯一施工入口

本线目标/写集/接口/测试/交接只取 docs/implementation/handoffs/N6-CANDIDATE/INPUT_CARD.md（已与源仓最新卡同步，S07改为境内口径）。基线58b74d07dd4f8b589c134ef9060a689864a8c089（HEAD 81d4524为基线+启动文档提交，工作树干净），PLAN_ID=n6-candidates。MAIN拥有共享入口与总PWF。

## 目标（唯一队列）

1. 经营事实候选召回：assess_unit层用通用（非公司名单）经营对象+动作/状态规则补齐业务内容漏选，反例（纯损益/合计/融资总额/产品名纯财务表/目录承诺/空泛持续推进/孤立"是的"）保持落选。
2. 最小上下文：group层修复 `_has_initial_member` 阻断补全；补全只做同source/角色/语言/页/章节的句内片段（主语/后半句/数字/预计/尚未），不同组冲突不静默覆盖，整页/整视觉组不被吞进精选（复用1600/1200窗口）。
3. 邻接层结构边界：不跨source/语言/页连接，冲突不覆盖，QA问题与答复绝不同group_id，角色与源unit字节/locator不改。

## 独占写集

- 源码：`src/company_wiki/source_catalog/{narrative_candidates,narrative_context,narrative_group_candidates,narrative_neighbors}.py` + 新增私有 `n6_candidate_operating_facts.py`、`n6_candidate_completion.py`。
- 测试：`tests/unit/test_n6_candidate_recall.py`、`tests/unit/test_n6_context_boundaries.py`、`tests/integration/test_n6_candidate_pipeline.py`（夹具未用到，未创建）。
- 文档：本PWF + `docs/implementation/handoffs/N6-CANDIDATE/`。
- 禁写：narrative_evidence/document/pdf_groups/finalize/budget/routing、旧测试/golden/report、总PWF、配置/数据库/原件、其他worktree、CI。

## 阶段

| 阶段 | 状态 | Next Step |
|---|---|---|
| 阶段1 接口核对与TDD反例RED | complete | RED 18失败/12通过/3.24s，已记录 |
| 阶段2 本线实现（GREEN） | complete | GREEN 30通过/0.99s + ruff全绿；既有相关测试181全绿未改动 |
| 阶段3 集中验收/真实定位回放/交接 | complete | 真实14/14点候选层恢复、原件sha/size/mtime不变、HANDOFF已提交；推送按主检出门禁裁定执行（详见progress） |

## 决策记录

- 原因词汇：复用 specific_business_event / project_plan_or_status / current_industry_context / direct_capacity_constraint / new_product_commercialization_milestone / current_business_progress；新增仅 `quantified_operating_status`（预算按other降级）。
- 规则注入：不新增必填公共字段；CandidateRules/GroupCandidateRules 各新增可选 `operating_facts`（默认内置通用检测器）；ContextRules/NeighborRules 无新字段；1600/1200窗口常量收口在 n6_candidate_completion（单源复用）。
- 财务排除顺序：assess_unit先保守辨别经营事实（对象+动作/状态且含数字才豁免financial_table），不放行纯数字行。
- fact仅在baseline规则单独不选中时贡献reasons/score → 基线已命中候选的输出字节不变（零漂移）。
- 组内fact最小窗口（operating-fact:N，重叠窗口先合并）仅在非章节上下文组启用，避免拆散既有原子上下文组（旧测试 test_visual_context_groups_are_atomic… 的规范）。
- 真实样本：parse_pdf(table_pages=目标golden页) 针对性实读（区别于benchmark全表扫描），内联python执行，产出即删。

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| 无PYTHONPATH时import到源仓editable安装的company_wiki | 1 | 测试断言module __file__位于本worktree src；命令固定PYTHONPATH=$PWD/src |
| fact窗口把章节上下文组拆散→旧测试原子组断言失败 | 1 | `_special_ids(in_context=...)`：章节上下文组内禁用fact窗口，全成员仍整组入选 |
| 重叠最小fact窗口把同一事实拆进两个组 | 1 | `_merge_fact_windows` 合并重叠窗口为同一 selection group |
| heredoc中文/EOF导致python补丁脚本截断 | 2 | 改用Write工具整文件重写tmp脚本 |
