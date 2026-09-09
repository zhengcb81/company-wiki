# revenue-forecast 文档补丁应用后独立复核

复核日期：2026-09-05（Europe/London）  
复核边界：`C:/Users/郑曾波/Projects/revenue-forecast` 只读；唯一写入是本报告。未修改 revenue 仓库、任务、代码、配置、数据库、manifest、receipt 或机器 state。

## Final verdict

**FINAL_POST_APPLY_PASS**

六回链最小补丁已按预审对象成功落地，前次唯一阻塞已经关闭。最终实际状态为：六份活动 GP 文档各恰好1条回链且目标存在；根状态页3条链接仍有效；HEAD、冻结锚点及46个受绑定文件不变；实际任务变化仍只限根 `PLANNING_STATUS.md` 和六份活动 GP Markdown；`git diff --check` 通过。此前的 `POST_APPLY_FAIL` 是六回链应用前的阶段性 verdict，现由本最终 verdict 覆盖。

## 初次应用后 verdict（六回链补丁之前，历史记录）

**POST_APPLY_FAIL**

补丁主体、状态事实、冻结哈希、canonical 计数及 Git 边界均通过；但指定验收项“六文件新增链接均有效”不成立：六份被修改的 GP Markdown 当前各含 **0** 个 Markdown 链接，diff 中也没有新增链接。根 `PLANNING_STATUS.md` 的 3 个本地链接全部有效。若验收意图是让六份活动文件各自回链到当前状态总入口，则须由实施者另加回链（建议 `../../../PLANNING_STATUS.md`），再由独立 agent 重跑本复核；本 reviewer 未越权修改 revenue 仓。

## 检查结果

| 检查项 | 结果 | 证据 |
|---|---|---|
| HEAD | PASS | `2cbd585efa6f7901e850ef205b6271b156e4f90d`，仍为预期 `2cbd585` |
| 本任务 tracked 变化 | PASS | `git status --short --untracked-files=no` 与 `git diff --name-status` 仅显示 `assurance/runs/2026-09-02_remaining-gap-closure/` 下六份 Markdown 修改 |
| 本任务新增文件 | PASS | `PLANNING_STATUS.md` 为唯一补丁 Add 目标；当前 Git 状态为 `?? PLANNING_STATUS.md` |
| 既存 untracked 区分 | PASS（证据限定） | 大量 `.review-*`、`.tmp-*`、运行 evidence 与历史 audit 包在应用前审计已存在；本补丁的目标清单只有六个 Update 路径和一个 Add 路径，不把既存 untracked 归入本任务。13个拒绝访问 tmp 仍为 UNKNOWN，不扩大结论 |
| diff whitespace | PASS | 六文件 `git diff --check` exit 0；diff stat 为 6 files、71 insertions、2 deletions |
| 根状态页链接 | PASS | 3/3 存在：活动 `task_plan.md`、company-wiki 的 `revenue-scope-inventory.md`、`revenue-forecast-audit.md`；机械解析 BROKEN=0 |
| 六份活动文件新增链接 | **FAIL** | 六文件全文和新增 diff 中 Markdown 链接数均为 0；不存在可供“均有效”验证的六个回链 |
| canonical 93→94 | PASS | 按已审定集合重新枚举：根 planning 现为5件，其余4+4+71+4+6，去重总数94，missing=0 |
| 新状态页全文 | PASS | 40行、5,297 bytes、SHA-256 `1da0b403740eb3d916a235a0c93f99097814dcfdc0396e75c87666c89f8090e5`；与 `revenue-docs.patch` 最后一个 Add File 正文逐行完全相同 |
| `plan_inputs.json` raw hash | PASS | `9e43255e5e56102cbc49e04615d1a1adeb34dece918b976bb0d8867b282d85e4` |
| 46个冻结输入 | PASS | 44 entries + 3 sources，按 `rel_path` 去重为46；当前原始字节 SHA-256 复算 `BAD=0`，无 missing/mismatch |
| 冻结/机器/产品边界 | PASS | tracked diff 的6个路径均为活动 GP Markdown；禁止路径匹配数0。补丁未触及 `TERMINAL_NOTICE.json`、state、receipt、manifest、代码或 config |
| 独立 review 门禁 | PASS | 活动 `task_plan.md` §3 仍规定“每个 GP 必须满足”独立 reviewer、独立重跑/重扫、12 reviewer receipt，以及状态机 `independent_review → accepted`；补丁未删除或弱化该门禁 |

## 冻结锚点与差异边界

- `TERMINAL_NOTICE.json` 当前 SHA-256：`b3f3ceb22f17e8a174bf5bd535bddef619132c9e6d72277eae3eea1e4eac9103`。
- `assurance/unified_completion/state.json` 当前 SHA-256：`82ad3600a8a64cab52e049fa2232b9e248966f80af31adf566f8991b504451f7`。
- `assurance/unified_completion/manifests/plan_inputs.json` 当前 SHA-256：`9e43255e5e56102cbc49e04615d1a1adeb34dece918b976bb0d8867b282d85e4`。
- `assurance/unified_completion/receipts/` 仍存在；本补丁没有 receipt 路径。
- 补丁声明路径共8个 Update hunk（其中部署指南出现三次）和1个 Add File；所有路径均落在上述七个文档目标。当前 tracked diff 没有删除文件，也没有 JSON、源码、测试、workflow、config 或 compatibility 文件。

上述事实只证明本补丁没有把这些对象纳入当前差异；对大量既存 untracked 的来源判断依赖应用前范围报告与独立审查日志。由于若干 tmp 目录拒绝访问，不能声称全文件系统绝对无其他内容。

## 当前状态事实复核

### GP-006 — `partial`

`.github/workflows/quality.yml` 的 `real-roots` job 仍为 `windows-latest` 且 `continue-on-error: true`；紧邻注释明确真正 REAL_DATA 套件需要有 production catalog 的 self-hosted runner，当前未纳入。因此只能认定 sibling 临时数据 CI 子集已接线，不能写成真实 roots 阻断门完成。

### GP-008 — `blocked_code + deployment_action_unverified`

`tools/daily_t2_schedule.py` 的注册 Action 仍生成 `--run-daily`，parser 仍只注册子命令 `run-daily` 且 subparser required。只读安全探针 `python -B tools/daily_t2_schedule.py --run-daily` 仍在 argparse 阶段失败：`the following arguments are required: command`，未进入 runner。任务实际 Action 的提权读取仍无独立证据，因此不能把 owner 重注册记录外推为可运行部署。

### GP-009 — natural-time incomplete

`daily_manifest.json` 仍指向 `20260903T211059Z`、observation_period=1；`legacy_periods.json` 仍只有 period1 `observing`，completed=0、`close_allowed=false`。未形成两个各≥24h且hits=0的 completed 窗口，也未证明7 Daily/2 Weekly/1 Monthly/1 drill完成。

### GP-010 — authorized / partial

状态覆盖一致写为 normalized 7/7、review receipt 7/7、summary 6/7、sections 5/7；1份 summary 被安全门 fail-closed 拒绝，另2份列表式研报仍无 sections。应用前独立 SQLite `mode=ro` 复核已确认 active broker_research cohort 恰为7份并得到同一 7/6/5 聚合；本次短范围 post-apply 不重复访问49GB生产 catalog。registry 197/197 passed 未被误写成生产语义7/7。

### N-1 / R9 — approved, not executed

`n1_r9_removal_request.md` 保留 2026-09-03 owner A+B 批准记录，同时顶部覆盖明确删除未执行。当前 tracked diff 无 deletion；删除清单中的 legacy 工具/workflow引用仍可见，窗口门仍未开。当前批次口径统一为 revenue 批1+2单一 commit、随后 wiki 批3独立 commit；历史正文的旧表述由顶部覆盖声明压住。

## 链接缺口的最小修复要求

六份活动文件是：

1. `task_plan.md`
2. `findings.md`
3. `progress.md`
4. `gp008_009_deployment_guide.md`
5. `gp010_cohort_cutover_request.md`
6. `n1_r9_removal_request.md`

若验收要求每份都能回到当前权威入口，应在各自的 2026-09-05 覆盖段中增加一个本地 Markdown 链接，例如 `[当前状态总入口](../../../PLANNING_STATUS.md)`。修改必须：

- 只涉及这六份活动 Markdown；
- 不改冻结文件、receipt、manifest、state、代码或 config；
- `git diff --check` 通过；
- 六个链接机械解析为存在；
- 由未参与修改的独立 agent 再次给出 post-apply PASS。

在这项缺口关闭前，本报告保持 **POST_APPLY_FAIL**；不得把其余通过项合并解释为最终全 PASS。

## 复核操作错误记录

- 首次全量 `git status --untracked-files=all` 被大量既存 fixture/untracked 输出截断；该输出不用于证明完整范围。后续改用 `--untracked-files=no` 核 tracked 差异、对 `PLANNING_STATUS.md` 精确 pathspec 核新增文件，并引用应用前范围快照区分既存 untracked。
- 首次从 patch 提取 Add File 正文时使用了错误的相对路径 marker，得到 `PATCH_ADD_FOUND=False`；未写 revenue。随后读取实际绝对路径 marker，并用最后一个 Add File 段逐行比较，40/40相同。

## 六回链最小补丁应用前独立复核

复核对象：`revenue-links.patch`  
SHA-256：`87c3866c69704d3fafbdc3b5ccc91abffb87f81bbbcc48ab7ea9e73cea2536b0d`

**LINK_PATCH_PRE_APPLY_PASS**

- 补丁边界精确为6个 `Update File`、6个 hunk、0 Add File、0 Delete File；目标路径互异且全部是六份活动 GP Markdown。
- 每个 hunk 只用对应文件的一级标题作为旧上下文。六个标题在各自当前文件中均精确出现1次，因此六 hunk 均唯一匹配，不存在模糊落点。
- 当前六文件原始字节 SHA-256 与实施者给定 CAS 全部一致：

| 文件 | 当前 SHA-256 | CAS |
|---|---|---|
| `task_plan.md` | `38f6b0feead015a9512d0f2c431cda66aaf35f6a3fe83552f8046fe0a6c65ce5` | MATCH |
| `findings.md` | `cc3ffb63ead6e1d31218dfb84ff28851fd97d6c280159fc767787a4a80f27903` | MATCH |
| `progress.md` | `bd4b81484bdb532d2479dd5eb2c1ade8ff35edf77504c1979c8dfb062465bbeb` | MATCH |
| `gp008_009_deployment_guide.md` | `69399163da8e621ea4e797eaa70e4c132d88a1b9d39088e93f6ceb23bd628934` | MATCH |
| `gp010_cohort_cutover_request.md` | `c0d94b0f1d7a54e6af1c17f2abe4fb1c76a5876b0bf4fc53e621e3af938127c1` | MATCH |
| `n1_r9_removal_request.md` | `9a916cae986b0b987d6482b79827b6fa4c80d5b4d46a0ca504bba34afd571efd` | MATCH |

- 内容变化机械解析为12条新增行（每文件1个空行 + 1个引用式 Markdown 回链）、0删除行；除统一的 `> [当前状态总入口](../../../PLANNING_STATUS.md)` 外无其他新增正文。
- 六个文件均位于 `assurance/runs/2026-09-02_remaining-gap-closure/`；从该目录解析 `../../../PLANNING_STATUS.md` 均得到 `C:/Users/郑曾波/Projects/revenue-forecast/PLANNING_STATUS.md`，目标当前存在。
- 补丁不包含代码、配置、state、receipt、manifest、任务、冻结目录或其他文件变化，也不改变六文件已有状态结论和独立 reviewer 门禁。

本 verdict 只批准该最小回链补丁按当前六 CAS 应用；不代表补丁已经应用。应用后仍须重新检查六个链接实际存在、`git diff --check`、目标文件集合及 immutable hash，然后才能把上文 `POST_APPLY_FAIL` 提升为最终 PASS。

## 六回链应用后最终复核

**FINAL_POST_APPLY_PASS**

| 最终检查 | 结果 | 当前证据 |
|---|---|---|
| 六文件回链 | PASS | 六份活动 GP Markdown 各恰好1条 `[当前状态总入口](../../../PLANNING_STATUS.md)`；全部解析到 revenue 根 `PLANNING_STATUS.md`，`LINK_WRONG_COUNT=0`、`BROKEN=0` |
| 根状态页链接 | PASS | 前次机械复核3/3存在；六回链补丁未修改根页 |
| HEAD | PASS | `2cbd585efa6f7901e850ef205b6271b156e4f90d`，与预审及初次应用后一致 |
| 实际目标集合 | PASS | tracked diff 仍仅为六份活动 GP Markdown；补丁新增文件仍仅 `PLANNING_STATUS.md`。其他大量 untracked 维持既存/UNKNOWN边界，不归本任务 |
| diff whitespace | PASS | `git diff --check` exit 0；最终六文件 diff stat 为83 insertions、2 deletions，其中相对前一轮新增12行恰为六个空行加六个回链 |
| immutable anchors | PASS | `TERMINAL_NOTICE.json=b3f3ceb22f17...`、`state.json=82ad3600a8a64...`、`plan_inputs.json=9e43255e5e561...`，均与前次一致 |
| 冻结输入 | PASS | 44 entries + 3 sources 去重为46个受绑定文件；最终再次复算 `BAD=0` |
| 状态事实与 review 门 | PASS | 六回链补丁只增加导航，不改变前次已通过的 GP-006/008/009/010、R9 状态结论，也不改变“每个 GP 独立 reviewer”的统一验收门 |

最终六文件 SHA-256（用于后续并发漂移检测）：

| 文件 | 最终 SHA-256 |
|---|---|
| `task_plan.md` | `25578b09ff1185dc060948c73722e83a6517b0ef55c747a6f61cbaf7e8d92c77` |
| `findings.md` | `193f5095d834ab9652713b15b4d89c872407a635ef50d3808a9abf8ee65b17be` |
| `progress.md` | `dcd9bc1c131d5bbbe423d7dd77b7026473cef6aed656d5996ab7e1a392dd6a94` |
| `gp008_009_deployment_guide.md` | `e8fc6e5478d54a596ca16d6810709324dd877d4fe887535263277d05a710cb0a` |
| `gp010_cohort_cutover_request.md` | `b1f2081fb5187b2a9d8cab76b28c4075b5dc6493657c6e1d543e08dbe9f29788` |
| `n1_r9_removal_request.md` | `b0581c7d04d4513b36fe23a635422fcee31764fe99fc5a8413d201889499ccd3` |

该 PASS 是规划文档同步与证据边界的验收，不是产品修复、Windows 任务部署、自然时间窗口、真实 roots CI 或 R9 删除完成的证明。GP-008仍为代码阻塞/实际Action未验证，worker及任何生产动作均未由本 review 启动。
