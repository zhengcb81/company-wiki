# P7：本次只有三张可立即启动的独立施工卡

上一批 M3-JSON / M3-USAGE / M3-FLOW 已验收，不再次发出。本批三个工作目录已准备，源码实现尚未启动，用户可各交一个 harness **同时开工，无需等 MAIN**。

| 卡 | 工作与独立工作目录 | 唯一施工卡 |
|---|---|---|
| P7-CWP-PROJECTION | JSON投影确定性/不可变/旧回放；`C:/Users/郑曾波/Projects/_harness_worktrees/p7/cwp` | [p7_cwp_projection_identity.md](p7_cwp_projection_identity.md) |
| P7-RF | 经营校准绑定/逐业务年份情景支持诊断；`C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/revenue-forecast` | [p7_rf_calibration_binding.md](p7_rf_calibration_binding.md) |
| P7-AUDIT | 请求/记录/四路风险检查工具和技能；`C:/Users/郑曾波/Projects/_harness_worktrees/p7/audit` | [p7_audit_execution_review.md](p7_audit_execution_review.md) |

工作目录是同项目的独立 Git checkout，原主目录及原 owner 改动不动。RF复用本任务已干净旧集成树，branch已换为P7，避免增加870MB复制；这个目录名称中的m3只是路径，不是让你重跑M3卡。

## 给每个 harness 的启动句

> 在本卡指定工作目录实施。先读唯一施工卡、项目AGENTS和已准备的独立PWF，核对branch/base，用PLAN_ID与PWF_PLAN_ROOT恢复本卡。先写RED责任测试，再实现及一次集中离线E2E；只改允许写集，不写MAIN/邻仓/生产库/安装。完成后normal commit，报告HANDOFF.md/JSON的绝对路径与精确HEAD。不要重新建立权限或人工签收链。

三卡各有仅含本卡启动文档的bootstrap commit；base是源码基线祖先，不要求HEAD==base，不reset本卡PWF。三卡各自工作树的 `.planning/<本卡ID>/IMPLEMENTATION_CARD.md` 是本次施工卡同SHA副本，可独立恢复；中央本文件/三卡/INTERFACES只由MAIN更新。后续接口改动由MAIN记录新修订，不要求harness自己刷新主线。

## MAIN责任及合并顺序

MAIN继续CWP AUTO官方JSON统一subject/view、batch、generation、store、effect、transport/CLI接线；不会并行修改三卡源码写集。MAIN负责跨仓对接、定点技能同步、主线合并/推送、精确CI、原三家与新三家的真实审查。IQS/StockWiki/Dayu等没有本次施工任务。

三卡结束后按先完成先验收，不互等：

1. Source卡接旧API，MAIN最后选择canonical producer1.0.2并跑AUTO多issuer/multipage兼容。
2. RF卡独立CLI/经营诊断及可能补丁版，MAIN核对native算术/旧emitter、定点安装。
3. Audit卡无remote，MAIN接受本地commit并定点同步；用已有接口运行审计，共同检查新RF可选诊断，未支持新诊断不能阻断原流程。
4. 一次跨仓大节点联调，之后按原PWF真实六家公司研究与四路审查；工程绿不代表研究完成。

不自行merge/push任何主线、不no-verify、不强推、不动他人WIP。分支CI未触发和audit无remote如实留状态，不编造green，也不新造CI/人工release门。

## 交接与证据

[INTERFACES.md](INTERFACES.md)定义冻结接口/写集；[HANDOFF_FORMAT.md](HANDOFF_FORMAT.md)与schema定义最小交接；[workspaces.json](workspaces.json)记录实查branch/base/目录。只在大的节点审查，不逐文件签收。默认测试零外部provider/model，0新增费用，原累计USD20/2M及旧unknown仍保留。

新RF工作树最初在870MB跟踪体积预检被拒，改复用干净树；其中旧 `.planning` 约845MB需要后续专门盘点，**不在三卡中顺手清理**。原始文档底线及旧封存证据优先，清理需先区分真实原件与中间副本。
