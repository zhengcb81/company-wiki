# company-wiki 当前规划状态

> **2026-09-12 上午最新覆盖（R4 阶段 A 收口 v0.4.2 / 阶段 B 设计三轮复审 / A06 首个真实基线）**：
> **① 阶段 A 合同 → v0.4.2**：A07=`accepted_with_findings`（22 条负例 + 五值错误模型）、A08=`rejected`（117 行映射：98 直连 / 6 桥接 / **13 无法指派**）。三份独立复审命中同一 P0：**`export_policy_2x` 在产**（`cli.py:835/849-851`，由 `:811`/`:831`/`:1182` 调用，是 filing-fetch **FC-501 containment / ZR-405 policy_hash 唯一来源**）→ **owner R-3 范围收窄为"仅准入 loader"**，导出路径保持。另：`reusable_for_filing` 实为**三处活实现**；**owner R-4 在现网惰性**（四个 root 都显式声明 `privacy_class: public`，受影响集合 = 0）；`read_only` 亦为假保证字段候选。
> **② 阶段 B 设计 → v0.1.2**（`B.DR` rev1/rev2 两次 rejected，已逐条更正；rev3 复审中）：B05 改为"停止销毁落选值 + provenance 存既有 `metadata_json` 列（无需 DDL）"；`_handle` 合格清单入参写死；B06 承载=`ResolutionEnvelope.qualification`；B07 划分 B 可签/不可签；新增读取预算与取消、`B-payload-hash` 必测项；checkpoint 生成器强制 `--reviewed-commit` + 完整性断言。**产品代码未改动**。
> **③ A06 首个真实基线（机制层）**：unit **787 passed**；contract **1748 passed / 7 skipped / 0 failed**（junit 入账）。其中 `test_dbx05_symlink_escape_rejected` 因 **宿主不支持 symlink** 跳过 → **symlink 逃逸控制在本机从未执行**（与 R-1 直接相关）。
> **④ 边界新事实**：**本机跑 CI 等价测试套件会打开生产 catalog（只读）**——`tests/contract/test_lt_uj_real_e2e.py` 硬编码生产路径且收集期即连接，**不在 CI 的 8 个 `--ignore` 内**。开库者清单因此为**四类**；主库与 `-wal` 全程未变（无逻辑写入）。
> **⑤ 待 owner**：批准 B 的 DEV 工作包与文件范围（[file-scope](assurance/runs/2026-09-11_r4-phase-b/file-scope.md)，在 revenue 侧）；确认 A05 样本清单 + 只读命令 manifest；可选新裁定（是否连导出路径一并收敛）。
> **⑥ GP-009 与门**：FC-705 预计 **今晚 22:00** 转 true（P10 24:00:05 + P11）；Daily 6/7→7/7、Weekly 0/2（09-13 04:30）、Monthly 1/1。下表 09-11 段落保留为当时观测。

> **2026-09-11 夜最新覆盖（22:00 运行后实测；R4 阶段 A 首轮 A.DR）**：
> **① FC-705 窗口修复已被真实运行验证**：`run_id=20260911T210001Z`、`ok=true`、`problems=[]`、`legacy_hits=[]`；权威账本关 **period 10 = 2026-09-10T21:00:13Z → 2026-09-11T21:00:18Z = 24:00:05（首个真正 ≥24h 的窗口）**，hits=0；开 period 11。**门仍 `close_allowed=false`，但唯一原因只剩历史窗口**：reasons=`["period 9: window 23:59:52 is shorter than 24h"]`（P9 已无法补救）→ **预计 2026-09-12 22:00 运行后确定性转 true**（last-two = P10 + P11，两者均 ≥24h 且零 hit）。修复机制见 revenue `41117ce`（runner 在调用观测器前补足窗口缺口；本次实际等待 ~5 s）。
> **② R4 阶段 A 首轮 A.DR = rejected（8×P1/5×P2/3×P3）**，更正已就地完成为 v0.2；运行目录在 revenue `assurance/runs/2026-09-11_r4-phase-a/`（**不在本审计证据目录内**）。**6 项 owner 裁定仍待决**（`symlink_policy` 假保证、`reusable_for_filing` fail-open、两套 root 准入实现分叉、`privacy_class` 缺省 public、R6 owner、R4 严格读法），A.DR 明确要求先裁定再冻结 A02。逐条见本仓 [progress.md](docs/plans/painpoint-outcome-audit-2026-09-05/progress.md) 顶部条目。
> **③ GP-009 累积**：Daily **6/7**（09-06~09-11，全部 ok=true）、Weekly 0/2（下次 09-13 04:30）、Monthly 1/1、drill 1/1。
> **④ 本轮边界**：owner 已批准 A 阶段精确 DEV/数据读取许可 + `--help`-only manifest + VR 指派；设计动作仅 52×`--help` 探针与只读核对。**未**改产品代码/配置/DB/任务/worker，未下载/LLM/删除。**边界更正（重要）**：生产库 `catalog.sqlite3-shm` 的三处前移**已归因**——两处 = revenue 侧**推送前强制 gate**（`tools/pre_push_gate.py` 的 real-data 套件对生产 catalog 跑 pytest，**只读**；GitHub Actions #139 21:19:16、#140 21:27:44 时间戳吻合），一处 = 22:00 每日任务；主库与 `-wal` 全程未变（**无逻辑写入证据**）。因此"本会话未运行任何会打开 catalog 的代码路径"的更强说法**已撤回**（push 协议本身会只读打开它）。详见 revenue `assurance/runs/2026-09-11_r4-phase-a/boundary-audit.md`。下方 09-09 段落保留为当时观测。

> **2026-09-09 深夜最新覆盖（22:00 运行后，只读核对）**：daily 触发成功——`run_id=20260909T210001Z`、`ok=true`、`problems=[]`、`legacy_hits=[]`；权威账本 `.source_catalog/legacy_periods.json` 开 **period 9**（`started_at 2026-09-09T21:00:21Z`、hits=0、sample 62 文档）。**FC-705 门仍 `close_gate_allowed=false`**：last-two = P7（23:59:41 ✗）+ P8（24:00:11 ✓）；预计 **2026-09-10 22:00 运行后**转 true。**R9 批 3 范围修正**：`backfill_v2`（`dropbox_governance.py:22` 生产导入）、`portfolio_promoter`（`cli.py:27` CLI 导入）、`_scan_root_v1`（`scanner.py:1401` 生产分派 + `shadow_parity`/`trace_parity`）、`legacy_bridge_enabled`（`resolver.py:322`/`architecture_gate.py`）均有活跃调用者，仅 `artifact_backfill.py` 零生产读者；批 3 需技术门 + owner 政策门并重新拆分，清单见 revenue 侧 [r9_batch3_checklist.md](../revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/r9_batch3_checklist.md)。**Worker v5 独立轨道全部完成**（V5-0/R/1/2/3 completed；冻结 51 项 + 三轴独立审查 accepted；四轮整改关闭 14 P1 + 3 P2；`--verify-manifest` 9188 通过、`--self-test` 17/32+4+3 全拒），仍 PLAN_ONLY、不授权实施。GP-009 累积 Daily **4/7**、Weekly 0/2（下次 09-13 04:30）、Monthly 1/1、drill 1/1。本轮仅文档 + 只读核对，未删除/未实施/未恢复 worker、未注册任务。

> **CI 推送协议（2026-09-08）**：本仓任何推送都必须走 revenue-forecast 的
> [CI 反复失败根因与根治协议](../revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/ci_root_fix.md)：
> 先跑本仓 `python tools/pre_push_gate.py`（ruff/compileall/config doctor/FC-1204 复杂度 ratchet/契约测试，绿才推），
> 推送后立即自盯 GitHub Actions 至绿；若失败面是本门漏掉的，必须同时扩展本页矩阵与该 gate，再推。

> **2026-09-08 当前规划覆盖：R4**。按用户要求，整改的唯一活动编排现为[虚拟数据湖收敛计划](docs/plans/painpoint-outcome-audit-2026-09-05/simplified-execution-plan.md)，配套[真实测试/审计矩阵](docs/plans/painpoint-outcome-audit-2026-09-05/simplified-test-matrix.md)与[旧WP迁移表](docs/plans/painpoint-outcome-audit-2026-09-05/r4-transition.md)。四个增量A/B/C/D及独立收入M取代旧15包/95门执行顺序；原117项、GP和原始负例保留。下方较早“15包/旧总计划为准”仅指当时交付，不再驱动执行。v5继续独占worker正式合同，仅约束对应后台能力，不阻普通本地读取。本次仅文档，没有复验源码/运行状态或授权实施；下方HEAD和daily均为历史观测，未来实施重新锁定输入。

> **2026-09-07最新覆盖**：其他任务继续推进，wiki HEAD=d92f8bf、revenue=6682ecf、filing=89c8bdb。最新daily为20260906T210001Z、ok=false/空triplet；默认观察账本已改到wiki路径，revenue旧ledger的green不可替代。revenue旧closure工具/测试及CI step已实际删除，wiki批3延后，不能再按下方旧快照重复删除或称“只等时间”。详见[并发状态差异与未验证边界](docs/plans/painpoint-outcome-audit-2026-09-05/current-delta-2026-09-07.md)；下方9/6事实保留为当时观测，相关原反证在新HEAD须独立重验。本轮仅同步文档，没有执行这些代码/删除/运行。

最新状态核对：2026-09-06。用户本次批准跨仓规划文档同步和步骤细化，不批准产品修复或真实运行；worker v5与主线仍不合并。当前效果判定以[原始痛点审计](docs/plans/painpoint-outcome-audit-2026-09-05/README.md)为准；修复编排以该目录[总计划](docs/plans/painpoint-outcome-audit-2026-09-05/remediation-plan.md)及执行手册为准，全部WP仍NOT_IMPLEMENTATION_AUTHORIZED。
观测HEAD：`853dca2d30bc2b85dc95e3117a6afc3b448daec7`；源码存在其他任务未提交改动，未来实施需重核精确输入。9/4～9/5同步为历史快照，不能覆盖下述9/6审计结果。

> **2026-09-08 观测快照（历史，已被上方 09-09/09-10 段覆盖）**：调度已连续触发成功——09-06 22:00（P3 开启、P2 关闭 25.3h）、09-07 22:00（P7 开启、P6 关闭 25 天零 hit）；最新 daily=`20260907T210001Z`、period=7。`--run-daily` 参数错误已在 revenue `2ff20d9` 修复并经真实触发验证；manifest `cat-file` 的 `safe.directory` 缺失已在 revenue `56ba0eb` 修复（SYSTEM 上下文）。**FC-705 门当时为 close_allowed=false**（权威账本 last-two = P5 短窗 + P6）。上方 9/07 段中的 HEAD/daily 数值为当时快照。**保留原文以便追溯；当前状态与门判定以本页顶部 09-09/09-10 段为准。**

## 活动计划全量索引（2026-09-08，防遗漏路由）

> 本表是**全部活动计划与审计入口的唯一路由**：任何新计划必须先登记在此，再进入执行讨论。状态列区分"计划可执行性"与"实施授权"——当前**全部整改均为 NOT_IMPLEMENTATION_AUTHORIZED**。

| # | 计划/文档 | 入口 | 状态 | 边界 |
|---|---|---|---|---|
| 1 | **R4 虚拟数据湖收敛计划**（唯一活动编排，44 步：A8/B10/C10/D10/M6+） | [simplified-execution-plan.md](docs/plans/painpoint-outcome-audit-2026-09-05/simplified-execution-plan.md) | PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED | 每步需精确授权；DR/VR/AR 独立审查；1→3→7 批次 |
| 2 | R4 真实测试矩阵（36 组：L01-L12/P01-P08/O01-O08/M01-M08） | [simplified-test-matrix.md](docs/plans/painpoint-outcome-audit-2026-09-05/simplified-test-matrix.md) | 全 pending | 继承全部非同义原反例；mock 只可诊断不可关闭真实 E2E |
| 3 | R4 旧 WP 迁移表（WP00-14 逐项归属） | [r4-transition.md](docs/plans/painpoint-outcome-audit-2026-09-05/r4-transition.md) | PLANNING_ONLY | 只调归属/先后，不宣称产品完成 |
| 4 | **架构减法诊断**（R4 依据：9 个复杂度泄漏点、门禁处置、7 类真实验收） | [data-lake-simplification/README.md](docs/plans/data-lake-simplification-2026-09-07/README.md) | 只读诊断已交付 | 未运行真实业务/性能；建议不自动取代旧计划 |
| 5 | R4 接班手册 | [execution-handbook.md](docs/plans/painpoint-outcome-audit-2026-09-05/execution-handbook.md) | 待授权 | 15 包/逐步检查点/失败停止 |
| 6 | 分面手册·控制面（WP00/11/12/14） | [execution-control-plane.md](docs/plans/painpoint-outcome-audit-2026-09-05/execution-control-plane.md) | 待授权 | G0–G5 独立审查 |
| 7 | 分面手册·数据面（WP01-07） | [execution-data-plane.md](docs/plans/painpoint-outcome-audit-2026-09-05/execution-data-plane.md) | 待授权 | 真实归档/恢复/跨 root 复用需 S01/S02 |
| 8 | 分面手册·模型面（WP08-10/13） | [execution-model-plane.md](docs/plans/painpoint-outcome-audit-2026-09-05/execution-model-plane.md) | 待授权 | 矿业真实运行需总计划 5.3 节动作门 |
| 9 | R2/R3 总计划（15 包，被 R4 取代） | [remediation-plan.md](docs/plans/painpoint-outcome-audit-2026-09-05/remediation-plan.md) | 历史领域细节 | 不作执行编排；映射后参考 |
| 10 | R4 计划独立审查 | [r4-independent-review.md](docs/plans/painpoint-outcome-audit-2026-09-05/r4-independent-review.md) | accepted_for_planning_delta | 仅计划可执行性，不授实施 |
| 11 | R4 文档验证 | [r4-document-validation.json](docs/plans/painpoint-outcome-audit-2026-09-05/r4-document-validation.json) | 文档核验通过 | 非产品测试 |
| 12 | 原目标索引 117 项 | [unit-ledger.md](docs/plans/painpoint-outcome-audit-2026-09-05/unit-ledger.md) / [.json](docs/plans/painpoint-outcome-audit-2026-09-05/unit-ledger.json) | 53 CONTRADICTED + 58 PARTIAL + 6 HISTORICAL_ONLY | 非生产重跑；逐项证据定位 |
| 13 | 机器门展开 95 门 | [gate-dag.json](docs/plans/painpoint-outcome-audit-2026-09-05/gate-dag.json) / [validate_execution_plan.py](docs/plans/painpoint-outcome-audit-2026-09-05/validate_execution_plan.py) | 全 pending | 只验计划结构，不准运行 |
| 14 | 审计报告群 | [wiki-audit](docs/plans/painpoint-outcome-audit-2026-09-05/wiki-audit.md) / [filing-audit](docs/plans/painpoint-outcome-audit-2026-09-05/filing-audit.md) / [revenue-audit](docs/plans/painpoint-outcome-audit-2026-09-05/revenue-audit.md) / [assurance-audit](docs/plans/painpoint-outcome-audit-2026-09-05/assurance-audit.md) / [gp-audit](docs/plans/painpoint-outcome-audit-2026-09-05/gp-audit.md) / [upstream-asset-audit](docs/plans/painpoint-outcome-audit-2026-09-05/upstream-asset-audit.md) / [historical-projects-audit](docs/plans/painpoint-outcome-audit-2026-09-05/historical-projects-audit.md) / [legacy-inheritance](docs/plans/painpoint-outcome-audit-2026-09-05/legacy-inheritance.md) | 只读审计已交付 | 结论不可由自签代替独立复核 |
| 15 | 独立审查群 | [assurance-independent-review](docs/plans/painpoint-outcome-audit-2026-09-05/assurance-independent-review.md) / [retention-independent-review](docs/plans/painpoint-outcome-audit-2026-09-05/retention-independent-review.md) / [remediation-plan-independent-review](docs/plans/painpoint-outcome-audit-2026-09-05/remediation-plan-independent-review.md) / [document-consistency-review](docs/plans/painpoint-outcome-audit-2026-09-05/document-consistency-review.md) / [execution-independent-review](docs/plans/painpoint-outcome-audit-2026-09-05/execution-independent-review.md) | 历史/计划级 | 不绑定 R4 当前版本 |
| 16 | 并发差异覆盖（9/7） | [current-delta-2026-09-07.md](docs/plans/painpoint-outcome-audit-2026-09-05/current-delta-2026-09-07.md) | 覆盖 9/6 观测 | 相关旧反证须新 HEAD 复验 |
| 17 | **Worker v5 独立计划**（V5-0/R/1/2/3 **全部 completed**，2026-09-09） | [v5 README](docs/plans/source-catalog-worker-recovery-v5-2026-09-03/README.md) / [task_plan](docs/plans/source-catalog-worker-recovery-v5-2026-09-03/task_plan.md) | V5_2_COMPLETED / PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED | 与主线不合并；worker 恢复前置 H01；冻结 51 项 + 三轴审查 accepted |
| 18 | GP 组（历史执行/批准 + 部署余项） | [remaining-gap-closure](../revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/task_plan.md) | 历史 + 部署尾项 | 不并行领取第二套队列；旧批准不扩为新动作许可 |
| 19 | 文档同步（9/4，历史） | [planning-sync-2026-09-04](docs/plans/planning-sync-2026-09-04/task_plan.md) | 历史交付 | 历史 hash 库存不是当前更新合同 |

**登记纪律**：新增计划/审计目录必须先在上表登记入口与边界，再进入任何执行讨论；未登记的计划视为未授权。

## 从哪里继续

| 范围 | 当前入口 | 状态解释 |
|---|---|---|
| 原三仓统一 DAG | [机器账本](../revenue-forecast/assurance/unified_completion/state.json) | 历史登记117/117 accepted；新审计发现范围缩减与实质反例，不证明117个原完整目标已解决，不重写历史收据 |
| 后续 GP 余项 | [活动计划](../revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/task_plan.md) | 存在代码、部署和生产验收余项；不能只等时间就宣称完成 |
| worker 恢复规划 | [v5 独立入口](docs/plans/source-catalog-worker-recovery-v5-2026-09-03/README.md) | V5_3_COMPLETED / PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED（冻结 51 项 + 三轴审查 accepted + 交接双审） |
| 历史文档同步 | [9/4同步记录](docs/plans/planning-sync-2026-09-04/task_plan.md) | 当时canonical范围阅读已完成；历史hash库存不是今天所有文件不许更新的合同 |
| 原痛点与后续整改 | [9/6审计及详细计划](docs/plans/painpoint-outcome-audit-2026-09-05/README.md) | 限定只读审计已交付；117项索引完整不等于生产重跑，15包整改仍未实施 |

## 不能作为现状的历史文件

- 根 `task_plan.md`、`findings.md`、`progress.md` 已由 [TERMINAL_NOTICE.json](TERMINAL_NOTICE.json) 封存为 `closed_superseded_incomplete`。保留原文；其8/2的Current Phase、PID、next-login accepted和8/9 FCAP入口不是当前运行状态。
- `task_plan_v2.md`、`task_plan_cw_recovery_20260725.md`、`review_plan.md`、`verification_CW-2.24_plan.md`、`.recover-task_plan-*.md` 为历史计划/恢复副本，不能从旧空框领取任务；逐文件内容审计仍记录在本次覆盖清单。
- [空间治理](docs/plans/catalog-space-remediation/CURRENT_STATUS.md)、[章节提取](docs/plans/core-section-extraction/CURRENT_STATUS.md)、[复用自动化](docs/plans/portfolio-reuse-automatic/CURRENT_STATUS.md)、[早期复用方案](docs/plans/portfolio-reuse-fix/CURRENT_STATUS.md) 已有历史关闭或转交状态。后续维护不可继续执行旧Strategy A。
- [legacy归档说明](docs/archive/CURRENT_STATUS.md) 覆盖旧Wiki研究型计划。2026-07-16后的职责边界以 [AGENTS.md](AGENTS.md) 为准：只做来源、解析、证据与只读export，投资研究语义归StockWiki；不恢复研究型writer或把LLM改成未经重构的多线程调用。
- v5 `baseline/**`、import manifest和reviews是已核验历史输入，不就地纠错、不从快照运行旧checker。旧v1–v4活动目录已回收，不要求历史source路径仍存在。

## 本次已经查出的跨仓风险

> **2026-09-06/07 审计快照 + 2026-09-10 状态标注**：下列前三项已于 2026-09-08 关闭/推进（逐项证据见 revenue [gp_tail_closure_2026-09-08.md](../revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/gp_tail_closure_2026-09-08.md)）；保留原文并就地标注，不删除历史判断。仍开放的是 H01、WP02–10、filing FC-903。

- GP-008：当前revenue `2ff20d9`已将daily注册参数修复为`run-daily`；实际Action/自然触发独立证明仍不足。latest观测manifest `20260905T194055Z`绑定旧`2cbd585`，不能证明当前组合通过。 → **2026-09-10 标注：已关闭**（09-06 22:00 起调度自然触发连续成功，09-08 起 daily 连续 ok=true；见 gp_tail §2）
- GP-006：Windows sibling CI接线存在，但job为非阻断且不包含生产catalog真实roots测试；原真实roots CI目标不能标完整关闭。 → **2026-09-10 标注：已关闭**（real-roots job 已改为阻断且绿，含生产 catalog 真实 roots；见 gp_tail §1）
- GP-010：已有owner批准与执行记录；normalized及receipt各7/7，summary6/7，sections=5/7，2份列表式缺口，安全拒绝不得绕过。kind宽范围历史处理与精确7份cohort不同；已产出的214份按owner处置保留，不擅自删除。机器T1不代真实语义闭环。 → **2026-09-10 标注：sections 已 7/7**（wiki `623e831` 列表式标题修复 + 09-08 欠抽取刷新 5 份；summary 6/7 的 1 份为 `_FORBIDDEN_OUTPUT` 正确拒绝，**不是缺陷**；见 gp_tail §5）
- H01：自动prune按旧归档目录日期判due，却覆盖全部retired EvidenceSpan，未证明逐条可信归档与恢复。独立核验确认代码风险但没有实际误删证据；WP01为worker恢复前置，不可仅修SQL即启动。 → **仍开放**（worker 恢复硬前置）
- WP02–10：policy/eligible、修订补缺、持久需求/attempt、真实语义与模型发布仍有实质缺口，详见分报告；不是单纯等待观察时间即可关闭。 → **仍开放**（R4 待授权）
- filing FC-903：reviewer所绑定implementer SHA与当前文件不一致；保留收据并披露，不修改签署字节来制造通过。 → **仍开放**（按 R4/审计处理）

最新证据与后续检查见 [审计入口](docs/plans/painpoint-outcome-audit-2026-09-05/README.md)。9/4同步分报告保留为历史观测；本次仍不修代码或改机器配置。

## Worker 安全边界

2026-09-04本次读取 `.source_catalog/worker_control.json` 为 `desired_state=paused`；成功读取HKCU Run key并确认`CompanyWikiSourceCatalog`不存在；成功查询CIM进程未发现匹配的source_catalog worker/supervisor。未重新穷举所有可能的系统启动入口，不能将范围扩大为全系统无任何自动任务。本次不恢复worker、不注册任务、不写库、不外发；8月旧日志中enabled/running和旧PID只作历史记录。

9/6较新审计的CIM查询被拒，不能沿用9/4进程查询推断此刻零进程。暂停控制与已知HKCU项是有限证据；本文同步没有操作worker或任何启动入口。

历史runbook中的整库backup参数已被后续轻量快照/受影响行恢复设计取代，不应直接照抄旧施工步骤。CW-2.24验证文档勾选618测试，但其结果仅记52+160项：这是证据覆盖差异，不证明当时失败，也不能补推当前全套通过。历史引用行号超出现文件长度时应回到相应历史版本定位，不能据此重新造实施队列。
