# 预算与选择效率：只读根因调查

**结论状态：调查结论已形成；不是修复验收，也不授权提高预算。**

## 结论

目前看到的是三种不同问题，不能用“把 16M 提高”统一处理：

1. **AMEC 招股书（429 页）遇到的是共享逻辑工作量上限。** 记录显示 PDF 解析用了 420,052 work units，完成 14,025 个原生单元后，解析与选择共用预算已到 15,999,740 / 16,000,000；最终 `needs_review`、0 个选中片段，没有进入摘要编译。这说明主要花费发生在解析之后的理解/候选闭环路径，但现有真实收据没有分阶段账目，不能把具体某个函数宣布为根因。
2. **金山云半年报的缺项不是预算耗尽。** 它只用了 3,644,236 / 16M，但 1,116 个候选被压到最多 112 个片段，结果 6,522 字符且 coverage 不完整。用户关心的经营事实漏选属于候选质量/排序/覆盖问题，应修选择策略并用原 gold 验证，单纯增加工作预算不会自动提高前 112 项的召回。两项目标事实未选是 ROOT 对真实预检的发现；本报告不对其语义正确性另行签收。
3. **微软 10-K 没有触顶。** 记录为 13,577,692 / 16M、112 个片段、50 个任务、coverage complete。ROOT 指出 Azure 层级事实仍缺失。这是“coverage complete 不等于必需业务事实命中”的 gold/选择验收问题，也不应通过提高预算掩盖。

因此，当前证据支持的共因是：**一个总账能阻止无限分析，但缺少足以定位高耗用阶段的分账；高候选文档先处理大量全篇语义和关系闭环，最后才受 112 片段上限约束；另外 coverage 状态没有保证业务 gold 召回。** 其中第一条需要补阶段观测并优化实际热点，第二条要修候选召回/排序，不能混为一种“效率优化”。

## 证据与边界

- 跨市场本地预检的 `run-manifest.json` 记录 HEAD 前后均为 `483cb2a56299cb28ca07bbd349674860baf04430`，source stable/protected unchanged；模型、API、下载、raw copy 均为 0，临时目录为 0。此次是离线预检，不是付费模型验收。
- AMEC 记录：PDF 429 页、14,025 units、parse work 420,052；selector 报告 8,361 candidates、0 selected spans、0 actual tasks，work budget exhausted，15,999,740 / 16,000,000，12.397 秒。`parse_work` 约占总 work 的 2.6%；余量主要发生在 parse 之后，但无法再按阶段精确切分。
- 金山云半年报：1,116 candidates、112 selected、6,522 字符、60 tasks，3,644,236 / 16M，coverage false。微软 10-K：484 candidates、112 selected、40,491 字符、50 tasks，13,577,692 / 16M，coverage true。候选数和选中数都是运行收据值，不等价于语义 gold 召回。
- `WorkBudget` 的单位是逻辑工作量，不是 token、字符、秒或 API 费用；目前 `_work_observation` 也明确写着 `full_pipeline_hard_bound: false`。所以 12.397 秒只描述该次观测耗时，不能由 `15.999M work` 推导为运行慢或将来耗时。
- 当前 `understand_units` 顺序执行 native signals、layout、structure、profile、reading plan、dependency packages、table purpose/binding；`select_reading_evidence` 在同一预算中继续做 source-parent understanding、候选与关系/连续性/引用闭环、财务过滤、最终选择和 decision trace。这些环节承担不同语义，不应未经逐阶段数据就删掉。
- 代码确有局部缓存：`SourceOperatingSession` 保存 facts/relations/references/financial 等结果，continuity 使用调用级 source context；应保留并核实缓存命中与失效，不能先验认定它们是重复浪费。
- 生产已有共享父预算和子 scope：`layout_snapshots/contract.py`、`narrative_continuity.py`、`narrative_evidence.py`（`shared_budget.scoped(1_000_000)`）及 `narrative_pdf_intent.py`。子 scope 仍向父预算 charge，不是独立预算库。CodeGraph 的调用图对部分 `.scoped()` 调用解析不完整；不能据此说生产没用 scope。
- 仓库已有较早的 `profile-real.json`：一个不同来源版本的美股 10-Q（2,274 units、约 2M 总 work）中，按 charge 位置统计的历史热点主要是 `_clause_events` 835,744、structure stage 489,708、`_detect_operating_relations` 213,835、layout contract 140,195。它可说明此前曾存在可用的逐 charge 归因方式，但该报告绑定的 `narrative_reading.py` SHA 为 `e65fd6…`，与当前 `AEDC19…` 不同，也不是本次 AMEC 文档；因此**只能作为历史调查线索，不能冒充当前热点测量或当前问题根因**。

## 最小、可验证的下一步

1. 在现有 `WorkBudget`/调用级 scope 中增加**零额外扫描**的阶段归因：对已发生的 charge 标注 owner/stage；总账仍只有一个，16M 上限不变，子账只用于解释用量。报告 inclusive 与 exclusive 口径，避免父子 scope 重复相加。
2. 在同一固定离线回放中记录 parse、pipeline 阶段、source closure、operating relations、reference/continuity、decision trace、selection 的 used/work calls 与完成状态；不为统计再遍历 units，不把逻辑 work 伪称 CPU/时间硬上限。
3. 先复现三类结果，再改根因：AMEC 大文档预算耗尽、HK 预算富余却 gold 漏选、US 预算未耗尽却 gold 漏选。预算上限、112 片段 cap、输入原文和 provider 均固定；结果必须记录 gold IDs/命中、实际选中字符/任务、partial 状态和 source SHA。
4. 若观测确认某阶段是主要开销，再针对该 owner 做缓存/索引复用或线性化；用 1x/2x 单元规模探针检测重复全量扫描或 N² 增长，同时断言同样的证据 ID/locator、业务 gold 召回、单一总预算、超限诚实 partial、0 外部调用。性能优化不能靠跳过候选、截断未声明或只调整预算。
5. 对半年度报告和 10-K 分别检查 gold 漏选：候选是否生成、因何淘汰、排序分是否足够、family/section 是否截断。测试应证明相关业务描述可在 112 cap 内入选，并保留格式化财务表不会挤占叙述事实的既有规则。

## 建议的 TDD 验收

- **预算归属单测：** 同一总预算中的 scope charge 合计与父预算完全一致；父/子层级报告不重复计总；父上限耗尽后所有阶段停止并产出明确的 `work_budget_exhausted`，不重启扫描。
- **阶段统计单测：** 给确定性 charge 序列，验证 stage breakdown 可加总到总账；关闭/打开统计不改变最终 evidence、locator、状态或预算边界。
- **规模探针：** 同一通用文档结构扩大单元数，逐阶段记录被访问/分类/closure 的单元量；以可解释的线性或既定复杂度为断言，禁止隐藏重复扫全表。避免以具体公司、页码或章节写规则。
- **真实离线回放：** 对三个已有样本分别检验固定 gold 命中、112 cap、source hash、partial/complete 语义、费用/调用为零、原文无副本；不需要再跑整套 pytest。

## 决策

先补同一总账的阶段观测，再按实测热点优化；HK/MSFT 的漏选另作为召回问题处理。当前没有依据提高 16M，也没有依据删去连续性、来源关系或决策追踪步骤。此调查没有运行脚本/测试、读取密钥、下载原件或调用模型/API；没有改产品代码。

## 绑定版本

- HEAD：`483cb2a56299cb28ca07bbd349674860baf04430`（跨市场 manifest 的前后 HEAD 一致）。
- 当前产品/证据源 SHA-256 列于配套 `budget-investigation.json`；该清单也标注历史 profiler 与当前代码版本不一致。
