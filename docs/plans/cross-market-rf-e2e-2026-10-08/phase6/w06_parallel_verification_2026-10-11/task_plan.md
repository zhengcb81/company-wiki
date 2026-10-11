## ROOT 当前入口 — 2026-10-11

当前状态、已发布SHA与下一步统一见 [ROOT接收状态](ROOT-reception-status.md)，优先于本文旧状态。
OCR/RF/Audit/Portability已并线发布，精确CI成功。W04质量带375工程绿、同六原件87.4409秒PASS，非作者17/17及四事实见证通过；18文件集成清单READY，ROOT待正常并线。ET/FF坏stdout覆盖已测用量共因已修并提交分支ETd0ac42c6/FF2d380a05，集中独审7PASS，尚未发布；原41最新1PASS/27PARTIAL/13NOT_RUN、184.54秒触及180秒截止，未认证。W07三包已实际准备（READY_NOT_STARTED）：FF固定41提速、RF组合测试、Audit买方风险诊断，ROOT保留W04/G2/G4/G5与主线安装；G2/G4/G5仍开放，目标active，0付费调用，无新增人工许可。
W07：[三包总览及实际工作目录](../w07_parallel_quality_2026-10-11/README.md)。三包可同时启动；各自只有A/B/C三个测试大节点，不增加小节点门禁。


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

# W06：三个独立施工包

## 目标与当前状态

建设数字口径审查能力和两套可复现的离线验收工具；不与 ROOT 或正在施工的 W05 抢文件。三条线无相互完成依赖。**工作树、固定输入准备好后才发布 READY；以 workspace-receipt.json 为准。** 主目标继续 active，不把本包完成当成真实公司预测通过。

W05-CWP-OCR、W05-RF-FLOW、W05-AUDIT-LOOP 均已观察到本线 PWF，Audit 已有产品 WIP，不能重新分派。它们的代码/测试、ROOT 的 selector/预算/LLM 配置/跨仓适配均排除在 W06 写集之外。

| 包 | 工作 | 固定起点 | 排他工作目录 | 卡片 |
|---|---|---|---|---|
| W06-AUDIT-MEASURES | 数字、单位、币种、存量/流量与算式口径审查工具 | Audit c0993332623637d53f059350a382d99a95ef731d | C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures | [施工卡](cards/W06-AUDIT-MEASURES.md) |
| W06-FF-MATRIX | 真 FF→ET→CWP 代码的离线联调与文档类型覆盖套件 | FF 08ec85b27133cdf8a8d3b38fdba15255fc1ebac2 | C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix | [施工卡](cards/W06-FF-MATRIX.md) |
| W06-CWP-PORTABILITY | 虚拟存储根迁移、重复原件和引用稳定性回归工具 | CWP 01ea86a37edb5506d6269b6e10d9cb56a1270efd | C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-portability | [施工卡](cards/W06-CWP-PORTABILITY.md) |

## 价值与范围

Audit 的既有 numeric_audit 只复算显式 scale/FX conversion，明确没有验证经济定义。新包在已有转换工具上增加显式 typed observation 与关系诊断，不代替四路独立审查。

FF 已有 ET/CWP producer goldens、transport 和隔离 wiki 测试；新包补的是一次连通真实三层实现的离线链及完整文档类型矩阵，不能复制旧金样检查宣称新增全链。

CWP 已有 N5-DOCSET 的真实内容质量基准，W06 不重做该包。这里验证“根目录换位置，上层仍按引用读原文”的存储抽象，不改 parser/selector/OCR，不扫描真实数据湖。

后两包允许工具正确、产品反例仍失败的 PARTIAL 交付：固定期望、封存失败，ROOT 修共用实现。禁止把产品缺陷变成 skip、expected failure 或放宽标准换绿。

## 接口和主线职责

所有包引用 [交接接口](handoff_contract.md) 和本线 input/inputs.json。没有跨仓可变数据库、额外权限/许可/人工签收；一次交付大节点由 ROOT 验收、集成、接入技能/选择快速 CI 范围、安装与推主线。各 harness 不自行安装、不改总 PWF、不改生产配置或母账，不 push 主线。

W06 默认 0 HTTP/下载/LLM/收费；ET 的 FMP 响应是明确 synthetic transport fixture，不能使用真实密钥。费用母账仍 413778 tokens /334463µUSD + FX2764µUSD hold，累计上限 $20/200万 tokens，不另开户。

## 阶段

- [x] 对照现有源码、旧包和 W05 实际 WIP，冻结排他写集。
- [x] 创建三个独立小工作树，固定 code/input SHA 与入口，生成 READY 收据。
- [ ] 各线：真正行为 RED → 实现及集中单元/集成 → 独立 scratch E2E 和正常 commit。
- [ ] ROOT 交付时一次验收接口；产品共因由 ROOT 修，再重放原失败向量。
- [ ] 接入已有 G2/G4/G5，不把这些免费工程工具升级成每 commit 的多分钟全链门。

## Next Step

固定输入和工作树已 READY，可立即分派；ROOT 继续统一阶段判定和语义预算召回修复。当前六份原件回放只证明原 SHA、hard cap 与 0.7.1 指纹；实际年报强业务候选仍落选，独立公开 0.8 probe 也发现旧候选路径绕过否定/条件判断，源码尚不能发布。

ROOT接口补充另发而未覆盖12原输入；最终18输入SHA/三卡同字节/三树仅docs/handoffs输入WIP/相对链接/两生产配置指纹均通过。未来实现和E2E未跑，未以准备PASS代工程质量。
