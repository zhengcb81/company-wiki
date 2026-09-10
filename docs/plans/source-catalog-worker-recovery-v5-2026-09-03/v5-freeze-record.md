# V5-2 冻结记录（2026-09-09；V5-2.4 四轮复审整改后）

状态：**FROZEN_FOR_INDEPENDENT_REVIEW**（PLAN_ONLY，未实施；本记录不构成实施授权）
冻结时点 HEAD：`89c0862d9a8b0fc9cc1edb0e243aa6aa39845b40`（冻结产物随后入库）
本记录本身**不是冻结锚**：它承载"实测值"与偏差说明，可在同一 generation 内更正；锚点是 manifest + 冻结集 + 冻结内代码钉扎 + Git 提交。

冻结共五轮：

| 轮次 | 提交 | 触发 | 结果 |
|---|---|---|---|
| 首轮 | `454f632` | V5-2 初冻结 | 预冻结 7658、verify 8866、自测 17/17 |
| V5-2.1 | `917b8d8` | 三路审查共 9 条 P1 | 预冻结 7710、verify 9174、自测 17 例/27 变异全拒 |
| V5-2.2 | `9418e72` | 二轮复审 2 条新 P1（N8 子进程劫持、v4 锚未锚定） | 预冻结 7720、verify 9188、自测 17/31+3 全拒 |
| V5-2.3 | `89c0862` | 三轮复审 3 条新 P1（父进程 import 劫持、N10 退化为索引比对） | 预冻结 **7720**（stdout 与上轮逐字节相同）、verify **9188**、自测 17/32+4+2 全拒 |
| V5-2.4 | 本轮 | 四轮复审 3 条 P2（`python -m` 绕过守卫、N6 汇总误报、记录措辞） | 同上产物计数；自测 **17 例/32 变异 + 4 默认模式检查 + 3 守卫检查**全拒 |

## 1. 冻结产物与哈希（V5-2.4）

| 文件 | sha256 | 字节 | 角色 |
|---|---|---|---|
| `plan_manifest.v5.json` | `f9735eb8e3128f8920c5bdd1a45d434428afa48d4c334fc7b7731a4e1bc252d3` | 14125 | 冻结 manifest（自排除） |
| `plan_freeze_check.v5.txt` | `5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83` | 172 | 预冻结检查 stdout（0 个 CR） |
| `plan_manifest.schema.v5.json` | `d7218d36e0e5134699581f136995e18b7483406befadc8b5f5b0fa738733c1e0` | 7327 | 治理件（冻结集） |
| `tools/v5_plan_consistency_check.py` | `b5b2da6caa5531a7ca2a3fa0793b3053cb88b699a934100a96e729183796ea38` | 58055 | 治理件（冻结集） |
| `.gitattributes` | 见 manifest 首项 | 172 | 治理件（冻结集） |
| `tools/v5_freeze_manifest_build.py` | `5ece62bc9c4a07fbed8c5f254efea983c7790b196f5fefb20ad77e18390ad459` | 6586 | 生成器（**不入冻结集**） |
| `tools/v5_version_reference_scan.py` | 见 manifest `evidence_tools` | 10057 | 证据工具（manifest 绑定） |
| `tools/v5_equivalence_check.py` | 见 manifest `evidence_tools` | 3035 | 证据工具（manifest 绑定） |
| `v5-version-reference-inventory.json` | `72db3a1ac13c0e94a6448852de7b2873b12896ca958d5d39db18d146d640b70b` | 29973 | 证据（manifest `evidence` 绑定） |
| `v5-baseline-equivalence.json` | `79ac6ca49ad7a7085cefcceeded65cc9d7fe2ae9f4bfcb26d608f20d867a0c67` | 2970 | 证据（manifest `evidence` 绑定） |
| `import_manifest.v5.json` | 见 manifest `capture_manifest` | 34238 | 捕获记录（manifest 绑定） |
| `v5-freeze-boundary.md` | `5e939d4646d233506447e6ca545c293347a9cfc86a62fe45b22f4b0ee9e47906` | 7262 | 边界记录 + N9 载荷 + 调用方式要求（manifest `boundary_record` 绑定） |

冻结集构成：**51** = 导入计划输入 48（`baseline/plan/**`，递归枚举，含空目录检测）＋ v5 自有治理件 3；自排除 1。
等价性（逐件按字节复算，并与 v4 冻结 manifest、`v5-baseline-equivalence.json` 三方交叉核对）：`v4_exact` 21 / `crlf_only` 17 / `unproven_new_baseline` 10。

## 2. 协议 B1–B6 执行结果

| 步骤 | 结果 |
|---|---|
| B1 冻结前逐文件哈希 | 51 个文件快照（递归枚举；`baseline/plan/` 下出现任何文件或子目录即 `V5-SET-NESTED` red） |
| B2 运行全套一致性检查 | 预冻结：`PASS: 7720 checks; {"fixed_nodes":115,"schemas":29,"tests":315,"vectors":18}`（命令 `python -I <checker>`） |
| B3 冻结后重哈希 | 51/51 哈希与字节数一致；`baseline/plan/__pycache__` 与 `tools/__pycache__` 均不存在 |
| B4 `.gitattributes` 入集且属性全 unset | `git check-attr text eol filter working-tree-encoding` × 51 路径 = 204 行，全部 `unset` |
| B5 旧目录检查 | 机器载荷声明 `NON_AUTHORITATIVE`、38 文件、inventory `da927ee2…`；候选判据 = 目录名含 `source-catalog-worker-recovery` **或**含计划标记文件；载荷字节由 manifest 绑定 |
| B6 记录 HEAD / index | 冻结时点 HEAD **`89c0862d`**（= manifest 的 `plan_freeze_git_head`，由 N10 校验为「HEAD 的祖先且已包含导入语料」）；冻结**产物**提交为 `4f4dea1`。两者不同：前者是生成 manifest 时的仓库 HEAD，后者是产物入库的提交 |

后冻结复验（入库后）：`--verify-manifest` → `PASS: 9188 checks; {"fixed_nodes":115,"schemas":29,"tests":315,"vectors":18}`。
`--self-test` → **17 例 / 32 变异 + 4 默认模式检查 + 3 守卫检查**，全部被拒。

> 计数是**运行环境相关的观测值**，不是冻结断言：`--verify-manifest` 的计数取决于 manifest 与 51 个冻结项是否已被 Git 跟踪（未跟踪时 N10 fail-closed 会 red）。**唯一的冻结断言**是 `plan_freeze_check.v5.txt` 的字节与哈希（172 字节、0 CR、`5e60611c…`），且 N8 以 manifest 记录的命令（含 `-I`）重跑并逐字节比对。

## 3. 负例 N1–N17 自测（`--self-test`）

每条负例在临时副本上施加一个或多个定向变异，并断言对应编码在**全检查**与**仅该编码**两种模式下都被拒（隔离模式排除"别的检查顺手拦住"的假阳性）；另有 4 项默认模式检查与 3 项守卫检查（GUARD / GUARD-I / GUARD-M）单独自测。

| 编码 | 变异数 | 覆盖的复现配方 |
|---|---|---|
| N1 | 1 | 活动目录出现 `plan_manifest.v4.json` |
| N2 | 1 | manifest 指向已退役旧目录 |
| N3 | 1 | `freeze_generation` 改为 v6 |
| N4 | 1 | 未知字段 |
| N5 | 1 | 条目哈希改零 |
| N6 | 2 | **计数守恒的标签互换**；单件标签改动 |
| N7 | 3 | 改字节；**改字节 + 同步全部可写记录**（由 v4 冻结 manifest 锚定）；改名 |
| N8 | 3 | 伪造计数；**计数正确且哈希自洽**（由 `-I` 重跑暴露）；命令藏在注释后 |
| N9 | 5 | 未申报兄弟副本；处置翻转；处置文件缺失；**改写退役副本并同步申报摘要**（由 manifest 绑定暴露）；**改名标记但保留目录名** |
| N10 | 3 | manifest 自身进入 normative 集；**提交后改写**；**改写并 `git add` 暂存**（HEAD 比对分支） |
| N11 | 2 | 取代链指向旧目录；西里尔字母形近路径 |
| N12 | 1 | investigation_source 指向旧目录 |
| N13 | 3 | 删条目；嵌套文件；**空子目录** |
| N14 | 1 | `.gitattributes` 移出冻结集 |
| N15 | 1 | capture manifest 的 generation 改为 v6 |
| N16 | 1 | 治理件标签改为 `v4_exact` |
| N17 | 2 | 证据工具哈希改零；证据输出哈希改零 |
| V5-TOOLS-EXACT | 2 | 植入 `tools/json.py`；植入 `tools/json.pyc`（非 `.py`） |
| V5-SET-NESTED | 1 | `baseline/plan/nested/` 空目录 |
| V5-PATH-SAFETY | 1 | `tools/` 换成指向外部的 junction |
| GUARD / GUARD-I / GUARD-M | 3 | 不带 `-I` 时植入的 `tools/json.py` 无法伪造 PASS；带 `-I` 时该植入被 `V5-TOOLS-EXACT` 报出；`python -m tools.<checker>` 被守卫拒绝（cwd 植入无法伪造） |

## 4. 与合同/既有语料的偏差与决策

| 编号 | 偏差 | 理由与影响 |
|---|---|---|
| D1 | 历史哈希钉按布局解析 | 基线 `IMMUTABLE_HISTORY_SHA256` 期望 `plan_manifest.v3.json` 位于 checker 的 `ROOT`；v5 导入把它放在 `baseline/history/`。checker 用同一期望哈希做布局感知解析（实测 `9ee84acd…` 等于钉值）。不改导入字节、不改冻结集。 |
| D2 | 禁止字节码写入 | 用 `importlib` 加载基线 checker 会在冻结目录内生成 `baseline/plan/__pycache__/*.pyc`。checker 置 `sys.dont_write_bytecode = True`，B3 断言 `baseline/plan/__pycache__` 与 `tools/__pycache__` 均不存在；证据工具永久排除 `__pycache__`。 |
| D3 | 预冻结输出强制 LF | Windows 文本模式 stdout 产出 CRLF。checker 统一 `reconfigure(encoding="utf-8", newline="\n")`；生成器在捕获含 CR 时中止。现产物 172 字节、0 个 CR。 |
| D4 | 证据范围收紧 | v5-1 证据范围含 v5 根目录活动文档（合同 §6.2 明确它们「活动，可更新」），冲突会使每次状态更新都让冻结证据失效。现范围 = `baseline/**`（54）＋ v5 根冻结输入（`.gitattributes`、`plan_manifest.schema.v5.json`）＝ **56**；排除活动文档、`v5-freeze-*` 记录与审查、两个冻结产物、`reviews/`、`tools/`、`import_manifest.v5.json`、`verify_import.py`、`__pycache__`。代价：活动文档中的旧目录引用不受机器检查覆盖（§6.5）。 |
| D5 | 生成器不入冻结集 | `tools/v5_freeze_manifest_build.py` 有写权限，不进入 48+3=51；manifest 的判定由 `--verify-manifest` 与 `--self-test` 承担。 |
| D6 | schema 路径正则放宽首位 `.` | `.gitattributes` 以点开头；改为 `^[A-Za-z0-9._]…`。只放宽合法路径集合。 |
| D7 | 合同计数行更新 | 合同 §3 的计数改为冻结时点实测值（41/12/8/10/30、`:v5`=3、`schema_version` ∈ {1,2}），并指向冻结证据 `totals`。 |
| D8 | 证据产物纳入 manifest 绑定（新增 `evidence` 字段） | 复审 TST-P1-2 指出证据输出未绑定。现 manifest 新增 `evidence`（两份证据的 path/sha256/size），N17 逐件比对。 |
| D9 | N9 载荷化（新增机器可读处置块） | 复审 LIF-P1-1 指出"文件存在即通过"不足。现 `v5-freeze-boundary.md` 携带 `disposition`/`retired_dirs` JSON 块，N9 复算 file_count 与 inventory 摘要，并要求任何候选目录都被申报。 |
| D10 | import 式加载的写入边界 | 以脚本执行零写入；以 import 加载本模块时，CPython 可能在模块体执行前为其自身写 `tools/__pycache__`。已在模块 docstring 声明，且该目录被 B3 断言与证据范围排除。 |
| D11 | N8 的重跑比对依赖真实 Git 树 | `N8` 的"重跑默认模式逐字节比对"在 `external=True`（真实树）时生效；自测用 N8.1/N8.2/N8.3 三个变异证明该编码有效。 |
| D12 | 冻结内代码钉扎历史文件 | 复审 NEW-P1-2 指出 N7 的 v4 锚自身可被改写。现 `PINNED_HISTORY_SHA256` 在**冻结集内**的 checker 里钉扎 6 份历史/来源文件；改写任一份都必须同时改写冻结 checker（其哈希由 manifest 绑定）与 manifest（Git 跟踪），从而留下可见提交。 |
| D13 | 边界记录纳入 manifest 绑定 | 复审 SQL-P3-4 / LIF-P2-8 / TST-P2-1 指出 N9 处置载荷未锚定。现 manifest 新增 `boundary_record`（path + sha256），N9 校验其字节。 |
| D14 | N8 子进程以 `-I` 隔离 + 枚举 `tools/` | 复审 NEW-P1-1 证明子进程 `sys.path[0]=tools/` 可被植入模块劫持。子进程加 `-I`；新增 `V5-TOOLS-EXACT`。 |
| D15 | **调用方式强制 `-I` + 启动守卫 + 全文件枚举** | 复审 NEW-P1-1-R / SQL-P1-3 证明**父进程**同样可被 `tools/json.py` 或 `tools/json.pyc` 在 import 期劫持并伪造 PASS。现：① checker 在任何标准库/第三方导入之前只用内建 `sys` 自检 `sys.path[0]`，不满足即 FAIL 退出；② 文档化命令、schema `const`、生成器调用、N8 重跑、两个证据工具子进程全部带 `-I`；③ `V5-TOOLS-EXACT` 枚举 `tools/` 下全部文件（含 `.pyc`，仅豁免 `__pycache__`）。自测含 GUARD/GUARD-I 两项。 |
| D16 | **N10 改比 HEAD 而非索引** | 复审 SQL-P1-2 证明批量化的 `git ls-files -s` 读的是**索引** blob，故"改写冻结文件 + `git add`（未提交）"可绕过。现改用 `git ls-tree -r HEAD -- <paths>`（仍为 1 次调用）与工作树 blob 比对；自测新增 N10.3「提交后改写并暂存」。 |
| D17 | **守卫改为要求隔离解释器（覆盖 `-m`）** | 复审 NEW-P2-C 证明 `python -m tools.<checker>` 时 `sys.path[0]` 是当前目录而非脚本目录，仅比较脚本目录会被绕过。现守卫直接要求 `sys.flags.isolated` 为真（并保留 `sys.path[0]` 比对），覆盖 `python <script>`、相对路径与 `-m` 三种形态；自测新增 GUARD-M。 |

## 5. 复现命令

```bash
cd <repo>
python -I docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py
python -I docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py --verify-manifest
python -I docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py --self-test
python -I docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_version_reference_scan.py --check
python -I docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_equivalence_check.py --check
```

不带 `-I` 运行会被 checker 的启动守卫拒绝（exit 1），这是设计意图。

## 6. 残余风险（不隐瞒）

1. 冻结只覆盖**规划文档完整性**，不覆盖 worker 实现、配置、数据库、任务；v5 仍是 PLAN_ONLY。
2. 旧目录是**独立第三份副本**（38 文件，干净）。V5-2.2 把它变成"候选枚举 + 申报 + 摘要复算 + 载荷由 manifest 绑定"，但仍未删除、未加锁。
3. **N9 的判据边界**：同时改写目录名与全部标记文件的副本、以及位于 `docs/plans/` 之外的副本不在机器判据范围内。
4. 不可变性最终依赖 Git：N10 对 manifest + 51 个冻结项做 **worktree↔HEAD** blob 比对（未跟踪即 red；V5-2.3 起不再误比索引），但一次**新的提交**本身不会被 N10 拦截——提交历史是唯一的最终账本；`frozen_at` 是声明值，无法被机器锚定（`plan_freeze_git_head` 已由 N10 校验为祖先且含语料）。
5. 活动文档（`README.md`/`task_plan.md`/`findings.md`/`progress.md`）中的旧目录引用不受证据或机器检查覆盖（D4 的代价）。
6. 本记录、审查记录与边界记录本身不在冻结集与证据范围内（避免自指）；边界记录另由 manifest `boundary_record` 绑定。
7. `.githooks/pre-commit` 仍会整仓 checkout + patch 恢复（v4 漂移事故的机制）。冻结窗口内 51 项零变化已实测，但该机制仍是并发写风险。
8. `reviews/old-plan-retirement-inventory.json` 含绝对个人路径（用户名 + 盘符）。该文件是历史记录，合同 §6.2 的 `reviews/` 行（合同文本第 91 行）规定「历史；不改字节」，故**按设计保留**；其中不含任何凭据。
9. 启动守卫与 `V5-TOOLS-EXACT` 只在 checker 真的被运行时生效；若有人用**另一个**解释器包装脚本运行（如 `runpy.run_path` 且未把计划目录放进 `sys.path`），防御不覆盖（调用方须遵守 §5/§6 的 `-I` 约定）。守卫覆盖 `python <script>`、相对路径与 `python -m tools.<checker>` 三种形态；其它平台/解释器需重跑 `GUARD*` 自测确认。

## 7. V5-2.1 复审整改（9 条首轮 P1）

| P1 | 根因 | 整改 | 验证 |
|---|---|---|---|
| SQL-P1-1 / TST-P1-1 | N6 只核对标签计数 | N6 逐件按字节复算，并与 v4 冻结 manifest、证据 JSON 交叉核对 | 自测 N6.1/N6.2 |
| TST-P1-2 | 导入字节只锚在可写捕获记录 | N7 增补 v4 冻结 manifest 锚；`evidence` 绑定；N10 覆盖 51 项 + manifest | 自测 N7.2/N17.2；V5-2.2 再由 D12 钉扎 v4 锚 |
| TST-P1-3 | N8 未绑定真实运行 | N8 解析产物计数 + 真实树重跑逐字节比对 + 命令 `const` | 自测 N8.1–N8.3 |
| TST-P1-4 / SQL-P3-1 | command 子串匹配 | 精确 `const` + 唯一 `.py` token + 禁 `#` | 自测 N8.3 |
| TST-P1-5 | 非递归枚举 | 递归枚举 + `V5-SET-NESTED` + N13 | 自测 N13.2/N13.3 |
| TST-P1-6 | N11 后缀匹配 + 回退 | schema `enum` + 恰好两条 + 规范路径 | 自测 N11.1/N11.2 |
| LIF-P1-1 | N9 判据不足 | 候选枚举 + 机器载荷 + 摘要复算 | 自测 N9.1–N9.5 |
| LIF-P1-2 | 路径安全不变量丢失 | `V5-PATH-SAFETY`（resolve 包含 + reparse 逐段） | junction 变异被拒 |

## 8. V5-2.2 / V5-2.3 二、三轮复审整改

| 新 P1 | 根因 | 整改 | 验证 |
|---|---|---|---|
| NEW-P1-1（二轮） | N8 子进程 `sys.path[0]=tools/` | 子进程 `-I`；`V5-TOOLS-EXACT` | 自测 V5-TOOLS-EXACT.py/.pyc、N8.2 |
| NEW-P1-2（二轮） | v4 锚自身未锚定 | D12 冻结内代码钉扎 6 份历史文件 | `PINNED-HISTORY` 6/6；N10 祖先/语料校验 |
| **NEW-P1-1-R（三轮）** | **父进程 import 期劫持（`tools/json.py`/`.pyc`）** | D15：启动守卫 + 全链路 `-I` + 全文件枚举 | 自测 GUARD / GUARD-I；V5-TOOLS-EXACT.pyc |
| **SQL-P1-2（三轮）** | **N10 批量化退化为「工作树↔索引」** | D16：`git ls-tree -r HEAD` | 自测 N10.3（改写并暂存） |
| **SQL-P1-3（三轮）** | 与 NEW-P1-1-R 同类（父进程 + `.pyc` + 证据工具子进程） | D15（含证据工具 `-I`） | 同上 |

| P2 | 处置 |
|---|---|
| N9 载荷未锚定 | 已修（D13 + 自测 N9.4） |
| 改名标记即可绕过 N9 | 已修（候选 = 目录名 **或** 标记；自测 N9.5）；「同时改名」「移出 docs/plans」列入 §6.3 |
| `baseline/plan` 下空子目录不可见 | 已修（自测 N13.3） |
| N10 Git 分支无自测 | 已修（N10.2 提交后改写；V5-2.3 增 N10.3 暂存改写） |
| `tools/` 未枚举（含 `.pyc`） | 已修（D15③；自测 V5-TOOLS-EXACT.py/.pyc） |
| `V5-SET-GOVERNING` 恒真 | 已修（断言等于预期三元组且三个文件存在；计数 conjunct 本身恒真，仅作一致性声明——如实标注，不声称它本身是判据） |
| `evidence_tools` 非精确集合 | 已修（N17 断言恰为两项） |
| 畸形 manifest 崩溃而非给编码 | 已修（verify 包裹异常 → `N4`） |
| `plan_freeze_git_head` 未锚定 | 已修（N10 断言为 HEAD 祖先且含语料） |
| `frozen_at` 无法锚定 | 列入 §6.4 |
| N6 归因 | 部分修：capture 无记录时由 N7 报告、manifest 声明但磁盘缺失由 N13 报告（N6 不再误报等价类别）；不再声称覆盖"路径错配"全部场景 |
| N2 子串误报 | 已修（`docs/plans/<name>` 前缀） |
| verify/self-test 耗时 | N10 的 156 次 git 子进程合并为 5 次；self-test 成本如实记录（一次性门禁） |
| `V5_PREFREEZE_CHILD` 死代码 | 已删除（改用 `-I`） |
| **NEW-P2-C（四轮）** `python -m` 绕过守卫 | 已修（D17：要求 `sys.flags.isolated`；自测 GUARD-M） |
| **NEW-P2-D（四轮）** N6 汇总误报 | 已修（仅当声明集等于冻结集时才比较 `equivalence_summary`；路径错配由 N13 报告） |
| **NEW-P2-E（四轮）** §6.9 未提 `-m` | 已修（§6.9 明确三种调用形态与平台前提） |
| **SQL-OBS-3（P3）** `--self-test` 墙钟随变异数增长（11s→50s→55s→89s） | **结构性搁置（2026-09-10 决策）**：优化（"复制一次 + 逐例回滚"）必须修改冻结 checker 或向 `tools/` 增加文件——前者破坏冻结集哈希（N5 red），后者破坏 `V5-TOOLS-EXACT`；在 generation v5 内不可行。属非阻断一次性门禁成本（~90s、零仓库写、全在 %TEMP%）。若未来负例继续增长，在**下一个 generation（v6）** 连同 manifest/schema 一起重设计 |

## 9. V5-3 交接审查整改（2026-09-10，两名非作者独立审查）

两轴结论：**冻结态保真度** `accepted_with_findings`（无 P0/P1；3×P2 + 3×P3，独立复现 51/51 哈希、52/52 blob、三模式输出与零仓库写）、**交接文档与运维状态** `accepted_with_findings`（无 P0；5 条 P1）。审查文件：[v5-freeze-review-handover-state.md](v5-freeze-review-handover-state.md)、[v5-freeze-review-handover-docs.md](v5-freeze-review-handover-docs.md)。

| 编号 | 轴/级别 | 发现 | 处置 |
|---|---|---|---|
| HDD-P1-1 | 文档 P1 | 工作树不干净：本记录 §8 的 SQL-OBS-3 行未提交，故"company-wiki 干净"表述失真 | 本记录与两份审查文件随本次提交入库；R4 `current-delta-2026-09-09.md` 的"干净"标注为**提交时点**事实 |
| HDD-P1-2 | 文档 P1 | README §5 只列 8 条风险，缺 §6.6 / §6.9 | README §5 重写为与 §6 九条**一一对应**，并补成本项 |
| HDD-P1-3 | 文档 P1 | README §5.8 与 progress 仍建议"复制一次 + 逐例回滚"优化，与新判定矛盾（照做会破坏冻结） | 两处改为"结构性搁置"，指向 §8 SQL-OBS-3 行与本节 v6 清单 |
| HDD-P1-4 | 文档 P1 | `task_plan.md` 的 V5-3 三项目标重复出现（已勾 + 未勾各一份） | 删除未勾的重复块，并新增"交接双审"已完成条目 |
| HDD-P1-5 | 文档 P1 | 根 `PLANNING_STATUS.md` 仍留旧 token `V5_BASELINE_READY / VERSION_CONTRACT_PENDING` | 两仓 PLANNING_STATUS 统一为 `V5_3_COMPLETED / PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED` |
| HDS-P2-1 | 状态 P2 | README §2 引用的 PASS 行非字面（引文冒号后无空格）却声称逐字节 | §2 改按实际字节书写，并注明边界文档中的旧渲染边界 |
| HDS-P2-2 | 状态 P2 | §2/B6 把冻结 HEAD 写成 `9418e72`（实为 V5-2.2 提交），与 line 4 及 manifest `89c0862d` 矛盾 | B6 已更正，并加"冻结时点 HEAD vs 产物提交 `4f4dea1`"说明 |
| HDS-P2-3 | 状态 P2 | §2/§3 写"2 项守卫检查"（实为 3；V5-2.4 增 GUARD-M） | 两处改为 3 |
| HDD-P2-* | 文档 P2 | README §7 缺 H01 硬前置；§4 缺审计边界（提权不可见的 hive/受保护任务）与"在库重挂路径" | §7 增 H01 条目；§4 增审计边界声明 + `startup.py::install_startup_task` 重挂路径说明，并扩展扫描面 |
| HDS-P3-1 | 状态 P3 | `v5-freeze-boundary.md`（manifest 绑定字节）含旧数值（27 变异、HEAD `436ecd3`、tracked 74） | **v5 内不可修**（改它即破 `boundary_record` 绑定）→ 列入 v6 待办；读者以 README §2 为准 |
| HDS-P3-2 | 状态 P3 | §8 行"任何新文件"措辞：`tools/__pycache__` 被显式豁免；把 TEMP 指到 RAM 盘可在不动冻结字节的前提下缩短墙钟 | 措辞已在 §8 行内限定为**代码级**优化；RAM 盘属环境手段，不影响判定 |
| HDS-P3-3 | 状态 P3 | SQL closure3 记录变异数 27→31→34，而冻结代码的 AST 计数为 32 | 不影响 §8 行（只引墙钟）；此处如实记录差异 |

**v6 待办清单（仅下一个 generation 可做）**：① 边界文档数值刷新（变异数 / HEAD / tracked 数）；② `--self-test`"复制一次 + 逐例回滚"优化；③ `frozen_at` 的机器可锚定化探索；④ 变异数与墙钟的自动登记。
