# 来源解析、共享阅读与摘要层代码质量审查

审查日：2026-11-01。基线：`d38613bc`（ROOT提供的运行版本为`7e10973e`）。结论针对当前工作树代码；本轮只审查并更新本文件，主公司循环仍 paused。

## 结论

发现 **1 项已复现的通用阅读准入缺口、1 项已复现的决策指纹漏项、1 项维护性风险**。没有在检查范围内发现按真实公司名称、证券代码或固定页码切换生产行为的特判。存在大量业务/语法词典，但不能将词典本身等同于公司特判；真正问题是一些词典仍决定资料能否进入摘要。

R4 p12 业务单元遗漏及跨股东承诺 context 串组沿用主计划的待源 RED 状态，本报告不以它们充当新发现。已修的 D&M、p14、519 不列为未修。

## 发现 SR-01 — P1：简单陈述句因有限语法兜底被排除出共享阅读

**状态：确认，纯本地真实 owner + admission helper 复现；未跑公司、完整 selector 或模型。**

位置与路径：

- `src/company_wiki/source_catalog/narrative_source_passage.py:56` `_EN_DECLARATION`、`:59` `_CN_DECLARATION`，`:211` `_declarative`（关键返回在`:222`）。
- 同文件`:225` `prepare_source_passage`，`:283` 只有 `_declarative` 成功才将未知词叙述设为 readable；`:296` 否则返回 `unresolved / relevant=False`。
- `src/company_wiki/source_catalog/narrative_operating_relations.py:771` `SourceOperatingSession.fact`，`:790` 用当前业务 assessment，`:794` 缓存 passage。
- `src/company_wiki/source_catalog/narrative_support_use.py:20` `source_narrative_relevance` 消费 passage relevance；`narrative_reading.py:65` `_admitted`，`:165` 将 irrelevant + unresolved 明确拒绝。
- 当前入口 `narrative_evidence.py:2597` 对 selector `0.9.0` 分派 `select_reading_evidence`，不是仅历史路径。

触发条件：原文为完整、独立的业务陈述；对象/动词未命中有限 operating 词典，也没有表格或已识别关系提供额外证明。英文简单现在时、中文无“正在/拥有/包括/是/为”等兜底词时尤其明显。

真实影响：可读业务原文在付费前即被拒绝，摘要无法覆盖它；`unresolved`虽保留诊断，但`relevant=False`使它不再是可送的未知业务材料。没有证据证明本轮任何公司已发生具体金额或模型结论错误。

最小诊断（`SourceOperatingSession` → `fact/source_passage` → `source_support_use/source_narrative_relevance` → `_admitted`，单原文单元，priority=1）：

| 原文 | passage | admission |
|---|---|---|
| Our vessels transport liquefied gas between coastal terminals. | unresolved, relevant=False | False |
| Our vessels are transporting liquefied gas between coastal terminals. | support, relevant=True | True |
| 本公司经营铁路运输业务。 | unresolved, relevant=False | False |
| 我们的船舶正在运输液化天然气。 | support, relevant=True | True |
| Is our vessel transporting liquefied gas? | context_only, relevant=False | False（正确负例） |

另在纯 `prepare_reading_business_assessment(text, {relations: []})` 诊断中，`Our trains carry passengers...` / `Our clinicians treat rare diseases...` / `Our stores sell fresh vegetables...` 同样失败，而加入 `are carrying / are treating` 后成功。`The template is describing future procedures.`正确不提供支持。

已有测试缺口：`tests/unit/du11_production/test_source_passage_admission.py:19` 的未知实体正例主要使用 owns、from/to、was/is、正在等已知兜底；`:185` 的简单动词例采用 software 等已知对象，绕过了“未知对象 + 普通完整动词”组合。现有问题/模板/会计规则负例应保留。

共用根修方向：将“资料可读且与业务相关”与“可证明 operating event/数值/issuer”继续分层，但前者不能由少数动词白名单穷尽。使用已有原文章节、独立句边界、主体/宾语范围及明确负例确定可读引用资格，未知词维持未知事实类型，不新增 vessels/clinicians/铁路公司专用分支。新增跨行业、同义时态变换的变形测试；正例只要求原文被保留，不能借此升级状态/收入确认/主体证据。

## 发现 SR-02 — P2：手写决策指纹模块清单漏掉直接影响阅读的 owner

**状态：指纹漏项确认；真实缓存陈旧命中未执行。**

位置：`document_understanding/decision_inventory.py:72` `_versions`，`:87` 手写 `business_modules`，`:140` 读取模块 bytes。`narrative_reading.py:30` 导入 antecedent owner，`:1588` 多原文 parent 合成；`pipeline.py:138` 开始 route/profile 路径，`:206` 绑定 reading plan。消费端 `automation/narrative_generation.py:592` `current_reading_decision_matches` 在`:609-613` 比较当前 trace 与 frozen dependencies。

当前至少以下实际阅读逻辑未被 `_versions` 的字节闭包覆盖：

| 模块 | 作用 | 进程内模拟仅该文件字节改变时 |
|---|---|---|
| `source_catalog/narrative_antecedent.py` | 前文窗口、reference envelope，影响依赖闭合 | 未读该文件，versions不变 |
| `source_catalog/narrative_parent_composition.py` | 多 source parent pipeline 合成 | 未读该文件，versions不变 |
| `document_understanding/profiles/signals.py` | 文档路由信号 | 未读该文件，versions不变 |
| `document_understanding/strategy_binding.py` | 章节策略匹配与继承 | 未读该文件，versions不变；仅显式版本常量覆盖 |
| 对照：`source_catalog/narrative_source_passage.py` | 可读性判定 | 读1次，versions改变 |

诊断方法：使用 `unittest.mock.patch.object(Path, 'read_bytes', ...)`，仅对指定路径的读取结果追加字节；没有更改任何源文件或版本常量。执行 `_versions(pdf_frontend=False, mime_type='text/plain')`，与未patch版本比较。此诊断确认当前自动字节指纹的覆盖缺口，不是实施规则变更，也不是运行缓存/selector。

触发条件与影响：上述模块进行规则修改，关联显式 feature/version 没有同步修改。前两模块没有被当前版本表直接采集的版本身份；signals也依赖别的维护者记得升级外层。于是决策层可返回相同指纹，缓存比较无法通过该机制识别阅读算法变化。若其他生成身份恰好变化会使外层失效，所以不将本轮证据扩大为“所有修改必然复用旧摘要”。但这违背当前字节指纹“rule-only change 也失效”的设计目标，并会让修复难以可靠传播。

已有测试缺口：`tests/unit/document_understanding_selection/test_reading_decision_inventory.py` 已覆盖 policy/reporting/continuity/若干 grammar 模块变化，采用逐个已知 owner 的正例；缺少针对当前激活阅读依赖集合的闭包校验，漏项不会自动触发新增用例。

共用根修方向：由 reader/各 owner 提供单一、显式的算法依赖声明，组合成 carrier-scoped recipe，再由 generic inventory 消费。不要继续只补四个字符串，也不要哈希全仓导致无关变化重跑。最小正例是 antecedent/parent composition/route signal/strategy matcher 任一实现变更使对应 carrier decision changed；负例是无关测试、其他不适用 document family 内容变化不失效。保留原文hash与实际使用组件的身份核对。

关联解耦问题：`decision_inventory.py:52` 导入 automation，`:77-78` 导入 source_catalog，同时 selector 又在`:1769`回调 inventory；lazy import避免初始化冲突，但低层目录仍承担高层组件知识。将组合放在 reading入口/recipe owner，DU inventory保留通用trace构造，可同时减少反向依赖与人工遗漏。当前没有把该导入关系误报为已发生循环导入异常。

## 发现 SR-03 — P3：共享阅读 adapter 的责任集中，后续修复易再次引入交叉否决

**状态：维护性风险确认；无独立运行故障归因。**

`source_catalog/narrative_reading.py`共1801行；AST只读统计：`_prose_reading_packages`（`:200`）402行，`_candidates`（`:604`）669行。后者同时组织原文单元、native groups、antecedent、operating session、context closure、table资格、admission、预算与diagnostics。`narrative_evidence.py`为2886行，当前parser与历史多selector共存；`narrative_business_policy.py`为1205行。行数不是bug，集中于这些变更轴才是维护风险。

共用修方向：保持现有 SourceOperatingSession、NativeSourceContext 和 selector budget 为单一owner，按“本次source材料/依赖计划 → 已准备assessment → admission结果 → budget选择/投影”拆纯阶段对象；各阶段返回原有ID与诊断，不重扫原文、不新建registry、不添加检查投票。保留当前函数入口作兼容adapter。不要单纯按文件行数切模块，或拆出多份判断同一事实的owner。

最小正反例与验证：同一 prepared scope 的 support/relevance/financial 结果供所有消费者复用；读取两次不增加已准备assessment的工作费；不同parent/context不得合并。旧selector版本的历史回放必须继续生成原有身份和行为。现有source_information_binding/source_passage用例是良好起点；本轮未跑测试，也不声称完整回归通过。

## 模块覆盖与限制

| 模块范围 | 检查深度 | 本轮判断 |
|---|---|---|
| DU pipeline/orchestration/strategy binding | 阅读主链和匹配/预算关键段 | single budget、child scope与策略继承边界合理；SR-02适用 |
| profiles/registry/signals/catalog | 文件/符号索引、关键调用、词典字面搜索、指纹诊断 | 没有查到公司/页码执行特判；catalog中的行业样本不足文字是证据范围说明，不是路由分支 |
| structure/layout/continuity/geometry/table measurements | 73个DU Python文件结构清单和import/体量扫描；pipeline接线、table purpose复用与coverage分支 | 未全面审阅所有几何/表格算法；不能给该层功能PASS |
| narrative_reading/operating session/business policy/support/passage | 主路径与关键状态转换详读；纯本地正反例 | SR-01确认；prepared assessment共享已做对 |
| narrative parser/legacy selector | 当前dispatch、版本选择、部分parse/模块边界 | 原parser不能因文件大删除；旧selector须保留历史replay；未跑PDF/OCR |
| summary_input/summary_tasks/source document projection | 阅读任务引用/预算/支持边界与主要projection；source_cards只结构定位 | Canonical span、单parent、support/context分区检查有实际价值；不是人工许可门禁 |
| decision inventory/dependencies 与 generation比较入口 | version构造、依赖回读、消费点及现有测试；纯内存bytes模拟 | SR-02确认；未跑catalog/cache复用 |
| narrative artifact/budget/retrieval/pdf enhancement等 | 文件级与literal扫描、部分调用关系 | 未逐行审查store/全文检索/外部解析运行；并入其他owner覆盖，不能说整层全读 |

使用CodeGraph取得DU 73个Python文件及source_catalog 52个narrative文件清单；explore只1次(maxFiles=6)。该结果混入的历史docs/.planning内容没有作为生产证据。主PWF仅只读CURRENT_STATUS/task_plan相关段，未创建新计划或修改ROOT状态。

## 检查的保留、合并与删除建议

| 检查/兼容行为 | 决策 | 理由 |
|---|---|---|
| 公司身份、immutable source/locator、同parent、原始顺序、support/context分区 | 保留 | 防止错误引用与跨原件串组；作用是来源完整性，不是投资批准 |
| 引用包所有数值的单位/期间与依赖闭合 | 保留 | 数字无上下文不能成为独立来源证据；未知保留而非伪造 |
| 文档WorkBudget/真实费用/时间上限及deferred说明 | 保留 | 已有成本边界；删除会破坏已授权额度，不能误当人工门禁 |
| 未命中有限“通用陈述动词”即relevant=False | 改造/取消这一否决条件 | SR-01证明其对完整业务陈述过窄；保留问题、模板、目录、纯会计、无主体依赖等负边界 |
| 同scope多次支持判定 | 合并到已准备owner | 当前主要路径已经用session缓存和passage；兼容调用fallback可保留，不能再增第三套词典 |
| 手写跨层hash模块清单 | 由reader recipe依赖声明取代 | SR-02；保留哈希校验能力，不删全部版本检查 |
| 旧selector/旧schema兼容 | 不直接删除 | 可重放历史artifact是实际合同；应隔离legacy实现与当前facade后再做可达性清理 |
| PDF child环境allowlist | 保留 | 限定子进程环境，防止污染；不向用户增加逐材料许可 |

所查narrative/DU路径没有发现private/public、逐文档人工许可或canary授权链。`approval/authorized`等字符串多数是原文业务规则（例如出口批准），不能误报产品审批。没有依据建议删除`needs_review`等质量状态：它表达未完成/不确定，不等于人为授权要求。

## 已执行诊断与交付范围

执行：CodeGraph search/context/files/callers及一次explore；生产代码literal搜索；AST模块行数/import/函数体量扫描；16条纯assessment对照；5条SourceOperatingSession→admission对照；5个模块的纯内存指纹模拟。首次Windows通配路径rg失败后改为目录 + `-g`，无写入。首轮Python stdout编码显示异常经显式UTF-8确认是输出解码问题，未将其误报为源码损坏。

未执行：pytest套件、source-select命令、PDF/OCR、公司run、新摘要/收费模型、下载、生产DB、技能部署。未修改代码/config/index/封存，也未触碰foreign `.githooks/pre-push` mode。只写本报告。报告完成后STOP；修复只应在用户另行恢复的实施节点进行。
