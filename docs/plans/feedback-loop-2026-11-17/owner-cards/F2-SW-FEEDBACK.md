# F2-SW-FEEDBACK · StockWiki 研究主体与来源关联反馈

2026-11-19。发给本仓现有 harness，写入和交接并入它的当前工作线。

| 项目 | 接续信息 |
|---|---|
| Owner | `stockwiki` |
| 工作目录 | `C:/Users/郑曾波/Projects/StockWiki` |
| 已核对的本地状态 | 主工区 `master@246910d`。由当前研究 owner 在已有施工分支接续。 |
| 本仓计划入口 | `C:/Users/郑曾波/Projects/StockWiki/.planning/modularity-closeout-20261111/feedback-20261117.md`。一并对照本仓现有 assessment lineage 和 Dashboard owner 改进计划。 |

## 开工顺序

第一步在当前工作树用 `git status --short --branch` 与本仓 PWF 核对身份桥、正式发布、研究来源关联正在由谁维护。先只读使用当前仓的固定公开结果和测试夹具，选一个已发布的 `entity/result/release`，核对两个证券挂牌与对应 SourceRef 的关系。用临时事实库运行 `python -B dashboard_company_assessment_cli.py history --root <隔离库> --entity <测试实体> --limit 2 --offset 0`，记下预期分组与实际回执。现有投影已正确时，用临时夹具注入缺组或缺来源，验证反馈可以识别该反例。

能独立做的离线对照可以先在现有 harness 推进。任何修改到身份桥、发布权威或 source-link 读写入口的工作，排在本仓已有研究和 Dashboard owner 施工对同一入口完成之后，由同一个 harness 接续。

保留现有 harness 的工作目录和分支。若它已在所属原工作树施工，以该工作树的当前 HEAD 为实施基线，并在交接记下绝对路径和 SHA。

## 写入范围与接口

- 只写 StockWiki 的评估读取反馈、来源关联的只读投影、局部旁路及相应测试。可从 `dashboard_company_assessment_cli.py`、`stockwiki/public_company_assessments.py` 和现有 source-link 公开入口追溯。需要改身份桥或正式 writer 时先纳入现有 owner 施工顺序。
- 记录原实体、挂牌关系、as-of、result/release 与 SourceRef，可区分已发布、缺来源绑定、诚实 absent、身份歧义、错主体与版本串线。缺失在源头时作为资料缺口，StockWiki 已有且公开结果丢组或丢来源时才记本仓偏差。下游显示错误交消费方。
- 写本仓 `skills/repair-stockwiki-issue/SKILL.md` 与当前 PWF；实际可复现的缺陷在原 PWF 下登记。业务查询只读，生产数据库、名单、既有发布物及邻仓由原负责线管理。

本次观察从真实公开入口产生。可选 `RESEARCH_FEEDBACK_OUT` 给本进程专用 UTF-8 JSONL，`RESEARCH_FEEDBACK_RUN_ID` 和 `RESEARCH_FEEDBACK_ATTEMPT_ID` 给上下文。每行的 `schema_version` 为 `feedback-observation/1`，含字符串 `owner, run_id, attempt_id, step_id, check_id, expected, actual`。保持原尝试稳定标识，真实重试另编号，跨主体及兄弟步骤区分。可选 `evidence_ref` 和 `version` 指向可只读复核的证据。用 `disposition` 区分合法结果 `expected`、可证偏差 `deviation` 和待查状态 `unknown`。输出缺失或写失败时业务仍按原生合同结束。父子用独占输出，凭据、真实正文和物理路径留在原 owner。 [总控观察协议](../interfaces.md)

## 测试

先用本仓固定输入写 RED 和合法对照，再接旁路并比较实际公开输出、作用范围及稳定 ID。所有写测试使用单次专用目录。相关命令如下，新增测试随本卡一起执行并在交接列出。

```powershell
python -B -m pytest -q tests/test_public_company_assessments.py tests/test_dashboard_identity_bridge.py tests/test_dashboard_research_source_link.py
```

追加新反馈回归。用公开 read/history 走单尺度、混尺度 V2、双挂牌同一主体、另一个主体的合法空结果、缺来源绑定和串错版本。对比业务回执字段和 SQLite 行内容在调用前后相同，检查乱序、重复投递和旁路写失败。用忠实的证据分别验证「无绑定」与「发布投影丢绑定」。

## 独审与交接

1. 在同一最终源码版本完成定向测试后，请一名未参与实现的独立 agent 对照本卡做一次大节点审查。检查任务覆盖、真实入口、在途边界、正常与反例、观测可选性、恢复副作用、隔离清理。逐项修复发现，复测并由审查者核对最终实现 SHA。
2. 在本工作树的 `.planning/modularity-closeout-20261111/F2-SW-FEEDBACK-handoff.md` 交付。附 base/实现/独审 SHA、实际命令及通过/失败/跳过、审查报告和关闭记录、至少一份本次真实入口产出的脱敏 JSONL、试验目录清理和现存余项。交 `entity/result/release` 及 SourceRef 的逻辑引用、按组发布的预期和实际、公开 read/history 的复跑命令。ROOT 用相同结果版本在 IQS 或 Dashboard 的公开读取入口复验。
3. 正常提交本仓文件，按本仓已有发布安排交付可读版本。ROOT 按公开观察做跨仓验收。

交接的简短机器摘要可使用下列字段，详细证据放正文。

```json
{"lane":"F2-SW-FEEDBACK","owner":"stockwiki","worktree":"<实际工作目录>","base":"<开工 SHA>","implementation":"<实现 SHA>","reviewed_commit":"<最终独审 SHA>","tests":[{"command":"<实际命令>","result":"<实际结果>"}],"sample_refs":["<脱敏 JSONL>"],"review_ref":"<独审与关闭记录>","cleanup":"<本轮清理结果>","remaining":["<仍待 ROOT 验证范围>"]}
```
