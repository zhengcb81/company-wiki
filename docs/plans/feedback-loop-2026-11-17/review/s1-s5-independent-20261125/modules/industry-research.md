# industry-research 独立复审

2026-11-25。实际 F4 检出 `C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime`，`HEAD=42c2333062faf256dcd64fd9563836615b303c5d`，跟踪和未跟踪状态均干净，本机 `origin/main` 引用包含该提交。在 Windows Python 3.13.9 下运行实际 CLI、仓内回归、本机 HTTP 替身及新进程回读。夹具使用独占临时根，真实供应商请求、新费用和生产写入均为零。四个逻辑技能入口的受管文件由总控复验为零差异。 [总控部署证据](../findings.md) · [S5 发布台账](../../../s5-verification-20261125.md)

## 五项判定

| 项目 | 状态及范围 |
|---|---|
| S1 | **不适用。** IR 无本仓 S1 止血卡。后续 S2 DeepSeek 边界和 S5 重试补修已验证对应响应、退出及脱敏行为。DeepSeek 当前 CLI 保持原有人读 stdout，成功框架由 JSON 文件交付。快筛捕获外部 CLI 的 stdout 与 stderr，结果保留两者尾摘，非零退出可另留脱敏 stderr 引用。 [DeepSeek](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/deepseek_client.py:712>) · [快筛运输](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/quick_scan_client.py:998>) |
| S2 | **部分。** 缺报告材料、坏快筛配置和模型已响应失败均可从原尝试冷读。无效报告日期的拒绝保留原运行号和 `SystemExit → ValueError`。正常模型和普通报告成功缺持久的原运行起止与依赖效果记录。常规错误日志的轮转阈值为 2 MiB，保留一份备档。进入失败处理时才写时间，详情无稳定输入引用和实际代码版本。普通异常的旁路全失有 stderr 提示，快筛内容偏差的原生投递全失仍可静默，见下方实测。强停后补投和已接收模型结果的费用冷查未独立复验。 [入口包装和失败日志](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/native_feedback.py:142>) |
| S3 | **部分。** IR 经 `stockwiki.quick_scan_query_v2_cli` 消费公开 facts 协议，相关路径中未见对 StockWiki 私表或内部 Python 符号的读取。普通报告仅消费框架、问题、公司三个本地 JSON。快筛栏目由单独命令可选插入，两者共用 Markdown 转义和原子写入。当前纯文件 `render-section`、`audit-section` 仍先构造完整 `QuickScanClient`，要求用于 subprocess 的 `iqs_code_root` 字段，即使输入、输出和 owner 路径防护信息齐全。F4 owner 冷查、纠正也整体加载同一 2,820 行快筛模块来获得栏目函数。应独立验收栏目处理可只装载本地文件职责，保持消费方和 owner 根的路径保护。 [公开端口](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/quick_scan_client.py:998>) · [统一客户端构造](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/quick_scan_client.py:2747>) · [根参数校验](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/quick_scan_client.py:979>) · [F4 owner 依赖](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/feedback_owner.py:10>) · [基础报告](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/report_generator.py:642>) |
| S4 | **部分。** 当前提交的工作流由 push、PR、手动调度触发，Ubuntu 上使用 Python 3.12，四个测试文件在本机按相同选择本地收集 47 项。覆盖模型已响应、原生普通失败和报告栏目等行为。`test_report_generator.py` 中的描述符复用回归未入此清单，内容观察默认出口失败也无对照；现有检查无法拦截本报告反例。私有远端 CI 执行结果未证。 [工作流](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/.github/workflows/owner-contracts.yml:3>) · [描述符复用用例](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tests/test_report_generator.py:737>) |
| S5 | **部分。** S5-04e 定向行为已验，S5-10 F4 检出和总控受管安装对齐已验，S5-09 最小工作流已落盘。S5-05 已覆盖普通报告、快筛和模型异常的本地轮转；本报告实证快筛内容偏差旁路以及正常生命周期仍有缺口。 [本仓 S5 记录](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/docs/plans/s5-feedback-20261125.md>) |

## 定向复验

从实际 F4 检出运行 6 项定向 pytest，全部通过。`DeepSeekBoundary` 的四项使用真实 CLI 和仅允许环回的 HTTP 替身。正常 HTTP 200 一次请求并生成框架 JSON；坏 JSON 或收到 200 响应头后截断正文，均退出 1，恰好一次请求且零等待。新进程按原 run、attempt、step 回读 `invalid_response/JSONDecodeError` 或 `response_unreadable`，响应正文与凭据无泄露。三次 429 只安排 5、10 秒两次等待，末次退出 1。其余两项核对缺材料、坏配置的冷读以及普通报告观察目录被文件占用时，原退出 1、轮转日志和 stderr 提示同时保留。 [模型定向测试](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tests/test_deepseek_boundary.py:246>) · [坏 JSON](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tests/test_deepseek_boundary.py:325>) · [截断正文](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tests/test_deepseek_boundary.py:374>) · [普通失败测试](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tests/test_native_failure_feedback.py:15>) · [旁路失败测试](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tests/test_native_failure_feedback.py:67>)

实现使用 `requests.post(..., stream=True)` 先获得响应头，`_received_content` 把坏 JSON、结构错误及读取正文的请求异常都转为终态 `DeepSeekRequestError`。未取得响应头时的超时和传输异常仍可依原规则重试，原外部执行与计费可能未知。普通失败 F4 观察只有 `details_ref`，本仓 `reconcile` 需要可核查 `evidence_ref` 才给出 `cost_unknown` 收据，单靠 HTTP 状态无法结算用量。 [请求边界](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/deepseek_client.py:55>) · [发送及重试](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/deepseek_client.py:98>) · [原观察核对](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/feedback_owner.py:102>)

另用 `tests/fixtures/report_generator` 的三份 `*_special.json` 运行普通报告。`--date 2026-01-01` 退出 0，Markdown 生成，按 `report-ok/attempt-1` 冷读到的运行记录为零。相同输入仅将日期改为 `bad-date`，退出 2，报告未创建，原 `report-refused/attempt-1/publish-report` 可从本地详情冷读到 `SystemExit` 及 `ValueError` 的脱敏原因。此项验证直接 CLI 的实际文件记录，未调度生产 F4。 [报告参数拒绝](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/report_generator.py:699>) · [入口身份与失败分支](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/native_feedback.py:218>)

## IR-01 · 快筛内容偏差投递故障无诊断（P1）

按本仓 `make_summary` 形状生成同一合成 query、snapshot、store 的两份摘要，旧摘要 `availability.status=empty`，权威摘要 `unavailable`。将 `IR_FEEDBACK_WORK_ROOT` 指向临时根，显式设 `RESEARCH_FEEDBACK_RUN_ID=ir-review-audit`、`RESEARCH_FEEDBACK_ATTEMPT_ID=attempt-1`。清除其它 `RESEARCH_FEEDBACK_*` 和实际环境里的 `IQS_QUICK_SCAN_*`。用只包含合成 owner、IQS 和 capture 路径的 `quick.json`，并把 `python_executable` 指向不存在的临时路径。两组都从各自临时根运行实际检出脚本，先用 `render-section --input old.json --output section.md` 生成旧栏目，仅在故障组把 `.feedback/observations` 置为普通文件，然后运行审计。 [摘要夹具形状](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tests/test_feedback_owner.py:55>) · [审计入口](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/quick_scan_client.py:2794>)

```text
python -B -X utf8 "C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/quick_scan_client.py" --config quick.json audit-section --input truth.json --section section.md --output audit.json
```

| 场景 | 退出 / stdout / stderr | `audit.json` 中偏差 | 新进程按 `.ready` 和公开 `read_observations` 冷读 |
|---|---|---|---|
| 目录可用 | `0 / 0 B / 0 B` | `coverage-projection`，期望 `unavailable`，实际 `complete_no_match` | 同一 run/attempt 有 1 条偏差 |
| 路径被文件占用 | `0 / 0 B / 0 B` | 同样的 `coverage-projection` | 0 条偏差，也无 `runtime-errors.jsonl` |

业务审计已正确识别覆盖状态错误，指定输出仍可读。自然发生的观察出口 I/O 故障让依赖 sidecar 的后续分诊完全失去原事件。`ObservationSink.emit` 在默认出口直接返回 `publish_native` 的布尔值，`publish_native` 捕获 `OSError` 后返回 `False` 且无告警，调用方 `_emit_findings` 忽略返回值。S5 的 `_warn_delivery` 在普通 `failure()` 路径中，对此路径不起作用。 [观察分流](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/feedback_observation.py:148>) · [原生投递失败](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/native_feedback.py:244>) · [栏目观察调用方](<C:/Users/郑曾波/Projects/industry-research/.worktrees/f4-runtime/tools/quick_scan_client.py:2506>)

验收应以该故障组为回归。业务退出和审计文件内容须与对照一致。任一可用诊断介质应留下原 run、attempt、step、检查和投递状态，出口全失时 stderr 应提供带原身份的脱敏提示。恢复出口后由新进程按原身份补投一次，冷读仅得一条相同偏差，新增采集、供应商请求和费用均为零。正常 CLI 的起止与关键步骤在本地轮转日志另以原身份验收，F4 继续消费偏差观察。
