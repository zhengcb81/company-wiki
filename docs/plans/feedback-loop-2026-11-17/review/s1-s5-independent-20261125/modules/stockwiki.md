# StockWiki S1–S5 独立复审

2026-11-25。复审在 F4 引用的 [StockWiki 本地仓](</C:/Users/郑曾波/Projects/StockWiki>) 执行，`master@65d3902578629c42d1caf72a16f5c2dea794d3e1`，无远端。复验前后跟踪差异均为 `findings.md`、`progress.md`、`task_plan.md` 三份在途文档。Windows Python 3.13.9、pytest 9.1.1。数据库和日志使用独占夹具，模型成功响应和 verified-open 回执来自本地替身。外部请求、费用和生产写入均为零。

| 项目 | 判定 | 本次验证范围 |
|---|---|---|
| S1 | 部分 | 复跑文档缓存和 HTML 异常日志、账本写失败日志。一次合成模型响应在账本不可写后原样返回，原异常可由新进程冷读，运输调用仍为 1，费用状态为 `unknown`。历史 UI 和 onboarding 修复随主线保留，本次读取实现。公开资料读取仍有下面的故障黑洞。 |
| S2 | 部分 | 身份 CLI 的真实 SQLite 错误可从轮转日志和 F4 找到同一运行、尝试、版本、步骤及原因果链。账本回归验证降级后保留原响应和费用未知。身份查询及资料验证的正常对照均无可冷读的运行步骤，资料读取 I/O 失败也没有记录。 |
| S3 | 部分 | 来源读取走 CWP 的版本化 export 和公开 verified-open 子进程协议。身份重键写已回到 QuickScanStore，同事务行为通过。身份桥仍自行打开并查询身份 SQLite，实际复现路径失败及只读操作创建文件。其余仓内 Store 访问和运行环为本轮未证。 |
| S4 | 部分 | 实际日常清单收集 396 项，含三条原生日志和一条身份写回滚。仓内有 Ubuntu 工作流和 API 边界扫描。已复现的 SQLite 路径问题及资料读取日志缺口没有对应日常用例。本地正式线缺同版远端执行证据。 |
| S5 | 部分 | 在普通路径独立验过跨库原键恢复、强停、同事务回滚、归档只读重投和公开 CLI 的结果回读。相关提交均在现行本地主线。轮转和日常门禁按提交与收集结果核对。资料入口覆盖和身份桥路径仍有实证缺口。 |

## 实证与根因

### SW-01 · P1 · 身份桥只读入口打开了错误路径

用 `QuickScanStore.migrate()` 生成空身份库，将同一字节复制到等长的 `owner-plain` 和 `owner-#lain` 工作区。用各库的 `Path.as_uri() + "?mode=ro"` 可执行同一 `SELECT count(*) FROM quick_scan_entity`，结果均为 0。分别在新进程执行 `python -B dashboard_identity_bridge_cli.py search --root <fixture> --query "Synthetic Name"`。

| 夹具 | 公开结果 | 诊断与数据 |
|---|---|---|
| `owner-plain` | 退出 0，stdout 一行 JSON，`resolution_status=no_match`，匹配 0，stderr 空。 | SQLite 字节一致。隔离收件箱和轮转日志均为 0 条，无法从原运行号冷查一次成功读取的起止步骤。 |
| `owner-#lain` | 退出 2，stdout 空，stderr 一行 JSON，`owner_offline`，原因 `no such table: quick_scan_entity`。 | 实库字节一致。日志、诊断、F4 ready 各 1 条。按原引用两次新进程 `get` 均退出 0、输出逐字节一致。 |

失败观察为 `independent-sw` / `hash` / `identity.search`，Git 版本与受审 SHA 一致。冷读原引用 `sw:runtime-failure/c11b182899084a328a07884c5dbde811`，异常从 `DashboardIdentityBridgeError` 追到 `sqlite3.OperationalError`，文件、函数、抛出点分别落在同一模块第 370 与 359 行。另一次只读复验用 `owner-#path`，CLI 退出 2 后同父目录新出现 0 字节 `owner-`，原库字节仍一致。

桥接层用 `database_path.as_posix()` 手拼 SQLite 文件 URI。SQLite 把 `#` 及其后的原路径和 `mode=ro` 当成 URI 片段丢弃，以默认模式打开前缀。随后执行的 `PRAGMA query_only=ON` 已晚于空文件创建。身份修复 `complete()` 也用公开身份解析确认，首轮 B34 测试在系统临时目录的 `#!sandbox...` 路径上有 3 项因此失败，错误为 `unable to open database file`。改用普通短路径后原三项通过。[只读连接与 resolve](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/dashboard_identity_bridge.py:158>) · [search 查询和异常包装](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/dashboard_identity_bridge.py:345>) · [对照用的归一化连接](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/security_id_normalization_store.py:66>) · [重键公开确认](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/admin_security_id_normalization.py:65>)

验收应经 QuickScanStore 的只读接口统一构造连接，在普通、`#` 和其他需 URI 转义的合法目录上，用真实公开 search、resolve 和 B34 同键恢复验证结果一致。对照检查正确库字节和目录文件清单。数据库确实不可读时仍须用原协议退出，异常链保持可冷读。

### SW-02 · P1 · 公开资料读取原异常与正常步骤均缺席

从同一代码根调用显式启用的公开入口 `python -B -m stockwiki.cli source-read-v2 --bundle <fixture> --reader-config <local-stub-config> --source-id <fixture-source-id>`。使用仓内 SourceExport v2 夹具和本地回执替身，真实入口退出 0、stdout 一行、stderr 空，返回 `verified`、`loc:v1/chars:4-22` 和原文 `Revenue increased.`。第二次把 bundle 路径换成不存在的合成文件，退出 2、stdout 空、stderr 一行 `bundle_unreadable`，`detail` 含系统错误和本机合成绝对路径。原夹具字节保持一致。两次均给定 run/attempt 与独立收件目录，实际本地日志、cause、F4 ready 各 0 条，冷查没有原证据引用。

主 `stockwiki.cli` 解析后直接调用注册处理器。资料处理器把 I/O 异常包装为 `SourceExportV2Error`，把 `str(exc)` 原样作为机器错误明细，并在同函数写 stderr 返回。这个入口未经过原生诊断链。verified-open 传输也会将缺回执转换为现有机器码，消费失败归属须在清除明细前记录。已接入的 `observe_cli` 只在异常、拒绝或非零结果发本地失败记录。受验失败日志包含时间、版本和栈，输入摘要在伴随诊断内。F4 写失败可以在日志记录 `delivery_error`，原拒绝机器输出保持。轮转日志和投递同时不可写时，现有 `handleError`、`OSError` 和外层异常处理不会再留下独立告警。[主入口](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/cli.py:21>) · [资料处理器](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/services/source_reader_v2.py:31>) · [资料本地夹具](</C:/Users/郑曾波/Projects/StockWiki/tests/test_source_export_v2_cli.py:345>) · [公开传输](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/_source_reader_v2_transport.py:126>) · [运行上下文](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/runtime_feedback.py:80>) · [双层持久化](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/runtime_feedback.py:309>)

验收应保留机器码、退出码和 stdout 结构，把系统错误与脱敏栈挂在同一次运行的原引用上。使用本地回执替身比较健康结果、bundle I/O、子进程拒绝及双诊断介质故障。正常调用的开始、验证请求、返回和终态须能用同一运行及尝试号回查，双诊断故障须保留机器流并留下可达的宿主诊断。

## 已通过的恢复与日常检查

- **账本。** `record_usage` 发独立 `usage_ledger_write_failed` 步骤，保留外层原运行和尝试。复跑已收到一次合成模型结果后写盘失败的用例，原响应和外层退出 5 保持。两个冷进程读取同一纪录，异常栈定位到原账本文件。owner reconcile 为 `cost_unknown / unconfirmed / unknown`，不生成新费用记录。文档解析回归检查缓存及 HTML 失败的原异常日志。账本价格读取另有常规 logger，`summarise()` 的逐文件 `OSError` 仍直接跳过，此路径仅源码核对。[账本](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/llm_usage_ledger.py:54>) · [账本冷读用例](</C:/Users/郑曾波/Projects/StockWiki/tests/test_llm_usage_ledger.py:109>) · [S1 解析和账本用例](</C:/Users/郑曾波/Projects/StockWiki/tests/test_s1_p0_logging_observability.py:10>)
- **身份事务。** `7bc366de` 把实体和绑定重键移到 `QuickScanStore.rekey_security_in_transaction`，继续使用原 `BEGIN IMMEDIATE` 连接。对真实 SQLite 在 owner 写之后注入异常，原实体、绑定、收据可读回，操作无此键，同键重试完成并重放零写。跨库阶段已先保存 `entity_saved` 恢复日志，子收据和旧收据 supersede 分步提交。收据提交后公开确认失败，可从 `pending_finalize` 沿用同一子收据和版本 2 完成。另在真实子进程用退出 73 模拟阶段强停，随后同键恢复并查验字节。公开 CLI 的 preview/apply/status 正常对照也通过。[写入和日志同事务](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/security_id_normalization_store.py:312>) · [QuickScanStore 写端口](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/quick_scan_store.py:299>) · [恢复锁及顺序](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/security_id_normalization_store.py:259>) · [确认失败用例](</C:/Users/郑曾波/Projects/StockWiki/tests/b34_id_normalization/test_normalization.py:236>) · [公开 CLI 与强停用例](</C:/Users/郑曾波/Projects/StockWiki/tests/b34_id_normalization/test_normalization.py:602>)
- **归档。** `d09e2bef` 的默认范围从当前 `native` 和历史目录冷读。由公开拒绝产生未送达的唯一历史副本后，两个新进程以相同原引用重投成功，当前目录仅一条观察，历史副本字节不变。明确传历史范围的兼容用例仍按调用方选择的目标写入。收件目录被文件占用时，公开拒绝原 JSON 和退出码保持。上述恢复、S1 和公开身份回读在无 `#` 的隔离根共 9 项通过，9.64 秒。[收件目录和归档读取](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/runtime_feedback.py:42>) · [同键重投](</C:/Users/郑曾波/Projects/StockWiki/stockwiki/runtime_feedback.py:417>) · [历史单副本用例](</C:/Users/郑曾波/Projects/StockWiki/tests/test_runtime_feedback.py:254>)
- **日常与静态。** 用实际 `SHORT_TESTS` 执行 `pytest --collect-only`，退出 0，396 个节点。四条新增节点分别覆盖读取占用时轮转、两个拒绝并发轮转、半行后的 F4 triage 冷读、原连接身份回滚。日常清单里有 Quick Scan sibling API、域预算和公开导出约束。SQLite 路径、`source-read-v2` 整体入口、账本冷读、归档重投、提交后确认恢复未进入该清单。仓库跟踪在 push/PR 上运行 `scripts/checks.py` 的 Ubuntu/Python 3.13 工作流，由既有 `120c1e5` 提交引入。Windows 文件占用语义和当前本地 SHA 的远端执行分别依赖本机定向用例及后续实际 CI 证据。本轮收集日常节点，另跑上述 9 项定向测试。[工作流](</C:/Users/郑曾波/Projects/StockWiki/.github/workflows/ci.yml:9>) · [日常节点](</C:/Users/郑曾波/Projects/StockWiki/scripts/checks.py:48>) · [域预算约束](</C:/Users/郑曾波/Projects/StockWiki/tests/test_f05_module_api_boundaries.py:625>)

版本链为 S1 `9904b43e`、S2 账本 `665f6a85`、原生收件目录 `dd5b0338`、归档和轮转 `7fbd9a5e` / `d09e2bef`、身份写端口 `7bc366de` 和日常检查 `65d39025`。此前 Windows 宿主接收及去重证据限定原上线节点。当前审查复验公开子进程和本地存储，使用总控既有 F4 路径核对，不改定时器。[原 S5 台账](../../s5-verification-20261125.md) · [StockWiki 本仓实施凭据](</C:/Users/郑曾波/Projects/StockWiki/.planning/modularity-closeout-20261111/S5-native-feedback-20261125.md>)
