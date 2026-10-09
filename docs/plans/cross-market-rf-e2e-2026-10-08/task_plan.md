# 三市场真实收入预测端到端审计

## 目标与边界

按用户 2026-10-08 的新请求，选择 3 家公司覆盖 US/HK/CN，由三个独立执行 agent 使用 revenue-forecast 完成真实全流程，再由独立审查 agent 逐家公司审查。覆盖至少一次既有原件复用和一次真实新下载。执行、审查结论分别留存，不用 fixture、虚构日期/数据或删减流程冒充成功。

本目录是独立新任务，不重写已完成的 narrative-evidence-pilot 历史计划。MAIN 独占三个共享 PWF 文档；各 agent 只写指定公司子目录。CWP 只留来源与工程验收记录；研究性预测成品先放独立 TEMP，签收后交付RF output，不成为 CWP canonical 研究状态。原件保留；Dayu 代码零修改，邻仓 owner WIP 不动。

## 阶段

### Phase 1: 版本、配置、资料盘点与公司选择
**Status:** complete

核对实际安装与仓库入口、只读目录、原件身份/期间/公开日，冻结 as-of=2026-10-08。记录缺失，不假定本地有文件就可被历史预测使用。明确新下载和复用公司。

### Phase 2: 三执行 agent 并行运行
**Status:** complete

按 common_execution_contract.md，各自记录全部命令、输出、原文 SHA、来源定位和技能 0–11 步。先走 RF source_preparation→FF→CWP，再建模、lint、hash、正式校验、计算、快照。实际结果未知的未来期间只冻结，不伪造回测。

### Phase 3: 独立逐公司审查与修复
**Status:** complete

执行 agent 不得签收自己。独立审查读取每条命令与产物，重新打开每条事实引用，复算所有金额/单位/期间/情景/桥接/敏感性，检查所有技能步骤、CWP 资料与虚拟接口、FF 和市场 provider。发现问题由 MAIN 分派原执行 agent 修正，再独立复查。细节全量审查只用于本轮用户指定大节点，不增加日常小节点门禁。

### Phase 4: 跨公司归总、清理与发布记录
**Status:** complete

汇总实际通过、未通过、不可用的来源；区分代码缺陷、配置/安装漂移、供应商限制、原件元数据和预测经济假设。检查原件不丢、独立测试目录恢复、临时输出大小、费用与 Git diff。必要修复先 TDD，定点责任层测试，不篡改测试成功标准。只提交本任务文档/必要修复，不混入其他 owner 内容。

## 完成标准

- 3 家（每市场 1 家），3 独立执行身份，独立审查覆盖每家公司。
- 至少一次真实 reuse、一次缺失原件经正确 provider 下载→CWP 入库→复用再验证。
- 每个事实/参数有打开过的原文定位、SHA、日期和单位；不能证明的内容列 gap。
- 每家公司技能步骤 0–11 均有事实证据或不可适用理由；必须真实运行正式 forecast validator/engine，不能只有手写数字。
- 所有缺陷和限制如实报告；不承诺预测一定正确。未来真实业绩尚未发布时不得伪造 out-of-sample 回测。

## Next Step

**当前行动（2026-10-08 Phase6）**：R6三卡责任验收、主线合并/推送/代码CI和RF安装闭包完成；最终整链43PASS/1FAIL/2BLOCKED/18NOT_RUN/7NA，HK旧语义待新研究、全图PPTX正文未实现，原件/环境保护通过。下一MAIN先[provider失败证明边界](phase6/r6_provider_cause_integration.md)和RF真实NarrativeRef输入消费，再跨run内容复用/图片能力与两组三市场真实新研究独立审查。详见[查收记录](phase6/r6_handoff_intake.md)，不要重派R6或恢复已关闭门禁。

### Phase 5: 固化三市场回归套件（2026-10-08 新请求）
**Status:** complete

施工细则见 regression_suite_plan.md。先写失败分类、样本验真、隔离清理、比较和语义回归测试，再实现命令入口。固定 CN v3 / HK v4 / US v2，不改已封存审查。离线真实原件重放与在线供应商联调分别计分；旧产品 PARTIAL 不改成全绿。大节点验收为：小测试 → 三公司重放及跨仓契约 → 重跑比较/故障清理。日常 CI 不增加真实下载或收费模型。

已交付 `benchmarks/cross_market_rf/README.md` 一命令入口、71检查点、固定来源/输入SHA、隔离 registry/catalog/AUTO/work/profile、真实RF/FF/ET/Worker流程、前后比较、可搬移去重数据包和完整新研究大节点施工卡。16小测试绿；full真原件重放92.555秒；脱离生产库的数据包重放90.309秒，71状态相同。在线CN半年报真实新下载→验字节→再次0下载→RF读取通过。临时环境均恢复，导出样本副本签收后删除。

**当前基线不是产品全绿**：46 PASS / 3 BLOCKED / 1 FAIL / 14 NOT_RUN / 7 NOT_APPLICABLE。US跨进程置信度验证缺陷已真实复现，优先放入follow_up_plan.md；HK官方认证、HTML/PPTX处理和在线Dayu/ET仍具名留存。固定输入/loopback不能证明新一轮研究、真实供应商或新摘要实际被模型消费。

本轮审计任务完成。CN v3、HK v4、US v2最终独立复查已封存：条件模型可接受，三公司产品E2E均PARTIAL。原件/旧快照保护、RF交付归档、237文件TEMP清理、359命令账核对及本仓主线发布完成；c72d532b远端CI成功。完整归总见acceptance_summary.md。尚未实施的Dayu bounded、ET套餐/路由、HTML Worker等是后续功能施工，按follow_up_plan.md推进，不能把审计完成说成完整产品全绿。

## 问题记录

- CodeGraph context 读取遇自动审批超时；不是代码错误。已尝试结构工具，后续对已知具体 CLI 文件使用文件阅读。
- 邻仓 git 默认沙箱拒绝读取，已通过授权外的正常 OS 只读执行取得版本。
- 猜测 `scripts/source_catalog.py` 不存在；需查实际入口，禁止复用错误命令。

Phase 5发布：`71fec1554abf1b0fc6350da28589593b8e345adb`已推主线；[远端CI](https://github.com/zhengcb81/company-wiki/actions/runs/37765260153)成功（88秒）。固定产品基线仍46PASS/3BLOCKED/1FAIL/14NOT_RUN/7NOT_APPLICABLE；后续按follow_up_plan实施，不用CI绿色替代产品检查点。

## 根因修复阶段（用户补充要求）

实施约束与责任分组见 [root_cause_remediation.md](root_cause_remediation.md)。每个原问题关联共用责任组，保留已证实机制/待证假设/原漏检原因；先RED责任测试，再共用层改造，最后一个集中大节点验收。不得以公司特判、固定seed、删失败检查、虚构日期或放宽关键语义校验完成修复。

下一步：P0 RF跨进程确定性，先建立多seed和多数量级权重的最小失败复现，确定旧快照兼容策略，再改稳定归约；当前仅完成根因施工计划更新，产品缺陷仍未关闭。

## 最终泛化验收（用户新增）

全部改造完成后执行 [second_cohort_generalization.md](second_cohort_generalization.md)：新选A/H/US三家公司，覆盖本地复用与真实新下载、完整RF流程和独立审查。执行前固定样本/版本/事实基准，失败不换公司；保留第一组回归。两组不同样本分别比较，新增问题回责任层并重跑两组，不增加小节点审批。当前仅安排最终节点，尚未执行第二组。

2026-10-08 目标扩展：第二组验收后仍须归纳共性新问题加入本 PWF 并继续实施，再按同一方式复验，直到符合 CWP/FF/RF 的设计职责与功能要求。外部账户/供应商限制单列，不制造公司特判或更换失败样本掩盖问题；每轮只在大节点审查与真实 E2E，不新增小节点门禁。

## Phase 6：全部根因改造与两组验收

**Status:** in_progress

用户明确要求持续实施直到完成。顺序：P0 RF稳定计算 → CWP-owned Dayu有界桥及来源资格 → FF/ET能力和费用路由 → HTML/PPTX规范化 → RF目标/输入证据/摘要实际消费 → 原三公司完整回归 → 新三公司独立执行与审查。只读结构探索可并行，代码改动按责任层隔离；原件及邻仓owner WIP不动。Next Step：独立RF工作树先写跨进程确定性的RED测试。

Phase6 P0实现与原三公司大节点已通过（47PASS、无FAIL、1改善/70不变），RF main=72ce94c1；剩余能力保留。Next Step：CWP-owned Dayu共用预算transport与失败usage/timeout责任测试，随后SDK桥。

P1基础预算/HTTP/子进程及入库集中79项通过；下一步实现Dayu SDK桥公开DTO/财政期间/配置路由责任测试，再运行隔离真实HK/US download→import→reuse→RF读取。生产acquisition配置尚未切换，Dayu零改动。当前累计模型授权USD20/2,000,000tokens，见phase6/budget_authorization.md。

P1 SDK公开接口/财政证据/实际HTTP回执及原件入库集中117项通过（包含实际Dayu SDK offline2），只读审查3项缺陷均有RED→GREEN。当前Next Step为复制候选配置的真实HK/US FF→CWP→reuse→RF读取，生产配置尚未提升；之后继续FF/ET费用及来源资格、格式规范化，不能把离线SDK绿记为真实供应商全绿。

当前：P1 Dayu annual/quarter/HK H1 raw-only有界采集已验收并提升配置。三市场full/live各真实新下载→入库→0下载复用→RF读取均PASS（50PASS、0FAIL；其余缺口保留），独立测试环境恢复不存在。新增Windows子孙进程超时根因已修并责任测试绿。下一施工项为FF/ET把费用、配置能力和账户权限分别判定，随后来源资格/HTML/PPTX/RF输入与摘要实际消费，两组完整新研究验收仍未完成。

最新：FF/ET费用与能力责任实现已并main/push（FF697af966、ET282e8908），ET74项、FF49项和真实0费用离线链通过；实际FMP账户明确entitlement拒绝，不算产品数据全绿。FF首次远端只有静态复杂度失败（418行为通过），拆开计数类型和回执身份两项责任后本地同测试绿，精确新SHA远端待监控。三条R6卡互相不写同一目录，基准/交接接口/责任测试和大节点明确；MAIN 持续目标不暂停，接收顺序按先完成先集成，不增加小节点审批。

发布确认：FF697af966 [远端CI37833957140](https://github.com/zhengcb81/filing-fetch/actions/runs/37833957140)成功；ET仓未配置Actions，不能虚报CI绿，用上述实际集中验收作工程证据。费用节点临时2工作树及9测试根已清除，原件删除0。新3工作树合计18,580,471字节，干净且未开工，见harness_lanes/worktrees.json。

## 2026-10-09：公司池真实审查循环

用户要求随机从已有公司池选公司→真实revenue-forecast-audit→四独立审查→专家共用根因PWF→实施及原公司复验→再选下一家，直到无主要问题/改进点。循环协调计划独立放在 C:/Users/郑曾波/Projects/revenue-forecast-audit/docs/plans/company-pool-cycle-2026-10-09/；此处旧工程责任、原两组回归和未完成Phase6仍保留，不重复创建同因施工包。当前goal active，语义已有继续循环，目标工具没有修改objective接口，未伪造新目标或完成旧目标。

重大修复后以三家不同公司连续四路实读clean并覆盖池中A/H/US、复用与真实新下载作收尾证据；BLOCKED/NOT_RUN/旧主要问题不算clean。预算沿现有效累计USD20/2M tokens，unknown照计。只在大的节点测试和审查。当前首轮从202个去重候选随机选定 NVDA，真实执行15步骤/9来源已封存且整体partial，四独立审查分批运行。复用FY25原件和真实新下载FY26/最新季度后再次0下载均有证据；叙述启动、latest期间、电话会entitlement和研究校准仍未解决，不能计clean。

## 当前 Next Step（2026-10-09）

用户最新顺序：先完成本主线PWF全部实施和两组三市场大节点，再运行公司池循环。W01已并三仓主线、定点安装且精确主线CI成功；W07记录兼容已合并审计工具并安装。W02已并ET/FF主线并推送、FF定点安装完成，三仓主线18检查点通过；W03已并CWP主线并集中113项通过。当前行动是RF同一owner按W04→W05→W06实施，同时CWP既有隔离目录推进跨run默认派生复用与离线OCR；随后做两组三市场真实研究大节点。接着完成跨run默认复用、全图PPTX正文能力、原三家和新A/H/US三家的真实研究与独立审查。NVDA首轮封存的24发现/14共因继续用于主线根治，不启动新的随机抽样；主线验收完成后再恢复NVDA复验及公司池loop。任何CI/算术绿均不替代研究验收。

### 2026-10-09 主线恢复实施清单

1. W02 ET已有预算实现及测试、FF已有传参接线，均尚未提交；完成实际公共CLI三仓联调，确认原件只入库一次、重复请求零下载、超限真实用量和无入库，再合并/同步/推送。
2. W03官方资料统一入库/发现/叙述读取已有未提交实现；接手完成公共读取与复用验收、交接后并线。RF W04–W06工作树目前干净，先责任测试后实施，保持同一owner串行。
3. 跨run派生复用和全图PPTX能力是本主线明确剩余责任，不能用来源工具的新功能替代或遗漏。
4. 固定原三家、新三家做真实完整执行及独立审查；保留旧失败/未执行基线和全部71检查点，发现共因回责任层修复。
5. 上述主线完成后启动审计技能loop，沿既有池、seed、预算和冻结NVDA证据恢复，不重新抽样绕开失败，不新增调度数据库或人工签收。
