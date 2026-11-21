# 运行失败覆盖复验

从 company-wiki 根运行以下命令。路径采用并排检出的 12 个仓库布局。使用装有该模块依赖的 Python。CWP 的探针和测试使用本仓 venv。脚本使用临时数据、受控的本地子进程或环回服务，输出 JSON。它们是本次审计的调查工具，运行不会启动修理或生产调度。探针自身退出 0 表示完成测量，覆盖情况以 JSON 里的业务和冷读结果为准。

| 范围 | 命令 |
|---|---|
| 总控进程、冷读及不可写收件箱 | `.venv/Scripts/python.exe -B docs/plans/feedback-loop-2026-11-17/probes/intake.py` |
| CWP 当前代码 | `.venv/Scripts/python.exe -B docs/plans/feedback-loop-2026-11-17/probes/cwp.py .` |
| CWP 当时实际使用的定时读取代码 | `.venv/Scripts/python.exe -B docs/plans/feedback-loop-2026-11-17/probes/cwp.py .runtime/sr-cwp-1e2a3b0e` |
| IQS | `python -B docs/plans/feedback-loop-2026-11-17/probes/iqs.py ../invest-quick-scan --revision 296ab842`。改用待验收的已提交 revision 可比较同一组案例 |
| StockQA | `python -B docs/plans/feedback-loop-2026-11-17/probes/stockqa.py ../StockQAbyLLM`。指定 `--working-tree` 测快照里的在途变化 |
| filing-fetch | `python -B docs/plans/feedback-loop-2026-11-17/probes/filing_fetch.py ../filing-fetch` |
| revenue-forecast | `python -B docs/plans/feedback-loop-2026-11-17/probes/rf.py ../revenue-forecast`，默认另查本地 F4 固定目录和实际技能，可传 `--runtime`、`--skill` |
| revenue-forecast-audit | `python -B docs/plans/feedback-loop-2026-11-17/probes/audit.py ../revenue-forecast-audit`，也可传实际技能目录 |
| StockWiki | `python -B docs/plans/feedback-loop-2026-11-17/probes/stockwiki.py ../StockWiki` |
| Dashboard | `python -B docs/plans/feedback-loop-2026-11-17/probes/dashboard.py ../investment-dashboard`，需要该仓后端依赖 |
| earnings-transcripts | `python -B docs/plans/feedback-loop-2026-11-17/probes/et.py ../earnings-transcripts/earnings-transcripts` |
| StockInfoDLSimple | `python -B docs/plans/feedback-loop-2026-11-17/probes/sid.py ../StockInfoDLSimple/v2-clean-rewrite` |
| MeetingConverter | `python -B docs/plans/feedback-loop-2026-11-17/probes/mc.py ../MeetingConverter` |
| industry-research | `python -B docs/plans/feedback-loop-2026-11-17/probes/ir.py ../industry-research`，可追加实际安装技能目录比较 |

核对基线发现可用 `python -B -m tools.feedback_loop plan docs/plans/feedback-loop-2026-11-17/issues/failure-coverage-20261121.jsonl`。同一文件传两次，观察身份和数量应相同。该文件记录审计发生，不会重跑发生时的业务。修复后另起 attempt 对比原生失败与 F4 的记录，保留旧观察原判。

每个 owner 的复验至少包含一条应完成的合法请求和一条确实应拒绝的请求。重点检查正常入口能否在没有调用者注入反馈环境变量时保留失败、HTTP 200/进程退出 0 里的部分失败是否被发现、新进程能否从原运行和尝试读回原因、哪些副作用确实发生过。直接取消和受控拒绝可以登记为预期结果。同一问题的多次观察保留各自发生身份。
