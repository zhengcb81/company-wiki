# G2并行施工总包：三仓独立工程线

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

**状态：2026-10-07三卡均已交付，MAIN责任验收并正常并入各仓主线。SW0b48919本地主线（无remote），RF1a2f9428已推/精确CI29秒绿，StockQA0f8fbfa已推/精确日常CI35秒绿、文档构建21秒及部署7秒均绿。owner工作保留；不再分派这三卡。**

正式接收：[SW](results/g2_stockwiki_daily_main_acceptance_2026-10-07.json)、[StockQA](results/g2_stockqabyllm_main_acceptance_2026-10-07.json)、[RF](results/g2_revenue-forecast_main_acceptance_2026-10-07.json)。大节点全包复用外线已绿收据，MAIN只补日常责任与真实剩余错误，不增加每小步审批。RF报告的历史质量读取器漂移及技能包装职责进入MAIN P1，G2B跨仓当前producer仍在总计划中。

用户2026-10-07要求较大且互不影响的独立施工包。本包从G2真实剩余中拆分，复用已完成reader/身份/旧工程卡；不重派已交付功能。MAIN继续CWP G2-13轻初始化、01b精确读pin、CWP/FF latest单请求及共享接口接线。目标服务已实读active，原paused文字属于上一轮时点。

## 1. 三条线与实际目录

| 卡 | 施工仓与基线 | 专属工作树（创建前确认不存在） | 任务 | 优先级/依赖 |
|---|---|---|---|---|
| [G2-SW-DAILY](g2_stockwiki_daily_checks.md) | StockWiki/master `9f552a6741dd093dc760ad6965458989cd027251` | `C:/Users/郑曾波/Projects/_g2/sw/StockWiki` | 单检查入口、日常与大节点分离、隐藏覆盖率/体量门退出、实际消费者回归 | P0-B；现在可开工；联调用冻结CWP代码快照 |
| [G2-SQA-CHECKS](g2_stockqa_engineering_checks.md) | StockQAbyLLM/master `6a9ff13864ebb160d5c4ab3cf2f42155d9f4aa99` | `C:/Users/郑曾波/Projects/_g2/StockQAbyLLM` | 本地sh/bat/CI/hook统一、真退出码、默认报告退出、关联workflow同步 | P0-B；无跨仓实现依赖 |
| [G2-RF-TOOLS](g2_revenue_forecast_optional_tools.md) | revenue-forecast/main `e241389adeda37bc9cbb53d7831063718552a936` | `C:/Users/郑曾波/Projects/_g2/revenue-forecast` | 可选发布/质量/会话清单收敛、check-only真只读、历史兼容 | P1但可并行；不等待CWP改造、不占MAIN工程优先级 |

三个写入根互不包含，分支分别为`codex/g2-sw-daily`、`codex/g2-stockqa-checks`、`codex/g2-rf-tools`。卡文件都存CWP以便统一交付，**实现分别在表中的三个仓库**。原工作树、用户配置/pilot/历史worktree不作为施工目录，不reset或清理。

StockWiki无remote，交付本地commit；其他两仓可正常推自己的施工分支。各harness不能合主线/改共享index/安装技能/写他仓。MAIN接收commit后检查允许写集、责任测试、接口影响，再正常并主线/推送对应代码/核精确CI；不要求每helper人工签收。

## 2. 为什么可以同时做

- 三卡只改各自工程入口、诊断工具、相应责任测试与本卡记录，不改公共来源/投资DTO、模型/预算或研究计算。
- StockWiki消费者E2E使用`93ac5a534e24ecbf9e1fc873f88bd106278f2fd6`已发布CWP代码导出到**SW自己的scratch**，不使用正在变化的MAIN工作树；代码依赖快照是临时测试材料，结束删除。
- RF不改`assurance/runs`三owner日志、forecast/evidence/source adapter或日常11包检查；StockQA不改业务`src/**`及7项owner资料；SW不改生产data/wiki/config/研究状态。
- harness仅写本仓本卡计划和交接。CWP总PWF、当前施工卡、生产状态、安装同步由MAIN独占。
- 全部测试离线；供应商HTTP/收费/翻译/生产写0。供应商套餐或凭证问题不能在此包变成新的审批系统。

## 3. 每卡共同实施纪律

1. 读完整单卡；重核HEAD/status/任务记录。基线若推进，解释相关diff后从最新合法主线开始，记录实际base；不擅自丢owner变更，也不为HEAD不同反复请求签收。
2. 创建自己的新worktree；目录/分支已存在则核归属和Git记录，不能覆盖、reset或借用其他任务目录。三卡给了可直接运行的命令。
3. 先写真实行为RED，再实施。数字阈值退出是用户授权的工程合同调整；真实测试、类型/格式、来源/预算/研究语义失败仍非零。
4. 日常commit仅便宜静态；检查入口用一份Python定义，shell/CI不能各维护一套列表。全套离线只在**本卡实现完成后一个集中节点**运行，开发时只跑受影响责任包。
5. 临时根运行前记录absent/清单；用当前OS账号创建、执行和清理，不用sandbox所有权错误修改ACL/safe.directory。Windows长路径失败先用独占短根验证原因，不删真实负例。
6. 成功和失败均清理本轮复制/生成/下载文件，恢复测试根原状。只能删除明确自己创建、绝对路径包含且无reparse的目标；不全盘`git clean`，不删生产raw，不做整库备份恢复演练。
7. 代码与本卡报告正常commit，按仓有无remote准确记录push/CI。完成后freeze写集并交付，MAIN统一接线；不等待每小步审查。

## 4. 交接接口与MAIN验收

每卡在自己仓内交付一份`HANDOFF.md`和小`handoff.json`，具体位置/字段已重复写入单卡，单独拿卡即可实施。必须包含：lane/base/branch/worktree/commit/写集、真实RED→GREEN、实际命令/退出码/计数/时长、保留反例、临时根恢复、owner保护、外部与生产副作用、兼容及剩余项。

不要求新的签名、authorization文件、trust TTL、coverage分数或固定测试数量。用例skip/NOT RUN需解释，不能报pass；工具启动/收集失败不能报绿；报告不能替代实际代码commit。

MAIN并线顺序可为SW→StockQA→RF；等待哪个包不阻断CWP13/01b。测试需扩大时只围绕实际修改的责任。StockQA security/release/docs和RF release_checklist/历史报告读取器是本次追加的同步责任，不再漏到旧工具继续要求签收。

## 5. 主线保留范围

MAIN独占CWP源码/来源DB/生产raw/总PWF、FF v1/v2及两个安装副本、所有主线合入；Dayu纯外部、IQS独立项目、StockInfoDLSimple owner工作不介入。公共SourceRef/SourceExport v2/NarrativeRef、原语言和真实SHA/身份/期间/as-of/locator不变。G2工程并行交付不等于R2生产metadata或R3真实final完成。

本包当前事实来自2026-10-07三仓只读复核；未创建外部worktree、未运行长测、未写任何外仓。用户可把三份单卡分别交给三个harness，现在无需等MAIN代码。
