# R6 CI返修R3集中独审 — 来源仍需根修，结构消费者范围PASS

**结论：来源语义 NEEDS_ROOT_FIX（R6-R3-A01 / P2），不能签本候选工程通过。** 已冻结的纯DTO/partial-cache两项消费者迁移保持中间限定PASS。433/262/121作者绿不能覆盖本轮未见词独立反例，更不能代替完整候选CI或真实公司链。

审查对象 `C:/Users/郑曾波/Projects/company-wiki/tmp/architecture-r2`，正常提交 **`a6841e9420dbe3eb6dac6e30563c29e4293a31e7`**。作者8份源/新测＋另2份消费者测试，10个raw SHA与冻结收据及commit规范化字节全部吻合，独立测试后未变。审查者 `/root/rectification_review_a` 未改产品/旧oracle、Git或主PWF；设计预先固定在 `.planning/architecture-quality-20261101/r3-independent/`，不是看新输出后修改预期。

同名JSON保留10文件身份、原12项观察、独立23例源码/JUnit、作者历史13份artifact核对、旧oracle变化核对及清理收据。

## R6-R3-A01：默认specific仍是未知目标的正证旁路

独立使用普通未见修饰词/目标头，而非只替换原5个负例的outstanding/strategic/宏伟等词。公开 `prepare_reading_business_assessment(text, {'relations': []})` 的结果如下：

| 未见原话 | 实际结果 |
|---|---|
| Our platform supports remarkable ambitions. | 原角色independent_payload=None、无witness、bound_payload=False；fact.eligible=True / operating_mechanism；passage unresolved/relevant=True |
| Our platform supports promising possibilities. | 同上，未知弱目标获得eligible业务机制与相关性 |
| Our platform supports unfamiliar technical endeavours. | 同上；并非只遗漏一个goal同义词 |
| We aim to pursue luminous horizons. | 无typed fact，却成为support/relevant=True |
| Our platform plans to support remarkable ambitions. | 成为support/relevant=True，显式plan没有补出具体业务依据 |

这不是已观察到的数字、货币或issuer幻觉；问题是**未知/未证目标被当成业务材料正证**，放宽了后续候选准入；本轮没有执行正式摘要，未把这种路径风险冒写成已观察的真实摘要槽位占用。fact.eligible这里是现有阅读资料机制的eligible标记，不应夸写为已经产生投资结论；它仍与“无独立payload证明”的状态不相称。

对照保持成立：原`outstanding goals`和`宏伟愿景`仍unresolved/relevant=False/factFalse；陌生具体`modular compressors`、`cryogenic separators`和从尾气回收氦气的业务原话均保留。故不能通过加入上述5词或把所有陌生内容一概拒绝修复。

共同链条：

1. `narrative_source_context.py:63-69` 的 `_argument_relevance` 对未落入有限abstract/tentative规则的文本，直接默认返回specific；NP head或整个prepared target因此没有承担“未知”的责任。
2. context保持candidate，未知弱功能的原role留在fact_roles。`descriptive_operating_relation(..., include_source_descriptions=True)`只返回roles.operating；随后 `_detect_reading_business_fact`可给它operating_mechanism eligible。
3. passage的既有unresolved/relevant快捷路径继续保留正相关；显式aim/plan的新目标也可因默认specific走一般完整句support。

应在共同source argument/role owner上明确未知与正证的区别，并一致供fact与passage使用；陌生原话可被保留，不等于其经营相关或事实已获证明。不要扩无限marketing词表、公司/行业名单、整句补丁或改原oracle来换绿。

另外发现需同组核对的静态旁路：新的 `_independent_reading_relation`正确使用原独立关系种类交集，但 `narrative_business_policy.py:931` 的 `payload_observations.append(bool(relations))` 仍把所有reading reason作为另一处payload观察。**这条不单列为新的已证失败**；ROOT/作者应检查callback与后续投影是否共享强proof判据，不能只在早期callback收紧。本轮具体5RED已足以阻断来源签收，无需再扩大语义探针。

## 独立执行：5F /18P，16.92s

正常host、短自有tmp，共23项，未跑433/262/121或全unit。5RED均为上述未见目标反例。

18P包括：

- 陌生具体设备/分离器/回收氦气原话3例；
- 原known False与unknown None完整角色各1例，原观察没有被fact mask抹去；
- 英/中数量coverage、未来计划coverage、第三方coverage4例，reading有business_coverage_relation，legacy无该reason，且不造current-state/milestone；
- 无问号WH fragment在source roles与fact_roles两视图都不逆归；
- 实际公开selector对全财务无span，混合业务/独立财务及倒序只保留业务原话；
- 实际PDF/非PDF recipe绑定共用business-policy helper；仅内存扰动其字节，两条hash都改变；
- typed关系true/false memo、phase预算不足不预扫、target实际长度预扣和重复零重扫、goal能力失败public selector保健康scope并partial，共5例。

原5份来源语义oracle Git blob与9f基线完全相同；消费者两个文件是已审的owner/child-import迁移。没有删旧失败断言、换行业词或增加额度。作者13份历史JUnit的字节核对保留在JSON；没有把这些大组重新执行或与独立23例累计成新唯一覆盖数。

独审自己的12项观察先保存JSON后，打印格式器错误地从asdict读取computed property而报KeyError。随后直接读取已完整保存的数据并只修正自有格式器；未重跑12项、未改产品。正式23例pytest不依赖该格式器，5RED可直接复现。

## 已完成的结构消费者中间结论

`.planning/architecture-quality-20261101/r3-independent/intermediate_owner_review.md/json` 的限定 **7P/8.06s** 沿用：

- partial injection迁到真实source inventory owner，原False与comparator零调用断言保留；complete same正控、独立changed反控均有效；
- pure DTO child以-I/-S显式candidate src并核__file__，错误ambient树/错误显式树/强制catalog导入反控均有效。

这2份测试在a684的SHA未变，故没有重复7例或35整文件。该结论仅针对测试迁移与真实边界，不抵消来源P2，也不签外部canonicalizer或全部缓存恢复。

## 预算、性能、隔离

既有16M/112、POS32n+1、4096/1024仍保留，prepared target按实际Σ字符×8预扣；本轮预扣/memo反控通过。unit324s相对此前280s只是一次观测，非timeout、未确定性能根因；不因这44s添加每commit大组或反复超时检查。

所有新材料只在 `C:/Users/郑曾波/Projects/company-wiki/tmp/z3`，basetemp43、无重定位；结束恢复初始不存在。复现与JUnit文本留JSON，无原文/图片/模型/源码副本遗留，10份冻结文件未动。没有原件解析、模型/API/下载、生产配置/DB操作，W23不在本次重审范围。

ROOT收到5RED后已明确允许作者进入R4，当前工区可能继续变化。本报告的a684＋10seal只绑定上述实际测试窗口；不要求解冻后仍等于旧seal，不继续测试在途R4，也不借旧结果签新代码。R4中若纠正前轮自增的“POS完整即support”假设，须明确记erratum，不能覆盖原测试历史或原20项oracle。

**来源NEEDS_ROOT_FIX，STOP。** 精确5RED与共同owner已报ROOT和作者；下一步根修后只做有界复审，再由ROOT跑精确候选完整CI。本报告不签fullCI、H1、正式摘要/持久恢复/RF采用或whole goal完成。
