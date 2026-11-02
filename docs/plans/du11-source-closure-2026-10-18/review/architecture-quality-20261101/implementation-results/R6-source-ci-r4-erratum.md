# R6 R4 root erratum — 先冻结语义假设，再修实现

状态：DESIGN_AND_RED；ROOT已明确允许纠正本线R2/R3自增测试中仅由POS产生的positive期待。旧R3报告仍保留，不回写PASS。基线a6841e9独审有P2，未验收主线。

## 共同根因与最小RED

POS只证明句法matrix和NP/VP绑定，不能证明一个未知argument具有经营意义。原`_argument_relevance`把未知词默认为specific；随后既有`descriptive_operating_relation`只看operating而追加operating_mechanism，导致raw payload=None的marketing目标被标为fact eligible、relevant。financial exemption集合也不是独立payload集合。

当前最小8例：4F/4P，23.36秒。四个RED为remarkable ambitions、promising possibilities、ambitious priorities、pursue luminous horizons；已存在function正控、普通未知action原文、abstract+beneficiary负控4例PASS。草案`.planning/architecture-quality-20261101/r6-r4-design/test_unproved_source_arguments.py`，JUnit在隔离工区`tmp/r6-r4-minimal-red.xml`。没有为这些词扩展词表。现有真实/原CI20正控不改。

## 原期待纠正表（ROOT已确认，尚未修改测试）

| 本线自增类 | before | after及原因 |
|---|---|---|
| aim/strive/aspire reopen neonatal wards，and/or/but/倒序/嵌套 | support+relevant | 无既有正向argument proof，仅POS，改为unresolved+irrelevant；全文/顺序不变、不fact |
| committed treat rare diseases、CN努力重开/运输等纯未知goal | support+relevant | 同上，语义能力未知而非已证套话False |
| supply surgical services + create value | support+relevant | 陌生modifier不能证明经营目标，仅POS，unknown |
| supports portable compressors（R3新例） | unresolved+relevant且fact mechanism | 这是错误设计假设；改为unresolved+irrelevant、raw payload仍None、fact不升级 |
| 原已绑定actual function/quantity/coverage/causal/billing | 已有positive | 保留，不降低原CI oracle |
| direct quantified operating goal | unresolved+relevant | 原量角色owner正向证明，可保原文；不制造当前数字事实 |
| 一体化生产服务覆盖多个下游客户工序（原CI） | 可选叙述 | 保留；由共享composition/coverage owner增加通用定性operating/process范围绑定，不能借POS或补一家公司例外 |

完整before观察（包括raw roles、原relations、passage和fact）在`.planning/architecture-quality-20261101/r6-r4-design/expectation-before.json`。

## 实施设计

1. 同一prepared relation observation记录原bound relation reasons与independent payload（不以financial exemption集合判断）。callback、bound_payload和fact消费同一结果；泛operating_mechanism须原positive payload，不能由operating语法角色推出。
2. source relevance为三态：已知abstract明确context；原argument owner positive可读support；无positive的generic function/goal为unresolved且relevant=False，保留原话/角色None。普通未知实际action可读原话不成为typed fact。POS/资源失败仍原deferred，不伪装成已证空业务。
3. goal直接argument调用原argument owner的positive语义，不把未知NP默认具体；不从beneficiary/background borrow，不加入公司/行业/营销名单。quantity回调仍原owner+memo。
4. qualitative operating coverage复用source offering subject+局部覆盖谓词+共享operating/process scope head，覆盖工序/流程/作业/operation/workflow与既有scope类，绑定同一assertion，不要求数字、不产生milestone。正控跨行业/语言/动作/地区；反控未知愿景、财务覆盖、流程指南、跨句donation。新增语义类归一owner，不为原单句开绕路。
5. 原WorkBudget、16M/112、resource/配置不变；prepared callback真/假结果和scope观察复用，不新增任务/身份/人工许可。只跑新RED与受影响有界组，原20期待/真实12unit检查点保持。

本稿不是验收或已实施声明，最终结果/版本/成本以R4完成报告为准。
