# DU9-CWP-GEOMETRY-PLANNER

状态：READY，ROOT仅建立工区和入口，业务尚未实施。工作目录：`C:/Users/郑曾波/Projects/company-wiki-du9-geometry-planner`。
PLAN_ID：du9-geometry-planner-2026-10-16。基线：`bf160c8e3fd8b9620f6bbc891ba448fd5647e388`。分支：`codex/du9-geometry-planner-20261016`。

先读construction_card.md、INTERFACES.md及AGENTS；只恢复本PWF，不用其他根计划覆盖它。

## A：调查和独立行为RED

Status: done。核实真实共因（findings.md：无请求规划组件、WorkBudget纯总量封顶、
fine_geometry无顺序偏好），冻结96页手算用例与期望，首FAIL见
receipts/red_first_fail.txt（基线贪心project饿死=0；planner测试 ModuleNotFoundError）。

## B：所属层实现与集中回归

Status: done。实现 `src/company_wiki/document_understanding/geometry_intent/`
（`61120fe1`，审查修复 `db126f24`）：`plan_geometry_requests` 有限章节公平配额/借用/
全局硬余额，`admit_geometry_request` 实际候选扣减+同页去重+原因分离，`new_admission_state`
/`summarize_admission_state` 调用内 JSON 值。只读复用 WorkBudget 协议，零预算类复制。
集中回归 `tests/unit/du9_geometry_planner/test_b_contract_counterexamples.py` 覆盖零额度/
尾部耗尽/上限1/海量窗口(2万+分离)/重叠/负数与bool页码/巨大scope/有界诊断/乱序重复/
纯度/确定性。未抬 cap、未改旧 gold。

## C：所属层E2E、恢复、清理和独立审查

Status: done。`test_c_e2e_stream_recovery.py`：96页真实事件流公开入口E2E（后部未饿死、
admitted==64==限、重复ACK不重复扣、精确因果计数）、plan+state JSON 中断重放与一次完整
运行逐 decision 等价、计数证明零 IO/模型/原生解析（monkeypatch open/stat/scandir/socket
+ AST import 白名单）、fixture/生产配置 SHA+mtime 未变。独立审查 agent
（agent_5dd60502-f82e-49e2-b382-41d7cfc8b2c8，非实施者）两轮：首轮 FAIL（F1 digest 绑定
P1 + F2-F4 P2 + F5 PWF），全部根因修复于 `db126f24`，复核实证关闭 F1-F4、零新 finding；
最终验证段见 review/independent_review.md。PASS 且零未解决问题后交接。

## Next Step

按施工卡执行A。可现在独立启动；提交后按INTERFACES报告独审身份、精确SHA、反例/测试/清理和ROOT接线方法，冻结STOP。
