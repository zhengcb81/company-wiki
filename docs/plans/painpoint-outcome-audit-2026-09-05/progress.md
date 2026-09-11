# 审计进度

## 2026-09-11 夜：R4 阶段 A 首轮设计审查（A.DR **rejected** → v0.2 更正完成）

- **运行目录**：`revenue-forecast/assurance/runs/2026-09-11_r4-phase-a/`（在审计证据目录**之外**，符合 handbook §2.5/§3）。
- **owner 三项批准**：① A 阶段精确 DEV/数据读取许可；② `--help`-only command manifest；③ VR reviewer 指派。据此执行 **52 次 `--help` 探针**（全部 rc=0），把 CLI 表面积从"源码 grep 的 47"更正为 **41 顶层 + 10 嵌套 = 51 节点 / 47 叶子**。**未**越界：产品写入、`--dry-run`、真实数据命令、网络、删除、worker 恢复均未发生。
- **A01–A04 草案 v0.1 送 A.DR** → 独立复审（非作者会话）**verdict = rejected**：**8×P1 / 5×P2 / 3×P3**。复审确认的正向事实：12/12 输入哈希与字节数、三仓 HEAD、root 配置表、51 节点 CLI 结构、checkpoint 产物哈希、跨仓 spawn 引用、仓库/目录边界隔离。记录见 revenue 侧 `reviews/A.DR.json`。
- **P1 实质问题（均已就地更正为 v0.2）**：
  1. `symlink_policy` 被当作"已强制 fail-closed"——实际**只解析、从不读取**（全库 `is_symlink|reparse` 命中 0）＝**假保证字段**；
  2. 冻结的复用链 `reusable_root_kinds → is_canonical → priority` **不存在**：复用只看 `root.kind`（`resolver.py:782-786/933-940`），**显式 `reusable_for_filing: false` 无法关闭复用（fail-open）**；所谓 `priority` 分支其实是字符串字面量（`resolver.py:531`），真实排序在 SQL（`service.py:329/527`、`:643-653`）；
  3. `canonical_write_target` 的"无校验"结论**错误**：校验存在于 `policy_2x.py:49/121-131`，但**该 loader 无生产调用者**，而现行 `config.py` 直接**拒绝该字段** → **两套分叉的 root 准入实现**；
  4. `identify` 被列入只读面——`--refresh` 实为**网络 + 本地写**（`cli.py:1080-1087`、`security_identity.py:1007/348`）；
  5. 命令清单**漏 7 个叶子**（`worker-status/start/resume/pause/stop`、`derived-audit`、`import-portfolio`）——其中 `worker-pause` 正是该契约规则 R3 点名要防的动作；
  6. A01 的子进程面被**严重低估**（真实为 **7 模块 / 12 个 spawn 点**，含 `dayu_cli_adapter`/`adapter_process` 的**外部 provider 边界**），且 F-A01-2 引用了 `company_wiki_source.py` 的 **docstring 文本**当代码证据（已删）；
  7. A04 规则 R4（路径不入身份）与现行 `is_canonical` 选择键（含 `priority`/`root_id`/`relative_path`）**相矛盾** → R4 重述为**目标**并点名残留；
  8. 边界声明被文件系统证据挑战：生产库 `catalog.sqlite3-shm` 在 run 窗口内被写入（21:18:15）——**已归因**（v0.2 定案）：本会话**推送前的强制 gate**（revenue `tools/pre_push_gate.py` 的 real-data 套件对生产 catalog 只读跑 pytest）在 21:18:15 / 21:26:47 / 22:05:03 / 22:10:11 四处开库，另 22:00:02/18 两处为 22:00 每日任务；主库与 `-wal` 全程未变（无逻辑写入）。逐条证据见 revenue 侧 `assurance/runs/2026-09-11_r4-phase-a/boundary-audit.md` §1–§3。v0.1 的"零副作用"快照**未覆盖 `-shm`/`-wal`** → 覆盖盲区已修复；"独立边界观测"仍登记为**操作员动作**（作者不代签）。**同时更正**：v0.1 中"本会话未运行任何会打开 catalog 的代码路径"的更强说法**已撤回**——push 协议本身就会（只读）打开它。
- **v0.2 新增产物**：`inputs.json`（依赖/lockfile 哈希 + schema 常量）、`boundary-audit.md`（shm 证据/受控实验/归因限制）、被动观测脚本与产物（**不开库、不执行 CLI**）、快照覆盖扩展后的 manifest 证据。
- **阻塞项（需 owner/操作员）**：① **6 项 owner 裁定**（`symlink_policy`、`reusable_for_filing`、两套准入实现收敛、`privacy_class` 缺省、R6 owner、R4 严格读法）；A.DR 明确要求**先裁定再冻结 A02**。② 独立边界观测与 reviewer 身份戳记（需操作员）。③ A05/A06 的样本清单与**隔离副本**（生产 catalog **49,677,344,768 B**，禁止行为探针）。
- **边界**：本轮只写文档 + `--help` 探针；未运行产品测试、未改产品代码/配置/DB/任务/worker，未下载/LLM/删除；R4 整体仍 **NOT_IMPLEMENTATION_AUTHORIZED**。

## 2026-09-09 深夜：并发状态核对（V5 完成 / FC-705 门 / R9 批 3 范围修正）

- **Worker v5 独立轨道全部完成**（同仓 `docs/plans/source-catalog-worker-recovery-v5-2026-09-03/`，提交 `6559075`）：V5-0/V5-R/V5-1/V5-2/V5-3 全部 completed；正式冻结 51 项（48 导入 + 3 治理件）+ 三轴独立审查 `accepted`（SQL/性能、生命周期/安全、测试/DAG，共 13 份审查/关闭记录）；四轮整改关闭 **14 条 P1 + 3 条 P2**；`--verify-manifest` 9188 通过、`--self-test` 17 例/32 变异 + 4 默认模式 + 3 守卫全拒。**仍 PLAN_ONLY，不构成实施授权，不改变 R4 的 WP 授权状态。**
- **FC-705 门**：09-09 22:00 daily 触发成功（`20260909T210001Z`、ok=true、`legacy_hits=[]`），权威账本开 **period 9**（hits=0）；last-two = P7（23:59:41 ✗）+ P8（24:00:11 ✓）→ 仍 `close_gate_allowed=false`，**预计 2026-09-10 22:00 运行后**转 true。
- **R9 批 3 范围修正（本目录相关）**：09-02 口径「无生产读者 backfill/promoter」已失真——~~实测仅 `artifact_backfill.py` 零生产读者~~ 🔴 **2026-09-10 再更正：这一条也错了**。`artifact_backfill.py` 实为**自带运维 CLI**（`--mode dry-run|apply`）、被 3 个契约测试导入、FC-906 卡片标注「FC-901 工具，**不改**」、冻结 v5 基线有 ZR1005-C1~C4 验收行 → **当前没有任何候选满足"零读者 + 无冻结约束"的机械删除条件**；owner 2026-09-10 的"执行 3a"指令因前提证伪而**暂停**，随后 owner **同日正式撤销 3a**（`artifact_backfill.py` 定性为受 FC-906 卡片保护的运维工具），**未删除任何文件**。其余候选（`backfill_v2`/`portfolio_promoter`/`_scan_root_v1`/`legacy_bridge_enabled`）均有活跃调用者。批 3 自此**只剩 3b/3c**，需技术门 + owner 政策门并先给出替代路径与回滚。清单见 revenue 侧 [r9_batch3_checklist.md](../../../../revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/r9_batch3_checklist.md)。对 R4 的影响：`r4-unit-remediation-map.md` 中 CA-304/ZR-1009 的"R9 批3（已批准待 FC-705 门）"应理解为**尚需 owner 重新确认范围**，不能按旧清单机械执行。
- **GP-009 累积**：Daily **5/7**（09-06~09-10）、Weekly 0/2（下次 09-13 04:30）、Monthly 1/1、drill 1/1。
- **本轮边界**：只写文档 + 只读核对；未运行产品测试、未改产品代码/配置/DB/任务/worker，未下载/LLM/删除。详见 [current-delta-2026-09-09.md](current-delta-2026-09-09.md)。

## 2026-09-09：Phase 7 收尾（117 逐行映射 + 独立复核）

- 交付 [r4-unit-remediation-map.md](r4-unit-remediation-map.md)：117 行＝25 CA + 92 ZR，逐行给出原痛点/原审计结论/域/旧WP/R4归属/R4步骤/验收路由/当前结果（全为待取证）；生成后由父 agent 机械交叉核验（117=117、第2/3列 0 处不一致、0 断链、实施子步骤 88 条唯一）。
- 独立复核（非作者 agent）产出 [r4-remediation-detail-review.md](r4-remediation-detail-review.md)：结论 **accepted_with_findings**，P0=0/P1=0/P2=2。C1 定义层 104 条唯一子步骤、0 重复（88 实施 + 16 CL/AC 映射行）；C2 117 行一一对应、第3列 0 处不一致、当前结果列全待取证；C3 16 条相对链接 0 断链；C4 两份核心文档 SHA-256 未变（E0DCCD11…896467 / B90EF4D0…380F49）；C5 无产品文件改动，revenue R9 批1+2 删除属实。
- 两处 P2 已按建议修正：F1（map 中 ZR-301–306 的组级引用落为 W04.01–.06/W06.01–.06/H01.01–.09）、F2（本目录 steps 路线表裸域标签改为「H01 风险控制（组）」「FC903 资格修复（线）」）；计数口径在 map 规则6写明（88 实施子步骤 + 16 映射行 = 104 编号项）。
- 本轮只写文档：未运行产品测试、未改产品代码/配置/DB/任务/worker，未下载/LLM/删除；PLAN_ONLY 边界不变。

## 2026-09-08：六类痛点实施细化（本轮进行中）

- 依planning-with-files选定既有审计目录，主agent独占共享三文件；协作者仅写117逐项映射，另一非作者独立审查两份新文档。
- 新增r4-remediation-steps.md初稿：88子步骤；H01硬禁用/可信归档/恢复/回收资格分栏，WP02–10实际consumer与真实测试、FC903原对象查找/unknown/新revision、117子条款执行规则、9泄漏/7验收、完整E2E和旧95门退出。
- 初步结构核验88唯一子步骤，原R4计划和矩阵SHA与历史review相同；尚未签本轮独立复核，产品测试未执行。
- README新增当前阅读入口；旧冻结计划/收据/95门原文件与产品配置/数据/worker不动。

## 2026-09-06至09-07：后续文档同步与实施细化完成

- 用户新增授权是同步其他planning文档及细化步骤；保护产品、冻结历史、生产状态不改的边界仍有效。活动23份文档已插入/精确更新状态，修改清单与hash见document-sync-validation.json；旧根三件套/冻结日期包不重写，由PLANNING_STATUS/CURRENT_STATUS覆盖解释。
- 两路手册agent在用量限制中断前已保存完整execution-data-plane/model-plane；9/7恢复由独立reviewer完整读回，不把中断算完成review。主agent完成handbook/control-plane、机器DAG和只读validator。
- 15包共160个编号小步骤（数据70、模型48、控制42）；每包G0–G5独立review，另5个安全签收门。真实来源/真实进程、独立oracle/来源→参数→输出、费用/文件/DB前后对账、失败停止/回滚分别细化，mock只可作为诊断不能关闭真实E2E。
- 独立计划review提出WP06.G3与S06自等、WP09依赖后续WP13来源两个问题；R3明确受控隔离进程协议和本包独立建立manifest，复核accepted_for_planning，7份输入hash绑定。没有实施或运行级PASS。
- 9/7发现其他任务提交：wiki d92f8bf、revenue6682ecf；旧closure删除、daily失败与ledger改路径均写current-delta覆盖，而非继续复述9/6“未删除/ok=true”。35旧选定hash中5漂移、30未变；本审计未作这些代码/运行动作，相关旧反证须新HEAD复验。
- 验证：46冻结唯一输入hash匹配；v5 import 54/54通过；静态DAG95门/15包及cycle/unknown/empty三个负例通过；23活动文档+审计Markdown合计251链接无缺。旧verify_sync快照不能用于强迫合法新状态回退，未改旧库存hash。
- 未实施真实E2E、生产SQL、下载/LLM、worker/任务、自启动、删除、push或安装。后续先精确DEV与G0/G1；其他运行动作各自批准。

## 2026-09-05 启动

## 2026-09-07至09-08 R4规划交付（当前接班点）

- 用户要求按数据湖减法调整planning。继续使用planning-with-files，在既有独立审计目录增加R4执行、真实测试矩阵、迁移表、独立审查与文档验证记录；只调整规划，没有新建另一套竞争实施目录。
- 形成A合同/B位置透明/C瘦消费者与唯一生产/D安全运维+独立M；44一级步骤，每步输入/产物/检查点/停止；DR/VR/AR独立审查及高风险动作、1→3→7批次审查保留，取消旧95门共同编排。36组测试（12L+8P+8O+8M）继续继承全部非同义原反例和真实层级。
- 独立审查提出VR/AR互等、C本地混入worker、broker目标误挂M；已修并获accepted_for_planning_delta。D.SAFE不授运行、snapshot写须独立动作、真实网络/自然期不作自身VR前置。报告绑定两核心文档hash；主agent审查迁移表但不冒称作者独立自签。
- 三仓PLANNING_STATUS、旧R3总计划/手册、GP六页与CI协议、filing E2E、v5衔接、诊断/审计入口已更新。旧手册状态头变更会改变当前hash，历史签署不被重写或解释成签新文件；旧DAG/verifier不用于R4。
- 文档核验：23页150本地链接零缺失；44步唯一、WP00–14完整、36测试ID唯一；两核心hash匹配review；46个冻结唯一输入SHA及v5 54份SHA/size均匹配。随后CI路由和收尾日志另作本地链接检查。详见r4-document-validation.json。检查不是产品测试，未逐117项复跑。
- 过程中PowerShell brace/猜错ci_root_fix子目录失败均无写；使用rg精确文件修正。测试组40为算术错误、全页正则39包含引用行，均改为定义表36；没有删case凑数。
- 本轮未改产品源码/配置/库/raw/任务/worker状态，未下载/LLM/启动/真实E2E/删除。其他任务可能继续变化，9/7代码快照不代表此刻HEAD；未来从A01重锁输入。本次文档任务完成，停在等待精确实施授权，不自动实施。

## 以下为历史阶段日志

- 用户明确将任务改为实际效果审计，允许写新审计目录，不允许修改既有目录内容。
- 已读取 skill、原始 P01–P11、ZR 92 项；CA 合并输出截断，待补全。
- 已发现旧入口页自相矛盾/状态滞后线索；不就地修改。
- 尚未执行产品测试、启动 worker、网络请求、数据库写入或任务变更。
- 接续：建立 CA/ZR/GP 逐项账本，按真实生产路径审计并记录反证，最后详细规划修复。
- 已完整补读 CA 25 项。CodeGraph 宽泛上下文命中不精确，改用具体 closure/scenario 符号及文件。
- 已启动三个有明确只读范围的独立代码探索，输出限定本目录的 wiki/filing/revenue 审计文件。
- 全仓 AGENTS 枚举遇13个 sibling临时目录和本仓pytest缓存拒绝访问；不绕过权限，不把这些临时目录当生产源码审计完成。
- 三仓git均提示全局ignore读权限不足；使用命令级safe.directory只读查询成功，未修改全局配置。
- 新运行记录表明源码/调度正在别的任务推进，本审计以文件hash/观测时间为证据，旧线索均重新核对。

## 2026-09-06 恢复

- 上轮三名独立审计均被服务用量限制中断；保留的是阶段发现，不是完整审计结论。现已从各自落盘断点续查。
- 本审计AST探针首次运行根路径parents层数错误，导致FileNotFoundError；无产品调用或写入。错误输出误存为probe-results.json，已安排本轮修正脚本路径并用有效JSON替换（仅新目录）。
- 重新核对所有当前运行证据；不沿用9/5前旧GP008参数错误结论。
- AST负例已成功，未来时间/缺tier证据/部分skip/空stdout/权限误分类全部复现。先前同patch delete+add同一路径被工具拒绝，改为Update；有效JSON已落盘。
- 117项完整receipt库存stdout超过工具返回上限；未把截断数据当完整库存。改为有明确excerpt标志的紧凑元数据，并按批次读取原证据。
- 117项逐项索引完成，初始汇总53 CONTRADICTED、58 PARTIAL、6 HISTORICAL_ONLY（这是原完整目标判定，不是53个模块全部错误）。GP10与历史空间/section/portfolio/v5项目另列。
- 独立复核确认A02/A04/A05/CA206，已吸收P2证据层级建议：machine_valid不等于实际state/CI放行，原select stub负例由真实schema+hash内存联合probe补强。
- 新增H01自动prune风险：生产worker调用apply=True，空旧归档目录足以触发全retired删除；已有测试反而断言此行为。未运行任何删除/数据库命令。
- v5阈值已完整阅读；它是历史v4导入最低标准，不是本轮授权或正式v5冻结。后续计划不得降格为“先修SQL就恢复”。

## 2026-09-06 审计与计划交付

- 完成三仓117项登记目标、GP10、历史继承与空间治理的限定只读审计；动态未验证范围在README和各分报告明示，没有运行全量生产测试。
- H01独立复核完成。编写15包修复计划，每个G0–G5有独立agent审查、负例、停止与授权门；原目录/主线/v5均不动。
- 计划R1独立审查提出2项P1/4类P2；R2补精确gate依赖、12a/12b/12c、作用域安全门、授权subtype、稳定归档snapshot/clock、恢复对象和缺失RED。独立复核verdict accepted_for_planning_delta；绑定rawSHA `07a0741d1ebe8a7ac82798efc9f0e33fcc77dd20d8119a703d9a097be24f562d`，未将计划通过算产品通过。
- 最终检查：5个JSON解析成功；coverage只输出摘要重新核实117/missing=[]（此前完整stdout超长截断，不据截断部分推断）；35个选定源码/证据SHA全部与快照相同；三仓HEAD及tracked dirty路径与既有记录相符。未对49GB生产数据库作hash/查询。
- 新增README作为交付入口；task_plan四阶段完成仅代表本轮审计和计划。未改产品代码、旧计划、配置、DB、任务/启动项，未恢复worker/网络/LLM/删除。其他线程既有修改保持原样。
- 19:54:40 UTC最终链接检查：146处同目录Markdown/JSON/Python产物链接无缺失；总计划SHA与独立R2签收完全一致。该检查不覆盖外部URL或所有历史源码行号。
- 后续必须先取得精确DEV批准，再做WP00/01设计与独立门；运行/外发/调度/自启动分别授权。无需继续无界审计来假装推进，当前交付结束。
