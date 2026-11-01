# Q01 r5 — CWP wire 修复 READY，待 ROOT 独审 / RF 同步，然后暂停

2026-11-01。R4 独审 41P / 后续独审的有界工程 PASS 保留为历史；**真实 H1 current-v2 在公有 handler 序列化发现新集成缺陷后，A 整合结论已重开，不能再以纯 selector 绿宣称该集成节点闭合。** 本线现仅完成 CWP 修复和隔离 handler 合同验证，尚待 ROOT 收取 RF 端同步、独审及最终发布。不重跑 H1、真实摘要、付费模型或 RF 主流程；遵守用户“手头工作做完先暂停”。

## 为什么之前没有发现

R4 的实际 `select_narrative_evidence` 公有函数测试跨过了原文来源处理/选择，却没有跨过 `NarrativeSelectHandler → NarrativeSelectResult.from_dict` 的严格输出 wire 边界。producer 新增 `reading_context.source_processing_complete`，但该边界仍有旧字段精确白名单，导致正常 H1 在发出模型请求前约23.17s就失败。

同根检查还发现：修完 bool 字段后，新 source-readability 诊断仍会失败，因 `known_unit_ids/count/limited` 不在 diagnostic 白名单，producer 也缺其必需 dimension。不能只让正常文档过而留着能力失败路径的下一处合同错误。

## 本次实现

1. DU 共享 wire owner `document_understanding/reading_context_contract.py` 定义：
   - `READING_CONTEXT_CONTRACT_FEATURE_VERSION = reading-context-wire/1.1`；
   - `source_processing_complete` **只在当前 `du-production-reading/4` 可选**；存在必须 `type(value) is bool`，null/0/1/string/array/object 均拒绝；
   - 历史无字段的记录原样接受/返回，**不补默认 True**；旧 schema1/2/3 不能携带这个新字段；
   - source-readability 诊断代码、dimension、16-ID sample bound 在共享 owner 声明。
2. `automation/narrative_contracts.py` 的 `_reading_context` 明确接入该字段及 validator；没有丢字段、改成任意属性或解除 unknown-fields 拒绝。
3. 同一合同的 `_selection_diagnostic` 明确接受 source-readability 的精确 shape（下节），同时沿用 canonical narrative-unit ID 和 count/limited 的严格校验。旧预算类诊断各自的精确 shape 保持。
4. producer `narrative_reading.py` 补 `dimension=source_readability`，sample bound/dimension 使用共享 owner 声明，不重写选择/收费/准入策略。
5. `narrative_decision_inventory._versions` 定点新增 `reading_context_contract` feature 身份。共享模块本来就在 reading recipe 的实际算法字节闭包内；集成测试检查显式 feature 及该实际依赖成员。

没有更改 `NarrativeSelectHandler` 的处理算法或 catch 行为；让它输出的真实合法数据通过其既有合同，而不是绕过合同。

## 给 RF 的准确同步接口

RF 存在独立便携消费者合同：

`revenue-forecast/scripts/company_wiki_narrative_contracts.py::_reading_context`（约850行）及 `_selection_diagnostic`（约784行）。ROOT 已安排 `/root/rectify_recipe` 窄同步，本线没有跨目录改代码、安装技能或提交。

context 新字段规则见上节。诊断必须精确包含：

```text
{code, count, phase, dimension, external_model_cost,
 known_unit_ids, known_unit_count, known_unit_ids_limited}
```

- code 只接受 `source_grammar_unavailable` / `source_grammar_scope_limit` / `source_assessment_incomplete`。
- phase 和 dimension 都为 `source_readability`；`external_model_cost is False`。
- count 为正整数，不能用 bool 代替。
- known_unit_ids 最多16个，都是 `urn:company-wiki:narrative-unit:sha256:<64小写hex>`；不要求它们在已选 spans 内，因它们正是未处理来源的 ID。
- known_unit_count 是整数，至少1且不小于 sample 长度；limited 为严格 bool，必须等于 total 大于 sample 长度。
- CWP 新分支复用既有 `_trace_unit_ids`；未额外增加 sorted/duplicate 约束。任意其他代码或属性不能借此放宽。

RF现有测试入口：`tests/test_shared_reading_narrative_contract.py`、`tests/test_du11_narrative_citation_wire.py`。同步应继续测试旧无字段材料与错类型/unknown 反控，不将缺字段解释为已完成。

**实际 CWP handler golden**：`CWP-handler-processing-golden-r5.json`，67,411 B，SHA-256 `0bec092a852adacdbacf93806ff3ebf540925cd48c67e35d2acdefccdf9781ae`。`cases.complete/deferred` 各为完整 `NarrativeSelectResult.to_dict`，有真实 reading_context 和 spans，可由 RF 自有公开 bundle fixture 重签消费。它来自当前真实 handler/HTML normalizer/selector；只有 deferred 场景将 English tagger加载模拟为缺资源。source port 是隔离内存 VerifiedContent，数据为合成英文公司原话，无生产材料/私有路径。

该 golden **不是**带模型 summary 的 NarrativeBundle/read response，也没有伪造 public receipt；RF不能冒称它证明收费 summary/完整收入预测已跑通。

## SourceExport / CWP bundle 边界

- 原件 `source_contract/source_export_v2.py` 不承载 reading_context，未增投资/摘要语义到该底层合同，不需要改它。
- CWP 叙述发布/读取在 `automation/narrative_projection.py` 多处调用 `NarrativeBundle.from_dict`；该 Bundle 与 SelectResult 使用同一个 `automation.narrative_contracts._reading_context` 和 diagnostic validator，因此 CWP 此处没有第二份字段白名单要补。
- RF 是独立跨仓 wire 消费实现，需要前节的同步，不应通过导入 CWP 内部模块耦合两个工程。

## 测试和证据

新 `tests/integration/test_source_processing_handler_wire.py` 用隔离内存 HTML bytes / VerifiedContent source port，实际运行 normalizer、0.9.0 selector、NarrativeSelectHandler、NarrativeSelectResult 严格序列化和 roundtrip。没有 mock selector/contract，没有原公司或生产库。

- 修改前正常与 capability-deferred+健康typed段两个真实 handler 场景均 **INPUT_SCHEMA_INVALID / 2F /14.26s**。
- 修复后 **18P /24.95s**：2个真实 handler场景；6种非bool shape；旧缺字段原样往返及未知字段拒绝；旧schema3拒新字段；7种错误diagnostic shape/代码/未知字段；feature与实际recipe身份。
- Ruff（4源＋新集成测试）通过，mypy（4源）通过，diff-check通过。
- 没有重复88/100整组、没有真实 H1重试、没有模型/供应商网络请求。

可复跑（宿主 Python；CWP cwd）：

```text
PYTHONPATH=src;tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -B -X utf8 -m pytest -p pytest_asyncio.plugin tests/integration/test_source_processing_handler_wire.py -q -p no:cacheprovider
```

冻结文件及 golden SHA 在 `Q01-rework-r5-evidence.json`。grammar模型/依赖/资源字节、生产16M/112、原件、生产库/配置、费用账、Git索引和主PWF均未由本线改动。没有新下载或构建临时树；golden是小型合成wire留证，不复制原件。

## 当前交接 / 停点

- 本线：CWP R5修复和隔离 handler验证 READY；源代码冻结。
- ROOT：收取RF便携合同及定点安装同步、做最后独审/发布，更新主PWF并暂停。
- A整体整合：等待ROOT闭合R5；不能沿用R4历史PASS声称真实集成缺陷已全部验收。
- C真实H1/真实摘要/持久缓存恢复/RF采用：未因本次18绿被代签，留待用户恢复后按唯一final-source继续。

本线 STOP，不开展新的边缘任务。
