# ROOT 公开接口组合验收

2026-11-14，M2 已按 E01–E09 工程矩阵关闭。测试从独立目录启动，使用指定代码版本、临时配置和测试目录。真实语义召回、付费恢复、RF 公司采用和公司循环接续父计划。

## 代码版本

| Owner | 受测主线源码 | 发布 |
|---|---|---|
| company-wiki | `c6189c623f6ec30e2a1a1059499e78c8ffe5b443`，原件公开流先在 `9e76592e1` 发布 | 本地及远端 master |
| filing-fetch | `d4f35cab5127d09c874d109080d911e6d394dec2` | 本地及远端 main |
| revenue-forecast | `fab819c25922af1366d7240af9bfee58d3bd612a` | 三表独审通过并推 main |
| earnings-transcripts | `915f216f764e83012e8ce6f418111c9ef9eacace` | 本地及远端 main |
| StockInfoDLSimple | `d084c4aab48f5f83275f65982bf561e6870ff3a4` | 本地及远端 v2-clean-rewrite |
| StockWiki | `21cf4891019c8202e9e86996f47f0dbde7976293` | 本地 master。无配置远端 |
| revenue-forecast-audit | `3589b69cb9d28d7395607ce4fe689025b9acee96` | 本地 main。无配置远端 |
| investment-dashboard | `e1d1f927cc09a1249c0db31e9f98cd4d358d7ee1` | 本地及远端 main |

## 实际组合

| 项 | 状态 | 证据 |
|---|---|---|
| E01 | 通过 | 当前 FF 以 US:BABA、US:BILI 请求 FY2025 的 HK 来源，两份本地原件均零下载并匹配冻结 SHA。再通过 CWP 公开原件读取核对 HK:09988 和 HK:09626、FY2025 和字节数；挂牌与来源 owner 定向 51 项通过。 |
| E02 | 通过 | D4 的 FF→ET→CWP 首取、原语言原文读回、复用及未知发布日期回放；ET 19 项、SID 27 项定向预算/错误/隔离通过。 |
| E03 | 通过 | CWP 流式读取缓冲事务锁定、失败候选回滚、超量、字节变化和输出失败；当前来源端口相关 53 项，解析隔离及其他 owner 44 项。出站前完成字节验证。多文种采用同一来源合同。 |
| E04 | 通过 | 中微公司年报、半年报及招股书，金山软件港交所半年报，万润股份 IR、微软原语言 TXT、中大力德 IR PDF 与吉比特 DOCX。真实募集说明书 P06 在两个四根布局使用同一 SourceRef，优先路径损坏后仍从其他原件验真回读。原件未被写入。 |
| E05 | 通过 | 使用可计数本地模型和临时对象库，当前协议付费响应/存储/恢复 59 项，损坏候选与元数据等复验 51 项。自动发现的坏制品可在原账户内重建，发布仅恢复同 SHA 的派生字节，同 run 重开零重复调用。精确引用、原件和付费响应保持严格校验。 |
| E06 | 通过 | 当前 D4 30 项全过、无 skip，包含 RF 参数与报告、StockWiki 来源入口、Audit 公开资料包导入。StockWiki 隔离受测提交 6c6dc74b 与本地 master@21cf4891 的交付补丁等价。 [D4 实跑记录](root_d4_current_20261114.json)D5 真原件样本 1 项通过，业务资料和报告归各自 owner。 |
| E07 | 通过 | 使用正式 RF/FF 安装器的临时副本，调用 RF→FF→CWP 的公开三表入口。中微公司冻结快照 105 个报表版本和 9,729 条源行；两次查询零 HTTP，三表锚点及 JSON Pointer、原件 SHA、知识时点、按股 EPS 单位均一致。其余金额行的单位和缩放保留未知。CWP 三表/边界共 12 项通过，RF 定向 57 项通过及 1 项 POSIX 专用用例跳过。 |
| E08 | 通过 | 独立 install 的 CWP wheel 与真实 StockWiki、Dashboard 消费者联调 1 项通过。浏览、HTTP 原件 SHA 与已持久化摘要证据均可读。Dashboard 流相关组合 55 项通过。最终版本另复跑空队列、满队列及真实 HTTP 中止 3 项通过，独审通过。 |
| E09 | 安装及主要反控已过 | 五卡独立交付与审查通过；CWP wheel 合同 6 项，FF 38 项，ET 19 项，SID 27 项，RF 原模块隔离 14 项及本次安装/新入口组合。遗留 B10 的直接解析和单解码行为反控已通过。投影窄读取端口、Worker 资源关闭及恢复 156 项通过；mypy 489 文件通过。 |

## 发现与归因

- CWP 导出和解析以前接收同一个宽读取器，内部可以直接触达底层目录。现在由来源 owner 组装分开的只读能力，保存配置快照的私有副本。源文件在锁定前变化、重复定位候选失败、传输写入中途失败都有反控。
- ET v2 的挂牌身份早已在公开适配载荷中。CWP 上次收紧写入合同后只看顶层字段，导致合法旧 wire 无法入库。现在 CWP 用已验证的公开值补齐自己负责的入库候选，明确不一致仍保持拒绝。
- StockWiki 把已配置可执行文件和 CWP 源码目录绑在一起。将配置的 CWP 公开命令接到独立安装，复用既有有界进程和稳定错误语义。Dashboard 原流测试改用公共浏览和真实流，响应异常或取消会回收本次进程与对象。最终测试复现终止后消费者等待超时的根因。流适配器清理时唤醒它自己的两个队列，真实 HTTP 客户端及时收到截断错误，服务继续响应。
- B10 原调用点计数把重命名、已走统一解码的合法转交和不同表同名字段算成越界。保留直接解析反控，移除依赖旧函数名的计数；用测试验证制品元数据只解码一次、扫描合并沿用同一已解码值。三条历史挂牌用例校正为缺少挂牌证据时仍允许验真预览，现有 SEC 原件补全挂牌后可复用，生产匹配规则未改变。
- E07 首轮测试把 Sina 报表币种当成所有字段的单位，快照证明这一断言错误。现在明确测试“金额单位未知、EPS 单位有来源”两种情况，财务数值保持原始十进制与日期。

- Worker/批次/选择/回放只接收验真投影读取函数，投影缺失的查询由源码反控证明没有目录副作用。Worker 关闭资源由工厂装配，调用者不用访问 catalog。
- 自动发现的损坏派生对象此前进入正常重建，若新制品字节相同又被旧对象挡在 outbox。制品 owner 现在可原子恢复同一内容地址，沿用配置的写入资源限额。未改付费原始响应的写入或读取合同。
- 历史强行用当前 context/4 搭配旧模型 /1、/2 的集成测试有三例失败，在未改的 3e6c66366 同样复现。旧协议不能表达新增 support/context-only 语义，模拟还未发模型请求即被拦截。保留语义边界和当前通过的付费恢复用例，历史生成夹具另交父计划维护。

### E01 真实来源复验

| 请求挂牌 | 实际源挂牌 | SHA-256 | 字节 |
|---|---|---|---|
| US:BABA | HK:09988 | 8ab1234844b56a2be8b90d92301d0a46123c8770610e87f9462bb27b0e2b7182 | 4,630,060 |
| US:BILI | HK:09626 | 88623041b7af0e423eb65a984ba34ca7bcba826b737210b062091bf51485bf4d | 2,473,744 |

二者为既有 P2 真实 FY2025 原件。旧隔离试验的 Bilibili FY2022 冻结件未用于这次测试。真实样本仅经公开 query/read 读取。

## 复验入口

- CWP `tools/run_source_system_tests.py --d4-final`，显式选各消费方版本。
- CWP `tests/financial_statements/test_offline_e2e_full.py`，`MB_RF_ROOT`、`MB_FF_ROOT` 指向各自临时安装版本。
- CWP `tests/e2e/test_installed_source_consumers.py`，`MB_DASHBOARD_ROOT`、`MB_STOCKWIKI_ROOT` 指向验收版本。
- CWP `tests/e2e/test_narrative_transport_real_samples.py` 与 `tests/e2e/test_source_version_reader_real_bytes.py` 使用固定已下载文档。
- Dashboard `tests/adapters/cwp_original_stream` 与 `tests/e2e/cwp_original_stream/test_original_stream_e2e.py`，`CWP_OWNER_ROOT` 指向受测 CWP 公开命令版本。

D4 运行前后代码签名一致。已核对并回收本次 CWP 基线、StockWiki、RF、Dashboard 四个测试工作树和四个测试目录，保留分支、用户未提交工作及原始资料。临时技能安装两次检查表明文件无漂移；未写入全局技能、业务资料或下载原件。费用与模型调用为零，模型恢复使用测试替身。RF 独立审查另从正式安装副本复跑缺省复用，并验证配置替换、公开启动和安装零漂移。RF push smoke 12 项通过。远端 CI 完整运行尚未核验。
