# 独立真实摘要审查 — 2026-10-30

**结论：摘要质量未通过，4 项共用问题仍 OPEN。** 已逐项核对 8 个 gold 检查点、真实 MiMo 请求与回复，以及正式 bundle；没有新增模型请求、下载或 PDF 解析。流程成功不能代替来源语义与业务覆盖验收。

审查对象为 `real-summary-v3` 的一次开发样本，模型 `mimo-v2.6-flash`，prompt `reading-source-scoped/4.1.0`，source SHA-256 `221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7`。不是 holdout，不据此声称完整文档召回率或普遍改善。

## 已验证的数量与边界

| 指标 | 观察结果 | 含义 |
|---|---:|---|
| 输入完整供给 gold 检查点 | 8/8 | 仅证明材料已送入，不证明摘要保留 |
| 真实回复及最终条目覆盖任务 | 6/8（75%） | t3、t7 未输出；解码后 6 条与正式 draft 完全一致 |
| 保留关键来源语义的正文检查点 | 5/8（62.5%） | 1 项归属限定丢失、2 项重要遗漏；不含结构化语态问题 |
| 已输出正文忠实性 | 5/6 | t2 失败；其余正文保留关键条件、主体、量纲 |
| 结构化语态仍 OPEN | 3/6 条 | t4、t6、t8 用单个 actual 表达多个不同语态 |
| 产品自身质量标签 | 6 条均 needs_review=false，bundle verified | 不代表本次独立语义审查通过 |
| 重算任务 coverage | 6/8，complete=false，semantic_status=not_evaluated | 这项诚实观测未序列化进 bundle |
| 调用/恢复/缓存 | 1 次 POST；activation recovery PASS；same/cross-run 零 POST | 已在 overall 中留存；本次没有重新调用模型 |
| 整个 harness | FAIL | consumer 阶段整体未闭合；不能把模型完成写成全链路通过 |

原选择本身也是 `selection.status=partial`、`coverage_complete=false`，这里只对真正送出的 8 个任务做输出语义审查，不推定全篇没有其他业务事实。

## 逐项来源审查

| task / gold | 结论 | 实际核对 |
|---|---|---|
| t1 境内收入 | 正文通过 | 2025 年度、约 8.19 亿元、约 22% 与较 2024 年提升均保留；未挪用问句“80%多”作管理层数字。 |
| t2 报道所述事项及重大影响否定 | 失败：归属限定丢失 | 原文“根据相应新闻报道，您所描述的情况涉及该公司的家电产品”；输出“三星所涉事项涉及家电产品”。“未对九目化学经营构成重大影响”及“重大”量级保留，但报道来源/问题前提变成无归属直接断言。 |
| t3 九目化学客户链 | 失败：遗漏 | 九目化学 OLED 升华前材料→国内外 OLED 成品材料企业→显示面板企业→显示屏应用企业，完整 support 已送，未输出。不得用客户类别推定发行人制造事件。 |
| t4 上市审核程序 | 正文通过；语态 OPEN | 收到第二轮问询、财务有效期已过、申请中止、更新后将申请恢复并回复均保留。**没有写成已恢复审核。** 单个 actual 同时覆盖历史事件及条件未来动作。 |
| t5 收入影响原因 | 正文通过 | 2024 年沸石系列环保材料及部分医药下游需求减少；2025 年沸石分子筛收入略低于 2024 年，主体、期间、因果均保留。 |
| t6 VC 否定及股东联系 | 正文通过；语态 OPEN | 公司现无生产 VC（碳酸亚乙烯酯）；根据控股股东信息；联系主体为中国节能与宁德时代；希望合作均保留。**没有变成发行人签约或带量采购。** actual 同时覆盖否定、已联系、合作愿望。 |
| t7 已售产品及研发数量 | 失败：遗漏 | 已销售光刻胶单体、树脂、光酸、清洗剂添加材料；已开发超 300 种化合物，两类事实完整送入，均未输出。没有发生“300 种全部已售”的输出幻觉，但缺失必要业务内容。 |
| t8 项目产能 | 正文通过；语态 OPEN | 2025 年启动万润工业园二期 C05、半导体光刻胶相关材料、约 751 吨/年、建成后条件均保留。**没有写成现有已投产 751 吨/年。** actual 混合启动与未来产能保障。 |

通用未来“提供更多优质产品”等套话没有被输出为独立经营事实。这个负对照仅对实际 6 条输出成立，不能代替全篇召回检查。

## 共用问题与根因

### F01 · P1 · OPEN：合法引用不保证改写保留来源归属

t2 的管理层 support 角色合法，问句作为 context 也合法；这些结构事实没有证明最终文字保留“据报道”。`decode_scoped_draft` 在 `narrative_model_scoped.py:268` 依据 support 角色生成 company_statement；`validate_summary_claim`（`narrative_evidence.py:2785`）校验非空、ID、上下文同源及角色；`_validate_claim_roles`（2817）并不比对正文主体、转述归属、条件或否定作用域。自动附带 context ID 不能补回正文已删限定。

本次真实错误是“报道/问题前提归属丢失”。没有把未输出的“三星退出整个中国市场”或“第一大客户”记成真实模型已说出的错误。

### F02 · P1 · OPEN：重要内容被降为 description 后，在 sparse 摘要中失踪

实际输入 t3、t7 均为 `reading.value_band=description`；t7 尽管含“已销售”和“已开发超 300 种”事实，仍为 description。其余 6 个输出任务为 meaningful_fact。提示同时要求 sparse、up to target，并明确 meaningful facts precede descriptions；decoder 在 `narrative_model_scoped.py:254` 只循环现有响应 `tasks.get(key, [])`，不要求对完整已供给的重要任务给出输出或缺失理由。

这与两项遗漏完全吻合，是共用优先级/覆盖策略的问题，不能用针对该公司补词解决。实际输出仅 348 tokens，而配置为 8192、target=8、max=40；没有证据显示硬上限耗尽。未做新模型反事实实验，因此“分类与提示是唯一生成原因”没有被证明。

稀疏摘要可以合法不复述所有来源；需要修复的是选定重要业务事实的覆盖可观察性和遗漏理由，而不是强制把所有原文抄进摘要。改进验收应覆盖通用客户链、已售产品与开发数量，不以公司名、特定材料名做白名单。

### F03 · P1 · OPEN：replay verified 被混同为摘要质量通过

`SummaryTaskPlan.coverage`（`summary_tasks.py:68`）明确给出 emitted 6/8、not_emitted t3/t7、semantic_status=not_evaluated；该观测没有写入正式 bundle。`project_summary_claim_quality`（`narrative_evidence.py:2852`）依据 parsed、quality flags、unknown role 和 uncertain 标签投影 needs_review；`narrative_verify.py:373` 于是把 draft 投影为 verified。

这些是有效的来源/提取检查，但不是改写语义检查。产品应机器可读地区分来源定位可回放、提取质量、摘要改写语义与选定任务覆盖；尚未审查语义时保留 not_evaluated，重要遗漏应显式 partial/open。

可复查反例：仅在内存中把 t2 改成原文不存在的“九目化学已完成对三星家电业务的收购”，保留同一合法 basis，decoder 仍保留、needs_review=false、status=draft。**这是人工构造的验证器探针，不是真实模型输出，未替换任何捕获文件。** 它证明边界目前不做语义蕴含校验。

### F04 · P2 · OPEN：单个 modality 标签无法忠实表示混合状态

t4、t6、t8 的正文限定都在，不应误判为已恢复审核、已签约或已投产。问题是机器消费者只看 actual 时无法区分“申请了”与“将申请”、“已联系”与“希望”、“已启动”与“建成后”。

旧 reading 提示 `narrative_model.py:165` 明确要求 single modality、拆分实际进展与未来动作；新 scoped 提示没有保留这一明确拆分约束。canonical SummaryClaim 只有一个 modality enum，角色校验仅要求 analyst_question 配 question，不检查公司陈述的状态粒度。因此这是结构化语义合同/粒度缺口，不能称为现行严格 schema 拒收错误。

应明确状态、否定、未来动作与条件的合同，拆分或按受控方式表达，同时保留同源 support、主体与条件。不能简单把整条改为 planned 后丢掉历史事实，更不能删掉条件以凑单一标签。

## 可复查资料与验收范围

- `review.json`：全部 8 项的 support/context 原文、locator、span ID、真实回复和正式最终条目；4 项 OPEN 的证据与验收要求。
- `reproduce.py`：只读捕获 JSON、运行真实 decoder、重算 coverage、验证真实输出等于 final draft；另有明确标识的合成验证器反例。
- `reproduction.json`：上述执行结果及 input/response/selection/bundle 的压缩和解压 SHA-256；真实 response 解压 SHA `26f69cc2838cd67e3183e8f2fbac80df01f812b0a8617b1398ae3f2db6874442`，bundle 解压 SHA `3a33d89419d325bdfc3be4facb1c7f85761384ba9a5e304c2c16008577ee5679`。

复现：从仓库根目录运行 `python .planning/source-description-20261030/real-summary-independent/reproduce.py`。不联网、不读模型密钥、不解析 PDF，只会更新本独审目录的 `reproduction.json`。

已验证 8/8 检查点，5 项正文关键语义通过，1 项归属失败、2 项遗漏，另 3 条结构化语态 OPEN。关键工程恢复与缓存证据可单独通过；完整 consumer 链路与摘要质量仍未通过。本审查没有更改产品、生产配置或母计划。
