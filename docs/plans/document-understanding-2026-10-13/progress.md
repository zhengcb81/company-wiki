# 当前过程记录（2026-10-21）

**唯一当前状态与接手入口：** [CURRENT_STATUS.md](../du11-source-closure-2026-10-18/CURRENT_STATUS.md)。整体计划仍开放，用户已恢复R1实施。旧记录中的“当前”“待推送”“Next Step”均只适用于当时，不覆盖此入口。

## 2026-10-21 R5受影响契约共因修复并线

隔离分支f1dba9b7及handoff已cherry-pick，master生产提交a5214bda。195项最终全绿，独审PASS；恢复public扩列反例而非降低断言。三源码在母工作树逐字节SHA等于被测/被审版本；Git LF与Windows CRLF分别记录。正常push/CI尚待本轮结果，不把旧76a CI转签新代码。药明康德initial封存不改，继续四审。

## 2026-10-21 R1首轮封存与四路审查

首家公司封存：639工件/36,665,980B全部SHA一致，RF实际产物partial；四路审查开始。公司累计39,026tokens/$0.009720（含MiMo401 unknown全hold），母账1,544,023tokens/$0.625258。DS成功与缓存零新增收费有原生证据；最新来源/桥接/外部校准/受控恢复未完成，不能用工程通过代签。R5隔离TDD及独审并行，未写母仓代码。

## 2026-10-21 R1恢复：holdout冻结与RF循环准备

用户明确恢复实施。已读取当前PWF、安装的RF审查/RF/FF技能与真实版本；并行只读盘点候选污染、本地原件及旧审查活动。发现既有audit公司池campaign保留NVDA首轮及未完成复验责任，须衔接；DU-BENCH另有已编写gold的holdout，不能自动当作全新盲测。当前未派executor、未新增下载或收费调用。

## 2026-10-21 文档状态统一

核对已发布代码与公开CI，纠正HK独审/核心收据/补写默认关闭/推送状态的过期描述；用唯一状态页统合产品进度、类型质量节点、剩余任务与暂停状态。当前代码CI为76a9440b / run39662983951 success；本轮只改文档，发布结果以本轮Git提交与push输出为准，不重签旧运行收据。

## 历史记录（保留原过程，不作为当前待办）

<details>
<summary>展开历史计划、验证和失败记录</summary>

## DU11 B2 三审修复；正式 C 首次真实 POST 后收尾失败 — 2026-10-18

三审 REJECT 的两个 P1（中文泛称声明、head 不比较）已修：head-first 专名提取、技术描述词黑名单、series/device head 强制匹配、前置“包括…在内的”集合、客户主语句归属、泛称英文短语不门禁。测试 105 PASS、selection 738 PASS；三源仍 10/10、7/7、8/8，US 未闭合从 11 降到 6。

正式 C：cn-h1 live 首次跑完选择→真实 POST→恢复→cache→cross-run 全链，但本机 TEMP 未设置导致 runner 把临时湖建在仓库内，收尾断言失败、receipt 未写出；真实计费已入母账（15,141 tokens / $0.002722，重复行按 attempt 去重）。第二次显式 temp 重跑 20 分钟无产出已停止。**C 仍 OPEN**，下一步先修 runner 的 temp 前置校验再重跑。

---
## DU11 B2 复审 v2 的两个新 P1 已修 — 2026-10-18

复审仍 REJECT：v1 的 P1 全部关闭（P1-4 部分），新增两个 P1——泛称句被当成具名声明（`We sell products`、`公司产品系列丰富`）、proven furniture 跳过后邻接比较错邻居。均已修复：专名化声明语法、声明后置的 collective、实际 head 识别、客户/供应商归属过滤、furniture 真实邻居 carry。另修 6 个 P2 并补 9 个正反例。

`tests/unit/du11_source_closure` 99 PASS、selection 738 PASS；真实 CN/HK/US 仍 10/10、7/7、8/8（0 API、原件/gold 不变），三源收据均可见 `REFERENCE_UNRESOLVED`（CN 5、HK 2、US 11）。详见 `du11-source-closure-2026-10-18/task_plan.md`。

---
## DU11 B2 独立审查 REJECT，P1/P2 已全修 — 2026-10-18

非作者独立审查判定 REJECT（5 个 P1、11 个 P2）。已逐条修复：声明上下文端到端进入 target 组的 citation context；envelope 按原始 unit 计数、carrier 展开全部 originals；声明 ref 改用原文 offset；跨页 `page_carries` 从 continuity 证明接线；内部声明只认 deictic 之前（forward=missing、内部竞争=ambiguous）；单卡 reference deferral 不再降级整篇 coverage；收据前置暴露 `REFERENCE_*`；产品 head 词表收敛为 `PRODUCT_SUFFIX` 子集。

`tests/unit/du11_source_closure` 89 PASS；真实 CN/HK/US 仍 10/10、7/7、8/8（0 API、原件/gold 不变），CN 收据首次出现 `REFERENCE_UNRESOLVED=3`、`REFERENCE_ENVELOPE=1`；t32/t34 仍 `selected_matches=0`。复审通过后正常发布，再进入正式 C。详见 `du11-source-closure-2026-10-18/task_plan.md`。

---
## DU11 B2 有界先行词已实现并完成三源回放 — 2026-10-18

B2 工程节点（当前唯一主线）已实现：product_reference 纯语法、`OperatingRelationSession.reference_closure`、`narrative_antecedent` 有界窗口与联合 envelope、`SourceOperatingSession.reference()`，以及 `_candidates` 中 readiness 先于 graph/fact 的接线。

真实 CN/HK/US 回放（0 API、原件/gold 前后不变、同 16M 账户）：10/10、7/7、8/8，selected 96；t32/t34 精确 SHA 不再 selected，p17「该系列设备已付运」按 `REFERENCE_UNRESOLVED/missing` 显式 defer（CN withheld 137，其中 reference 相关 3）。范围收敛为族/系列指代，单数「该设备/该产品」保留 legacy admission。`tests/unit/du11_source_closure` 78 PASS；全量 unit 除 4 项宿主环境失败（Git-bash msys、真实 config 公司数、sqlite tmp）外无新增失败。

独立审查与正常发布进行中；正式 C（三供应商原语言摘要、付费恢复、同/跨 run 缓存、FF/RF 真实消费）仍 OPEN。细节见 `du11-source-closure-2026-10-18/task_plan.md`。

---
## DU11 两卡已并线发布，三仓 CI 全绿 — 2026-10-18

**当前唯一执行入口：** [DU11 当前主线接手指南](../du11-source-closure-2026-10-18/review/harness-handoff.md)；当前发布/接收事实见[本轮收尾与保留项](../du11-source-closure-2026-10-18/review/du11-reception-closeout.md)，下一实现边界按[有界先行词最终接口/TDD](../du11-source-closure-2026-10-18/review/antecedent-source-interface-final.md)。不要重做已接收两卡，不把下方历史“待发布”当当前任务。

RF/FF作者交付均已进入各自主线。CWP producer0ccdc689：6801PASS24SKIP346.26s＋142合同PASS48.31s，精确CI39094787278 success；RF runtimef8002f5f及最终依赖表9669c4d7正常发布，final416PASS＋36子测73.74s，精确CI39095818018 success；FF main e8740748：873PASS7SKIP78子测91.13s，精确CI39095654355 success。两技能各6物理源码定点同步，FF依赖序原子安装并双根imports/help通过。.claude junction不重复写，无整套安装覆盖。唯一compatibility manifest已收敛wiki0cc/revenuef800/filinge874，皆远端可fetch，不追docs HEAD/递归pin。

本轮根修：最终reader manifest日期/provider优先旧query；CWP唯一canonical市场代码owner；单次metadata观察；真实PDF MIME/per-pair coverage；同parent预算线性索引；页内paragraph与全局ordinal分责/未知counter只defer；CLI ASCII JSON避免GBK/UTF8；qualifications准确class-info类型；既有公共mypy hook涵盖transitive scripts。完整unit以两个worker同600秒期限跑完，未删测/提阈值/绕hook。正常FF共3次尝试=2RED+1GREEN，旧fixture只补真实provider证明以隔离未知日期，原不重复下载/日期资格断言不减。失败收据保留，各独审绑定实际源SHA。

原件/gold/生产配置/密钥、作者树、Dayu/IQS不改，无新收费模型调用。RF3个旧assurance WIP保留，stage1观察到weekly_manifest变化如实记、不猜writer/不恢复；stage2前后相同。**一个RF外层审查Temp仍NOT_CLEAN：** 旧PermissionError后平台拒删，保留且未绕通道重试，内部E2E已恢复；不是生产原件丢失。未知发布日期/3投影仍source_availability_unknown，不伪造日期/新增许可。

**Next Step：** 整体PWF仍OPEN。t32最新实源诊断不再selected，t34仍缺先行词；先按最终接口TDD与现唯一source/operating owner实现有界前驱、original/analysis namespace和context闭包。正文+已有context+必要声明仍8原unit/4个(source,page,block)/2048chars、同parent16M，未知/多义/超限只defer该卡。完整节点后一次真实三源及独立内容检查，再正式配置三供应商摘要、费用/activation恢复、同跨run缓存与FF/RF真实C，之后holdout/RF循环。不新增小节点签收。

下方均为历史轨迹。本次后续汇总提交仅PWF/证据，生产代码仍与已绿0cc相同。

---

## DU11 接收完成，页内编号修复已合线；正常发布验证中 — 2026-10-18

RF外包已正常发布f8002f5f并核CI39092538354 success、6源码定点安装、3旧WIP不变。FF最终29个不同跨次控制通过，ROOT修复a9c2dcf7待CWP配套canonical reader接口先发布，不提前上线新flag。

CWP 32ab6e06及最新2022432e已分别合本地主线5ad4295f、0352c2b7。前一次6ee5ebf1正常push在600秒时完整unit约96%超时，未发布，失败日志保留于`.planning/shared-reading-production/du11/push-source-flow-reader-port.log`。现完整unit使用已声明xdist两个独立worker按文件调度；不删测/增时/跳hook。84相关控制通过、独立4项及3边界控制通过；真实超时双worker/SQLite实验返回124且worker和自有Temp均退出/删除，明确600秒测试期限另有约15秒既有关停，不把微型实验当全量提速证明。

实源页内paragraph_index与全局ordinal分责、未知底部counter不再提前释放pending半句；77相关控制及独立10个不同控制跨两次通过。实际CN诊断旧t32已不再selected，t34仍1，原件/gold不变、0API；不是冻结内容验收。详见[独审](../du11-source-closure-2026-10-18/review/page-local-readiness-independent.md)及[worker审查](../du11-source-closure-2026-10-18/review/full-unit-workers-independent.md)。

**Next Step：** 正常完整push验证本组件、确认远端及精确CI→FF正常并线/推送/安装。随后按现有先行词owner设计继续t34，源就绪再正式三供应商摘要、收费/activation恢复、同跨run缓存及实际FF/RF消费C。整个PWF未完成，不新增小节点人工签收；下方保留历史。

---

## 两张DU11外包已验收，物理/cache与FF配套读取接口已合本地主线 — 2026-10-18

RF正常发布main=f8002f5f，精确CI39092538354 success，18有限独立行为通过、2物理安装根6源码定点同步，3旧assurance WIP SHA不变。FF初审102主链绿后4反例查出当前发布日期/跨市场去零缺陷，ROOT隔离根修a9c2dcf7再独审28边界＋1真实HK TXT链通过，0ET/network、原件和作者树不写；待CWP producer先正常发布，再并线推送FF。见[RF发布](../du11-source-closure-2026-10-18/review/du11-rf-publication.md)、[FF最终联调](../du11-source-closure-2026-10-18/review/du11-ff-final-integration.md)。

CWP完整组件32ab6e06合5ad4295f：7源码与ROOT受审字节逐一相等；219物理/grammar/cache相关PASS10.11s、最终独立27PASS8.51s，reader端口59相关PASS37.37s及独立真实跨仓验证。PDF实际mime、pair级coarse/fine覆盖、繁体/English独立主语、线性扫描/真实grammar字节cache依赖已修；当前reader一次manifest观察并提供可选canonical_identity，FF不再复制市场normalizer。原shared预算/上限/原件/gold不变。B1已发布9c681ed2，精确CI39092308121 success（5221PASS/11SKIP正常push517.05s），本组件正常push/精确CI仍待，不能借B1代签。

**Next Step：** 正常发布本组件→FF正常并线/推送/定点安装；按[唯一/集体先行词设计](../du11-source-closure-2026-10-18/review/antecedent-owner-design.md)继续source readiness。最新真实三源仍10/10、7/7、8/8及canonical一致，但CN p17 t32/t34仍被选中，整体语义/指代闭合与正式三供应商摘要/恢复/同跨run缓存/FF-RF C仍OPEN，不能以gold命中或synthetic代签。新holdout/RF循环后续继续；不新增小节点人工签收。下方历史保留。

---

## B1 共享预算与线性索引已验收合入本地主线 — 2026-10-18

完整组件f5a26b48已合b2503245；739相关PASS/50.52s，最终独立9PASS/3.27s及3个有限控制，精确源码SHA一致。逐member重建背景集合的平方级路径已消除，几何/索引扩展先消耗同parent账户；两处预算不足仍先遍历的漏洞已修。原件三源CN10/10、HK7/7、US8/8和canonical一致，同16M账户未超额，0收费/0原件复制、gold不改、自有Temp删除。详见[独立审查](../du11-source-closure-2026-10-18/review/budget-index-independent.md)和[真实源收据](../du11-source-closure-2026-10-18/budget-source-replay/receipt.json)。

本节点正常推送/精确CI尚待，不将前置e33的CI代签B1；全量耗时仍未声称彻底解决。两张DU11外包已发出，作者树独占。**Next Step：** 正常发布B1，同时ROOT隔离继续跨页多原span/有界先行词闭合，再正式三供应商摘要/收费与activation恢复/同跨run缓存/FF-RF消费C；新holdout和RF循环仍OPEN。下方为历史证据。

---

## 已正常发布并核远端CI — 2026-10-18

已审来源工程与旧测试兼容修复正常推送至e33d40ed7688cfdcead1e02d55542f7026d0b8e5，远端master一致。prepush全量6741PASS/24SKIP580.05s、合同142PASS37.31s，无跳hook/提时限；GitHub CI352/runs39090720114精确HEAD已匿名REST确认completed/success。详见review/du11_source_checkpoint_published_20261018.json。旧4FAIL及timeout记录不删。

全量unit580s仍接近600s，不能宣称耗时已彻底解决。ROOT隔离下一阶段已实测16/32成员的源容器context访问288/1088次（平方级），并复现总budget耗尽仍扫描几何；正在统一索引与现parent budget责任层修复。跨页/指代source实际API RED仍在隔离工区，未混入本次绿色主线。两个外包作者树不写，原件/config/gold/累计费用不改。

**Next Step：** 完成同source owner的metadata线性索引/真实共享工作计费，再按剩余闭合设计完成跨页/有限先行词；源就绪后正式摘要与缓存恢复C、新holdout/RF循环。整体PWF未完成。

---

## 2026-10-18 ROOT 大节点更新

已审工程dd5e1f2f合本地b5d413d6，旧测试fixture修复44941956正常提交。来源短尾工程最终独立34PASS/8SHA及最终138相关PASS，真实三源当前源码0收费回放10/7/8，独审反例全部修复；见 ../du11-source-tail-geometry-2026-10-18/integration-handoff.md。当前正常提交并线/重推待完成，不能说远端已新发布。两外包作者树独占。

剩余跨页/指代共用owner细则已调查并纳入引用：../du11-source-tail-geometry-2026-10-18/review/remaining-closure-design.md。强调原多span、同AUTO/预算、target/context命名空间、实际家具/列证明及source-page-block计数；无新人工门禁。正式摘要质量C/新holdout/RF循环仍OPEN。累计费用/token不变，无新LLM调用。

---

## 2026-10-18 DU11 ROOT 实测更新

用户确认两张独立施工卡已发出；不触碰其作者树。正常push92976930没有超时：合同142PASS36.59s，unit6569PASS24SKIP4FAIL542.35s；发现三个旧测试未随并行phase/v7 nullable字段同步，当前仅测试修正102PASS，待独审及重推。不称远端已更新。

来源质量工程dd5e1f2f已提交隔离分支，未称内容C完成。短尾新接线行为RED6FAIL/8PASS，列证明反控再RED10FAIL/14PASS，修后183PASS5.64s；纯helper独立70PASS。CN真实0收费parse/select/typedcompile10/10，raw/gold不改、零复制，owned Temp删除，物理断尾已进入一个真实native range。仍发现模板勾选载体回流；跨页/指代与整体内容C仍OPEN，保留失败收据。

---

## DU11 三供应商真实基线完成，资料质量整改优先 — 2026-10-18

共享引擎、付费响应耐久化、activation及同/跨run缓存工程已提交并合主线。三家各一次真实POST：CN/MiMo、HK/DeepSeek、US/MiniMax，当前配置、原母账、原件只读且零复制，三处Temp均删除。新增已知45607tokens/14866microUSD；累计742228tokens/$0.421556proxy，401新增未知hold及历史7均保留。仅工程进展，不叫整体质量验收通过。

独审发现共同P1：会计/勾选/审计理财噪声、审计师we误认公司动作、断句/指代未闭合、表格年份/数值不齐。CN64卡含完整selected原文不代表语义闭合；MiMo坏排序已回退留诊断。HK合法55任务排序和缓存通过，但FF把9896/09896字符串不等当异公司导致下游FAIL；US59task中5因原字节预算deferred，独审确认关键RPO转化被噪声挤掉，摘要只6/8；三家独审均CHANGES_REQUIRED。不得把runner PASS、source金标命中或引用正确替代内容质量。

详细实测和独审见[三家真实基线](review/du11_real_v5_c_baseline.json)，整改和行为测试见[业务/主体/闭合施工细则](review/du11_real_c_quality_followup.md)。先统一源owner准入/连续/表格闭合与FF表示规范，不按公司补特例、不删失败/改gold/加人审；无上下文则显式defer，不让模型补事实。RF/FF两外包作者工区继续独占。

**Next Step：** F3身份投影已分配ROOT内部独立工区TDD（不触碰FF/RF外包），ROOT按F1/F2源准入/闭合/容量根因接口先写RED，在隔离工区集中修复后大节点独审/真实复验；已完成工程检查点正常推送并核精确CI。正式质量C、新holdout、完整RF审查循环仍OPEN。

---

## DU11 摘录式摘要与付费恢复工程实施中 — 2026-10-18

主线已发布2340b78c且精确CI Success（2m52s），进度文档345b58f0已推；新代码7a84f47b及测试目录解耦f60f109b已合母仓57d63e90，尚未标正式C通过。源卡/有限ID排序、完整paid body、同AUTO失败恢复、终态有界执行报告已完成组件独审和实HTTP装配。集中151PASS52.25s；其后补policy零调用误伤及预模型容量typed错误，分别真实1PASS13.36s/核心18PASS6.97s，最终生产代码增量独审PASS，真实C仍OPEN。原C失败/未知费用历史均不改，未新增真实收费调用。

最新范围、每份收据绑定版本、已发现并根修的问题、真实budget和测试残留见[工程进度](review/du11_extractive_engineering_progress.json)。旧默认V3兼容调查77项不作为当前源码验收；保留显式旧协议语义，调整新默认/假HTTP供应商的请求协议，随后重验必要公共链发现真实PDF跨run多一次POST；同一最终generation却因scope排序改变facet归属误失效。两纯RED复现，owner已做scope一次规范排序及稳定source-wide代表，inventory1.5；最终161项单元及29项实际公共集成全绿（15.08s/483.30s）；摘要/耐久恢复114PASS31.56s。真实C两次前置0POST发现测试工具隐式目录及未适配request6，已修显式来源配置和观察分发，37项含实际C loopback恢复全绿34.37s，独审中/待最终工具提交；真实累计费用不变。工具平台拒绝了自有Temp递归清理，未绕通道/重复询权，剩余独审夹具明确NOT_CLEAN，不把它说成生产原件损坏或全部测试已清理。

**Next Step：** 最终生产/公共读取增量验收与独审→提交新引擎→按现配置实跑三供应商C、paid/activation缓存恢复及FF/RF只读消费→并线推送核CI；新holdout及RF审查循环仍OPEN。两外包作者工区继续独占。

---

## DU11 上批工程已正常发布，新摘要模式隔离实施 — 2026-10-18

主线2340b78c已正常push，远端master实核一致；完整prepush6571PASS/24SKIP/0FAIL，542.66秒，未跳hook。精确CI #351/runs39082085864已由可见页面核对Success，2340b78c一致，总2分52秒/唯一job2分47秒。新隔离工区du11-extractive-runtime已写行为测试并实跑13RED/1兼容PASS（原先不支持v5/缺模块），再开始实现。两外包RF/FF作者树不写。

新执行审计端口采用仅内部job wrapper，public summary/bundle不变；同AUTO终态压缩须保留32KiB内逐task报告，否则正常收尾会丢审计。源卡预算是canonical64KiB内保守56KiB draft，剩余8KiB envelope余量，最终仍实际64KiB校验；完整support原文不截断，context引用保留，mixed状态只uncertain。缺model排序是unprocessed诊断，不删safe卡；原v4/已付费失败仍原语义。

**Next Step：** 集中实现/测试源卡＋ID排序、同AUTO完整paid response恢复与审计留存，独审全修后才恢复三供应商真实C；旧C仍FAIL/真实C及新holdout OPEN。累计628394tokens/$0.393953proxy，unknown历史7不删。

---

## DU11 下一实施位置：源摘录摘要与付费恢复 — 2026-10-18

离线真实响应已确认根因：64任务由模型自行挤20，22条不仅超限，还出现合法引用串产品、漏关键业务；不是8192输出不足。已完成独立设计审查，实施细则见[源摘录/恢复施工](review/source_extractive_summary_implementation.md)，输入/预算/版本/兼容/测试/独审边界已细化。优先实施源原文业务卡、模型仅排序/处置、同AUTO完整paid-response耐久化；不简单抬20、不改旧失败、不新增人审或第二store、不改两外包消费者源码。

正常push完整检查：6570PASS/24SKIP/1FAIL、538.30秒，非超时，未发布。唯一旧测试把fine max_pages=1误当“第二页不能有任何粗布局”，已保留原断言并增强真实WORDS仅1次、page2无words/cells+block，46集中PASS/4.30秒、独审PASS，生产源未改。下次正常push继续核真实CI，不跳hook。

**Next Step：** 正常提交/推送本次测试责任修正与已审实施细则；在隔离ROOT工区先写源卡/有限计划及完整响应恢复的行为RED，再按施工白名单实现，集中离线绿和独审后才恢复真实付费C。累计628394tokens/$0.393953proxy，历史unknown7保留；C/新holdout/完整RF审查循环仍OPEN。

---

## DU11 正式C第二次CN结果 — 2026-10-18（最新）

最终受审HEAD ae9a2fbb 的真实只读CN选材10/10通过，96片段7739字、64个source tasks；MiMo一次POST返回22条（协议总限20），整份以CLAIMS_LIMIT拒绝。原响应还见未知本地引用，进入离线正式decoder/taskbinding共因诊断，不修引用、不直接抬20、不盲重发；HK/US暂缓付费，避免重复共因。详细记录review/du11_real_summary_second_cn.json。

实际新增14819tokens/2681microUSD，累计628394tokens/$0.393953预算proxy，unknown新增0/历史7保留。原件/config/gold/sentinel不改、raw复制0、owned湖已删除。正式摘要C仍FAIL，付费恢复/缓存/消费者未到达。已完成源工程和独审结果保留，下一步诊断共享任务/输出容量与质量策略，再TDD修复后重验。

---

## DU11 正式摘要C前工程已修并独审 — 2026-10-18

RF/FF两外包已派发，作者树仍独占。ROOT已提交native布局75e024cf、推送诊断ec80b0c5；本次接收共享业务覆盖关系3文件，最终独审PASS/0已知未修缺陷。此前aafbd662已修模型展示metadata及下游诊断分层，原首批三例FAIL保留，不能当作真实摘要验收完成。

业务覆盖按同一有界关系owner处理，保留原文当前/未来及第三方状态、不推断市场份额或完成里程碑；/8只作用新reading路径，legacy0.8不变。独审发现并修金融主体/分母误升，常见收入/销售/盈利词族统一局部否控，仍保留前后独立财务分句和sales services经营正控；45集中PASS、独审15纯控制PASS，原190相关收据复用。版本测试改实时常量并保留test-next反控。

此前正确工区模块路径、同16M/96片段真实CN选择支持10/10、7739字、0POST；此收据绑定金融否控前c0f447版本，明确只作开发回归。最终受审20cb13f7尚须正式C实际实读选材/模型/恢复；不把旧10/10移给新SHA。首误载editable母仓的调查已记录NOT_TESTED_NEW_POLICY，施工总表已补运行来源要求。

范围工具两P1已闭：资源未知full、文件名字面量不能证明执行；本次bootstrap仍full，不宣称局部测试几秒即发布。超时日志GBK反例已修，保留600秒/红码124及真实子进度，未放行失败。远端当前仍4bc3492f、发布待正常push。

**Next Step：** 在本次最终提交HEAD串行真实cn-h1→hk-annual→us-10k（当前配置、同一母账、registered_readonly、仅0.9、activation-recovery），验独立摘要质量、公共read/同run及新run同AUTO缓存、FF/RF只读消费和精确清理；随后正常push并核实际CI。C、新盲样本、完整RF审查循环仍OPEN。

---

## DU11 来源复用与同run恢复工程已独审 — 2026-10-18（当前）

已接收8份冻结源码/测试：query与resolve共用当前来源事实，权威公司身份覆盖错误目录及旧ticker；handle只输出已有canonical ID，否则空列表，不造ID。相关102项通过（101+修正canonical夹具1，runtime不变），只读测试工具22PASS、恢复装配1PASS31秒。统一独审PASS/0未决代码问题，见review/du11_source_facts_c_review.md/json。三份真实SourceRef与正式语言准备已通过、原件/config/生产DB不改、0原件复制/0模型/实际预检Temp全删，见review/du11_registered_source_preflight.json。

模型C仍OPEN：下一步用现配置串行真实摘要，并启用显式--activation-recovery验证已付费outbox在同run/DB/workdir恢复0新增POST；现有loopback证明工程装配，不能当真实供应商内容绿。推送范围工具的共因修复由内部线在ROOT隔离树继续，不碰外包RF/FF；600秒超时历史保持，不跳hook或延长超时。

**Next Step：** 正常提交本次冻结C工程，然后真实cn-h1→hk-annual→us-10k；完成推送范围修复独审后正常push/核精确CI。两个pytest Temp共2,981,888bytes明确NOT_CLEAN并记录，未绕过平台拒绝。

---

## DU11 正常预推送超时与C工程 — 2026-10-18（当前）

第二次正常push在600秒总超时被拦，仍未发布；不得写远端CI失败或通过。实际触发比单个策略JSON更广：当前工具将整个tools/和tests/fixtures/归为全局，局部JSON没有资源依赖边，顶层tests/test_phase_c*.py又不属于现有执行测试识别。这导致无关全Unit，同时遗漏工具自己的准确执行消费者。ROOT将按资源/工程工具责任修复选择器，保留未知配置、全局入口、未知资源与生产动态执行的保守回退；不跳hook、不改CI全Unit、不延长600秒。

隔离C工程已完成来源事实统一投影及现有canonical ID的真实输出，正确公司可复用、错目录和旧ticker不能冒名；相关102项通过（最终101+夹具修正1，运行源SHA不变）。只读原件三例已进入正式语言准备，0模型/raw复制，生产原件/config/DB不改；同run paid-outbox恢复装配loopback1PASS、1POST/80tokens/110microUSD均无增长，均待最终统一独审。两个pytest自有Temp各1490944bytes被平台拒绝清理，保留准确路径与NOT_CLEAN，不换通道重试；实际三源预检Temp全部恢复。

**Next Step：** 独审C运行源/工具→提交进展；并行修复有明确归属资源与测试工具的推送范围选择，独审后正常push；随后/期间按现配置串行真实摘要、公共读取、同run恢复与缓存，不重复授权。RF/FF两外包独占作者树。

---

## DU11 工程接线已提交，正常推送修复中 — 2026-10-17（当前）

共享引擎生产接线提交d52a6562，正式CN/HK单账户选材与独立工程B审查通过，真实模型摘要/缓存恢复C仍OPEN。两张RF/FF卡已派发，作者工区不改。

正常push的完整预推送6455项结果6428PASS/24SKIP/3FAIL（585.28秒），未推远端。三项已从契约确认修正：旧测试不再要求空邻页扫表；零工作预算以完整text-only canonical身份对照，其他零cap仍对照table ID；offering策略canonical设计源同步已审1.0.3资产，运行资产字节未变。37集中PASS/5秒、独审PASS且18份B运行源SHA未变。只读测试工具删除query之后重复manifest精确门禁，正式语言owner/错误身份期间asof拒绝仍在，11PASS和独审PASS。

**Next Step：** 正常提交并推送上述修正，核完整预推送和精确CI；随后按[来源事实统一投影与C验收](review/source_metadata_reuse_phase_c.md)先TDD修复query/resolve事实投影，再真实摘要/缓存恢复。不跳hook、不新增小节点许可。

---

## DU11 真实全链容量诊断 — 2026-10-17

- 两外包卡已派发，ROOT继续独占CWP，不改变作者工区。
- 相同策略连续目录段合并，风险/contrary/gap边界保留；补未知前缀、未匹配导航有限探索和冲突页deferred。真正finder前复核预算，包括显式页/全扫0.9，legacy无账户路径保持。
- 新candidate支持分行表头与纯描述项目表，同页语义结果有界复用，重复30行解释31→3。源matcher及预算实现唯一；因果缓存覆盖真实桥/执行算法与采用策略。
- 1004集中首轮989PASS/13SKIP/2FAIL：一项旧测试fake缺正式metadata字段，一项offering策略有意增加发行人业务后旧指纹。独立核理由，单一offering gold升级、其他14未变；186集中复测PASS。新增探索预算公平隔离1PASS。套件重叠不相加。
- 默认真实CN283页单次TextPage、最多2native并存，93/94/223真实fine cells212/89/42，原件SHA/mtime保持，约10–14秒。HK p12 28cells，晚页deadline诚实停止，不宣称所有fine完成。
- 独立容量trace：parse1.682Mwork+同2M选择→0spans；未知导航局部收紧后parse1.268Mwork仍0spans。fresh2M仅诊断的selector也在layout/structure耗尽，说明既有全篇语义默认容量本身不足。正测阶段真实工作量后系统调整，未调用新模型。
- 唯一phase_c_runner的registered_readonly与single0.9升级9PASS，原件/配置/母账不变；独审PASS/0未决、源码冻结一致，已提交b914728e待正常推送，不把工具绿等同真实供应商绿。

后续修复已实测：组合默认16M由实际长文档9.2–10.8M工作量校准，未知探索固定封顶250k、显式小预算保持，source几何原上限不变。PDF子表裁剪同步只删合法移除cell的provenance，未知/缺ID仍严格拒绝。正式默认handler单账户、每源单parse、原文span验证：CN160/HK96有效片段，均明确partial，0收费/原件不变；不能把选材绿当摘要C绿。

**Next Step：** 最终工程大节点复审/正常commit/push/CI，随后真实摘要/缓存恢复/holdout。C OPEN。

---

## DU11用户已派发 — 2026-10-17

两条RF/FF外包已启动，由作者独占各自新worktree；ROOT继续CWP source/engine/summary/cache，不改它们的源码、索引或配置。

**Next Step：** 完成CWP真实默认深页根因修复及独立复审，然后按配置运行正式摘要/恢复。

---

## DU11 两条独立施工卡就绪 — 2026-10-17

独立审卡已PASS，FF卡最初把provider=None误指向专用lookup，已按实际普通SourceRequest/query_local及reader manifest接口修正并复核。两卡现在可启动，状态READY_FOR_DISPATCH（尚未获用户已派发通知）：[总表](parallel/du11-2026-10-17/README.md)。RF/FF独立新worktree和源码白名单互不重叠，与ROOT CWP生产接线无文件争用。每卡交接前必须独立agent全面审查、全部问题修复/测试绿、按最终源SHA复核，0未解决才交接。

ROOT主线A/B正在实施：初始行为RED6FAIL/1PASS；共享matcher/native桥加source端初步37PASS，旧selector/handler81PASS、邻域772PASS（套件重叠不累加）。真实首回放HK经营页已到12；金禾223/224与销量/客户页仍漏，明确FAIL不验收。独审发现普通跨行表头、capture拒绝后仍finder、桥算法缓存身份/有限coverage遗漏，正按共用责任层修复。原件/config未改，0新模型调用；正式摘要/恢复/holdout仍OPEN。

**Next Step：** 完成候选网格/实际执行前预算/因果身份修复，集中默认真实PDF回放通过后，进入正式配置模型与恢复。

---

## ROOT 生产接线实施中 — 2026-10-17

用户确认继续。实施依据 [共享阅读生产接线B/C](review/production_wiring_phase_bc.md)：先固定单parse/同WorkBudget/默认深页行为，再接唯一策略与真实材料、正式摘要和缓存恢复；A进行中，B/C仍OPEN。内部agent仅strategy_binding/geometry_intent/reading与专属测试；ROOT独占source/automation，其余两张DU11外包只写RF/FF。只在大节点集中验证，当前0新模型费用。

**Next Step：** source单parse/预算与默认深页先RED；外包卡准备后及时交用户，ROOT并行实施生产链。

---

## DU10 已验收并推送 — 2026-10-17（当前）

三包独立复审PASS、0未解决，实现已全部进入各自主线并核远端：FF main f1a939e（754PASS/7SKIP＋78subtests，精确CI39072192244 SUCCESS）；ET main2584b7e（ROOT304PASS，FF→最新ET117PASS，无CI）；CWP master757bb833（Gold71PASS，11/11真实SourceRef回放，pre-push148PASS，docs/plans按既有paths-ignore不触发CI）。作者工区与原件/配置保持，两个ROOT接收worktree已正常移除。工具平台拒绝清理显式测试temp目录，剩余体积/路径列入 [最终机器记录](review/du10_reception.json)，未绕过拒绝、不虚报恢复完成。

FF完整41例及中断新attempt恢复固定环境C已关闭；Gold已修正的11例是回归集，不是盲holdout。当前没有待作者交付包。完整说明见 [DU10最终验收](review/du10_reception.md)。

**Next Step：** 继续 review/pdf_page_intent_implementation.md 的PDF导航/唯一matcher/POLICY+PLANNER/统一WorkBudget/source单parse生产装配，然后真实深页、按配置供应商正式摘要、缓存恢复和新盲样本验收。整个项目尚未完成；下面的“待派发/待推送/FF41OPEN”只描述历史时点。

---

## DU10 三包验收收尾 — 2026-10-17（最新）

三包作者完整历史已合入本地主线；ROOT独审发现的问题已修复并复审通过，0未解决。具体见 [DU10接收](review/du10_reception.md)。FF固定依赖/限额完整41例和中断新attempt恢复已按有效收据关闭；ET EOF token/main直挂文本共因已修复，304PASS，FF→最新ET合同117PASS；CWP样本6项语义修正和真实SourceRef/locator回放，71PASS、11/11来源实读，独立核10原件未改。样本为已看过回归集，正式摘要/盲holdout未完成。

ET main已推送2584b7e；FF正常push/CI与CWP本次发布收尾以 review/du10_reception.json 为最终机器记录。CWP仅docs/plans改动由现有CI paths-ignore跳过，不冒称产生新CI；ET无CI。未绕hook、未重复全矩阵，不加签收许可链。历史OPEN/待派发记录不代表当前。

**Next Step：** 继续 review/pdf_page_intent_implementation.md：原生PDF导航/唯一matcher/POLICY+PLANNER/同一WorkBudget/source单parse生产装配，再做深页真实文档、配置供应商正式摘要、缓存恢复和新盲样本；FF41 C节点不再OPEN，真实模型摘要主线仍OPEN。不改Dayu/IQS，不碰作者工区。


---

以下为历史记录（状态以顶部 ROOT 更新为准）。

## 当前收尾完成：外包工程待交付0 — 2026-10-17（最新）

## DU10 独立施工包已准备 — 2026-10-17

为并行工作建立三张独立卡，范围分别属于 filing-fetch、company-wiki（仅新增 goldset 目录）和 earnings-transcripts；固定起点提交、专属测试/临时目录、交接格式和独立审查复核要求均已写明。作者须由不同 agent 审查最终 HEAD，发现的问题修完并复核后才可交接。各工作目录目前未创建，卡尚未派发。总表：[DU10](parallel/du10-2026-10-17/README.md)。

当前DU8/DU9六包工程交付已全部接收并线，最后ET main/origin7d06777已核远端；CWP接收及推送范围共因修复已正常发布80be6877。pre-push6344PASS/24SKIP（296.69秒），精确[CI39047038268](https://github.com/zhengcb81/company-wiki/actions/runs/39047038268) SUCCESS。ET454PASS/10gold、FF117PASS、CWP12PASS，五轮独审受审源未变；作者工区/原件/配置/主仓既有文件保持，ROOT临时工区清理。详情见[最后ET接收](review/du9_et_reception.md)。AUDIT无remote仅本地，ET无CI不冒称CI绿。

已修复收尾效率共因：可执行contract/integration/e2e测试专改不再作为未知生产runtime回退全Unit，而跑实际模块与已知测试消费者＋原smoke。新TDD原4FAIL/4PASS，相关选择器与隔离76PASS；生产代码/配置/未知删除依赖保守回退、CI全Unit保持。本次工具自身变更已完整验证，不加人工许可/防伪签收。ROOT旧push外层300秒错误已绕回正确的直接正常Git执行，未跳hook，旧失败与实际前后选择证据保留。

**Next Step：** ROOT继续既有pdf_page_intent_implementation：原生导航/唯一matcher/POLICY+PLANNER/同一WorkBudget/source单parse生产装配，随后真实PDF深页、配置供应商摘要、缓存恢复与holdout；FF完整41例C及完整中断恢复仍OPEN。工程外包收齐不等于全项目完成。旧巡查任务不存在，未重建，当前也无待外包可巡查。下方各次“待接收/待推送”记录仅为历史。

---

## 接收收尾的推送范围共因修复 — 2026-10-17（最新）

六个DU8/DU9外包源码已接收且交付历史全部在各自主线，ET已推送7d06777；CWP接收提交5d41尚未推送，因为ROOT收尾脚本给git push错误套300秒超时，遇旧推送范围回退全Unit后提前杀Git；不能称母仓已远端发布，之前的ROOT联调绿仍有效。

已直接根治推送选择共因：contract/integration/e2e的可执行test模块是其自身消费者，不应因“没有unit消费者”回退全Unit。测试模块专改时选实际模块和逆向依赖测试，保留固定smoke；生产源码、配置、全局fixture、未知/删除依赖原保守回退不变。新TDD最初4FAIL/4PASS；修复后原选择器/临时隔离/新回归集中76PASS（1.89秒），既有unit-only reason保持，不改CI全Unit或跳hook。旧收尾脚本不再用于执行push，直接正常Git由工具管理，不加虚构运行许可。

**Next Step：** 正常提交本次选择器共因修复并直接push（不再套ROOT脚本300秒上限）；工具自身变更本次仍按现规则全Unit验证一次，随后只改契约测试即可收敛到相应模块。核精确远端CI和母PWF，返回CWP默认深页生产装配。外包接收完成不等于PDF/摘要或FF完整C已完成。

---

## DU8/DU9全部外包已验收并线 — 2026-10-17（最新）

最后ET作者6d94c38已接收：五轮独审PASS/0未解决，da82后仅文档变更；ROOT454PASS/10gold、FF117PASS、CWP12PASS。ET main/origin 7d06777e250ee3f7ae58f0be2cee62944bd2c104已正常推送并用ls-remote核对。原件/配置/作者树未改；主仓3个原未跟踪文件SHA/mtime保持，自建ROOT工区已清理。见[最后ET接收](review/du9_et_reception.md)。其余CWP/RF/FF/AUDIT五包已只读核对交付历史包含于主线，当前外包待交付=0。AUDIT无远端仍只本地发布，ET无CI不冒称CI绿。

**Next Step：** ROOT继续既有默认深页实施的原生导航/唯一matcher/POLICY+PLANNER/同一WorkBudget/source单parse生产接线，随后真实PDF深页、配置供应商正式摘要、缓存恢复、holdout；FF完整41例C及完整中断恢复仍OPEN。全部外包接收不等于整个项目完成。旧巡查任务不存在，未重建。

---

## 全部外包交付：最后ET包接收 — 2026-10-17（最新）

用户确认全部外包完成。RF/两个CWP组件已验收发布；唯一待接收ET作者HEAD6d94c38、工区干净，最终独审第5轮PASS/0未解决绑定da82f3a，da82..HEAD只变交接文档，源/测试未变。沿用已有五轮独审，不重复发起同范围审查；ROOT核版本/范围与最终集中回归，若发现新delta再按实际风险复核，不新增小门禁。

**A/B/C收尾：** A核作者22条白名单、冻结legacy oracle不变、主仓既有未跟踪.workbuddy-ai/eval_results保持；B ROOT隔离工区保留作者全历史，复测DU9+DU7/ROOT+提取/API预算相关回归和10gold；C 并线前FF→ET→CWP离线契约联调，正常快进/推送，核实际远端配置和必要定点同步，再更新母PWF/清理自建工区。0收费/翻译/外网provider/原件复制，真实CWP PDF/摘要仍OPEN。

**Next Step：** 建立ET ROOT小型隔离接收工区，集中执行实际最终源测试。首轮沙箱外部Git误报非worktree，正常主机只读核对已恢复；ET无AGENTS、无.githooks/pre-push和.github/workflows/ci.yml，实际现有检查按Git跟踪列表核对，不凭猜测加新CI。ET未初始化CodeGraph，仅接收既有已审源码，已知文件读回即可，不在作者树建索引。

---

## DU8 RF对比外包已接收并发布 — 2026-10-17（最新）

作者8845bc18完整历史并入RF main/origin c984a8fa，ROOT共因修复b41dceef。最终28相关套件558PASS/7SKIP＋163subtests、26.09秒；独审PASS/0未解决、12SHA绑定；正常pre-push416PASS＋36subtests，精确CI39016431219 SUCCESS。三份安装各4文件定点同步，6正常运行/6篡改拒绝通过。既有main告警WIP与147个output未变，作者工区只读。见[最终接收与具体修复](review/du8_rf_reception.md)。不是对作者旧冻结声明/旧收据盲签；删除3项重复AST表达式门禁，保留所有关键行为/数字gold，修复bool/null类型共因。

**Next Step：** 返回ROOT默认深页实施：原生导航/唯一matcher/POLICY+PLANNER与同一WorkBudget/source单parse生产装配，然后真实PDF深页、配置供应商正式摘要、缓存恢复和holdout。RF组件已完成，CWP生产验收仍OPEN。ET继续外包；旧du8-du9定时任务不存在，未重建，不宣称仍在巡查。

---


### DU8 RF 接收共因整改记录 — 2026-10-17

ROOT工区正常完整历史合流6bd53b78，作者8845bc18保持只读；最终作者27相关套件实际504PASS/7SKIP（32.01秒），与陈旧handoff计数不混淆。独审又实证报告将数值0/1等同bool（legacy bool()弱化，typed dict==本身有Python等价陷阱），旧布尔wire可被篡改后重封hash放行。新增57项ROOT跨legacy/typed/input-bound反例；首稿48FAIL中20只是异常消息断言过窄，原日志保留；修正消息断言且尚未改工程时真实RED为28FAIL/29PASS。

修复在report同一bool/null边界用owner singleton identity，typed缺base的合法null仍保持not_comparable；不复制计算公式、不更改数值/原gold、不增人工许可。集中回归与独立原探针复放进行中。RF根无AGENTS、workflow实际quality.yml（不是ci.yml），查询路径缺失非项目失败。作者CodeGraph未初始化，保持只读；改动前使用主仓索引影响查询。ROOT新临时工作树验收发布后检查清洁再移除，防止扩增资料空间；不删作者树和既有main WIP/output。

## DU8 RF 对比任务最终接收 — 2026-10-17（最新）

用户确认RF对比外包完成。作者HEAD8845bc18、树干净；相对当前RF main0feea9b0仅35条本卡工程/测试/文档路径。已修正原“源码冻结”的虚假口径为“发布输出不变”，但MD顶部仍指67b15a60最终、JSON implementation_commits未含05b1f38f/8845bc18，旧125/504收据不能当最新版本验证。本次以实际最终源重新验收，不再等待作者补小签收。

**顺序：** A核对最终范围/既有RED/发布兼容及主仓WIP；B独立ROOT接收工区保留完整历史，集中比较/报告/季度/typed邻域测试和隔离CLI，独立agent对实际最终SHA审查；发现共因先RED再修，不为实现改gold；C正常commit/push、精确远端CI、定点技能同步并更新本母PWF。作者工区只读，RF main告警三文件及output保持，不涉ET/Dayu/IQS/CWP生产代码。此RF接收不宣称CWP深页/真实摘要已完成。

**Next Step：** 创建RF主线基线的ROOT独立接收工区，并合入作者完整历史后一次集中测试。主仓CodeGraph可用但作者未初始化；不为查询初始化只读作者工区。RF仓无AGENTS.md，读取未找到已记录，不据此修改规范。

---

## PLANNER组件与POLICY联调已验收 — 2026-10-17（最新）

完整作者历史e4f946a2已合本地主线f4ef8531；ROOT共因修复a4ca0a85，独审PASS/0未解决、11SHA无变化。修复更紧请求限导致后部饥饿和同页嵌套fine被配额归因吞掉，未增限额或许可链。ROOT集中796PASS/17SKIP（25.46秒），独立55PASS及9控例PASS；原RED与64/64 gold保留。见[最终接收](review/du9_planner_reception.md)。正常推送master/origin c300e801已完成，pre-push6336PASS/24SKIP、311.06秒；精确[CI39008113871](https://github.com/zhengcb81/company-wiki/actions/runs/39008113871) SUCCESS，发布收据已保存。

**下一步：** ROOT按既有pdf_page_intent_implementation完成native窗口/唯一matcher/同一WorkBudget/source单parse生产装配及真实PDF深页/正式摘要/缓存恢复/holdout。组件已完成，生产验收仍OPEN。RF/ET工区不动。旧du8-du9自动任务实际不存在，未重建，不承诺持续巡查。

---

## PLANNER跨组件共因整改实证 — 2026-10-17

完整作者历史已合本地主线，作者树只读。ROOT新增真实compile→plan→admit/JSON重放/共享WorkBudget联调，首次2FAIL/5PASS：max_pages64/max_requests2仍预留61页，前部吃完2请求使后部饥饿；同页outer only-discover+透明inner fine会只取归因outer请求，丢失inner fine。独立agent另9控例同样7PASS/2FAIL，反例未提高cap或改64/64gold。

共因修复：公平可执行容量统一min(页限,请求限)；同父文同物理页仍只扣一个reservation，但合法reserved覆盖规则合并discover/fine，cancelled不提供能力。8个ROOT接口回归含取消类不能借fine、两种更紧cap、行政取消、预算已耗尽、scope去重与JSON恢复。原request-one测试纠正强制先到行政必放行的假设，改one-class独立固定夹具，仍明确quota1/花费1且不超请求限；原64/64手算gold未变。

修复后六目录集中796PASS/17SKIP（25.46秒），ruff绿，未调用供应商/下载/复制原件。最终独立delta复核进行中。作者报告“几十至几百窗口亚毫秒”不作性能保证：ROOT独立实测50/300/1000窗约0.4/1.7/6.8ms/admit；暂无实际生产阻塞证据，不为此扩成性能重构或加防伪门禁。not_arrived仅表示reserved-unused，不能当未读页事实。真实深页source装配/摘要仍OPEN。

---

## PLANNER最终交付接收与POLICY联调 — 2026-10-17（当前）

用户确认PLANNER完成。实际作者HEAD e4f946a2，工作树干净，原白名单20文件；受审源码db126f24的9个源/测试/fixture SHA与当前及Git blob均一致，独审后无代码delta。作者独审PASS/0未解决，47新测试及618邻域/17SKIP的作者收据仅作其版本证据。ROOT保持作者工区只读，接收完整提交历史到主仓，补真实POLICY→PLANNER公开接口联调和关键预算/重放/父文范围反例，再集中测试、正常发布。原公开default_intent=unknown与planner不继承缺字段兼容，不新增许可或人工签收。

**本轮顺序：** A最终交付/边界核对已完成；B主线合流与真实compiled-policy/调用者共享预算联调，发现共因先独立RED再修；C必要独立delta审查、相关集中回归及正常commit/push/精确CI，并更新PWF/自动巡查。原生导航/唯一matcher/source单parse生产装配和真实PDF/正式摘要是后续具名OPEN，不把纯组件验收冒充全项目完成。RF/ET外包与Dayu/IQS均不进入。

---

## POLICY发布核对 — 2026-10-17

工程/交接已推送master/origin bb678a718ec59e87aecd595b059fdc740ac50bd2；正常pre-push6281PASS/24SKIP，409.24秒。fallback defaults作为配置变更触发既有全Unit范围，这是本次工程大节点检查，不新增逐材料/逐小节点门禁，也未跳hook。精确远端[CI38999581404](https://github.com/zhengcb81/company-wiki/actions/runs/38999581404) SUCCESS（03:42:10Z），不同于修复前版本或仅本地通过。见[发布收据](../du9-geometry-policy-2026-10-16/receipts/publication.json)。源码仍冻结6e0edeef，独审33SHA未变；后续仅补文档。PLANNER继续等待，生产深页和真实摘要仍OPEN。

---

## POLICY组件已完成并独审，PLANNER继续等待 — 2026-10-17（当前）

用户明确POLICY的A移交ROOT，已保留A历史并完成唯一catalog typed intent、registry因果来源及纯compile_geometry_policy。设计源与catalog/fallback同步，15旧profile wire SHA不变。实现30df8eae，独审发现共用嵌套引用污染和IR落generic假覆盖，已在6e0edeef根治并加12污染回归/12实际family断言。

最终集中626PASS/11SKIP（10.48秒），独立agent另263PASS，catalog parity/25策略/11畸形及公开反例通过；最终独审PASS、未解决0，33SHA读回匹配。[组件交接](../du9-geometry-policy-2026-10-16/handoff.md)。0供应商/0下载/0原件复制/0作者工区写入，不提高预算或增许可链。该组件完成不等于默认深页/真PDF/正式摘要完成。

**Next Step：** 按用户要求等待PLANNER，其geometry_intent目录与工区不改；收到最终交接后ROOT统一POLICY→PLANNER→原matcher/native windows→共享预算/source生产接线，再做真PDF深页与配置供应商摘要/缓存恢复/holdout。RF/ET继续只读等待交付；自动跟进已排除POLICY，不误报停A。

---

## POLICY由ROOT接手B/C，PLANNER继续外包 — 2026-10-17（当前）

用户明确POLICY只冻结A期望，后续由ROOT按INTERFACES实施profiles/geometry_policy.py；PLANNER仍在施工，ROOT等待、不写其geometry_intent目录。A历史f70318f1已正常合入主线；ROOT在本主仓完成POLICY原白名单，实现/测试/独审后发布，原作者A工区保持只读。自动跟进du8-du9已更新为三条外包，不再把POLICY停A当新阻塞。

**实施顺序：** 先固化接口RED和旧wire指纹；再补唯一catalog的typed意图/真实可转债heading变体、registry因果摘要和纯编译器；集中矩阵/旧profiles/策略回归；C从route→resolve→compile走公开入口并核对隔离恢复，独立agent全面审查修复后正常提交推送。不做PLANNER/source生产装配，等待其最终交付后ROOT统一联调。A研究中的SHA截断、缺路径转字符串unknown、同path不同alias必拒和MD&A必须与business不同fine只是作者假设：按原固定接口纠正，以完整规则SHA、结构化空路径/unknown意图、合法多规则保留为准。真实PDF深页与付费摘要仍OPEN，不用此组件测试代替。

---

## 剩余施工包巡查已建立 — 2026-10-17（当前）

只读实查RF6de6a0c4、POLICYf70318f1、PLANNER8ff47e28、ET36c9b38。RF冻结声明与实际最新源码不一致；ET实现/测试已推进但无最终交接；两CWP缺B/C。未重跑作者测试，0供应商/0作者写入。Codex heartbeat du8-du9已确认ACTIVE/每30分钟，无变化静默，有新交付或新阻塞通知。[证据和约定](review/remaining_packages_watch.md)。

---

## DU9实查与CWP工程发布 — 2026-10-17（当前）

指定POLICY工区f70318f1干净但仅A调查，无实现/测试；PLANNER工区8ff47e28有A RED与未提交contracts/__init__，缺planner实现，B/C未完成，无最终handoff/独审。已核对本地refs、注册worktrees、Projects同名目录及远端DU9 refs，未发现另一最终交付；异步问用户最终文件/commit，暂不动作者树。母线既有代码/资料保护，不因缺交付重写他人半成品。[接收记录](review/du9_reception.md)。

实际import分别ModuleNotFoundError(geometry_policy / geometry_intent.planner)，收尾再次只读核对仍未补齐。已提供[原卡继续B/C说明](parallel/du9-2026-10-16/CONTINUE_BC.md)，无A人工签收/新签名，不另开包。

核对期间完成既有CWP工程：add7afef源码提交，首pre-push6212PASS/1FAIL/24SKIP(280s)，失败为旧测试假设tables导入qualify_table。只改测试验两真实入口有界unknown，原断言未放松，44PASS；测试修正ce6e4646后正常pre-push6213PASS/24SKIP(270.07s)，远端CI38979991954 SUCCESS。本地ff-only初因四文件索引/换行冲突被拒，40文件均先核对已提交/压缩留存，再仅恢复所属worktree+index/refresh后正常快进成功。master/origin均ce6e4646，已完成源码/测试/工具不再未提交；仅工作记录/继续说明待文档发布。0原件改写/0供应商；source默认仍0.8，新0.9默认v3，真实摘要/默认深页未称完成。

---

## DU8工程接收发布 — 2026-10-16（历史）

两作者完整历史与ROOT修复已正常并入main，作者树未改。AUDIT `a2f216bd` 本地并线/干净，无remote；两安装目录各5技能文件定点同步，全部38文件MATCH。实际完整unittest620PASS/2SKIP(91.330s)，随后修独审复合locator/null归一化P2；最终59PASS/15subtests(7.49s)含unittest遗漏的17例，独立终审13SHA/8控例PASS。前后源版本与重叠计数分别保留，不虚报同一版本重跑全套。

FF工程 `c7c8867d` main/origin已发布，ROOT修复41f49882，251PASS/独审0P1/P2，正常pre-push754PASS/7SKIP/78subtests(87.73s)，精确quality CI38977822228已SUCCESS。唯一41链20PASS/4PARTIAL/17NOT_RUN(173.27s)，完整中断后重启NOT_RUN，C仍OPEN。完整209文件/1.15MB证明保留、scratch/cache删除；未偷偷重跑、改CaseSpec或抬30/180限额。[详情](review/du8_reception.md)。CI绿不等于完整41例通过。

CWP冻结原生表格另复放17PASS/2.61s（与190重叠），实际VRSK/MSFT原2M预算分别1,989,140/1,035,473、单parse、无耗尽；Temp/sentinel/config保护通过。0供应商/0原件复制；CWP工程WIP待正常发布，DU8RF仍外包、DU9不写。Next：接收记录发布→CWP生产闭包；FF效率C保留具名责任。

---

## DU8并行施工已就绪 — 2026-10-16

三条新独立线已准备为READY：[总表](parallel/du8-2026-10-16/README.md)、[RF比较单一责任](parallel/du8-2026-10-16/du8_rf_comparison_owner.md)、[FF固定时限矩阵](parallel/du8-2026-10-16/du8_ff_matrix_completion.md)、[AUDIT数值实读证据](parallel/du8-2026-10-16/du8_audit_measure_evidence.md)。各自RF/FF/AUDIT独占工区，源码base/seed/干净状态/import已验证，启动共9,893,247bytes，0原件副本/0供应商/主仓WIP保持；各卡业务A/B/C尚未实施。可立即同时启动，不等待ROOT的CWP/ET接线；只有原三个大节点集中验收。

ROOT主线继续：ET独审已完成三共因修复，228PASS/10旧gold，待测试基础设施收尾及正常并线；多父文真实入口2RED→50PASS，原生TABLE生产3RED→90相关PASS。深页按显式请求的来源port已修，真实金禾223/224有31bound/4ambiguous，但默认自动triage请求136页仍在前部耗尽原15秒/64请求页限，深页仍deferred；此条继续OPEN，必须由统一阅读策略提供有限优先请求，不提高限额/写公司页码补丁。公开v4真实batch选择/正式runner由ROOT子线继续，尚未称真实付费摘要或完整语义通过。

**Next Step：** ROOT完成ET并线、默认深页优先请求与TABLE未知标记/缓存身份、正式v4端口/runner集中验收，再执行原配置真实摘要与独立语义holdout；三DU8作者分别独立A→B→C交付，ROOT合流。母目标仍OPEN。

---

## 2026-10-16 主线生产闭包恢复实施

用户确认DU7-ET-EXTRACTION已交付，ROOT开始独立验收；原四包均已并线，工程CI与PWF发布已完成（bd270b71）。本轮严格复用既有配置、预算和授权，原件/生产目录只读，所有真实摘要与下载测试在独立可清理测试根中执行。

- A（进行中）：接收ET，复放其真实入口/既有TXT复用/不翻译与失败路径，审清作者披露的baseline失败，再正常并线、推送；不直接按作者文字跳过失败。
- B（进行中）：完成已有STATE效率进展与parent composition真实生产接线；来源层修复深页layout捕获与native TABLE依赖闭包，覆盖缓存版本/恢复、不同文档策略/父文作用域，按根因修复，不提高上限掩盖复杂度。
- C（待执行）：正式worker→公共资料读→RF/AUDIT实际消费者；用现配置真实供应商生成原语言摘要并验证首次调用/缓存恢复0重复调用、原引文/数字/语义质量与独立holdout。保留未知/失败，不用组件通过代替语义验收；最终正常提交/推送并核对工程CI。

仅在原A/B/C大节点集中审查测试。ET只读独审、PDF来源结构只读调查、真实E2E复用路线只读调查互不改代码；ROOT独占CWP生产接线和总PWF。源/测试既有WIP已按字节冻结到`.planning/shared-reading-production/production-closure-20261016/start-source-sha.json`，不丢弃未提交进展。

**Next Step：** 先固化parent真实依赖丢失的生产RED并接入已有composer；同时收齐ET独审和深页捕获定位，进入一次集中生产节点。

---

## 发布收尾已核对 — 2026-10-16

本次四包已验收并入主线，RF、FF、CWP均已正常推送并核对精确HEAD的远端CI成功；AUDIT无origin，仅本地合并并定点同步技能。DU7-ET-EXTRACTION仍施工，目录未改。四包结果不等于共享引擎生产全链完成；原生TABLE/深页捕获、正式摘要及RF/AUDIT消费者、真实语义holdout和母审查循环继续按原计划执行。

FF发布时发现ROOT迁移测试误假设无输入时stdin总是PIPE。Ubuntu真实复现两项None.closed；生产无输入正确使用DEVNULL，stdout/stderr仍为管道。先增加跨平台形状回归得到2RED，再修两个测试并明确stdout/stderr存在，保留进程退出、管道关闭和线程清理；Windows32PASS、Ubuntu4PASS，正常推送及精确CI成功。未改生产transport、0.2s/<5s断言、30/180预算或旧业务金标。完整失败和修复收据仍保留。

ROOT稀疏接收工区漏检出.githooks，导致CWP首次推送未执行本地hook：已补齐并按原始推送全范围实际回放，6144PASS/14FAIL/24SKIP（14项均缺已有受控资料），补齐原资料后14/14原样PASS；不是称首次hook成功，也没有修改失败断言。另一次沙箱定向复验120s超时不计通过；正常宿主原14项6.64s通过。远端完整CI在原工程83cc4be已独立SUCCESS。以后ROOT稀疏工区启动同时检出实际配置的相对hooks/CI与本轮回归所依赖的受控fixture，不增加人工门禁。当前主仓STATE/parent WIP保持原冻结SHA，正常pre-commit暂存恢复造成的两文件换行已按原SHA恢复。

**Next Step：** 返回ROOT统一来源准备、深页/native TABLE闭包与既有STATE效率/parent组合接线，在原大节点集中做正式worker→公共读→RF/AUDIT、真实配置摘要和独立语义holdout；等ET交付再集中接收。0新增供应商调用，不改原件/生产配置；主目标仍OPEN。详细提交、CI与收据见[接收记录](review/du67_reception.md)及[发布收据](common-root-quality-evidence/du67-publication.json)。

---

## ROOT当前状态：DU6三包与DU7-PDF接收并线完成 — 2026-10-16

用户确认后已接收四个干净交付；DU7-ET-EXTRACTION仍IN_PROGRESS，未进入其施工目录。RF、AUDIT、FF、PDF的作者完整历史及ROOT修复已正常合入各自主线。RF/AUDIT技能已定点同步（三路径RF为两物理副本）；AUDIT无origin，明确仅本地并线/安装。RF/FF/CWP远端发布与精确CI状态随后归总，不把未观察CI说成绿。见[完整接收](review/du67_reception.md)、[紧凑收据](common-root-quality-evidence/du67-reception.json)。

大节点结果：RF199PASS+119subtests，原生季度/默认未建模/带符号目标/旧严格数值边界统一；AUDIT90PASS+15实际CLI/16checks与当前CWP公开v2/v3两项联调（v3临时合成原件经真实来源/公开读），同次正文/SHA/attempt及单8MiB物理读取、unread、投影上下文与一对一库存修复；FF305PASS，复用已有bounded process owner，删除重复taskkill/等待，不改0.2s/<5s和case30/batch180，原子不覆盖输出；PDF43短测、557旧兼容PASS/24SKIP，另两项因ROOT漏检出旧资产失败，补资产后原两项2PASS，未改断言。

PDF独审3P1/3P2已修，真实名创p12单parse所有ref真切片，2M消耗1,162,753；深页223/224因上游64页capture仍未覆盖，正式生产TABLE/摘要/消费者接线和语义验收没有关闭。已保留全部原RED/失败/未知，作者新增错误假设有原zip及独立理由，不改旧binder/layout/研究金标。不新增人工签收、许可文件或逐材料审批。0新增供应商，原件/配置保持。

ROOT原STATE效率、parent composition和跨仓E2E本地进展完整保留，未混入这四包并线；后续纳入下一主线节点。默认0.8、新0.9默认v3均未切。旧20条8/6/6、PD5/Matrix业务遗漏、母G2/G4/G5/原三→新三及八公司审查loop继续OPEN，不能以组件绿称项目完工。

**Next Step：** 完成本次远端发布收尾，随后将来源层深页捕获/原生TABLE闭包与已有STATE效率/parent组合统一接入主线；复用正式worker→公共读→RF/AUDIT做真实配置摘要和独立语义holdout验收，等待ET交付。仅原A/B/C大节点，无新增小节点许可。

---

## DU6／DU7 交付接收进行中 — 2026-10-16

用户确认：DU7-ET-EXTRACTION仍在施工，保持其工作树排他；其他已发施工包已交付。ROOT只读盘点得到四个干净作者HEAD：RF `86ca2941`、AUDIT `c603d23`、FF `ff08a8e0`、PDF `caca0eb6`。尚未验收或并入，不能把作者测试等同ROOT验收。CodeGraph当前主仓已初始化（1295文件）；其他目录需要时已获用户授权初始化。

按原A/B/C大节点集中验收：检查提交范围/交接、独立代码与数值/来源反例、旧新回归及真实CLI/可用原件端到端；通过后正常并线/推送/定点同步及PWF收尾。RF/FF/PDF独立只读审查，ROOT审AUDIT并统筹跨仓接口。保留主仓STATE/parent composition/RF E2E未提交进展，不混入作者接收；原件、生产配置、RF原alert WIP不改。

PDF已披露64页layout capture上限，真实金禾p223/224的未覆盖是ROOT来源层后续事项，不能因组件绿关闭。AUDIT真实发布完整bundle与/3.0为NOT_RUN，ROOT核查可用现有产物再补，不编造真实证据。沙箱首次无法进入外部RF工作树，已转正常宿主只读盘点，未改变仓库。

**Next Step：** 收齐四包独立集中验收，按依赖顺序处理必要共因修复并正常并线；DU7-ET保持IN_PROGRESS不触碰。接收收据见 `.planning/shared-reading-production/du67-reception/`，后续固化紧凑正式记录。

---

## 当前发布与并行安排 — 2026-10-16

主线工程 `04c7f1bc93386a5703693f9303c3a59bb7546025` 已正常推远端，pre-push **6115 PASS/24 SKIP/373.88s**，无跳hook；[发布收据](common-root-quality-evidence/native-state-scoped-publication.json)。推送执行器最后在GBK控制台打印时UnicodeEncodeError，发生在成功push、远端HEAD核对和落盘之后，不是Git失败；保留原错误，后续使用Python -X utf8。精确CI [38865710454](https://github.com/zhengcb81/company-wiki/actions/runs/38865710454) SUCCESS（04c7f1bc）；文档提交5b685f3b正常push148 PASS/23.76s，未触发CI。

[DU7两张新卡总表](parallel/du7-2026-10-16/README.md)已READY，分别独占PDF细格适配新组件和ET现有网页抽取窄port，真实工作树/基线/种子在[launch](parallel/du7-2026-10-16/launch.json)。两个imports和干净状态通过；共20.32MB，0原件复制、0供应商，业务A/B/C由作者执行。可立即同时开工，不等待ROOT，不重复DU6三包。

ROOT继续STATE真实预算耗尽共因整改、TABLE依赖闭包、正式跨仓及真实摘要；默认仍0.8、新0.9默认v3。真实VRSK/MSFT耗尽和旧六错引/业务遗漏未关闭，母G2/G4/G5和公司循环仍开放。

**Next Step：** 发出DU7两卡，由ROOT完成共享STATE惰性事件准备，正式TABLE及worker→公共读→RF联调后再真实供应商/holdout验收；只用原大节点，不增加小节点许可。

---

文档收尾第一次preflight因Windows默认换行为CRLF导致母PWF整段diff/check失败，未形成提交；已按HEAD原始字节保留旧正文、仅添加LF新前言，未改Git attributes或旧证据。

## ROOT发布节点更新 — 2026-10-16

FORM/native TABLE适配、STATE、共享结构与策略预算、显式v4工程已收齐，独立scope/预算尾部反例修复并复放通过。[本节点详情](review/native_state_scoped_engineering.md)与[验收收据](common-root-quality-evidence/native-state-scoped-engineering-acceptance.json)。集中1212 PASS后12项失败已分类修复：可选role/kind不再阻断，正常宿主相关25 PASS（含v4与旧paid恢复）；未删除失败或跳hook。准备正常提交和推送，精确CI未返回前不称远端绿。

真实VRSK/MSFT在固定2M共享预算内仍耗尽，已优先安排STATE惰性事件准备共因整改；只读剖析83%耗在大多无事件owner的全语法扫描。当前不切默认，不提高cap，不把partial视为质量通过。新DU7候选仅两张：PDF已观察细格适配与ET既有HTML抽取忠实度，均与DU6三卡排他；正式卡/工区准备后再交付。

**Next Step：** 完成本工程节点正常发布；随后STATE共享效率共因、TABLE依赖闭包和正式跨仓/真实摘要验收继续。母目标未完成，DU6已分包继续，不进入其owned目录。

---

## 2026-10-16 DU6已分发，ROOT主线继续

用户确认三卡已发出，README保持DISPATCHED。首段commit06f4ea24完成但未push。FORM独立两P2固定后原探针回放通过，显式v4交付238 PASS/44.26s，loopback初次1 POST、恢复0 POST，0供应商调用。ROOT策略准备5 RED（缺共享端口）→23相关PASS/1.53s；Temp/sentinel/config/RF默认registry保护通过。

结构首版代表规模暴露2M耗尽和代理层复杂度，ROOT拒收并要求收敛；STATE/TABLE处于隔离owned文件主线施工，非外包作者目录。未来Git操作前先冻结写者，避免已实证pre-commit stash隐藏活源码；不跳hook、不把并行快照当最终验收。完成的来源/预算/摘要工程将在集中节点正常提交推送，真实质量与母计划未结束。

---

## ROOT当前状态 — 2026-10-16 统一准备与共享预算首段、DU6启动

**并行调度更新：用户已确认 DU6 三包发出（DISPATCHED），ROOT不进入三卡源码范围；各作者独占工区和接口继续按总表。**

DU5三包已接收。ROOT新增准备/预算首段：route与policy复用实际Observation；选择入口拥有同一WorkBudget并传至各parent/layout/binding；零预算/耗尽在进入后续正文分类前返回未完成；共享路径只overlay增强字段，standalone独立返回保持。初始5RED、owner3RED和独审3P2各自固定后修；最终224集中PASS，独立相同探针复验通过，Ruff/mypy8源通过。这里只完成layout准备/绑定与prepared限额复用，**结构/strategy/candidate尚未全部计费，full_pipeline_hard_bound=false**，不能称预算/来源准备整体完成。

完整1045PASS/11SKIP是中途兼容快照；旧只读作者runner在ROOT并行场景因卡文档变更触发status断言，不能称清洁作者收据。后续目录收集意外带入FORM作者正在写的9条RED（1057PASS/9FAIL/11SKIP）；失败原样保留，不当主线验收、不改作者expected洗绿。下一集中节点冻结所有相关写者后只跑一次，避免活施工源码/测试混入。

[首段证据](common-root-quality-evidence/prepared-source-budget-acceptance.json)、[实施细则](review/production_preparation_budget_implementation.md)。FORM原生carrier与显式v4正式runtime已在互不重叠文件委派主线agent施工，尚未接收，不算完成。默认0.8、新0.9仍v3；旧20条8/6/6、PD5/Matrix遗漏、原生12/37与母G2/G4/G5仍开放。0供应商；累计599590tokens/385113µUSD代理、旧unknown7、限2M/$20不变。

[DU6三张独立卡](parallel/du6-2026-10-16/README.md)已真实READY：RF目标计量、AUDIT公开摘要导入、FF原生证据路径重放。三工区源码基线/种子已提交、导入定位PASS；只读CWP/ET固定依赖隔离ROOT当前未提交代码。合计约28.89MB、0原件副本/0API；启动核对不是业务验收。ROOT不写三卡白名单，作者不写CWP。

**Next Step：** 提交已验收首段和DU6调度；继续单次来源索引与结构/strategy/candidate真实工作计费，FORM→STATE→TABLE正式接线、v4/旧paid恢复，冻结后集中离线worker→公共读→RF，再按现配置做真实摘要质量和holdout。原大节点，不新增小节点许可。

---

## ROOT当前状态 — 2026-10-16 DU5三包接收完成

DU5三包已验收并线。CWP merge b083a1b1及配置补丁5dae70a0正常推送，精确CI 38834945691 SUCCESS；最终5954PASS/24SKIP、真实benchmark252PASS、Git12种往返PASS。RF main794240df/收尾5122107b已推且CI38833831553/38834985290成功，210集中及23CLI通过，三路径/两物理副本定点同步。AUDIT main58b2797/收尾a3f36d1本地并线、48集中/静态与真实CLI通过，两份技能同步；无origin/对应远端not found，未远端发布。

独审发现的根因均已修复：金标合法舍入/页行SHA/例外范围；share与count真正数值单位；审查谱系/冲突无损聚合/unknown/历史与当前区分及片段去重（同输入591439→54835B）。旧20条8/6/6和业务遗漏、原生12/37保持，不用工具绿替代生产质量。原件/配置/作者树保护，RF原alert WIP保留，测试Temp恢复；0供应商，累计599590tokens/385113µUSD代理/旧unknown7/2M/$20不变。

[完整接收](review/du5_reception.md)，[正式发布证据](common-root-quality-evidence/du5-reception-publication.json)。

**Next Step：** 按[生产接线细则](review/du4_production_integration.md)先TDD修统一准备与WorkBudget所有权，复用一次来源视图，再FORM→STATE→TABLE接线、v4正式摘要/覆盖/旧付费恢复及真实质量。默认0.8，HKIPO性能、母G2/G4/G5与原三/新三公司审计仍开放，母目标未完成。只保留原大节点，不新增许可或小节点签收。

---

## ROOT当前状态 — 2026-10-15 DU4三包组件集中接收

FORM已发布master cbfe3e7f，正常推送5784PASS/24SKIP321.47s、精确CI38804974095 SUCCESS；文档收尾de6b4660已正常推送148PASS/26.54s，docs-only无workflow。TABLE/STATE用户均已交付，作者head fa1681c0/284eea60，36/90原测试ROOT复跑通过。两分支已正式合入master并推送，保留作者完整历史；独审发现的7类共因经集中RED/共同责任修复，最终三包+Git字节 **251PASS/6.42s**，独立纯探针复核通过，Ruff/mypy8源PASS。两包已正常合并并推送master `a4cb40c9`：**5948PASS/24SKIP，515.93秒**，精确CI **38810541475 SUCCESS**，作者完整history保留。[发布收据](common-root-quality-evidence/du4-table-state-publication.json)。

修复包括真实ref作用域与表头可用性、明确起止与同标签冲突、单位维度保留、稀疏原生列/一次label缓存；STATE限定词/条件/假设、主句与供应商从属描述的主体隔离、控制动词对象及原文偏移，原relative反例中取得类助动词也不再被当成对象。所有变量长工作先扣原WorkBudget，无第二预算或重复身份流程。23初始RED、后续4/3/6及aux1RED与旧失败均保留；foreign row仅剔除并partial为原绑定定义允许行为，不为此新增整表阻断。STATE真实fixture恢复原manifest准确字节，不改gold；作者目录不写。

细则见[两包接收](review/du4_table_state_acceptance.md)，证据见[紧凑验收](common-root-quality-evidence/du4-table-state-acceptance.json)。**组件通过不等于生产接线或语义完成**：默认0.8、新0.9仍v3，新v4未实现；六错引/重要遗漏、真实holdout、HKIPO性能及母G2/G4/G5/公司循环继续开放。原件/配置/sentinel保持、测试Temp删除，0供应商，累计599590tokens/385113µUSD预算代理（旧unknown7；限2M/$20）不变。

**Next Step：** 按[生产接线细则](review/du4_production_integration.md)统一source-owned生产接线（FORM native/carrier→原cap/router、STATE唯一经营谓词、TABLE原生槽/解释依赖），再完成v4正式边界/源任务覆盖/费用恢复和真实摘要验收。先修来源作用域可避免新协议绑定旧错误来源，不重复付费探路。只在原A/B/C和母G大节点集中验收，未完成不切默认。


## DU5 并行施工窗口 — READY

已准备[三张独立施工卡](parallel/du5-2026-10-15/README.md)：CORPUS只写DU-BENCH工具与自己PWF；AUDIT只写audit仓摘要双向审查包；RF只写金额单位责任层及直接consumer。各有独立稀疏工作树、源码基线、5份已提交启动PWF和实际import locality核对，逻辑新增共约29.90MB，0原件副本/0API。作者尚未开始实现，READY不是完成。

ROOT继续统一准备/WorkBudget及FORM→STATE→TABLE/v4生产接线；接收前只读benchmark与RF卡列明文件，不写作者范围。只有A/B/C集中验收，不增加小节点签收。接口/分母/原失败保留及交接格式已冻结；三卡互不等待，不以新组件绿替代生产质量。[启动收据](parallel/du5-2026-10-15/launch.json)。

---

## ROOT 当前状态 — 2026-10-15 DU4-FORM发布前共同边界收尾

FORM组件已正常合并本地主线（作者head2cde9de9，ROOT merge8406461c）；327集中契约、独审11组及最终87项FORM/Git传输测试通过。正常prepush首次5775PASS/24SKIP/1FAIL，拦截旧Windows OCR worker退出，远端尚未更新；具体退出原因UNKNOWN，未盲重推。进一步集中测试真实发现response open的PermissionError。ROOT统一文件交接责任：只在原绝对deadline内复试Windows共享文件操作，成功后也复核到期，不重发native、不续期；保留输入/输出cap和真实退出码。受控read/publish先2RED，独审成功越期先2RED；最终冻结集中 **96PASS/55.64s**、Ruff/mypy通过，独审无剩余阻断。完整CRT矩阵保留。最终工程提交 `cbfe3e7f` 已正常推送：**5784PASS/24SKIP，321.47秒**；精确CI **38804974095 SUCCESS**。FORM作者history已在master，未跳hooks。[发布收据](common-root-quality-evidence/du4-form-publication.json)。

证据：[FORM接收](review/du4_form_acceptance.md)、[OCR边界收据](common-root-quality-evidence/du4-form-ocr-acceptance.json)。组件不等于生产接线：FORM native→adapter→router/真实holdout、新v4协议/source依赖/覆盖、六错引及重要遗漏、HKIPO性能和母G2/G4/G5继续开放。默认0.8不变，TABLE/STATE均已交付，作者测试36/90复跑通过，独审接收中；作者目录保持原样。0供应商，累计599590tokens/385113µUSD代理（旧unknown7；上限2M/$20）不变，原件/生产配置/sentinel保持、测试Temp删除。

**Next Step：** 接收已交付TABLE/STATE，再继续v4正式摘要/恢复及统一DU4生产接线。目标未完成，不增加小节点许可。

---

## ROOT 当前状态 — 2026-10-15 DU4-FORM组件接收

DU4-FORM作者分支四个commit已接入ROOT合并工作区；原72测试复跑通过。独立审查发现两类P2（同owner不连续片段可拼出原文没有的表单值；预算前循环/raw JSON复制/平方级预留）及一个异常类型问题，ROOT先9个RED再共同根因修复，组件81PASS，含现有router/adapter/父子scope共327PASS（包含81，不累加）。独立11组纯探针复核PASS_COMPONENT，无剩余阻断；Ruff/mypy两源文件PASS。测试helpers已改包内导入避免各施工线同名helpers污染，最终namespace复核81PASS；另在推送前查出Git规范换行会使CI失败，已停止自有push且确认远端未变，不改gold，统一夹具字节角色与真实Git往返6控制共87PASS/4.58s。正常重推待执行。[接收细则](review/du4_form_acceptance.md)、[不可变组件证据](common-root-quality-evidence/du4-form-component-acceptance.json)。

**组件接收不等于生产接线：** 一次native walk→carrier→adapter→原cap预留→唯一router、真实VRSK/电话会/8-K holdout仍待ROOT实施。TABLE/STATE仍按用户施工通知保持独立，不修改作者树。源原件/配置保持，测试Temp已删除，本节点0供应商，累计599590tokens/385113µUSD预算代理（旧unknown7；上限2M/$20）。

来源任务/view5f54f81b已发布，5689/24正常推送测试及精确CI38796376285成功；PWF收尾a89467b0也已推送，148PASS，精确docs-only查询无workflow。新v4正式协议仍未实现，已付费摘要六处错引及重要遗漏仍未关闭，默认0.8；不得以FORM组件绿宣称共享引擎质量完成。

**Next Step：** 完成本FORM合并正常提交/推送和精确CI；继续显式v4正式接线、source依赖与覆盖，再统一FORM native/route接线和真实摘要/恢复验收。HKIPO分阶段有界解析、供应商质量、母G2/G4/G5与原三→新三公司审计继续开放。旧模型模块保持字节，有限runtime入口设计见原施工细则；未实际接线不称完成。

---

## ROOT 当前状态 — 2026-10-15 来源任务与逐命题回归

当前已实施一段共同机制：原真实paid终文经正式decoder仍逐字还原20条；新的逐claim锚点观察会将六处错引用分开检出，不允许借其他claim、context或完整selected里的事实。该观察依赖独审明确的命题→原文锚点，不是通用自然语言蕴含证明。原20条8PASS/6WARN/6FAIL及PD5/Matrix等遗漏的正式语义FAIL保持，不改旧终文、不偷换分母。

共享引擎已实现不可变 `SummaryTaskPlan`，新纯model-view编译器保留96原文/64来源组、QA双view、共享图与本地part绑定；不补邻居、不做第二排名、原文每source span只定义一次。缺少新v4正式注册/worker接线、source-owned指代/对象/覆盖分配和真实候选质量，组件完成不能当生产完成。

**集中证据：** ROOT最终组件47PASS/4.30秒；先前含旧None/v1/v2/v3/QA契约集中160PASS/8.08秒；独立44PASS/2.88秒是compact前快照，最终编码仅独立静态核对，不能混写成独立重跑47。Ruff六文件/mypy三责任源PASS。真实材料呈现初版47813B，压缩后30590B，旧同范围30758B，仅少168B；这不是完整HTTP、真实token、速度或语义提升结论。[验收与失败收据](common-root-quality-evidence/source-scoped-foundation-acceptance.json)。

**实施细则：** [逐命题根因](review/summary_grounding_implementation.md)、[source-scoped具体接口/测试/接线](review/source_scoped_summary_implementation.md)。新增代码仅两纯组件与原quote oracle的观察组合；旧production v3/model/generation/factory未改，默认仍0.8。新模块仍须正式接入，不能作为闲置替代品留在目标完成声明里。

本节点代码 `5f54f81b` 已正常推master：pre-push **5689PASS/24SKIP，456.05秒**；精确CI **38796376285 SUCCESS**。没有绕hooks；[本节点发布和旧v3请求快照](common-root-quality-evidence/source-scoped-foundation-publication.json)。上一CWP/RF工程CI已绿，RF收尾090a6310/CI38790621941 SUCCESS。源码工作区已清，旧owned scratch与三作者目录保持。

三[DU4作者包](parallel/du4-2026-10-15/README.md)仍按用户通知IN_PROGRESS，ROOT未写其新组件/测试/独立PWF。门禁不新增，旧恢复/原文SHA/身份/期间/预算职责保持在所属层；审查仍只在原A/B/C及母G大节点。

本轮供应商0调用，母累计599590tokens/385113µUSD预算代理，旧unknown7保留，累计限200万tokens/$20；原件/生产配置/sentinel保持，测试Temp删除。长招股书B0/B1/B2、三供应商正式语义质量、并发2/4、默认切换、母G2/G4/G5及原三→新三公司审计循环继续开放，目标未完成。

**Next Step：** 用已冻结来源task/本地view注册显式v4正式协议与decoder、来源依赖/覆盖，先写旧wire/本地scope/费用恢复/E2E反例，再接现有worker/caller和RF消费。只在候选冻结后真实调用，保留原失败与独审；随后推进HKIPO分阶段有界恢复。不能把合法basis或nested task当语义PASS。

---

## 上一工程节点记录 — 2026-10-15（历史，发布状态以顶部为准）

引用归属/恢复共因节点e1b3e234已正常提交；首次正常push由6项兼容问题拒绝（5610PASS/24SKIP），已按真实职责修复并88集中PASS，准备连同用途范围配置节点正常补交/重推。新显式0.9使用单一citation-unit/3，完整原文只发一份；原生QA的回答支撑与提问上下文分别传递，程序恢复canonical ID，不让模型回填来源。context/2和可选claim context字段由既有RF消费者接收，旧None/v1/v2请求字节与已存Ref保持。PDF重放传真实源语言；语言观察逐claim比较自己的事实支撑，避免其他中文段落掩盖英文被翻译。

实际验收：ROOT 146单元/契约、7正式生产E2E、6历史恢复E2E通过；独立审查另跑110单元及20纯反例，无阻断发现。各测试集可能重叠，不相加冒充唯一覆盖数。真实旧5a源码生成activation_pending，由新代码正常恢复，额外模型POST=0，费用/attempt保持；输出结算三字段正常变成真实已发布字节/SHA。新的FF→CWP→RF完整离线CLI PASS；另有原生QA→正式选择/模型/验证/发布→公共compact /3→RF真实CLI PASS，管理层支撑/投资者问题上下文和完整正文逐字段保持。静态Ruff/mypy通过。

新测试全部为隔离loopback，0供应商、母账不变；配置/原件/sentinel保持，临时目录清理。真实HK source-only重放96/96另有收据；旧付费HK的typed snapshot缺失仍NOT_RETAINED，不用新重放冒充旧任务恢复。初始配置快照选错、探针夹具/版本/summary路径错误、13E2E合并超时、mypy及sandbox失败均保留，在所属测试工具修复，未放宽产品断言。详见[验收收据](common-root-quality-evidence/source-attribution-recovery-acceptance.json)和[123份紧凑证据](common-root-quality-evidence/source-attribution-recovery-receipts.zip)。

RF消费者代码caf74c5f已正常推送，416+36subtests通过，精确CI38784099830 SUCCESS；两份物理安装副本只定点同步一个脚本。DU4卡/PWF4f065af2已推远端，用户确认三个作者包均已开工，目录独立IN_PROGRESS；ROOT不写它们的新组件/测试/PWF。[DU4总调度](parallel/du4-2026-10-15/README.md)与[固定接口](parallel/du4-2026-10-15/INTERFACES.md)有效，只有A/B/C大节点。

用途范围配置共因也已TDD完成：统一loader/builder先选择真实profile，llm范围不消费无关search/wiki/schedule/downloader或未选fallback；实际key/参数仍严格，不靠pytest宽松。25新反例与旧配置/模型/purpose共74PASS，真实CLI缺搜索配置/旧路径且无测试宽松变量的摘要+0POST恢复E2E PASS，官方JSON问答另PASS。独审最初找到两处残耦合，修复后5个原fallback形状和4个profile控制均通过。见[范围/兼容收尾](common-root-quality-evidence/scoped-config-recovery-acceptance.json)及[紧凑证据](common-root-quality-evidence/scoped-config-recovery-receipts.zip)。

**仍未完成：** DU4表格期间/选择、经营状态、真实FORM/turn信号及ROOT接线；HKIPO有界性能；三配置供应商正式摘要新旧质量、并发2/4、默认切换、母G2/G4/G5和原三/新三公司研究审计循环。默认仍0.8；工程通过不等于正式摘要或买方研究通过。累计581487 tokens /381768µUSD代理（旧unknown7保留），上限$20/200万tokens，本节点新增供应商消耗0。

Next Step：正常发布本次CWP/RF工程节点并核精确CI；随后处理不与DU4重叠的HKIPO有界性能/真实验收准备。接收DU4后统一接线并重新跑真实摘要质量，保留失败和原分母。

以下为历史冻结记录；若与本节状态不同，以本节为准。

## ROOT 当前接收与真实质量整改 — 2026-10-14

三 DU3 已实收，本地工程提交870b0a78。正常pre-push发现3个Worker重复解码失败及1个旧瞬时元数据预期失败（5153 PASS/24 SKIP），因此未推送；不跳hooks。Worker统一一次冻结快照已68 PASS，原count=1不变；几何测试补验共享/不可变/持久ID及model/Bundle不泄漏，36 PASS，非源码泄漏。

新真实MiMo请求输入13624 tokens（此前64804），但output8192中reasoning6547，最终JSON在c16截断；1次真实POST、21816 tokens、5002µUSD预算代理照账。没有原件修改、没有自动重发，独立测试目录已删除。母累计502598 tokens/353764µUSD（含旧FX保留），旧未知7项继续保留。原费用与FAIL收据不覆盖。

安踏周转天数实际已选中，旧测试把native表格分隔符误作漏读；品牌组合是真实通用语法准入遗漏，另有源已验真的枚举换行观察缺口。分开修复policy和单一测试oracle，不修改金标语义/12项分母。source25/25、fresh9/12只是旧冻结结果，不能提前写新分数。默认仍0.8，A/C和母G2/G4/G5开放。

接下来的统一实施顺序：①并行完成Worker/瞬时几何测试与通用portfolio/源表示观察修复，冻结后集中测试；②正式摘要使用已有generation_policy按narrative用途明确thinking设置，遵守真实配置，保留模型/endpoint/8192/temperature及旧代重放；③先原三零付费回归，再按同一母账进行三家供应商新旧真实摘要、各自独审关键业务/数字/引用/阶段及恢复；④质量达标才切默认，一次大节点验收、正常提交/推送和精确CI。若单次摘要仍不能满足覆盖，再设计复用现AUTO的有界分批，不凭提高cap或补截断JSON放行。

配置依据：MiMo/DeepSeek/MiniMax-M3官方均支持thinking disabled，当前缺少narrative用途配置导致供应商默认推理。工程根因修复将把用途选择集中放在已有配置端口，HTTP只执行并绑定配置，不写供应商临时特判、不增加许可。一般研究推理不变。具体外部依据和下一批真实结果随后进入收据，不能用配置意图代替质量证明。

以下保留此前冻结节点记录；当前状态以本节及阶段表为准。

## ROOT 冻结发布节点 — 2026-10-14

三 DU3 已全部实收，DEPENDENCIES 补交 282aee36/ef59a574 已纳入暂存、138 PASS，作者树只读不变。SOURCE STOP 已覆盖所有 ROOT 子线；正常发布工程节点，正式默认仍0.8，真实质量尚未达标。

源码因果版本：pipeline1.7、business-policy/5、table-purpose/3、source-script-match/1；唯一经营指标facet1.4同步源record与编译runtime，没有第二registry。简繁只作用于匹配，原文/ID/locator不改；混合表只保留实际经营行与必要上下文。264相关PASS＋新55/20Kcase共56PASS。实测同20K用例38.668→15.95s；2000 facts结果SHA逐项不变，宽正则seed快路是主因，固定配置词4096条/256字符有界缓存为次因，原文不缓存。

正式模型由已冻 scalar reading_model_projection=reading-model-input/1选择一个语义视图；仅missing表示legacy，present-null/未知不能误降级。旧0.8及旧unfinished原指令/输入保持，new generation因果不同，same/cross0POST；真实暂停竞态统一作为paused正常控制处理。相关111PASS、最后恢复16PASS、静态检查通过。保存真实MiMo输入重构136913→52618字节（策略111932→27543），96证据/64组引用和公开全context原样；尚未测新真实tokens或摘要质量，不能按字节降幅宣布质量提高。

ROOT因果＋生产选择42PASS；夹具真实HTML必须显式mime_type，不能用PDF默认或伪造frontend使partial假绿。CLI Python/native fd1诊断归stderr，JSON-only stdout18PASS。新正式离线CWP→FF→RF CLI联调PASS：0.8成为LATEST后精确历史0.9 Ref，完整body/context/spans/summary/sourceRef保持，same/cross0新增POST、两负例0预留，临时目录恢复，0真实供应商调用。

真实源码冻结回放原三25/25；新三9/12（SMIC4/5、ANTA1/3、Apple4/4）。精确漏项是分红计划、品牌组合、周转天数；安踏已保留Amer Sports最大股东与独立上市身份，不得把参股关系和周转天数的支持结果说反。分红属于用户业务阅读范围争议，旧12分母保持。仅Apple原文字面引号按独立验证修订，旧金标与5/12失败保留。第一份真实MiMo摘要仍7完整1部分2漏及4引用不足；母账480782tokens，新增11535µUSD只是预算代理。默认切换与三家真实供应商质量、母G2/G4/G5仍开放。

紧凑证据：[冻结节点与未完成范围](common-root-quality-evidence/finalization.json)、[23份实际测试/独审/回放收据](common-root-quality-evidence/final-receipts.zip)，另[前节点31份证据](common-root-quality-evidence/acceptance.json)保存原失败和第一次真实费用。RF aed581ac精确CI38609253663 success；CWP本节点正常commit/push后核精确CI，不跳hooks、不改他人WIP。

## 当前节点 — 2026-10-14 真实摘要之后

三 DU3 已交付。QUALITY dcde9aae 与 GEOMETRY a8cc604d 的全部改动已收到；DEPENDENCIES ef59a574 的补交 282aee36/ef59a574 已实收暂存，ROOT 138 PASS。它们修复同一依赖文件被重复扣字节预算的问题；完整 cache 仍由正式 AUTO 链验收。ROOT 未修改三个作者工作树。

本节点源码：business-policy/4 具名分部归属 161 PASS；唯一 operating-table-purpose/2 按实际经营行筛选、保留建设期/混合表经营行 286 PASS；其版本已进入决策依赖，因果测试 41 PASS；冻结代默认升级恢复 9 PASS（真实 selector 0.8→0.9 与 PDF parser 0.1.0→0.1.1）。旧升级测试实际未运行 bootstrap 的问题已纠正，不把基线失败直接当可删的断言。全部零真实 POST，独立临时目录与配置/原件约束保持。

真实开发回归原文选择 CN 10/10、HK 7/7、US 8/8；换公司开发泛化 SMIC 3/5、ANTA 0/3、Apple 2/4，共 5/12。它们不是未见 holdout；不修改 gold 或隐藏范围边界来提高分数。HK 实际路由是 hkex/annual，不能凭市场 metadata 猜错路由；简繁 matching、品牌/股东关系及混合经营指标仍需根因整改。两次只读 observer 的后置测试工具故障保留，不能签为真实 window 观测通过。

第一次实际配置 MiMo 摘要已生成、公开回开 verified、96 spans，67004 tokens（输入64804/输出2200），预算代理费用11535µUSD，非发票。母累计480782 tokens/已知345998µUSD＋FX hold2764；剩余1519218 tokens/$19.651238，旧 unknown 仍照账，不重记 reasoning。真实摘要独审为7完整/1部分/2遗漏（关键4/7完整），4 claims 引文范围不足，混合 actual/planned 需修。原文10/10不能替代摘要忠实度。

实际请求暴露 reading_strategy 115003 字节，包含 matcher/UUID/未读诊断等程序信息；模型端应使用一个语义投影，公开完整上下文和来源身份保留。旧/新 prompt/generation 必须因果区分。随后同 run 恢复完成且0新增POST，但第三方 PDF 提示污染 JSON stdout，整体 runner FAIL；修 CLI 操作边界，不能在 harness 剥掉提示或把失败当模型失败。

RF main/origin main 已到 aed581ac（源512e85bb精确CI38563752875 success）；正常push416 PASS＋36子测试。reading_context 消费完整，定点同步两物理安装副本完成；旧 assurance/output WIP 保留。CWP 8f1c607b 与 d240871d 待本节点正常提交/推送，默认仍0.8。

### 历史 Next Step（已被当前入口取代）

ROOT 先收尾当前引用归属/恢复节点的跨仓联调与发布；三个 DU4 作者按各自独立卡开工。接收后执行 [DU4 总计划](parallel/du4-2026-10-15/README.md) 的生产接线及真实 holdout，不改默认或跳过质量验收。

## 最新 ROOT 节点 — 原生范围、公平覆盖、正式恢复和跨仓消费（2026-10-14）

正式源层新增 native-pdf-range/1：仅从已读取、明确版本的 native page view 取真实子串，原始 unit/span ID 不变；范围保存原文成员/locator/hash，不持久化全页副本。混合语言连接按实际字符边界解释，英文词和数字单位不拼造。reading_plan/3 在同价值层比较真实主题访次，未知标签也记录实际访次；旧 /1、/2 与 legacy 的 4,000 个结果及诊断逐项不变，不增加 96/48K/2M 上限。

源层 142 PASS；畸形范围绑定 4 RED 后 36 PASS，独审 8/8 PASS。连续意义/语言边界 62 PASS，公平覆盖集中 119 PASS、独审 6/6 PASS；ROOT 公有接口/原文回开/缓存/批次恢复集中 **89 PASS / 80.38s**，生产原件、配置与独立 Temp 恢复，0 外部 POST。这些工程结果不代替真实摘要质量。

冻结真实三原件各 parse/select 一次，canonical closed_group_support 验原文闭包：CN **9/10**（SiC 8英寸产品进展仍漏），HK actual mixed **7/7**，US en **7/8**（Azure 所属业务归属仍漏）；此前失败和 gold 字面修正证据保持。正在只读诊断两个共用根因，未花费新模型预算，不能默认切换。

RF 消费者仅新增有界 reading_context 合同，真实 public Bundle 的 claim/versions 没有臆造新字段。独立作者 153 PASS / 2既有SKIP、ROOT 8/8独审；并 main/push **512e85bb**，正常 pre-push 416 PASS＋36 subtests，精确 [CI38563752875](https://github.com/zhengcb81/revenue-forecast/actions/runs/38563752875) success。单文件 LF SHA ca878e4d1b5cfa254ec1db2734596eab36c7d542d49b3b28b5a95097d5cfa10a 已同步 .agents/.codex 两物理副本（.claude 是前者 junction）；check selected/unselected均0。旧三 assurance文件和 output 未动。

完整离线真实 CLI CWP→FF→RF **PASS / 41.293s**：两初次 POST 仅本机假服务，0 外部调用；0.8 成为 LATEST 后 pin 历史 0.9 Ref，消费者四项实际材料逐字精确一致；same/cross-run 均0新增 POST，两负例0 reservation/POST，三个独立 Temp finally 删除。原失败 RF reading_context 收据保留，不删字段凑通过。

## ROOT真实漏读共因与DU3接收 — 2026-10-14（历史节点）

实际form贯通family/strategy/unit scope/decision inventory，新增准入algorithm版本reading-business-policy/2；通用计费、分部变更、业务驱动、合同转化关系只进入0.9。旧0.8 detector与真实TXT指纹不改。相关439PASS/11SKIP、经营295PASS/45.76s；独立7个反例PASS/0.99s，无新增架构/跨parent/旧兼容阻断。源码本轮仍在统一收尾，未将未完成真实质量标绿。

微软同源/SHA/gold且parse/select各一次：当前87spans/47880chars，8业务金标保留7，旧4/8及初新1/8保持。唯一计费候选入选前闭包1span/681chars，被character_budget拒绝；实际136候选、所有87selected仍priority2/section unknown。原HTML无h标签、标准Item编号以paragraph表示且续页重复；不能将TOC的BUSINESS当body标题，也不能先抬cap补此公司。正在修通用编号/续页策略绑定，再判预算根因。

ROOT首joint receipt的字符cap字段误写50000，实际函数默认及真实planner observer均为48000，没有提高上限；原收据保留，correction明确记录。后续脚本从真实常量取cap，不凭手填。

GEOMETRY作者final a8cc604d干净，三个排他提交本地接7e023a15/c6224a1a/ef69957a；ROOT集中89PASS/13SKIP/12.25s。首sandbox TEMP哨兵无法写是环境错误、未进入测试，真实独立TEMP重跑并恢复；失败空目录已不存在。生产配置保持，0supplier/模型/费用。正在接同一个TextPage的真实dict/WORDS和既有find_tables结果，不另开parser、不复制全页到持久层。其余两作者树WIP保持，未提前接最新施工。

正式默认仍0.8；真实模型、跨run缓存与母G2/G4/G5仍开放。已发布工程CI success保持。下一步标准编号共因→同gold回放→统一A/B集中发布→DU3剩余接收/真实C。

## ROOT生产接线工程验收 — 2026-10-14（已发布节点）

实现d3c57b31＋fixture修复fc2a4513已正常推master；正常pre-push4379PASS/17SKIP/381.75s，精确CI38540579403 success（官方REST只读核，gh不可用不冒称未查）。[发布收据](production-wiring-evidence/publication.json)。ROOT继续下一批真实意义/策略绑定根因，不暂停。三外包树已有commits/handoff，但仍有收尾WIP，未修改/提前签最新交付。

已完成显式0.9 request→正式select→实际策略与唯一原文→同事务final CAS→配置model→Bundle/Artifact/public read；v5旧AUTO先只读history再由唯一Store additive升级，旧费用/结果不重签。QA真实roles/记录/parent边界、HK实际family、结构化SEC form不依赖诊断文案、20K有界planner与多行经营表已修。

集中UNIT1149PASS/17SKIP/3历史factory失败保留；旧版本改为静态已冻结generation，受影响51里50PASS/1新测试遗漏显式selector参数，补正确参数后18PASS。旧11E2E全绿；新7节点集中6绿/1计数observer错接，下沉统一byte owner后该case绿，tamper失败/0新POST/旧账不变断言未放宽。最终独立只读review无新A/B阻断，unknown语言重复读P2；Ruff/mypy通过。详[验收/原证据](production-wiring-evidence/acceptance.json)。

真实whole native三市场同原件对照已跑，源SHA/mtime/size保持。US冻结8业务事实仅1/8新保留（旧4/8），是实际family policy没绑定、经营解释准入和机制预算分配共因，不是拆句；新通用RED先在owned recall-root留证，下一批TDD修，默认仍0.8。真实模型/跨run缓存/DU3几何及母G2/G4/G5均未假签完成。

下一步：正常commit/push本批已完成工程代码/PWF，继续root真实业务覆盖共因；三个外包目录零写，旧他人scratch/Dayu/IQS不动。

正常pre-commit捕获一条新负例用了Windows绝对路径字面量；改为独立tmp_path构造同义路径，13受影响断言全绿/2.06s。没有加基线例外或跳hook；本轮工程失败和自动检查修复一起留节点收据。

本地代码已正常commit d3c57b31。首次正常pre-push扩大到202相关文件/3809items，3795PASS/11SKIP/3旧夹具FAIL（407.94s）阻止远端更新。两例无列名SQL INSERT及一例写死迁移版本；同类盘点后改具名列/当前版本范围，保deep一次、COMMIT前、rollback/unknown accounting等断言，受影响30PASS/8.08s与Ruff绿。详[推送修复](production-wiring-evidence/push-repair.json)。正常补充commit/push中，不重复把旧失败称远端CI。

## ROOT当前实施与并行拆分 — 2026-10-14（此前记录）

主线实际开始Phase A：19项新阅读budget反例RED/2旧回放PASS后扩既有planner为reading_plan/1，共享依赖unique成本/主题多样性/完整闭包/字符与工作上限；旧默认和selector0.8.0不改。独审发现嵌套signature工作漏计、闭包实际扫描漏计、签名metadata未限、低预算误诊及依赖中已发value未记主题/签名，均按根因统一修复；最终38/38独立probe通过。尚未把ReadingPlan接正式生产，不标Phase A/B/C全部完成。

受影响首轮87PASS/1sandbox tmp setup error，独立真实Temp88PASS并恢复；追加回归一项短fixture不足旧hint12-token门槛，实际只有8tokens/self-repeat=false，改为17tokens且加complete/min12前置断言，原失败保存，没有改旧算法或降低选择断言。类型检查与ruff通过；最终集中节点结果按随提交证据记录。

三张新DU3卡READY_NOT_STARTED：真实质量benchmark、纯决策依赖manifest、真实版面快照投影，排他目录/独立worktree/DU3/1接口。ROOT继续source_catalog/DU选择和正式AUTO接线；两种fingerprint与几何实际消费缝留给ROOT，不让worker各建权威路由/布局/数据库。只在A/B/C大节点验收；原件/配置保持，0model/provider/network费用。下方历史不作为当前调度。

## ROOT当前收尾推进 — 2026-10-13

用户要求完成共享引擎＋多份文档阅读策略并合入PWF。已将研究、DU/DU2接收和剩余生产工作统一成根task_plan＋completion_implementation；母跨市场与叙述计划只引用这一执行表。

两个独立agent只读核入口、选择断点、缓存因果与现有factory/reuse/outbox/recovery测试。发现并纠正“旧最终HTTP重复全文”推断；明确select决策依赖不同于最终提示指纹，冻结两阶段CAS顺序以避免重复parse/select。

此次是计划合并与施工细则完成，未运行新代码/模型；A待先RED，B/C保持pending，生产默认和真实研究未宣称完工。已完成模块证据仍引用DU2 receipt，不重复验收。以下旧进度为历史。

## 当前执行入口 — 2026-10-13 DU2 接收

[DU2候选模块验收/发布](du2-reception/acceptance.md)：三新包与共享ROOT修复已接收，1135联合离线PASS、四PDF658原文span验真、同源10Q六项PASS；唯一24/14运行catalog、层级策略与有界layout/原文上下文已实际消费。已并 master 并推送 `deb7eb7d`，[精确CI](https://github.com/zhengcb81/company-wiki/actions/runs/38476678472) success；发布收据见du2-reception/evidence/publication.json。生产默认模型尚未切换；粗几何/实际0列保持partial，旧MSFT4/8与B8/B10–11/C12–15、母G2/G4/G5开放。下面旧状态为历史。

## 当前发布状态 — 2026-10-13

旧 DU 三包接收与 ROOT 共同修复已并 master、推送 `9e9907cd7c013ecf0a6787dd0f591ba242eb223a`，[精确 CI](https://github.com/zhengcb81/company-wiki/actions/runs/38462668903) success；[接收结果](reception/acceptance.md) / [下一步](reception/task_plan.md)。首次 push 抓到共享 Windows 同目标 rename 争用，已 TDD 根治并实际1000写入零失败，未跳过测试。新 DU2 三卡仍独立施工，生产模型摘要与真实业务漏读/G2/G4/G5保持开放。下方“发布中”是历史。

## 2026-10-13 旧三 DU 包 ROOT 接收

最新 profile e74b9dcb / structure f8f456a3 / benchmark b891cf74 / ROOT 4b6a8599 全部整合；接收修复分别 7fa6dee2 / ead4aab6，ROOT e9af9ae9 / 1c5784cb / observer 8a5721db。一次联合491 PASS / 四原件11 PASS，追加 seam5 PASS，独立最终审查通过。来源/配置/测试恢复通过，0模型0费用。
修复真正的策略消费、最终预算断链和自证式评测；gold 全保留。微软真实 baseline 4/8 关键业务漏读如实 FAIL，生产与母计划未完成。
新 DU2 三卡用户已分发，独占目录零写。当前发布与精确 CI 记录见 [reception](reception/task_plan.md)，后续统一集成由 ROOT 承担。

# 进度

## 2026-10-14 12:15 UTC — 原件回归结果与范围载体

三份最终实际parse/select各一次，来源SHA/mtime/size保持：HK原单span判定7/7；独立共同oracle改正HTML document定位后US8/8。CN同原件/新gold为2/10，原strict0/10和保守oracle1/10均留历史receipt。96原生碎片仅3339字，核心候选大多已识别但budget_full；下一步不是给样本加boost，而是原生source range进入同一planner。

实施细则已补具名native page view、原始range绑定/回开、历史0.8兼容、唯一carrier字符/槽费用与因果版本，来源/候选/RF/ROOT排他。源view只在内存共享，输出不保存页全文；不存在新的审批/签收/任务库。RF36新DTO TDD绿，旧相关集中验收中，尚未并线。

## 2026-10-14 11:50 UTC — 连续性收尾与真实跨仓缺陷

a117fafc已正常推送；精确CI38554334091 success。连续性作者最终STOP：43正式＋10原独审53 PASS（真实exit0）；ROOT独立重跑原10probe10 PASS/1.93s/SHA一致。旧相关257 PASS/39.06s，记录wrapper编码失败与真实后续exit0，未将前者改签PASS。经营表筛页使用唯一catalog可选bool强信号；小真实PDF经营矩阵及新span原解析器回开2 PASS，0.8保持。因果inventory纳入连续性FEATURE，18 PASS。

同原件cn-h1/hk-annual/us-10k原生最终回放已启动，每份parse/select一次，无模型费用。CN金标已独立确认p18原文无“已于2022”首字，仅明确修正字面quote；旧金标压缩与十事实分母/原FAIL保留。跨块quote oracle独立校验中，不用同页全集提高召回。

C runner真实离线CLI：新旧摘要各1本机POST，CWP Store/public read/same-run/cross-run及FF复用通过；RF新Bundle被旧消费者精确字段集合拒绝，保留原失败材料。RF独立worktree进行完整DTO/引用/投影兼容TDD，ROOT负责接收并线；不触碰RF已存在assurance/runs和output。正式模型仍0调用，默认仍0.8，A/B/C未全部完成。

## 2026-10-13 深化复审

已做三份独立只读审查、三组ROOT纯函数复现和一份独立真实HTML反证。新增 [review](review/README.md) 的报告/矩阵/ROOT细则及三张目录排他的卡；保留原DU/1和四个旧工作树。实现缺陷尚待ROOT按新优先级修复，不把本次文档交付写成生产升级完成。新包准备与发布记录在review/progress。

## 2026-10-13 用户确认共享引擎与策略配置

- 将用户明确同意的架构写入design和当前计划；三张已分发施工卡及DU/1接口继续有效。
- 纠正README、task_plan、implementation中“尚未分发/等待W08”的过时当前指令。W08已完成，三DU包施工中，生产接线与真实G2/G4/G5仍待完成。
- 本次仅更新ROOT共享计划；没有改三个独立工作目录、冻结接口、施工卡或生产代码/配置，0下载、0模型调用、0原件写入。文档变更检查沿用git diff --check，不增加业务测试节点。

## 2026-10-13 并行实施位置

- 用户确认三包已分发；ROOT没有写三个工作目录或独占模块。
- W08剩余RF/Audit已验收并主线，RF精确CI38367459762绿；Audit两个安装副本已6fresh CLI实测。详母W08接收汇总。
- 下一步ROOT主线准备G2真实批次/预算与DU接口整合；等待的是独立交付结果，不创建逐小节点批准。

## 2026-10-13 ROOT

- 按用户要求启动设计调查；读取 PWF/PDF 技能和现有路由。
- 本轮0下载、0外部LLM调用、0原件写入。当前只增加本子计划；生产代码未改。
- 下一步：原件抽样与架构实证。

## 2026-10-13 调查完成

- 20文档原生扫描/重点抽读，4页图像目视；3文档真实parser0.1.1/selector0.8.0回放共21.956秒；恒锋同parse类型/预算对照确认仅调cap不能解决建设期漏选。
- 完成design.md、INTERFACES.md、implementation.md与三独立卡。保留当前存储/来源/Worker/配置模型责任；新增结构和profile，不加权限/签收。
- 原件0复制/改动，LLM0调用；四PNG已删除，原始观察压缩后删除自有JSON副本，摘要与压缩证据留本子计划。
- 当前只写文档/调查脚本；无生产代码、配置和其他仓库改动。尚未分发或启动任何harness。

## 分包准备与发布

- 调查/设计已正常commit `7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8`，静态hooks通过/无适用代码检查；21文件1068行含两份紧凑压缩证据。
- 三个稀疏worktree已在README路径准备，分别codex/du-profiles-20261013、codex/du-structure-20261013、codex/du-benchmark-20261013，共同base7f6f7cbd，干净；每份约20MiB代码/测试，原件不复制。
- 文件链接/JSON/压缩回读检查通过；母PWF仅14行导航新增，原正文按HEAD字节保留。此轮无需运行完整业务测试套件，已有3份诊断用来验证设计问题，未声称修复。

## Phase A预算组件节点

纯planner104集中PASS/38独立probe PASS，mypy/ruff通过；原RED、环境失败、测试fixture纠正及独审中间失败留证：[小归档](phase-a-budget-evidence/receipts.zip)/[组件收据](phase-a-budget-evidence/acceptance.json)。只签纯planner，生产ReadingPlan/候选/最终模型输入仍待接线；旧默认与原件/配置保持，0付费。

## 2026-10-14 正常发布

实现195aba20与工作树清单36f15dd0已推master，精确CI38522896889 success；正常pre-push3268PASS/11SKIP（204.59秒）。104集中/38独立收据逐字节归档后清本次owned scratch，失败sandbox Temp已无残留。三harness树保留READY_NOT_STARTED，其他历史scratch不动；纯planner不冒称Phase A整体完成。精确发布见phase-a-budget-evidence/publication.json。
# ROOT 正式接线实施 — 2026-10-14

已读选定PWF并核对master4204180a tracked clean；三DU3作者树基线未变化，仅只读查看。ROOT分工互不写外包owned目录：生产选择TDD与结构经营表、正式wire后接planner效率、AUTO Store/factory后接独立生产E2E；ROOT统管源桥/trace producer/发布接线和PWF。

TDD真实失败：生产首轮5FAIL/10PASS；追加sharedcontext字符1PASS；独审脚注/拒绝包/work停止4RED后20PASS；跨原件同文同locator1RED→1PASS；decision inventory3RED→3PASS。新transport首轮7RED/14PASS→30新PASS/246相关PASS；Store16有效RED→143相关PASS。临时SyntaxError、mypy lambda联合类型错误和fake fixture未加新optional字段均留记录后修，不能算业务缺陷已验收。脚注/拒绝包/work停止/父身份为真实代码缺陷已修。

真实原件只读窄页probe：恒锋增发真实project anchor可用；名创p12经营表漏读实证新增计划；没有调用供应商、写原件或生产配置。长文20K负例基线只选2个且late漏读，context1.09MiB；优化后待集中复核。4新正式production loopback端到端PASS/65.91s，same-run恢复和付费后待activation不重复POST；真实供应商与完整decision-cache仍未签收。

根任务继续，不暂停、不标升级完成。下一节点：长文/经营表及新trace界面集中验收→正常commit/push；然后作者组件接收和真实同预算质量/消费者泛化。ROOT scratch均在.planning/shared-reading-production，最后压缩留证并恢复；外包与历史scratch保持。
# 2026-10-14 ROOT — 真实价值准入、预算排序与细几何接线

正常commit `a117fafc` 已完成（48文件，源码/测试与63,593B压缩节点证据）；正常push测试进行中，尚不声称远端已发布。pre-commit host-assumption拦了一个负例夹具的固定C:/路径，改用tmp_path保留“不迁移物理路径”断言，定点1PASS后全部hooks通过。三载体真实CLI跨run缓存强制complete并且0新增reservation/POST，集中143PASS/37.83s；A/H周期用途统一source信号修复195PASS/2.14s。

随后正常push完成：master fc2a4513→a117fafc，prepush4771PASS/24SKIP/410.16s；[精确CI38554334091](https://github.com/zhengcb81/company-wiki/actions/runs/38554334091)于11:10:15UTC仍in_progress，不能提前称success。正式外包三线均已并线推送；下一节点开工解除的是测试冻结窗口，不是材料/权限批准。新native矩阵筛页真PDF反例RED1FAIL（old/new均未扫描），旧0.8不动，0.9接同asset强table信号正在施工。

后续官方GitHub只读API回收该精确head的CI结果为completed/success，见publication收据；不是借其他提交的CI绿色。ROOT另独立只读原件p18核“于2022年推出”存在、“已于2022年推出”不存在，与agent视觉核对一致，下一冻结gold版本须显式修订并重算双算法，不抹旧FAIL。

下一节点：只读CN p13/p18表明8类关键句跨2–4真实native blocks（甚至字断裂），background非first成员没有anchor机会，所有43已承认meaningful fact其实都入选，故不是加预算。有限连续上下文与配置经营表筛页接口已写INTERFACES。独审发现GAN金标多“已”字，原件视觉确无；保留冻结gold与FAIL，不悄改分母/重要性。正式摘要0外部调用，预算母账不变。

金标字面修正已显式执行：[修订收据](gold-literal-revision/receipt.json)与旧字节gzip。cn-h1新gold SHA10d1dc12…a335，只去GAN支持quote开头的“已”；10required/7critical及阶段/数量全部不变，必须两算法用同新版gold重新冻结比较。旧e2602c66…金标、旧0/10 FAIL不改。配置经营表筛页实际小PDF反例从1FAIL→1PASS；新增实际四行table locator回放在修正测试API参数误用后2PASS，真实旧0.8无table、新0.9发现表、原正文定位不变，既有强制目标页回放全部spanIDs验真。

真实摘要执行器的loopback中间FAIL诚实分类：Windows launcher缺main guard、向typed hash接口误传dict、误读不存在的receipt.body_sha256皆为测试执行器构造/接口误用；cross-run复用旧worker工作目录触发正确防覆盖，已纠正prep为每run独立worker-<run-id>（同catalog/AUTO不变），不改生产防覆盖。缺gold已实证0reservation/0POST，最终对照/恢复仍待执行器集中结束，不能把loopback称真实supplier质量。

微软原件/金标未变，reading_plan/2在同48000字符/96span上限取得8/8 required_business、90spans/47999字符（parse2.75s、select6.19s、各一次）。原1/8、7/8、章节接线后2/8中间FAIL原样保留；2/8暴露纯页码/项目符号/空标题及多标签访问总和偏置，已从通用价值准入与同一heap排序修复。当前结果仅原文锚点召回，不是正式摘要语义PASS。

PDF原生前端同一次TextPage取得真实words/cells/fonts，独立36PASS、集中263PASS；真实四原件单页原unit/text/locator/旧EvidenceSpan保持。共享layout_hints1.2.0实际消费fine geometry，集中143PASS（143不是整仓），新模块类型检查绿，旧整包既存26项类型诊断未新增。ROOT新增compact native_frontend coverage，有效RED2FAIL/1PASS→31定点PASS（含28 cache tests），不把细坐标partial误标正文未读，诊断保完整计数及128样本，不持久化细metadata。

真实港股whole-PDF新fine回放仍0/7、96spans/13786字符（parse7.23s、select12.75s），尚未通过。新oracle收紧为实际物理页和同一真实闭包组内AND，未调整金标或原件；定位第12页各层遗漏原因后再继续。A股cn-h1回放进行中。0付费/0下载；摘要与默认切换未验收。

DU3三树最新均干净，QUALITY本地接收四commit至804dfbb7、ROOT217PASS/7SKIP；DEPENDENCIES正常接收六commit至d6e91356，排他owned目录核对，未覆盖外包WIP。PDF/projector因果版本独审有遗漏，作者在补实际used proof与独立projector版本（HTML不受影响），不凭MIME伪造实际使用。

## 2026-10-15 DU4 准备记录

三独立稀疏工作树已创建并附各自卡/接口/真实观察/参考设计，实际各约20.8MB，三份约62.4MB（源码15.2MB，另根工程文件/夹具；共享 Git 对象）。无原件/生产 config 目录。包本身尚未实施/测试，READY。准备中一次误用 PowerShell 不支持的 Bash 花括号路径导致 ParserError，改为显式四路径；一次猜测预算文件不存在，改用 CodeGraph 定位既有 WorkBudget；CodeGraph node 首次参数 name 无效，按 symbol 调用修正。均未修改源配置/原件。

DU4 启动核对：三个计划入口/独立 Git 分支/稀疏目录与本树 src import 均确认，diff-check 通过；尚未执行作者组件测试。核对脚本首轮子进程输出使用本地编码导致 UTF8 解码失败，改显式 -X utf8；第二轮把 Python repr 路径直接与原始路径比较导致观察器断言失败，改 JSON 解码后的 resolved Path 比较，最终三树通过。均为准备脚本问题，无源码/原件变更。


## 2026-10-16 ROOT继续

用户确认三DU8包发出，launch/总表更新DISPATCHED；ROOT不进入三作者白名单。ET228/10gold与隔离99+跨cwd7已冻结待正常发布。v4最终26PASS/172.11s含无.planning部署；0供应商，六错引/真实holdout仍开放。


## ROOT工程节点更新 — 2026-10-16

ET 0cb71731已正常并线推送且精确远端HEAD一致，2个未跟踪原项保持。CWP新增用途前置真实RED→修复、原生表未知质量标记与capture因果；1016PASS/11SKIP，VRSK1966632和MSFT1035473工作单位不耗尽，39/96片段原范围验真。旧probe在沙箱Temp末级目录删除失败记录保留，新probe改工作区owned临时根并验证清理。


## DU9与当前审查 — 2026-10-16

三个READY工区共50,750,798bytes，0生产原件副本/0供应商。正常docs提交070ae520已推远端，主仓活动源码不暂存/不恢复。初启动全status相等检查捕获ROOT授权structure/tables.py并发修改，三个seed已完成；只读恢复核对精确seed/branch/clean/card字节后产出launch，不重建或覆盖源码。独立审查的同表混合行/partial问题修复仍待最终验收；原1016不能代表最终源SHA。


## 2026-10-16 DU8接收

FF作者C只有21/26/14PASS，完整完成仍OPEN；原15基线失败不能自动当新回归，也不能因基线存在就绕hook。AUDIT最终源码a915456，后续仅文档至3ed248df，必须接完整历史不能按旧handoff只取首feat。两作者树只读，ROOT用独立树审查和修复。

### 接收收尾脚本环境错误与恢复

ROOT临时工区已正常移除，但收据脚本默认GBK解码git worktree中文路径而报UnicodeDecodeError；随后cleanup-final缺失使复制和定点add失败，空commit未产生提交。改明确UTF-8只读复核后生成收据，不重复删目录、不改生产代码；原WIP继续保留并核SHA。此为ROOT收尾脚本错误，不是RF测试失败。

### 最后ET接收的实际联调结果与遗留断言修复

ET454PASS、10gold、ruff绿；FF117PASS（显式W07_ET_TOOL真实ET CLI，未skip）。CWP provider/import原11PASS/1FAIL仅文件名旧前缀：现canonical writer经d71c8e4f已统一内容SHA/Windows路径预算命名。旧contract不该把供应商或发布日期绑定物理命名；移除此一旧前缀断言，保留.json类型、完整原件SHA/字节、SourceRef、provenance publication=None/as-of未知、reader query/open、历史截止拒绝与重复复用。首次失败收据保留，不修改生产storage或ET已审源码。复测只重放受影响CWP联调，不再重跑不变ET454/FF117。

## 2026-10-18 ROOT继续：两外包独占，质量整改与推送范围调查

两张DU11卡已发出，RF citation-closure及FF local-transcript-reuse作者工区继续独占。F3在内部独立工区完成单一market-qualified代码规范化与canonical候选投影；不同agent独审37PASS13.20s，真实FF两方向零下载/原文SHA/同尺寸篡改拒绝通过，等待正常提交接收；真实HK旧C消费节点仍待0新增POST重放。

ROOT F1先15个行为测试9FAIL6PASS，修后15PASS；补跨句借词/审计RPO/真正审计软件/预算耗尽反控再3FAIL18PASS，修后集中179PASS4.88s。源用途与语法关系分开、逐分句观察、实际业务财务附注保留、未观察用途不绕工作预算回退。尚未提交，不把它视为F2闭合或真实C通过。F4源卡按已有策略分配同56KiB已在内部并行完成56PASS，等待不同agent独审及ROOT字段生产投影测试。

正常push9daa0c38被本地600秒上限拒绝：6696项进行至98%，没有已出现的断言失败；不是远端CI失败。首个过宽触发为nested fixture-only conftest，全量推断忽略pytest目录责任。先1FAIL12PASS复现，修后56PASS2.54s，独审额外发现并修顺序别名遮蔽/导入hook/装饰参数和函数默认值/注解模块执行；global hook/plugin/未知路径仍fallback。该修复仍待最终独审。当前完整提交范围仍因tools README未知资源等触发full，不声称已经缩成局部，不抬600秒、不跳hook、不盲重试。下一次正式发布在集成大节点集中执行。

### 最新纠正：推送范围实验撤回；F3已并主线

独立审查用真实最小反例确认，nested conftest即使只有import+fixture，其import仍可造成全局副作用，局部1PASS不能证明兄弟测试安全（完整1PASS1FAIL）。不继续膨胀成递归静态证明工具；本次两个门禁文件已精确恢复HEAD，独审结论WITHDRAWN_NOT_ACCEPTED，600秒与原门禁未变。完整提交范围另有tools README等触发full，未声称解决全量开销。实验GREEN56仅是局部，不是签收；正常发布仍须集中大节点检查。审查一次失败诊断误含继承环境repr，落盘记录已去除敏感值，不复制值，未声称工具历史可撤回；后续纯实验使用最小环境与受控字段。

F3代码310252bd、交接8b40b479已正常merge进入母仓；不同agent实跑37PASS/13.20s，当前仅本地，尚未push，真实HK C消费0新增POST回放仍OPEN。F4独立22PASS/3.79s且runtime冻结SHA一致，allocator工程PASS；ROOT生产字段投影另验，不能宣称真实三家摘要绿。

ROOT新F2强反控4FAIL/1PASS已复现：单块open-end漏标、native块中部缺前驱仍当句首、表格ambiguous仍生成card、heading混入support。修后58PASS/4.63s；保留原证据查询，summary将真实table结构未闭合记unsupported，不推数字归属。更广936项先935PASS1FAIL/62.02s，捕获裸allocated RPO被误升；修后又发现真实含未来转换期的RPO被误杀，补用既有clause-bound转换观察区分，正重放最终集中套件。ROOT F1/F2冻结独审及真实0收费源选择回放进行中；未新增真实供应商POST。

### 真实零费用回放阻止错误并线

ROOT F1/F2独审四delta已37PASS2.49s/13最终SHA一致（初审保留），但这仅工程修复。真实同原件/同16M/96span/48000字符/56KiB上限：CN关键源与canonical10/10，模板/期权/租赁旧噪声消失，三断句/指代仍OPEN；US关键源与canonical8/8，RPO及转化不再被容量挤掉，0API/0原件副本/原件hash不变。HK初轮输入装配不等价已保留，实际mixed/titleNone重放仍0/7；同oracle+同goldSHA对旧正式a8bundle却7/7，确认真实召回回归，不能归咎金标或放宽验收。新质量实现仍隔离，不进主线；先对新增native singleton/open-start defer做有界内存因果ablation，不引入生产fallback/开关或加预算。母仓已审F3/旧工程正常push914e0283另进行中，源码稳定，不宣称推送成功。

### 推送阶段并行与HK召回修正

正常push914e0283再次600秒超时，实际全部unit及几乎全部smoke已完成，最后停B10；不能把停点等同B10耗时600秒。根因是Windows全量bootstrap与CI独立合同责任串在同pytest中累加deadline。本次只fullfallback拆为两个独立pytest并行：全部unit、排除已覆盖unit的原FAST_CONTRACT非unit集合；集合无删无重、各600上限不变、不同shortTemp、禁cache与bytecode，任一红保持失败并等待两边清理。不改普通affected/CI smoke入口、不修改CI、不抬deadline。真实5RED→15PASS1.95s，含两真实Python进程Temp/哨兵恢复、Barrier同时启动、任一失败/包装异常/完整case集合；不同agent实际实现独审PASS，见review/du11_push_phase_isolation.md/json。正常hook实测收益仍待，不承诺CPU竞争下一定<600。

HK根因受控：保持新finish仅放开left_closed仍0/7，实际OPEN_START触发0；原finish7/7。新singleton无句末即defer额外挡1951单位，windows349未变。physical连续性没有edge不能判整个原block语义不完整（可含段落/多句/列表引介），恢复其候选地位并报告standalone/semantic_not_evaluated，不伪造closedwindow；既有多块open尾与限额defer不变。原错层测试/RED历史保留且按责任修正，新89PASS5.26s；实际生产HK同DTO/cap恢复selected7/7、canonical7/7、27.147s、12,098,578/16M单账户、0API/0rawcopy/原件不变。三处CN真实闭合缺口已用p16/17/31、102原单位定位，不称F2/C完成；独审正在最终有限delta复核。

</details>

### 2026-10-21 R1 N1冻结节点完成

已固定药明康德→药明合联→Snowflake、20项通用检查、真实代码/195份安装内容SHA、母预算和首家隔离scope。配置脚本真正执行通过原生schema校验，0下载/0模型；独立agent终审PASS_PREPARATION_ONLY（r1-holdout-freeze-review-20261021），不是来源或预测通过。母账真累计1,504,997tokens/$0.615538，剩495,003tokens。下一步立即派独立executor完整RF，封存后四路独审及根因专家；旧NVDA和未来八家任务保留。
