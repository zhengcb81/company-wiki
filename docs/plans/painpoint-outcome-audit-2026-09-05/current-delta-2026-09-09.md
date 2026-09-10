# 并发状态差异与未验证边界（2026-09-09 深夜）

> 本文件覆盖 [current-delta-2026-09-07.md](current-delta-2026-09-07.md) 之后的新进展；9/7 及更早的观测保留为当时快照，不重写、不当新 HEAD 的全量验收。
> 本轮只做**只读核对 + 文档同步**：未运行产品测试、未改产品代码/配置/DB/任务/worker，未下载/LLM/删除。

## 1. 机器观测（2026-09-09 22:00 运行后）

> **2026-09-10 22:00 运行更新（实测）**：`run_id=20260910T210001Z`、`ok=true`、`problems=[]`、`legacy_hits=[]`；账本开 **period 10**（`2026-09-10T21:00:13Z`），P9 关闭为 **23:59:52（差 8 秒，SHORT）** → `close_gate_allowed` 仍 **false**。**机制级根因**：窗口时长 = 相邻两次 daily 的间隔，任务按 22:00 触发但有 ±20 秒抖动 → 约一半夜晚 <24h（P7 −19s、P8 +11s、P9 −8s；零 hit 实质条件每晚均满足）。**根治已由 owner 授权并实施**（revenue `41117ce`）：`run_daily` 在调用 observer 前真实等待补足到 24h（上限 180 秒；不放宽阈值、不回溯时间戳；提前的手动重跑不补）。**生效时点**：2026-09-11 22:00 起；**门预计 2026-09-12 22:00 确定性打开**（P10+P11 均 ≥24h）。GP-009 累积更新为 Daily **5/7**、Weekly 0/2。详见 revenue 侧 [gp_tail_closure_2026-09-08.md](../../../../revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/gp_tail_closure_2026-09-08.md) §6.4。

| 项 | 实测 |
|---|---|
| daily run | `run_id=20260909T210001Z`（22:00:20 本地）、`ok=true`、`problems=[]`、`legacy_hits=[]`、`resolve_sample_sec=0.0066` |
| daily manifest | `observation_period=9`；triplet revenue `218ba7e` / filing `bb8d485` / wiki `454f632`（运行时刻快照，非当前 HEAD） |
| 权威账本 | `.source_catalog/legacy_periods.json`（22:00:21 写入）→ period 9 `started_at 2026-09-09T21:00:21Z`、`legacy_bridge_hits=0`、`mode=sample`、`sampled_documents=62` |
| FC-705 门 | `close_allowed=false`，reason `period 7: window 23:59:41 is shorter than 24h`（last-two = P7 ✗ / P8 24:00:11 ✓） |
| 预期关闭 | ~~2026-09-10 22:00 运行后~~ → **2026-09-10 22:00 实测：仍未开**（P9 = 23:59:52，差 8 秒）；按 last-two 规则**最早 2026-09-12 22:00 后**，每次短窗再顺延一天 |
| GP-009 累积 | Daily **4/7**（09-06/07/08/09）、Weekly 0/2（下次 2026-09-13 04:30）、Monthly 1/1、alert drill 1/1 |
| 三仓工作树 | company-wiki **提交时点干净**（2026-09-10 交接复核时 v5 冻结记录尚有一行未提交的 §8 决策，现已随 V5-3 交接提交入库）；filing-fetch 干净；revenue 仅 3 个 ACL 受限空目录（`.tmp-zr408-unit*`）未清理 |

**不可做的动作**：今晚**不要**手动跑 `legacy_observer`/`run-daily`——会把 period 9 提前结束（<24h），反而把门关闭时点推后一天。

## 2. Worker v5 独立轨道已完成（同仓另一目录）

- 目录：[source-catalog-worker-recovery-v5-2026-09-03](../source-catalog-worker-recovery-v5-2026-09-03/README.md)，提交 `6559075`。
- 阶段：V5-0/V5-R/V5-1/V5-2/V5-3 **全部 completed**；正式冻结 51 项（48 导入计划输入 + 3 v5 治理件）；三轴独立审查 `accepted`（SQL/性能、生命周期/安全、测试/DAG），共 13 份审查/关闭记录。
- 验证：`--verify-manifest` `PASS: 9188 checks`；`--self-test` `17 cases / 32 mutations + 4 default-mode checks + 3 guard checks; failures=none`；四轮整改关闭 **14 P1 + 3 P2**。
- **边界**：只证明规划文档完整/可复现，不证明 worker 实现/配置/DB/任务健康；`NOT_IMPLEMENTATION_AUTHORIZED` 不变，H01 风险与隔离验证仍需 R4 各自取证。

## 3. R9 批 3 范围失真（对本目录映射表的影响）

09-02 授权申请把批 3 写成「无生产读者 backfill/promoter」。2026-09-09 逐符号实测：

| 候选 | 活跃调用者 | 结论 |
|---|---|---|
| `backfill_v2` | `dropbox_governance.py:22`（生产治理导入 `classify_bucket`） | **有生产读者** |
| `portfolio_promoter` | `cli.py:27`（CLI 导入） | **有 CLI 读者** |
| `_scan_root_v1` | `scanner.py:1401`（生产分派）、`shadow_parity.py:94`、`trace_parity.py:206` | **非死代码** |
| `legacy_bridge_enabled` | `resolver.py:322`、`architecture_gate.py:127/139/278` | **非死代码**（迁移期 bridge/回滚） |
| `artifact_backfill` | **自带运维 CLI**（`--mode dry-run\|apply`；FC-901 收据记载 production caller 即同模块 CLI main()）；3 个契约测试导入（zr305/zr1005/test_source_catalog_artifact_backfill）；FC-906 卡片标注 Forbidden「FC-901 工具，不改」；冻结 v5 基线有 ZR1005-C1~C4 验收行 | 🔴 **2026-09-10 更正：不是零读者**。先前"唯一零生产读者"基于过窄 grep（只查 import），已证伪；**3a 已由 owner 同日正式撤销**，未删除任何文件；若将来退役该能力属"能力退役"另议 |

影响：
- `r4-unit-remediation-map.md` 中 CA-304 / ZR-1009 行的「R9 批3（已批准待 FC-705 门）」应理解为**尚需 owner 重新确认范围**；技术门（FC-705）+ 政策门（2026-09-06 owner 延后至 v2 迁移稳定）双重满足后才可能执行。
- 执行清单（含门、范围、验证、回滚、冻结边界）见 revenue 侧 [r9_batch3_checklist.md](../../../../revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/r9_batch3_checklist.md)。

## 4. 本轮未验证/未授权

- 未复核 9/7 之前的旧反证在当前 HEAD 下是否仍成立（须实施时重锁输入）。
- 未运行 R4 任何步骤、未做真实 E2E、未跑生产 SQL、未下载/LLM、未改任务/worker。
- 所有 WP 仍 `NOT_IMPLEMENTATION_AUTHORIZED`；本文件不构成任何授权。
