# D4 外包施工包总览

状态：**五张实现卡已备妥，尚未派发。** 最终组合联调留给 ROOT 总控，不包装成第六张外包卡；实现修复仍未开始。D4 是解耦补漏，不等同于启动 RF/AUDIT 业务计划。

## 为什么这样拆

1. D4-01 是唯一需要同时改 CWP 来源清单接口和 StockWiki 默认消费者的跨仓业务线，必须让同一负责人维护两端的逻辑公司来源合同。
2. D4-02 完全属于 RF 的摘要采用入口。
3. D4-03 完全属于 CWP 的解析/理解 DTO 与包依赖方向。
4. D4-04 完全属于 CWP 的电话会入库 wire decoder；保持现有外层 v2 请求格式，FF 不需要同步改造。
5. D4-05 完全属于 FF 子进程诊断采集；既有请求/响应 wire 不改。
6. AUDIT 的两项跨仓测试先由 ROOT 收口，与五条实现卡分开管理。最终组合必须等所有实现卡交付后由 ROOT 做，这个协调工作不外包。

## 写域矩阵

| 卡 | 写入仓库/目录 | 不可碰的其它卡目录 |
|---|---|---|
| [D4-01 StockWiki 来源虚拟化](D4-01-stockwiki-source-virtualization.md) | company-wiki：新增 company source list/query 专用实现、CLI 入口及其本仓契约测试；StockWiki：公司来源适配、默认研究入口、公司配置与本仓测试/文档 | CWP `document_normalization`、`document_understanding`、`transcript_import_cli.py`、FF、RF、CWP `integration/`、ROOT runner |
| [D4-02 RF 摘要实际采用](D4-02-rf-narrative-consumption.md) | revenue-forecast：`scripts/source_narrative_context.py`、两项用户工具和本仓测试 | 其它全部仓库 |
| [D4-03 CWP 解析纯层](D4-03-cwp-document-layer.md) | company-wiki：`source_catalog/narrative_document.py`、`source_catalog/transcript_layout.py`、`source_catalog/__init__.py`、`document_normalization/`、`document_understanding/` 及这些模块的本仓测试 | StockWiki、RF、FF、CWP 来源清单新实现、电话会 importer、CWP `integration/`、ROOT runner |
| [D4-04 电话会公开 wire](D4-04-transcript-import-contract.md) | company-wiki：`source_catalog/transcript_import_cli.py`、相关 CWP wire/contract fixtures 与本仓契约测试 | FF 生产实现、StockWiki/RF、CWP 文档理解层、CWP `integration/` |
| [D4-05 FF 诊断输出](D4-05-ff-process-diagnostics.md) | filing-fetch：`scripts/ff_process_transport.py` 和本仓真实子进程测试 | CWP、ET、RF、其它 FF wire/API 和配置 |
| D4-06 ROOT/AUDIT 验收（ROOT 自持，不是外包卡） | company-wiki：整个 `integration/`、`tools/run_source_system_tests.py` 及直接相关说明；AUDIT：`tests/test_du6_current_cwp_bundles.py` 和为保持普通测试独立所需的本仓测试 | ROOT 持有，不与五张外包卡共享 |

每张实现卡均须在独立分支/worktree里施工。CWP 多张卡可以并行，但每张卡只改矩阵列明的路径；`integration/` 和 ROOT runner 不派给外包。跨仓卡 D4-01 使用 StockWiki 与 CWP 各自 worktree，提交由总控分别接收。

## 公共接口边界

- CWP 是来源目录、原件版本、物理路径与字节校验的唯一 owner。StockWiki 只拿逻辑来源列表、SourceRef/manifest、提取状态，并通过可替换端口读取原文或 CWP narrative；不能再遍历 `doc_root`。
- CWP 当前 `source-query` 按公司+已知文种/期次查询，不视作“列出公司的全部资料”。D4-01 在自己的跨仓卡内同时定义/实现有界公司来源清单端点及 StockWiki 消费。其 wire 至少要表达公司逻辑身份、as-of、可分页 SourceRef/必要 manifest 字段和明确来源可用状态，不传物理路径；精确字段、排序/分页、增量兼容和单公司多期样例都由该卡冻结在便携 fixture。其它卡不消费这条新端点，故无接口等待链。
- RF 复用现有 NarrativeContext v2/v3 语义。D4-02 只让实际消费链和两项用户工具接收并使用同一可替换 reader 配置；不改 CWP producer 或 wire。
- D4-04 保持 `company-wiki-transcript-import-request/2` 外层合同及现有 FF payload。CWP 显式解码协议已有字段，再映射到内部 `SourceRequest` 和 `DownloadCandidate`；内部默认字段变化不能隐式改变 wire。错误身份、期次、原始 SHA/字节和预算仍在 CWP owner 校验。
- D4-05 保持 `WikiConnection` 和业务 JSON 输出。正常 stdout JSON 决定业务结果；stderr 是诊断，保存/丢弃日志不能推翻已完整交付的成功结果。真实 deadline、进程树清理、stdin 截断、输出 JSON 不完整/畸形仍由现有责任层处理。不得改成无限日志/无限内存。
- D4-06 只组合公开接口和冻结 fixture，保留两项 AUDIT 原断言。AUDIT 无 remote 时 ROOT 本地测试报告如实写入参与范围；不得将 skip 计通过，也不创建未经授权的 remote。

## 依赖与收口顺序

五张卡无需互等其他卡的源码变更，可各自在自己的写域实现。D4-06 的两项 AUDIT 测试归属由 ROOT 按照既有独立端口先行收口；最终组合必须等 D4-01/02/03/04/05 都可接收后再运行一次。总控并线/集成，而不是让外包线改同一个 runner。

每卡交接前都由未参与该卡实现的独立审查 agent 按该卡验收表检查完整度、真实调用路径、泛化和测试；发现的问题由该卡负责人全部修好，通过后才交 ROOT 验收。测试只针对本卡新增/受影响域；D4-06 负责一次 ROOT 组合节点。不能把审查扩成每个 helper 签收。

ROOT 汇合顺序：先接收并各自检查五条实现线；收完后接收 D4-06 的一次组合/清理报告；总控只运行受影响的合同和该次组合测试，必要的源代码 CI 由各实际仓库自行触发。所有包通过后更新 `CURRENT_STATUS`，把 DEFERRED 的 RF/AUDIT 业务卡重新校准 READY；不自动启动它们。

## 每张卡通用交付字段

以卡内列出的一个 `handoff.md` 为准，提供基线 HEAD 和实际交付 commit、修改路径、逐项 D4 闭合点、公开合同与兼容性、确切测试命令/结果、独立审查结论/版本、临时资料清理情况、未完成外限。问题都修完再交付，不留下“已知小问题待 ROOT”。不覆盖原件、生产数据库/配置和别人的 WIP；不加人工授权文件、canary 放行或多重签收。

