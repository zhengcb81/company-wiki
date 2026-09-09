# revenue-forecast planning-with-files 最终范围与完整性复核

审计时间：2026-09-05（Europe/London）  
审计快照：`C:/Users/郑曾波/Projects/revenue-forecast`，HEAD `2cbd585efa6f7901e850ef205b6271b156e4f90d`  
操作边界：对 revenue-forecast 只读；只新增本报告，不修改计划正文、代码、配置、数据库、任务、receipt、manifest 或生产状态。

## 结论

- 按本报告明确的 planning-with-files canonical 边界，当前共纳入 **93 份 Markdown、25,163 行、2,304,586 bytes**；既有主审计已经逐份补读到 EOF，本轮对最新发生变化的 GP 组重新核对。此处“全文覆盖”表示阅读范围无缺口，不表示计划中的实现、部署或生产验收已完成。
- 其中 **46 份唯一文件**受 `assurance/unified_completion/manifests/plan_inputs.json` 的 entries/source hashes 约束；本轮按当前原始字节复算，**46/46 匹配、0 missing、0 mismatch**。44 个 entries 加 3 个 sources 中，`input_snapshot.md`重复出现，所以唯一文件数是 46，不是 47。
- `.review-zr407-20260818/` 不含 revenue-forecast 自身的 planning 克隆，只含 company-wiki 与 filing-fetch 的历史 review 快照；因此 revenue canonical 计数中没有依赖该隐藏目录的语义覆盖，等同副本覆盖数为 **0**。
- `assurance/fc/` 与 `assurance/unified_completion/receipts/` 下的 WU card、RED、change contract、reviewer receipt 是执行/审查证据，不是 planning-with-files 当前计划文档；它们明确排除，不以 117 个单元或 194 份 receipt Markdown 人为膨胀计划文档总数。
- 没有发现指定 canonical 范围内遗漏未读的 planning Markdown。不过，仓库仍有 **13 个不可访问的 `.tmp-*` 目录**；它们按命名和既有上下文属于测试/review fixture，明确排除于 canonical 计划范围。对其内部是否存在 Markdown 副本保持 `UNKNOWN`，不能把本报告扩张成“整个文件系统绝对无遗漏”。
- 发现一个必须上报的最新状态问题：仓库已从旧审计基线 `6b4e3cf` 前进到 `2cbd585`，但 2026-09-05 的“调度根因已修复”提交仍生成 `daily_t2_schedule.py --run-daily`，而 parser 只接受子命令 `run-daily`。当前安全探针仍在 argparse 阶段被拒绝，未进入 runner。电源条件、`StartWhenAvailable` 和 22:00 触发修复并没有关闭这个独立的 CLI action 缺陷；因此 GP-008 仍不能标作运行闭环。

## 1. canonical 纳入边界与精确计数

行数使用 PowerShell `Get-Content -Encoding UTF8` 的内容行计数；bytes 使用文件原始长度。目录递归只纳入 `.md`，并排除缓存目录。

| 组 | 纳入规则 | 文件数 | 行数 | bytes | 覆盖 |
|---|---|---:|---:|---:|---|
| 根 planning | `task_plan.md`、`findings.md`、`progress.md`、`IMPLEMENTATION_PLAN.md` | 4 | 6,114 | 485,726 | 全文 |
| `review_audit/` 根四件 | `task_plan.md`、`findings.md`、`progress.md`、`roadmap.md` | 4 | 940 | 69,161 | 全文 |
| `audit_review/` 根四件 | `README.md`、`task_plan.md`、`findings.md`、`progress.md` | 4 | 1,374 | 156,085 | 全文 |
| 六个日期 plan 包 | 下表列出的六目录内全部 Markdown 附件，递归 | 71 | 13,605 | 1,124,469 | 全文 |
| 8/13 session | `assurance/runs/session-2026-08-13/` 根下四份 Markdown | 4 | 2,491 | 408,793 | 全文 |
| 9/2 GP 活动组 | `assurance/runs/2026-09-02_remaining-gap-closure/` 六份 Markdown | 6 | 639 | 60,352 | 全文；本轮复核最新字节 |
| **合计** | 唯一路径去重 | **93** | **25,163** | **2,304,586** | **93/93** |

六个日期 plan 包的分组计数：

| 日期包 | 文件数 | 行数 |
|---|---:|---:|
| `2026-08-08_adversarial_plan` | 4 | 2,386 |
| `2026-08-09_data_lake_refactor_plan` | 9 | 3,094 |
| `2026-08-09_full_completion_assurance_plan` | 17 | 2,671 |
| `2026-08-12_zijin_skill_run_audit` | 13 | 1,636 |
| `2026-08-13_three_repo_completion_rebaseline_plan` | 15 | 1,860 |
| `2026-08-13_zijin_data_lake_remediation_plan` | 13 | 1,958 |
| **合计** | **71** | **13,605** |

9/2 GP 六件的当前行数是：`task_plan.md` 147、`findings.md` 78、`progress.md` 157、`gp008_009_deployment_guide.md` 79、`gp010_cohort_cutover_request.md` 79、`n1_r9_removal_request.md` 99。此前审计中 task/progress 的 146/135 是旧字节计数；本表以 HEAD `2cbd585` 为准。

## 2. 全文覆盖证据链

本报告对照了：

- `revenue-forecast-audit.md`：记录根巨型三件套、review/audit 根文件、session 四件、GP 六件以及六个日期包逐段补读到 EOF 的游标；后续追加明确撤销了早期“仅片段/盘点”的暂态描述。
- `revenue-remediation-tail.md`：独立复核 remediation 包最后四份 237/193/85/174 行文件，无剩余区间，且当前 hash 与冻结清单一致。
- `revenue-datalake-adr.md`：独立全文覆盖旧 data-lake 五份 ADR（48/35/19/33/29 行），并正确区分 `contract_frozen` 与正式 reviewer accepted。
- 本轮文件系统枚举：重新计算当前 93 文件的数量、行数和字节；确认旧报告列出的六个日期包文件数之和等于当前递归枚举的 71。
- 本轮 GP 复核：由于仓库在 2026-09-05 继续提交，重新读取活动组，确认 `progress.md` 已增至 157 行，并核对最新提交和当前 CLI action/parser。

因此，早期审计表格里“根三件套仅片段”“session progress 尚未补完”“旧日期包附件尚未逐份读取”等文字均是中间态，已被同一审计文件后续带日期的“补读完成”段落覆盖。最终范围判定不得再引用这些早期行作为当前缺口。

## 3. hash/机器证据覆盖

以下四件只作为控制面或机器证据读取，不计入 93 份 planning Markdown：

1. 根 `TERMINAL_NOTICE.json`：说明根旧 planning 入口已封存/被后继链取代。
2. `assurance/unified_completion/README.md`：统一完成包的人类入口。
3. `assurance/unified_completion/state.json`：117 单元机器状态；其 `completed` 只代表原 DAG，不证明当前 GP 部署和自然时间门。
4. `assurance/unified_completion/manifests/plan_inputs.json`：44 entries 与 3 sources 的冻结输入绑定。

本轮把 entries 与 sources 合并后按路径去重，再对当前文件逐一复算 SHA-256：`unique_bound=46`、`bad=0`。这项 hash 复核证明冻结输入没有字节漂移；它不能替代语义阅读，也不能把历史 accepted 外推为 Task Scheduler 当前可运行、真实 roots CI 为 blocking 或 broker sections 全部完成。

## 4. 明确排除项

### 4.1 执行证据，不是 planning-with-files 文档

- `assurance/fc/`：16 份 Markdown、96,397 bytes。内容是历史 WU/变更合同/reviewer 报告与 mutation evidence。
- `assurance/unified_completion/receipts/`：194 份 Markdown、541,907 bytes。内容是卡、RED、reviewer/closure receipt 等历史执行证据。
- 这些证据由 state、manifest、receipt 链和必要的抽样/机器验证解释；本次不把它们算入 93 份规划文档，也不要求为了“全文”重复读取 117 个单元的每张卡。

### 4.2 隐藏 review 克隆

- `.review-zr407-20260818/` 实际只包含 `company-wiki/` 与 `filing-fetch/` 快照，没有 `revenue-forecast/` planning 镜像。
- 它是历史独立 review 工作区，不是 revenue 的第二套活动计划；其中普通 wiki、fixture、产品文档和另两仓计划由各自 canonical 仓审计处理。
- 由于不存在 revenue planning 对应路径，本仓没有需要用“同 hash 代替全文”的隐藏克隆文件；计数为 0。

### 4.3 普通产品文档和运行产物

- 根 `AUDIT_REPORT.md`、`FILING_FETCH_AUDIT.md`、`CHANGELOG.md`、`SKILL.md`，以及 `docs/`、`e2e/`、`references/` 下普通设计/使用文档，不属于本次明确的 planning-with-files 集合。
- `assurance/runs/20260903T211059Z/`、preflight/verify 输出、JSON ledger、日志、测试缓存、benchmark、artifact、compatibility snapshot 等是运行/产品/机器证据，不作为 planning 文档。
- 当前尚不存在根 `PLANNING_STATUS.md`；因此它没有计入 93。若主任务随后创建该入口，应将最终数量更新为 94，并单独全文/链接/状态复核。

## 5. 13 个不可访问 tmp 目录（UNKNOWN）

以下目录在递归枚举时被访问控制拒绝；不提权、不绕过、不据名称猜测其内部文件：

1. `.tmp-zr409-review`
2. `.tmp-zr409-review2`
3. `.tmp-zr409-review3`
4. `.tmp-zr501-delta1`
5. `.tmp-zr501-delta2`
6. `.tmp-zr501-r1`
7. `.tmp-zr501-r2`
8. `.tmp-zr501-r3`
9. `.tmp-zr501-review`
10. `.tmp-zr501-review2`
11. `.tmp-zr501-review3`
12. `.tmp-zr502-t1`
13. `.tmp-zr502-t2`

三份可读 `.tmp-zr408-unit*` 已知是 fixture；精确 planning 文件模式未发现其 canonical planning 副本。全部 `.tmp-*` 均因 fixture/临时 review 性质排除，不是当前可领取计划。结论必须写成“canonical planning 范围完整，13 个 tmp 内部 UNKNOWN”，不能写成“全仓所有目录绝对完整”。

## 6. 真正遗漏与最新状态漂移

### 6.1 GP-008 当前代码与文档仍矛盾（阻塞性）

当前 HEAD 已包含：

- `c701f6d`：允许电池/唤醒；
- `3ea24b7`：`StartWhenAvailable`；
- `e9a6071`：03:30 改为 22:00；
- `2cbd585`：文档称“schedule root-cause fixed”、owner 已重注册。

但是当前 `tools/daily_t2_schedule.py` 同时存在：

- `cmd_register` 的 `New-ScheduledTaskAction` 参数仍为 `"...daily_t2_schedule.py" --run-daily`；
- `build_parser()` 只注册子命令 `run-daily`，且 `subparsers(..., required=True)`；
- 安全探针 `python -B tools/daily_t2_schedule.py --run-daily` 仍输出 `the following arguments are required: command`，在执行 runner 前即失败。

所以应把“错过触发/电源条件”视为一个已发现并有代码修复的原因，但不是唯一根因；注册 action/parser 不一致仍在。最新计划文字把 GP-008 写为“完成”“root-cause fixed”属于当前事实漂移。只有修复 action 或增加受测兼容入口、重新注册、提权读取实际 Action、观察真实 manifest/period 前进并由独立 agent 复核后，才能关闭。

### 6.2 六份 GP 文档内部的其他未同步项

- `task_plan.md` 与 `progress.md` 的顶层/表格仍写 GP-001~010 全部完成、GP-008/009 registered；这与上述 argparse 探针冲突。
- `task_plan.md` 的交接时间线仍是 09-05/06/07 03:30，`progress.md` 新增段改为 09-05/06/07 22:00；前者已过时。
- `gp008_009_deployment_guide.md` 仍写“已注册任务无需重注册，代码落盘即生效”，与 action 本身不兼容相冲突；手动示例的 catalog 仍是 revenue 根下 `.source_catalog`，而代码默认是兄弟 `company-wiki/.source_catalog/catalog.sqlite3`。
- `gp010_cohort_cutover_request.md` 页首/页尾仍写“待批准/等待批准”，正文批准记录又写已于 09-03 执行；验收项也未满足（summary 6/7、sections 0 或后续 5/7，安全门命中 1/7）。应标为已授权、部分执行、fail-closed 拒绝保留、sections gap 未全关。
- `n1_r9_removal_request.md` 页首仍为待批准，批准记录又存在；successor 映射与冻结 registry 不一致，末尾仍“批1→2→3每批独立 commit”，而 §3.2 要求 revenue 批1+2单 commit。它也保留了 03:30/09-07 时间线，未吸收 22:00 变更。
- `progress.md` 末尾在 9/5 新状态段之后又追加较旧的“9/3 晚间”段，且旧段仍承诺 03:30 与 09-06；按文档顺序读取会把旧状态误当最新。应由统一状态页给出明确优先级，不应继续仅靠 append 顺序推断当前状态。

这些不是“未读文件”，而是已读文件里的真实状态不一致。主任务的最终同步必须基于 HEAD `2cbd585` 重新生成/审查 patch；先前以 `6b4e3cf` 为基线的 `revenue-docs.patch` 已失效，不能直接应用。

## 7. 对主任务的交接建议

1. 把本报告作为 revenue 范围终局：93 份 canonical planning Markdown 已全文覆盖；13 个 tmp 明确 UNKNOWN/排除；210 份 FC/receipt Markdown明确为执行证据而非计划。
2. 放弃旧基线 patch，基于 `2cbd585` 和当前 GP 文件 hashes 重新制作最小文档补丁；先不改冻结日期包和 hash-bound 文件。
3. 新建根 `PLANNING_STATUS.md` 时明确分层：旧 DAG 117/117 终局、GP 当前未闭环、历史文件只读、自然时间门尚未满足、实际 Scheduler 状态需 owner 提权证据。
4. GP 当前状态至少应为：GP-006 `partial`；GP-008 `blocked_code + deployment_action_unverified`；GP-009 `deployment/natural-time unverified`；GP-010 `authorized + partial_execution`；R9 `authorized but not executed`。
5. 文档补丁完成后必须由未参与编写的独立 agent 复核：当前 HEAD/CAS、全部相对链接、action/parser 实证、时间线、冻结 hash、diff 边界和 93→94 新计数。只有 reviewer `PASS` 后才能应用。

## 8. 本轮错误与边界说明

- 两次 PowerShell 汇总命令因 `foreach {...} | Format-Table` 的 empty-pipe 语法触发 ParserError；均无写入。随后改为先累计 `$rows` 再格式化，成功取得计数。后续不应重复该写法。
- 日期包递归枚举触及 `.pytest_cache` 时被拒；改为 `-ErrorAction SilentlyContinue` 并显式排除缓存。缓存不是 planning 文档，未请求扩大权限。
- 一次六文件合并输出因工具总输出上限截断；没有把该次调用算作新全文覆盖。随后单独分段读取发生变化的 `progress.md`，并结合既有逐文件 EOF 记录完成复核。
- 当前代码探针只验证 argparse，不会进入 runner、不会写 manifest/catalog/periods，也没有注册、注销、启动或修改 Windows 任务。

最终 verdict：**CANONICAL_SCOPE_COMPLETE_WITH_EXPLICIT_UNKNOWN_TMP；CURRENT_GP_DOCS_CHANGES_REQUIRED**。
