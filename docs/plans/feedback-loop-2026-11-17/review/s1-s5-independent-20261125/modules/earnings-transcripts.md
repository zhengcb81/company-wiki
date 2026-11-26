# earnings-transcripts S1–S5 独立复审

**结论。** 真实 CLI 的原语言成功响应、机器用量及同身份冷读通过。父进程被拒绝创建 worker 时，仍会丢失机器响应、用量及故障终态，同时输出未脱敏 traceback 并遗留请求信封。S5 的子进程导入与诊断写失败修复覆盖了已经创建的 worker，父进程启动边界仍有缺口。

## 运行范围

实际工作目录 `C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts`，`main` 与本地 `origin/main` 指向 `7f4c1e7df865581babef3365c36ec763ba71e2d6`。测试使用活动工区源码。已有脏文件为根计划 `findings.md`、`progress.md`、`task_plan.md` 与未跟踪 `.mimosa/`、`.workbuddy-ai/`，相关 Python 源码、测试和 CI 定义无差异。Windows Python 3.13.9，Python 审计钩子阻断连接、DNS 和发送，临时根已清除。真实请求、翻译、外发和费用均为零。CodeGraph 在 ET 工作目录未初始化，本次用源码和子进程验证。发布与远端 CI 结论沿用总控同版台账。 [S5 发布记录](C:/Users/郑曾波/Projects/company-wiki/docs/plans/feedback-loop-2026-11-17/s5-verification-20261125.md:12)

## S1–S5 判定

| 项目 | 状态 | 适用范围 |
| --- | --- | --- |
| S1 | 部分 | S1-04 的 provider 异常类型、原因链和源位置有专门投影，入口保留原业务错误名。子进程 `stderr` 有安全排空和降级标记。父进程 `Popen` 拒绝仍直接输出原异常，见反例。 |
| S2 | 部分 | 正常抓取以同一 run、attempt、step 关联始末、期间、原文引用、用量和产品版本，重投幂等。父进程启动失败只留下 `started`，零请求语义、退出原因与失败终态无法冷读。实际在途 worker 随 CLI 被强停的生命周期未证。 |
| S3 | 部分 | ET 与 FF 的主调用使用公开进程契约。ET 的预算与预检 owner 已公开，兼容名指向同一个实现。翻译兼容门面和历史回放工具仍有具名私有耦合。全仓运行时环未重扫。 |
| S4 | 部分 | S5-09 的 ET 最小日常 CI 已有同版通过台账，覆盖现有导入、冷读、写失败、强停和并发复用用例。CI 未收集父进程 `Popen` 拒绝反例，也没有全仓私有依赖或运行时循环约束。 |
| S5 | 部分 | `7f4c1e7d` 已对齐，子进程诊断回退、manifest 拒写、原子中断和发布延迟已有定向回归。S5-04g 的父进程启动缺口已实证。S5-05 已有轮转实现，错误入口覆盖仍有缺口。ET 无已知需重验的受管安装副本。 |

## 同一真实入口的两条实测

使用 `C:/Miniconda/python.exe -B transcript_tool.py --request-stdin --report-usage`，输入 `earnings-transcript-request/1`，明确 FMP、MSFT、NASDAQ、2026Q3、as-of `2026-09-30`，授权字段与超时合法。父、子进程都加载临时目录的 `sitecustomize.py`。正常组仅替换 worker 的 `requests.Session.get`，返回合成英文 JSON。故障组在 `subprocess.Popen` 的 Python 审计事件中对 `retrieval_worker.py` 抛出带合成错误文本及合成绝对路径的 `PermissionError(13, ...)`，故障点位于操作系统进程创建前。两组各观察到一次启动尝试，网络和翻译探针均为零。 [公开用量契约](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/README.md:414) · [CLI 运行路径](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcript_tool.py:381)

| 观察项 | 正常 `et-independent-success / one / et-audit-success` | 拒绝启动 `et-independent-spawn-denied / one / et-audit-spawn-denied` |
| --- | --- | --- |
| 返回 | 退出 0，stdout 一份 `fetched` JSON，正文仍为合成英文 | 退出 1，stdout 0 字节，stderr 为 42 行 traceback，出现合成异常原文及绝对路径 |
| 用量与临时文件 | stderr 一行 `earnings-retrieval-usage/1`，`usage_complete=true`，1 次合成 GET，862 字节。临时目录清空 | 无机器收据。GET 为零，工作临时目录留有 `request.json`，无 `runtime_errors.log` |
| 原身份 | 首次即发布 1 个 `.ready`。冷读看见 `started` / `finished`，5 个检查项含 `usage-accounting` 和原文引用 | 初次发布 0 个 `.ready`。冷恢复后恰有 1 个，只有 `action-started` 与 `started` 明细 |
| 公开恢复 | 同 ID 两次 `--capabilities` 都退出 0，无新 worker，发布保持 1 个包。两次独立读取内容一致，owner `reconcile` 为 `succeeded / cost_unknown` | 同 ID 相同恢复步骤仅补投开始记录。两次独立读取一致，owner `reconcile` 为 `unconfirmed / cost_unknown`。启动失败和零请求事实丢失 |

两组 F4 版本为 `earnings-transcripts-transcript-tool/1.0.0`，与上文精确 Git SHA 分别记录。owner `reconcile` 通过公开 `tools/feedback_owner.py --db <隔离路径> --sidecar <bundle> reconcile` 读取，两组均未创建数据库。用量计数与账户成本是独立字段。 [产品版本](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcript_tool.py:46) · [公开冷恢复](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcript_tool.py:258) · [owner 冷读](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/tools/feedback_owner.py:297)

## 缺口、根因与后续验收

1. **P1 · 父进程启动失败越过诊断及用量契约。** supervisor 在创建工作目录、写入信封和调用 `Popen` 后才建立 `finish()`。这三处的 I/O 或启动异常无法进入该收敛路径。上层 CLI 只处理 JSON/Unicode 异常，正常终态、机器收据与投递都在其后，故拒绝启动与外力硬停在冷读里同为 `started`。使用 stderr 单 JSON 的 FF 将本次无收据归为未知用量，空 stdout 按当前源码会归为 `provider_result_invalid`，无法承接真实启动错误。后续用同一公开入口验证 `mkdir`、信封写入和 `Popen` 分阶段失败，结构化保存异常类、脱敏原因和源位置，保留统一机器响应及一条用量收据。仅在能确认未派发时记零，在途用量未知继续保留原语义。两次冷读按原运行号得到同一失败终态，获知子进程未创建或确认已退出后回收临时目录。 [父进程启动](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/retrieval_runtime.py:208) · [正常收敛](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/retrieval_runtime.py:263) · [ET wire 与终态](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcript_tool.py:395) · [FF 全 stderr 解析](C:/Users/郑曾波/Projects/filing-fetch/scripts/transcript_tool_transport.py:109) · [FF 空 stdout 归类](C:/Users/郑曾波/Projects/filing-fetch/scripts/transcript_tool_transport.py:770)

2. **P1 · 局部轮转与强停证据仍有边界。** worker 创建成功后有专用 stderr 管道，结构诊断优先，早期导入或 `worker_error.json` 拒写可回退到安全异常类别。S2 回归明确覆盖本地 `logs` 路径被占用时保持单份用量和 F4 已落记录。已有强停回归在 `begin_step` 后等待并硬停父 CLI，再用 `--capabilities` 补投原开始事实，它没有启动 worker。另有源码缺口是 `record_local_failure` 在显式关反馈时直接返回，连本地轮转诊断也停写。`runtime_errors.log` 使用 2 MiB 两份归档，但这只证明已有调用点，`scraper.py` 通用故障分支仍直接打印异常原文并调用 `log.exception`。后续各做一条真实入口反例，确认在途 worker 强停的进程树/临时目录和用量证据，确认反馈关闭或诊断介质故障时本地诊断和主结果的边界。`--report-usage` 的 stderr 继续只有机器收据。 [子进程诊断](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/retrieval_runtime.py:119) · [拒写回归](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/tests/test_s2_worker_bootstrap.py:271) · [强停回归](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/tests/test_f4_ordinary_failures.py:949) · [轮转开关](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcript_feedback.py:1398) · [轮转定义](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/runtime_logging.py:36) · [批量异常分支](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/scraper.py:1789)

3. **P2 · 机器跨仓边界成立，仓内兼容和工程入口仍相互牵连。** FF 将公开 request/1 送 stdin，使用 `--include-source-payload --report-usage` 读取 result/2 与独立用量，当前审查路径无 ET 私有 Python 或 SQLite 依赖。ET worker、API 和预检使用同仓公有函数和 `BudgetSession`，旧 `_BudgetSession` 为同一对象的兼容别名。`common.py` 直接重导 `translator._OpenAITranslator`，`reader.py` 只读入口也导入 `common`，移除私有符号会使其在启动时发生 ImportError。`tools/replay_feedback_case.py` 直接替换 `_fmp_period` 和 `_publish_usage_receipt`，属于在用工程反例，内部改名会先破坏回放。生产 CLI 未暴露这两类故障开关。`transcript_feedback.py` 同时承担诊断、事件映射、文件恢复和投递，当前交付未拆分。后续验证读取入口可独立加载，以及历史反例可经明确测试注入保留旧失败。 [FF 真实入口](C:/Users/郑曾波/Projects/filing-fetch/scripts/transcript_tool_transport.py:693) · [ET 公共预检](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcript_preflight.py:26) · [预算别名](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/retrieval_budget.py:233) · [兼容门面](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/common.py:25) · [reader 导入](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/reader.py:17) · [回放私有注入](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/tools/replay_feedback_case.py:242)

4. **S4/S5 定向验收边界。** 日常 CI 在 `main` push、PR 和手动触发时运行 Ubuntu / Python 3.10 的显式 pytest 白名单。已纳入的测试验证 worker 导入与脱敏诊断、批次 manifest 写失败非零且保留原件、旁路拒写保留业务结果、原子旁路 `KeyboardInterrupt` 传播，以及记下开始后强停父 CLI 的原身份补投。旁路原子函数用 `finally` 清理临时文件，worker 捕获退出类异常时记诊断后立即重抛。新反例应进入相同 CI 节点，用合法启动与模拟拒绝成对验证，并用相同断言复核 Windows。现有隔离测试检查特定导入链，私有翻译门面和回放工具仍缺可执行的结构约束。 [当前 CI 定义](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/.github/workflows/ci.yml:3) · [同版 CI 台账所引结果](https://github.com/zhengcb81/earnings-transcripts/actions/runs/45698502294) · [provider 异常投影](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcript_api.py:809) · [manifest 回归](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/tests/test_batch_runtime.py:1129) · [原子写中断回归](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/tests/test_feedback_observation.py:697) · [worker 重抛](C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/retrieval_worker.py:226)
