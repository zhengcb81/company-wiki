# V5-3 交接文档独立复核（axis：handover documentation & operational state）

- 复核对象：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03/README.md` 的 §1 阅读顺序、§3 历史索引、§4 worker 暂停审计、§5 残余风险、§6 实施顺序、§7 不授权；以及 `task_plan.md`、`findings.md`、`progress.md`、`v5-freeze-record.md` §6。
- 仓库：`C:\Users\郑曾波\Projects\company-wiki`；实测 HEAD `1a992cdf9576c49e047c7d6d184d6617514570bd`（2026-09-09T23:12:04+01:00）。V5-3 交接提交 `6559075` 是 HEAD 祖先，且 `git diff --stat 6559075 HEAD -- <v5 目录>` 为空（提交树内 v5 目录逐字节等于交接提交）。
- 复核身份：独立复核者，非作者；未修改/新增/删除本目录以外任何文件；未 `git add/commit/push`；未触碰 worker、数据库、计划任务、注册表；未改动 `baseline/**`、`tools/**` 或任何冻结产物。
- 方法：全部结论由本机实测得出（链接/计数/哈希逐项复算、冻结 checker 三模式重跑、worker 与自启动入口独立重查、路由文档交叉比对）。raw 输出见附录 A–D。

## 结论（verdict）

**`accepted_with_findings`**

计划本体（冻结 51 项、负例 N1–N17、三条验证命令、历史索引、计数、非授权声明）经独立复算**全部为真**：16 条 README 链接全部存在且指向正确目标，48/5/1/3/13/4 等计数全部正确，冻结记录 §1 的 13 个哈希/字节数全部逐字节复现，`python -I` 默认模式 stdout 与 `plan_freeze_check.v5.txt` **逐字节相同**（172 字节、0 CR、`5e60611c…`）。worker 暂停结论独立重查成立。**无 P0**。

但交接层存在必须修的材料性缺陷：**冻结记录在交接后被改动且未提交**（HEAD 不含其最新决定）、README §5 相对冻结记录 §6 漏 2 条风险且把一条已被记录判定为"结构上不可行"的建议留给实施者、`task_plan.md` 的 V5-3 段自相矛盾、根 `PLANNING_STATUS.md` 存在一条指向 v5 的过期状态行。

## 已验证为真的关键事实（复核通过项）

| 复核项 | 实测 |
|---|---|
| README 链接 | 提取 16 条 markdown 链接，`Test-Path` 全部 `True`（含 5 个 `baseline/plan/` 实施顺序指针） |
| 计数 | `baseline/plan` 递归 48 文件（含 0 个子目录/空目录）；`baseline/history` 5；`baseline/investigation` 1；`reviews` 3；`v5-freeze-review*` **13**；`v5-version-contract-review*` 4 |
| 冻结产物哈希 | 13 项全部与记录 §1 一致（`plan_manifest.v5.json` `f9735eb8…`/14125B、`plan_freeze_check.v5.txt` `5e60611c…`/172B/0CR、schema `d7218d36…`、checker `b5b2da6c…`/58055B、generator `5ece62bc…`、inventory `72db3a1a…`、equivalence `79ac6ca4…`、boundary `5e939d46…`） |
| §2 默认模式 | `PASS: 7720 checks`，exit 0；与冻结产物 `IDENTICAL=True`，同 sha256 |
| §2 `--verify-manifest` | `PASS: 9188 checks`，exit 0（**在冻结记录已被改动的脏工作树下仍通过**，印证 D4：该记录不在证据范围内） |
| §2 `--self-test` | exit 0，`17 cases / 32 mutations + 4 default-mode checks + 3 guard checks; failures=none`，实测墙钟 70.8s（README §5.8 的 11s→89s 区间内，非阻断） |
| 两个证据工具 | `--check` 均 `CHECK OK: … reproduces byte-for-byte`，exit 0 |
| 复核零写入 | 三模式与两工具跑完后 `git status --porcelain` 仅剩既有的冻结记录脏行；v5 目录下 `__pycache__` 计数 0（D2/B3 成立） |
| 旧目录复活声明 | `docs/plans/source-catalog-worker-recovery-2026-08-22/`：38 文件、38 tracked、`git status` 空、最新 mtime `2026-09-07T18:08:52.8971277Z` —— 与 README 第 6–8 行完全一致 |
| 历史钉扎计数 | checker `PINNED_HISTORY_SHA256` = 6 项（`baseline/history` 5 + `baseline/investigation` 1），故 README §2「钉扎 6 份」、§3「history 5 份被钉扎」均准确 |
| §4 worker 暂停 | 独立重查与 README 表格逐行一致，并新增服务/WMI/GPO/ActiveSetup/IFEO/全部计划任务文件夹等入口排查——**未发现 README 漏掉的自启动路径**（附录 A） |
| §7 不授权 | 全目录扫描 15 处授权相关命中**全部是否定式**（"不授权/不并入主线/尚未开始/未恢复"），无任何"已实施/可实施/授权实施"表述；"等待用户决定并入或实施"状态与 task_plan、progress、findings、current-delta 一致 |

## 发现表

| ID | 严重度 | 发现 | 证据（命令 + 实测输出） | 要求修复 |
|---|---|---|---|---|
| HDD-P1-1 | **P1** | **冻结记录（权威残余风险清单所在文件）在交接后被改动且未提交**：HEAD 不含其最新决定（SQL-OBS-3 结构性搁置，2026-09-10）。交接提交 `6559075` 与 HEAD 中该文件均无此行，故"交接出去的状态"与磁盘现状不一致；同时使 `current-delta-2026-09-09.md:16`「company-wiki 干净」变为不实陈述。冻结完整性未受影响（见上行 `--verify-manifest` 仍 9188）。 | `git status --porcelain` → ` M docs/plans/.../v5-freeze-record.md`；`git diff --stat` → `1 file changed, 1 insertion(+)`；`git show HEAD:docs/plans/.../v5-freeze-record.md \| Select-String 'SQL-OBS-3'` → 空（HEAD 无此行）；mtime `2026-09-10 20:29`（晚于交接提交 `2026-09-09T22:50:30+01:00`） | 提交该行（或在交接层显式撤销），并同步 `current-delta-2026-09-09.md` 与 `PLANNING_STATUS.md` 中"工作树干净"的表述；提交前重跑 `--verify-manifest`（应仍 9188） |
| HDD-P1-2 | **P1** | **README §5 只有 8 条残余风险，冻结记录 §6 有 9 条**：§6.6（本记录/审查记录/边界记录本身不在冻结集与证据范围内——这正是本记录可被改写的原因）与 §6.9（启动守卫与 `V5-TOOLS-EXACT` 只在 checker 真被运行时生效；`runpy.run_path` 等包装调用不覆盖，其它平台须重跑 `GUARD*` 自测）**均未出现**；README 反而用 §5.8（`--self-test` 墙钟）顶替，而该项并非 §6 条目。同一交接集内的 `progress.md` 第 101 行明确把 **§6.9** 列为剩余项，自相矛盾。 | README §5 逐条比对记录 §6（9 条）；`Select-String -Path README.md -Pattern 'H01\|prune'` 与 §6.9 关键词 → 无命中；`progress.md:101` → 「剩余项为记录已声明的残余风险 §6.3/§6.4/**§6.9**」 | 在 §5 补齐 §6.6 与 §6.9（或明写"以下为节选，完整 9 条见 §6"并逐条编号），使 §5 与 §6 一一对应 |
| HDD-P1-3 | **P1** | **README §5.8 给出的建议已被记录的最新决定判定为结构上不可行**：§5.8 建议把 `--self-test` 优化为"复制一次 + 逐例回滚"；记录的 2026-09-10 决定写明该优化在 generation v5 内**不可行**（改冻结 checker 会破坏冻结集哈希致 N5 red，向 `tools/` 加文件会破坏 `V5-TOOLS-EXACT`），只能留待 v6 与 manifest/schema 一并重设计。只读 README 的实施者照做即会打破冻结。`progress.md:102` 同样给出该建议。 | README:80 与 `progress.md:102` 的措辞；对比冻结记录 §8 末行（未提交的 SQL-OBS-3 行）；实测自测成本 70.8s、exit 0、零仓库写，属非阻断 | 把 §5.8 改为"结构性搁置至 v6"的结论（依赖 HDD-P1-1 的提交），并删除"建议改为复制一次+逐例回滚"的可执行暗示 |
| HDD-P1-4 | **P1** | **`task_plan.md`（README §1 的第 1 顺位入口）Phase V5-3 自相矛盾**：同一段先以 `[x]` 列出三项交付（第 66–71 行），随后又把**同样三项**以未勾选 `[ ]` 再列一遍（第 73–75 行），而该 Phase 标题写"状态：completed"。只读入口的读者会认为交接未完成，并可能重做 worker 暂停复核或误判隔离未落地。 | 读取 `task_plan.md` 64–75 行：`## Phase V5-3（交接）— 状态：completed（2026-09-09）` → 3×`[x]` → 紧接 3×`[ ]`（逐字重复） | 删除第 73–75 行的重复未勾选块 |
| HDD-P1-5 | **P1** | **根 `PLANNING_STATUS.md` 存在指向 v5 的过期状态行，与同文件第 17 行冲突**：第 53 行"worker 恢复规划"仍写 `V5_BASELINE_READY / VERSION_CONTRACT_PENDING / NOT_IMPLEMENTATION_AUTHORIZED`，而第 17 行与 v5 README 均为 `V5_2_COMPLETED / PLAN_ONLY`。该文件自称"全部活动计划与审计入口的唯一路由"，按"从哪里继续"表阅读会得出"版本合同/冻结尚未完成"的反向结论。（v5 目录自身文档一致；缺陷在路由文档。） | `PLANNING_STATUS.md:53` vs `:41`（row 17）vs `README.md:10`；`progress.md:82` 显示该过期 token 源自 2026-09-03 的历史状态值 | 把第 53 行状态更新为 `V5_2_COMPLETED / PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED`（或指向 row 17） |
| HDD-P2-1 | P2 | **README §7 缺少其它路由文档记为硬前置的 H01**：§7 只列"用户精确授权 + 隔离验证 + 持久领取/失败恢复闭环"；而 `PLANNING_STATUS.md` row 17 写"worker 恢复前置 H01"，同文件第 70 行与 R4 README 第 19 行把 H01（按旧归档日期判 due、却覆盖全部 retired EvidenceSpan 的自动 prune 风险）列为"恢复 worker 前应先堵住的数据安全缺口"。只读 README 的实施者会低估恢复前置。 | `Select-String -Path README.md -Pattern 'H01'` → 无命中（仅第 6 行"回收站"字样）；`PLANNING_STATUS.md:41,70`；`painpoint-outcome-audit-2026-09-05/README.md:19` | 在 §7（或 §5）显式引用 H01 作为恢复前置，并标明其归属 R4 |
| HDD-P2-2 | P2 | **README §4 只给结论、不给审计面与边界**，而同类文档都显式标注了自身审计的不可穷尽性（`PLANNING_STATUS.md:78`"未重新穷举所有可能的系统启动入口"；R4 README:50"CIM 进程查询权限不足"）。本次独立扩展排查（全部计划任务文件夹、服务、WMI `root\subscription`、GPO 登录脚本、Active Setup、IFEO/AppInit_DLLs、Winlogon、HKCU/HKLM/WOW6432Node/HKU Run）仍未发现 catalog/worker 入口，结论成立；但非提权会话下 3 个 HKU hive 与被保护任务不可读，边界客观存在。 | 附录 A 第 1–9 节命令与输出；`HKEY_USERS\S-1-5-19/20` 等 → `Requested registry access is not allowed`；`schtasks /query /tn revenue_daily_t2` → `ERROR: Access is denied.` | 在 §4 补"已审计面清单 + 未能覆盖的剩余面（未提权 hive/受保护任务）"，把结论写成有界否定 |
| HDD-P2-3 | P2 | **README §4"未被任何入口引用"未提示仓库内的再武装路径**：表述对"活动入口"成立，但产品自带且 tracked 的安装代码可以一键重建同一入口——`src/company_wiki/source_catalog/startup.py::install_startup_task` 会写 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`（`build_startup_registry_args`）并发 `schtasks /Create`，指向同一对 wrapper 脚本。§7 又禁止"运行登录测试"，故该 latent 入口应在交接层点名（R4 已设 AUTOSTART 授权门）。 | `Select-String startup.py -Pattern 'HKCU\|CurrentVersion\|/Create\|install_startup_task'` → 62/88-89/118 行命中；`git ls-files --error-unmatch src/company_wiki/source_catalog/startup.py` → tracked；`control.py:55,85` 同引用两 wrapper | 在 §4/§7 交叉引用该再武装路径与 R4 的 AUTOSTART 门，避免读者把"脚本未被引用"误读为"能力已移除" |
| HDD-P3-1 | P3 | **README §2 引用的期望 stdout 与真实字节不符（空格）**：README 写 `{"fixed_nodes":115,"schemas":29,…}`，而冻结产物与真实运行含空格 `{"fixed_nodes": 115, "schemas": 29, …}`。同一句又声明"与 `plan_freeze_check.v5.txt` 逐字节相同并给出 sha256"，照抄该串无法用于校验。 | `plan_freeze_check.v5.txt` repr = `b'PASS: 7720 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}\nREAD_ONLY: …\n'`；live repr 与之 `IDENTICAL=True` | 用真实字节（含空格、含 READ_ONLY 行）替换 §2 的引用串 |
| HDD-P3-2 | P3 | **README §5.7 相对记录 §6.8 过度泛化（overstated）**：§6.8 精确指 `reviews/old-plan-retirement-inventory.json` 含绝对个人路径，§5.7 写成"`reviews/` 历史文件含绝对个人路径"，读起来像整个 `reviews/` 目录。 | `Select-String reviews/* -Pattern 'C:\\Users\\'` → `old-plan-retirement-inventory.json` 3 处；`import-review-2026-09-03.md` 0；`old-plan-retirement-result.md` 0 | 在 §5.7 点名该文件 |
| HDD-P3-3 | P3 | **状态 token 命名落后于实际交付**：README 第 10 行写 `V5_2_COMPLETED`，但 V5-3（本次交接）已 completed（task_plan:64、progress:110、current-delta:23「V5-0/R/1/2/3 全部 completed」）。两个方向都不授权实施，仅为状态命名不一致。 | `README.md:10` vs `task_plan.md:64`、`progress.md:110`、`current-delta-2026-09-09.md:23` | 改为 `V5_3_COMPLETED / PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED`（或注明 token 只描述冻结里程碑） |

## 附录 A：worker 暂停与自启动入口 raw 结果（2026-09-10 实测）

1. 控制状态：`.source_catalog\worker_control.json`（178B，mtime `2026-08-20T21:43:32.3713867Z`）
   `{"desired_state": "paused", "paused_at": 1785095409.9560082, "schema_version": "1.0", "stop_requested_for": "8efeb3b1e30c4a70b8d6781ae7b1b226", "updated_at": 1787262212.3703358}`
   时间戳换算：`paused_at` → `2026-07-26T19:50:09.956008+00:00`；`updated_at` → `2026-08-20T21:43:32.370336+00:00` —— 与 README §4「`updated_at` 2026-08-20T21:43:32Z」一致。
2. 启动器末条事件（`worker_launcher_events.jsonl`，共 1187 行）：末行 `"recorded_at":"2026-08-20T21:43:37.4312532Z"`、`"status":"exited"`、`"reason":"persistent_pause"`、`"exit_code":2` —— 与 README §4 一致。
3. 进程：`Get-CimInstance Win32_Process` 全量命令行走查；`CommandLine -match 'source_catalog|worker_launcher|worker\.ps1|company-wiki'` 的命中项只有本次复核自身的 pwsh/node 进程。python 进程共 2 个，均为 `minimax-coding-plan-mcp.exe`（MCP，与 worker 无关）—— 与 README §4「无（仅有无关 MCP python 进程）」一致。
4. 计划任务：`Get-ScheduledTask` 可见 202 个任务（`schtasks /query /fo csv /nh` 283 行），按 `catalog|worker|company|wiki|source` 过滤任务名与路径**无命中**（唯一命中是 Windows 自带 `\Microsoft\Windows\LanguageComponentsInstaller\ReconcileLanguageResources`，因 "Resources" 误匹配）；`Get-ScheduledTask | ? TaskName -eq 'CompanyWiki Source Catalog'` → **NOT REGISTERED**。全部任务文件夹已列（`\`、`\GoogleUserPEH\`、`\SoftLanding\*\`、`\Microsoft\**`），非 Microsoft 任务 11 个，其 Actions 中无一引用 python/company-wiki/`.vbs`/`AppData`。
5. 注册表自启动：HKCU/HKLM `Run`、`RunOnce`、`Policies\Explorer\Run`（不存在）、`WOW6432Node\Run(RunOnce)`、`Winlogon`（`Shell=explorer.exe`、`Userinit=C:\WINDOWS\system32\userinit.exe,`）、`HKCU\...\Explorer\StartupApproved\Run`、`HKLM\...\Windows`（`AppInit_DLLs=` 空、`LoadAppInit_DLLs=0`）—— 逐项列出，**无 source_catalog/CompanyWiki 条目**。`HKEY_USERS` 全部可读 hive 的 Run/RunOnce 亦无匹配（`.DEFAULT`、`S-1-5-21-…-1002`、`S-1-5-18` 仅有 OneDrive/Claude/GoogleDriveFS/Edge/Adobe 等）。
6. 启动文件夹：`%APPDATA%\…\Startup` 与 `%ProgramData%\…\Startup` 均**仅 `desktop.ini`**（174B）—— 与 README §4 一致。
7. 其它被主动排查的入口（README 未声明、本次新增）：`Win32_Service`（名称/显示名/PathName 匹配 catalog/worker/companywiki → **无**）；WMI `root\subscription` 的 `__EventFilter` 仅系统自带 `SCM Event Log Filter`，`__EventLogConsumer` 非命令行/脚本消费者，无 CommandLineEventConsumer/ActiveScriptEventConsumer；`System32\GroupPolicy\{Machine,User}\Scripts\scripts.ini` **不存在**，`HKCU\...\Group Policy\Scripts` 无内容；`Active Setup\Installed Components` 无 catalog/wiki/worker 项；IFEO 子键全部为常见应用（无 mshta/wscript 劫持类异常）；`Session Manager` 的 `BootExecute`/`RunLevelExecute` 为系统默认。
8. 未能覆盖的剩余面（诚实边界）：`HKEY_USERS\S-1-5-19`、`S-1-5-20` 及另一 SID → `Requested registry access is not allowed`；`schtasks /query /tn revenue_daily_t2` 与 `revenue_weekly_t3` → `ERROR: Access is denied.`（**注意：这不是通用"找不到"错误**——同一命令对不存在的 `zzz_no_such_task_xyz_12345` 与自造名 `revenue_t2_daily` 返回的是 `ERROR: The system cannot find the file specified.`）。故 README §4 第 8 行把三个营收任务记为 `unknown` 是**正确且未夸大**的表述。
9. 自启动脚本与引用：`scripts\source_catalog_worker_at_logon.ps1|.vbs`、`scripts\source_catalog_worker.ps1` **均存在**（git tracked）。全仓 `git grep -F` 三个文件名：命中的都是**历史/文档/产品代码**（`docs/contracts/legacy-caller-reachability-v1.md`、v5 `baseline/plan/findings.md`、原调查报告、根 `findings.md`/`progress.md`）与产品自身实现（`scripts/source_catalog_worker.ps1:173-174` 计算这两个脚本的哈希、`source_catalog_worker_at_logon.vbs:19` 调用 ps1、`src/company_wiki/source_catalog/startup.py:38,130-131` 与 `control.py:55,85`）——**没有任何活动入口引用**（无 Run 值、无计划任务、无启动文件夹项），与 README §4 一致；再武装能力见 HDD-P2-3。
10. 追加负面证据：`.source_catalog` 下 929 个文件中，**2026-08-21 之后无任何 worker 相关写入**；仅 `legacy_periods.json`（2026-09-09T21:00:21Z，daily 观察）与 `catalog.sqlite3`（2026-09-08T21:23:21Z）与其 `-shm` 更新，`control_center.log`/`worker_control.json`/`worker_state.json` 分别停在 2026-08-20/2026-08-12 —— 支持"持久暂停"结论，同时说明 catalog 库近期由 daily 观察（非 worker）写入。

## 附录 B：冻结可复现性 raw 结果

```
$ python -I docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py
PASS: 7720 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}
READ_ONLY: no production database, registry, process, source, config, or network access
exit=0 elapsed≈2s

$ python -I .../v5_plan_consistency_check.py --verify-manifest
PASS: 9188 checks; {...same counts...}
exit=0 elapsed≈4.3s

$ python -I .../v5_plan_consistency_check.py --self-test
SELF-TEST N1..N17 PASS: rejected (full+isolated)   [32 mutations]
SELF-TEST V5-TOOLS-EXACT.py/.pyc, V5-SET-NESTED.dir, V5-PATH-SAFETY.junction PASS
SELF-TEST GUARD / GUARD-I / GUARD-M PASS
SELF-TEST: 17 cases / 32 mutations + 4 default-mode checks + 3 guard checks; failures=none
exit=0 ELAPSED_SEC=70.8

$ python -I .../v5_version_reference_scan.py --check   -> CHECK OK: inventory .json and .md reproduce byte-for-byte   exit=0
$ python -I .../v5_equivalence_check.py --check        -> CHECK OK: v5-baseline-equivalence.json reproduces byte-for-byte  exit=0
```

逐字节比对（`subprocess.run([sys.executable,'-I',chk],capture_output=True)` 与产物 `read_bytes()`）：

```
FROZEN len=172 sha=5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83
LIVE   len=172 sha=5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83
IDENTICAL=True
```

## 附录 C：链接/计数审计 raw 结果

- README 链接 16 条，`Test-Path` 全 `True`：`../painpoint-outcome-audit-2026-09-05/simplified-execution-plan.md`、`task_plan.md`、`findings.md`、`progress.md`、`v5-version-contract.md`、`plan_manifest.v5.json`、`plan_freeze_check.v5.txt`、`v5-freeze-record.md`（×2）、`v5-freeze-boundary.md`、`tools/v5_plan_consistency_check.py`、`baseline/plan/task_plan.md`、`baseline/plan/execution_playbook.md`、`baseline/plan/gate_dag.v4.json`、`baseline/plan/test_acceptance_plan.md`、`baseline/plan/test_id_registry.v4.json`。**无死链、无错目标**。
- 计数：`baseline\plan` 递归 48 文件 / 48 条目（含目录）→ 无嵌套文件、无空子目录（与 `V5-SET-NESTED` 前置一致）；`baseline\history` 5；`baseline\investigation` 1；`reviews` 3（`import-review-2026-09-03.md`、`old-plan-retirement-inventory.json`、`old-plan-retirement-result.md`）；`v5-freeze-review*` **13**（lifecycle-security ×4、sql-performance ×4、test-dag ×5）；`v5-version-contract-review*` 4。README §3 的"13 份"指冻结三轴审查/关闭记录，与实测一致（版本合同四轮审查在另一行单列，不重复计入）。
- 冻结集与节点数：`fixed_nodes 115`、`schemas 29`、`tests 315`、`vectors 18`（checker 复算值），与 README §6「115 个固定节点」「315 个测试 ID」、§2 期望输出一致。
- 证据工具/证据：`v5-version-reference-inventory.{json,md}` 与 `v5-baseline-equivalence.json` 均存在且 `--check` 字节可复现。

## 附录 D：路由一致性 raw 结果

| 文档 | v5 状态表述 | 判定 |
|---|---|---|
| `PLANNING_STATUS.md` row 17（第 41 行） | "V5-0/R/1/2/3 **全部 completed**，2026-09-09"；`V5_2_COMPLETED / PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED`；"与主线不合并；worker 恢复前置 H01；冻结 51 项 + 三轴审查 accepted" | 与 README 一致 ✓ |
| `PLANNING_STATUS.md` 第 53 行（"从哪里继续"表） | `V5_BASELINE_READY / VERSION_CONTRACT_PENDING / NOT_IMPLEMENTATION_AUTHORIZED` | **过期，冲突** → HDD-P1-5 |
| `PLANNING_STATUS.md` 第 78/80 行（Worker 安全边界） | 明确自限："未重新穷举所有可能的系统启动入口"、"CIM 查询被拒，不能沿用推断零进程" | 诚实边界；与 v5 README §4 的更强结论**不冲突**（本次独立重查支持 v5 结论），但提示 §4 应自带边界 → HDD-P2-2 |
| R4 `README.md` 第 3 行 | "worker v5 独立轨道全部完成（冻结 51 项 + 三轴独立审查 accepted，仍 PLAN_ONLY、不授权实施）" | 一致 ✓ |
| R4 `current-delta-2026-09-09.md` §2 | "V5-0/V5-R/V5-1/V5-2/V5-3 全部 completed"；`--verify-manifest` 9188；`--self-test` 17/32+4+3；"NOT_IMPLEMENTATION_AUTHORIZED 不变，H01 风险与隔离验证仍需 R4 各自取证" | 一致 ✓（H01 仅此处与 PLANNING_STATUS 提及，README 缺 → HDD-P2-1） |
| R4 `current-delta-2026-09-09.md` 第 16 行 | "company-wiki 干净" | 该文档写于 2026-09-09 23:02，属当时快照；但现状已被 2026-09-10 的未提交改动破坏 → HDD-P1-1 |
| R4 `README.md` 第 36 行 | 把 "旧空间治理/section/portfolio/**v5**" 一并路由到 `historical-projects-audit.md` / `legacy-inheritance.md` | 易误读：该两文件实际把 v5 记为"隔离修复规划，不是已实施产品"（`historical-projects-audit.md:39-41`），并未把 v5 当历史项目关闭；路由措辞可更精确（P3 级观察，未单列发现） |

## 附录 E：复核范围声明

- 本次仅**新增本文件**一个路径。全部命令为只读（`Get-*`/`Select-String`/`git status|diff|show|ls-files|grep|merge-base`/冻结 checker 三模式/两个证据工具 `--check`），未执行 `git add|commit|push|checkout|stash`，未注册/删除计划任务，未启动/停止任何进程，未写数据库或 registry，未修改 `baseline/**`、`tools/**`、冻结产物或任何被引用的历史文件。
- 冻结 checker 三模式与两证据工具跑完后仓库状态未变（唯一脏行是复核开始前即存在的 `v5-freeze-record.md`），v5 目录下无 `__pycache__`。
- 本文件不构成实施、worker 恢复、合并或任何形式的授权；上述所有发现均属规划/文档层，不改变 worker 的持久暂停状态。
