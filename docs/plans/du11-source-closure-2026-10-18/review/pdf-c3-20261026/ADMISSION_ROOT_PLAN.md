# 可读来源与摘要支持的准入缺口：只读根因设计

> 2026-10-28 实施修订：下文最初只读设计已实施到未发布的SOURCE v3。跨仓兼容已独审、公共联调、并线/部署；CWP生产源码仍不能发布。最新真实整源审查证实不能仅靠refs合法、reason字符串或三个gold就签收。当前优先执行本文末尾“SOURCE v4共同根因收敛”，其状态高于下文最初拟议步骤；不新增人工许可。

结论：低价值分类已经产生，但没有形成“该闭合来源scope能否独立支持本次业务摘要”的契约。来源阅读层为召回而允许业务章节中的描述材料；任务层把所有来源view变成task；source-card把parsed/nonempty视为可用，仅阻断已知数表歧义。因此footer、单位/期间caption、断词和孤立财务数都能获得合法task与basis。软target已不强迫填满，但无法撤销这些错误支持能力。

还存在第二类来源语义问题：若会计规则、股权计划目的等已被误标meaningful或operating_metric，仅加value_band过滤仍会漏。推荐先建立可读性/完整支持能力/此次用途的分离，再在已有purpose/relationship owner根修这类误判。不能在摘要compiler再造财务词表、指代解析或业务rank。

## 实际证据与边界

只读资料：hk-native-v5 `phaseC-090-64100fdc01a5.selection.json.gz` 与 `.input.json.gz`，压缩字节SHA与8个代码owner的LF SHA见同名json。未跑helper、测试、PDF、SDK或LLM，只解析已有gzip/JSON和源码AST。

- selection共112 spans，coverage_complete=false；source阅读1042候选/选择112。admission trace记录799次、104 admitted/695 rejected，抽样limited=true，不能把该104当实际task数或全量candidate证明。
- 实际请求55任务：23个priority=1/description/score=0；10个priority=1/meaningful_fact/score=3；22个priority=2/meaningful_fact/score=3。**首12个均为description，但不是前23个都为description。** source优先级数字来自来源意图，不是已证明价值。
- t1仅期间，t5仅单位说明；t3/4/10/11/12是footer；t6、t8是“非公”“非公認”，t7/9各为缺失完整GAAP限定的尾段；t2完整现金快照仍是本次经营摘要的低价值独立财务总额。这里分为“支持不完整”和“支持完整但用途不适合”，不能混成同一种坏解析。
- t21也是unknown/description/score0，却包含基础设施→产品→行业解决方案的完整定性关系；不能将unknown或description一刀切。t34/35为unknown但有实际成本/毛利原因，t37为风险敞口与无对冲政策，t30研发资源、t31未来计划、t38明确无未来重大投资均须保留相应用途和模态。
- t14会计股权激励规则、t15非GAAP定义、t16对账说明、t39股权计划年期、t41激励计划目的、t51公平值计量政策已获得meaningful，部分purpose甚至为operating/operating_metric。因此“score>0才发”“只发meaningful”“purpose非unknown才发”都不是共享根修。具体哪个谓词导致每个误判本轮没有执行重放，不冒称已经逐项定位。
- t55的服务月度使用记录/交付对应收入确认是有业务机制的财注正例；t50有持续经营评估和融资可用性上下文。不能通过删除整章财注、所有现金/收入/成本词来过滤。

## 代码链证据

1. `source_catalog/narrative_reading.py::_admitted:58`：既有非经营purpose、financial_only、非叙述marker及heading检查后，`scoped = section_role in _BUSINESS_ROLES`即可admit；并未要求fact.eligible。Chinese字词footer/单位caption含isalpha字符，不能靠既有纯数字/outline过滤覆盖。
2. `_candidates:548`在该结果后才解释meaningful，弱描述仍继承章节priority；description还获得章节scope_topics。`narrative_business_disclosures.py::reading_material_value:514`明确只解释价值、不改变准入。因此降为description本来就不等于不能被下游引用。
3. `narrative_business_policy.py::reading_financial_only:884`是既有金融谓词与source-purpose投影的责任层；SOURCE_ACCOUNTING并不覆盖所有现金/毛利表达，完整non-GAAP词组又可能被原生断开。实际metadata证明这些片段未被阻断，但没有必要在compiler复制一份更长的词表。
4. `document_understanding/summary_tasks.py::build_summary_task_plan:76`保留每个来源citation view，并把未分组span注册成standalone task。它只验证来源/成员/顺序/分区，不判断独立陈述能力，符合引用视图职责。
5. `source_cards.py::source_cards:81`只检查成员parsed/nonempty及table_structure_ambiguous；`source_task_admission:62`只依据available和精确scope去重给admitted。`reading_hint:31`将priority/value/score/purpose投影为提示，未参与可执行性。
6. `automation/narrative_model_scoped.py::compile_scoped_model_view:413`消费上述admission；model_tasks仅筛status=admitted。resolve_basis验证的是本地support ID，不验证语义/限定完整性，所以当前footer也能成为结构合法basis。instruction虽已禁止padding和无主体原因，不能代替来源能力判断。

## 建议契约：三件事分开

| 层面 | 含义 | 本次片段例子 | 责任 |
|---|---|---|---|
| 可读/可追溯 | 原文存在、parsed、source/locator可回放 | footer、单位caption也满足 | 现有source/SourceCard.available；不改成“坏来源” |
| 完整支持能力 | 闭合scope是否独立支持带主体/限定的陈述，或仅为另一事实的上下文 | 日期/单位是context；缺GAAP前缀是unresolved；完整定性机制可support | 来源原生group/reference/purpose/operating owner |
| 此次摘要适用性 | 已完整内容是否适合当前source-oriented业务摘要 | 独立现金总额通常只作资料；经营原因、风险边界、资源和计划可用 | 来源已判用途＋共享source_task_admission消费，不重解析正文 |

最小投影建议（名称供实施owner统一，不是新许可协议）：在现有reading structured_value/来源citation view上携带 `reading_support_use = support | context_only | unresolved` 及一个有界reason。判断按**source-owned support scope**，不是逐字符或每span单独投票；表格需要完整headers/period/unit，Q&A需要完整attribution/问答依赖。同一caption可作为别的合格scope的context，却不能单独变fact。实际可用字段先复用已有结构、reference状态、purpose与关系证据，不增加第二份plan/rank。

`SourceCard.available`继续表示引用可物化；摘要admission另消费来源use和当前用途，保留完整canonical source plan及对未执行scope的原因。不要把context_only伪标source_not_parsed，也不要通过needs_review/uncertain把不闭合支持重新放行。raw原文、ID、locator、support/context分区和完整成员不变；缺前缀只由原生闭合owner在有证明时恢复，compiler不得拼t6+t7或借邻task补限定。

来源判断不能直接写成“fact.eligible/meaningful为真才support”。description的具体经营机制、未知状态但有完整产品/客户/流程关系的定性事实仍可support；没有数字不扣能力。若现有识别尚无法判断，应明确unassessed/unresolved并保留资料召回与诊断，不能冒充财务坏行或从检索中删除。明确未知状态本身不变成商业进展或financial_exempt。

对于意义已误判的会计/计划规则，使用现有source_purpose与源绑定关系：区分规则条件与实际事件、会计计量对象与业务指标、激励计划与经营资源、审计行为与公司行为；用相同动词/数字但不同对象和语用的中性正反例固定，而不是新增公司/词句黑名单。完整风险限制、明确否定、未来投资披露、服务计费/交付机制不能因财经章节被排除。

## 责任边界、资源与兼容

来源层先做scope闭合，再给support use，最后按既有预算选完整包。只靠summary边界过滤虽能净化模型packet，**不会追回已经被caption/footer占用的112 selection预算**；本次reading diagnostics已有selection_spans budget_full观察。完整claimable anchor及其必需context应在同一既有账户被选择，孤立context不应因章节priority1成为另一anchor。不新增“只许N个描述”的quota，也不在B重排所有source任务。

建议实施顺序：A复用 `_admitted/_candidates` 与已有source-purpose/continuity关系owner生产有界use；B在既有source_task_admission统一映射，并由task投影携带来源判定；C仅按需要更新现有execution reason枚举和observer，不能保留“admitted表示可读”而继续让caller误用。旧/5显式兼容的原文卡不充当正式摘要；不要为清理packet把所有SourceCard.available改False，破坏资料使用与旧读取。

旧selection缺use需标legacy/unassessed；新付费生成应消费当前来源投影，不能缺字段默认声明闭合，也不在模型边界临时解析旧文本。历史已完成产物按原版本只读，不重新贴新能力标签。既有reading policy/producer/implementation hash、selection bundle和scoped boundary（已含source_card owner SHA）负责新语义身份，不另建授权、门禁、任务库或缓存。

Q&A不得因为question不能作公司声明而丢整个回答；来源view继续区分question、answer、operator/context及unclear attribution。风险的否定/条件、资源存量的期间与人头口径、未来模态、无未来投资、财注经营原因均作为正例完整贯通，context不能向support捐优先级或关系。

## 先TDD的可执行验证设计（本轮未执行）

1. 来源中性RED：业务章节中footer/单位/日期/断半财务限定均可读但不得独立support；完整经营说明即使purpose未知、score0/description、无数字仍可support。无章节证明的碎片不得借section title成事实。
2. 用同一语义作简/繁/英和原生断行变体：完整non-GAAP定义/财务快照与有经营原因的财务段区分；prefix丢失为unresolved；原生证明闭合后保完整限定，不能跨task拼。
3. 规则/事件反控：股权激励年期/目的与实际研发资源；公平值计量“减值/变动”与客户使用量实际变化；审计测试与业务交付/计费机制。不靠动词或“计划”一个词决定。
4. 保留Q&A完整回答/问题身份，风险敞口及无对冲政策，资源人头口径与将来招聘/投资，无未来重大投资，unknown完整经营原因，经营表格与不完整财表。比较/主体/币种/单位/期间原约束保持。
5. 协议RED：source use逐scope到scoped packet和resolve_basis；context-only/unresolved不执行，完整source plan/理由保留；同源多view不可按文本误去重，context不能捐能力，旧bundle读取保持而新生成身份更新。
6. 先用本次typed selection做0POST离线重放：首12不成为独立摘要任务，t21/30/31/33/34/35/37/38等正例不丢；t14等误判需source-owner真实输出判定，不凭手填expected metadata冒充修好。这里只能证明已选112 spans的投影，新全文候选/资源收益不能用该snapshot假称已验。
7. 大节点独审后，按原预算一次真实来源与actual sent检查，再做已计划的正式摘要。3gold不改、不豁免，空packet/少packet不是内容PASS；真实final仍需完整独审，不能把“没送垃圾”当“关键信息必然输出”。

## 下一节点具体文件与测试

最小产品owner按前述链依次为 `source_catalog/narrative_reading.py`、`narrative_business_policy.py`、`narrative_source_purpose.py`，以及 `document_understanding/source_cards.py`；若来源view判定需进入task binding，再小改既有 `summary_tasks.py` 携带，不新造plan。`automation/narrative_summary_execution.py`仅在新增准确reason/disposition需兼容时更新；scoped compiler原则上只复用现有admitted筛选、resolve_basis与source-card实施SHA，不增加正文分类。具体清单及每件职责见json。

先扩现有 `tests/unit/document_understanding_selection/test_summary_source_admission.py`、`test_reading_material_value.py` 和 `tests/unit/test_source_summary_tasks.py`。若无现有合适的scoped admission测试owner，拟新增一个 `tests/unit/test_scoped_source_capability.py`，覆盖实际packet/basis、旧bundle和新身份接缝。所有测试这里只列设计，未创建或执行。不能把此次native8/工具独审的PASS迁移为本设计已经实施。

本轮只冻结此设计与同名json，不改产品、测试、配置、PWF或原件，不运行任何复验。ROOT可据此固定下一节点PWF；不继续扩大只读调查。

## SOURCE v4共同根因收敛（2026-10-28，优先实施）

### 已有反证，不能绕过

- 单次组合影响域2534P/11F/11skip，77.04秒。没有超时，不再重复整域。工厂收购、制造基地投产、产能、客户复购等失败不是额度不足；nested例实际work仅14,688/16M且每物理edge只观察一次。
- 完整工厂业务句direct fact为eligible/operating，但SourceOperatingSession投影移除operating_activity后丢掉可支持性；“未知阶段不能假造进度”和“完整实际业务不能摘要”被混淆。
- 真实整份native /4仍有规则、套话与碎片漏网。unknown relation中“参与者”被切成“参与/者”，“经营租赁”被切成“经营/租赁”；出处refs落在assertion内不等于完整业务语义。激励限额、审计范围、前瞻性定义、业绩免责声明、编制假设及会计对账也不能因此变成独立业务事实。
- 相反，带字母数字产品码、代际序号的完整产品发布/平台上线被换行+任意isdigit二次推断为数列；同一SourceOperatingSession已给has_unbound_numeric_cells=false。必须消除相互矛盾的第二套判断。
- 会计/估值关键词作为“实际向客户提供的软件产品”的修饰语仍有误排。应按同子句actor、业务对象、动作、规则对象的角色辨义，不能添加软件产品名或“公允价值/期权定价”白名单。
- 原三项gold在实际新选材均保留（101span/2330units，6.178Mwork）；这只证明三组完整依据可用，不代表47个support view全部有用或模型摘要通过。真实服务交付、履约与计费财注仍须保留，不能整章排除。

### 责任与实施顺序

具体owner和11节点逐项对照见[已接受的v4详细设计](SOURCE_V4_DESIGN.md)。当前为实施中，不等待额外人工签收。

1. 先冻结独审中性反例、11原失败节点及实际新view的正负支持scope。保持原件SHA/原三gold/全部资源上限，测试可记录公司样本locator，生产不得按公司、页号、task号分支。
2. 来源层共享assessment统一“原文定位、完整断言、经营用途、阶段/模态、数列质量”五件事；出处证明不是业务事实证明，未知阶段不是碎片通行证。优先复用/修复现有SourceOperatingSession、business policy/purpose及typed relationship owner，不在摘要compiler或消费者再解析正文。必要时可重构现有共享owner，不因旧五文件边界强行叠helper。
3. early candidate和完整support view消费同一assessment及现有受界session。去除reason字符串回退放行、任意isdigit二次数列推断；完整的通用经营事件、资源变化、功能/用途/服务关系无需猜标准阶段才保留。真实规则/模板按其条款对象与用途识别，不能由另句业务词反向洗白。
4. 先跑新增中性RED和原11失败节点；只有确认过期的year label/topic精确元组夹具才由ROOT迁移，保留原业务、原文、边界、归属断言。真实业务漏召不能靠改断言解决。已将production测试湖移出pytest发现树，解决并发创建/删除目录干扰collection的基础原因。
5. 定向影响包通过后，整原件native读一次，检查原三gold及所有完整support view的财务碎片/规则/模板占位和新品/平台/产能等召回。关键节点独审检查相同源码，按实际完整范围签收；不靠三个gold替代全材质审查。

   新正式准备revision额外采用[业务恢复检查点](business-recovery-checkpoints/README.md)：旧3对象不变、新增产品发布和平台上线2项，分别报告旧3/新2；先查实际准入/请求，再独审正式摘要。不得改旧gold或把新增标准反写为历史已通过。
6. RF兼容`0991e25d`已main/远端CI成功，StockWiki`33534818`本地master（无remote）；安装四新进程公开字节复验通过。保持/4 wire不变时不为纯SOURCE语义改动重跑部署或模型。最终source域修复通过、全src类型检查与关键独审后再提交/推送CWP producer，更新本计划与收据。
7. 然后回到既定按需增强与配置内真实摘要、缓存恢复、FF/RF实际采用、新holdout及公司循环。PDF SDK启动慢保持单独根因诊断，不为本轮oracle重复120秒批次、不提高费用/token/切片额度。

### 实施验收口径

完整statement和实际业务召回必须正例绿；词内动词、残句、规则/套话不能独立支持摘要。原文/上下文仍可读，可用性不等于摘要用途。每轮只跑变化对应反例和必要影响包，未改变的绿项不重跑；一次全域已留证，不能隐去11失败、独审红或把接口绿当业务质量绿。

## v4复验与v5选材预算收敛（2026-10-28，实施中）

v4共享角色修复最终266项通过，ROOT全src396文件mypy通过；一次完整native读取5/5业务依据保留。独审112项110P/2F，全文读取38个support确认原13碎片/规则漏网已关闭，业务与服务财注正例保留。

尚有21个numeric-unresolved任务（其support21span，含上下文共31成员）占用选材容量。源码把任何未绑定数列直接称为可读business，再按原topic/section priority参与预算；中性1格实验3F/1P证明它们可击败完整业务。没有证明某个额外真实事实已被挤掉，不能夸大观察。

按[已接受的v5细则](SOURCE_V5_SELECTION_DESIGN.md)一次修三处接口：共享table_purpose识别已知财表account行→raw/context-only而非独立叙述anchor；经营未知数列仍可读/unresolved；同一use状态经metadata/finalize/BudgetItem传入既有heap，让完整support先于unknown，再保留既有主题公平、优先级和全闭合计费。预算、不完整表格质量、原件可读、具体融资约束/服务财注及旧协议回放不变。

ROOT额外协议/缓存包306P/7F（非全域）：四项是旧schema/codec/空请求夹具，已保持原意迁移；三项是真实海外渠道/交付地域及客户验证闭合召回，交同一共享proof根修，保留原断言。只复验这7节点、新S7反例及必要影响包，不重复313项或整域。新断言角色及预算模块实际字节均由现有inventory绑定，新增真实修改字节→complete decision失效控制；不依赖手动版本号或新签收链。

## S8：三轴收敛，原文可查不等于独立叙述候选（2026-10-28，已启动）

v5原S7、全局support-first、闭合成本、私有proof、3真实召回均已通过独审对应控制，ROOT原七失败与四个字节失效/共享缓存合计12节点已逐一闭合（11P＋仅剩旧投影元数据夹具修正后1P，不重复整包）。原件复验5/5业务依据保留、38个support原文集合与v4一致、全src396文件类型检查通过。

但新独审100项98P/2F冻结出更底层缺口：通用“Other/其他＋三行数字”无任何业务证明仍独立offer。只扩大account词表并让unknown用剩余额，会继续把未归属裸表当叙述记录。剩16未决表格行的真实存在是反证，不据此造公司/页号条件，也不假称它们已知属于金融领域。

| 来源材料 | 原件/索引可读 | 独立叙述offer | 可支持模型生成 |
|---|---|---|---|
| 已知财表account裸行 | 是 | 否 | 否 |
| 未能归属的裸数字行 | 是，保持未决 | 否，不假称已识别财表 | 否 |
| 有经营量纲/业务原因的未绑定数列 | 是 | 是，预算低于完整support | 否，不补单位/期间/列 |
| 完整业务描述、标准stage未知 | 是 | 是 | 是，原模态/归属不猜测 |
| 已证明的经营表格 | 是 | 是 | 按原完整性/质量合同 |
| 合法闭合所需的财务/未知上下文 | 是 | 不独立offer，但完整依赖仍保留/计费 | 仅上下文，不捐赠事实 |

复用SourceAssertionRoles/table_purpose的正向经营证明，撤销“numeric未决自动等于business可读候选”的残余旁路。generation三值/wire仍/4；不新增classifier、来源权限或额度。无关裸数可仍标未决，但不必为了可查原文而预建叙述切片。保留Active customers、Capacity utilization、完整设备用途＋未知数列三个正控，required context例外与未知阶段完整定性句正控。

只对物理已完整读取、确为结构化raw-only的文档沿既有skip终态，不因无摘要而调LLM/反复重试；未知prose、未读页、预算耗尽不能伪装无关而跳过。先新paired RED与必要影响包，再一次真实5gold/全部views独审；不逐财表字段续加特例、不重复未改变全量。

## v6c组件结案与下一步

 共用typed断言/对象动作及用途证明；可读原文、独立业务候选、可生成支持三轴分开。财表行、残句、页脚和规则套话保持原文可检索，不再靠章节位置取得独立摘要位；实际业务因果、服务交付/计费、资源、未来及否定保留。未知叙述和未读/超限不能被当作“无内容”跳过。当前reading_plan/3只接受来源完整处置证明，旧1/2重放计数兼容保留。已有同一预算heap按完整support优先，无公司/页码/产品码特判、无新许可、无提高额度。

**真实复验：** 同一金山云2025半年报2330units，112→81个完整来源片段、38个support任务全部保留，5/5业务检查点均在准入任务内；4.139秒、6,175,509/16M work、原件SHA不变、0SDK/0供应商POST。原三gold与旧失败记录未改；新五项金标是新revision用，不能反写旧摘要通过。最后作者53P/6.16秒，独审32P/6.96秒、24文件冻结一致，全src396文件mypy通过。原失败节点已按原意修复；计数有重叠不相加。


最终组件独审PASS，见[SOURCE_USE_ACCEPTANCE](SOURCE_USE_ACCEPTANCE.md)。正常发布→真实配置内摘要/cache/FF-RF→holdout，整体ACTIVE。
