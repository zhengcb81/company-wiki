# N6-BUDGET：固定配额的整组去重与业务选材

**ready，可以立即独立实施，与N6-CANDIDATE/N6-FOOTPRINT并行。** 这是较大的确定性选择策略改进；只负责候选之后的去重/预算/打包，不改候选、parser、权限或模型。

## 工作目录与固定上下文

源项目company-wiki；源master `C:/Users/郑曾波/Projects/company-wiki`只读。**施工目录`C:/Users/郑曾波/Projects/cwp-lanes-20261006/n6-budget`**已建立，分支codex/n6-budget，基线`58b74d07dd4f8b589c134ef9060a689864a8c089`，CI37528050044已绿75秒。不建第二worktree、不合最新main或其他外线。PWF仅`.planning/n6-budget/`三文件，PLAN_ID=n6-budget；启动核HEAD/status，其他总计划/历史卡不成为本线任务。

真实DOCSET：9类型/86点、744定位全回放、12/33 required。S05重复24/160、S06重复14/160。限定表页诊断S01 G02/G05、S05 G03、S06 G02/G03已经进入候选，但最终未选；不能单纯扩大96/160限额。源原件不丢、同语言、无投资结论。候选/分组接口已经固定，不需等待另一条线完工。

## 唯一写集

- `src/company_wiki/source_catalog/narrative_finalize.py`、`narrative_budget.py`；可新增私有`n6_budget_*`模块。
- 新`tests/unit/test_n6_budget_selection.py`、`test_n6_group_dedup.py`、`tests/integration/test_n6_budget_packages.py`；短夹具`tests/fixtures/n6_budget/`≤256KiB。
- 本线PWF与`docs/implementation/handoffs/N6-BUDGET/`。

不改narrative_evidence/document/routing/candidates/context/group_candidates/neighbors/pdf_groups、旧测试、benchmark/golden/report、配置/原件/数据库、CI或外仓。本线不改_source reader公共合同、selector版本或summary模型。

## 接口与边界

```python
EvidenceCandidate(unit, topics: tuple[str, ...], reasons: tuple[str, ...], score: int)
group_ids: Mapping[str, str]  # unit_id -> 原子事件group_id
BudgetItem(item_id, group_id, page_key, locator, order_key, reasons,
           score, is_heading, payload)
select_budget_items(items: tuple[BudgetItem, ...], *, limit: int) -> tuple[BudgetItem, ...]
finalize_selection(structure, route, candidates, *, group_ids,
                   heading_pattern, dropped_financial_count) -> NarrativeEvidencePackage
```

保留签名/返回形状、原source_id与source_sha256、真实unit/locator；输出按既有坐标稳定排序，数值计数有真实定义。候选线只提供更完整组，本线不能拆必要事件组；组成本是实际span数，limit硬上限不变。未知reason仍可按other降级，不新增必填字段，不依赖另一线额外schema。新增映射由handoff列明给MAIN接线。

## TDD与实施步骤

1. 读两个源模块和只读NarrativeUnit/DocumentRoute/candidate接口，先写本线3阶段PWF与RED。当前_deduplicate按text+page+role，只消同页重复；预算有特定reserved reason与按page/category轮转，不能凭感觉全推翻。
2. RED：同一经营事件跨章节重复不能挤占多个配额；精确重复与空白/表格分隔差异；相似但不同项目/期间/公司/角色/否定的句子不能误并；整组事件不可只保留一半；去重后group_ids不悬空或错误合组。优先按整个事件组的内容/上下文去重，无法证明同事件则保守保留。不能全库按文本SHA删原件。
3. RED：96/160限额内具体产品验证、产能/募投、行业需求都可被保留，高频泛化风险/承诺不能占满；同分、输入顺序变化稳定；超大组放不下完整舍弃并诊断、limit非法报错；预算算法只使用当前输入，不再去读磁盘/模型。
4. 实现安全去重与业务组优先/多样性选材。公司答复与提问不可共用group_id；保留业务条件/否定原文，canonical成员始终有真实定位。源版本事实不变，不引入第二份正文或第二任务库。
5. 保留当前source-only Package状态含义（partial/needs_review不需人工签收）；omitted/dedup/candidate等计数不能为好看瞒删。_status职责与IR是否整份可skip由MAIN处理，本线不改空结果政策。不自动扩限额、改golden/阈值或公共合同。

## 一次集中测试与真实材料

Unit用合成NarrativeUnit/EvidenceCandidate及冻结接口，断言最小limit/事件组、跨页重复/不同事件、角色、稳定性、cap与计数。Integration直接finalize_selection→Package→summary_input，回放真实短原文组，检查分组/角色/定位；不依赖另一线未来候选数或断言它的排名。可从只读MAIN样本S01页40/75、S05页101、S06页43建立小候选fixture，source/locator须来自真实原件，明确是否手工候选而非生产parser；保持SHA。

```powershell
$env:PLAN_ID='n6-budget'
$env:PYTHONPATH="$PWD/src"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:CW_BASETEMP_FALLBACK_ROOT="$PWD/tmp"
python -m pytest -p no:cacheprovider --basetemp tmp/n6bt tests/unit/test_n6_budget_selection.py tests/unit/test_n6_group_dedup.py tests/integration/test_n6_budget_packages.py
python -m ruff check src/company_wiki/source_catalog/narrative_finalize.py src/company_wiki/source_catalog/narrative_budget.py tests/unit/test_n6_budget_selection.py tests/unit/test_n6_group_dedup.py tests/integration/test_n6_budget_packages.py
```

真实根只读：CWP源仓companies原件，路径/SHA从只读samples.json。0下载/LLM/费用，无生产批次。临时根先absent/finally恢复absent，原件/源配置不变；不用真实ACL或完整大备份演练。只在本线收口做一次集中节点，MAIN合两线后才跑一次9样本与正式Worker→检索→RF E2E。不要把长真实数据测试加日常CI。

## 交接

正常提交与推codex/n6-budget，不推master。交HANDOFF.md/handoff.json（schema cwp-independent-handoff/1）：lane_id、base_head、delivery_head（代码）、branch/worktree、精确changed_paths、RED/最终GREEN命令/数量/秒、接口兼容、选择/去重的理由、real_vs_fixture、protection/cleanup/calls、main_wiring/remaining。给每个示例去重前后组/成员/成本、丢弃原因和来源locator，报告≤256KiB，不交大全文/数据库。

完成标准：确定性纯预算算法、整组完整性/固定cap/保守去重/角色与计数全部过，真实定位保持，写集无越界，原件不改和tmp恢复；不以更大配额或另一条线代码获得绿灯。MAIN接线版本与最终业务覆盖归总由MAIN负责；无需逐helper人工签收。

启动PWF和本卡副本已放本工作树，status里这些新文档是可解释输入，可随本线提交。自定义测试核模块来自本树src，避免跑到源master或全局安装版本。

收口同时跑tests/unit/test_narrative_evidence.py与预算/去重相关现有短测试。旧断言若确与新规范冲突，列具体输入/断言/新旧期望给MAIN，不改旧测试或假报通过。原artifact的旧evidence_id/locator必须可读；本线不更改身份生成或旧事实，最终跨版本读/回放由MAIN验证。
