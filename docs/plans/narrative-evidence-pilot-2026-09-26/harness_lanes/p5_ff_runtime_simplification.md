# P5-FF：旧Worker编排退出与真正有界的JSON进程

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

**已交付并验收合入；不要重派。** 原卡为中等代码包，外线交付ab9ce33/code7c6cf48，MAIN修复/验收已合入本地及远端FF main758e8f4，精确CI37385101051全绿；[MAIN验收收据](results/p5_ff_main_acceptance_2026-10-05.json)。下面保留原施工范围和上下文。仅负责filing-fetch，不依赖RF迁移或CWP真实模型结果，SourceRef v2/电话会wire未变。

## 1. 两个实证缺口

2026-10-05实读FF `d4d2fac4c690bfb8b1368d2ca140fd75150fd288`：

1. `scripts/fetch_filing.py`仍有`PausedWorkerScope`、`filing_fetch_pause.refcount/owner`和worker-status/pause/resume编排。CWP旧Worker创建/启动已退役，明确下载不依赖后台状态；FF SKILL仍说明“inert upstream”。这段编排增加进程调用、磁盘状态和门禁，应该整体退出。
2. `_run_company_wiki_json`及`transcript_tool_transport.py`的JSON runner先`subprocess.run(capture_output=True)`后限长；filing runner用`len(str)`对比“byte cap”。32 MiB共享常量存在，但不是读期间硬上限，非ASCII也不是按UTF-8字节计。超时只终止直接child并不能自动证明孙进程/持pipe者已回收。

目标：一个FF仓内有界进程实现，两个调用面复用；在读取时限制stdout/stderr、共享deadline与清理宽限，退出不遗留自己创建的进程/pipe；不写CWP暂停状态。不是重复已完成FF-S3、SourceRef、companion或ET-DEADLINE卡。

## 2. 目录和写集

- 源仓：`C:/Users/郑曾波/Projects/filing-fetch`；fcap和origin/main同`d4d2fac`，tracked干净。未跟踪`config/FMP_API_KEY.txt`是用户凭证，别读、别暂存。
- 新worktree：`C:/Users/郑曾波/Projects/cwp-lanes-20261005/ff-runtime-cleanup`。
- 分支`codex/p5-ff-runtime-cleanup`，基于最新已发布origin/main。

```powershell
git -C 'C:/Users/郑曾波/Projects/filing-fetch' worktree add -b codex/p5-ff-runtime-cleanup 'C:/Users/郑曾波/Projects/cwp-lanes-20261005/ff-runtime-cleanup' origin/main
```

先核目标未占用；存在时检查身份/status后复用本卡目录或新兄弟目录，不reset原树/未知WIP，不改global Git配置。

允许：`scripts/fetch_filing.py`、`transcript_tool_transport.py`、新`ff_process_transport.py`或同用途薄模块、相关测试、SKILL/CHANGELOG、本卡PWF与handoff。不改wire schema/golden字段、source/candidate validator投资语义、provider路由、CWP/ET/RF/StockWiki/Dayu、真实配置/原文/运行数据、全局安装目录或CI矩阵。

独立PWF放`.planning/p5-ff-runtime-cleanup/`。本仓历史合同只保真实产品责任；旧卡Git工作树写集检查不成为永久Unit或阻挡用户WIP。

## 3. 兼容接口与正确性

- `resolve_filing`当前签名与`--no-pause-worker`/worker超时参数若有调用者，接受为兼容no-op并更新help；不再探测、pause/resume或写refcount。不要加另一开关控制是否启用旧scope。
- **v2 CLI已自动选SourceRef**，本卡不重复改默认route。`--source-ref-v2`继续接受；v1显式flag与现有legacy candidate shape保持到MAIN统一迁caller。RF新卡向当前FF传该flag即可独立验收。
- SourceRef `2.0`、FF现有request/response、ET request `/1`/payload `/2`、CWP transcript import request `/2`/response `/3`不变。市场、证券、FY/Q、语言、原JSON与canonical text各自hash规则不变。
- stats按真实上游调用递增；删掉Worker调用后计数减少，不能填虚拟calls维持旧数字。download outcome只取真实envelope，失败仍保留已发生计数；reuse不触provider。
- stdout按实际bytes在读期间计数，超过当前`MAX_JSON_OUTPUT_BYTES=32*1024*1024`就停止，不能读完才检查；stderr也必须有有限cap并并发读取，原始stderr/凭证不回显。
- 共用请求剩余deadline；ET已有3秒外层清理宽限继续正确，不把有限清理时间当新下载额度，也不让每个child得到全新deadline。UTF-8严格解码、JSON object/退出/schema仍校验。
- Windows用可回收自建进程树的已有仓内模式或明确OS原语；POSIX用独立session/group。只终止本调用创建的进程，不扫描/杀其他用户程序；处理子退出孙持pipe，不遗留后台读取线程。

公用进程层只负责bytes/时间/exit/cleanup，不解释证券、source、companion。各调用者仍负责其原JSON/错误分类。优先复用本仓已有可靠实现；需抽取时一次集中到新薄模块，不把代码复制到多个大helper，不跨仓导入ET内部Python。

## 4. TDD与施工顺序

1. 读本仓PWF/最近S3收据及两个runner、旧scope调用点。列实际旧Worker调用/写盘位置；核没有活动producer重新需要它。
2. RED先框住：任何resolve/reuse/download路径都不调用worker-*或写pause文件；真实child持续喷stdout/stderr在cap/deadline前被停；非ASCII计bytes；child退出后孙持pipe不会无限等。
3. 删除scope/refcount/owner/PID维护及调用，签名/flag薄兼容。旧scope专属测试迁为“无旧调用/写盘”行为断言，不整文件删除provider/hash/失败计数测试。
4. 实现一个有界进程层，filing与transcript runner复用；保留错误分类及统计。无自动扩大cap、无限retry、secret日志或fallback。现有有限catalog busy重试共用剩余deadline。
5. 集中离线E2E：FF公开CLI→真实隔离CWP的reuse与fake-provider受限download、FF→ET→CWP companion wire；验证旧Worker0调用/0写盘、source hash与计数、重复0provider、超时/overflow清理。只在本包隔离根跑。
6. 节点责任测试和既有快速发布门通过后提交，推自己的codex分支；MAIN后续合入与三仓离线汇合。不要安装全局技能或合main。

## 5. 测试包

新增建议：`tests/test_p5_process_transport.py`、`tests/test_p5_worker_scope_retirement.py`、`e2e/test_p5_ff_process_runtime.py`。

复用并更新有变化的责任：`tests/test_fetch_filing.py`、`test_source_ref_v2.py`、`test_ff_v2_contract.py`、`test_transcript_companion.py`、`test_transcript_companion_transport.py`、`test_s3_single_request_limits.py`、`e2e/test_source_ref_v2_cli.py`及现有golden验证。先相关小包，再节点一次既有门；不新增每commit全仓测试。

真实进程负例使用短本地Python child，不依赖网络速度或sleep竞赛：父/孙输出/退出信号可控，带外部watchdog。测返回elapsed、cap处读数、自己启动的PID/pipe退出和随后测试目录可删；不仅mock超时异常。不把POSIX恶意setsid逃逸等未实现能力伪称已覆盖。

真实原文E2E可只读复制CWP中微2025年报（SHA `d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5`）到隔离catalog，元数据fixture标注。companion使用现有ET CLI fake-provider及goldens，不接FMP真实HTTP，不读key、不收费、不翻译。

运行前记录独立短测试根快照，finally关闭连接/pipe、回收本卡创建的进程并恢复原样；临时raw、DB/WAL/cache、fake child与下载结果结束删。报告保存在根外；生产配置/raw/owner文件保持SHA一致。

## 6. 大节点完成条件

- 0 worker-status/pause/resume调用、0 pause refcount/owner写入；源码旧编排退出，原参数兼容且不新增双门。
- 两个runner共用实际读期间bytes/deadline上限；stderr同时读且有界，UTF-8 byte cap正确，overflow/timeout具名失败、自建process/pipe回收。
- 既有wire/golden、provider/identity/period/hash/as-of与计数保持真实；跨仓离线链和相关回归绿。
- 0外网/真实下载/LLM、原件及配置未改、测试目录恢复；正常提交不bypass hooks。

## 7. 交接

提交`docs/implementation/handoffs/P5-FF/HANDOFF.md`与`handoff.json`，遵循[统一格式](p5_parallel_packages_2026-10-05.md#统一交接格式)。列旧scope删除路径、兼容参数、实际调用减少、两runner公用模块、cap/elapsed/process清理指标、golden版本/SHA、完整可运行命令、fixture原文SHA、producer/ET固定HEAD及清根前后摘要。

不要交一份“理论上subprocess timeout会清理”的结论。现有32MiB cap和3秒ET宽限是兼容约束；任何必要变化先保持原wire并在交接明确影响，不去其他仓补实现。
