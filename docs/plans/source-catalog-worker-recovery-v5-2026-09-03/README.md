# Worker 恢复计划 v5 — 独立工作目录

> 2026-09-08 跨计划衔接：当前由 [R4 数据湖收敛计划](../painpoint-outcome-audit-2026-09-05/simplified-execution-plan.md) C/D 协调持久任务、安全、性能与恢复；本目录独占 worker 版本合同/正式冻结，不被替代或并入主线。R3 的 95 门不再叠加；适用的 v5 安全/版本/恢复要求仍必须满足，A/B 本地读取不等 v5。D.SAFE 不是恢复许可；真正 worker 仍需本候选隔离验证、持久领取/失败恢复、v5 适用前置和精确授权。

本目录由用户明确同意后于 2026-09-03 新建，是当前唯一继续维护的 worker 恢复计划目录。
原 `source-catalog-worker-recovery-2026-08-22/`（v1–v4）已按用户要求移入 Windows 回收站，**但实测已复活**
（38 文件、tracked、clean、mtime `2026-09-07T18:08:52Z` UTC），因此按 N9 作为**非权威副本**显式处置，
不再作为活动目录。**本目录不并入主线计划**，已核验的基线副本与原调查报告保留。

当前状态：**V5_3_COMPLETED / PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED**（2026-09-09 三路复审全部 `accepted`；2026-09-10 交接双审 `accepted_with_findings`，P0/P1 已按 [冻结记录 §9](v5-freeze-record.md) 关闭）。

## 1. 活动入口（按顺序读）

1. 本文件 → [`task_plan.md`](task_plan.md) → [`findings.md`](findings.md) → [`progress.md`](progress.md)（planning-with-files 三件套）。
2. 版本合同（唯一版本轴裁决）：[`v5-version-contract.md`](v5-version-contract.md)（协议线 `v4` / 冻结代 `v5`）。
3. 正式冻结与验证：[`plan_manifest.v5.json`](plan_manifest.v5.json)（51 项）、[`plan_freeze_check.v5.txt`](plan_freeze_check.v5.txt)、
   [`v5-freeze-record.md`](v5-freeze-record.md)（偏差 D1–D17、残余风险、四轮整改表）。
4. 冻结边界与 N9 载荷：[`v5-freeze-boundary.md`](v5-freeze-boundary.md)（含机器可读处置块与 `-I` 调用要求）。
5. 冻结语料本体：`baseline/plan/`（48 份导入计划输入，逐字节副本）；`baseline/history/`（v3/v4 manifest、旧进度/审查、冻结漂移诊断）；
   `baseline/investigation/`（原 worker 调查报告）。
6. 只读校验器：[`tools/v5_plan_consistency_check.py`](tools/v5_plan_consistency_check.py)（默认 / `--verify-manifest` / `--self-test`）。

## 2. 冻结与验证（可复现）

```powershell
cd <repo>
python -I docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py
python -I docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py --verify-manifest
python -I docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py --self-test
python -I docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_version_reference_scan.py --check
python -I docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_equivalence_check.py --check
```

期望（冻结产物提交 `4f4dea1`；冻结时点 HEAD 为 `89c0862d`，即 manifest 的 `plan_freeze_git_head`——两者不同，勿混用。三路独立复审与 2026-09-10 交接双审各自复现）：

- 默认模式：`PASS: 7720 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}`，stdout 与 `plan_freeze_check.v5.txt`
  **逐字节相同**（172 字节、0 个 CR、sha256 `5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83`）。注意：本行按实际字节书写（冒号后有空格）；`v5-freeze-boundary.md` 里的同类引文是旧渲染，以本页与产物字节为准。
- `--verify-manifest`：`PASS: 9188 checks`，exit 0（N1–N17 全绿）。
- `--self-test`：`17 cases / 32 mutations + 4 default-mode checks + 3 guard checks; failures=none`（实测约 70–90 秒）。
- **必须带 `-I`**：不带隔离解释器时 checker 的启动守卫会直接 FAIL（防止 `sys.path[0]` 影子模块伪造 PASS）。

锚点层级：① 51 项冻结集逐字节哈希；② 冻结内代码钉扎 6 份历史/来源文件；③ manifest 绑定证据输出、证据工具、
捕获记录、边界处置载荷；④ N10 对 manifest + 51 项做 **worktree↔HEAD** blob 比对（未跟踪即 red）。最终账本是 Git 提交历史。

## 3. 历史索引

| 内容 | 位置 |
|---|---|
| 原 v3/v4 manifest、旧进度/审查、冻结漂移诊断 | `baseline/history/`（5 份，哈希被冻结内代码钉扎） |
| 原 worker 调查报告 | `baseline/investigation/worker-investigation-2026-08-20.md` |
| 导入审查、旧目录退役清单与结果 | `reviews/`（历史；按合同**不改字节**） |
| 版本合同四轮设计审查 | `v5-version-contract-review.md` / `-rev2.md` / `-rev3.md` / `-rev4.md` |
| 冻结三轴审查与四轮关闭记录（共 13 份） | `v5-freeze-review-*.md`、`v5-freeze-review-*-closure*.md` |
| 版本引用枚举与等价性证据 | `v5-version-reference-inventory.{json,md}`、`v5-baseline-equivalence.json` |

## 4. 只读复核：worker 暂停与自启动入口（2026-09-09 实测）

| 检查项 | 实测 |
|---|---|
| 控制状态 | `.source_catalog/worker_control.json` → `desired_state: "paused"`（`updated_at` 2026-08-20T21:43:32Z） |
| 启动器最后事件 | `worker_launcher_events.jsonl` 末条 → `status: exited`、`reason: persistent_pause`（2026-08-20T21:43:37Z） |
| 运行中的 worker 进程 | 无（仅有无关 MCP python 进程） |
| 计划任务 | 无 python/catalog/worker 相关任务；`CompanyWiki Source Catalog` **未注册**（全部 Task Scheduler 文件夹已扫） |
| 注册表自启动 | HKCU/HKLM/WOW6432Node/HKU `Run`、两个启动文件夹、GPO 登录脚本、Active Setup、Winlogon、IFEO/AppInit_DLLs、WMI `root\subscription`、服务：均无 source_catalog/CompanyWiki 条目 |
| 启动文件夹 | 仅 `desktop.ini` |
| 自启动脚本 | `scripts/source_catalog_worker_at_logon.{ps1,vbs}`、`source_catalog_worker.ps1` 存在但**未被任何入口引用**；注意**在库重挂路径**：`src/company_wiki/source_catalog/startup.py::install_startup_task` 仍可写 HKCU `Run` 或 `schtasks /Create`（当前无人调用，属"可被重新武装"而非"已武装"） |
| 三个营收任务 | 非提权会话不可查询（`Access is denied` → `unknown`）；其运行由 `company-wiki/.source_catalog/legacy_periods.json` 与营收侧报告记录 |

**审计边界（如实声明）**：2026-09-10 复核覆盖上述清单；3 个 HKU 侧 hive 与受保护的计划任务在非提权会话不可读，故"无自启动"是**在当前可见范围内**的结论，不排除提权后才可见的条目。

结论：**worker 处于持久暂停状态，未发现任何活动的自启动入口**。本目录的任何工作都不改变该状态。

## 5. 剩余风险（与 [冻结记录 §6](v5-freeze-record.md) 的 9 条一一对应）

1. §6.1 冻结只覆盖**规划文档完整性**，不覆盖 worker 实现、配置、数据库、任务。
2. §6.2 旧目录**未删除、未加锁**；N9 只保证"被申报 + 摘要复算 + 不得并列权威"。
3. §6.3 N9 判据边界：同时改名目录名与全部标记文件的副本、以及 `docs/plans/` 之外的副本不在机器判据内。
4. §6.4 不可变性依赖 Git：一次**新的提交**不会被 N10 拦截；`frozen_at` 是声明值（`plan_freeze_git_head` 已校验为祖先且含语料）。
5. §6.5 活动文档中的旧目录引用不受证据/机器检查覆盖。
6. §6.6 本记录、审查记录与边界记录本身不在冻结集与证据范围内（避免自指）；边界记录另由 manifest `boundary_record` 绑定。
7. §6.7 `.githooks/pre-commit` 仍会整仓 checkout + patch 恢复（v4 漂移事故的机制）。
8. §6.8 `reviews/old-plan-retirement-inventory.json` 含绝对个人路径（该文件按合同 §6.2 `reviews/` 行不改字节，无凭据）。
9. §6.9 启动守卫与 `V5-TOOLS-EXACT` 只在 checker 真的以 `-I` 被运行时生效；用**另一个**解释器包装调用（如 `runpy.run_path` 且未把计划目录放进 `sys.path`）不受覆盖；其它平台/解释器需重跑 `GUARD*` 自测。
10. 成本项（非缺陷）：`--self-test` 墙钟随变异数增长（11s→89s）。**该优化在 generation v5 内结构性不可行**——改 checker 会破坏 N5 的哈希绑定、向 `tools/` 增文件会破坏 `V5-TOOLS-EXACT`；故**不再作为可执行建议**，只在未来 generation（v6）重设计时处理（见冻结记录 §8 SQL-OBS-3 行）。

## 6. 实施顺序（不重述，指向冻结语料）

实施顺序以**冻结语料**为准，本页不复述：先读 [`baseline/plan/task_plan.md`](baseline/plan/task_plan.md)（阶段划分）、
[`baseline/plan/execution_playbook.md`](baseline/plan/execution_playbook.md)（执行手册）、
[`baseline/plan/gate_dag.v4.json`](baseline/plan/gate_dag.v4.json)（115 个固定节点与门依赖）、
[`baseline/plan/test_acceptance_plan.md`](baseline/plan/test_acceptance_plan.md) 与
[`baseline/plan/test_id_registry.v4.json`](baseline/plan/test_id_registry.v4.json)（315 个测试 ID）。
跨计划协调见 R4 计划的 C/D 段；本目录与主线保持隔离。

## 7. 明确不授权

- **不授权**实施 worker 修复、恢复 worker、运行登录测试、外发数据、写生产数据库或配置。
- **不授权**把本目录并入主线计划，或把 `baseline/plan/` 里的旧 checker/Gate/worker 命令直接执行。
- **恢复 worker 的硬前置**（见 PLANNING_STATUS 与 R4 计划）：**H01 可信归档/危险入口风险必须先关闭**——旧归档目录日期可触发对全部 retired EvidenceSpan 的回收，且生产 worker 以 `apply=True` 调用；在 H01 关闭前不得恢复 worker，也不得把它当作"冻结已完成即可恢复"。
- 冻结 manifest 是**未来实施的输入**，不是实施许可；真正的恢复仍需用户精确授权 + 隔离验证 + 持久领取/失败恢复闭环。
- 计划工作只写本目录；不改其它仓库/主线计划/根级 Git 属性；提交一律经过 pre-push gate，不使用 `--no-verify`。
