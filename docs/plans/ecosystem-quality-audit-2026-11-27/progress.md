# Progress Log — 全 12 模块深度审查与综合整改规划

**当前节点**　P0-01 至 P0-11 全部交付候选。11 张止血修复已并线。FF T3 离线组合通过，正式绑定与精确 CI 核对继续；P1-00 独审通过并发布，Phase 1 从 CWP、ET、RF 三仓开始。W12 业务循环仍在原检查点。

## 2026-11-27 22:54 UTC — P0-01 至 P0-11 分批派工

用户要求总控直接派 agent 执行 11 张止血卡。会话同时可运行 3 个子 agent，各卡使用独立 agent，空出席位后即派下一张。11 张卡已全部启动，使用 `C:/Temp/s6a/` 下的独立候选工区。当前记录按候选独审和发布进度更新。原 `C:/Temp/s6/` 工区及作者未提交内容仍作为只读参考。若原作者先交付，从同一发布目标核对两套候选并接受一套，保留已有测试与独审。

| 卡 | 新候选工区 | 候选 SHA / 当前状态 | 实施者的定向证据 |
|---|---|---|---|
| P0-01 | `C:/Temp/s6a/audit` | `c41db5ddc78506b3f665983fdae715626ff04581`，独审通过，本地 `main` 已快进（无远端） | 原 CLI 复现 `NameError`；Windows 6 项通过，审计三类回执从新进程查读，同一动作各执行一次 |
| P0-02 | `C:/Temp/s6a/et` | `2f7e03db01c9aed817811e07b7e83acddeac4ba0`，远端 `main` 已核对，[CI 通过](https://github.com/zhengcb81/earnings-transcripts/actions/runs/46082021743) | Windows 37 项定向通过，另在实际 console-subsystem Python 验证无新控制台及进程树回收 |
| P0-03 | `C:/Temp/s6a/ir` | `5edb9fb561f077d828af00b921dfbdc0926eb412`，远端 `main` 已核对，私有 CI 待查 | Windows 104 项及 11 个子测试通过；最终再验 3 项，覆盖依据渲染、模型透传、裸输出路径和独立安装 |
| P0-04 | `C:/Temp/s6a/stockwiki` | `6c75adf45c1ed76735d64f561268e951cb92c862`，独审通过，本地 `master` 已快进（无远端） | Windows 8 项定向通过，邻近回归 208 项通过，覆盖 SQLite 特殊路径、回滚和 HTTP 请求框架 |
| P0-05 | `C:/Temp/s6a/iqs` | `b4aee7fb05671b162ef7f6d8e270ef3cb2692e52`，远端 `master` 已核对，[CI 通过](https://github.com/zhengcb81/invest-quick-scan/actions/runs/46082564988) | 邻近定向 136 项通过，最终 55 项通过；实测锁竞争、冷读、并发成功不可覆盖和无窗启动 |
| P0-06 | `C:/Temp/s6a/cwp` | 远端 `master@d1987560eafe97e71753cf3e5d7e6712d661bbdd`，[CI 通过](https://github.com/zhengcb81/company-wiki/actions/runs/46083438812) | Windows 定向与独审通过。实测判定已发布的原件后再停进程，部分写入继续；合并版推送钩子 23 项通过 |
| P0-07 | `C:/Temp/s6a/ff` | watchdog `035d415b81268d1192721cfdc7b743238f674d32` 已入远端 `main`，[CI 通过](https://github.com/zhengcb81/filing-fetch/actions/runs/46083923728)。T3 `82c749464b494cf8dc9ec9e694c433adb02717e5` 也已入远端 `main` | watchdog 28 项通过，已有输出不触发新的尺寸拒绝。T3 最终 18 项与跨仓四案通过；正式绑定待验 |
| P0-08 | `C:/Temp/s6a/sid` | `8bc6e93b55142e0eff464c14adc08ebc93fb59c3`，远端 `v2-clean-rewrite` 已核对，[CI 通过](https://github.com/zhengcb81/StockInfoDownloader/actions/runs/46082044981) | Windows 102 项定向通过，实测 HTTP 截断、原 PDF 保留及占用后原子替换 |
| P0-09 | `C:/Temp/s6a/rf` | `5a28c0c88df1a8e8fb9b167dbd884eebef7d7894`，远端 `main` 已核对，[CI 通过](https://github.com/zhengcb81/revenue-forecast/actions/runs/46082671176) | Windows 170 项和 13 个子用例通过。另有 1 项既有跳过、1 项在基线也失败的历史 review 断言，交 Phase 1 更新 |
| P0-10 | `C:/Temp/s6a/mc` | `c0ec9c168d8f2c038405ab0c6cbab0438ff5ad87`，远端 `master` 已核对，[CI 通过](https://github.com/zhengcb81/MeetingConverter/actions/runs/46082052941) | Windows 137 项定向通过，真实 CLI 和 ffprobe 验证坏配置、坏音频及正常音频，新增供应商请求为零 |
| P0-11 | `C:/Temp/s6a/dash` | `de62760090c6380914b5c30c4726afe85c5234d7`，远端 `main` 已核对，私有 CI 待查 | Windows 7 项启动测试通过；邻近 55 项通过，另 1 项 M8 过期断言在 `666e2426` 同现。保留已有 RF 配置和 48766 运行 |
| P1-00 | `C:/Temp/s6a/spec` | 候选 `b11d45f457a60203bbc7ecb6e598704e4904013b` 已独审；同一工具文件发布于 CWP `7320c52a2a6daf2d424c35216fa6ed3cad88f063` | 25 项通过，实际 pytest 验证子集选择、收窄配置、合法输出选项、缺失项和合法包导入。CWP P1-01、ET P1-03、RF P1-05 已按正式基线开工；各自旧测试差异按根因处理 |

RF 的一次隔离测试把过长请求放在 Windows 命令行，启动失败后 pytest 把继承变量带进本地工具输出。现已将请求改由 stdin 传入，并在启动测试进程前白名单化测试环境。后续施工沿用环境隔离，保留 Windows 和临时夹具所必需的变量。凭据值不抄录到计划或受版本控制的证据中。

## 2026-11-28　T3 组合与 Phase 1 首批

- **P0-07 组合证据**　用真实 FF 和 CWP 进程、CN/HK/US 本地采集替身和一个损坏原件执行四案，四案通过。三个市场各 discover/fetch 一次，损坏原件零采集。同一 run 冷读与再执行的回执相同，新调用为零。CWP 提供方已发布 `1a62edf1d0d89567a5a552709d7027880ea3b857`。第一轮复验发现 FF 短请求将探针诊断落入默认目录。已用 `--jobs-dir` 接入原 DirectRun 回执及 outbox，FF 候选 `82c749464b494cf8dc9ec9e694c433adb02717e5` 经独审，18 项回归通过。固化脚本的最终组合四案再次通过，安装根 `.ff_jobs` 零残留，临时目录已回收。复跑用 [replay_t3_composition.py](review/replay_t3_composition.py)。
- **P1-01 CWP**　`C:/Temp/s6a/cwp-p1` 从发布工具版开始。Windows 31 项定向通过；全目录收集涉及历史外部依赖，在处理真实收集和运行清单。保持开发者快测。
- **P1-03 ET**　`C:/Temp/s6a/et-p1` 真实 Windows 收集 831 项，旧 CI 从未覆盖的退出及回告断言已逐一追踪。完整单跑超过 610 秒，按适用平台分片并核对执行并集。旧退出码、原作业、输出协议和本地脱敏留痕保留。Windows 收集 833 项，分为 251/297/285，六项 F4 回归通过。候选 `93c522e68917c8540138585a47200cba5d369333` 修正 GitHub 的 job/step 环境与同 SHA 采证。已推送 [ET 草案 PR](https://github.com/zhengcb81/earnings-transcripts/pull/1) 等真实双平台组合验收。
- **P1-04 SID**　`C:/Temp/s6a/sid-p1` 已按正式 `8bc6e93b` 开工，补齐真实离线测试发现以及 Windows 原生执行。
- **P1-05 RF**　`C:/Temp/s6a/rf-p1` 定向 82 项通过。移除过时的缺 review 拒绝期待，保留实际 SHA 错拒绝；查清被旧硬编码测试列表遗漏的四个收集故障，正在核对完整离线执行。

## 2026-11-28　Phase 1 首次 CI 反馈

- **CWP ↔ FF T3**　[FF 正式 CI](https://github.com/zhengcb81/filing-fetch/actions/runs/46086264095) 通过，实际 CWP 配置用四份隔离夹具完成 `open/close`，采集派发为零且临时目录清空。CWP 首次 [精确 CI](https://github.com/zhengcb81/company-wiki/actions/runs/46085744052) 的架构测试暴露按字符串动态导入。候选 `ac9ba2b3d176ddb7fe01c5a41c24d5b1bd3b6288` 只用显式 CWP 公开入口，保留原测试红转绿。独立 Windows 复验两项通过，已保留在途的暂存与未暂存差异并快进、推送 `master`。 [修复版精确 CI](https://github.com/zhengcb81/company-wiki/actions/runs/46088694086) 与发布组合复验仍在运行。
- **P1-03 ET**　[首次双平台 CI](https://github.com/zhengcb81/earnings-transcripts/actions/runs/46086664981) 识别三类实际问题。Windows 原文比较改用文件身份，Linux 不解析 Windows 原生绑定，强停后以原作业的持久事件区分已知中断和尚未确认，费用保持 `unknown`。Windows 上六项针对用例通过，Ruff 与双平台 mypy 通过。`b0d8394ea0983d0c0c6ebc39d5be1da0151c3ffb` 已推到原草案，[六个执行分片与覆盖归集](https://github.com/zhengcb81/earnings-transcripts/actions/runs/46088338831) 全绿，正在做合并前独审。
- **P1-02 FF**　从已发布 `82c749464b494cf8dc9ec9e694c433adb02717e5` 创建 `C:/Temp/s6a/ff-p1` 开工，Windows 收集基线 1,885 个节点。只在该工区改工程检查和隔离测试。主工区的财报报表施工归原 owner。
- **P1-04 SID**　把实际旧提交的 HTTP 断流和原件替换缺陷作为红证据。Windows 首次完整运行还找出请求夹具身份歧义、安全作业号的旧断言和参考工具自测的进程污染，正在消除根因。候选 `7c34f34c4be4c76f2363097b9be58ab84a3089db` 保留作定位依据，待接受版本另记。
- **P1-05 RF**　旧 CI 漏跑的身份夹具和原子写用例已按公开契约修正。候选 `fed82030b640be3633ea683f0e21377d17806677` 的 87 项 Windows 针对复验通过，完整 Windows 执行进行中。日常 12 项快测继续保留。

## Session: 2026-11-27

### 前置审查与规划（首批实施前的历史记录）
- **Status:** complete
- **Started:** 2026-11-27 19:43 UTC
- **Completed:** 2026-11-27 20:06 UTC
- **Actions taken:**
  - 读取 `planning-with-files` 规范及项目既有总控 PWF（`PLANNING_STATUS.md`、`README.md`、`du11-source-closure-2026-10-18/CURRENT_STATUS.md`、`HANDOFF.md`、`task_plan.md`、`module-boundaries-2026-11-11/*`、`feedback-loop-2026-11-17/*`），厘清 12 个自有模块职责、历史 S1–S5 演进及最新 2026-11-27 无窗/恢复基线。
  - 核对全部 12 个仓库的本地分支、远端分支与实际运行 worktree，定位并校正了 RF（`.worktrees/f4rd@782cfd9a`）、IQS（`.planning/wi26@3094c5f7`）、Dashboard（`release-de59feed@de59feed`）、StockQA（`.worktrees/f4-runtime@86f633d8`）、IR（`.worktrees/f4-runtime@77f3c7dd5`）的真实最新代码检出。
  - 运行全量只读 Python AST/正则/Git/测试扫描脚本（覆盖 2,039 个生产 Python 文件、524,419 LOC、约 20,000+ 条测试函数），量化统计全部 12 模块的 SCC 运行时环、延迟导入、私有导入/属性/反射、`sqlite3.connect`、`sys.path`/`sys.modules`、硬编码路径/URL/模型/端口、日志覆盖、无日志 `from None`、静默吞错、最近修复提交及测试结构。
  - 并行派发四路只读深度架构与质量审查员（Cluster A: CWP/FF/ET；Cluster B: SID/RF/Audit；Cluster C: StockWiki/IQS/Dashboard；Cluster D: StockQA/IR/MC），逐文件核查源码与测试，沉淀精确 `file:line` 证据与历史缺陷回归对照表。
  - 直接只读核验 IQS `quality.yml`、Dashboard `feedback-contracts.yml`、IR `owner-contracts.yml`、RF `origin/main:quality.yml`、StockQA `origin/master:ci.yml` 及 `scripts/checks.py`，消除隐藏目录与稀疏工作树盲区。
  - 将完整审查发现与 6 阶段实施方案（Phase 0–Phase 5）写入本 PWF 包，并同步在父级总控入口登记链接（`PLAN_ONLY`，未修改任何生产代码、测试或配置）。
- **Files created/modified:**
  - `docs/plans/ecosystem-quality-audit-2026-11-27/findings.md` (created — 全 12 模块定量总表、5 大系统性根因、9 类伪解耦技巧清单与逐仓 `file:line` 详录)
  - `docs/plans/ecosystem-quality-audit-2026-11-27/anti-trick-governance.md` (created — 四层反偷懒/反伪解耦治理机制：10 类技巧黑名单 AP-01..10、12 项静态 AST/Meta 门禁 AT-01..12、4 项运行时行为证明 B-01..04、对抗式独立审查与 3-Strike 熔断协议)
  - `docs/plans/ecosystem-quality-audit-2026-11-27/module-blueprints.md` (created — 全 12 模块逐仓目标包树、单向 DAG、公开 `Protocol`、日志接线、硬编码清退与七维 E2E 施工蓝图)
  - `docs/plans/ecosystem-quality-audit-2026-11-27/task_plan.md` (updated v2 — 纳入 P1-00 防偷懒门禁前置落地、单卡强制 6 步闭环流水线、全局依赖图与全部 Phase 0–5 精细施工卡)
  - `docs/plans/ecosystem-quality-audit-2026-11-27/progress.md` (updated — 审查与计划深化日志)
  - `docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.md` & `CURRENT_STATUS.json` & `HANDOFF.md` (updated — 正式将本计划登记为主线 `S6` / `ecosystem-quality-audit-2026-11-27`，排在 `feedback-loop-2026-11-17` S5-10/F4 收尾线之后、W12 业务摘要接续之前，状态保持 `PLAN_ONLY_QUEUED_AWAITING_USER_START`)
  - `docs/plans/feedback-loop-2026-11-17/task_plan.md` & `docs/plans/module-boundaries-2026-11-11/task_plan.md` (updated — 增补主线直接后续交接指向 `ecosystem-quality-audit-2026-11-27`)

## Test Results

| Test | Input | Expected | Actual | Status |
|---|---|---|---|---|
| 只读定量扫描 (`audit_12_modules.py` + `summarize_audit.py`) | 12 仓最新正式代码树 | 全部 12 仓 AST/硬编码/日志/Git/测试完整产出 | 12/12 仓成功扫描，0 源码改动，产出 `audit_12_modules_result.json` | PASS |
| 四路并行深度源码审查 | 12 仓真实源码与测试文件 | 4 维度精确 `file:line` 证据 + 历史缺陷矩阵 | 4/4 路完成并交叉验证 5 仓 `.github/workflows/*.yml` | PASS |
| 生产代码与配置零修改核对 | `git status --short --untracked-files=no` | 零新增生产代码或生产配置变动 | 仅新增规划文档，生产源码与 `config/source_catalog.yaml` 零修改 | PASS |

## Error Log

| Timestamp | Error | Attempt | Resolution |
|---|---|---|---|
| 2026-11-27 19:44 | PowerShell 递归扫描 `.venv`/`.planning` 耗时过长 | 1 | 取消任务，改用跳过非源码目录的定向查询。 |
| 2026-11-27 19:48 | 临时脚本 `audit_12_modules.py` 局部变量 `full` 未初始化 | 1 | 初始化 `full = ""` 并优化 `ExceptHandler` 遍历，全 12 仓顺利完成。 |
| 2026-11-27 19:52 | 稀疏工作树（RF/StockQA）无 `tests/`/`.github/` 且 `skills/` 过滤导致 Audit 统计偏低 | 1 | 用 `summarize_audit.py` 放开 Audit `skills/` 并通过 `git ls-tree`/`git show` 读取远端完整测试与 CI。 |
| 2026-11-27 20:02 | 子代理未列出隐藏目录 `.github/workflows`（IQS/Dashboard/IR） | 1 | 直接 `read_file` 读取 3 仓 workflow 文件核正，避免误报“零 CI”。 |

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | S6 首批已派发，逐仓接收状态见下方台账。 |
| Where am I going? | P0 止血和 P1-00 并行，随后按仓接入 Phase 1，再做日志、架构、配置和组合 E2E。 |
| What's the goal? | 让全部 12 个模块达到真正架构级松耦合与封装、无硬编码高质量代码、全入口可追溯日志+历史错误回归锁定、以及高置信度跨平台端到端测试覆盖。 |
| What have I learned? | 详见 [findings.md](findings.md)：12 仓存在 11 项实时 P0 级隐患（含 Audit/ET 实时 `NameError`、IR 推荐依据静默丢数据、StockWiki 未转义 SQLite URI、IQS 80ms 锁困死等）、9 类“小技巧伪解耦”、系统性日志/stderr/stdout 缺口及 9–10 仓 CI 樱桃采摘/零 Windows CI 盲区。 |
| What have I done? | 完成基线审查；实施、接收与发布状态分别记录在后续条目。 |

## 2026-11-27 21:02 UTC — 配额中断（BLOCKED: 外部配额，非技术问题）
- Wave 1/2 共 12 个 card-implementer 因 RESOURCE_EXHAUSTED (HTTP 429, Individual quota) 全部中止；约 3h41m 后重置（约 2026-11-28 00:43 UTC）。
- 中断时 C:\Temp\s6\* 的 13 个 worktree 均无任何提交（HEAD 仍为基线 SHA），仅 mc 有 1 个未提交改动；无半成品落入主 checkout，生产配置/主 checkout 未被触碰。
- 切换模型后 send_message 续跑 P1-00 仍返回 429，确认为账号级配额。
- 恢复动作：配额重置后重新派发 P1-00 与 P0-01..P0-11（先核对各 worktree git status，mc 的未提交改动需先审视），随后按 anti-trick-governance 流程独立对抗审查。


## 2026-11-27 21:04 UTC — 换模型后重新派发
- 旧实现者会话固定在原模型上，续跑仍 429；新建的 card-implementer（继承新模型）正常运行。已为 P1-00、P0-01..P0-11 共 12 张卡重新派发全新实现者（worktree 与基线 SHA 不变，均无历史提交）。
- 原派发记录。当前按候选到达顺序接收，见下方首批交接台账。

## 首批交接台账

2026-11-27 22:36 UTC。总控只读核对 13 个工区的 HEAD、状态及发布引用。首批 12 张卡均沿用原指派，未见高于下表基线的候选提交。Audit 有两处在编，其余工区当时干净。下表是已观察到的交接状态，不能用于推断作者进程是否在线。收到候选后在对应行登记候选 SHA、关键用例、独审和集成版本，复用 owner 原记录。

| 卡 | 工区（位于 `C:/Temp/s6/`） | 派工基线 | 总控接收状态 |
|---|---|---|---|
| P0-01 Audit | audit | `9e9e980` | 等候候选；实现与测试有未提交改动 |
| P0-02 ET | et | `672ed10` | 首页故障已隔离复现，等候修复与进程回收证据 |
| P0-03 IR | ir | `77f3c7d` | 等候候选 |
| P0-04 StockWiki | stockwiki | `0fbaf7c` | 等候候选 |
| P0-05 IQS | iqs | `3094c5f` | 等候候选，保留原运行工区 |
| P0-06 CWP | cwp-p0 | `35b8b250d` | 等候候选，只接收 CWP 适配器、CLI 和定向用例 |
| P0-07 FF | ff | `4dd4e13` | 等候候选 |
| P0-08 SID | sid | `5c65605` | 等候候选 |
| P0-09 RF | rf | `782cfd9a` | 等候候选，以已验 SYSTEM 版本为运行基线 |
| P0-10 MC | mc | `7b83fe6` | 等候候选 |
| P0-11 Dashboard | dash | `de59fee` | 等候候选；集成时核验后续发布改动，见下 |
| P1-00 工具 | cwp | `35b8b250d` | 等候工具和正反例，自身可单独验收 |

`stockqa@86f633d` 是第 13 个预留工区，当前批次未派该卡。P0-12 的首轮只读清点发现 12 仓共登记 188 个 Git 工区，IQS 有 1 个被 Git 标记为 prunable；IQS 唯一标为 prunable 的记录属于 Dashboard 的独立施工项目，实际叶目录和上层工区仍存在。目前保留，等该 owner 确认有效入口与独有产物。总控已回收本轮两个用于发布的空临时工区。

**发布目标复核。** 独立核验发现，9 张卡与本地已有发布引用同版。CWP 两张卡的基线到总控 `e90a16c59` 只有两个 F4 文档提交。Dashboard 的 48766 部署记录（Dashboard 本仓 `.runtime/dashboard-m7-666e242/live-release.json`） 记载 20:20 UTC 已发布 `666e2426`，相对施工基线多 5 个提交。本地 main 与已知 origin/main 分别另有 6 和 8 个提交。在候选到达时刷新发布头，只合并故障修复，验证 `backend/dashboard/main.py` 与 `adapters/factory.py` 仍把 `rf_verified_scope_root` 传给 RF，保留已发布的作业分页。组合验收使用隔离目录与随机本地端口。

**ET 首页基线实测。** 总控从 Git 对象 `672ed1012e27685b58e501377f2548a859ff20da` 读取 reader、真实模板及其依赖，在临时目录放入空公司表与本地配置。用真实 `ReaderHandler` 监听 `127.0.0.1:0`。先 GET `/api/data` 返回 200 和空数据，再 GET `/`，客户端收到 `RemoteDisconnected`，服务端是 `NameError: _TEMPLATE_FILE`。临时目录已回收。此记录可直接作为 P0-02 的 RED；候选需让同一配置下首页返回 200，并保留其余卡内用例。
