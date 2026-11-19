# F2-IQS-FEEDBACK · IQS 逐题回执与混尺度投影反馈

2026-11-19。发给本仓现有 harness，写入和交接并入它的当前工作线。

| 项目 | 接续信息 |
|---|---|
| Owner | `invest-quick-scan` |
| 工作目录 | `C:/Users/郑曾波/Projects/invest-quick-scan` |
| 已核对的本地状态 | 现有 `codex/iqs-manifest-delivery-01@3dde7fa`。在 MANIFEST-DELIVERY-01 的原 harness 接续。 |
| 本仓计划入口 | `C:/Users/郑曾波/Projects/invest-quick-scan/docs/implementation/parallel-lanes/packages/2026-11-11-modularity-closeout/feedback-20261117.md`。 |

## 开工顺序

第一步读本仓 `docs/implementation/parallel-lanes/packages/2026-11-15-iqs-manifest-delivery-01/STATUS.md`，核对当前 result 发布与最终一题的处置。取该工作树里保存的逐题回执和冻结问卷夹具，在离线的公开 result/history 入口先复现「部分题完成或混尺度结果被误报为完整」。用同一批输入记录原 scan/job、题号、尺度和公开结果版本。

先准备样本、预期和只读检查。与现有线共同涉及问卷冻结、正式登记、outbox 或 `dashboard_company_projection` 时，等该项在 MANIFEST-DELIVERY-01 稳定后由同一个 harness 接续。

保留现有 harness 的工作目录和分支。若它已在所属原工作树施工，以该工作树的当前 HEAD 为实施基线，并在交接记下绝对路径和 SHA。

## 写入范围与接口

- 限 IQS 的 result/history 读投影、逐题状态反馈、必要的公开 adapter 旁路及定向测试。生产实现从 `scripts/iqs_scan/workbench/dashboard_company_projection.py`、`scripts/iqs_scan/questions/frozen_release_projection.py` 和 `scripts/iqs_scan/tools/scan_result_check.py` 追溯。保留 `scripts/dashboard_company_projection.py` 的兼容入口。既有 manifest 登记和正式发布改动使用原工作线。当前投影通过时，向临时公开响应注入遗漏题或缺组来验证反馈。
- 输入使用 StockWiki membership/assessment 和 StockQA 的公开 DTO 或现有回执夹具。本卡区分未运行、受控过滤／截断、已结算未保存和可用完成；保留各组原尺度。35/36 等实际部分完成按 partial 并保留缺项。已确认的合法空结果保留其原因。
- 实际偏差定位到第一次有证据的 IQS 投影环节，必要时更新本仓 `skills/repair-iqs-issue/SKILL.md` 和当前 PWF。测试使用留存回执和本机 fixture，真实逐题发送由原 owner 的计划管理。

本次观察从真实公开入口产生。可选 `RESEARCH_FEEDBACK_OUT` 给本进程专用 UTF-8 JSONL，`RESEARCH_FEEDBACK_RUN_ID` 和 `RESEARCH_FEEDBACK_ATTEMPT_ID` 给上下文。每行的 `schema_version` 为 `feedback-observation/1`，含字符串 `owner, run_id, attempt_id, step_id, check_id, expected, actual`。保持原尝试稳定标识，真实重试另编号，跨主体及兄弟步骤区分。可选 `evidence_ref` 和 `version` 指向可只读复核的证据。用 `disposition` 区分合法结果 `expected`、可证偏差 `deviation` 和待查状态 `unknown`。输出缺失或写失败时业务仍按原生合同结束。父子用独占输出，凭据、真实正文和物理路径留在原 owner。 [总控观察协议](../interfaces.md)

## 测试

先用本仓固定输入写 RED 和合法对照，再接旁路并比较实际公开输出、作用范围及稳定 ID。所有写测试使用单次专用目录。相关命令如下，新增测试随本卡一起执行并在交接列出。

```powershell
python -B -m pytest -q tests/test_company_assessment_v2_projection.py tests/test_dashboard_company_result.py tests/test_scan_result_check.py
```

追加新反馈回归。混尺度两个不同组、单尺度合法、题目乱序、partial、已结算后中断、缺正式登记各有对照。用同一个公开结果比对分组、完成范围和终态；重复读取既有收据只增加观察查询，供应商发送、费用和业务写入增量为零。

## 独审与交接

1. 在同一最终源码版本完成定向测试后，请一名未参与实现的独立 agent 对照本卡做一次大节点审查。检查任务覆盖、真实入口、在途边界、正常与反例、观测可选性、恢复副作用、隔离清理。逐项修复发现，复测并由审查者核对最终实现 SHA。
2. 在本工作树的 `docs/implementation/parallel-lanes/packages/2026-11-11-modularity-closeout/F2-IQS-FEEDBACK-handoff.md` 交付。附 base/实现/独审 SHA、实际命令及通过/失败/跳过、审查报告和关闭记录、至少一份本次真实入口产出的脱敏 JSONL、试验目录清理和现存余项。交 `scan/job/attempt`、问卷版本、题和尺度组引用、公开 result/release ID、正反例和真实调用计数。ROOT 用该公开版本经 Dashboard 的消费入口复验。
3. 正常提交本仓文件，按本仓已有发布安排交付可读版本。ROOT 按公开观察做跨仓验收。

交接的简短机器摘要可使用下列字段，详细证据放正文。

```json
{"lane":"F2-IQS-FEEDBACK","owner":"invest-quick-scan","worktree":"<实际工作目录>","base":"<开工 SHA>","implementation":"<实现 SHA>","reviewed_commit":"<最终独审 SHA>","tests":[{"command":"<实际命令>","result":"<实际结果>"}],"sample_refs":["<脱敏 JSONL>"],"review_ref":"<独审与关闭记录>","cleanup":"<本轮清理结果>","remaining":["<仍待 ROOT 验证范围>"]}
```
