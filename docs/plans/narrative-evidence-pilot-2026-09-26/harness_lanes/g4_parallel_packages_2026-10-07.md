# G4：两项新增、可同时开工的大任务

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

**状态：两包已验收、并线及远端发布；不再派发。** CWP df7d7ba/精确CI74秒绿；SID eb8495c/127责任和真实离线合同绿，无workflow。MAIN短接收树与测试根恢复absent，外线工作树/记录保留。完整G2-12仍未完成；总目标保持paused。见[正式收据](../g4_main_acceptance_2026-10-07.md)。

发卡时记录（现G3已验收）：上一批G3的三个工作树已经存在，RF/SOURCE-FACTS已有独立task_plan，未见完整交接。G3不重复派发。本批分别取自现有G2-03退休待办和G2-12调查中已证实的CN provider能力缺口；不增加新阶段或人工门禁。

## 1. 两张施工卡

| 单卡 | 任务与规模 | 独占工作目录 | 已提交基线 |
|---|---|---|---|
| [G4-CWP-PIPELINE](g4_cwp_frozen_pipeline_retirement.md) | 整体退出冻结Pipeline/Gate0–5配置与实现；迁移有价值测试、纯stdlib退休入口、修正部署报告；代码+测试+接线表 | `C:/Users/郑曾波/Projects/_g4/CWP-PIPELINE/company-wiki` | CWP `5930a644453ed46494c2c83c5ecfb97767fa9492` |
| [G4-SID-LATEST](g4_sid_latest_discovery.md) | CNINFO按as-of发现最新年报/半年报/季报；日期、分页、期间、版本与共享资源限额；真实JSON CLI离线联调 | `C:/Users/郑曾波/Projects/_g4/SID-LATEST/StockInfoDLSimple` | SID `8ed5fdde5e88c13470c120665ff3074a7f44a052` |

两个目录互不包含，也不是G3目录的子目录。分支分别`codex/g4-cwp-pipeline`、`codex/g4-sid-latest`。目录/分支若被其他工作占用，用独占后缀并记录；不能reset、覆盖或复制原仓未提交文件。

## 2. 源码所有权与冻结接口

- **G4-CWP-PIPELINE：**仅旧`full_pipeline/gate_system/pipeline_rules`、deployment报告相关代码和精确专属测试、自己计划/交接。它不写G3-MAINT的维护后端，也不写MAIN的来源CLI/获取服务/指纹/hook/CI。
- **G4-SID-LATEST：**仅SID的adapter/API/JSON CLI及对应测试、自己的计划/交接。原SID的11个tracked owner改动与未跟踪资料/脚本保留；不改downloader/browser/mapping/logger、生产config，不清原仓。SID当前执行分支是`v2-clean-rewrite`；Git remote仍名为StockInfoDownloader，不意味着要整理或合入旧项目的main。
- **G3：**RF质量/包装、CWP维护后端、R2/R4只读事实调查继续按原卡；不占本批写集。
- **MAIN：**继续拥有G2-12 acquisition/service/close_gap、公共CLI、FF、版本配置接线、工程清单、安装、生产状态、总PWF和主线合入。总目标服务此刻实读paused；本次只交付计划，不擅自恢复生产/付费运行。用户另行启动的harness只按自己的卡施工。

CWP SourceRef/SourceExport v2、NarrativeRef、FF/ET协议不变。SID成功/失败JSON仍schema1.0；latest只增加兼容请求解释，返回真实候选，唯一目标与canonical路径由CWP决定。新adapter版本与路由版本由MAIN配套接入，不让harness修改生产路由或用户配置。

## 3. 工作方式

各卡自包含背景、精确写集、输入输出、TDD、恢复、交接与MAIN责任，不依赖阅读另一个harness的上下文。代码责任先RED再实现；开发只跑受影响测试；每卡完工一个集中责任/E2E节点。MAIN接收后在已有G2A/B集中验收，不追加小节点审批，不把固定pass数、coverage或文档签名当门。

模型调用、翻译、付费API均为0；Dayu、IQS、StockWiki/StockQA其他owner工作不涉及。测试下载/副本/日志只在自身短临时根，finally恢复最初状态，原件0删除。单卡详细说明实际路径和清理证据。

## 4. 接收与合入顺序

两包不等待MAIN即可完工，也不互相依赖。已执行：MAIN先独立接收两包，SID provider与路由合同可先并线；完整G2-12事务仍待后续集中节点，不将provider交付阻塞在未完主线之后。具体责任：

1. PIPELINE库层/脚本退休与MAIN工程清单同次集成；G3-MAINT的公共CLI接线单独归MAIN，避免两外线同时编辑清单。
2. SID的CLI/共享预算JSON先通过已发布CWP `JsonCommandAdapter.discover_bounded`消费合同，再由MAIN在统一ensure中验证实际最新期间、只下载一次、重复复用和清理。CN latest发现成功不等于US/HK外部provider硬限额已支持。
3. 正常提交、合入实际目标分支、推送对应远端并核代码SHA的CI。外线可推自己的分支，不能代MAIN合主线/发布生产/安装技能。
4. G3来源事实交付仍供应R2/R4；G4不改生产metadata、不生成生产final、不扩累计模型预算。G2→R2→R3→R4→R5总顺序保持。

## 5. 独立交接

每卡在自身`docs/implementation/g4-.../`交`task_plan.md/findings.md/progress.md/HANDOFF.md/handoff.json/main_wiring.md`。统一`schema_version=g4-handoff/1`，字段见两张单卡。引用实际实现commit和可解析delivery分支，不要求JSON在自身提交前写出该提交SHA；不能为自指SHA循环新增签收。

交付必须区分：代码责任GREEN、真实公共CLI的离线GREEN、未执行live、尚待MAIN接线。报告实际替换的HTTP边界、命令/退出码/耗时、owner保护、临时根恢复与remaining；不能拿mock CLI响应称真实三仓链已通过。
