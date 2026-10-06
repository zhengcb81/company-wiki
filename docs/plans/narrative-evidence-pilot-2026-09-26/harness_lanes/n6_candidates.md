# N6-CANDIDATE：经营事实候选与最小上下文

**ready，可以立即交给独立harness实施。** 这是较大的运行时质量改进包，和N6-BUDGET、N6-FOOTPRINT同时开工。只做本卡，不执行旧N5、总PWF里的其他施工；MAIN负责共享入口、版本与最终联调。

## 独立上下文/工作目录

- 源项目：company-wiki，`C:/Users/郑曾波/Projects/company-wiki`只读。
- **在此施工：`C:/Users/郑曾波/Projects/cwp-lanes-20261006/n6-candidates`**；已建立，分支`codex/n6-candidates`。
- 固定基线`58b74d07dd4f8b589c134ef9060a689864a8c089`，精确CI37528050044已成功/75秒。不再建第二工作树，不在源master施工，不merge最新main或另一外线。
- 独立PWF `.planning/n6-candidates/{task_plan,findings,progress}.md`，`PLAN_ID=n6-candidates`；已放启动草稿，启动时核HEAD/status。总计划仅背景，本卡为唯一队列。

项目只供应原文、精选证据/摘要与定位，不产投资研究。原件不丢、不要翻译。N5真实9类型/86点，现selector0.3.2 required12/33、744定位全部合法：主要问题是业务内容漏掉，而不是权限或SHA。当前`benchmarks/narrative_document_types`内旧/新报告与golden都是只读。

## 独占写集

仅改4个源文件：`src/company_wiki/source_catalog/narrative_candidates.py`、`narrative_context.py`、`narrative_group_candidates.py`、`narrative_neighbors.py`；可新增紧邻的私有`n6_candidate_*`模块。

仅新增测试：`tests/unit/test_n6_candidate_recall.py`、`test_n6_context_boundaries.py`、`tests/integration/test_n6_candidate_pipeline.py`；短夹具放`tests/fixtures/n6_candidate_context/`（合计≤256KiB）。本线文档仅独立PWF和`docs/implementation/handoffs/N6-CANDIDATE/`。

**不可写** narrative_evidence/document/pdf_groups/finalize/budget/routing、旧测试/golden/report、总PWF、配置/数据库/原件、其他worktree或仓库、安装skills、CI。需要共享改动写`main_wiring`，不跨界补代码。

## 冻结输入输出（不需新DTO）

保留现有调用签名与返回形状：

```python
assess_unit(unit: NarrativeUnit, rules: CandidateRules) -> CandidateAssessment
build_section_context(document_kind, groups, rules: ContextRules) -> SectionContext
enrich_context_groups(groups, *, initial_candidates, initial_group_ids,
                      project_scores, business_scores, rules: GroupCandidateRules) -> GroupEnrichmentResult
enrich_neighbor_context(units, *, initial_candidates, initial_group_ids,
                        rules: NeighborRules) -> NeighborEnrichmentResult
# 两线之间仍交换：
EvidenceCandidate(unit: NarrativeUnit, topics: tuple[str, ...], reasons: tuple[str, ...], score: int)
candidates: tuple[EvidenceCandidate, ...]
group_ids: Mapping[str, str]  # 原unit_id -> 原子事件组
```

NarrativeUnit没有source_sha256属性，source_id绑定原件SHA身份；保留原unit/坐标/文本，不拼造一个虚假的合并span。组必须同source、同角色、同语言且有连续事件关系；QA问题与答复绝不能同group_id（summary_input取首span角色）。unit_id唯一、组映射只指真实成员、输出确定性。预算线负责选整组，本线不改排序/96或160配额。

topics/reasons优先复用既有词汇（如specific_business_event、current_industry_context、project_plan_or_status、named_product_milestone_context、direct_capacity_constraint）。新reason只可向后兼容追加，并在handoff明确列出，预算未知reason按原other降级；不依赖另一外线已追加映射。Rules新增字段必须有安全默认值，现有构造继续有效；不得新增必填公共字段。

## 实施步骤（TDD先红后绿）

1. 读上述4模块及只读共享文件；结构问题先CodeGraph，可查源仓基线图；已知模块直接读。核实际签名，不照猜测路径造新体系。先将目标、写集、3个大阶段写本线PWF。
2. 先写候选正反例RED：已应用/客户验证/投用/产能、新产品第二曲线、并购扩展、行业需求/产销、募集项目用途/计划、IR海外与产品组合、英文“demand continues to exceed available capacity”。增加不同公司/行业合成表达，不能专有公司名名单匹配。
3. 反例包含纯损益行/合计数/融资总额、产品名+纯财务数表、目录/承诺、空泛持续推进、孤立“是的”。具体经营对象+动作/状态的定量内容不能先被financial_table吞掉；可在本层assess_unit保守辨别后再作财务排除，不泛化为所有数字行都留。
4. 最小上下文RED：已有一个块命中，后半句/主语/数字/“预计、尚未”仍必须补齐；当前group模块_has_initial_member可能让已有命中块反而阻止补全。不能跨页/章节/source/角色连接，现有不同组冲突不静默覆盖；复用现有1600/1200字符窗口，不能把整页/整视觉组吞进精选。
5. 实现通用规则/章节/邻接层修复。计划、预测、否定保留原文，不输出语义真值。IR答案保持公司角色，问题保持analyst/investor_question；源unit字节/locator不改。不要为本线测试绿调整其他线的配额或golden。

## 真实复现点与一次集中验收

只读实际原件的根：CWP `C:/Users/郑曾波/Projects/company-wiki`；ET `C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcripts`。样本相对路径/SHA从只读samples.json取；local配置放本线tmp或ignored文件，不写主仓。全部0下载/LLM/付费。

- S01 G01页32/G03页40，S02 G02/G03页18/G04页31，S03 G03页3：parsed完整但候选缺必要片段。
- S07 G01页1：海外营收占比；S08 G01页3：克重/一口价产品组合，不能因程序性标签整份skip。
- S09 G05行200/UTF8字节32538–32593：需求超产能；G01在正文marker前的provider摘要不当管理层原话。
- S04页34/49、S06页43：募集项目名称、用途、投产/产能；纯融资数额不能当业务进展。

Unit验上述规则、组完整/边界、身份/角色、遍历顺序稳定、冲突及原unit不变。Integration直接跑NarrativeUnit→assess→section/group→neighbor；用固定基线finalize做兼容烟测，断言候选/组，不要求预算线未来最终名次。针对性实读可只扫golden页的表，注明区别于全表/默认生产策略；不得把所有真实9样本长基准重跑放CI。

测试命令在本工作树执行：

```powershell
$env:PLAN_ID='n6-candidates'
$env:PYTHONPATH="$PWD/src"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:CW_BASETEMP_FALLBACK_ROOT="$PWD/tmp"
python -m pytest -p no:cacheprovider --basetemp tmp/n6ct tests/unit/test_n6_candidate_recall.py tests/unit/test_n6_context_boundaries.py tests/integration/test_n6_candidate_pipeline.py
python -m ruff check src/company_wiki/source_catalog/narrative_candidates.py src/company_wiki/source_catalog/narrative_context.py src/company_wiki/source_catalog/narrative_group_candidates.py src/company_wiki/source_catalog/narrative_neighbors.py tests/unit/test_n6_candidate_recall.py tests/unit/test_n6_context_boundaries.py tests/integration/test_n6_candidate_pipeline.py
```

只在收口做一次Unit/Integration与定位回放；短tmp先absent，finally关闭/删除副本或缓存，结束实际验证absent、原件SHA/size/mtime与源生产/配置保持。不用实际ACL修改作故障测试。不执行paid或生产批次。正式Worker→检索→RF E2E由MAIN在两线并入后做一次。

## 交接与MAIN接线

正常提交本线，推codex/n6-candidates；不推master。提交`docs/implementation/handoffs/N6-CANDIDATE/{HANDOFF.md,handoff.json}`，schema `cwp-independent-handoff/1`：lane_id、base_head、delivery_head（代码commit）、branch/worktree、changed_paths、RED与GREEN命令/数量/秒、接口与新增可选规则、main_wiring[]、real_samples[]、protection、cleanup、calls、remaining。

每个真实点记录golden_id/source SHA/locator/候选unit IDs/角色/组成员/理由和实际阶段结果。`main_wiring`逐项注明narrative_evidence.py::_candidate_rules、ContextRules/GroupCandidateRules/NeighborRules、_topics/_financial_table是否仍需注入、具体字段与调用示例。只给接线说明，不写共享文件。MAIN最终更新selector版本、接两线、一次9样本与正式E2E/精确CI；helper绿不代表完整业务质量已完成。

完成标准：本线通用规则/完整事件与反例通过、接口向后兼容、所有写集合法、真实定位可回放、根恢复、无外发；仍被MAIN旧规则注入限制的项写remaining，不假称全链已修。不增加人工签收；完整交付后MAIN集中接收。

启动草稿和本卡副本已放本线目录；它们是可提交的输入文档，不是未知WIP。自定义测试要核被测company_wiki模块来自本工作树src，避免测试到源master/全局安装版本。共享入口仍由MAIN写。

收口同时跑已存在的tests/unit/test_narrative_evidence.py及这4模块相关现有短测试。若旧断言与新经营事实规范冲突，列具体断言/输入/新旧期望到remaining并解释，不跳过、伪造绿灯或改旧文件；MAIN统一判断规范。交接状态区分helper已完成与仍需共享接线。
