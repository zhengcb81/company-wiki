# 三仓原始痛点与完成真实性审计

## 目标与授权边界

以原始 P01–P11 痛点、CA/ZR 117 项及后续 GP 项为索引，逐项审计已完成主张是否实现用户结果。全部发现、证据、审计脚本和后续修复计划只写本新目录。不得修改原项目代码、已有计划、配置、数据库、收据、任务或 worker；不得运行下载、生产处理或恢复后台工作。独立计划不并入主线。日期：2026-09-05。

## 判定规则

## Phase 7：六类遗留痛点实施细化 — completed（2026-09-09，仅文档）

- [x] 在既有R4下展开H01、WP02–10、FC-903的操作顺序、输入产物、失败恢复与独立验收（88条实施子步骤＋16条CL/AC映射行＝104条编号项）。
- [x] 建立117个原ID逐行修复/验收规划映射（[r4-unit-remediation-map.md](r4-unit-remediation-map.md)：117行＝25CA+92ZR，结论与[unit-ledger](unit-ledger.md)逐字一致，当前结果全为待取证）。
- [x] 显式映射9个架构泄漏/7类真实验收，明确旧95门的历史地位和R4实际执行顺序。
- [x] 独立复核新增文档（[r4-remediation-detail-review.md](r4-remediation-detail-review.md)：accepted_with_findings，P0/P1=0；F1/F2两处P2已按建议修正），核ID/链接/核心历史hash与未授权写入边界；入口已更新。

## Next Step

等待精确实施授权（DEV/数据/运行各自批准），从 R4 A01 重锁三仓输入开始。Phase 7 只完成规划细化，不构成产品实施或真实测试结果；原R4两份被审核心文档及历史签署字节不变。

### 2026-09-09 深夜并发状态核对（只读 + 文档）

- **Worker v5 独立轨道已全部完成**（同仓 `source-catalog-worker-recovery-v5-2026-09-03`，提交 `6559075`）：V5-0/R/1/2/3 completed，冻结 51 项，三轴独立审查 `accepted`（SQL/性能、生命周期/安全、测试/DAG）。它是 R4 中 worker 相关 WP 的**版本合同/冻结输入**，但不改变 R4 的 `NOT_IMPLEMENTATION_AUTHORIZED`，也不替代 H01 前置。
- **FC-705 门**：09-10 22:00 daily 成功但 P9 窗口 **23:59:52（差 8 秒）** → 仍 false；owner 已授权根治（revenue `41117ce`：runner 真实等待补足 24h），**门预计 2026-09-12 22:00 确定性打开**。见 [current-delta-2026-09-09.md](current-delta-2026-09-09.md)。
- **R9 批 3 范围修正**：~~实测仅 `artifact_backfill.py` 零生产读者~~ → 🔴 **2026-09-10 更正：该结论已证伪**（该模块自带运维 CLI、被 3 个契约测试导入、FC-906 卡片标注「FC-901 工具，不改」、冻结 v5 基线有 ZR1005-C1~C4 验收行）。其余候选（`backfill_v2`/`portfolio_promoter`/`_scan_root_v1`/`legacy_bridge_enabled`）均有活跃调用者 → 批 3 需技术门 + owner 政策门并重新拆分（**3a 作废**，只剩 3b/3c，二者均需先给出替代路径与回滚，当前**没有任何小批满足机械删除条件**）；`r4-unit-remediation-map.md` 的 CA-304/ZR-1009 行按此理解（清单见 revenue `r9_batch3_checklist.md`）。
- 本轮未运行产品测试、未改产品代码/配置/DB/任务/worker。

## Phase 6：按虚拟数据湖减法调整为R4 — completed（仅规划交付）

用户已要求依据简化建议调整规划，授权仍仅文档。R4以四个增量为主路线：统一只读合同、位置透明读取、消费/生产解耦、受控运维收尾；收入模型单独轨道。保留原始发现/测试，不再把R3的95门当全部工作的共同前置。

- [x] R4四增量+独立M、44个一级步骤、36组测试及组内旧领域步骤/反例；WP00–14完整迁移，117项原目标不批量关闭。
- [x] 三仓根入口、GP/CI/E2E活动说明、旧总计划与三手册、v5/诊断入口更新；R3正文/签署保持历史含义，冻结46唯一输入及54份v5文件hash仍匹配。
- [x] 独立复核修正VR/AR互等、本地/worker混验及broker归属；accepted_for_planning_delta仅绑定两份R4文档。主agent另审transition；44步/36ID/15WP结构与150本地链接通过，记录见r4-document-validation.json。

下一步（未来另获实施授权后）：R4 A01当前三仓与副作用基线，A02–A05冻结合同/真实oracle；不可从旧WP00/01/G门重新领取。D安全准备按实际依赖另行推进；本次worker/产品/真实E2E全部未动，不存在自动进入实施的后续动作。

### 2026-09-06 后续授权变更

用户现明确要求同步三个仓库主目录及子目录的其他planning文档，并进一步细化实施步骤。本轮允许文档一致性修改，不再限于新目录；产品代码/配置/DB/worker/任务、历史收据和签署证据仍不改。旧阶段记录保留历史意义。同步必须保护并发修改，对冻结证据型计划用外部状态说明而非破坏其hash。兄弟仓写入须通过环境权限，拒绝时留精确补丁并报告，不绕过。

## Phase 5：跨仓计划一致性同步与执行手册增强 — completed（文档交付）

- [x] 枚举三仓planning文档，区分活动入口/当前计划/历史冻结证据；document-consistency-review记录差异及范围限制，未重读全部历史正文。
- [x] 同步23份活动主/子目录状态；冻结46唯一输入及54份v5基线保持原字节。9/7并发代码/运行漂移另建current-delta并覆盖旧快照，不重复执行或追认。
- [x] 15工作包细化为三份分面手册和接班手册，逐阶段review/checkpoint、真实数据E2E、回滚/停止；95个计划门机器展开，结果全部pending。
- [x] 独立审查修正G3自身依赖和下游manifest互等后accepted_for_planning；3个结构负例拒绝，251链接无缺。机器结构PASS不等于产品测试/授权验证。

分别评估实现、生产接线、真实结果、证据有效性。结论使用 RESOLVED_CURRENT（当前证据完整）、PARTIAL（局部解决）、CONTRADICTED（存在反证）、HISTORICAL_ONLY（仅历史）、UNVERIFIED（证据不足）、SUPERSEDED（后续边界取代）；不得把未验证写成失败，也不得把 accepted 写成已解决。所有最终判断必须给出文件/函数/收据、检查方法、推理与局限。

## Phase 1：恢复原始目标、完成项清单与只读基线 — completed

- [x] 确认三个仓库与新目录限制，读取 planning-with-files。
- [x] 读取原始 P01–P11 和 ZR 工作项注册表。
- [x] 完整读取 CA 注册表、GP 状态；历史继承关系已逐项整理于legacy-inheritance.md。
- [x] 记录 HEAD、dirty、证据时间、嵌套 AGENTS 和全部完成项清单。117项/351主要receipt元数据/197场景已落盘；44plan input hash+size通过。旧71FC含5closure+10waves已建继承表。

## Phase 2：逐项核查实现与真实结果 — completed（只读审计范围）

- [x] CA 完成保证与旧完成项继承；证据不可由自签代替独立复核。
- [x] company-wiki：只读、安全、复用、processing demand、worker、broker、运行资源。上游601–604与旧空间治理另补专篇；未重跑生产的部分明确列限。
- [x] filing-fetch：多根、版本新鲜度、下载权限、失败恢复、跨仓真实消费。
- [x] revenue-forecast：模型/矿山、验证发布、回测、真实 E2E。
- [x] CI/调度/观察窗口/回滚/legacy 删除；逐项回填 CA/ZR/GP。
- [x] 只执行经审阅无生产副作用的静态或隔离探针；无法验证明确列缺口。

## Phase 3：审计覆盖与反证复核 — completed

- [x] 每个注册项有结论、原痛点映射和证据；抽样与全量边界明确。117/117索引无缺项；不是117项生产重跑。
- [x] 复核关键结构问题，区分局部单测与端到端成果。assurance四项独立复核通过技术观察、P2措辞已吸收；旧空间prune独立核验完成，见retention-independent-review.md。
- [x] 全部范围的只读审计结论与未验证限制已经记录；H01独立复核确认风险但没有误删已发生证据。不提前执行修复。

## Phase 4：详细修复计划及交付 — completed（审计/计划交付，不是产品完成）

- [x] 按依赖排序15个工作包；明确可改文件、禁止动作、输入输出、测试夹具、失败停止条件、回滚；R2增加精确gate依赖。
- [x] 每个关键节点安排独立 agent 审查（实现者不得自审），列审查材料、反例及签收门槛。
- [x] 真运行、外发、费用、启动/任务修改必须有单独授权；自然观察窗口不得伪造。
- [x] 检查新目录文档一致性与实际写入范围，报告已证实结论和未验证限制。117索引无缺项，5个JSON均可解析，35选定hash无漂移，三仓HEAD/既有tracked dirty名单相符；README提供导航。R2获独立accepted_for_planning_delta，全部WP仍NOT_IMPLEMENTATION_AUTHORIZED。

## 错误与约束

- 本轮细化：send_input首次误用id字段被schema拒绝，无消息发送；改为target成功。若合并读取输出截断，按章节补读；git全局ignore与旧pytest缓存访问警告不绕过，未影响指定规划文档。rg未找到docs下AGENTS以exit1返回，不当产品故障。

- 2026-09-08：PowerShell不支持本次使用的`{README.md,task_plan.md,...}`路径brace写法，命令解析失败未访问目标；已改显式路径和普通rg目录参数，不重试原命令。
- 同日补记：后续单项brace路径再次被rg误解，改为明确目录+`-g`筛选；误猜ci_root_fix/task_plan.md不存在，rg实际定位为ci_root_fix.md。测试计数最初把12+8+8+8误加40，且正则误计第6节引用行；限制定义表后36唯一ID全齐，修正导航/报告算术，不改变用例。

| 事件 | 处理 |
|---|---|
| sibling 根 AGENTS.md 不存在 | 非项目失败；继续检查嵌套指令，不重复读取不存在路径 |
| CA/ZR 合并输出被截断 | 已单独补全CA，之后使用分段读取；coverage大JSON再次截断后改只输出total/missing摘要 |
| 其他线程可能并发修改 | HEAD/hash 是观测点；写操作限定新目录，不重置现有 dirty |
| AST探针parents路径层数错误 | 仅FileNotFound；修正为parents[3]，再运行；错误输出不作为有效测试证据 |
| 9/5独立agent服务用量中断 | 9/6从已有阶段记录续查，不把中断视为审查通过 |
