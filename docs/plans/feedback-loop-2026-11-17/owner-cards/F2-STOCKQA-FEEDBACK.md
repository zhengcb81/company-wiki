# F2-STOCKQA-FEEDBACK · StockQA 逐题结算与恢复反馈

2026-11-19。发给本仓现有 harness，写入和交接并入它的当前工作线。

| 项目 | 接续信息 |
|---|---|
| Owner | `stockqa` |
| 工作目录 | `C:/Users/郑曾波/Projects/StockQAbyLLM` |
| 已核对的本地状态 | 现有 `codex/qa-content-filter-resolution-01@9be7176`，由该恢复线原 harness 接续。 |
| 本仓计划入口 | 反馈计划在本地 Git 已发布版本，活动分支用 `git show 21d3c99d07888003cd69e26fb4c5e6603f7c15e8:.planning/modularity-closeout-20261111/feedback-20261117.md` 读取。以本仓恢复线当前 PWF 跟进。 |

## 开工顺序

第一步在现有分支用 `git status --short --branch` 查看在途改动。当前 `src/utils/quick_scan_refresh_inspect.py` 和三个定向测试正被原工作线修改。先读公开 `python -B -m src.utils.quick_scan_refresh_inspect_cli --help` 及已存在的离线夹具，确定 ledger 中「已收到、已结算、无可用答案」与「已发送但结果未知」的不同依据。

当前检查器和恢复测试的修改先随原恢复线完成，再由同一 harness 接本卡的写入。期间可先准备隔离数据库、复现预期及回归案例。

保留现有 harness 的工作目录和分支。若它已在所属原工作树施工，以该工作树的当前 HEAD 为实施基线，并在交接记下绝对路径和 SHA。

## 写入范围与接口

- 限写本仓逐题凭证的只读投影、`src/utils/quick_scan_refresh_inspect_cli.py` 及其局部反馈适配器、相关测试和 `skills/repair-stockqa-issue/SKILL.md`。共享检查器及原恢复测试按上面的排队顺序接续。
- 复用 work journal、paid visible journal、checkpoint 和 outbox 的公开事实。观察绑定题、尝试、同一代际和原生结算证据。对已结算无答案、可读答案、发送未知、后到新标签分别报告。费用未知需要用原作业只读对账。
- 真实供应商执行、生产账本和 IQS/Dashboard 归各原负责线。用本仓临时 SQLite 和合成元数据测试。实际新缺陷在现有 PWF 留下发生、根因及负例。

本次观察从真实公开入口产生。可选 `RESEARCH_FEEDBACK_OUT` 给本进程专用 UTF-8 JSONL，`RESEARCH_FEEDBACK_RUN_ID` 和 `RESEARCH_FEEDBACK_ATTEMPT_ID` 给上下文。每行的 `schema_version` 为 `feedback-observation/1`，含字符串 `owner, run_id, attempt_id, step_id, check_id, expected, actual`。保持原尝试稳定标识，真实重试另编号，跨主体及兄弟步骤区分。可选 `evidence_ref` 和 `version` 指向可只读复核的证据。用 `disposition` 区分合法结果 `expected`、可证偏差 `deviation` 和待查状态 `unknown`。输出缺失或写失败时业务仍按原生合同结束。父子用独占输出，凭据、真实正文和物理路径留在原 owner。 [总控观察协议](../interfaces.md)

## 测试

先用本仓固定输入写 RED 和合法对照，再接旁路并比较实际公开输出、作用范围及稳定 ID。所有写测试使用单次专用目录。相关命令如下，新增测试随本卡一起执行并在交接列出。

```powershell
python -B -m pytest -q tests/unit/test_paid_visible_journal.py tests/unit/test_quick_scan_refresh_inspect.py
python -B -m pytest -q tests/unit/test_quick_scan_known_outcome.py -k "unknown_send or settled_completed_physical_outcome"
```

追加公开 inspect 到旁路的定向回归与正常回复对照。确认 ledger 写入和付费调用数保持零增量，缺收据时 lookup 继续 unknown，已有结算但无有效答案不会重新发题。覆盖假零费用、旧代际串号、未识别标签和损坏旁路。

## 独审与交接

1. 在同一最终源码版本完成定向测试后，请一名未参与实现的独立 agent 对照本卡做一次大节点审查。检查任务覆盖、真实入口、在途边界、正常与反例、观测可选性、恢复副作用、隔离清理。逐项修复发现，复测并由审查者核对最终实现 SHA。
2. 在本工作树的 `.planning/modularity-closeout-20261111/F2-STOCKQA-FEEDBACK-handoff.md` 交付。附 base/实现/独审 SHA、实际命令及通过/失败/跳过、审查报告和关闭记录、至少一份本次真实入口产出的脱敏 JSONL、试验目录清理和现存余项。交原题目和尝试、结算和 checkpoint 的逻辑引用、代际、原公开状态、新旧调用计数及费用未知样本。ROOT 用该公开版本确认 IQS 消费与已付结果恢复。
3. 正常提交本仓文件，按本仓已有发布安排交付可读版本。ROOT 按公开观察做跨仓验收。

交接的简短机器摘要可使用下列字段，详细证据放正文。

```json
{"lane":"F2-STOCKQA-FEEDBACK","owner":"stockqa","worktree":"<实际工作目录>","base":"<开工 SHA>","implementation":"<实现 SHA>","reviewed_commit":"<最终独审 SHA>","tests":[{"command":"<实际命令>","result":"<实际结果>"}],"sample_refs":["<脱敏 JSONL>"],"review_ref":"<独审与关闭记录>","cleanup":"<本轮清理结果>","remaining":["<仍待 ROOT 验证范围>"]}
```
