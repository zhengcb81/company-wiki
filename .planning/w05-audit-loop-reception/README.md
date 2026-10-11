# ROOT 接收工作包

本目录属于 ROOT，只用于 W05-AUDIT-LOOP 接收；不接管 W05-CWP-OCR、W05-RF-FLOW、W06 或其他 harness。

## 恢复入口

先读 task_plan.md、progress.md、findings.md 与母 PWF 最新顶部。以实际 Git HEAD 和接收 evidence 为准；历史原交付 PASS 与 ROOT 原独审 FAIL 都保留，不能覆盖。

核心源码与新19回归在 `C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop-root`；正常并线后 canonical 为 `C:/Users/郑曾波/Projects/revenue-forecast-audit`。工程复现使用该仓库 `python -B -m unittest discover -s tests -v` 和 `tools/run_pool_progress_e2e.py --help` 指定独立 owned scratch / receipt。以测试初始目录清单为准恢复，不能操作真实 runs、原件或他人临时目录。

本目录 `apply_closure.py`、`finalize_closure.py`、`close_stop_rules.py`、`final_e2e.py` 是已执行的一次性精确 SHA/旧文本补丁脚本，**不能作为日常启动器再跑**。旧失败/修复日志用作因果证据，不是新的待实现问题。`acceptance_report.py` 与 `update_pwf.py` 也是 create-only 单次封存工具，重跑会拒绝覆盖。重复测试另建新 attempt，不能改写过去 receipt。

本次通过只证明有界进度记录、恢复协议及技能接线；真实公司来源、四个独立 agent 和预测质量仍按母 PWF 大节点执行。零新项目费用，不新增人工审批或每 commit 全量测试。
