# StockWiki 独占任务：持久叙述证据薄 consumer

> **已完成，勿重复派发（2026-10-03）：**最终`4c3334e`正常merge到master`ae0b3e3`，保留W05其他owner提交；合并后相关172passed/1平台skip，Ruff绿。14真实producer/consumerE2E、785项单仓节点和两平台生命周期包有既有收据，不重复运行。无remote不新增。见[G-C收尾](results/gc_consumer_closeout_2026-10-03.md)。下方为实施历史与接口记录。

## 范围与前置

只写 StockWiki 新 narrative adapter/来源 DTO、查询入口调用点、本线测试和文档；不写 CWP/FF/ET/RF/IQS。W01–W04、SourceExport reader 已在 StockWiki 主线，不重复实施；保留现有 `.claude/` 和无关 owner 工作。先核 Git/current PWF，基于当前 master 建 `codex/...` worktree。

先读 [producer 交接](../narrative_transport_handoff.md)，核 CWP 新接口已提交推送。使用主线 `tests/fixtures/narrative_transport_v1/` 作为 wire输入，不把 SourceExportBundleV2 当叙述包，不要求业务层 raw root。

## 顺序

1. 核既有 source-export reader、来源查询入口和可复用 subprocess 部署配置，先写新 narrative adapter RED：严格 request/receipt/bundle/hash/size、未知版本、退出非零/超时、metadata-only不能生成可用证据。保持 raw SourceRef/SourceExport wire不变，禁止导入 CWP Store/automation。
2. 实现精确 NarrativeRef read，形成 StockWiki 自有来源 DTO：source/version/hash、locator、摘要、coverage/质量/skip。同 source 新摘要不能改变旧 ref；请求身份/期间/as-of必须匹配。partial/needs_review保留事实诊断，skip无证据，不自动创建 accepted 投资结论或研究状态。
3. 接入现有来源查询/预览的显式 opt-in 入口，给可运行CLI或公开函数调用示例。缺包、unknown publication或错误都明确报告，0 Tavily/全文/LLM隐式回退。full sync/weekly/default切换留待后续 G-D，不在本卡扩大范围。
4. 节点 E2E：StockWiki 独占短根中的当前 CWP producer真实生成/持久化包→StockWiki 正式入口→CWP CLI→自身 DTO；至少招股说明书和 IR（P07质量needs_review应保留），覆盖原文/工件篡改、撤回、迁根、错身份/期间/时点、skip/partial、重复读取与失败0副作用。仅测试fixture可导入CWP测试辅助，不让运行时依赖其内部模块。生产文件/身份库/研究DB零写，网络零次。
5. 跑本线包、受影响已有 SourceExport回归和一次现有质量门；在仓库支持的方式正常并入本地主线。无remote不自行创造远端。交总指挥验 G-C；不等待无关 IQS full G2b。

## 输出和停止点

交一页 base/branch/commit、入口调用、接口版本/golden SHA、改动路径、测试/清根结果、hold。测试生成raw/DB/WAL/cache退出恢复；不改生产catalog/研究state、不开Worker、不加人工签收或private/public权限。该卡完成是消费能力，整体 G-C仍由总指挥汇合测试。
