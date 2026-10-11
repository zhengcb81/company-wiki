# W05-AUDIT-LOOP：公司池循环的进度保存与中断恢复

**可立即开工；三卡中最独立，推荐优先给一个harness。** 工作目录已创建：`C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop`；分支 `codex/w05-audit-loop`；起点 `c0993332623637d53f059350a382d99a95ef731d`。读树内AGENTS.md、`skills/revenue-forecast-audit/SKILL.md`及references/company-pool-loop.md、workflow.md、artifact-contract.md，再读本文及本树 `docs/handoffs/w05-audit-loop/input/`。本线PWF `.planning/w05-audit-loop/`。

## 1. 实证与交付范围

P7已验收：147测试及独立5项通过、记录/冻结/逐文档状态费用join/数字出处/审查coverage工具齐备，不重做。公司循环已有详细文字规则和手工campaign.json，但现有8脚本没有公司池选样、clean计数、有效版本变化或跨进程恢复的机器入口；已有12测试未覆盖这些行为。未证实真实循环已经丢样或重复收费，不能把能力增强描述成已发生事故。

交付一个小型纯进度reducer、一份原子JSON状态、恢复建议CLI及离线崩溃恢复测试。它服务native harness，**不启动agent/provider、不做scheduler、不新建数据库或费用账、不自动宣称研究质量通过、不新增审批/身份/canary门**。ROOT最终把入口写进技能主卡、安装并用于真实loop。

## 2. 排他可写集合

新增产品：

- `skills/revenue-forecast-audit/scripts/pool_progress.py`
- `skills/revenue-forecast-audit/references/pool-progress-contract.md`
- `tests/test_pool_progress.py`、`test_pool_progress_cli.py`、`tests/fixtures/pool_progress/`
- `tools/run_pool_progress_e2e.py`
- `.planning/w05-audit-loop/`、`docs/handoffs/w05-audit-loop/`、`docs/implementation/w05-audit-pool-progress/`

只读现有audit_run.py的原子写/Redactor接口、document_status_join.py和review_protocol.py输出及已有loop规范。SKILL.md/company-pool-loop.md/workflow.md、旧campaign/candidate_pool/budget_snapshot/真实runs、安装目录和其他仓库禁止写；ROOT最后一次接线。测试替身全部新owned scratch，不覆盖P7初审/复审/failed报告。

## 3. 公共接口（ROOT已定义）

纯函数 `reduce_progress(state, observation) -> {new_state, next_action, diagnostics}`，无I/O/provider/agent调用。CLI：

```text
pool_progress.py init --pool-ref <json> --seed <seed> --versions-ref <json> --budget-ref <json> --out <new-state.json>
pool_progress.py plan --state <json> --observation <json> --out <new-plan.json>
pool_progress.py apply --state <json> --observation <json> --event-id <id> --expected-revision <n>
pool_progress.py migrate-preview --campaign <old.json> --pool <json> --out <new-preview.json>
```

`plan`不改state；`apply`原子更新本活动state；init/output占用不能覆盖历史；migrate-preview不写旧输入。schema `audit-pool-progress/1`，小型JSON字段至少：revision、event_id/指纹、pool_ref SHA/seed/algorithm、current_run/attempt/entity_key、stage、四角色观察、selected、有效版本refs、clean证据refs、open根因refs、必须复测refs、budget_ref、possibly_paid_invocation_refs、next_action/why/diagnostics。只存定位和小摘要，不塞正文/全报告，不逐轮复制runs。

动作枚举：dispatch_executor、dispatch_missing_reviewer、dispatch_expert、resume_remediation、rerun_same_company_after_fix、select_next_company、reconcile_possible_charge、query_role_status、stop_related_paid_work、campaign_sample_criteria_met、no_action。动作仅建议native harness下一步，不实际调度。

### 选样与恢复

消费已有resolver提供的冻结主体pool，不扫描companies、不重新验证公司身份。stable sort＋明确版本的seed算法、无放回抽样；同pool/seed跨进程可复现。entity_key按上游提供，不按名字合并不同上市实体；跨上市地等价上游未提供则unknown，不自造identity限制。

先保存selection/run_id再给dispatch建议。崩溃恢复同一公司/attempt，不重新随机换失败样本。封存executor已完成则只补缺失reviewer；四报告完成则进入专家/复验，不重跑RF。旧writer状态unknown先query，不能擅覆盖其角色目录；确认结束后给新attempt。四审查保持独立，不由本工具捏造报告或代替agent实读。

### 并发原子进度与费用

同event_id/相同payload重放幂等；同ID不同内容诊断冲突，旧state不丢。expected_revision避免旧协调者覆盖；仅revision检查不足以保证并发CAS，使用短时OS级本地互斥/锁或等效原子方案保护read-check-replace，崩溃可恢复。它是数据一致性，不是用户许可；不能增加长时签收lease或常驻服务。写前/flush后/replace前中断只留下旧或新完整JSON，孤立owned临时文件可定位，旧报告不覆盖。

budget_ref引用现有AUTO/provider真账，不自计一份“累计余额”。P7单call join已去重，复用其调用ID/ref；观察重复不产生重复调用或重复费用。可能已经POST但结果未知时输出reconcile，cost/usage保持null，不能以不完整日志推成0或盲重发；没有供应商对账接口时仍unknown。预算不足保留当前公司与unknown，只停止相关付费动作，继续可做的无成本工作，不把活动标complete。

### Clean与版本

只有四个不同角色的实际最终质量结论、相应执行及检查refs齐、主要P0/P1/实质P2处置复验、scope/行为版本一致且无关键BLOCKED/NOT_RUN才能计clean。结构records_complete和quality_status=not_evaluated不计clean。新主要问题或影响结果的代码/安装/config改变计数归零；纯文档无行为变化需明确依据记录，不强制重跑付费。

默认连续3个不同、未参与修复的主体及实际可用市场覆盖达到**抽样停止条件**；不代表全部公司正确，也不能吞掉旧PWF必须复测/未完成义务。根因引用run_id::issue_id；迁移历史campaign只给preview，保留既选US:NVDA/initial/0clean/预算refs，未知补诊断，不把迁移当执行通过。

## 4. 三个实施节点

### A：TDD/接口冻结

先写上述行为反例，保留当前没有入口/相关能力的真实RED；另验证P7现有join的去重能力已具备而非重写。模块导入失败不当作算法反例。新设计只一个小型state与已有run引用，不增加账库。

### B：实现＋集中单元/集成

至少覆盖：种子/稳定排序/不同进程；pool SHA改变；保存选样后崩溃；executor封存但state滞后；仅fetch reviewer失败；writer active/unknown；unknown charge重启不POST；重复/不同call refs；低预算；new major/行为版本/纯文档变化；四审/版本/NOT_RUN/BLOCKED/旧复测义务；event幂等与冲突；并发stale revision；atomic故障；旧campaign preview；脱敏与有界输出。

接实际P7 status_index/coverage形状证明transport成功、records_complete不等业务成功；调用既有只读工具而非mock一个永远PASS。新contract和fixture字段完全写明，弱模型可照CLI复现。

```powershell
python -B -m unittest discover -s tests -p "test_pool_progress*.py" -v
python -B -m unittest discover -s tests -v
```

147旧测试仍通，快速全audit套件本来约38秒，可最终一次跑；小函数提交不增加新的全集/收费节点。

### C：离线跨进程崩溃恢复E2E与交接

```text
python -B tools/run_pool_progress_e2e.py --owned-root <fresh-scratch> --receipt <small-receipt.json>
```

冻结6个明确synthetic CN/HK/US主体；保存选择后杀协调子进程；新进程恢复同主体/run；封存本地fake executor；仅一reviewer失败并只补该role；模拟unknown fee重启且0外部POST；四报告与fixture质量观察补齐；重复apply；行为版本改变和旧复测义务；3个不同未参与修复fixture清洁回合；导出resume.json/md。记录实际dispatch计数/状态/hash和SIGTERM位置，不只改内存标志模拟重启。

网络拒绝、真实paid为0；synthetic费用不进母账。scratch预置sentinel初末SHA稳定，最后按精确owned清单恢复初始目录；保留小型receipt。明确这是恢复协议测试，不是真实公司研究PASS，不可能保证外部收费exactly-once。

按input/handoff_contract.md普通commit交付JSON/MD/manifest、RED/GREEN/E2E、接口fixture、安装候选文件列表与ROOT接线说明。不要安装/发布主线/迁移真实campaign。只三个大节点，完成即可STOP等ROOT接收。
