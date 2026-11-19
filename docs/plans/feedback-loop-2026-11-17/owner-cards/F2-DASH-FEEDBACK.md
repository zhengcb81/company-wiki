# F2-DASH-FEEDBACK · Dashboard 公开响应与页面反馈

2026-11-19。发给本仓现有 harness，写入和交接并入它的当前工作线。

| 项目 | 接续信息 |
|---|---|
| Owner | `investment-dashboard` |
| 工作目录 | `C:/Users/郑曾波/Projects/investment-dashboard` |
| 已核对的本地状态 | 主工区 `main@57e97d2`。由 D00 在原 M6/IQS 负责线接续。 |
| 本仓计划入口 | `C:/Users/郑曾波/Projects/investment-dashboard/.planning/unified-dashboard-2026-10-26/START_HERE.md`、同目录 `feedback-20261117.md`，再读 `modules/m6-quickscan/task_plan.md`。 |

## 开工顺序

第一步读 D00 的 M6 与 BFF 责任分配，在现有 harness 核对未提交的 FF owner 交接与当前页面写入范围。用受控的 IQS 公司结果 fixture 通过实际 adapter 读取，列出结果组、期间、缺失原因和历史版本的预期。用 Dashboard 的公开结果对照页面显示，先复现一次「owner 给了多个尺度组，但页面丢组或误报完整」。

D00–D06 的同文件改动由当前维护者按原顺序接续。E14 按原暂停状态管理，本卡的离线 M6 夹具可独立运行。现有 FF owner 交接文件属于原任务。

保留现有 harness 的工作目录和分支。若它已在所属原工作树施工，以该工作树的当前 HEAD 为实施基线，并在交接记下绝对路径和 SHA。

## 写入范围与接口

- 生产写入限定 `backend/dashboard/adapters/iqs/quickscan.py` 和 `apps/web/src/features/quickscan/` 的 M6 范围，另写本卡关联测试及本仓 PWF。M0 的 `_shared.py`、共享 transport 和 verify 由原线维护。若复现定位在 owner DTO，交最小受控 DTO 和公开引用给该 owner。当前 V2 投影正确时先用临时响应注入缺组验证旁路。
- 反馈区分加载、旧缓存、诚实缺失、部分结果、多个分组和所选历史版本。BFF 与浏览器各记录一个可复验的定位，通过相同 result/version 和挂牌上下文绑定。浏览只读，对账用原作业读取。
- 由 D00 在本仓维护最小 `skills/repair-dashboard-issue/SKILL.md` 与本仓问题卡。读稳定 DTO，生产名单、下载、研究发布及费用账走各原 owner。

本次观察从真实公开入口产生。可选 `RESEARCH_FEEDBACK_OUT` 给本进程专用 UTF-8 JSONL，`RESEARCH_FEEDBACK_RUN_ID` 和 `RESEARCH_FEEDBACK_ATTEMPT_ID` 给上下文。每行的 `schema_version` 为 `feedback-observation/1`，含字符串 `owner, run_id, attempt_id, step_id, check_id, expected, actual`。保持原尝试稳定标识，真实重试另编号，跨主体及兄弟步骤区分。可选 `evidence_ref` 和 `version` 指向可只读复核的证据。用 `disposition` 区分合法结果 `expected`、可证偏差 `deviation` 和待查状态 `unknown`。输出缺失或写失败时业务仍按原生合同结束。父子用独占输出，凭据、真实正文和物理路径留在原 owner。 [总控观察协议](../interfaces.md)

## 测试

先用本仓固定输入写 RED 和合法对照，再接旁路并比较实际公开输出、作用范围及稳定 ID。所有写测试使用单次专用目录。相关命令如下，新增测试随本卡一起执行并在交接列出。

```powershell
python -B -m pytest -q tests/adapters/b03_company_result/test_iqs_company_result.py tests/unit/m6-quickscan/test_quickscan_projection.py
```

追加新反馈回归，覆盖 v1/v2、合法 absent、单尺度、多尺度、partial、切历史版本。触及 UI 时按 `tests/e2e/m6-quickscan/README.md` 用合成后端和 Chromium 新开独占测试目录，记录实际路由、页面结果及运行范围。受控 UI 与真实 owner 的观测分别交付；复验后只清理该次资源。

## 独审与交接

1. 在同一最终源码版本完成定向测试后，请一名未参与实现的独立 agent 对照本卡做一次大节点审查。检查任务覆盖、真实入口、在途边界、正常与反例、观测可选性、恢复副作用、隔离清理。逐项修复发现，复测并由审查者核对最终实现 SHA。
2. 在本工作树的 `.planning/unified-dashboard-2026-10-26/F2-DASH-FEEDBACK-handoff.md` 交付。附 base/实现/独审 SHA、实际命令及通过/失败/跳过、审查报告和关闭记录、至少一份本次真实入口产出的脱敏 JSONL、试验目录清理和现存余项。交用户步骤、同一次公开 result ID、BFF 回执和组件定位、正常和错误展示的断言及证据。页面变化另附真实浏览器复验；ROOT 接口验收按 owner 版本配对。
3. 正常提交本仓文件，按本仓已有发布安排交付可读版本。ROOT 按公开观察做跨仓验收。

交接的简短机器摘要可使用下列字段，详细证据放正文。

```json
{"lane":"F2-DASH-FEEDBACK","owner":"investment-dashboard","worktree":"<实际工作目录>","base":"<开工 SHA>","implementation":"<实现 SHA>","reviewed_commit":"<最终独审 SHA>","tests":[{"command":"<实际命令>","result":"<实际结果>"}],"sample_refs":["<脱敏 JSONL>"],"review_ref":"<独审与关闭记录>","cleanup":"<本轮清理结果>","remaining":["<仍待 ROOT 验证范围>"]}
```
