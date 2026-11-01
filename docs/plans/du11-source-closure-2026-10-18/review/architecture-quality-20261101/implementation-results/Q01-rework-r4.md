# Q01 r4 — READY，来源能力未知沿公有选择链保留

2026-11-01；接续 `independent-A-r3.md` 的新 P2。**保留 r3 独审 41P 及其 P2 未签收历史，不将旧绿项冒作本次修复验收。** 源码/测试身份见 `Q01-rework-r4-evidence.json`。本线已冻结，等待 ROOT 定点独审；没有恢复真实摘要/RF C。

## 根因

独审精确复现的同一原话：

`Our vessels transport liquefied gas between coastal terminals. Net income was $20 million.`

正常 grammar 可用时为 mixed support，真实 public selector 选出1 span。只 mock `_english_tagger` 为缺资源后，原 `prepare_source_passage` 的 `finance_seen` 先于 `_grammar_uncertainty` 返回，将未处理业务句吞成 `financial_only`；选择链再将它当作已证明没有业务，输出 `skipped_no_narrative`、零 withheld/诊断。纯业务缺资源及实际超过4096字符也丢失能力原因，仅余 `unresolved_without_business_relevance`。

问题不止一个 if 顺序：prepared capability 之前没有区分“处理完但语义歧义”与“能力/范围未处理”的位，scope_use/admission 又只携带 use/relevance，公有 processing、withheld 和 decision inventory 都未收到未完成信息。

## 修复及责任边界

- `SourcePassageCapability.assessment_complete` 为单个 prepared 结果的完成位，默认 True。语言歧义仍是完成的 unresolved 观察；资源缺失/超界为 False。不是任务库、审批、权限、配置开关或第二状态机。
- `source-passage/6`。已观察到的资源/范围失败优先于同 scope 的财务标签或一般 support 归并；不会让另一个财务句证明未处理句没有业务。语言歧义仍 `unresolved + relevant=True`，明确 fragment 仍不准入，纯财务不需要 grammar。
- `ReadingBusinessAssessment.financial_only` 复用原链已有的 bool/None 轴：能力未完成为 None；已证明可读业务的 mixed scope 为 False；真正财务-only 为 True。Fact/event/number/issuer 投影不变。
- `scope_use` 携带该能力是否 deferred；admission 消费完成位并保留具体 source reason，代替丢成泛泛的 `unresolved_without_business_relevance`。已证明的 context-role / qualified table 仍由自己的 owner 负责，不因不需要的 prose 能力增加门。
- 来源能力 deferred 进入既有 withheld，记录 `status=deferred`、`phase=source_readability`、reason 和真实 known unit IDs；公有 selection diagnostics 按 reason 聚合，ID最多16并提供总数/limited。没有把原话放入诊断。
- 公有 `reading_context.source_processing_complete` 明确语义/来源处理是否完成。零可读 span 为原有 `needs_review` 状态，有其他可读 span 为 `partial`；这里表示质量/能力未完成，不新增人工许可或签收队列。
- **不修改 parsed 的物理/几何覆盖。** 单纯 prose 能力 deferred 时，原公有 coverage 也保持原来的物理覆盖值，另以 source_processing_complete/withheld/status/reason 表示语义未处理；既有真实 WorkBudget/结构未完成路径保持原语义。
- 不将局部能力失败写成 `SourceOperatingSession.complete=False` 或 budget.exhausted。最终财务统计遇到该 scope 的 None 会记录原因并继续；另一个正常独立 scope 仍处理。真正 WorkBudget stop 继续使用原 stop/partial 链。
- decision inventory 在来源 processing 未完成时显式标 partial，不能把这个未完成 attempt 作为完整 cache reuse 证据；不创建另一个缓存。

## 真实公有测试与 TDD

新文件 `tests/unit/du11_production/test_source_readability_deferred_selection.py` 使用真实 `select_narrative_evidence(... selector_version=0.9.0)`、规范 source unit 和实际 whole-document pipeline，只有“缺资源”场景 mock 语言资源加载。超界用实际 >4096字符的完整单 scope，**没有 mock scope_limit**。均为隔离内存原件，不连接生产资料/下载/模型。

- 最初三态 RED：3F /4.71s，确认纯业务缺资源、mixed缺资源、实际scope_limit都丢 processing 真相。最初试验将 coverage 当成来源处理完整度断言；ROOT澄清物理覆盖轴后，最终合同改用明确 source_processing_complete，并要求几何覆盖保留。不是改测试掩盖业务失败。
- 加两个“另一个健康 scope 继续”反控后的正确合同 RED：**5F /34.87s**，baseline 缺 source_processing_complete，另一个 span 存在时错误报 selected/fully handled。
- 核心传播接线后5P /18.34s。
- 再加正常/负控，发现已选 mixed assessment 仍带旧 coarse financial_only=True：10P/1F /26.65s。以实际 source passage 的业务可读性修正 financial-only 归并，保留财务内容但不说整段只有财务。
- **冻结最终组 19P /33.34s**：新公有用例13项，加既有6项工作预算/typed proof/同scope复用回归。没有重复88/100整组或真实公司批次。

13项新公有用例覆盖：

1. 纯业务缺资源，mixed缺资源，实际scope_limit → 明确 deferred、原因/IDs/拒绝原因/诊断、partial decision inventory；原文物理覆盖仍完整。
2. >4096完整 scope + 正常未知行业独立 scope → 整体 partial，后者原话入选，非 WorkBudget 耗尽。
3. 缺English资源 + 独立既有 typed proof → 后者原话入选，非全局停止。
4. 资源可用时纯业务/mixed 正常 selected，financial_only=False。
5. 纯财务在资源缺失 mock 下仍明确 skip，tagger零调用，无能力 deferred。
6. 明确 relative 名词片段不准入，但处理本身完成，不伪报资源失败。
7. 完整但词典歧义原话和同形潜在 NP：都保留 unresolved，Fact不升级，非能力未完成。
8. 同一 session 已准备失败结果重复访问不重扫、不补收费；session工作未全局停止。
9. 独立新一次 selection 在资源恢复后正常选回同一原话，不沿用负面的“没有业务”结论。这只证明 public attempt 恢复，不冒充 AUTO 持久化重放验收。

6项既有定点回归：source WorkBudget(1)、128-unit真实source工作停机（1M原测试额度）、same-scope matrix结果复用、grammar预算前置停机的2个变形、typed proof不调用POS。仍使用其既定测试额度，没有提升生产 **16M /112**。

可复跑：

```text
PYTHONPATH=src;tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -B -X utf8 -m pytest -p pytest_asyncio.plugin tests/unit/du11_production/test_source_readability_deferred_selection.py tests/unit/document_understanding_selection/test_source_support_use.py::test_source_assessment_exhaustion_is_explicit_and_never_an_unbounded_fallback tests/unit/document_understanding_selection/test_reading_production_selection.py::test_unassessed_source_work_is_explicitly_partial tests/unit/du11_production/test_statement_grammar_runtime.py::test_statement_boundary_result_is_reused_for_the_same_scope_without_a_second_charge tests/unit/du11_production/test_statement_grammar_runtime.py::test_shared_source_session_turns_grammar_budget_stop_into_partial_once tests/unit/du11_production/test_statement_grammar_runtime.py::test_existing_typed_proof_never_needs_pos_fallback -q -p no:cacheprovider
```

Ruff（4源＋新测试）通过；mypy（4源）通过。既有2条 jieba/pkg_resources 弃用 warning保留，未增加版本门或压警告。

## 文件和实施范围

实际改动：`narrative_source_passage.py`、`narrative_business_policy.py`、`narrative_reading.py`、`narrative_reading_admission.py`、新定点测试。本次**没有**改 `SourceOperatingSession` 的 stop 状态实现、grammar算法/资源/依赖、原件、生产配置/库、主PWF/Git index/commit/push/LLM费用账。

资源仍10,775,669 B；NLTK/jieba版本和资源字节身份不变。本次没有新资源、wheel、下载/解压临时树或模型/原件副本。公有测试在内存中构造 source units；复用测试设施的fixture cleanup，不删除全局缓存。r3/以前轮次的 wheel/cache/C 旧收据不代表R4端到端已通过。

ROOT下一步只需对冻结R4做定点独审，再继续原来的真实 summary/cache/RF C。19个小样本绿不能替代该生产链验收。本线 STOP。
