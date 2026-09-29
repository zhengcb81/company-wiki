# StockWiki 独占施工卡：来源 reader、QuickScanStore 与身份消费

> **2026-09-29 状态更新：**W01 已在本地 `master@5bb68f6` 完成并独立验收。基础 SourceExport v2 reader 现在有可直接派发的[独立施工卡](stockwiki_source_reader.md)，应先按该卡实施；本页下方 W01 的 8/10 失败数是开工前历史快照。W02/W03 仍待 IQS 公开验证 CLI 和 StockWiki 真实身份 snapshot，不是基础 reader 的前置。同一时刻只保留一位 StockWiki 写入者。

> 可单独交给一个 StockWiki harness。**唯一写入目录**：`C:\Users\郑曾波\Projects\StockWiki` 的指定集成 worktree；`C:\Users\郑曾波\Projects\StockWiki-v2-reader` 是可检查的既有隔离工作树，不表示已有 reader 实现。CWP/IQS/RF/FF 只读；不得写它们的数据库或文件。StockWiki 独占投资研究状态，CWP 只提供来源与证据。

开工输入包：本卡、S0a observed 接口表、CWP SourceExport/selected 的 S0b golden（未产时标 pending）、IQS 2.2 schema/校验 CLI、只读 P/T 样本清单和本仓 W01 活动文件归属表。

## 已知状态和外部接口

2026-09-29 调查时 `master@f5b8526`；`stockwiki/quick_scan_store.py` 和 `tests/test_quick_scan_store.py` 是未跟踪的**活动 W01 实现**。早期 18 项测试有 8 pass/10 fail，但本轮未重跑；先核实际状态并把有效 W01 工作保存到本仓集成分支。reader 分支与 master 同 HEAD 且没有 reader 代码，不把空分支当完成。仓库没有已知 remote，先完成本地 main 整合，不编造远端发布。

外部输入有两项，均通过版本化 JSON/CLI 与真实 producer golden：

1. CWP SourceExportBundleV2 `2.0.0` manifest/span/locator/export ID/bundle SHA，与 SourceRef `2.0` verified-open。StockWiki 只保存 source ID/version/hash/locator，不自己扫描 company/dayu/Dropbox 根或把物理路径 hash 当 source ID。
2. IQS identity package `2.2.0`，其中 Entity `2.1.0` 与 AnalysisSubject `1.0.0`，提供 issuer/security/listing 的 schema、参考校验器、合同夹具和公开 JSON 校验 CLI；**StockWiki 是身份库/名单唯一生产写入者**，须从自己的真实 DB/serializer 生成 identity snapshot golden。本仓运行时按公开 schema 本地验，总指挥在 G2b 用 IQS CLI 交叉验，不让 StockWiki 导入 IQS 内部 Python 模块。跨仓映射结果 DTO 目前不存在，须由 StockWiki 定义并实现版本化 status、issuer/security/listing、as-of、来源绑定、错误码。`mapping_status=null` 是 JSON null、表示未请求/未尝试；`unknown` 是已尝试但无精确匹配，`ambiguous` 是多个候选，`mapped` 是唯一精确绑定。四态交 IQS 校验，不可写成 identity 2.2 已有输出；身份映射不成为基础来源 reader 的前置。

## 在本仓内的实施顺序

1. **W01：**先 TDD 收拢活动 QuickScanStore，解决绑定漂移、同 revision 覆写、verified 无来源结果、布尔/版本 coercion、SQLite 句柄问题，使 18 项及直接依赖测试通过。若修复影响既有研究状态，保持历史 accepted/rejected 语义和可读性。
2. **基础 reader：**先针对 CWP 真实 SourceExport v2 golden 写消费合同，建立 StockWiki 自有薄 reader/CLI；从 CWP verified-open 取得字节或验证结果，检索和引用只持逻辑 ID。`stockwiki/sources.py` 的绝对路径 SHA1 source ID、`analysis.py`/`enrichment.py` 的 `doc_root` 分支在新 v2 路由下退役。只有真有旧持久引用时实现窄兼容，不能依据 CodeGraph 过期索引重建已不存在的 `source_provider*.py`。
3. **Q 线：**先让 W02/W03 身份库/名单真实 serializer 产生 snapshot golden，用 IQS 2.2 schema 验正反例；再定义四态 mapping DTO，逐态消费与返回。`mapped` 需精确 issuer/security/listing + as-of + 来源绑定；`unknown` 有已尝试查询且无匹配的事实，`ambiguous` 列候选而不合并，JSON `null` 表示未尝试且不能伪造无匹配。错证券/上市地/期间返回具名失败。更新 DTO 版本和 golden 后交 IQS 补参考反例与总指挥用公开 CLI 做 G2b。Q 线测试与基础 reader 可独立报告，身份尚未完成不阻 v2 reader opt-in。
4. **full sync/weekly：**确定真正缺失的 provider/sync/weekly adapter；先写重复、撤回、版本替换、坏 verified 结果及零隐式 Tavily 的 RED 测试，再实现显式 CWP 来源模式。保持 opt-in，G-D 由总指挥跑完整 CLI/weekly 真入口后再决定默认路由。
5. **selected 消费：**CWP 持久 package 的真实 golden 冻结后，在 StockWiki 增独立只读 adapter/CLI，从 source ID/version/raw SHA 回源 verified-open 并回放 locator；区分 selected、skip、partial、needs_review（后者是来源质量诊断，不自动变成投资审核）。撤回/as-of、错 hash、未知版本不得进入研究事实。此线实现和测试是 G-C 前置，不以基础 v2 reader 通过代替。
6. **工程测试流程：**当前 `AGENTS.md`/`scripts/check_all.sh` 每次提交要求两轮 pytest（普通及 coverage）；按用户统一简化要求改为开发时受影响测试、大节点一次全量及 coverage。同步本仓 AGENTS/脚本说明，保留真实质量阈值；`review_workflow.py` accepted/rejected 是投资研究状态，不作为工程人工签收清理。

## 本线测试包

- W01：`tests/test_quick_scan_store.py` 的 18 项及受影响集成测试；以本次实际运行结果替代历史 8/10 计数。
- identity：现有或新增 `tests/test_quick_scan_identity.py`、`test_quick_scan_universe.py`、`test_identity_mapping.py`，用**本仓真实 serializer/DB golden + IQS schema/校验器**的 issuer/security/listing、四态映射正反例；四态 DTO 尚未定义，先 RED 后实现。
- 来源 reader：新增 v2 reader/CLI 合同测试，覆盖 schema 版本、无路径字段、同 SHA 迁根、撤回、错 hash、旧引用及 P06 增发真字节 dry-run；正式 G-B 由总指挥使用 CWP 真 producer/verified-open 跨仓运行。不得通过同时 mock 掉生产者和消费者来宣称集成。
- selected：新增 `tests/test_selected_source_reader.py` 与 CLI 合同测试，用 CWP 正式 package golden 验 locator 回放、skip/partial/needs_review、as-of/撤回/错 SHA/错版本；正式 G-C 由总指挥跑 StockWiki 真入口。
- full sync/weekly：隔离 CLI/weekly 的正常、重复、撤回、版本替换和 Tavily 零意外调用；只在 G-D 做完整真实批处理。所有生成文件进本仓唯一测试根，结束恢复该根，生产研究状态不变。

## 交接与界限

交付本仓 base/branch/commit、W01/W02/W03 实际状态、本仓身份 producer golden 与 IQS 校验版本、CWP 来源/selected 消费 golden 版本、CLI/DTO/错误码、测试命令/退出、隔离根恢复和未解决项。总指挥在 G-B 测 reader，在 G2b 测 identity，在 G-C 测 selected，在 G-D 测 full sync/weekly。若 CWP 的 SourceExport 或 IQS schema 尚未冻结，本线可先修 W01 和写输入合同负例，但不得伪造 CWP producer 正例或跨仓改目录。

**本线自动验收：**W01 回归、v2 reader、身份 snapshot/mapping DTO、selected adapter、full sync/weekly 分别报告测试命令和通过/待完成；任何未实现项保持 pending，不用其它项的绿灯代替。新路由零 skip，错证券/版本/原文 SHA/撤回仍拒绝；真实 identity golden 来自本仓 DB/serializer 并通过 IQS 校验。测试只用本仓可写短临时根，生产研究状态及测试树前后相同；accepted/rejected 语义保留。
