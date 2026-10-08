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
