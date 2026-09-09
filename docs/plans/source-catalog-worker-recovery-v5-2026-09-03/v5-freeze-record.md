# V5-2 冻结记录（2026-09-09；V5-2.2 二轮复审整改后）

状态：**FROZEN_FOR_INDEPENDENT_REVIEW**（PLAN_ONLY，未实施；本记录不构成实施授权）
冻结时点 HEAD：`85044ed8ced021eeb77565564e455274d0a2a5ad`（冻结产物随后入库）
本记录本身**不是冻结锚**：它承载"实测值"与偏差说明，可在同一 generation 内更正；锚点是 manifest + 冻结集 + 冻结内代码钉扎 + Git 提交。

冻结共三轮：

| 轮次 | 提交 | 触发 | 结果 |
|---|---|---|---|
| 首轮 | `454f632` | V5-2 初冻结 | 预冻结 7658、verify 8866、自测 17/17 |
| V5-2.1 | `917b8d8` | 三路审查共 9 条 P1 | 预冻结 7710、verify 9174、自测 17 例/27 变异全拒 |
| V5-2.2 | 本轮 | 复审又发现 2 条新 P1（N8 重跑可被 `sys.path[0]` 劫持、v4 锚自身未锚定） | 预冻结 **7720**、verify **9188**、自测 **17 例/31 变异 + 3 项默认模式检查**全拒 |

## 1. 冻结产物与哈希（V5-2.2）

| 文件 | sha256 | 字节 | 角色 |
|---|---|---|---|
| `plan_manifest.v5.json` | `fc2dfb60bd0e1195456b0018b77a3ffeb16c910104bf6a35523bc4330f229367` | 14122 | 冻结 manifest（自排除） |
| `plan_freeze_check.v5.txt` | `5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83` | 172 | 预冻结检查 stdout（0 个 CR） |
| `plan_manifest.schema.v5.json` | `ebc6c904fb06f2d857610638d9c172de0b3ab078155182857ec2b0c38cafce9a` | 7324 | 治理件（冻结集） |
| `tools/v5_plan_consistency_check.py` | `252c44a2d9dbe120f6982737ddbc614cd98cdfe3f962985ebd8d76fcca96a342` | 52485 | 治理件（冻结集） |
| `.gitattributes` | 见 manifest 首项 | 172 | 治理件（冻结集） |
| `tools/v5_freeze_manifest_build.py` | `d7377f24eccfbdfb3f5e0736ad304f5edebfa43ea0ff172f3efd366bd4eab88d` | 6577 | 生成器（**不入冻结集**） |
| `tools/v5_version_reference_scan.py` | `ab46623873e4c52969d52888b020c52a74f1323ff15022bbc83a02f342206407` | 10057 | 证据工具（manifest 绑定） |
| `tools/v5_equivalence_check.py` | `c29e19ad1d9392fcd546f3a2be163d0134ce85828927b9a429c239ac105a0874` | 3035 | 证据工具（manifest 绑定） |
| `v5-version-reference-inventory.json` | `c0a165bb1ccc12f891626faad8d7fa6a3242d9bf808d038c599530432ef601ad` | 30088 | 证据（manifest `evidence` 绑定） |
| `v5-baseline-equivalence.json` | `79ac6ca49ad7a7085cefcceeded65cc9d7fe2ae9f4bfcb26d608f20d867a0c67` | 2970 | 证据（manifest `evidence` 绑定） |
| `import_manifest.v5.json` | 见 manifest `capture_manifest` | 34238 | 捕获记录（manifest 绑定） |
| `v5-freeze-boundary.md` | `b5a8a67a2c7c0b8f654a95e07a787c59dc102f5dd100a9ac14f962caabbe9720` | 6009 | 边界记录 + N9 载荷（manifest `boundary_record` 绑定） |

冻结集构成：**51** = 导入计划输入 48（`baseline/plan/**`，递归枚举，含空目录检测）＋ v5 自有治理件 3；自排除 1。
等价性（逐件按字节复算，并与 v4 冻结 manifest、`v5-baseline-equivalence.json` 三方交叉核对）：`v4_exact` 21 / `crlf_only` 17 / `unproven_new_baseline` 10。

## 2. 协议 B1–B6 执行结果

| 步骤 | 结果 |
|---|---|
| B1 冻结前逐文件哈希 | 51 个文件快照（递归枚举；`baseline/plan/` 下出现任何文件或子目录即 `V5-SET-NESTED` red） |
| B2 运行全套一致性检查 | 预冻结：`PASS: 7720 checks; {"fixed_nodes":115,"schemas":29,"tests":315,"vectors":18}` |
| B3 冻结后重哈希 | 51/51 哈希与字节数一致；`baseline/plan/__pycache__` 与 `tools/__pycache__` 均不存在 |
| B4 `.gitattributes` 入集且属性全 unset | `git check-attr text eol filter working-tree-encoding` × 51 路径 = 204 行，全部 `unset` |
| B5 旧目录检查 | 机器载荷声明 `NON_AUTHORITATIVE`、38 文件、inventory `da927ee2…`；候选判据 = 目录名含 `source-catalog-worker-recovery` **或**含计划标记文件；载荷字节由 manifest 绑定 |
| B6 记录 HEAD / index | 冻结时点 HEAD `85044ed`；`plan_freeze_git_head` 由 N10 校验为「HEAD 的祖先且已包含导入语料」 |

后冻结复验（入库后）：`--verify-manifest` → `PASS: 9188 checks; {"fixed_nodes":115,"schemas":29,"tests":315,"vectors":18}`。
`--self-test` → **17 例 / 31 变异 + 3 项默认模式检查**，全部被拒。

> 计数是**运行环境相关的观测值**，不是冻结断言：`--verify-manifest` 的计数取决于 manifest 与 51 个冻结项是否已被 Git 跟踪（未跟踪时 N10 fail-closed 会 red）。**唯一的冻结断言**是 `plan_freeze_check.v5.txt` 的字节与哈希（172 字节、0 CR、`5e60611c…`），且 N8 会以 `-I` 隔离模式重跑默认模式逐字节比对。

## 3. 负例 N1–N17 自测（`--self-test`）

每条负例在临时副本上施加一个或多个定向变异，并断言对应编码在**全检查**与**仅该编码**两种模式下都被拒（隔离模式排除"别的检查顺手拦住"的假阳性）；另有三项默认模式检查单独自测。

| 编码 | 变异数 | 覆盖的复现配方 |
|---|---|---|
| N1 | 1 | 活动目录出现 `plan_manifest.v4.json` |
| N2 | 1 | manifest 指向已退役旧目录 |
| N3 | 1 | `freeze_generation` 改为 v6 |
| N4 | 1 | 未知字段 |
| N5 | 1 | 条目哈希改零 |
| N6 | 2 | **计数守恒的标签互换**；单件标签改动 |
| N7 | 3 | 改字节；**改字节 + 同步全部可写记录**（由 v4 冻结 manifest 锚定）；改名 |
| N8 | 3 | 伪造计数；**计数正确且哈希自洽**（由隔离重跑暴露）；命令藏在注释后 |
| N9 | 5 | 未申报兄弟副本；处置翻转；处置文件缺失；**改写退役副本并同步申报摘要**（由 manifest 绑定暴露）；**改名标记但保留目录名** |
| N10 | 2 | manifest 自身进入 normative 集；**提交后再改写已跟踪冻结文件**（Git blob 分支） |
| N11 | 2 | 取代链指向旧目录；西里尔字母形近路径 |
| N12 | 1 | investigation_source 指向旧目录 |
| N13 | 3 | 删条目；嵌套文件；**空子目录** |
| N14 | 1 | `.gitattributes` 移出冻结集 |
| N15 | 1 | capture manifest 的 generation 改为 v6 |
| N16 | 1 | 治理件标签改为 `v4_exact` |
| N17 | 2 | 证据工具哈希改零；证据输出哈希改零 |
| V5-TOOLS-EXACT | 1 | 向 `tools/` 植入 `json.py`（N8 子进程劫持的根因） |
| V5-SET-NESTED | 1 | `baseline/plan/nested/` 空目录 |
| V5-PATH-SAFETY | 1 | `tools/` 换成指向外部的 junction |

## 4. 与合同/既有语料的偏差与决策

| 编号 | 偏差 | 理由与影响 |
|---|---|---|
| D1 | 历史哈希钉按布局解析 | 基线 `IMMUTABLE_HISTORY_SHA256` 期望 `plan_manifest.v3.json` 位于 checker 的 `ROOT`；v5 导入把它放在 `baseline/history/`。checker 用同一期望哈希做布局感知解析（实测 `9ee84acd…` 等于钉值）。不改导入字节、不改冻结集。 |
| D2 | 禁止字节码写入 | 用 `importlib` 加载基线 checker 会在冻结目录内生成 `baseline/plan/__pycache__/*.pyc`。checker 置 `sys.dont_write_bytecode = True`，B3 断言 `baseline/plan/__pycache__` 与 `tools/__pycache__` 均不存在；证据工具永久排除 `__pycache__`。 |
| D3 | 预冻结输出强制 LF | Windows 文本模式 stdout 产出 CRLF。checker 统一 `reconfigure(encoding="utf-8", newline="\n")`；生成器在捕获含 CR 时中止。现产物 172 字节、0 个 CR。 |
| D4 | 证据范围收紧 | v5-1 证据范围含 v5 根目录活动文档（合同 §88 明确它们「活动，可更新」），冲突会使每次状态更新都让冻结证据失效。现范围 = `baseline/**`（54）＋ v5 根冻结输入（`.gitattributes`、`plan_manifest.schema.v5.json`）＝ **56**；排除活动文档、`v5-freeze-*` 记录与审查、两个冻结产物、`reviews/`、`tools/`、`import_manifest.v5.json`、`verify_import.py`、`__pycache__`。代价：活动文档中的旧目录引用不受机器检查覆盖（§6.5）。 |
| D5 | 生成器不入冻结集 | `tools/v5_freeze_manifest_build.py` 有写权限，不进入 48+3=51；manifest 的判定由 `--verify-manifest` 与 `--self-test` 承担。 |
| D6 | schema 路径正则放宽首位 `.` | `.gitattributes` 以点开头；改为 `^[A-Za-z0-9._]…`。只放宽合法路径集合。 |
| D7 | 合同计数行更新 | 合同 §3 的计数改为冻结时点实测值（41/12/8/10/30、`:v5`=3、`schema_version` ∈ {1,2}），并指向冻结证据 `totals`。 |
| D8 | 证据产物纳入 manifest 绑定（新增 `evidence` 字段） | 复审 TST-P1-2 指出证据输出未绑定、可被重新生成后与 manifest 自相矛盾。现 manifest 新增 `evidence`（两份证据的 path/sha256/size），N17 逐件比对。 |
| D9 | N9 载荷化（新增机器可读处置块） | 复审 LIF-P1-1 指出"文件存在即通过"不足。现 `v5-freeze-boundary.md` 携带 `disposition`/`retired_dirs` JSON 块，N9 复算 file_count 与 inventory 摘要，并要求任何候选目录都被申报。 |
| D10 | import 式加载的写入边界 | 以脚本执行零写入；以 import 加载本模块时，CPython 可能在模块体执行前为其自身写 `tools/__pycache__`。已在模块 docstring 声明，且该目录被 B3 断言与证据范围排除。 |
| D11 | N8 的重跑比对依赖真实 Git 树 | `N8` 的"重跑默认模式逐字节比对"在 `external=True`（真实树）时生效；自测用 N8.1（计数不符）、N8.2（临时 Git 仓库上的自洽伪造）、N8.3（注释藏命令）三个变异证明该编码有效。 |
| D12 | **冻结内代码钉扎历史文件** | 复审 NEW-P1-2 指出 N7 的 v4 锚自身可被改写。现 `PINNED_HISTORY_SHA256` 在**冻结集内**的 checker 里钉扎 6 份历史/来源文件（v3/v4 manifest、旧 progress/revision、事故报告、原调查报告）；改写任一份都必须同时改写冻结 checker（其哈希由 manifest 绑定）与 manifest（Git 跟踪），从而留下可见提交。 |
| D13 | **边界记录纳入 manifest 绑定** | 复审 SQL-P3-4 / LIF-P2-8 / TST-P2-1 指出 N9 处置载荷未锚定。现 manifest 新增 `boundary_record`（path + sha256），N9 校验其字节，"改副本 + 同步申报"会同时触发 N9 与绑定失败。 |
| D14 | **N8 子进程以 `-I` 隔离运行 + 枚举 `tools/`** | 复审 NEW-P1-1 证明子进程 `sys.path[0]=tools/` 可被植入 `tools/json.py` 劫持。现子进程加 `-I`（隐含 `-P`，不把脚本目录放进 `sys.path`），并新增 `V5-TOOLS-EXACT` 断言 `tools/` 恰为 4 个预期脚本。 |

## 5. 复现命令

```bash
cd <repo>
python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py
python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py --verify-manifest
python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py --self-test
python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_version_reference_scan.py --check
python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_equivalence_check.py --check
```

## 6. 残余风险（不隐瞒）

1. 冻结只覆盖**规划文档完整性**，不覆盖 worker 实现、配置、数据库、任务；v5 仍是 PLAN_ONLY。
2. 旧目录是**独立第三份副本**（38 文件，干净）。V5-2.2 把它变成"候选枚举 + 申报 + 摘要复算 + 载荷由 manifest 绑定"，但仍未删除、未加锁。
3. **N9 的判据边界**：同时改写目录名与全部标记文件的副本、以及位于 `docs/plans/` 之外的副本不在机器判据范围内。
4. 不可变性最终依赖 Git：N10 对 manifest + 51 个冻结项做 worktree↔HEAD blob 比对（未跟踪即 red），但一次**新的提交**本身不会被 N10 拦截——提交历史是唯一的最终账本；`frozen_at` 是声明值，无法被机器锚定（`plan_freeze_git_head` 已由 N10 校验为祖先且含语料）。
5. 活动文档（`README.md`/`task_plan.md`/`findings.md`/`progress.md`）中的旧目录引用不受证据或机器检查覆盖（D4 的代价）。
6. 本记录、三份审查记录与边界记录本身不在冻结集与证据范围内（避免自指），其完整性由 Git 与独立审查背书；边界记录另由 manifest `boundary_record` 绑定。
7. `.githooks/pre-commit` 仍会整仓 checkout + patch 恢复（v4 漂移事故的机制）。冻结窗口内 51 项零变化已实测，但该机制仍是并发写风险。
8. `reviews/old-plan-retirement-inventory.json` 含绝对个人路径（用户名 + 盘符）。该文件是历史记录，合同 §88（`reviews/` 行）规定不改字节，故**按设计保留**；其中不含任何凭据。

## 7. V5-2.1 复审整改（9 条 P1 逐条关闭）

| P1 | 来源 | 根因 | 整改 | 验证 |
|---|---|---|---|---|
| SQL-P1-1 / TST-P1-1 | SQL/性能、测试/DAG | N6 只核对标签计数，从不复算等价类别 | N6 对每个导入件用字节 + `historical_v4_sha256` 复算类别，并与 v4 冻结 manifest、`v5-baseline-equivalence.json` 逐件交叉核对 | 自测 N6.1 计数守恒互换被拒（全检查 + 隔离） |
| TST-P1-2 | 测试/DAG | 导入字节只锚在可写的 capture 记录上 | N7 增补 v4 冻结 manifest 锚；新增 `evidence` 绑定；N10 覆盖 51 项 + manifest 的 Git blob | 自测 N7.2 被拒；N17.2 被拒；**V5-2.2 再由 D12 钉扎 v4 锚自身** |
| TST-P1-3 | 测试/DAG | N8 不把预冻结产物绑定到真实运行 | N8 解析产物计数并与复算比对；真实树重跑逐字节比对；命令改 schema `const` | 自测 N8.1/N8.2/N8.3 全拒 |
| TST-P1-4 / SQL-P3-1 | 测试/DAG、SQL/性能 | command 只做子串匹配 | command 精确 `const` + 唯一 `.py` token + 禁 `#` | 自测 N8.3 被拒 |
| TST-P1-5 | 测试/DAG | 非递归枚举 | 递归枚举 + `V5-SET-NESTED` + N13 | 自测 N13.2/N13.3 被拒 |
| TST-P1-6 | 测试/DAG | N11 后缀匹配 + 静默回退 | `supersedes` schema `enum` + 恰好两条；N11 要求规范 ASCII 路径、禁旧目录、无回退 | 自测 N11.1/N11.2 被拒 |
| LIF-P1-1 | 生命周期/安全 | N9 只判"路径存在 + 文件存在" | N9 改为候选枚举 + 机器可读处置块 + 摘要复算（V5-2.2 再加 manifest 绑定） | 自测 N9.1–N9.5 全拒 |
| LIF-P1-2 | 生命周期/安全 | v4 的 reparse/包含路径安全不变量被丢弃 | 新增 `V5-PATH-SAFETY`（逐项 resolve 包含 + 逐段 reparse） | 默认模式 102 项；junction 变异被拒 |

## 8. V5-2.2 二轮复审整改（2 条新 P1 + P2）

| 新 P1 | 根因 | 整改 | 验证 |
|---|---|---|---|
| NEW-P1-1（TST） | N8 子进程 `sys.path[0]=tools/`，植入 `tools/json.py` 可劫持重跑 | 子进程加 `-I` 隔离；新增 `V5-TOOLS-EXACT` 断言 `tools/` 恰为 4 个脚本 | 自测 `V5-TOOLS-EXACT` 被拒；N8.2 在隔离下仍被拒 |
| NEW-P1-2（TST） | N7 的 v4 锚（`baseline/history/plan_manifest.v4.json`）不在冻结集也不在 N10 目标内，可被改写 | D12：在冻结内 checker 钉扎 6 份历史/来源文件；改写它们必须同时改冻结 checker 与 manifest | `PINNED-HISTORY` 6 项默认模式检查；N10 祖先/语料校验 |

| P2 | 处置 |
|---|---|
| N9 处置载荷未锚定（SQL-P3-4 / LIF-P2-8 / TST-P2-1） | 已修（D13：manifest `boundary_record` + 自测 N9.4） |
| 改名标记即可绕过 N9 候选判定（TST-P2-2） | 已修（候选 = 目录名含 `source-catalog-worker-recovery` **或** 含标记文件；自测 N9.5）；「同时改名」与「移出 docs/plans」列入 §6.3 |
| `baseline/plan` 下空子目录不可见 | 已修（递归枚举含目录；自测 N13.3） |
| N10 的 Git 分支无自测变异 | 已修（自测 N10.2 提交后改写） |
| `tools/` 未枚举（NEW-P1-1 根因） | 已修（`V5-TOOLS-EXACT`） |
| `V5-SET-GOVERNING` 恒真 | 已修（断言等于预期三元组且文件存在） |
| `evidence_tools` 非精确集合 | 已修（N17 断言恰为两项） |
| 畸形 manifest 崩溃而非给编码 | 已修（verify 包裹异常 → `N4`；自测同样包裹） |
| `plan_freeze_git_head` 未锚定 | 已修（N10 断言为 HEAD 祖先且该提交已含导入语料） |
| `frozen_at` 无法锚定 | 列入 §6.4（时间无法机器锚定，如实声明） |
| N6 路径错配时的误导归因 | 已修（capture 无记录时交给 N7 报告） |
| N2 子串误报（TST-P2-9） | 已修（改用 `docs/plans/<name>` 前缀） |
| 合同 §88 → §91 引用错位 | 本记录已改为 §88（`reviews/` 行）；合同行号以合同文本为准 |
| verify/self-test 耗时上升（SQL-OBS-1） | N10 的 156 次 git 子进程合并为 3 次；self-test 成本如实记录（一次性门禁） |
| `V5_PREFREEZE_CHILD` 死代码（SQL-OBS-2） | 已删除（改用 `-I`） |
