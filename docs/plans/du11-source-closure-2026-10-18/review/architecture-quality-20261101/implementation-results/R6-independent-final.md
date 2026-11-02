# R6 A域＋ROOT CI诊断集中独审

**结论：语义A域 NEEDS_ROOT_FIX（1项P2）；CI诊断两文件的本次范围 PASS。** 不能把作者746P或B域迁移PASS扩展成当前候选整体验收通过。ROOT已接收P2并安排按谓词/补语作用域根修，不需要新许可或再跑746域。

独审工区 `C:/Users/郑曾波/Projects/company-wiki/tmp/architecture-r2`，分支 `codex/architecture-rectification-r2-20261101`。开始时基线 `f298a383`，本轮审查绑定的旧版后由ROOT正常提交为 **`718fced8d0cc5b15fc9eb144982b627086eaf348`**，并未因此获得语义签收。审查者 `/root/rectification_review_a` 未改作者src/test、Git或主PWF。本报告/JSON绑定作者4源码＋新语义测试的5个SHA，另绑定ROOT CI工具/测试2个SHA，7份冻结内容在审查后仍完全一致。

## 实质问题 R6-A-01 / P2：抽象尾部仍能吞掉具体业务

位置：`statement_grammar/__init__.py:184-188` 把**整个剩余tagged串的最后一个VB**作为补语起点；`narrative_source_context.py:92-94` 再以所剩名词是否全抽象否决整句。这样没有保存各个并列谓词的补语归属，先前具体业务会因末尾套话而消失：

| 原话 | 实际结果 |
|---|---|
| `We aim to reopen neonatal wards and create value.` | independent，但 argument_nominals 只有 value；context_only / source_abstract_objective / relevant=False |
| `We aim to create value and reopen neonatal wards.` | independent；argument_nominals 为 wards；support / relevant=True |
| `We are committed to treating rare diseases and creating value.` | 只有 value；context_only / relevant=False |
| `We are committed to treating rare diseases at regional clinics.` | support / relevant=True |

具体诊疗/病区计划的存在，不应取决于与抽象目标的先后顺序。这里应保留带原有计划语气的具体业务原话，不意味着已经开业、完成治疗或成立新的typed fact。上述计划的 fact.eligible 均False，故发现的是**关键业务召回错误**，不是已经观察到数字或事实升级。

独立新增两个断言以实际公开 `prepare_reading_business_assessment` 重现，两例都RED；没有mock private validation、改原测试预期或加公司/行业样例分支。它是同一作用域根因，不能用“and之后再看一下”或添加病区/诊疗名单补丁。根修应保存控制谓词及其具体补语、并列关系和作用范围，同时守住相对从句、受益者/宾语中的动词不得捐成发行人动作，不能把纯抽象目标放开。

完整14项独立观察、两项RED测试与可复现源码已嵌同名JSON。ROOT及语义作者已获精确复现；修复版必须另绑新SHA并集中复审这个小组，不补写旧版PASS。

## 本次已经通过的独立范围

正常获准host Python，短自有tmp，共 **22例：20P /2F，21.84s**。没有重跑746域、真实H1、原件或付费模型。

- **跨行业三轴观察**：具体诊疗、果园服务、陌生设备用途、灌溉因果、中文歧义/明确片段、弱membership及非经营展品均通过实际assessment观察。设备被动用途仍 unresolved+relevant，未被POS补成support；中文语言歧义仍 unresolved+relevant、factFalse；明确“公司拥有的沿海码头”片段不相关。另一个主体的展览不得充当本公司财务原因。弱membership原句和带描述性相对尾部均 unresolved/relevantFalse；有业务服务头的membership保留。除上述P2，不把这些观察夸为开放域经济常识覆盖。
- **真实公开R4/R5 handler（3P）**：完整输入 selected/processing_complete=True；缺EN资源＋独立typed健康段 partial/False，source_readability diagnostic和健康span保留；from_dict/to_dict严格wire真实通过。旧可选字段缺失保持缺失，未知字段仍拒。只mock了必要资源缺失和原件reader夹具，不mock handler的私有验证。
- **准备/预算复用（8P）**：五类已知context在POS前识别、同Session访问不重复观察/收费；精确同clause OBJECTIVE一次（2例）；32/64/128长度的context访问线性（1例）。
- **实际recipe（2P，独立新反控）**：PDF与非PDF的 `business_algorithm_hashes` 都自动纳入新source_context，hash与真实规范化字节一致；仅在内存中改变该文件读字节，两个recipe都变化。没有手补全仓hash或反向import实现，物理源文件不改。

源码检查未见新公司/行业白名单。`_PAGE_NAME`为页码＋法定组织后缀的来源格式；courtesy/meta词用于有限话语角色识别，没有issuer授权或经济事实通行含义。句法owner只返回结构观察；source_context消费其观察并判source相关性；fact仍由既有关系/度量owner负责。职责方向比旧“完整句=经营support”清楚，但P2证明补语作用域还未完成。

## 计量与性能边界

新增source_context以每个prepared clause观察并存入SourceStatementScope；objective标志及矩阵观察复用，comma子视图各自有键，不以无关整篇文本反复兜底。`SOURCE_PASSAGE_SCAN_PASSES`从24到 **24+12=36**，显式对新增工作记账；总量仍 **16M/112**，POS仍 **32n+1、4096字符/1024tokens**。本次静态检查和上述复用/线性小例没有发现改总配额或扫描整份文档的新增回路。

这不是性能PASS。作者早期741例36.51s、最终746例111.94s的原始JUnit全部在，8份历史artifact的SHA均吻合；性能根因尚未确诊，不能写成宿主并发已证实。作者如实保留此限制是正确的。未来真实H1在不变16M/112下的召回/耗时仍OPEN；本次不通过多跑冷初始化来猜原因。

## ROOT CI诊断两文件

本次选择 **7例PASS**：两个新增长组/escaped UTF8案例，以及旧隐私body、25个体限制、参数组折叠、skipped两种状态；没有重复全部17例。

原单条约12000字符annotation在平台4096B边界丢后组的根因，已改为：按实际escaped UTF8字节生成总计有界inventory（12000B，超界明确披露），每chunk≤2600B；首个体diagnostic≤800B；其他group chunks在个体case尾巴之前输出。故首条在正常边界内，63个测试指定的长组均出现在模拟首10条/4096B可见区。超长身份有[truncated]，不会默默宣称所有未知长度的组都可无限保留。

短first-group行为、25个体案例数、后续未显示案例计数、失败body不输出、参数group不暴露参数值、skipped不读取旧JUnit等行为保留；Step Summary也加入有界group inventory。没有增CI步骤或读取凭证。本轮是工具代码/平台限制模拟验收，不是远端Actions实跑回执。

## 清理与结论边界

测试仅写 `C:/Users/郑曾波/Projects/company-wiki/tmp/a6`，basetemp长43，无重定位；完成后恢复初始不存在。观察/测试源码和JUnit全文以文本留JSON，无原件、图片、模型或源码副本遗留。作者7份冻结文件SHA前后相同；本轮没有动生产OCR、模型资源、配置或数据库。

**STOP。** CI诊断范围可随候选整合；语义A域等待ROOT已安排的P2根修和新冻版小组独审。整候选精确CI、真实H1、真实摘要、持久缓存恢复、RF经济采用及W23均不在本报告通过范围内。
