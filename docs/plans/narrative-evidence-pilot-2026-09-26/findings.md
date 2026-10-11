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

# Findings：当前事实与证明范围

**2026-10-08｜R3生产与R5完整审计/发布完成。** 当前状态取[task_plan](task_plan.md)；历史完整调查在[6dd5601](https://github.com/zhengcb81/company-wiki/blob/6dd56011a7d49e2b8c147f2163b0708074f9edd7/docs/plans/narrative-evidence-pilot-2026-09-26/findings.md)。

## 架构与精简

来源层负责raw/版本/SHA/locator/质量，消费者通过pathless SourceRef/Export v2/NarrativeRef读来源，不操作底层目录。CWP不保存投资研究state；RF/StockWiki各负责自己的语义。一套AUTO、独立模型子进程、有界多文档P4，不重造reader/队列。G2十四组及A/B全发布：人工许可、review receipt、签收、private/public、canary、固定SHA人工许可表退出；保留真实SHA/身份/期间/历史公开日/locator、路径归属、事务与资源限制。[完整对账](r5_full_closeout_2026-10-08.md)。

## R3真实生产

既定正式请求r3-20261008-production-deepseek-01成功：微软原语言TXT106792B final、真制度1457B skip，只有1实际DeepSeek POST；20claims、49原文证据、16管理层/4分析师问题、13actual/3forecast/4question。所有claim逐条受引用支持；六个重点经营主题均在短摘要，仍非全文穷尽质量声明。原件provenance legacy_unverified和未知公开日期没有被伪造。[生产](r3_production_acceptance_2026-10-08.md)、[语义](harness_lanes/results/r3_production_semantic_review_2026-10-08.json)。

真实CLI首次暴露nullable采集时间、登记语言被误当身份冲突。三个读取层现保持未知原登记值和独立派生语言，不依靠新开关或来源白名单。有值错误/已知冲突仍拒绝；显式null当前阅读与ISO历史公开日规则分开。三仓公共read/list/search/exact、49定位、同证据DTO与制度skip都通过，历史unknown均拒绝。同run恢复6任务终态、0新attempt/POST/token/费用、相同工件/hash。[总收据](harness_lanes/results/r3_production_acceptance_2026-10-08.json)。

累计199534tokens/估算110737microUSD；220000/$10已授权，余20466tokens/9886499microUSD（扣旧FX2764），历史unknown7不退。既有DeepSeek/MiMo配置、价格与资料范围不变，现金账单未知。不会为消费重跑付费摘要。

## 空间与归属

历史S5/S6生产净释放5659443210B、raw0、DB222408704B。新R3主DB不增，仅WAL+57680B、AUTO389120B/SHM32768B、两个final108249B、work212B及锁1B，共588030逻辑B；CLI内部报588029B，差1B为owner lock。scratch峰106792B。当前每final2MiB/持久1GiB/scratch2GiB均通过，实际allocated未知。[测量](harness_lanes/results/r3_production_space_protection_2026-10-08.json)。

R5A清8根119913476B；R3A清工作树91161217B；本次R3清自己2工作树+16文件94840547B。三项是测试/代码副本，单列不重复加到旧生产净释放。26原件/config/侧录/历史pilot SHA保持，formal AUTO/成功final与未知费用历史保留。邻仓owner只能检查归属不覆盖：StockWiki独立交接提交753dfca/6d1dddb并清自己runs；旧342基线不能再宣称全未变。我们的四消费者提交只改接口/测试，与owner不重叠。SID/SQA等独立WIP保留，Dayu/IQS0写。

## 有意保留的边界

S7九原件仍29/33/761定位零错、optional2/17、重复6。四miss是纯金额、另页canonical产能定位、正文外provider、纯guidance，原golden/分母保留；不称33/33。R4实读重复extra34.5MiB/allocation未知，证据决定不对象化。FMP真实402只证明当前套餐限制；Koyfin/SeekingAlpha调查不等于自动化provider或购买。P4计算3/模型1，不称实测四模型并发；Windows POSIX skip不计通过。原scope是有界来源平台能力，不是全历史已处理或投资研究自动化。

## 发布

CWP6cd9b6d精确CI37736338454全success；RF7cf337e依赖当前producer、精确CI37737193724全success；实际消费测试343e2de源码与7cf相同。SW1ebe012被独立6d1dddb推进，consumer源码逐字相同，无远端。[八仓只读状态](harness_lanes/results/r5b_final_repository_state_2026-10-08.json)。最终文档检查点34141d3d已推送、实际远端相等、CWP干净，最终状态提交复用这些源码绿；关闭原目标。
