## W05-AUDIT-LOOP ROOT 已接收（2026-10-11）

Audit `codex/w05-audit-loop` 的 `7a5d4b8`、`2ed0b5e` 已接收；ROOT封存原FAIL并按共因修复，正常快进 main `321d4c165575e81add3b4aa1ee9ba0a047ca6082`。两套物理技能目录 .claude/.agents 各24文件SHA MATCH，只同步本技能4差异文件/套与manifest，其他文件保留。Audit无remote，未创建远端。

24项原交接验真、19新增RED→GREEN、全220PASS、48步隔离E2E PASS（86.696s）、独立原6纯/2tmp反例复验PASS_WITH_SCOPE；scratch恢复absent，0项目HTTP/LLM/token/费用。实际源码/安装/独审与失败记录见[接收报告](evidence/root-audit-loop-acceptance/acceptance.md)。这是循环进度/恢复工具验收，不是三家真实预测质量通过。

W05-CWP-OCR、W05-RF-FLOW继续原owner；W06三卡READY各自排他，不能重派在施工卡。ROOT W04阶段判断/预算召回独审仍FAIL，保留原3P1/2P2及实证，不发布有缺陷selector；G2真实摘要消费、G4原公司独审和G5新公司/池loop未完成。原件、生产配置、活动累计账、其他owner WIP、Dayu/IQS均未改。既有母账413778tokens/334463µUSD+FX2764保持；本轮增量0。

CWP接收资料commit c9dd5124尚未远端发布时，发现`.planning`与`docs/plans`分类不一致导致资料误触发全量Unit/CI；原失败保留，5RED→58GREEN并正常提交8d281af1，正常钩子全范围PASS（====================== 3240 passed in 302.47s (0:05:02) =======================）、远端8d281af1已实读验真。纯资料以后走已有小smoke/CI路径忽略；运行源码、配置、未知路径仍检查。独立临时根已恢复absent。ROOT旧集成树的3个原干净门禁文件已核baseline blob后定点同步，其他W04 WIP不动。

## Next Step

本次CWP接收/分类修复已发布；ROOT继续修W04共用阶段/预算召回，原件回放和大节点独审通过后才推进G2→G4→G5。接收已完成的其他施工卡按真实交接逐项并线，不增加小节点签收。

以下为历史记录；原字节保留。

## 当前：IN_PROGRESS（2026-10-11T09:22:06.853114+00:00）

只读核对三树已有各自PWF，Audit已有pool_progress和测试WIP。原READY收据是开工前快照，不作为未分派新卡。遵守原排他写集，不清理他人未提交内容。新W06三包见[总计划](../w06_parallel_verification_2026-10-11/task_plan.md)，写集不重叠。

以下为历史记录。

# W05 独立施工总计划

状态：READY，可立即分派；协调员 ROOT；母计划 `cross-market-rf-e2e-2026-10-08` 继续 active。

## 目标与拆分依据

从真实审查发现的共用缺口拆分独立任务。每条线只有一个代码仓库、一个已创建的工作树、一份独立计划及交接目录；ROOT 接收并集成，不让施工者自行修改其他仓库来消除问题。

| 线 | 责任 | 工作目录 | 固定起点 | 卡片 |
|---|---|---|---|---|
| W05-CWP-OCR | 图片中未读清区域的诊断及有限恢复 | `C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr` | CWP `159b993e2f4d36c7e86dc12c9d6028f4a31b353a` | [CWP施工卡](cards/W05-CWP-OCR.md) |
| W05-RF-FLOW | 任意真实起止日的并表/收入贡献区间 | `C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow` | RF `1b616622763ece6549676f2a74f596e6c65244af` | [RF施工卡](cards/W05-RF-FLOW.md) |
| W05-AUDIT-LOOP | 公司循环的可复现进度与恢复诊断 | `C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop` | Audit `c0993332623637d53f059350a382d99a95ef731d` | [Audit施工卡](cards/W05-AUDIT-LOOP.md) |

三树为 Git 稀疏工作树，起始干净，共用各自已有 Git 对象，没有复制数据湖。精确创建收据：[workspace-receipt.json](workspace-receipt.json)。卡片读作独立完整入口，不要求另开或重置工作树。

## ROOT 的责任与公共接口

ROOT 继续 W04 的 0.8 业务阶段分类、预算召回、LLM 配置集成；这些文件不在 W05-CWP-OCR 写集合。RF 的财务日期修复及 WP06 文档已发布，W05-RF-FLOW 从其最新主线开始。P7-AUDIT 已验收，W05 不重做其请求/逐文档状态/出处/审查协议工具。

公共接缝只增数据表达，不增加授权链：

1. CWP 仍输出原 `NormalizedDocument`/EvidenceSpan/SourceExport；未识别区域作为质量诊断，真正恢复的正文才成为有原始位置的 unit。旧未恢复区域不能被摘要编造。
2. RF 保持参数 `time_basis=period_flow`、`period_start`、`period_end`，通过新的 schema 3.10 表达不完整月/并表区间；3.9 及更早的含义不变。所有 annual consumer 必须复用区间规则。
3. Audit 用小型活动索引引用既有 runs/报告/预算账；输出恢复建议和诊断，不启动 agents/provider、不成为授权或质量门。

只有 ROOT 写六份共享 PWF、生产配置、累计母账及跨仓消费适配。施工者只写自己 `.planning/<lane>/` 与 `docs/handoffs/<lane>/`；正常提交其验证后的分支。ROOT 最终接收代码、做接口联调、安装及主线快进/推送。

## 阶段

- [x] 对照真实审查/主线和已有计划，明确起点与排他目录。
- [x] 建三份小型、干净、独立工作树。
- [x] 完成三张自包含施工卡、精确输入与统一交接格式；三树固定input已落地，独立卡片审查的发布前缺口已修。
- [ ] 各线先保存真正失败反例，再完成单元、集成、隔离端到端测试和普通 commit。
- [ ] ROOT 在交付大节点验收三个接口；互不依赖的交付可分别接收。
- [ ] 集成后回到 G2 原语言摘要 → 实际 RF 消费 → G4 原三家及 G5 新三家四路审查。

不在每个小节点新增复核。每张卡只保留三个工程里程碑：反例/TDD、实现及集中测试、最终交接。真实收费跨仓循环由 ROOT 在原大节点执行。

## 接收与冲突处理

每线给 `handoff.json`、`handoff.md`、`manifest.json`、测试日志与独立账本；格式见 [handoff_contract.md](handoff_contract.md)。ROOT 核实际差异与接口行为，在隔离集成树按提交接收。分支运行期间不 rebase 到 ROOT 尚未完成的工作，主线前移也不清除别人 WIP。若接缝确实需越界，交付最小事实与建议接口，由 ROOT 处理共享代码；本线继续本责任层工作。

本轮施工默认无付费 provider/LLM。OCR 只用本机现有配置和权重；RF/Audit 主要离线。累计 $20/200 万 token 母账沿用，不能每张卡从零另开户。

## Next Step

施工计划已正常提交并推送db6a72ee，交给用户分派；ROOT继续W04阶段否定/预算召回与配置集中发布。三个harness无需互等。
