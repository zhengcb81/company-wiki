# W03 业务召回根因与有界选择设计（只读调查）

- 调查基线：`accdeccc737ccaf27d1698238a31af022960a3fa`，实际 MAIN 隔离树；记录时间 `2026-10-10T23:20:18.479760+00:00`。
- 只写本报告；不改源码、tests、生产配置、DB、原计划或旧证据，不调用 provider/LLM。
- 对应原计划：`phase6/m3_root_remediation_2026-10-09/work_packages/W03.md`、R04；W02/AUTO 接线、actor 修复和业务召回分开验收。本报告不是 W03 完成签收。

## 1. 可复查的当前事实

完整读取已提交的 `tests/fixtures/narrative_real_transcript/MSFT_Q4_2026_earnings_call.txt`，66,324 bytes，SHA `4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a`。用真实 `parse_transcript_text` → `select_narrative_evidence` → `verify_transcript_evidence_spans` 的纯本机函数执行，不开目录库、不生成摘要。

| 项目 | 本次实际值 |
|---|---:|
| TXT parser | 0.3.1 |
| selector | 0.6.0 |
| 全文 unit | 489 |
| 初始业务 candidate | 40 |
| 上下文扩展后 candidate / selected | 51 / 51 |
| omitted / selection_limit | 0 / 96 |
| selected 原文 UTF-8 bytes | 7,648 |
| selected management / analyst | 40 / 11 |
| QA1–4 入选 unit | 5 / 5 / 4 / 5 |
| QA5 / QA6 全文 unit | 26 / 28 |
| QA5 / QA6 初始 candidate、最终 selected | 均为 0 |
| selected semantic selection_group_id | 0（51 条分别成组） |
| 原文 replay | 51 verified / 0 failed |
| package status / coverage_complete | selected / true |

**直接结论：当前漏选发生在候选发现之前/之中，不是排序或 96 的上限挤掉了 QA5/6，也不是 actor/parser 0.3.1 漏掉了这些内容。** `coverage_complete=true` 在此表示解析覆盖；`selected`/omitted=0 表示已发现候选的选择结果，不能据此说业务语义完整。

### 最小复现入口

从本树导入 `company_wiki.source_catalog.narrative_evidence`，读取上述 TXT 的全部 bytes，`source_id_for_sha256(sha256(bytes))` 仅用于纯函数探针的合法测试标识，不登记/冒称新的 catalog 来源。调用：

```python
parsed = parse_transcript_text(text, source_id=sid, source_sha256=sha, language="en")
package = select_narrative_evidence(parsed, title=fixture.name,
                                  existing_kind="investor_call_transcript")
verified, failed = verify_transcript_evidence_spans(
    text, source_id=sid, source_sha256=sha,
    evidence_spans=package.evidence_spans, language="en")
```

## 2. 真正共因与精确源码接缝

### 2.1 业务价值被缩成“短距离事件词”，经营机制/限定未成为一级候选

`source_catalog/narrative_candidates.py:assess_unit` 先要求 topics / pre_signal / operating_fact，再要求 `_eligible`；`management_statement` 只是入选后的 reason，不负责召回。`narrative_evidence.py:_candidate_rules`/`_HIGH_VALUE_EVENT` 与 `n6_candidate_operating_facts.py:detect_operating_fact` 承担这些决定。

- QA5 管理层原句在 lines 304–312、char 590–802 说已推出的红队 agents。`launched` 后到 `agents` 的间隔实际为 **98 字符**，超过 `_ENGLISH_OPERATING_GAP` 的 **80**。topics=products_rd、progress=true，但 event=false、current_business_progress=false、operating_fact=false，最终拒绝。单加 `cybersecurity` topic 仍不能越过 `_eligible`。
- QA5 char 1492–1680 的 50% cost 对比、1682–1820 的 90%/10%任务路由、2015–2238 的供应商消失/运营韧性都不命中业务机制规则；`multimodel` 不等于现有短语 `multiple models`。加入一个拼写别名只能改善个别句子，不能解决成本因果和必要限定。
- QA6 lines 318–324 中 char 18–117 的“计算方法未变”、772–1031 的 token/cost 效率机制、1207–1454 的应用组合均 topics=()、pre_signal=false、operating_fact=false。它们不属于“新发布/新订单”，仍是有价值的管理层经营方法、机会和限制。
- 财务 API 能提供已清洗数字，不能代替“为何/在什么条件下/哪些产品或工作负载”的原文说明。经营因果句含 margin/ROIC/cost 不能一律归作金融表；同样，只有利润或分红数字也不能因含产品字样晋级。

在同一 `assess_unit` 下，以下**不含 issuer/name 的通用文本**当前都被拒绝，说明不是微软特例：

1. `Our service uses a diversified model mix to reduce token cost and remain available if one provider fails.`
2. `The return calculation has not changed. Efficiency depends on workload mix, token usage and silicon price performance.`
3. `公司产能具有一定弹性，但突发订单下短期配备的人工、组装检测设备和供应商短期供货能力仍会限制生产。`
4. `报告期内公司营业收入增长，主要通过提高付费转化率和广告价格实现，海外需求尚存在不确定性。`

套话 `We take security and shareholder returns seriously and always seek excellence.` 和单独分红/融资数字当前正确拒绝；新策略必须保持这两个负控。

### 2.2 语义完成依赖格式与“已有 seed”，没有补齐跨句主体和限定

- `narrative_evidence.py:select_narrative_evidence` 的 `_pdf_context_groups` → `enrich_context_groups` 为 PDF/OCR 的局部视图补齐片段；TXT句子、official JSON字段没有等价的业务语义组召回。
- `narrative_neighbors.py:_add_adjacent_subject` 只处理 pdf_text_block/OCR、依赖已有 high_value_event；完整前句只有显式指代与受限 subject signal 才进入。主语句本身没命中时，后面的“该系列”会悬空。
- `_add_linked_questions` 只在已有 answer candidate 后补问题；QA5/6 没有 answer seed，问题上下文也无法进入。该关联本身不生成同角色 `selection_group_id`，所以实际 TXT 51 个选段全部是独立预算条目。
- `n6_candidate_completion.py:linkable` 正确保持 source/role/language/parser/QA/actor 边界，但 page_number 必须相等；它不是跨页经营条件完成器。IPO p173 乐观产能说明与 p174 突发订单限制不能靠“完成同一句”自动得到完整组。
- `narrative_budget.py` 已有原子 group 和 BudgetDiagnostic，`narrative_finalize.py` 已按有效 group 消费。缺口主要在**产生有意义且有界的组**，不需要重建预算系统。

## 3. 原年报、招股和投资者 JSON 的共同边界

本次按旧审查引用读取冻结原文页文本，不把它们当成当前新版 PDF parser 已通过。下列三个 page JSON 的 bytes SHA 与 coverage.json 原记录完全一致：

| 冻结 page 文本 | SHA / 实际原文含义 |
|---|---|
| CN annual `d64c410832f2-pages.json` | `168c37d0a48ff39e4b44536b079307dc4cc419f1618c0d7f0f47578c5223a9c5`；p44 CVD/HAR/ALD 钨主体后才有“该系列”验证/重复量产订单；p40 薄膜设备 >300反应台是较宽表述，p41 才明确 LPCVD >300，两者不能简单同名或去重。 |
| CN IPO `19cdb41e03b2-pages.json` | `652b43aeecb19737190682aec9b827457715df1e3e7ac77ace771e245d476fc6`；p173 正常订单下人工/原料/装配弹性，p174 突发订单下短期人工、组装检测、供应商供货会限制生产；必须保留条件而非只挑正面结论。 |
| CN H1 `182e2062fed9-pages.json` | `dfeb05b8c94f103a594bbcbf4d02dbade684490f39d66101f7866833b3b6c4f2`；旧审查要求 p17新品和 p18样机计划，与年报阶段/量产证据不能混作相同事实。本报告没有新跑该PDF。 |

另实读旧捕获的 `qa-precollect-form-10.raw`，SHA `784217fbfdddc06cd53235b3bef8159250b1d4209761092577d35ebb0f313234`；真实 record 36395 在 `/datas/0/records/1`，companyId=145565。

- 原语言 answer 字段 172字符，明确“海外最先进逻辑客户累计交付约800反应台”“持续对接意向客户/拓展海外”。同一现有候选函数的**原生字段探针**已 eligible，score=6、topics=overseas；不要强行声称这个记录当前也漏选。
- question 字段 420字符中“海外客户传闻、20个晶圆厂、SEMI投资增速”等是提问者信息，不能升级为管理层证实。当前 source-owned projection/native role 边界必须保持。
- 这是字段级候选探针，未重新导入或打开 catalog/projection，不冒称真实当前入库或 AUTO 端到端验收。

**共同改造对象是 `DocumentStructure` 上的业务候选/主体/限定与预算，而不是让 PDF、TXT、JSON 的解析器互相模拟。** annual/IPO 是布局段落；TXT已有句子级char/line locator；JSON当前是原生整个 decoded field + pointer/token SHA。三者的原文重放责任继续属于各自 source parser。

HK旧审查的 p5–10经营/变现与 p140融资表挤占问题在原R04保持：先验证候选分类，再看排序，不把“融资表23段”简单改成低分业务候选。此处依据冻结 coverage.json 的报告，不声称本次已重新回放 HK PDF。

## 4. 最小实现设计（给 MAIN 顺序实施，不新开外包卡）

### A. 纯业务 policy：事件 + 机制 + 限定三类

沿用 `CandidateRules`、`OperatingFact`、`EvidenceCandidate`，把“经营机制/条件”作为可解释 reason，不给管理层角色无条件加候选。

1. 事件仍要求可辨识经营对象和行动；在**同一有界原文子句**内识别 action/object 次序及插入说明，解决98字符插入语例。不得把80全局改成任意全文窗口，也不得让 revenue/profit increase 后任一远处 product 触发事件。
2. 机制要求经营对象（服务/产品/工作负载/客户/价格/供给/生产流程等）与显式因果/用途/成本效率/供应韧性/回报框架、组合条件同时出现。ROI、安全、AI或“有信心”单词本身不够。
3. 否定、未变、尚未、仅在、短期/突发、预计/意向/样机/认证阶段可成为已选业务事实的必要限定；不把 opportunity/forecast 改成 actual，不把管理层对ROI的信心变成测得回报。
4. 匹配文本可规范化，输出 raw_text、span IDs、parent/pointer/token/char locator 必须保持原件。source parser/actor版本不为策略改动而升版；selector版本必须升级，进入既有 generation/cache identity。

### B. 有界的业务组完成：复用原子预算，不吞整个QA

在现有 neighbor/group 层对 source-owned units 做纯函数业务完成。优先让同一 policy 处理普通结构/上下文，不把业务词库放进 `transcript_layout` 或 official source adapter。

- 连续邻接窗口复用现有 **MAX_COMPLETION_UNITS=8、BUSINESS_CHARACTER_WINDOW=1200**；募投既有1600窗口维持其范围，不用于放宽一般问答。
- scope至少含 source、parser/version、language、role、speaker及QA/record association。同一个整数QA标签或多个母页的相同 record label不能串组；禁止跨issuer、operator、heading、新问题、role边界。
- 同角色语义组包含最小主体 + 事件/机制 + 必要否定/条件。问题与回答只保留 association，**绝不放在同一个公司事实 support group**；问题可以指示应查哪个管理层回答，但其事实/数字不能提供 answer eligibility 的唯一支撑，更不能支持 company_statement。
- PDF相邻页条件需单独的有界“同业务段/同对象续接”规则，最多探相邻一页、保留两个原页locator；不把现有 `linkable` 泛化成忽略page/QA。无可靠对象/段落边界就报告缺上下文。
- 一个selection_group可以是多个原文locator的support集合，不自动宣称是连续quote。非连续/跨页片段不能用拼接后字符串冒充单条原文。

实际 QA5 Satya主要回答长2562字符，QA6 Amy主要回答长1995字符，均超过1200；**禁止一个QA整体入选**。合适的自然小组为：QA5推出/红蓝绿流程、大小模型成本与90/10限定、韧性条件；QA6框架未变、效率/成本杠杆、portfolio范围。每组自己闭合，不要求每一礼貌/过渡句被选。

JSON约束：当前 locator 绑定整个 native field。policy可以用匹配用的有界子窗口判定，但输出仍应是原来的 whole-field span。原生字段超过输入/组上限时不能在 selector 截字或编造char locator；保留定位与 oversize/coverage 诊断。将来真要拆字段，先由 source-owned parser提供带精确字符/decoded/token关系的合法span并由其replay验证，再交policy，不在AUTO/selector假造源对象。

### C. 同一预算、原子选择、诚实覆盖

- annual/semiannual/call/IR维持96 span；prospectus/equity/convertible维持160；显式max_selected原样；P1/P2/P4是worker并行配置，不是选择/费用扩容。
- 复用 `BudgetItem` / `select_budget_items` / `budget_diagnostics`。组成本等于真实span数，排序看经营事件/采用/机制/限制价值；普通融资数字、免责/ESG/行政套话不能挤占候选。既有类别公平性和确定性保留。
- 必要限定不允许为“凑进余量”只留正面seed；整组不fit则明确 `group_exceeds_limit`/`budget_full`，或先形成几个独立闭合的子组，不能事后随便剪碎一个support组。
- 模型现有实际费用/token/time/output/transport caps不变，默认max_output_tokens=2400不变。选段不能私自启动额外收费补轮或第二任务库；最终模型请求必须来自真实冻结选择，仍由现有caller/ledger执行实际cap。
- 不把 coverage_complete 重新定义为研究/语义穷尽。保留解析coverage + selected_excerpts_only，同时输出有界选择诊断（reason计数 + 少量真实locator/group ID，避免再次复制全文/全部unit）。现有 `BudgetDiagnostic`先复用；若要进严格公共DTO，MAIN先冻结可选/版本化shape，不随意塞字段破坏oldwire。
- 对业务组识别出的“未完成必要上下文/oversize”保留partial影响；不能把没有候选解释成“该业务贡献为零”。也不能承诺每一QA或每一原页都必须selected。

## 5. 最小 TDD 样本与大节点验收

建议八类责任例即可，参数化正反对照；不增逐小节点审查。本文没有修改或执行新tests。

| 责任例 | 先RED的验收点 / 关键负控 |
|---|---|
| 1. 已提交完整MSFT fixture | 真实parse0.3.1→selection包含QA5推出/模型路由/韧性及QA6未变/效率/组合所需原句和限定；<=96、全selected原文replay、角色不变。检查具体业务锚点而非“QA1–6都有一条”或关键词数。 |
| 2. 未知公司/另一表述 | 无issuer/name规则：插入语>80但有界的发布句、通用 diversified model/服务成本与韧性、return未变+efficiency；问题顺序/产品标签变化不改变业务policy。Security/ROI套话仍拒绝。 |
| 3. PDF 主体跨段 | p44类型的命名产品列表 + “该系列验证/订单”；必须保留真实主体，另一产品/另一段标题不能补错。布局拆分不同仍定位一致。 |
| 4. IPO 条件跨页 | 正常弹性 + 下一页突发订单/短期供货约束同时可消费；不丢但/短期，不吞数量/收入表，不跨到不同公司/章节。 |
| 5. Native IR JSON | 复用真实owned TEMP import→projection→select；原生answer/未知记录机制进入，question不能支持company_statement，translated fields/foreign issuer仍不入选。Whole-field pointer/token/parent SHA完全不变；oversize只诊断或使用真正source-owned子span。 |
| 6. 经营因果 vs 财务表 | 付费转化/价格/供需的因果描述可选；融资现金流、dividend、safe-harbor/ESG空话、仅数字增长不可因产品词晋级。 |
| 7. 紧预算/长组/确定性 | limit=1/3与8unit/1200边界；完整组fit才入选，oversize有定位诊断；反序候选不变，负面限定不被替掉，不能跨role/parent/pointer/QA组合。 |
| 8. 单节点无模型复用 | selector版本变化导致新generation；原件/配置/原parser未变；同gen缓存复用0reservation。真实免费parser/selection/replay先过，再在原有统一大节点预算里做摘要，无重复单独收费轮次。 |

责任测试位置优先：`tests/unit/test_narrative_selection_architecture.py`（policy、scope、主体/条件）、`tests/unit/test_n6_budget_selection.py`（原子/上限/诊断）、`tests/integration/test_n6_budget_packages.py`（结构→finalize→summary input）、`tests/integration/test_official_json_select_handler.py`（真实JSON链）。完整TXT业务回放可新增专门integration函数/文件，直接用已提交fixture；actor责任留 `test_transcript_parser_compatibility` / `test_transcript_speaker_affiliation`。不能只用预制 candidates 给planner喂数据来证明召回已经修好。

源码顺序：①先责任RED、冻结候选与组边界；②修共用policy与有界semantic组，不改source-owned parser以迎合选择；③紧预算/financial/role/locator负控；④在同一大节点对完整TXT、原annual/IPO小集与真实native JSON做无模型 before/after及公开replay；⑤与W04模型/摘要质量一起用实际配置、原budget真实重跑。下游group closure仍只是机械引用完整性，独立审查负责命题、数字和因果的真实质量。

## 6. 没有完成/没有假定的事项

- 没有声称当前CN/HK PDF最新版召回已复验；读的是hash匹配的旧冻结页原文。没有触碰已接受P7投影叶、RF校准或audit技能。
- 没有执行新AUTO/provider/LLM，没有新费用，没有创建/修改catalog或生产配置。
- 51/51可replay不等于QA5/6没有价值；反过来，想覆盖QA5/6也不要求把26+28个units或整份原件持久化为切片。
- 通用机制规则需要上述正负例TDD验证；有限规则不承诺语义穷尽，超长/不透明/未知主语继续如实诊断。


## 7. Selector 语义版本与旧回放的最小接线

**必须显式区分 0.6.0 与建议的新 0.7.0，不能只扩大词表后继续标记旧版本。** 本次已读到真实旧消费者：`source_catalog/narrative_retrieval.py:NarrativeEvidenceResolver._replay_record` 在行521–525仅接受 `contract.selector_version == NARRATIVE_SELECTOR_VERSION`；行618–623按当前 `select_narrative_evidence` 重选原文后比对 selection state/summary groups。因此直接把常量改成0.7.0，会拒绝旧0.6.0包；只放宽允许版本列表但仍调用当前策略，同样会让旧包按新语义重选而回放失败。

### 7.1 建议冻结的公共入口

```python
NARRATIVE_SELECTOR_VERSION = "0.7.0"  # 新生成默认
SUPPORTED_NARRATIVE_SELECTOR_VERSIONS = frozenset({"0.6.0", "0.7.0"})

def select_narrative_evidence(
    parsed: NarrativeParseResult,
    *,
    title: str,
    existing_kind: str = "unknown",
    max_selected: int | None = None,
    selector_version: str = NARRATIVE_SELECTOR_VERSION,
) -> NarrativeEvidencePackage: ...
```

- 未知版本在入口以明确 `ValueError` 拒绝，由已有调用层映射为现有 typed error；这是语义路由正确性，不是许可、人工签收或新门禁。
- 0.6.0 路由维持当前候选、PDF/邻接补齐、分数、理由、组ID、预算顺序和结果计数；新机制/结构说明/业务组只在0.7.0开启。保留当前旧 regex/rules，选择不同 policy 或追加版本化纯层；不复制整个 parser/selector 模块，也不让旧路径引用后来不断变更的“current”规则。
- `CandidateRules` 可以继续承载同一接口；`_candidate_rules` 的版本选择及新增纯 policy 接口在实现前由责任RED冻结。旧链条必须实测输出指纹，不只是检查版本字段等于0.6.0。
- parser、source ID、source SHA、原 locator/EvidenceSpan ID 的算法不因候选策略升版。新增group IDs/理由可以改变新选择产物，因此 generation 必须包含真实 selector version。

### 7.2 MAIN 的运行时接线

1. `automation/narrative_select.py` 的 `NarrativeSelector` Protocol、自定义 selector 注入和 `_result_dict`/projection result 要使用**本任务实际冻结的版本**。当前结果写 global version，不能只改变global后把旧冻结任务冒称新版本。对现有未接受 `selector_version` keyword 的 test/custom selector，由单个绑定适配器负责；不在每条业务调用到处 catch `TypeError` 猜签名，也不对 raw 与 JSON 各建一套版本策略。
2. `automation/narrative_official_json.py:select_verified_projection` 继续用同一版本绑定 selector callable；来源适配、整个 native field 和角色不变。它不自行挑另一个版本，也不重复导出/读母页。
3. MAIN 顺序调整既有 manifest/execution_versions/generation 冻结与 resume 检查：新请求默认0.7.0，明确旧0.6.0仍使用旧语义；immutable run binding 里的版本决定执行与发布，不能在恢复时取当前global替换。已有 generation/pin 不重写，不新增表、第二库或人为授权材料。具体 manifest/generation 文件由 ROOT 的已有运行时写集统一确认；本报告没有修改该共享5runtime。
4. `source_catalog/narrative_retrieval.py:_replay_record` 检查“selector name正确且version是明确支持值”，随后将 `contract.selector_version` **传给 selector_version**。旧 replay schema、原始路径映射、实字节SHA、parser version、输出group比对继续原样；不能把0.6.0改标0.7.0，不能自动再选后覆盖旧artifact。
5. 当前AUTO公开read路径按已有 bundle/ref/真实source replay读取选定证据，不需要为新选择语义升ref1/ref2/source协议；它们的selector元数据和generation需真实。不要把 legacy pilot resolver 的“重新选择校验”扩散成每层都再次做完整选择/来源读取。

### 7.3 排他写集与责任测试

| 顺序责任 | 建议排他文件 / 边界 |
|---|---|
| W03纯候选与有限组 | `source_catalog/narrative_evidence.py`、`narrative_candidates.py`及确需的独立新 `narrative_business_policy.py` / `narrative_business_groups.py`；已有 `narrative_neighbors.py` / `narrative_group_candidates.py`若改只归同一条W03线。保持旧0.6.0规则并复用budget，不碰source-owned TXT/PDF/official projection leaf。 |
| ROOT顺序运行时 | `automation/narrative_select.py`、版本绑定所需 `automation/narrative_official_json.py` 薄适配、ROOT既有 manifest/generation/resume 文件、`source_catalog/narrative_retrieval.py`。这些不得与候选线并写；ROOT先冻结实际调用和版本选择，再串行接线。 |
| 责任tests | 候选/组沿第5节；旧pilot消费者回放例由ROOT放入其既有责任tests；本次追加未确认该消费者的测试文件名，canonical CodeGraph 的 `*resolver*.py` 清单没有对应 narrative 文件，不把推测的文件名当既有事实；冻结version/generation责任留现有AUTO select/manifest/generation/resume tests，不另造模型或存储测试框架。 |

最小版本负控：

- 在改语义前封存完整MSFT fixture按0.6.0的有序span IDs/locator、原text SHA、topics/reasons/groups、候选/遗漏/状态的确定性指纹；改后**显式0.6.0必须逐字段相同**。已经观察到51段/51replay通过，可作旧行为基准，但不能仅靠51这个数量验兼容。
- 新0.7.0必须出现目标经营锚点与必要限定；显式0.6.0不能悄悄出现这些新groups/reasons，不能将新结果写旧tag。
- 真实旧bundle0.6.0由resolver按旧version重选回放成功；未知version拒绝，new0.7.0包按新version成功。使用已提交TXT即可，无provider/费用。
- 同source/parents/parser版本、同0.6.0与0.7.0须有不同generation；不能复用旧pin或零选择缓存。每个版本自身重复请求应精确复用且0新增reservation；old run resume仍使用old binding，不随global切换。
- 新旧公共read都保留真实role、原parent/pointer/token/char定位与相同原文SHA；选择版本不是来源版本，不能假造投影source或变更旧originals。

以上是一个语义分流和已有责任测试的大节点，不增加小步骤签收、全量额外采样或人工许可。

## 8. 招股/增发/可转债的详细业务结构也属于召回目标

A节的机制规则还必须覆盖**有具体业务对象及明确关系/约束的结构描述**，不要求每句都有 launch、交付、增长或一个最新动作。静态不是低价值的充分条件：招股、增发、可转债中产品体系/用途、工艺及生产组织、客户与销售渠道、地域/供应链布局、研发平台、商业模式及业务之间的关系，可能正是理解主营与新业务所需的高价值来源。

最小区分是“经营对象 + 具体结构/关系/用途/渠道/生产约束”，例如 `公司的产品分为控制器与执行器，控制器通过直销供给设备厂，执行器由海外渠道销售；关键部件须完成客户验证。` 可形成有限同主题组；未知公司名同样适用。`本公司依法经营，坚持创新发展，为客户创造价值。`、孤立课程式技术定义、行政制度、纯财务表/分红数字仍不因此成为业务候选。

实现可以增加 `business_structure` 一类可解释reason与bounded topic-group，而不是把整章复制为切片或新建研究结论。章节标题可提供局部业务主题上下文，但不能以“公司业务”标题为许可让全部后续段落入选。每组仍遵守source/actor/role/record边界及8units/1200字窗、原子预算；实际产能/订单、意向/样机、行业描述和公司特定事实保持各自原文限定。第5节未知公司及招股责任例应参数化一个无动作的具体结构正例与套话/定义/纯表格负例，无须扩大材料采样或额外收费轮次。
