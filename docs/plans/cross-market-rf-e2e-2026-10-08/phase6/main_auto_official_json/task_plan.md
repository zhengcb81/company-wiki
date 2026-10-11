## 当前执行与发布状态（2026-10-11T06:56:13.845649+00:00）

- P7-AUDIT已正式接收：main c0993332，最终147 PASS/38.226s、独立5/5复验绿、两个独立安装目录已同步；没有remote，CI=not_triggered。CWP32a412bb、RFb7fe04aa、FF08ec85b2均已普通commit/main快进/push，精确源码CI38118943063/38118272390/38119051847均success。
- 已完成源码与已安装入口一致。RF/FF的.claude是指向.agents的junction；RF7脚本、FF4脚本各只是一套物理文件，不能把两入口14/8条逻辑路径说成双份磁盘占用。FF同步4物理文件后重复alias旧SHA断言退出1，已真实samefile/原字节复核完成，不再重复写；错误和恢复均收据。
- 正常CWP push实际2783 PASS/191.42s（whole221.6422s）；3234只是全unit+精选非unit理论union。先前额外5627测试超360s仍是timeout，不冒签；继续用现有受影响范围和CI，不删反例、不增加每小步复核。RF284 PASS/2subtests，FF645 PASS/7环境SKIP/78subtests，skip具体原因保持。
- Wave2已派两排他树：WP02摘要语义（新CWP树32base）与WP06研究规范（RF b7base稀疏92files/1.10MB）。ROOT负责公共接口、配置G2和发布，worker不写共享PWF/旧run/production config。
- selected-availability只读调查确认c620多issuer原件null全局事实正确；所选行只有revision clocks，无发布日期/链接或prior capture，actual2.2 availability=null。该项继续unknown，不能捏造历史资格；未来subject qualification seam仅在真实来源proof可用时由ROOT做TDD，不为此阻断其他合格年报/官方release的研究链。
- 原三家12sealed审查FAIL/246映射、原raw、Dayu、生产config及邻仓WIP保持。本轮0供应商/模型/新费用；母账413778tokens/334463µUSD+FX2764，剩1586222tokens/$19.662773。mW03两唯一raw788213B和w4p1共享fixture仍保护。

[精确发布收据与当前接口状态](../w04_post_pw03_common_roots_2026-10-11/evidence/integration/publication-status.json)。

## Next Step

接收WP02语义与WP06研究规范的排他交接，ROOT并行准备实际配置G2；只归档已STOP发布证据并正常推送。然后G2真实有限摘要→public读→RF实际消费，G4原三家新执行/12独审，G5新A/H/US及池loop。工程闭包不等于研究验收；主目标继续active。

以下带日期内容为历史记录。

## 发布验收范围纠正（2026-10-11T06:31:19.815369+00:00）

P7-AUDIT main/两处安装已完成；RF lint补充3文件无逻辑变化，完整9文件Ruff及既有mypy/30新测试绿，普通commit b7fe04aa已完成，main/远端发布在执行。FF WP04独立94checks PASS、真实FF→RF四类联调及200旧/新兼容绿，未签真实新下载/经济质量。

ROOT额外全量命令超360s不是PASS，也未保存partial stdout/起止UTC/PID。只读调查实际选择5627项=3103unit+2524contract，当前发布/CI范围应3234=3103unit+131精选非unit；2438项额外手动contract含45s/10s故意慢case，且该手动命令漏精选integration45。纠正为现有正常push-checks，不重复整个manual全集、不删慢测试/放宽断言，不以局部绿冒签全套。下一发布命令日志直接写exclusive文件，timeout也记录收据。独立报告在W04/evidence/independent/major-timeout。旧原始失败/所有sealed报告保持。

Next Step：正常集中提交推送CWP关闭源码/PWF，运行既定CI同范围大节点并观察精确HEAD CI；并行收尾RF/FF定点发布。Wave2摘要语义/研究authoring与G2/G4/G5仍未完成。

## 当前执行入口（2026-10-11T06:18:38.272553+00:00）

- P7-AUDIT正式接收：原代码18a52f16、交接40b38103，与W04修复一起正常commit/审计main快进到c0993332623637d53f059350a382d99a95ef731d；main干净，无remote，因此CI是not_triggered。147项最终全套PASS/38.226s，源码12条SHA前后及main一致；独立原1P1/4P2复验5/5 PASS。两处安装各只变18文件，22文件完全匹配，8未改文件保留，4真实CLI启动PASS；0供应商/模型/新费用。[接收细则](P7_AUDIT_ACCEPTANCE.md)。
- WP01 CWP与ROOT generation独审PASS（91 actualchecks）；WP03 RF源码/30新例+兼容204PASS/1已有skip收尾完成，G1独审已STOP、材料发现为空；真实H1→capture→rationale→完整公式通过（技术图不签经济校准）。完整投影未知公开日父来源在真实capture仍被正确拒绝，不能冒称完整经济链已跑通；H1原/1完整技术rationale链实测，不代真实预测校准。
- ROOT审计builder预期SHA/同stage deadline/CAS→私有普通副本/失败pin/有界清理恢复已完成并安装；最终147是最终版本，不把旧141/旧96冒充最终测试。别名限额取min、季度/半年错配、末段deadline与部分copy恢复反例均保留RED。
- Wave2 WP04已在FF隔离tree开工；24FAIL/2PASS真实RED封存，ROOT新增单一serializer error_envelope seam排他写权已写WP04_INTERFACE_AMENDMENT.md。RF consumer与audit typed消费已做，仍需FF producer真实联调；CWP/RF目前待正常集中发布、对应精确CI与定点安装。
- 后续顺序：发布已关闭源码→Wave2 WP02/WP04/WP06→配置实际G2摘要/公共读/消费→G4原三家新执行与12独审→G5新A300750/HK00175/USCOST→NVDA/池loop。旧三家sealed partial/FAIL及246映射保持，不签研究PASS。
- 母账413778tokens/334463µUSD+FX2764保持、余1586222tokens/$19.662773；本轮0新模型/采集调用。原件、production config、Dayu、邻仓WIP不动；HK唯一新raw两件788213B仍保护，未完成持久原字节/replay与必要catalog/AUTO恢复前不删mW03 TEMP。

## Next Step

完成CWP/RF第一波关闭源码的正常发布、精确HEAD CI及必要定点安装；FF WP04独占写集继续并行。


正常发布发现：RF首commit按现有pre-commit被拒（2 unused imports/7测试bootstrap E402），原失败log已保留；WP03仅纠正3文件并集中校验所有9文件完整Ruff，不能用C901局部绿代替发布静态检查，不放宽全局lint/不绕钩子。CWP最终一次全单元+契约在隔离tree运行，未完成前不签全套GREEN。

以下带日期的状态为历史快照，按以上入口执行。

## W04 第一波实施进度（2026-10-11T04:24:27.138451+00:00）

- 已发布规划3d540797，精确远端CI38110440211success；P7-RF47f497ad已主线/安装验收。
- WP01停止写入：新18+旧兼容110GREEN、真实65父 public /3及两件nonperiodGREEN。最新流65父/195条、问题流11/33、预收集10/29合计257条；provider_company_id非空union21，不把此前24当证实发行人数。
- WP05停止写入：23请求/CAS+9状态/provenanceGREEN。ROOT shared generation真实3NULL RED→98GREEN；审计expectedSHA/deadline/CAS/privatecopy/失败pin/有界清理恢复共13GREEN。尚未发布安装，不签研究质量。
- WP03正在收尾：实际CN H1四/五键及zh-family与zh-CN原声明、65父 /3、US两nonperiod与错期间拒绝已联调；最终报告尚待ROOT读SHA。
- G1 CWP与G3 audit两个独立审查正在执行；ROOT一次G3全部兼容套件运行。独审发现composer blob_store未透传cas mode，真实反例将保留并补ROOT amendment，不以早期局部GREEN掩盖。
- 后续：集中修独审实质问题→正常发布/定点安装→Wave2 WP02/WP04/WP06→真实配置G2→G4原三家新执行/12审→G5新三家及loop。旧三家sealed partial/FAIL保持；母账413778tokens/334463µUSD+FX2764无新增；HK唯一raw2未迁移前不删TEMP。

# MAIN：官方 JSON 接入同一叙述 Worker

## 2026-10-11T01:15:38.127724+00:00 — 来源真实准备封存；原三家独立执行 READY

SOURCE 8 register/29 source-facts/3 public reader共40 capture全部exit0和输入输出完整；32/32 Ref2实字节读回，29/29旧patch+proof精确原样转用，新copy原件0B。70保护文件SHA和32原件stat未变；0 provider/model/新token/费。handoff SHA4554b035…与来源报告bf375dd7…冻结，source owner停写；随后ROOT只对自有scope作一次READY_SOURCE_PARTIAL冻结，保留CN FY24、HKoverview及无旧patch资格差异，不把PARTIAL当失败许可或强制PASS。

每公司消费者pathless交接+独立施工卡已落地；deadline仍真实03:06:57Z，旧unknown母账保留。正常docs-only提交推送此真实进度后派3 fresh上下文，不读取旧forecast答案，之后每公司4独立审查/专家共因。工程0f7540b5/3163PASS/CI38100444473与RF47f497ad已接受，P7-AUDIT未交源不动。Next Step：正常归档当前已完成记录→三独立RF执行。

## 2026-10-11T01:08:52.246654+00:00 — 修复普通发布闭环；原三家新隔离环境已初始化

CWP本地/远端master一致`0f7540b50e404eb1083192ad5412b9aa6fa4d4bc`，normalcommit7.67秒/73文件/54原字节evidence核staged blob相同；normalpush实际3163PASS/174.85秒（全181.86秒），精确CI38100444473 success。生产config/source_catalog.yaml及config.yaml前后SHA保持，canonical clean；全部原RED/独立反例保留，没有绕hooks。真实回执[normalpush](evidence/source-10-publication/normal-push.json)、[exactCI](evidence/source-10-publication/exact-ci.json)。本机gh不在PATH，使用GitHub公开只读API核同HEAD；不是CI失败。

按真实来源能力调查，旧readonly catalog+新AUTO无法隔离新artifact/projection写，故新ownedTEMP`mW03-ahg078jp`分三家公司新catalog/auto/work/registry/providerstate，旧原件用readonly roots精确register、不clone DB/整湖scan/复制PDF。新运行实际01:06:57Z开始，asof2026-10-08、CN/HK2026–28及US2027–29、7200s deadline沿cohort真实冻结。三小identity cache仅2238B同字节复制；资料32Ref/29旧SHA-bound field proof由来源owner原样转用到新publicsource-facts，不借文件名/目录或弱US sidecar推断事实。source owner内部agent独占新TEMP与coordinator记录，停写后才交3独立RF executor，ROOT不并写其记录。实际scope和run入口见[cohort](../post_w03_original_research_2026-10-11/cohort.json)。当前来源登记进行、executor未启动、0外部provider/model/新增费。

DeepSeek从实际Config.load(...,llm_provider=deepseek)读取deepseek-flash/https://api.deepseek.com/chat/completions/maxoutput8192/temperature1/max_tokens字段，凭证环境变量存在但值不记录；继续原versioned conservative pricing、母账332015tokens/250690µUSD含旧unknown+FX2764。新fresh每公司≤120k/$2，总≤360k/$6及真正累计余量；未知不自动重发。原件/config/Dayu/其他owner WIP保持；StockInfoDLSimple/v2-clean-rewrite另owner源WIP只读记录，不reset、不以HEAD冒称其dirty运行源纯净，若实际新下载消费须冻结真实runtime字节。

Next Step：SOURCE新catalog32范围真实登记/29proof复用handoff→ROOT冻结ready scope并派3fresh RF上下文→各公司四不同reviewer/专家原157问题共因复验→新三家与既有loop。P7-RF47f497ad发布/安装/CI接受；P7-AUDIT未交付保持边界。工程PASS不等于研究PASS，goal active。

## 2026-10-11T00:57:24.703695+00:00 — source09根因修复与W08来源网址集中独立接受，正常发布准备

先前normalpush真实7FAIL及原日志SHA389f0e29…保留，不绕hooks。五项pure0.7误选/邻接原断言保持：实际具体组件/用途/流程关系与明确指代的紧邻原子组替代泛经营标签，122PASS属于首次修复快照；独立审发现列表尾“等/等等/以及”通用词法遗漏，再真实RED3FAIL/2PASS→新5+原20定点25PASS/0.63s，不重跑122/public3。独立2原生负控/正控PASS，原文、locator、groups、旧策略和真实TXT全指纹保持。另两项ROOT职责测试20PASS仍有效，W04生产源码未改。最终集中[独立补充](evidence/w03-default-independent-review/FOLLOWUP.md)接受，历史BLOCKER不覆盖。

W08真正共因是shared producer丢失observed capture URL；现只在producer读取既有receipt.url或SHA+size同页original_capture_observation.url→existing publicmanifest，未知/坏URL诚实None且原件照常入库，不猜body/issuer网址/新网络验证/许可。真实两parent两issuer/publicexport/reopen/replay/retained-recovery/immutable-dedup组57PASS+唯一新测试容器误读修正定点1PASS；其联合58责任不冒称重跑58。独立发现DEL/C1遗漏，通用UnicodeCc分类再RED2FAIL/1PASS→3PASS0.39s，Ruff绿，独立原DEL微probe PASS。最终[独立補充](evidence/w08-provenance-independent-review/FOLLOWUP.md)接受。旧placeholder immutable来源不静默改写；SSE86页真实import和研究仍待。

P7-RF47f497ad主线/远端、精确CI38096229764与定点安装已接受。下一真实大节点已落实为[独立PWF](../post_w03_original_research_2026-10-11/task_plan.md)，按[W08实际入口](evidence/w08-operational-readiness-20261011.md)、[母账刷新](evidence/w08-budget-refresh-20261011.json)及不含旧答案的[W09执行卡](W09_EXECUTOR_BRIEF.md)。当前母账保守charged332015tokens/250690µUSD含7旧unknownhold，FX2764保留；未新增外部provider/model/费，不重置/双扣。

Next Step：本次源码/测试/计划与原始证据normalcommit→canonical干净ff→一次normalpush和精确新HEAD CI，当前远端仍accdeccc，不能称新CI通过。随后初始化原三家真正新scope/独立executor并四审，之后新三家泛化及既有loop；P7-AUDIT未交付源不动。goal active；原件/config/Dayu/邻仓WIP保持。

## 2026-10-11T00:39:20.165835+00:00 — 正常source09推送拦下真实7FAIL；按共因修复，不绕过

普通commit1415e314已完成9.77秒，canonical master干净ff至同HEAD；normalpush实际3137PASS/7FAIL、197.27s pytest（全203.31s），远端仍accdeccc未发布。原失败[log](phase6/main_auto_official_json/evidence/source-09-publication/normal-push.log) SHA389f0e29…及回执保留；上面的104/公共3/独立复核只证明其覆盖责任，不代替此发布节点，不能签最新CI绿。

五项default0.7纯筛选问题由内部actor独占pure policy/groups/evidence及必要旧unit，查泛经营/静态noise、具体新业务上下文，不能一律改pin/断言。ROOT另外两项已查明责任：parser版本边界原测试误依赖缺省selector完整度，用实际历史0.6明确保护其全部旧断言，新0.7的96cap/partial由公共节点实验；W04已冻结response_sha256仍decoded final，旧断言None失实，加强双SHA/原wire字节/真实final/正式output0和唯一settle，不回退诊断功能。两个文件集中实际20PASS/2.71s+Ruff绿，原件/config/W04源码SHA保持，owned+pytest重定位TEMP均清理；[回执](phase6/main_auto_official_json/evidence/source-09-test-contract-repair/green-contract20.json)。

W08只读发现官方JSON共享writer用official.invalid占位URL，而真实HTTP capture保留在extensions。下一实跑前调查公共SourceRecord/export主来源URL是否丢失；见[责任细则](phase6/main_auto_official_json/W08_PROVENANCE_CONTINUATION.md)。应在producer保留真实capture URL，缺失则诚实unknown，不猜网站、不加network检查/人工授权、不重写sealed旧来源或删原件。

Next Step：pure根因定点GREEN→一次集中影响/独立复核→正常commit/ff/push和新HEAD CI；并行W08真实母账/来源URL准备，W09研究安全输入已交。P7-RF仍47f497ad主线/远端/CI/安装接受；P7-AUDIT未交源不动。goal active、真实研究四审仍open，累计20USD/2M/旧unknown不重置，本节点0外部provider/model/费。

## 2026-10-11T00:29:43.905332+00:00 — W03集中独立验收通过，正常发布准备

W03共享责任104PASS及独立34PASS（138不重叠；另外4定点与104重叠不加），ROOT公共3PASS/55.06秒，独立只新增2组合PASS/0.185秒，261源码与配置/原件保持。审查[报告](phase6/main_auto_official_json/evidence/w03-shared-independent-review/review.md) SHA58a4323a…；真实0.7业务内容/prompt/公开原定位、实际0.6历史SQL/费用零变化、新0.7generation不命中旧pin、全TXT双指纹/96真locator成立。无阻断问题，不重复整包。完整验收见[W03](phase6/main_auto_official_json/W03_ACCEPTANCE.md)。

P7-RF已主线/远端47f497ad、精确CI38096229764绿、两根安装实际fresh业务入口验证完成。W04及pure W03已236fca08；本次正常提交共享接线/实际default0.7/公共测试/证据，再一次合master推送与新HEAD CI，不用旧CI替代。普通PWF工作文本换行统一回Git已有LF，原始evidence字节不格式化。

W08[资料盘点](phase6/main_auto_official_json/evidence/w08-readiness-20261011.md)确认32精确已有Ref（当前mFresh scope均active）、CN半年报/IPO/USHTML/HK正式presentation/融资已下载，应以所属层实际复用/读取验真，不能以旧production索引miss重下或SQL复活retired。SSE86页完整官方JSON与来源资格缺口、真实配置供应商摘要、原三家研究四审仍待；工程loopback不计真实外部供应商费。P7-AUDIT未交付保持排他边界。

Next Step：正常commit→canonical干净fast-forward→一次普通push/exact HEAD CI→W08/W09同as-of真实三家重跑。goal active，USD20/2M累计旧unknown不重置，原件/config/Dayu/邻仓WIP保留。

## 2026-10-11T00:23:29.960736+00:00 — W03共享责任及真实公共三项GREEN，独立最终复核中

共享17新+87受影响既有集中104PASS/22.88秒，7源Ruff/mypy绿；ROOT按先写好的W03_SHARED_CONTINUATION最后仅pure默认0.6→0.7，SHA64b724df…，不重标旧记录。最终public3实际3PASS/55.06pytest秒（全命令57.72秒），9源/新测试前后SHA完全相同；回执[public3](phase6/main_auto_official_json/evidence/w03-public-main-reception/green-public3-20261011T002035Z-a2218c36.json)。缺省新策略的具体行业许可变化进入rawTXT/两issuer两母页JSON实际模型prompt、generation与最终public原定位；同run resume SQL/budget不变、exact新run reuse三pin零新增POST。真正旧0.6 first公共CLI/Worker/publish→新0.7 finished history原binding/generation/SQL/费用/refs零变；新0.7另run不误命中旧pin，仅真实3缺项POST。全66324B微软TXT旧11ad9c7/newc5e4全指纹、103candidate/96selected/7omitted诚实partial，9管理层业务anchor、两saved版本逐group resolver及公开新anchorsearch/lookup96locators通过，原件与TEMP恢复。

最后existingcustom fixture声明和unknown/missing frozen真实mixed模型构造前拒绝小组已绿（与104存在重叠不相加）；共享owner只收尾自己handoff，源码已停。独立复核只查关键共因/新反例，不重复public3或整包。资料覆盖只读盘点发现部分重要原件已在mFresh隔离catalog注册，需要下一实跑固定正确catalog、复用既有bytes，不能据旧production索引miss重下；详单准备中。

仍0外部provider/model/费，不提高model400或实际预算上限，不新增审批/签收/canary。正常新HEAD并线push/exactCI尚待；旧accdeccc CI不能替这轮验收。Next Step：独立复核闭环→普通commit与一次并线push/exactCI→按W08/W09及P7-AUDIT交付边界推进真实三家四审/新三家/loop。goal active、真实研究未冒称完成。

## 2026-10-11T00:07:43.720007+00:00 — P7-RF交付正式闭环，共享版本接线实施中

P7-RF已验收、正常并主线与远端47f497ad，精确CI38096229764 success；两根安装的40实际业务CLI等验收保持原证据，不再次重跑。CWP完成的W04/纯W03责任节点已正常提交236fca0850800445bc5d89948049c38e7c80c2fb，pre-commit静态/host规则通过，21.74秒；尚未将此新提交推送，计划与共享接线大节点合并一次正常发布，当前canonical/remote仍accdeccc。公开发布不能用旧CI替新HEAD。

内部共享owner按W03_SHARED_CONTINUATION先写RED，独占factory/runtime/select/official/verify/resolver，默认仍0.6.0；ROOT保留最后0.7默认切换、一个公共mixed/旧history/reuse集中节点和正常并线push/exactCI。内部另一路只读准备最小公共节点入口，避免反复整包测试。P7-AUDIT未收到交付，源不动。原三家真实四审、新三家泛化/loop和条件八家仍open；goal active，原件/config/Dayu/邻仓WIP保留，0外部provider/model/费，USD20/2M及旧unknown不重置。

Next Step：共享责任GREEN与静态→ROOT默认切换及公共大节点/独立复核→normal发布/精确CI→原三家真实修后复验。

## 后续接收 2026-10-10T23:53:17.615142+00:00

P7-RF已正式发布/安装验收，详见[P7 RF验收](P7_RF_ACCEPTANCE.md)。W04内部责任源码stable，独立集中复核进行；W03pure责任/真实原件回放绿，显式新策略/default旧策略待ROOT冻结版本接线与大节点公共AUTO/replay/reuse测试。既有MAIN M1–M3工程发布结论不变。Next Step：提交已完成进度、W03 shared TDD接线，随后真实原三家四审和新三家。

## 状态与责任

计划已依据三卡验收与独立调查细化，共同接口已冻结，MAIN正在隔离树TDD实施。同一AUTO功能与集中工程验收已通过，已正常主线发布accdeccc且精确CI38094790883成功。只由 MAIN 持有下述 AUTO 共享写集；外包 M3-JSON/W02、M3-USAGE/W06、M3-FLOW/W07 已验收并发布，不重开同写集施工。根 PWF 由 MAIN 更新，本目录不写 `.planning/.active_plan`。

依据：[三卡验收](../m3_acceptance_2026-10-10/ACCEPTANCE.md)、[完整实施细则](IMPLEMENTATION.md)。旧 157 问题包、旧公司研究及失败记录均保留。

## 目标

官方多公司、多页 JSON 原件，经已有投影 parser → 统一有限 AUTO select/summary/verify → 发布 → 公开 read → 精确零模型调用复用。各摘要保留真正母页来源、字段定位、公司和 as-of，原语言，不翻译。旧 PDF、TXT/FMP JSON 和旧版本恢复/读取继续成立。

## 大节点

1. **接口与失败测试：completed（责任层）**。统一内部 subject/view，先写路由、角色、多发行人、多母页、generation/reuse、终态 receipt/compaction 的 RED。显式新公共版本限于旧严格 DTO 无法表达的投影；不逐 helper 创建协议。
2. **同一责任层实现及集成：completed**。已有 projection port 负责实读验真；AUTO 各层仅对自身责任负责，贯通 item 身份。复用现有 store/lease/outbox/预算，不增任务库或授权链。
3. **一次集中大节点验收与发布：completed（工程验收与normal发布/精确CI PASS）**。隔离公共 CLI import→project→AUTO→publish→read→reuse，加恢复和兼容正负控；独立审查关键不变量后正常 commit/push、精确 CI。真实供应商/公司研究另按根计划执行，工程 stub 不冒充研究。

## Next Step

W03/W04/来源URL工程正常0f7540b5发布/精确CI绿，P7-RF47f497ad主线/远端/安装接受；1152dad7来源交接进度已推送。三fresh executor按post_w03_original_research_2026-10-11/cohort运行，seal后各四独立审查→专家共因→新三家泛化/既有loop，P7-AUDIT未交源不动。

## 保留约束

- 原件、生产配置和旧 sealed 报告不改；Dayu 外部仓零改动。
- 累计 USD20 / 2M tokens，包括旧 unknown；责任测试和本地 stub 不产生供应商调用。
- 下载/模型意图沿已有授权与配置执行；不添加人工许可、签收或 canary。
- 测试仅 owned TEMP，结束恢复原样；不做完整资料湖恢复演练。
- 不重复嵌入整页 JSON 或 projection records 到 request/event/binding；空间增长只来自小描述、精选片段和必要回执。

## P7外包边界（2026-10-10）

[三卡总入口](../p7_parallel_handoff_2026-10-10/README.md)用户已发出；CWP source已独立验收合隔离树，其余RF/AUDIT外部施工中。MAIN禁止并行修改 source_catalog/official_json_projection.py/new official_json_snapshot.py；该确定性/深快照/旧回放叶责任归P7-CWP-PROJECTION。MAIN先按原1.0.1默认API接线，最终选opt-in1.0.2。RF校准/audit技能也独占外包，MAIN仅最后跨仓集成/版本安装。MAIN的AUTO统一subject/view/store/generation/transport/CLI和责任tests不交叉。无需等待三卡才能写MAIN RED；外包完成后在一个大节点验收接线。

## W04/W03后续源码节点 2026-10-11T00:03:32.361246+00:00

W04 source+独立6probe已接受；W03 pure source/实际原件回放已接受，default0.6保留。共享接线按[W03_SHARED_CONTINUATION](W03_SHARED_CONTINUATION.md)TDD实施，由ROOT最后切默认与一次公开集中大节点。当前源码责任节点先normalcommit归档，不冒称全部AUTO/真实研究完成。
