# 审计发现

> 2026-09-09 最新状态请先读 [current-delta-2026-09-09.md](current-delta-2026-09-09.md)：worker v5 独立轨道全部完成（冻结 51 项 + 三轴审查 accepted）、FC-705 门仍 false（差一晚）、R9 批 3 范围失真（仅 `artifact_backfill.py` 零生产读者）。下方 9/5～9/7 观测保留为当时快照，不重写、不当新 HEAD 全量验收。

> 2026-09-07最新状态请先读current-delta-2026-09-07.md：其他任务已推进R9删除/daily修复并产生失败run；下方9/5～9/6观测不重写，也不当新HEAD全量验收。同步23活动文档及执行手册R3已经独立审查；产品整改仍未实施于本任务。

> 按时间保留的发现日志；最终范围与结论见README及各分报告。下方“初步/待验证”是发现当时状态，后续条目与分报告提供核验结果。新审计不修改任何原计划。

## F009：R9 批 3 的"无生产读者"口径已失真（2026-09-09 深夜实测）

- 证据（逐符号 grep，wiki 源码）：`backfill_v2` ← `dropbox_governance.py:22`（生产治理链导入 `classify_bucket`）；`portfolio_promoter` ← `cli.py:27`（CLI 面）；`_scan_root_v1` ← `scanner.py:1401`（生产分派）+ `shadow_parity.py:94`/`trace_parity.py:206`（对账）；`legacy_bridge_enabled` ← `resolver.py:322`、`architecture_gate.py:127/139/278`。
- 🔴 **2026-09-10 更正（本条部分作废）**：当时写"仅 `artifact_backfill.py` 无 src/scripts 生产导入 → 零生产读者"是**基于过窄的 grep**，**已证伪**。完整扫描显示：① 该模块自带**运维 CLI**（`artifact_backfill.py:305 main()` → `python -m …artifact_backfill --catalog … --mode dry-run|apply`），`assurance/fc/FC-901/11_implementer_receipt.json` 明确记载「run_artifact_backfill 的 production caller 就是**同模块的 CLI main()**」；② 被 3 个契约测试导入（`test_zr305_legacy_migration.py`、`test_zr1005_artifact_backfill.py`、`test_source_catalog_artifact_backfill.py`）；③ **FC-906 工作单元卡把它列为 Forbidden files**（`assurance/fc/FC-906/00_wu_card_a.md:24`「`artifact_backfill.py`（FC-901 工具，**不改**）」）；④ 冻结 v5 基线 `baseline/plan/test_acceptance_plan.md` 有 ZR1005-C1~C4 验收行；⑤ ratchet 登记 `37`/`79`。→ **它不构成"最小死代码步"**：owner 2026-09-10 的"执行 3a"指令因前提证伪而暂停，**未删除任何文件**。
- 推理：09-02 授权申请把批 3 描述为"无生产读者 backfill/promoter"，若照此机械删除会破坏生产治理/CLI/对账/回滚路径。批 3 的实质是"退役 v1 扫描路径与迁移期机制"的架构清理，必须先有替代路径与回滚，再谈删除。
- 影响：R9 批 3 需**技术门（FC-705）+ owner 政策门（2026-09-06 延后至 v2 迁移稳定）**双重满足；拆分后 **3a 已作废**，只剩 3b（`_scan_root_v1`+parity）与 3c（bridge+flags+resolver），二者均需先给出替代路径与回滚，**当前没有任何小批满足机械删除条件**。清单见 revenue 侧 `r9_batch3_checklist.md`。
- 边界：本轮只做只读 grep 与文档记录，未删除、未改产品代码。

## F008：worker v5 的"完成"只覆盖规划文档完整性（2026-09-09）

- 证据：v5 冻结集 51 项 + `--verify-manifest` 9188 + `--self-test` 17/32+4+3 全拒 + 三轴独立审查 accepted（见同仓 v5 目录）。
- 推理：冻结证明的是"规划文档完整、可复现、未被静默改写"，**不证明** worker 实现、配置、数据库、任务健康，也不授权恢复 worker。
- 影响：R4 中 worker 相关 WP 可把 v5 冻结作为**版本合同输入**，但 H01 风险、隔离验证、持久领取/失败恢复仍必须各自取证。

## F001：文档同步并不等于原始痛点消除

- 证据：`company-wiki/PLANNING_STATUS.md` 同时记载 117/117 accepted 和 GP-006/008/010 未闭环；原始目标文档要求实际多根消费、实际调度与观察窗口等。
- 推理：机器账本的 accepted 只能证明账本状态，不能自动证明原始用户结果。需要独立检查实现、真实接线、结果及签署绑定。
- 入口页仍写 GP-010 sections=0 和“尚未宣称全量审计完成”；上次审计记录已有更新线索，本次须用实际产物确认，不能直接沿用旧结论。
- 初步判定：全局完成主张不成立；具体功能逐项待核。

## 原始问题分类（不可降级的验收来源）

P01 防假绿/真实完成证明；P02 无副作用只读/锁与失败恢复；P03 全部授权根消费与身份；P04 最新版本与最少下载；P05 可信加工复用/最小失效/实际需求；P06 安全审查与消费闭环；P07 研报多实体/页表章节事实；P08 收入合约与事务发布；P09 矿山颗粒度与合并口径；P10 实际 E2E/动态监测/Windows；P11 技术债与旧实现退出。

来源：`revenue-forecast/audit_review/2026-08-13_three_repo_completion_rebaseline_plan/project_goal_and_pain_points.md`。

## 待验证线索（不是本轮确认结果）

上次文档审计发现 daily CLI 参数不匹配、Windows CI 非阻断且用 fixtures、broker 实际处理超出七份 cohort、收据重签与 reviewer SHA 不匹配、自然观察周期不足。必须检查当前代码和当前证据后给出最终状态。

## F002：场景验收仍按 status 汇总，而非 required tier × triplet × 实际证据

- 当前源码：`revenue-forecast/assurance/unified_completion/uc/scenarios.py::closure_report` 仅检查 status；`verify` 只检查冻结来源hash、计数和ID集合，不校验执行证据。`uc/closure.py::closure_report` 对场景也只检查 status。
- 原验收：CA-105 明确每个 scenario × required tier × triplet 都需要真实结果，缺一项 closure 红；CA-107 要求缺收据、陈旧组合和自然窗口均阻断。
- 反证：当前汇总函数没有读取 evidence_path、tier执行结果、当前triplet或freshness；因此通过该汇总不能证明原始验收。待隔离负例确认，并继续检查更外层是否有补偿门。

## F003：运行与源码已并发更新，不能复述旧 GP-008 快照

- 22:18 左右只读基线：wiki HEAD `853dca2d30bc2b85dc95e3117a6afc3b448daec7`，filing `89c8bdb2cfba4d88720d005d0558f422957e8ade`，revenue `2ff20d9b410d3498181f7258a23ed9625caab826`。
- wiki section_extractor.py 与其contract test已有未提交修改；这些不是本审计所写。
- daily_manifest 已更新到 `20260905T194055Z`、period=2、ok=true；旧入口页的run1已失效。新报告绑定 revenue `2cbd585...` 而不是观测HEAD；不能用于新HEAD的严格闭环。
- 报告中的 roots_fingerprint 实为三根计数，latency 名为 resolve_sample_sec；后续核查是否真实resolver/全路径hash。报告的 ok 不自动证明原 CA-202 目标。

## F004：隔离反例证明 freshness/weekly/scenario 门不足

- 证据：本目录 `audit_probe.py` 与 `probe-results.json`；2026-09-06执行exit=0。只编译预审过的具名纯函数，不导入生产入口、不运行DB/调度/网络。
- 2099年的ledger被 `freshness_status` 判fresh；缺evidence_path/fixture_hash的T2场景被 `scenarios.closure_report` 判closure_ready=true。
- `weekly_t3_schedule._suite_outcome` 对 `1 passed, 2 skipped` 和空stdout且rc=0均判ok；不符合全required markets不得skip验收。
- `task_status` 把AccessDenied判为missing，丢失部署未知和未注册的区别。
- 新daily源码已使用 `run-daily`；原参数错误是历史问题，当前缺口转为部署Action/自然触发来源不可证、报告质量及release门不足。

## F005：原始任务被缩减为机制验收，形成accepted循环证明

详见assurance-audit.md A01及25项CA表。CA206真实自然周期、CA301干净三仓独立重放、CA302真实三公司、CA304真实删除等，在11receipt把实际动作移到部署却标accepted；CA305再验证accepted/文件存在/40字符即可“证明”六问题。不能解释成只等时间即可完成。

## F006：当前业务仍有可复现实质错误

filing-audit.md记录policy旁路、global canonical遮蔽eligible、修订ID词序错误、多gap只做首项、deadline10秒可耗14秒、失败后下载计数丢失；revenue-audit.md记录矿山单位/TC-RC/持股时间与发布事务缺口；wiki-audit.md记录内存DemandQueue和producer journal/安全门生产接线不足。每条以分报告具体代码与安全探针为准，不据统一accepted推翻反证。

## F007：空间回收门会把未证实归档的retired证据纳入自动删除范围

详见historical-projects-audit.md H01。旧目录日期达标即due，DELETE覆盖所有retired，worker.py周期直接apply=True；archive同日覆盖且只count对账。未证明已发生生产误删，但恢复worker之前必须修复此门并独立审查，不能等日历自然放行。当前paused不等于代码已安全。

## F008：本轮静态证据覆盖量与局限

evidence-inventory.json记录117个单元、351个主要receipt元数据与hash（长说明明确为excerpt）；197场景全passed但fixture_hash与oracle均197个缺失。44个冻结plan input本次全部hash+size匹配，这证明历史输入未坏，不证明履约。

## F009：独立计划审查防止执行依赖歧义

remediation-plan-independent-review.md对R1提出两项P1和四类P2：裸工作包依赖可能造成能力验收互等、WP12真实运行安全前置不足，以及授权subtype/稳定归档快照/显式RED/恢复对象边界。R2第5–6节已逐项修订，获独立accepted_for_planning_delta；不得把计划审查通过等同产品验收或实施批准。15个工作包每个G0–G5均安排独立review（此为R2历史记录，R4已取代其编排）。

## F011：六类痛点实施粒度补充（2026-09-08，本轮）

用户要求细化修复计划实施步骤，范围仍是文档。FC903已有旧remediation-plan.md WP00第6条的原字节查找/unknown/新revision方案，应显式接入R4，而非称无计划。117项需按原注册条款及各审计表逐行分派实际验收，不能仅有WP级归属。H01硬禁用只控制运行风险、不关闭归档恢复完整目标；R4的隔离VR与真实AR仍分层，旧95门不重新执行。已安排协作者单独编写117映射，主agent负责实施细化与共享规划文件。

本轮按技能显式选择既有审计目录作PWF_PLAN_ROOT，resolver未返回命名计划，使用该目录既有三文件，不创建竞争root计划；子进程环境不冒称修改宿主hook pin。git diff无tracked变化，status显示本审计目录及既有临时文件等untracked并有全局ignore/.pytest_cache权限警告，保持它们不动。本轮不启用技能gated/attestation，也不读取本地会话历史。

## F010：R4减法与独立审查纠偏（2026-09-08）

R4调整的是活动编排而非原始目标：A合同、B位置透明、C瘦消费者/唯一生产入口、D安全运维，收入M独立。保留117项/GP/历史要求和旧反例；旧95门及其verifier只作R3历史，不再驱动R4。详细44个一级步骤和36组测试（12+8+8+8）见simplified-execution-plan.md及simplified-test-matrix.md，组内继续展开原领域步骤与反例，不是把所有断言减到36个。初稿导航误加为40，已由逐ID结构核对纠正，未删任何测试。

独立agent发现草稿“VR所有required”可能把尚待联网/自然AR的结果反向作为VR准入，另发现C本地签收误含worker、broker九源只挂M。已分隔离VR/真实AR层，C本地/加工/provider同包分栏，broker归C；D.SAFE不等C.AR亦不授worker绿灯，持续运行只等拟启用路线。新建快照为显式准备写动作，不能藏在query/open声称零写。独立修订复核accepted_for_planning_delta仅签两份R4文件，不是产品通过；transition由主agent通读审查，未冒称独立自签。

三仓根入口、旧总计划/手册及v5衔接已更新；旧正文与历史review保留。旧手册新增状态头导致当前hash变化属于本次授权文档变更，旧review仍仅绑定当时输入，冻结manifest/receipt/baseline不改。本轮未复验最新源码、启动worker或跑真实E2E。
