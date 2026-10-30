ROOT已接收本只读设计意见，作为当前C后续实施细则；状态READY_NEXT，未实施，不增加人工许可。基线f05576e5，外包W21三个runtime owner仍独占。先TDD修同owner两轴和业务因果，再共享闭合视图，不启动付费摘要凑结果。

# C 来源语义后续：只读设计审查（2026-10-30）

结论：需要修两个共用 owner，再改问答的支持范围。不能只拆 QA、为 VC 加一个词，或把 `unknown` 直接变成产品资格。本文件是设计意见，**没有签实现、真实金标或摘要通过**。ROOT 正在发布的四文件 QA 节点不受本意见改写。

## 一、已确认的两条轴

### A：语法位置不等于实体类别

`relations._classify_np` 现在返回 `(role, attribution)`，其中 role 混合了语法位置和词典认出的实体类型：只有 product head/operating theme 被归为 object；其余未知一概落到 actor/unknown。`_bind_event` 又用这个结果决定私有 `bound_operating_object`，最后影响已经准备好的来源 payload。

极小中性探针：`本公司现无生产QX-7（甲基环氧乙烷）的情况。` 已有真实 production relation、明确 object_refs、negative/current/issuer，但 binding=False、payload=None、无支持。只把对象改成 `QX-7材料`，同一句法便得到 binding=True/support。不是缺少语法宾语，而是实体词尾在反向裁决语法证明。原始探针输出转录见 C_SOURCE_DESIGN_OBSERVATIONS.json。

建议把同 owner 的私有 NP 观察分成三个独立信息：**谓词 frame 给出的参数位置、实体语义类别、来源归属**。显式宾语 slot 中的未知名词保留为“宾语、实体类型未知”，不能再当成另一个 actor；subject slot 的未知名词也不能自动成为已知发行人。实体/归属未知并不等于整个断言没有信息，也不等于可以直接 qualified。

独立业务证明仍需要共同满足：实际操作 frame 的局部绑定、完整可见的非空 argument、原始 actor/否定/条件/计划范围、以及不存在已证明的会计/行政/抽象用途。用这些正面语法证据形成局部 proof，而不是 `unknown -> product` 或“没有命中排除词就授资格”。财务报表、抽象效益、只有数字的参数、问题/引用/名词化、未闭合窗口均需控制反例。不要求加入化学品名或公司名词库。

具名参与方的联系/希望也是相同问题：两项明确来源参与方的位置和“是否识别为某种企业”的语义类别应分开。现有 `CUE_RELATED/CUE_THIRD` 与 session name_classes 可复用同源别名、控股股东归属；不能因未知另一方而抹掉整条已观察的联系，也不能将其认成发行人进度。真正缺失参与方或归属仍保 unknown，actual contact 与 aspirational cooperation 分别保留。

### B：经营解释不能被“出现收入”否决

沸石问题比“整个 QA 被后文财务传染”更深。把保存的沸石单元**单独**交给同一 `SourceOperatingSession`，仍得到 fact eligible=True、reason=operating_mechanism、purpose=operating，但 financial_only=True、payload=None，最后被 financial_only 拒绝。`reading_financial_only` 在 recognize 存在且 `_SOURCE_ACCOUNTING` 命中任一收入词时提前 True；`source_support_use` 又在观察局部 payload 之前消费这个 veto。单独拆 QA 不能解决它。

改动责任应留在 `prepare_reading_business_assessment`/prepared assertion 的共同语义层：把财务词作为要解释的 cue，识别**局部断言的用途与因果结构**，而不是把任何收入字样等同“仅财务”。同一闭合断言中，明确产品/客户需求/订单/量价因素导致业务收入变动，属于可摘录的经营解释；纯收入净利结果、会计政策、资金余额仍不是独立业务支持。反过来，单有 eligible、score、reason、泛“持续努力”不能成为财务豁免证据。

沿用 `SourceAssertionRoles` 的 clause/payload 三态与 prepared witness，新增必要的“业务因果局部证明”应在这里准备一次。`ReadingBusinessAssessment` 同时消费该 proof 来计算 fact、financial_only 与 source_roles；不得另让 source_support_use、relevance 或 empty policy 各扫一遍、各投一票。财务标签只影响自身作用域，真实未知保持 unknown/unresolved；不借额度耗尽做 False。

## 二、复用接口及 QA 范围责任

- `OperatingRelationSession` 已有 MatchingText/MatchingView、name_classes、relation_bindings、complete_assertion：在它的参数绑定 owner 内准备 A 的局部证明；私有 bool sidecar可以继续投影到既有消费者，公开 relation wire 不需要因本修复新增实体字段。
- `SourceOperatingSession` 已有 `owner_for/source_text/fact/financial_only/source_assertions`、analysis group、`maps/_original_refs`：继续一份预算、一份准备结果。给一个闭合 support view 建分析 owner时复用这些接口，不覆盖某个原始 unit 的另一个 owner，也不新建 store。
- `SourceAssertionRoles.clauses` 目前只有规范化 text，没有原文 offset；payload_witnesses 也只是规范化观察，**不能用字符串搜索伪造原文 locator**。需要更细支持范围时，复用现有 MatchingView 的位置映射，再通过 session maps 映射原始成员；原始 bytes/ID/locator 继续由来源层负责。
- `orchestration` 默认把 QA 全部 answer anchors 作为一个 citation_support_view；`_citation_support_views` 只滤 question/context roles，未分出独立经营断言。因此局部拒绝/局部证明都可能在整个答复作用域传播。
- 下一步应在共享结构/来源准备边界形成**闭合支持视图**：support 原始成员、必要 context 原始成员、闭合状态/原因。QA parent 继续表示“这是同一问答”，不再隐含“全部答复只有一个事实”。阅读/摘要消费同一个视图，不能在发送阶段重做句法分类。

闭合视图不是每句话独立：保留主体/产品指代、前置条件、后置否定/限制、比较基期、因果两端及必要原问题；同一问答相邻并不足以无条件合并，不同来源/不同轮次更不能借用。先复用现有 `reference_closure`、`local_qualification_dependencies`、`local_operating_context_dependencies` 的证明责任；若 QA 目前缺这些算法需要的 source adjacency，仅从同一来源问答/实测原生片段建立它们所要求的边，不以文本相似或模型推测补边。无闭合证明保留 partial/必要原范围。

只把 `[all_answers]` 改成 `[[uid], ...]` 不可接受。也不能只改变 citation views：如果 package 的 required 仍是全部 QA members，financial 后文仍会被每张卡重复携带，draft/token 成本不一定下降。应将闭合视图同时投影为既有 package 的 member/anchor/required 以及 citation view；可保留 parent QA 关联，但预算、选材、实际 sent task 必须消费同一作用域。保留完整原文供展开阅读，不强塞每个原文段落到每张摘要卡。

## 三、先 RED 的最小中性对照

| 组 | 代表输入/变化 | 应保护的不变量 |
|---|---|---|
| A1 | 同一生产否认，陌生代号+括号定义 vs 带“材料”词尾；再换另一陌生名及英语明确动作 | 参数位置由 frame，未知实体不变 actor，不靠行业专词恢复；不丢否定 |
| A2 | 同动作但对象财务报表、经营风险、泛效益、纯数字、未闭合截断 | 不因一个强谓词或 unknown NP 直接授经营支持；截断未知不判无用 |
| A3 | 控股股东具名别名与另一具名方已联系，并希望合作；新句转为发行人或另一个主体 | 联系事实/愿望分开；股东与第三方不能变发行人；不跨无界句继承 |
| A4 | 问句、被引用/否认的“已生产”命题、供应商定语 | 不能把问题前提、引用或第三方资格洗成发行人事实 |
| B1 | 单独“需求减少→某产品收入下降”的业务解释；同文添会计收入净利结果；次序对换 | 真实经营因果在局部/组合均可支持；不是只在 QA 拆完才通过 |
| B2 | 只有收入净利结果、泛“努力推动收入”或错配产品/主语的假因果 | 没有独立经营证明仍 context/unresolved；reason/eligible 不能当 proof |
| Q1 | 两个自足经营回答中夹纯财务/套话；JSON 与物理 PDF QA 同义 | 不让低价值段占独立摘要任务，不使后一财务段否决前一经营段；问题仅 context |
| Q2 | 句尾“但尚未验收”、下一片“这一变化主要由于…”、跨片主语/产品、比较基期 | 不因按句拆分丢限定/否定/因果主语；缺前文则 partial，不制造较小 complete |
| Q3 | 相邻另一问答、另一原件、错位 fragment、工作量中途耗尽 | 不捐前提；已确认项保留，未知项诚实 deferred；同预算且重复读 cached proof 无额外扫描 |

这些是代码应满足的对照，不是本设计审查已经运行全部测试。实际本次只做 C_SOURCE_DESIGN_OBSERVATIONS.json 的 6 个短 source-owner 输入及 4 个 NP 观察；不声称任何真实金标通过。

## 四、最小实施次序与验收边界

1. 在当前已发布 QA 工程之上先冻结上述两轴的中性 RED/原有控制，尤其把“孤立业务因果仍财务拒绝”作为独立测试，不以全 QA 失败替代。
2. 修同 relation 参数 owner 的两轴；修同 prepared assertion owner 的业务因果/财务用途。先相关短测和资源边界，保持未知与 non-operating 控制。此时不需要重跑 PDF/模型。
3. 对 QA 支持范围做共享闭包与 package/citation/预算一致投影，复用现有 session/映射；先验证“不能按句拆”的负例，再看财务段是否退出独立任务。无需新 gate/权限/协议库。
4. 输入实现稳定后做一次受影响领域检查和独立终审；复用保存 parsed 做真实重选/角色 oracle 对齐，记录旧基线不抹掉。若仍有来源物理缺口，再由 ROOT 与 W21 单一运行时 owner 协调读取；不反复重跑整批。
5. 最后检查实际 sent tasks 的内容/范围/费用，再真实摘要、恢复及 FF/RF 采用；工程绿、解析数/候选数增加或源词可见均不能替代这些验收。

本次未改产品、测试或 PWF，未读取原件、配置密钥或 W21 工区，未调用 SDK/LLM/下载；只有自有设计文件。意见交 ROOT 后停止，不接管下一阶段实现。
