# F2 首批三卡签收 · 2026-11-18

三个 owner 的本仓实现、修理技能、恢复指引和公开观察通过独审及离线组合复验。下表的 Git SHA 为实际 `git ls-remote` 确认的发布版本；原提交、独审核对的源文件及测试细目见各仓交接。各仓只写自己的仓库，ROOT 消费独占 sidecar 和业务公开结果。保留原有工作区的未跟踪资料。

| 卡 | 远端发布 | 复验和直接修复 |
|---|---|---|
| FB-ET · [本仓交接](../../../../earnings-transcripts/earnings-transcripts/docs/plans/feedback-loop-2026-11-17/handoff.md) | `main@6b512daddc7e739351d10fec29442784b10dbcd6` | **737 项、10 份原 golden**通过。保留原取用与反馈代码。旧测试把损坏的可选收据当成拦截，现验证只作诊断以及真实的 TXT 字节冲突仍拒绝。真实 CLI 前置拒绝有且只有一条终态用量收据，确认为 0 请求；中断仍保留未知。 |
| FB-SID · [本仓交接](../../../../StockInfoDLSimple/v2-clean-rewrite/docs/plans/feedback-loop-2026-11-17/handoff.md) | `v2-clean-rewrite@4796a871dfbb8d9cb06efd07f2b9f77a3fd86f59` | **79 项通过**，含四个 CWP 路由用例。最小包包含反馈依赖；启用、关闭、不可写诊断都不破坏业务协议。用公开请求内容给同轮不同期次分别编号，开始、预算、终态分不同检查；请求重投复用原身份。隔离本机旧证券缓存，原验真和限额断言未撤销。 |
| FB-IR · [本仓交接](../../../../industry-research/.planning/modularity-closeout-20261111/feedback-handoff.md) | `main@6f938b49d7cfc17b600abbc330fe800a0094d22f` | 全量 **285 项执行，283 通过、2 外部向量跳过**。按实际落盘栏目检查，保留原报告，能识别「数据不可用」错报为「完整零命中」。不同查询和渲染步骤不串号；子进程不写父观察，观察计算和写入不阻断报告。 |

## ROOT 组合与回放

- 以当前实际 CLI 及受控传输取样。SID 用已存 CNINFO 响应复现 FY2023、FY2024 及同一 FY2024 键重排；每期各保留开始、身份和预算三条。另验发现、暂存 PDF 字节 SHA、原生预算拒绝；SID 的 CWP 路由读取 `ce89127b6ba1878935e2dd1e17b065e4153c88af` 导出的生产包与干净最小 SID 运行包。旧工作区 org-id 缓存不参与夹具。
- ET 用 `tools/replay_feedback_case.py --case fmp-entitlement-402` 和 `--case fmp-worker-aborted` 产出观察；`transcript_tool.py --request-stdin --operation discover --include-source-payload --report-usage` 给出 `usage_complete=true`、`requests_used=0`、`response_bytes_used=0` 的单一收据。filing-fetch 本仓的 `tests/test_et_s0b_contract.py`、`tests/test_transcript_companion_transport.py` 共 **42 项通过**，其中包括用量出错的回退与不重复调用。
- IR 的 `tools/quick_scan_client.py audit-section` 用权威的 unavailable 摘要复查历史栏目，实际输入的旧报告原字节不变，只记录 `coverage-state-lost`。独审还注入编号计算失败，渲染和审计的正常产物字节相同。
- ROOT 用 `python -B -m tools.feedback_loop plan` 导入九份原始侧车（含一份同请求重投），再传两遍同样文件。两次输出一致：**27 条唯一观察**（SID 15、ET 10、IR 2），其中 24 条符合预期、2 条未知、1 条受控偏差，0 条解析、身份冲突或读文件诊断。未启动修理 agent、下载或收费调用。全部操作临时目录已清理；只保留本仓样本和验收结果。

## 接续边界

首批三卡可从各自主线接续。FF/RF/Audit 及其他 owner 按[分工](dispatch.md)继续；F4 仍需用宿主验证自动分诊修理、消费方回告，以及强制终止只有开始记录时按原生作业对账。缺终态不会据此重派下载。W12 与固定公司池的启停、预算和正式业务验收仍按业务主线。
