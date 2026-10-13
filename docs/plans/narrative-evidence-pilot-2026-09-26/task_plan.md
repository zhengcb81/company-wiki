## ROOT最新入口 — 2026-10-13 DU2候选模块接收

[文档理解升级最新签收](../document-understanding-2026-10-13/du2-reception/acceptance.md)：1135联合PASS、4PDF658证据span验真、同源10Q6项PASS；原件/配置/测试环境保持。三最新作者提交与ROOT共用根因修复已并 master 并推送deb7eb7d，精确CI 38476678472 success；详情见子计划publication.json。没有启用生产默认LLM摘要或签G2/G4/G5。优先继续B8旧selector硬编码/价值预算→B10–11正式消费与局部缓存→C12–15真实模型和原/新公司审查；无新许可/canary链。下方旧并线计数为历史。

## 文档理解升级并线状态 — 2026-10-13

[文档理解升级（du-input/route/structure/packages）](../document-understanding-2026-10-13/README.md)
三包已实现并合并到 `codex/du-root-integration-20261013`，跨层验收 420 tests 通过（含真实原件节点），
原件 0 复制 0 修改、0 模型调用、0 费用；**尚未接入生产解析链**。母计划的 W04、G2、G4、G5
保持开放，本计划不替代也不签收它们。生产切换与真实模型大节点按母计划 G4/G5 另行执行。
下面内容为原有记录，按原字节保留。

## ROOT 当前入口 — 2026-10-11

当前状态、已发布SHA与下一步统一见 [ROOT接收状态](../cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/ROOT-reception-status.md)，优先于本文旧状态。
OCR/RF/Audit/Portability已并线发布，精确CI成功。W04质量带375工程绿、同六原件87.4409秒PASS，非作者17/17及四事实见证通过；18文件集成清单READY，ROOT待正常并线。ET/FF坏stdout覆盖已测用量共因已修并提交分支ETd0ac42c6/FF2d380a05，集中独审7PASS，尚未发布；原41最新1PASS/27PARTIAL/13NOT_RUN、184.54秒触及180秒截止，未认证。W07三包已实际准备（READY_NOT_STARTED）：FF固定41提速、RF组合测试、Audit买方风险诊断，ROOT保留W04/G2/G4/G5与主线安装；G2/G4/G5仍开放，目标active，0付费调用，无新增人工许可。
W07：[三包总览及实际工作目录](../cross-market-rf-e2e-2026-10-08/phase6/w07_parallel_quality_2026-10-11/README.md)。三包可同时启动；各自只有A/B/C三个测试大节点，不增加小节点门禁。


## ROOT 当前状态 — OCR 已本地并线 / 两张 W06 接收修复 — 2026-10-11

- **W05-CWP-OCR：资源与来源大节点验收通过，已正常并入本地主线 ae0ca0d3。** ROI 先计算整数几何、预扣预算，再分配图像和推理；原生进程统一截止与清理。最终54项集中、34项非作者探针、现有快测148项通过；同一微软原件真实两阶段83.006秒（37.706/44.104，原85/90秒限额），22旧行完全一致，两条定义恢复，fresh locator 回开通过。原85秒FAIL、后续88.83秒PASS均保留。POSIX仅静态审查，未测峰值RSS，不能宣称全部OCR召回或研究质量已验收。此次提交后正常推送；精确远端/CI记录另行写入 publication.json。
- **W06-AUDIT-MEASURES：已完成。** Audit main9cd5ff8a，296项大节点、最终77项及独立反例通过；两份技能各26文件MATCH，原件/配置/输出未动。Audit仓无remote。算术检查不认证来源真值。
- **W05-RF-FLOW：最终 typed ancestry 修复已冻结，待非作者复核。** 原标签洗成年度收入的stock/rate/scalar问题按共用数学类型与时间阶数修复；现有唯一工程节点376+36 subtests通过，两个native冻结输入的5份产物完整字节一致。尚未主线并入或安装；他人assurance/output WIP保留。
- **W06-FF-MATRIX：已交付，接收发现工具误判与隔离问题，正在独立ROOT树修复。** 旧12项绿不覆盖错误季度、重复下载、未知用量、SourceRef缺失、环境/清理归属及绝对截止；11项非作者探针10FAIL。测试工具问题不冒充生产缺陷。
- **W06-CWP-PORTABILITY：已交付，非作者接收中。** 当前真实Reader合成移根/原字节/篡改/版本回开等流程通过；工具会清理已有固定目录、改写export证据、刷新输入ref等问题仍需修复，不能据原worker全绿并线。仅修本卡工具与测试，不扩展生产权限或许可。

本批次未调用provider/LLM、无新费用，原件与生产配置未变。母PWF的W04、G2、G4、G5仍开放。下一步先完成RF/W06各自大节点验收与正常并线，再返回统一候选覆盖及真实公司重跑。下面旧记录是历史，不作当前完成声明。

## ROOT 当前状态 — W06 accepted / W05 resource finalization — 2026-10-11

- **W06-AUDIT-MEASURES：完成。** 原交付6a50d7e在最新W05 audit main上整合并修复共因；main正常合并至9cd5ff8a2c8f9c1726c4047785164e3263673614，clean。296项大节点测试、最终77项及独立19+8+4探针通过；两份技能各26文件MATCH，仅5个包文件/份及manifest更新。Audit无remote。验收限声明的类型与算术，不能替代来源真值与经济模型审查。
- **W05-CWP-OCR：最终资源收尾中，尚未并线。** 原85秒失败来自重复stdin监听与Windows CRT锁互阻，保留原FAIL；去掉冗余监听后22项集中通过、有效50ms产品硬截止通过；同一微软原件真实初次处理及独立回开总88.83秒（阶段各在原85/90秒上限），两定义恢复、22旧行完全一致。独审另发现ROI在PIL放大/拼接后才验像素，ROOT正在统一整数几何预检和预扣，禁止把native推理前已计预算误说成分配前也已计。
- **W05-RF-FLOW：修复集中工程节点通过，尚待最终独审与并线。** 唯一现有pre-push节点356+36 subtests通过（33.20秒），可移植兼容/3.9节点52+7通过，隔离native CLI和三仓显式根集成通过。原FAIL与他人assurance/output WIP保留；不凭解释文字放宽时间窗口或重复贡献，不新增许可门。

本批次没有供应商/LLM调用或新费用，原件与生产配置未改。下面旧状态只作历史；母PWF的W04、G2、G4、G5仍未全部完成，不能写整体完工。下一步：OCR分配前硬预算修复集中测试及真实E2E，RF非作者复核；达标后正常commit/merge/install/push，再返回母计划。

W06精确证据：phase6/w06_parallel_verification_2026-10-11/evidence/root-audit-measures-acceptance/publication.json 与 independent/final-review.md；隔离ROOT接收计划为 .planning/w06-audit-measures-reception/。

## ROOT 接收状态：三交付已盘点、隔离修复中（2026-10-11）

W05-AUDIT-LOOP 已并 main321d4c1、两技能同步，旧结论保持。新三交付均已核 Git/manifest；“worker 完成”仍需 ROOT 验证事实范围，不扩展人工许可。

| 线 | 已核事实 | 当前动作 |
|---|---|---|
| W05-CWP-OCR | 32项SHA/字节匹配；最终184PASS/66.32s、ruff绿、原6反例及有效50ms startup截止绿；真实PPTX首次原图推理85.047s触deadline FAIL | 保留 original-fail 日志/result/receipt；先定位隔离 native 初始化/推理性能根因，不加85/90s上限；未发布 |
| W05-RF-FLOW | 87项匹配、120 tests+33 subtests绿；3个期间语义P1穿透强输出读者；C1 CNY/USD标签、8 ignored产物须纠正；compatibility实为已tracked稀疏排除 | 独立 rf-flow-root 接原提交，正式RED→共用期间语义/依赖顺序修复，未并线或安装 |
| W06-AUDIT-MEASURES | 23项匹配、40+7绿；19冻结反例11假PASS/5结构异常，真实CLI复现 | 独立 audit-measures-root 基于已接W05 main321d，正式RED→typed操作/未知传播/容差/输入边界修复，未并线或安装 |

原交付树不改；ROOT在三个排他树整合，最终集中测试/独审后正常提交并线。只读原件/生产配置SHA保持；测试scratch恢复；本轮0 HTTP/provider/LLM/token/费用。累计413778 tokens /334463µUSD +FX2764 hold保持。Dayu/IQS、其他owner WIP不动。W04阶段/预算召回缺口及G2/G4/G5真实公司质量尚未完成；不能以本次工程绿签收经济结论。

## Next Step

OCR先分段查 native 性能，不凭重跑或提高预算换绿；RF/Audit共因修复在独立树并行，正式失败证据不删除，ROOT负责最终接线、发布、技能定点同步。W06另两卡保留原owner，未交付不重新派工。选定接收计划为 .planning/w05-cwp-ocr-reception、.planning/w05-rf-flow-reception、.planning/w06-audit-measures-reception；母PWF沿用本文状态，历史字节如下保留。

## W05-AUDIT-LOOP 最终收尾（2026-10-11）

Audit main321d4c1及两套技能已接收；CWP源码8d281af1的精确CI38132897880 success。收尾资料98ef925a已正常推送，实际范围为no behavior changes，137PASS/28.94s，验证.planning修复后不再误触发全Unit。初始in_progress与最终CI成功分文件保留。原件/配置不变、项目费用增量0；W04语义缺口及G2/G4/G5仍未完成。

## Next Step

本接收包已完成；ROOT回到母PWF的W04共因修复。其他W05/W06保留原owner，禁止重跑本次一次性封存/补丁脚本。

以下为历史记录。

## W05-AUDIT-LOOP ROOT 已接收（2026-10-11）

Audit `codex/w05-audit-loop` 的 `7a5d4b8`、`2ed0b5e` 已接收；ROOT封存原FAIL并按共因修复，正常快进 main `321d4c165575e81add3b4aa1ee9ba0a047ca6082`。两套物理技能目录 .claude/.agents 各24文件SHA MATCH，只同步本技能4差异文件/套与manifest，其他文件保留。Audit无remote，未创建远端。

24项原交接验真、19新增RED→GREEN、全220PASS、48步隔离E2E PASS（86.696s）、独立原6纯/2tmp反例复验PASS_WITH_SCOPE；scratch恢复absent，0项目HTTP/LLM/token/费用。实际源码/安装/独审与失败记录见[接收报告](../cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-audit-loop-acceptance/acceptance.md)。这是循环进度/恢复工具验收，不是三家真实预测质量通过。

W05-CWP-OCR、W05-RF-FLOW继续原owner；W06三卡READY各自排他，不能重派在施工卡。ROOT W04阶段判断/预算召回独审仍FAIL，保留原3P1/2P2及实证，不发布有缺陷selector；G2真实摘要消费、G4原公司独审和G5新公司/池loop未完成。原件、生产配置、活动累计账、其他owner WIP、Dayu/IQS均未改。既有母账413778tokens/334463µUSD+FX2764保持；本轮增量0。

CWP接收资料commit c9dd5124尚未远端发布时，发现`.planning`与`docs/plans`分类不一致导致资料误触发全量Unit/CI；原失败保留，5RED→58GREEN并正常提交8d281af1，正常钩子全范围PASS（====================== 3240 passed in 302.47s (0:05:02) =======================）、远端8d281af1已实读验真。纯资料以后走已有小smoke/CI路径忽略；运行源码、配置、未知路径仍检查。独立临时根已恢复absent。ROOT旧集成树的3个原干净门禁文件已核baseline blob后定点同步，其他W04 WIP不动。

## Next Step

本次CWP接收/分类修复已发布；ROOT继续修W04共用阶段/预算召回，原件回放和大节点独审通过后才推进G2→G4→G5。接收已完成的其他施工卡按真实交接逐项并线，不增加小节点签收。

以下为历史记录；原字节保留。

# 公司来源平台：唯一当前施工入口

**2026-10-08｜全部PWF约定内容完成。** R3正式生产、语义、跨仓消费、恢复、空间、清理均通过；[完整要求对账](r5_full_closeout_2026-10-08.md)覆盖全部计划家族。模型累计上限220000 tokens/$10，旧费用与unknown保留；无需再批准。完成检查点34141d3d已正常推送、实际远端HEAD相等/CWP干净；本次仅发布最终状态。

## Goal与边界

完成全部PWF及引用实施细则的约定内容，不用试点或缩小范围代替完成。原件/来源版本/历史usage不丢。CWP供应来源、精选业务描述、原语言摘要和可回放证据；投资研究语义属于StockWiki。上层使用SourceRef/SourceExport v2/NarrativeRef，目录归存储层。一套AUTO/lease/generation/outbox；解析与模型各自有界，不启永久全文PDF→MD或无限worker。

MAIN负责共享接口/生产/总PWF/并线。Dayu零代码修改，IQS独立项目不写；其他owner WIP不回退、不混入提交。CN维护StockInfoDLSimple的v2-clean-rewrite，不维护旧StockInfoDownloader main。人工review/许可/签收/canary不恢复；保留真实SHA、来源身份/期间、历史公开时点、版本、写入归属与资源正确性。只在大节点测试，测试副本恢复，不加每helper审查或每commit长pytest。

## 全部阶段

| 阶段 | 状态 | 权威证据与范围 |
|---|---|---|
| S0–S2/N4并发恢复 | complete | [完成证据](main_completion_evidence_2026-10-06.md)、[N4细则](n4_production_batch_implementation.md)：同AUTO、隔离子进程、lease/generation/outbox、预算、kill/ACK恢复 |
| S3来源虚拟化 | complete | SourceRef/Export v2、FF→ET→CWP、迁根/真实读取。目录不进入消费DTO；不等同完整预测算法 |
| S4/N4C/R6摘要能力 | complete | 四类真实模型、[run10](harness_lanes/results/n4c_live_business_review_2026-10-06.json)、[R6](harness_lanes/results/r6_partial_summary_node_2026-10-06.json)；现另有R3正式生产证据 |
| S5/S6旧派生/数据库 | complete | [生产收据](harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json)：净释放5659443210B、原件0删除、DB3055841280→222408704B |
| S7九类质量 | complete（约定有界范围） | [质量节点](harness_lanes/results/s7_adoption_fundraising_main_acceptance_2026-10-07.json)：29/33 required、761回放、四miss/optional/重复6保留；不改golden |
| G1/G2门禁补漏 | complete | [G2最终验收](g2_consolidated_node_2026-10-08.md)：十四组/A-B、真实安装/重复0写、签收/canary及旧入口退休 |
| G2–G5/早期外包 | complete | [G5](g5_main_acceptance_2026-10-07.md)、[G4](g4_main_acceptance_2026-10-07.md)、[G3](g3_main_acceptance_2026-10-07.md)；约定交付已验收并线，不重派 |
| R0/R1完整核查/融资分类 | complete | [完整实施单](all_pwf_completion_implementation_2026-10-07.md)、原设计/16要求和102项历史目录继任对账 |
| R2正式来源事实/TXT | complete | [细则](r2_source_preparation_implementation_2026-10-08.md)：四restore、九facts、TXT66324B+589B，重复0新增，精确源码CI绿 |
| R3正式生产与当前消费 | complete | [正式验收](r3_production_acceptance_2026-10-08.md)：2 visible、1模型POST、20claims/49证据、三仓公共CLI、制度0模型、同run新增0、空间588030B、原件保护 |
| R4可选原件对象化 | complete：证据决定不迁移 | [G3事实](../../implementation/g3-source-facts/MAIN_ACCEPTANCE.md)：实读extra34.5MiB、allocation未知；不为小收益迁引用或删原件 |
| R5导航/清理/完整发布 | complete：实质审计与正常发布完成 | [最终对账](r5_full_closeout_2026-10-08.md)、[R5细则](r5_cleanup_and_navigation_implementation_2026-10-08.md)；全部家族已核，[发布检查点](harness_lanes/results/r5b_publication_checkpoint_2026-10-08.json)已验证远端/CWP干净 |

## 最新生产事实与预算

既有Config.load DeepSeek Flash/8192/温度1/default thinking/timeout60保持，MiMo mimo-v2.6-flash既有配置保持。本次英文电话会9499tokens/估算10235microUSD，真制度0模型；总199534tokens/110737microUSD，历史unknown7/unsettled0、FX2764照计。当前余20466tokens/$9.886499（代理估算，不是供应商账单）。[授权](harness_lanes/results/r3_budget_approval_2026-10-08.json)、[实账](harness_lanes/results/r3_production_live_batch_2026-10-08.json)。不因额度扩大而换配置、清账或启动全库处理。

当前普通资料使用显式as_of_date:null，未知公开日/采集时间/登记语言保持未知；派生检测语言单列。历史ISO仍检查公开日，不让current读取自动变成预测资格。所有来源/工件SHA和49定位验证。正式AUTO=.source_catalog/automation.sqlite3，work=.source_catalog/r3；成功final为正式资料，保留。一份106792B英文业务工件+1457B制度skip，整个库逻辑新增588030B，scratch峰106792B，终态work/log仅212B。重复同request/run没有新模型/attempt/费用或对象。

CWP源码6cd9b6d/CI37736338454，RF源码343e2de及依赖pin7cf337e/CI37737193724，SW源码1ebe012，独立交接后6d1dddb consumer源码相同，无remote。正常提交/push门均绿；不重复已完成端到端或付费生成。

## Next Step

无必要施工剩余。原PWF及全部引用约定内容完成；[完整最终对账](r5_full_closeout_2026-10-08.md)、[正常发布检查点](harness_lanes/results/r5b_publication_checkpoint_2026-10-08.json)为交接入口。仅提交此完成状态后核最终远端并关闭原目标，不再启动模型/无限worker或新外包。未来新增需求另立具体任务，原件/final/AUTO/旧usage和独立owner资料保留。

## 导航

2026-10-08新增的三市场真实RF审计与固定回归不重开原历史目标；当前工程入口是[三市场PWF](../cross-market-rf-e2e-2026-10-08/task_plan.md)、[71检查点回归套件](../../../benchmarks/cross_market_rf/README.md)、[新检出确定性缺陷与后续施工](../cross-market-rf-e2e-2026-10-08/follow_up_plan.md)。固定套件已交付，当前基线保留真实FAIL/BLOCKED，不将原计划签收等同于所有线上能力全绿。

[实施单](all_pwf_completion_implementation_2026-10-07.md)、[最终对账](r5_full_closeout_2026-10-08.md)、[findings](findings.md)、[progress](progress.md)、[README](README.md)。旧120卡顶部指向本入口；旧paused/待签收/旧预算仅历史。原完整日志固定在已推[6dd5601](https://github.com/zhengcb81/company-wiki/tree/6dd56011a7d49e2b8c147f2163b0708074f9edd7/docs/plans/narrative-evidence-pilot-2026-09-26)，不复制大归档。
