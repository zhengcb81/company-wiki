# ROOT source-scoped正式摘要实施卡

2026-10-15；原共享阅读PWF Phase B/C，不另建计划许可链。DU4-TABLE/STATE/FORM仍在独立作者目录，本卡全部由ROOT实施。

## 本节点固定接口与实施顺序

### A：实证与RED（进行中）

真实六错引、PD5/Matrix等遗漏及20/20 decoder精确映射已经冻结；逐claim锚点观察28PASS，正式摘要质量仍FAIL，不用测试绿替代质量。独立架构只读7责任文件，不读PDF/API。

### B：统一责任层实现（尚未全部实现）

1. 新 `document_understanding/summary_tasks.py` 只把已选canonical EvidenceSpan和来源reading_context group/views变成 `SummaryTaskPlan`，原文不复制，不做第二轮业务排名。`SourceSummaryTask`固定fields：key、member_ids/support_ids/context_ids、kind/section_role、source原有topics/reasons。短key仅本次呈现；完整原文引用/源组及plan digest仍由程序持有。QA两个view保留，真正ungrouped才单独建任务，不能递归扩张overlap或借邻居。
2. 来源任务输入全部原有selected素材均可回开；task plan提供已观察的任务/方向范围和max_claims，不声称全文或所有语义覆盖。后续只有共享策略/依赖责任层可添加有证据的指代/对象关系，renderer不能猜该系列定义，也不能读取gold。
3. 新显式 `reading-model-input/4` 的编译/解码另分 `automation/narrative_model_scoped.py`，一次API内任务局部草稿，原文只出现一份。共享标题/QA/表头用source图back-reference，唯一正文尽量放在本地任务旁，模型不抄全局长hash。basis只能指当前任务source拥有的part，程序恢复完整闭包和QA support/context；不能凭输出文本自动补旁边出处。
4. 旧None/v1/v2/v3保留instruction/schema/data/HTTP/解码/历史恢复金样；新协议独立因果身份。先明确测试再接 `narrative_model` 有限版本分支、generation/factory/summary实际调用及现有预算/语言观察；不改配置模型参数，不增加N次调用/失败自动重发。
5. 将原生source语义意图/指代关系与覆盖分配接入唯一shared policy；DU4组件交付后ROOT合流。只有任务键合法不足以证明任意paraphrase正确，需逐命题真实语义节点。不得把全文摘抄当质量改进。

### C：集中工程＋真实质量（未完成）

原28观察、旧请求金样、QA/表格/多source/预算/恢复契约集中跑一次；正式worker→verify→public read→RF离线联调；然后按真实配置MiMo/DeepSeek/MiniMax冻结候选摘要与独立审查，对比原错引和真实新公司，不改原分母、不删失败。保留费用/原件/Temp/诊断。默认仍0.8，只在整个Phase C通过后讨论默认切换，不新增小节点签收。

## 独立架构报告（设计依据，未实现内容不可写完成）

# 正式业务摘要：从全局选引用改为 source-scoped 草稿

2026-10-15，独立只读设计调查；`attribution_release_review`。

## 一、建议与不能承诺的边界

建议下一版本同时做三件事，不能只改prompt：

1. **唯一共享阅读引擎形成有证据的叙述任务和覆盖计划**：让“该系列”的定义、阶段、否定/限定条件随原生依赖进入同一scope；业务方向的内容分配使用已有policy/priority，不在模型层再写一套公司/产品选择器。
2. **一次API请求内的source-scoped草稿**：原文只出现一份，按原生章节/共同上下文组织，把短任务key和原文放在一起；响应内容放在相应task下，程序恢复其支持链，模型不再自由在96段原文、64个长hash和64条strategy之间挑引用。保留20条和现有8192 token/模型配置，不能变成每unit一次API。
3. **分清确定性来源链和语义保证**：局部basis、角色、对象/数值/期间等已有类型约束能确定性检查的就检查；自由改写是否忠实仍需真实样本语义验收。不要以合法引用、数字都出现在某处、合法quote或嵌套JSON当通用语义证明。

**一次请求内的task scope不是模型可见性的硬隔离。** 模型仍看得到其他task，完全可以把A的句子放进B的槽。因此“程序选scope+局部草稿”是减少不必要工作、固定出处责任的架构改进，不是自动证明任意paraphrase正确。新方法必须用本次六条错引及换公司/文档的真实输出证明质量；不能只让结构测试变绿。也不能为了易通过，把用户要的有效摘要默默替换为整段原文摘抄。

## 二、真实请求的具体负担

调查对象：`live-20261015T184634-4e0b40` 的实际cn-h1 input/response/bundle和逐claim审查，没有读取PDF或调用API。

| 实际观察 | 数量 |
|---|---:|
| 原文记录 | 96 |
| 不同citation units | 64 |
| strategy group行 | 64 |
| unit member refs / support refs | 135 / 135 |
| 原文字符 | 7,769 |
| model data UTF-8字节 | 55,329 |
| 完整JSON body按紧凑等价序列化字节 | 62,496 |

同一原文已经只发送一份；不能误称当前在重复发送整份全文。重复引用主要是共享标题：MOCVD标题被10个unit引用，薄膜研发标题9个，ICP标题6个等。模型当前做的是：

```text
读eN原文表 → 找u_hash对应哪些eN → 找strategy里的u_hash → 合成20条 → 再输出u_hash
```

长hash缩短只能省若干字节/抄写负担，不能单独解决语义归属。本次20条decoder都按真实unit正确展开，六条依然错引；错误没有发生在程序hash映射，而发生在模型把命题与合法unit关联时。

六个真实反例：

- c1的研发数字在e15，却选了e14/e16。
- c10从e29/e31借产品定义/特殊器件进展，实际只选e28/e30；e30开头“该系列”本身还有语义依赖。
- c11概括Uniflash定义与交付，实际选了e28/e33的ALD氮化钛。
- c12 Micro-LED+GaN选了红黄LED的e47；c13 SiC+红黄LED选了InP的e48；c14 InP选了红黄LED开发的e46。
- gold critical的PD5完全漏写，同段Matrix也被压掉。EPI、气体净化、数字平台等已在输入中仍未覆盖。

详细原文/真实support/context/locator见既有独立审查，不修改付费证据。

## 三、共同责任层：已有对象及其缺口

### 已有、可以复用

- `NarrativeSelectResult`：同一source/subject、96个原始span、selection/reading_context/reading_dependencies；不需要第二份来源注册表。
- `reading_context` context/2：原始group及source-owned `citation_views`；QA支持/上下文分离已存在。
- `CitationUnits`：完整成员、事实support、group映射、去重顺序、same-parent约束；保留为程序侧闭包编译器，不再强迫模型抄它的长hash。
- 共享 `pipeline/strategy_binding/orchestration/summary_input`：唯一profile/业务facet/章节优先级/依赖，不另起模型侧业务排序器。
- `narrative_reading`：native-continuity原文、候选/最终选择、完整成员/上下文。其 `_context` 当前压成kind/section_role/group成员，**丢掉了多项决定草稿分配的意图**；不能在模型层靠猜文本重新推回全部意图。
- `SummaryClaim`/`validate_summary_claim`：来源已知、角色、context same-parent、质量投影。它不提供通用entailment验证。
- 现有generation/selection材料hash、AUTO/费用、response hash和旧版本解析/恢复：继续同一体系。

### 当前没有的能力，需明确新增

- 来源拥有的**摘要任务计划**，包含scope内哪些对象/业务方向需要被保留、是否因20条预算而defer。
- 指代/对象限定的语义依赖，不只是“本段有标题”；“该系列”不能只带“薄膜研发”标题便称语义已闭合。
- task-local model renderer/decoder及稳定映射；当前只有全局flat claims+任选unit列表。
- 逐claim source-basis记录及局部可检查约束；不能说现有quote/citation验证已具备。
- 源输入覆盖、摘要覆盖与语义质量的分离观察；当前固定target20不等于重要业务都保留。

## 四、拟议接口：先冻结责任，再TDD

以下是ROOT可实现的拟议接口，不是现成端口。新增内容均为源处理/摘要表达，不涉及研究结论或第二任务库。

### 4.1 `SummaryTaskPlan`：共享引擎拥有，模型编译器只呈现

建议内部versioned数据：

```text
build_summary_task_plan(selected source material, reading intent, max_claims=20)
  -> SummaryTaskPlan
     source/subject + selected material digest
     tasks: ordered SourceSummaryTask
     coverage: required/recommended/deferred source obligations
     limits: existing chars/tokens/claim limits

SourceSummaryTask
  task_key: transient short local key (e.g. t07)
  source_scope: immutable source parent and known group/view references
  support_members: exact canonical span IDs
  context_members: exact source-required context, disjoint from support
  role/modality_constraints: only actually observed source constraints, unknown allowed
  purpose: existing policy/facet/section intent, never source fact
  coverage_keys: source-owned scope/object/topic references
  origin: native member IDs/locators and dependency reasons
```

- 这个plan是现有selection的有界派生view，不是新的canonical group库。不能在summary模块新增公司名、产品名单、日期白名单或行业特殊分支。
- 先确定source原生scope，再编译模型展示key；短key不作为持久身份，完整members/support/material/策略hash仍在程序映射与请求身份中。重排任务可以改变这次request字节，但不会改原文span ID。
- QA answer/question是同一exchange的不同视图：原文只保存一份，输出scope的事实support不能因问题视图/展示顺序改变。required context不能授权事实或翻译。
- 对非QA，不可把原本只是排序用途的anchor直接当事实support；事实支持边界必须由来源语义责任层声明。未知就保守保留，不把标题/邻居变成凭空事实。
- 支持跨多个有原生关系的fragment才能完整表述的事项，例如产品定义+“该系列”客户进展，必须由这个plan保留关系。不能到decoder看到模型写了产品名后才自动搜邻居补引用。
- 不把所有未知完整性都变成阻断：该任务可以标`needs_context/deferred`，独立闭合的其他业务事项继续产出；诊断不成为许可链。

### 4.2 coverage allocation与native依赖

使用现有共享策略的business facets、section priorities、native结构/父范围和实际已读材料形成覆盖义务。不能在renderer里重新排名，更不能从gold读生产必选事项。

- “业务方向/明确产品代际/阶段差异”是覆盖单位，不是每个动词一个claim。允许同一业务对象的自然复合句，只要阶段归属清楚且支持充分。
- 主营产品、明确新产品/新业务、经营项目、行业/出海等按该文档现有profile处理。重复描述一个方向不能挤掉另一个已读且重要方向。
- 当重要事项多于20条可用空间，计划要明确本次输出范围/压缩分配与deferred；不能偷偷发送64条文本草稿再截成20条，不能声称已穷尽全文。
- 原始selected96项继续保留且只一份；任务计划不允许未经记录丢弃其中的素材。未用于最终摘要的事项仍可检索/回开。
- “该系列/该设备/this platform”依赖只沿已验证的同原生窗口/章节/父范围、显式对象定义/接续关系建立。需要有界成员和停止条件；跨产品相同关键词不能建边，不递归拉入整章。
- 表格任务交给同一typed结构/DU4-TABLE接口：原始row、header、period、unit与真实ref；不得把“拟达到目标”混成进展，也不得用same numeric literal判等价。DU4作者目录继续独立，ROOT只在已交付接口处接入。

当前真实输入中native_continuity的section_role大多unknown，不能假定它们已具有高质量产品标签。先复用已观测标题/依赖，逐步补同一共享引擎的source关系；无确定对象标签时保留unknown，不把global facet提示当事实。

### 4.3 新的model boundary：一次请求的task-scoped草稿

建议显式新版本，例如 `reading-model-input/4`、独立prompt/request/decoder版本。**不要就地改/3。**

输入展示应满足：

1. 全部原文正文按原生scope呈现，每个source fragment只出现一次。
2. 公共标题/QA交换等共享context只一份；真正重叠是图，不能为了树状展示强行复制或删除。允许有限back-reference到已展示的fragment，禁止三个全局表之间反复抄长hash。
3. 在task本地放短key、原文范围/源角色、明确阅读意图；标题可以直接用已有原文标题，不生成假公司/产品标签。
4. 典型结构是“章节的原文context + 局部tasks的原文body”，再为少数真正共享body保留同scope引用。代码可编译成稳定有限JSON，不引入任意模板执行。
5. 新response以task为容器，claim不再带可自由替换的全局`citation_unit_ids`。例如：

```json
{
  "drafts_by_task": {
    "t07": {
      "claims": [{
        "claim_id": "c7",
        "text": "original-language supported business summary",
        "basis_parts": ["b1"],
        "claim_type": "company_statement",
        "modality": "planned"
      }]
    }
  }
}
```

task key及b1是这次plan的本地有限标记；程序知道它指向哪个完整source span/支持分区。模型不输出source SHA、path、canonical IDs、自己定义的context或需要精确数数的原文绝对字符偏移。basis_parts只允许当前task内已经提供的原生part，不允许引用其他task。

输出总claims仍≤20、每条≤280字符，model/max_output/thinking等遵守现有配置。若一个scope需要跨几个part才支持，basis要完整包含，程序按照共享引擎的依赖恢复context；不能把任意多个task的内容合并后用单个task名蒙混过去。

对无法产出/未分配的scope保留有限diagnostic（例如not-selected/needs-context），不要求为64个task各写一段解释，防止结构化汇报本身挤占token。全局预算仍由既有HTTP caller判断，不新增一个LLM预算账。

### 4.4 Decoder、source basis与真值界限

拟议纯函数：

```text
compile_grounding_view(selected, source_task_plan) -> frozen renderer view + local map
decode_scoped_drafts(response, selected, frozen view)
  -> canonical draft + bounded grounding/coverage observations
```

- task key、part key、duplicates、source parent、QA视图、必需依赖、role/modality枚举、原语言等确定性检查由程序完成。禁止模型覆盖绑定。整条不合法命题按现有recover-whole-claim方式处理，不删一半引用后悄悄保留。
- 如果需要持久source_basis，存**span/range refs和source-owned约束观察**，不要再复制原文。可用现有SummaryClaim的有限additive可选字段风格；旧wire省略，严格消费方（包括RF）同步兼容测试。若本节点选择不改公共合同，至少保留可复查的raw response/request映射于既有受界diagnostic/产物机制，不能另建无界日志库。
- 精确引用/完整source basis只证明出处。数字/单位/期间的typed关系（已有或DU4 source binder返回）能做局部矛盾检查；不能以“数字都在本task出现”证明对象、币种、期间、因果关系、否定均正确。
- 原文摘录可以作为basis，合法quote也不证明自由paraphrase被它蕴含。不能引入一个默认返回True的“entailment validator”，也不能把未知改成通过。
- 建议质量观察分列：`scope_binding`、`source_basis`、`typed_consistency`、`coverage`、`semantic_review`。未做语义审查就写未验证，不把`needs_review=false`或合法引用冒充语义签收。这些是质量信息，不是新的人工许可。
- 自由paraphrase对同task内容仍可能张冠李戴，不能通过JSON schema彻底杜绝。本次及holdout真实语义审查依然是验收标准；如果选择抽取型basis辅助显示，必须明确它是支撑材料而非用来降低用户摘要要求。

## 五、兼容/因果/恢复不变量

1. None、v1、v2、v3 的instructions/schema/request/data/input hash/HTTP body及旧响应解码金样保持。新增v4独立分支，不改变既有v3 helper行为来省工作。
2. 新model view/compiler/覆盖分配及source dependency版本进入当前generation causal identity；每个请求的短key映射和确切HTTP字节进入既有reservation hash。不能只改展示而不记录它对模型输入的影响。
3. 旧已付费generation继续stage-scoped恢复和outbox，无重POST。旧pending renderer不可执行仍在实际summarize前拒绝，不伪装当前decoder等于旧代码。
4. SourceRef、原件、locator、QA角色和原语言仍由原责任层验真；model boundary不读磁盘、不parse、不搜索供应商，不跨仓写文件。
5. source task plan只能消费当前selected材料及其已冻结依赖。post-model不能调用其他原文来给已付费claim补出处。
6. maxclaims20、maxtext280、实际token/费用/响应字节/时间/空间上限不变；不增加N次API、无自动修JSON重发。调试观察只存小型受界refs/计数，不落全MD。
7. profile默认/生产selector切换与新boundary合入分开。一次新样本机械绿不能直接把0.9改成默认。

## 六、ROOT实施文件与合理分阶段

### A：先用既有真实反例冻结测试

测试夹具只保留必要selected原文、实际units、真实paid claims及精确source SHA/locator，旧原始gzip留证不改。建立“形状合法但语义错”的负控，避免测试只验证decoder会展开合法ID。

### B：共享source task plan和新model协议

- `document_understanding/narrative_continuity.py`及已有source strategy/binder：有证据的指代/对象/阶段依赖和源覆盖意图，唯一责任。
- `source_catalog/narrative_reading.py`：把最终选中材料的任务/覆盖意图带到边界；版本化、partial诚实，不在模型层反推原文。
- 可新增 `document_understanding/summary_tasks.py` 一类纯模块，复用已有policy/结构；不是第二ranker或source库。
- `automation/narrative_model_citations.py`：继续原有闭包编译；新展示编译器可分新文件，旧3函数语义不变。
- `automation/narrative_model.py`：有限v4 boundary、task-scoped renderer/decoder、schema及旧分支冻结；不把所有不同renderer塞成不可读条件链。
- `narrative_generation.py`、`narrative_worker_factory.py`、`narrative_summarize.py`：注册新因果边界、当前runtime版本选择、沿既有caller与语言观察。源阶段不额外调用模型。
- 若持久basis/coverage字段：`narrative_contracts.py`、`source_catalog/narrative_evidence.py`及RF唯一消费合同同步处理，旧可选字段省略金样不变；FF无需新增下载入口。

### C：集中真实验收后再泛化

固定同一配置/预算重跑原cn-h1，独立逐claim语义审查；至少覆盖新范围的另一家公司/不同格式，检查不是针对中微名字修好。已有HK/US真实问题也要适配到同一协议/约束验证。合并正常hooks/CI与PWF更新，但CI工程绿不取代语义节点。

这里不建议为了“确定性”立即对64个unit分别调用64次模型；也不建议改为每个产品写一个provider或skill。相同共享引擎+阅读策略仍是唯一核心。

## 七、TDD反例矩阵

### 结构/引用/请求预算（可确定性单元测试）

1. 原文96项在新request恰好一份；共享标题/QA重叠不复制raw；无unit因展示树化而消失。
2. 同source两个产品、相同验证/订单词：不同task各有独立原生support；短key重排不能改canonical ID；未知/跨task/duplicate key/part拒绝。
3. question和answer展示在同一exchange、两个role view；只选问题不能产生公司actual，中文问题不能授权英文回答翻译。
4. 该系列定义+后续进展的有界原生依赖保留；另一个无关产品/隔页附件/独立公司声明阻断自动接续。无证据指代为unknown/deferred，不拿固定前一段补齐。
5. 一条自然复合句允许保留，前提是同scope/所需part和阶段全部支持；不按逗号/每个动词强制拆分。
6. table同一数字出现在投资额/产能、两行同数、两个年份同数、万元与亿元、货币不同、目标与进展不同：只有对应typed关系才能判一致，literal相同不代表通过。
7. 总claims21、文本281、输出字节/unknownsource/invalidJSON/path/metadata覆盖保持拒绝；20条预算不能内部先造64文本再截断隐藏。
8. None/v1/v2/v3全部请求/HTTP/hash/旧响应金样原样；v4 hash含新编译/计划/映射，旧付费恢复不多POST，pending unknown decoder仍拒绝。
9. 改变policy、source、parser/真正依赖必失效；仅可视key不同不重写旧generation。源原文不变，配置/Temp/费用账不写穿。
10. 只有一次model.generate/HTTP POST；失败无自动修JSON或按task补发；实际配置的模型/thinking/token字段不变。

### 语义/覆盖回归（不能冒充纯schema证明）

11. 固化c1：正确数字+错误任务出处仍属语义FAIL，不能因为20.41等出现在别的task就通过。
12. 固化c10：钨系列定义、存储/逻辑/特殊器件进展需要真实支持part；不能只带研发标题。
13. 固化c11：ALD TiN子产品quote不能证明Uniflash完整系统交付；同一术语出现也不能洗产品范围。
14. 固化c12/c13/c14：Micro-LED/GaN、SiC/红黄LED、InP三种不同scope和阶段不能互借。
15. 错误文本放入**正确嵌套task key**，合法basis_parts也仍不能声称semantic PASS；此为“嵌套scope不是通用隔离”的必备负控。
16. 相同数字/相同客户验证词但对象相反、否定遗漏、报告期与发布日期不同、旧代与新代：按实际原文语义验收。
17. source selected已有PD5/Matrix/EPI/气体净化/数字平台/行业更新，明确覆盖/范围诊断；不允许20条主要重复同一方向却声称业务覆盖完整。
18. 当前事实+未来目标允许自然表达，结构字段不得反转含义；不是每个动词都拆句，更不能把保留阶段文字的WARN统称幻觉。
19. 合成同构公司名/型号与第二真实公司验证；生产代码不能读取gold或识别中微产品名，换别名/顺序仍成立。
20. 真实新输出若仍错引/遗漏，保存失败和费用继续共因修复；不能静默改证据、放宽gold或把旧0.8测试适配失败当新0.9质量失败的替罪羊。

## 八、未知风险与实际下一步

- 新展示是否改善MiMo/DeepSeek/MiniMax的引用正确率，尚未测量。不能把设计建议当真实成功。
- task分配可能提前丢重要事项；必须沿共享策略记录allocation/deferred并看真实PD5/第二曲线反例，不另加固定公司清单。
- 共享source是图；强行每unit完整内嵌会重复原文，强行独占一份会丢依赖。需要对真实overlap分型（标题/QA/表头/重叠body）并保留原生refs。
- 原生“该系列”依赖本身可能跨多产品或读序不确定，不能承诺通用指代消解；保守unknown而非凭相邻猜测。
- 新basis公共字段会影响严格RF consumer，需要独立契约测试；并不要求任何消费者访问CWP物理目录。
- 只靠输出schema无法证明一般paraphrase语义；不应再新造一个可伪造的“semantic accepted”布尔值/人工签收合同。

建议ROOT下一具体动作：把真实六条错引、PD5/Matrix遗漏及两个产品同构例组成集中RED；冻结共享任务plan和新boundary接口；实施一次请求内的局部草稿与源依赖/覆盖共因，再做真实集中语义节点。报告本身不新增审批或小节点审查。


## ROOT当前实现状态与下一小步（不新增审查门）

来源task view与逐claim观测已集中144PASS/8.50秒（含旧v2字节和v3/QA契约），mypy两责任文件与Ruff通过；新语义质量仍FAIL。下一步先在新model-scoped文件实现纯编译view：每source span原文只定义一次、shared标题/QA以ref保留图，task本地pN只映射自己source-owned support，完整hash/原文locator留在程序binding。`resolve_basis(task_key, parts)`只能恢复该task原闭包与QA support/context，返回的semantic_status永远not_evaluated，不凭合法task或quote宣布蕴含。其后才注册新v4正式renderer/decoder、费用/恢复/真实候选验证。生产当前仍v3，不先改配置或老字节。

纯view测试路径固定`tests/unit/test_narrative_scoped_model_view.py`；真实96/64素材、overlap、QA双view、多个source、局部key不跨task/不能选context作事实、未知/重复basis和wrong-text-in-right-task负控；纯测试不能使用真实API。该子组件未接线时只能称接口/组件完成，不能写正式摘要质量完成。


## 来源任务＋纯编译节点实收（生产v4仍未接线）

最终47组件PASS/4.30s，原None/v1/v2/v3/QA集中160PASS/8.08s是compact前快照；独立44PASS/2.88s同为compact前，最终defaults只读核对无阻断。无损回还测试覆盖实际角色/flags/kind/section/topics/all-parts与QA例外；实际source view30590B对旧同范围30758B，保留47813B退化初版和相应RED。完整v4 HTTP/token/真实语义尚未测。见[节点实证](../common-root-quality-evidence/source-scoped-foundation-acceptance.json)。

审查找到的两项新增helper边界已TDD修复：可变kind/section标签影响不可变plan hash，改为有限str字段；JSON对象role先去重会TypeError，改为按已有规则非str→unknown再去重。不重新做来源身份/SHA或引入许可。原始quote oracle的matcher/业务角色边界保持；显式负控证明错误文本搭配合法锚点仍不能称一般蕴含成立。合成夹具改metadata未重建EvidenceSpan造成的hash错误已在夹具修复；mypy局部list标注、测试角色预期、所有RED与初版结果均保留。

下一步必须注册显式v4正式renderer/decoder、因果依赖和现有worker/caller，不留作永久闲置模块；旧v3真实终文和None/v1/v2/v3 wire保持。source task的每个原文body只一次，共享refs是图；context不作事实，完整native scope闭包不表示所有命题真实。继续补共享引擎有证据的指代/对象和覆盖分配，再做离线正式E2E/恢复与真实配置供应商独审，原六错引与PD5/Matrix遗漏未关闭。


## ROOT下一正式协议接线细化（优先于报告中的示例字段）

本来源view节点5f54f81b已发布，远端CI38796376285 SUCCESS；正式v4尚未实现。未来clause只需text/basis_parts/modality；摘要编号和来源角色由程序生成，不再让模型重复抄已知ID/类型。当前公开canonical SummaryClaim仍沿原合同，不引入新材料授权。

# ROOT下一正式接线的已核源码接口（2026-10-15）

当前commit5f54f81b源码冻结，正常push验证正在跑，不改工作树源码。以下是下一节点设计，不是已实现/验收。

1. `narrative_generation._bind_reading_projection`在selector0.9且未显式冻结projection时，目前选v3。`generation_manifest(... reading_model_projection=...)`已有显式测试端口，不另造env override/config模型开关。新v4注册完成后才更新0.9新generation默认；历史manifest的projection按原值，公开selector默认0.8保持。
2. `narrative_model.resolve_model_boundary`、`reading_model_boundary_identity`和request `from_selection/with_output_budget`需要有限v4独立分支；request schema用新版本，不就地改v3。新compiler/sourceplan实现哈希必须进入v4因果身份，最终HTTP字节沿原reservation hash；当前view.binding_sha只证明引用映射，不是完整wire或实现哈希。
3. `_validate_model_software`在summarize前比较所需模型软件身份；已paid/verify/outbox阶段继续stage-scoped恢复。全narrative_model文件SHA会被新增v4改变，因此需要真实旧v3 paid/no-POST恢复反例，不能凭新metadata声称兼容。未知版本仍0POST拒绝；不得伪装修改后的软件等于旧SHA。
4. `narrative_summarize`从subject冻结projection，先validate_model_execution，然后唯一caller.generate，再decode。复用这条线，不新增model任务/第二费用账。
5. v4输出建议固定`sparse drafts_by_task: {tN: [clause...]}`，clause只含text/basis_parts/modality；claim_id按source plan/task+ordinal由程序生成，claim_type按source-owned support roles推导，source/hash/language/context全部来自程序。减少让模型重复抄已知字段；不把错误文字因task合法就当真。claim_type/modality必须复用原统一规则，不能再造分类分支。
6. response_schema不要为64个task复制64份schema；使用有限object +同一clause schema，未知key由程序精确映射验证。所有clauses先计总数再校验，21条不能按任务拆开绕过20条限制；key重复由现有strict JSON reader拒绝。坏条整条恢复，不静默删错引用或补邻居。
7. 当前source task仅保存原group scope；该系列定义/产品/阶段关系和重要方向分配仍需在唯一共享引擎native结构/策略层补有证据的依赖。native窗口8成员/4块等已有边界不能直接放大或把整章变事实。不要因source span原文相邻就自动归同一产品。
8. v4 request observer/测试response fixture必须同步真实shape，不能旧schema假数据装作新正式调用。下一次真实MiMo/DeepSeek/MiniMax遵守已有配置、统一2M/$20账，先冻结候选、0盲目重发；同时检验原6错引和重要业务遗漏/新公司。

正常prepush的全单元触发原因已经只读确认：changed_unit_tests将tools/及tests/fixtures/一律global；当前这批包含两者所以必走全suite。作为后续效率审视线索，不在推送过程中改规则或跳过检查。


旧v3请求和HTTP raw/official两快照已先离线冻结，压缩12415字节、SHA789c3e64d4d73656b85864b44c258cc1e9626bc36e0693a1e2ce2c999bc84a79，存于本节点[发布材料](../common-root-quality-evidence/source-scoped-foundation-publication-receipts.zip)。下一节点从归档解压为自己测试fixture再改正式协议，不能改后重新生成旧金样。


## 2026-10-15 ROOT正式协议接线决定（DU4继续独立施工）

收尾a89467b0已正常推送（148PASS/35.83s），精确查询该docs-only SHA当前无workflow，不称CI通过。第一次commit受瞬时index.lock拒绝；检查后锁已自行消失，未删锁，正常重试成功。源码节点5f54f81b的5689/24与精确CI成功不变。

下一段采用一个有限的 `narrative_model_runtime.py` 协议入口，旧 `narrative_model.py` 保持实际字节和类型归属，作为原None/v1/v2/v3的唯一实现；v4的独立模块承担新schema/局部草稿/绑定。这样新增协议不再使旧整文件decoder SHA无关失效，不复制旧引擎或伪造历史哈希。现有正式generation/factory/summarize/verify通过该入口选择；HTTP/caller仍使用同一request/response类型及费用机制。公开默认0.8、新0.9默认v3先保持，显式v4先集中TDD/真实恢复，source指代/覆盖尚未完成前不切生产默认。

先固化旧v3 raw/official实际request与HTTP和boundary identity，再写新task request/decoder、局部scope/QA/20总量/整条恢复/程序ID及角色/未知版本反例。新协议按任务原顺序生成ID，clause只允许text/basis_parts/modality，模型不能回填ID/类型；角色集合由source_catalog单一规则同时供推导和验证。v4实现hash包含入口、新protocol/compiler/plan和所依赖旧公共工具及角色规则；旧identity仍由原实现计算。coverage仅是来源范围观测，语义不自动通过。

现摘要handler whole-file validation identity在本节点接线后会如实变化；已完成typed摘要/verify/outbox不执行历史软件，仍按实际旧paid快照做0POST恢复。未完成且实际不可执行旧validator的任务继续明确不可用，不伪装兼容或盲目重付费。此段结束需报告真正覆盖到的恢复阶段。三个DU4作者目录/源码/测试/PWF只读，ROOT只改共享正式接线文件和自有测试。
