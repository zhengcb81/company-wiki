# N6-CANDIDATE Handoff

schema `cwp-independent-handoff/1` · lane_id `n6-candidates` · branch `codex/n6-candidates`
base_head `58b74d07dd4f8b589c134ef9060a689864a8c089` · delivery_head `9a4b81518d7b966744fdcce9768c801686e83351`
worktree `C:/Users/郑曾波/Projects/cwp-lanes-20261006/n6-candidates` · 源仓只读未写

**状态：helper已完成**（本线测试全绿、接口向后兼容、真实定位可回放、根恢复、无外发）；**共享接线与最终质量门仍属MAIN**（详见 remaining）。机器可读明细见 `handoff.json`。

## 1. 交付内容

| 类别 | 路径 |
|---|---|
| 修改 | `src/company_wiki/source_catalog/narrative_candidates.py` |
| 修改 | `src/company_wiki/source_catalog/narrative_context.py` |
| 修改 | `src/company_wiki/source_catalog/narrative_group_candidates.py` |
| 修改 | `src/company_wiki/source_catalog/narrative_neighbors.py` |
| 新增 | `src/company_wiki/source_catalog/n6_candidate_operating_facts.py` |
| 新增 | `src/company_wiki/source_catalog/n6_candidate_completion.py` |
| 新增 | `tests/unit/test_n6_candidate_recall.py`、`tests/unit/test_n6_context_boundaries.py`、`tests/integration/test_n6_candidate_pipeline.py` |
| 同步 | `docs/implementation/handoffs/N6-CANDIDATE/INPUT_CARD.md`（S07境内口径） |
| 文档 | 本目录 + `.planning/n6-candidates/*` |

写集之外零改动；tmp一次性验证脚本/产物已删除；夹具目录未用到（无文件）。

## 2. 机制（都发生在本线4+2模块内，零共享文件改动）

1. **通用经营事实检测**（`n6_candidate_operating_facts`）：10个白话规则——已应用/投用/客户验证、产销量/产能状态、量化结构占比、第二曲线/增长引擎、并购（完成/拟）、行业需求产销变化、募集项目用途、启动建设项目+产能、需求超产能（中英）。无公司名单；只给原文打标，不输出语义真值（计划/预测/否定原样保留）。
2. **assess_unit**：先保守辨别（对象+动作/状态且含数字才豁免`financial_table`），再作财务排除——纯损益行/合计/融资总额/产品名纯财务表仍drop；fact只在注入规则单独选不中时贡献reasons/score → 基线已命中候选输出零漂移；`_pre_signal`补入certification信号（修S05-02类topics空早退）。
3. **组补全**：已有命中块时按句界补全主语/后半句/数字/预计/尚未（`completion_indices`，同source/角色/语言/页、≤8单位、标题/目录为屏障），替换旧`_has_initial_member`整组阻断；`assign_group`冲突不覆盖；非同质组不共享group_id。
4. **fact最小窗口**（`:operating-fact:N`，复用`window_finder`，重叠窗口先合并）：修复"同一句话被拆进两个视觉块"（S01-03类）；仅在**非章节上下文组**启用，不拆散既有原子上下文组（守旧测试原子规范）。
5. **窗口有界**：`narrative_context`窗口改为"整组放得下才计入"，1600/1200常量单源收口；组成员入组累计字符受同一窗口约束，整页视觉组不可吞入。
6. **邻接层**：`_unit_by_location`键加source_id，前块/续块校验language；冲突跳过；linked question仍不带group_id、角色不动。

## 3. RED → GREEN

```powershell
$env:PLAN_ID='n6-candidates'; $env:PYTHONPATH="$PWD/src"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; $env:CW_BASETEMP_FALLBACK_ROOT="$PWD/tmp"
python -m pytest -p no:cacheprovider --basetemp tmp/n6ct tests/unit/test_n6_candidate_recall.py tests/unit/test_n6_context_boundaries.py tests/integration/test_n6_candidate_pipeline.py
```

- RED（实现前，同命令）：**18 failed / 12 passed / 3.24s**
- GREEN（实现后，同命令）：**30 passed / 0.99s**
- ruff（卡原文文件清单）：**All checks passed**；pre-commit mypy contract 钩子通过（修正completion anchor一处类型标注）。
- 既有相关短测试（**未改动**）：`test_narrative_evidence` + `test_narrative_selection_architecture` + `test_narrative_english_business_recall` + `english_operations` + `pdf_bytes` + `retrieval` + `select_handler` + `verify_handler` = **181 passed**；含新测试合计 **211 passed / 2.91s**。**旧断言冲突：无。**

## 4. 接口与新增可选规则

- 四个公开签名、`EvidenceCandidate`/`candidates`/`group_ids` 形状**全部不变**；所有现有构造为关键字且无必填新字段。
- 新增可选字段（安全默认=内置检测器）：`CandidateRules.operating_facts`、`GroupCandidateRules.operating_facts`。`ContextRules`/`NeighborRules` 无新字段。
- 新增原因（向后兼容追加）：**`quantified_operating_status`**（预算未知reason按other降级）。其余均复用既有词汇。新selection group id形态 `{group}:operating-fact:{i}`（与`:certification-timeline:`同族）。

## 5. main_wiring（逐项，只给说明）

1. `narrative_evidence.py::_candidate_rules` — **无需改**：topics/financial_table/全部信号模式照旧注入；`operating_facts`默认已生效，可显式传`detect_operating_fact`增加可见性。
2. `_topics`/`_financial_table` — **仍需注入**：financial_table仍是主排除器；本线仅在assess_unit内对"具体经营对象+动作/状态+数字"行保守豁免，纯财务行照旧drop。
3. `select_narrative_evidence` 内 ContextRules/GroupCandidateRules/NeighborRules 构造 — **无需改**：`window_finder`现同时被fact窗口复用（同一已注入字段）；NeighborRules无新字段。
4. `narrative_budget.py::_REASON_PRIORITY/_REASON_CATEGORY` — **可选**：为`quantified_operating_status`加映射；不加则按other（第7档）运行，无功能影响。
5. `NARRATIVE_SELECTOR_VERSION` — **必须升版**（仍0.3.2，narrative_evidence本线不可写），避免复用旧选择结果。
6. 合并后MAIN执行：两线并入 → 9样本benchmark → 精确CI37528050044 → Worker→检索→RF正式E2E各一次。**helper绿≠完整业务质量完成。**

## 6. 真实样本回放（14/14候选层恢复）

方法：只读根 CWP/ET；先按samples.json核SHA，`parse_pdf(table_pages=目标golden页)`（**针对性实读，区别于benchmark的full_table_scan**）/ `parse_transcript_text` → `select_narrative_evidence`全管线；逐点记录golden_id/SHA/locator/unit IDs/角色/组成员/理由/阶段（完整数据在`handoff.json::real_samples`）。

| 点 | locator | 候选层 | 进入96/160预算 | 关键证据 |
|---|---|---|---|---|
| S01 G-S01-01 | p32 | ✓×2 | ✓ | 已应用于3纳米产线 / 批量销售，specific_business_event |
| S01 G-S01-03 | p40 | ✓×2 | ✗ | 拟购买控股权跨两块 → `operating-fact:4`同组，project_plan_or_status |
| S02 G-S02-02 | p18 | ✓ | ✓ | 销售额有望提高至1300亿美元，current_industry_context（基线MISS→init） |
| S02 G-S02-03 | p18 | ✓ | ✓ | 已应用在国际一线客户产线，specific_business_event（基线MISS→init） |
| S02 G-S02-04 | p31 | ✓×2 | ✓ | 主语块+已投入使用/产能大幅提升（fact+补全），同组 |
| S03 G-S03-03 | p3 | ✓ | ✓ | 薄膜设备营收+新引擎，quantified_operating_status（基线MISS→init） |
| S04 G-S04-03 | p34 | ✓ | ✗ | 募集资金投资于以下项目，project_plan_or_status（fact窗口） |
| S04 G-S04-04 | p49 | ✓×2 | ✗ | 拟用于…项目+续块补全，project_plan_or_status |
| S06 G-S06-02 | p43 | ✓×2 | ✗ | 拟投资于生产线建设项目+续块 |
| S06 G-S06-03 | p43 | ✓×3 | ✗ | 达产新增50万件/140万支+续块 |
| S07 G-S07-01 | p1 | ✓ | ✓ | **境内**收入8.19亿/占比22%（management单元），topics=core_business、无overseas；qa_text_shadow副本正确排除 |
| S08 G-S08-01 | p3 | ✓ | ✓ | 克重/一口价占比，quantified_operating_status；程序性标签未致整份skip |
| S09 G-S09-01 | line30(marker前) | n/a | n/a | provider摘要bytes991-1118**未被解析成任何unit**→不可能成管理层原话；见remaining |
| S09 G-S09-05 | line200 | ✓ | ✓ | "Customer demand continues to exceed available capacity."，direct_capacity_constraint+management（基线MISS→init） |

9/14同时进入预算选择；未进者为96/160配额内排序（预算线领域，按卡不断言）。8份原件终检sha256/byte_size/mtime_ns全部不变（S05未跑也核过）。

## 7. protection / cleanup

- 0下载/0LLM/0付费；无ACL测试；无配置/数据库写入；golden/samples/report只读；未动其他worktree/skills/CI。
- tmp一次性脚本与JSON已删除；pytest basetemp各次运行由fixture hook清理并验证absent；原件无副本。

## 8. remaining（不假称全链已修）

1. **G-S06-01 纯融资总额**按卡反例故意不成候选；若benchmark仍要求"发行规模"，由MAIN/预算线裁决归属规则。
2. **G-S09-03/04 收入指引**不在本卡目标清单，基线仍MISS（未扩 scope）。
3. **G-S09-01 marker前provider摘要**：解析起点在narrative_evidence（本线不可写），文本根本不会被解析——"不当管理层原话"由不解析满足；若要选中该文本需MAIN/parser决策。
4. 5/14点为候选但不在96/160预算内（S01-03、S04-03/04、S06-02/03）——最终名次归预算线。
5. S07/S08 `status=needs_review` 来自parser声明的`locator_unstable`质量标记（表格单元span），narrative_document/evidence不可写。
6. 升selector版本、9样本benchmark、精确CI、正式E2E：MAIN合并期执行。
7. `quantified_operating_status`的预算映射可选（当前按other降级，已文档化）。

**未修改任何旧测试/旧断言；无需要MAIN裁决的规范冲突。**
