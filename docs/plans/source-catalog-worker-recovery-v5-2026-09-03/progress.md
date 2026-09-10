# Worker v5 — 进度日志

## 2026-09-09：V5-1 完成（版本合同 rev4 获独立复审 accepted）

- 版本合同经 **rev1→rev4 四轮**：rev1 独立设计审查 **rejected**（2×P0/4×P1/4×P2，见 [rev1](v5-version-contract-review.md)）→ rev2 **accepted_with_findings**（[rev2](v5-version-contract-review-rev2.md)，F1–F6 全闭、新增 G1 阻断）→ rev3/rev4 闭合 G1 与 H1–H3（[rev3](v5-version-contract-review-rev3.md) / [rev4](v5-version-contract-review-rev4.md)）→ **rev4 复审 verdict = accepted，V5-1 关闭，V5-2 可开始**。
- 最终交付：`v5-version-contract.md`（rev4；§5.1 19 项必填字段含 `evidence_tools[]`；§5.2 冻结集合 = 48 导入 + 3 v5 自有治理件 = **51**，含派生规则与 checker 路径规则；§7 N1–N17）、两份证据（可字节复现）、两个证据工具（含只读 `--check`，**字节级**比较，EOL 漂移即失败）、四份独立审查记录。
- 复审独立复现：三个证据文件与提交字节逐一相同（inventory.json `b7612e0f…`、inventory.md `0240a85f…`、equivalence.json `79ac6ca4…`）——**这三个哈希是 V5-1 时点（提交 `2fbbe5e`）的值**，V5-2 冻结时证据已按 D4 重生成（现行值见 [v5-freeze-record.md](v5-freeze-record.md) §1 与 manifest `evidence`）；两工具 `--check` 退出 0 且不写盘。
- 遗留（非阻断 P3，已修）：K1 `evidence_tools[]` 条目类型补为 `{path, sha256, size_bytes}`；K2 `--check` 改为 `read_bytes()` 字节比较（EOL 漂移必失败）。
- 本轮只写 v5 目录文档与只读证据工具：未改协议语义、未生成正式 manifest、未运行旧 checker、未触碰 worker/配置/数据库/任务。

## 2026-09-09：V5-1 版本合同（rev2，待独立复审）

- 交付 [v5-version-contract.md](v5-version-contract.md)（rev2）、[版本引用枚举](v5-version-reference-inventory.json)、[基线等价性](v5-baseline-equivalence.json)：
  - **方案裁决**：拆分 `protocol_revision`（v4）与 `freeze_generation`（v5）两轴，不整体升 v5——依据 29 个 `$id` 的后缀分布 `:v4`=14/`:v1`=12/`:v5`=2/`:v2`=1（整体升版会与既有 `journal-manifest:v5` 撞名）。
  - **引用枚举**：59 个文件（baseline 54 + v5 根 5）；44 份含 `v4`、13 份含 `v3`；10 份引用已退役旧目录、9 份引用旧 checker。
  - **基线等价**：**21 exact / 17 crlf_only / 10 unproven**。本页与 `findings.md`、`task_plan.md` 原写的「16/11」为笔误，已更正；`baseline/history/progress.v4.md` 属冻结历史，保留原字并在此披露。
  - **v5 manifest schema**：新建 `plan_manifest.schema.v5.json`（`$id …:plan-manifest:v5`、`schema_version 3`），字段见合同 §5；导入的 v4 manifest schema 不校验 v5。
  - **负例**：N1–N15，待 V5-2 以机器检查 + 测试 ID 实现。
- 独立设计审查 rev1 结论 **rejected**（2×P0、4×P1、4×P2），审查文件 [v5-version-contract-review.md](v5-version-contract-review.md)；rev2 已逐条修订，待复审。
- **两项现状更正（实测）**：
  1. 本目录已随 R4 语料入库（wiki `f23ad1b`）；README/findings 的「未被 Git 跟踪/tracked=0」不再成立（精确 tracked 数以 `git ls-files` 实时查询为准，本页不写死），V5-2 必须先重验 Git/index/属性/并发写边界。
  2. **旧目录 `source-catalog-worker-recovery-2026-08-22/` 已复活**：38 文件、tracked、clean、mtime `2026-09-07T18:08:52Z` UTC（本地 19:08:52+01:00），字节与 v4 冻结 0/38、与 v5 基线 0/38 相同——与「已移入回收站」表述不符，按合同 N9 处理（并列权威风险）。
- **rev3（同日）**：按 rev2 复审的 G1 修订**冻结集合定义**（`normative_files` = 48 导入 + 3 个 v5 自有治理件 `plan_manifest.schema.v5.json`/v5 checker/`.gitattributes` = **51**；`frozen_set_composition` 显式记录；证据工具记入 `evidence_tools[]` 而非 normative；新增 N16/N17），并统一 `equivalence` 枚举为 `v4_exact/crlf_only/unproven_new_baseline/v5_own`（证据 JSON 同步重生成）、把旧目录 mtime 改为 UTC、不再在正文写死 tracked 数（G2–G4）。
- 本轮只写 v5 目录文档：未改协议语义、未生成正式 manifest、未运行旧 checker、未触碰 worker/配置/数据库/任务。

> 2026-09-06文档同步记录：只更新本目录活动README及三件套的跨计划路由，baseline54份/import manifest/reviews保持原字节；没有新增正式plan_manifest，没有推进V5-1/2/3或实施worker。当前统一依赖见[整改总计划](../painpoint-outcome-audit-2026-09-05/remediation-plan.md)。

## 2026-09-03：用户授权退役旧 v1–v4 目录（已完成）

- 用户明确要求v5启用后删除原v1–v4计划。本轮精确候选仅为平行旧目录
  `docs/plans/source-catalog-worker-recovery-2026-08-22/`；保留v5及其已核验基线、原调查报告，
  不碰源码/配置/主线计划/worker。
- 正在做路径、reparse、逐文件副本和引用预检；计划优先移入Windows回收站，不执行不可恢复擦除。
- 首次库存核对fail closed：旧目录现有54个文件，导入manifest映射旧目录文件为53个。尚未删除，
  下一步只读定位额外文件及其来源，不能直接跳过数量差异。
- 已派独立agent进行删除范围与副本完整性预检；只有范围明确、所有内容有可恢复保障后才执行。
- 差异已定位为`__pycache__/plan_consistency_check.cpython-313.pyc`（88831 bytes，SHA-256
  `43400901a8c84470a3cb70ed220eb4382249d5b2a2eed4537cf39d1ba208f669`）；它是生成缓存，不是新增
  计划正文。53份计划/审查文件均在v5有精确副本，缓存明确列为`DERIVED_CACHE_RECYCLE_ONLY`，
  随完整旧目录进入回收站，不永久擦除，也不改导入manifest/已核验baseline来塞入缓存。
- 独立预检确认v5校验器只读取新目录，旧source路径只是历史字段；移除旧目录不会破坏校验器。
  初次BLOCK仅因53/54副本差异，已明确上述生成缓存例外并提交复核。
- 已保存精确54文件清单、hash/size、53份v5副本映射与缓存例外至
  `reviews/old-plan-retirement-inventory.json`；清单状态PREPARED_NOT_EXECUTED，不表示已经删除。
- 独立reviewer复核后返回SAFE_TO_RECYCLE，关闭唯一缓存BLOCK；库存SHA-256为
  `68a039b59dee1a8ad452c0214166f75b10254bb5194da705f4d4bd4642d3632b`。
- 已执行严格路径/54文件hash副本再核验后的Windows SendToRecycleBin；API成功、旧路径absent，
  回收站同名目录及原位置匹配已确认。没有改为永久擦除，没有清空回收站。
- 删除后verify_import.py仍54/54 PASS；原报告及v5 import manifest hash未变。38个原tracked文件
  在Git呈删除状态，没有代用户stage/commit；v5仍独立保留。
- 已更新README/task_plan/findings并新增`reviews/old-plan-retirement-result.md`，明确v5是唯一活动
  目录，历史source路径无需存在。本节早先PREPARED清单保留原样，实际结果以该result记录为准。
- 本次未改项目实现、生产配置/数据库、主线计划、Git设置/hook或worker；下一步仍为V5-1版本合同。

## 2026-09-03：新目录创建

- 已读取 planning-with-files 技能全文。
- 已确认新目录不存在、没有 tracked 路径；仅创建本目录的 README、task_plan、findings、progress
  和局部 .gitattributes。
- 当前：V5_BASELINE_IMPORT_IN_PROGRESS；尚未复制基线，尚未创建正式 v5 manifest。
- 下一步：精确名单复制、前后 raw hash 验证、保存导入清单、独立只读导入审查。
- 原 v4、项目实现、生产配置、数据库、主线计划、Git 设置/hook 和 worker 均不改动。

## 2026-09-03：导入完成，独立复核待完成

- 已逐字节复制54份明确文件，无递归目录复制或旧文件移动；所有源前/源后/副本SHA-256相等。
- 固定导入manifest SHA-256：`da7d116e8c692d6311411c7390bec4278b59666a771823672f53e9b0f6567e4a`。
- 已添加仅访问新目录文件的verify_import.py；两次运行均54/54 PASS，明确输出IMPORT_ONLY。
- 61路径/244项有效Git属性全部unset，tracked=0；未运行git add/commit/stash/checkout/hook。
- 更新README的一次多文件patch因无关末尾上下文不匹配而整体拒绝；只读确认没有部分写入后
  缩小上下文重试成功。后续校验通过。
- 当前阶段：V5_BASELINE_CAPTURED / IMPORT_REVIEW_PENDING；正式v5版本迁移和三路复审尚未开始。
- 下一步：独立agent核验同一导入manifest、54份副本、只读检查器、原目录边界与活动/历史标记。

## 2026-09-03：V5-0完成

- 额外20项纯内存helper检查通过：有效/非法路径、类型错误和duplicate JSON；没有fixture或生产写入。
- 独立reviewer `/root/v4_test_dag_review`完成54/54副本、54/54当前来源、路径/reparse、精确集合、
  旧manifest对应、属性/未跟踪状态与检查器核验，返回唯一`IMPORT_REVIEW_PASS`。
- 已保存`reviews/import-review-2026-09-03.md`，同一reviewer回读后返回`FAITHFUL`，报告SHA-256为
  `baa64f7b4749c13b4f8188e4982a9e3fa907f692e776c37014f4dd2e57490e43`；确认后不再修改该报告。
- V5-0标记completed；当前为`V5_BASELINE_READY / VERSION_CONTRACT_PENDING`。V5-1/V5-2尚未开始，
  没有正式plan_manifest.v5.json，没有三路正式技术审查PASS，更没有实施或worker恢复授权。
- 本轮写入全部在新v5目录；原v4目录/manifest/报告、项目源码/配置/数据库、主线计划与worker不动。
- 下一次从本目录README→task_plan→findings→progress恢复；先运行verify_import.py，再进入V5-1。

## 2026-09-09：V5-2 冻结 + 三路独立审查 + V5-2.1 整改

- V5-2 冻结：新建 `tools/v5_plan_consistency_check.py`（复用导入基线全套检查 + v5 检查 + N1–N17 机器检查 + `--self-test`）与 `tools/v5_freeze_manifest_build.py`（生成器，**不入冻结集**）；生成 `plan_manifest.v5.json`（51 项 = 48 导入 + 3 治理件）与 `plan_freeze_check.v5.txt`（172 字节、0 个 CR）。
- 首轮冻结 `454f632`：预冻结 7658 checks、`--verify-manifest` 8866、`--self-test` 17/17；边界 B1–B6 逐项实测（204 行属性全 unset、旧目录 38 文件干净）。
- 三路独立审查（SQL/性能、生命周期/安全、测试/DAG）各自只读、独立复算 51/51 哈希与 B1–B6，不共享快照：三份均 `accepted_with_findings`，**无 P0**，共 **9 条 P1**（N6 只核对标签不复算、导入字节只锚在可写捕获记录、N8 未绑定本 checker 真实运行、command 子串匹配、`baseline/plan/*` 非递归、N11 后缀匹配+静默回退、N9 判据只认路径存在、v4 的 reparse/包含路径安全不变量被整体丢弃）。
- V5-2.1 整改冻结 `917b8d8`（`85044ed` 提交记录）：逐条修根因 → 预冻结 **7710** checks、`--verify-manifest` **9174** 通过、`--self-test` **17 例 / 27 变异**在「全检查」与「仅该编码」两种模式下全部被拒；新增 manifest `evidence` 字段绑定两份证据输出、N9 机器可读处置载荷（`NON_AUTHORITATIVE` + 目录清单摘要复算）、`V5-PATH-SAFETY`、`V5-SET-NESTED`、N10 fail-closed（未跟踪或改写即 red）、N8 在真实树重跑默认模式逐字节比对。
- 逐条整改与验证见 [v5-freeze-record.md](v5-freeze-record.md) §7；偏差 D1–D11 与残余风险 §6 如实记录（含未删除未加锁的旧目录、pre-commit hook 机制、活动文档引用不受覆盖、`reviews/` 绝对路径按设计保留）。
- 状态：`FROZEN_FOR_INDEPENDENT_REVIEW`；待三路复审各自确认其 P1 已闭。**未实施任何 worker 修复，未触碰源码/配置/数据库/任务，未恢复 worker。**

## 2026-09-09：V5-2 完成（三轴复审全部 accepted）

- 整改共四轮：V5-2.1（9 条 P1）→ V5-2.2（2 条新 P1）→ V5-2.3（3 条新 P1）→ V5-2.4（3 条 P2），每轮都由三路独立审查以**自己的复现脚本**复核，不采信作者记录。
- 关键整改（全部根因级）：N6 逐件按字节复算等价类别；N7 增补 v4 冻结 manifest 锚并由**冻结内代码**钉扎 6 份历史文件；N8 以 manifest 命令（含 `-I`）重跑并逐字节比对；N9 改为候选枚举 + 机器载荷 + manifest 绑定；N10 比 **HEAD** blob（非索引）且未跟踪即 red；N11 取代链恰好两条；N13/`V5-SET-NESTED` 递归含空目录；`V5-PATH-SAFETY` 恢复 reparse 不变量；`V5-TOOLS-EXACT` 枚举 `tools/` 全部文件；启动守卫要求隔离解释器（覆盖 `script`/相对路径/`-m` 三形态）。
- 最终冻结（提交 `4f4dea1`）：预冻结 **7720** checks、`--verify-manifest` **9188** 通过、`--self-test` **17 例/32 变异 + 4 默认模式 + 3 守卫**全拒；51/51 冻结项哈希与字节一致；`plan_freeze_check.v5.txt` 172 字节、0 CR。
- 三轴结论：SQL/性能 `accepted`、生命周期/安全 `accepted`、测试/DAG `accepted`（均无 P0/P1；剩余项为记录已声明的残余风险 §6.3/§6.4/§6.9）。
- 已知非阻断后续（V5-3 移交项）：`--self-test` 墙钟随轮次增长（11s→89s）——**在 generation v5 内结构性不可行**（改 checker 破 N5 哈希绑定、加 `tools/` 文件破 `V5-TOOLS-EXACT`），已搁置至 v6（见冻结记录 §8 SQL-OBS-3 与 §9 v6 清单）；`frozen_at` 无法机器锚定（§6.4）；`reviews/old-plan-retirement-inventory.json` 按合同 §6.2 不改字节（含绝对个人路径，无凭据）。
- **V5-2 完成不授权实施**：本计划仅可作为未来实施的输入；worker 仍暂停，源码/配置/数据库/任务未动。

## 2026-09-09：V5-3 交接完成

- [README.md](README.md) 重写为唯一活动入口：阅读顺序、冻结与验证命令（含期望输出与 `-I` 要求）、历史索引（13 份审查/关闭记录）、只读复核结果、残余风险、实施顺序指向冻结语料、明确不授权。
- 只读复核 worker 状态：`worker_control.json` `desired_state=paused`；启动器末条事件 `exited/persistent_pause`（2026-08-20T21:43:37Z）；无 worker 进程；无相关计划任务（`CompanyWiki Source Catalog` 未注册）；HKCU/HKLM `Run` 与启动文件夹无条目；`scripts/source_catalog_worker_at_logon.{ps1,vbs}` 存在但未被任何入口引用。
- 活动文档（README/task_plan/findings/progress）更新后 `--verify-manifest` 仍为 `PASS: 9188 checks` —— 证明 D4 的"证据范围只含冻结后不变文件"设计有效。
- V5-0/V5-R/V5-1/V5-2/V5-3 全部完成；本目录进入**等待用户决定并入或实施**的稳定状态。

## 2026-09-10：V5-3 交接双审 + P1 关闭（本阶段收尾）

- **两名非作者独立审查并行复核**（互不共享结论）：
  - **冻结态保真度轴** → `accepted_with_findings`，**无 P0/P1**：独立复现默认 7720（stdout 172B/0 CR/sha `5e60611c…` 与产物逐字节相同）、`--verify-manifest` 9188、`--self-test` 17/32+4+3（73.6s/72.4s）、无 `-I` 时 exit 1 且 stdout 0 字节；51/51 哈希+字节、52/52 worktree↔HEAD blob、evidence/evidence_tools/capture/supersedes/investigation/boundary 绑定全对；N9 摘要复算 38/`da927ee2…`；证据工具 `--check` 均 OK；全盘 57878 文件前后对比**零仓库写**。审查文件 [v5-freeze-review-handover-state.md](v5-freeze-review-handover-state.md)。
  - **交接文档与运维状态轴** → `accepted_with_findings`，**无 P0、5 条 P1**：16 个 README 链接与全部计数（48/5/1/3/13/4/51/115/315）准确；worker 暂停结论**复现并扩展**（全部 Task Scheduler 文件夹、服务、WMI `root\subscription`、GPO 登录脚本、Active Setup、IFEO/AppInit_DLLs、Winlogon、HKCU/HKLM/WOW6432Node/HKU Run、两个启动文件夹）未发现被漏掉的自启动路径；§7 与全目录无任何"已实施/可恢复"表述。审查文件 [v5-freeze-review-handover-docs.md](v5-freeze-review-handover-docs.md)。
- **5 条 P1 + 5 条 P2 已关闭**（逐条见 [冻结记录 §9](v5-freeze-record.md)）：① §8 决策与记录随本次提交入库（工作树回到干净）；② README §5 重写为与 §6 九条一一对应（补 §6.6/§6.9）；③ 撤掉与新判定矛盾的 self-test 优化建议，改为结构性搁置 + v6 清单；④ 删除 task_plan 中 V5-3 的重复未勾块并登记交接双审；⑤ 两仓 PLANNING_STATUS 统一为 `V5_3_COMPLETED`；另修 §2 引文按实际字节、§2/B6 冻结 HEAD 更正为 `89c0862d`（并与产物提交 `4f4dea1` 区分）、守卫检查数 2→3、README §4 审计边界与 `startup.py::install_startup_task` 重挂路径、§7 增 H01 硬前置。
- **v6 待办（仅下一代可做）**：边界文档数值刷新（改它即破 `boundary_record` 绑定）、`--self-test` 优化、`frozen_at` 机器锚定探索、变异数/墙钟自动登记。
- 本轮仍只写文档 + 只读复核：未改产品代码/配置/DB/任务，未恢复 worker，未删任何文件。
