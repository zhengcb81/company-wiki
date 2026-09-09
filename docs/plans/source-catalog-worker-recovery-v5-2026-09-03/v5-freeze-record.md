# V5-2 冻结记录（2026-09-09；V5-2.1 复审整改后）

状态：**FROZEN_FOR_INDEPENDENT_REVIEW**（PLAN_ONLY，未实施；本记录不构成实施授权）
冻结时点 HEAD：`454f632c046880980df5ce53bdaccdef88ca762a`（冻结产物随后入库）
本记录本身**不是冻结锚**：它承载"实测值"与偏差说明，可在同一 generation 内更正；锚点是 manifest + 冻结集 + Git 提交。

冻结经历两轮：首次冻结 `454f632`（`--verify-manifest` 8866）→ 三路独立审查（SQL/性能、生命周期/安全、测试/DAG）各返回 `accepted_with_findings`、**无 P0、共 9 条 P1** → 本目录 `917b8d8` 为 **V5-2.1 整改冻结**（`--verify-manifest` 9174 通过、自测 17 例/27 变异全拒）。逐条整改见 §7。

## 1. 冻结产物与哈希（V5-2.1）

| 文件 | sha256 | 字节 | 角色 |
|---|---|---|---|
| `plan_manifest.v5.json` | `afedfdd8806719ae5153dbe2225a76efaa01c519a26ab834e02979b0eecb820e` | 13976 | 冻结 manifest（自排除） |
| `plan_freeze_check.v5.txt` | `8c01b9dc011bda445fd6d055812105ff535205371b8dbf8e66d73a38ecd6197f` | 172 | 预冻结检查 stdout（0 个 CR） |
| `plan_manifest.schema.v5.json` | `4e7ce1e6c983b0f3461ccd7a16c51dfeb0b0be05205d39258032e9b626d36dfd` | 7039 | 治理件（冻结集） |
| `tools/v5_plan_consistency_check.py` | `a40a3d7a5477401252f86d4df2e4cba1863ce81b584a97835a9479fb482e1f44` | 41389 | 治理件（冻结集） |
| `.gitattributes` | 见 manifest 首项 | 172 | 治理件（冻结集） |
| `tools/v5_freeze_manifest_build.py` | `459b7c7dc4ac1c8cb885f5133f3b1d6d240005e0bc0334ff56ddddb3494f5122` | 6420 | 生成器（**不入冻结集**） |
| `tools/v5_version_reference_scan.py` | 见 manifest `evidence_tools` | 10057 | 证据工具（manifest 绑定） |
| `tools/v5_equivalence_check.py` | 见 manifest `evidence_tools` | 3035 | 证据工具（manifest 绑定） |
| `v5-version-reference-inventory.json` | `150ae6a428d64415ebeaf14d9d69ea56b08df6161217b42bce7622a25edccfee` | 30088 | 证据（manifest `evidence` 绑定） |
| `v5-baseline-equivalence.json` | `79ac6ca49ad7a7085cefcceeded65cc9d7fe2ae9f4bfcb26d608f20d867a0c67` | 2970 | 证据（manifest `evidence` 绑定） |
| `import_manifest.v5.json` | 见 manifest `capture_manifest` | 34238 | 捕获记录（manifest 绑定） |
| `v5-freeze-boundary.md` | `f14f8cfcb9b7a8b7cb76670f2b24e264d06db96adf3cea0824b07cccccc5d985` | 5489 | 边界记录 + N9 机器载荷 |

冻结集构成：**51** = 导入计划输入 48（`baseline/plan/**`，递归枚举）＋ v5 自有治理件 3；自排除 1。
等价性（逐件按字节复算，不采信标签）：`v4_exact` 21 / `crlf_only` 17 / `unproven_new_baseline` 10。

## 2. 协议 B1–B6 执行结果

| 步骤 | 结果 |
|---|---|
| B1 冻结前逐文件哈希 | 51 个文件快照（递归枚举；`baseline/plan/` 下无子目录，否则 `V5-SET-NESTED` red） |
| B2 运行全套一致性检查 | 预冻结：`PASS: 7710 checks; {"fixed_nodes":115,"schemas":29,"tests":315,"vectors":18}` |
| B3 冻结后重哈希 | 51/51 哈希与字节数一致；`baseline/plan/__pycache__` 与 `tools/__pycache__` 均不存在 |
| B4 `.gitattributes` 入集且属性全 unset | `git check-attr text eol filter working-tree-encoding` × 51 路径 = 204 行，全部 `unset` |
| B5 旧目录检查 | 机器载荷（§5）声明 `NON_AUTHORITATIVE`、38 文件、inventory `da927ee2…`；任何含计划标记的兄弟目录未申报即 red |
| B6 记录 HEAD / index | 冻结时点 HEAD `454f632`；v5 目录冻结前已跟踪 74 个文件 |

后冻结复验（入库后）：`--verify-manifest` → `PASS: 9174 checks; {"fixed_nodes":115,"schemas":29,"tests":315,"vectors":18}`。
`--self-test` → **17 例 / 27 个变异**，全部在「全检查」与「仅该编码」两种模式下被拒。

> 计数是**运行环境相关的观测值**，不是冻结断言：`--verify-manifest` 的计数取决于 manifest 与 51 个冻结项是否已被 Git 跟踪（未跟踪时 N10 fail-closed 会 red）。**唯一的冻结断言**是 `plan_freeze_check.v5.txt` 的字节与哈希（172 字节、0 CR、`8c01b9dc…`），且 N8 会在真实树上重跑默认模式逐字节比对。

## 3. 负例 N1–N17 自测（`--self-test`）

每条负例在临时副本上施加一个或多个定向变异，并断言对应编码在**全检查**与**仅该编码**两种模式下都被拒（隔离模式排除"别的检查顺手拦住"的假阳性）：

| 编码 | 变异数 | 覆盖的复现配方 |
|---|---|---|
| N1 | 1 | 活动目录出现 `plan_manifest.v4.json` |
| N2 | 1 | manifest 指向已退役旧目录 |
| N3 | 1 | `freeze_generation` 改为 v6 |
| N4 | 1 | 未知字段 |
| N5 | 1 | 条目哈希改零 |
| N6 | 2 | **计数守恒的标签互换**；单件标签改动 |
| N7 | 3 | 改字节；**改字节 + 同步全部可写记录**（由 v4 冻结 manifest 锚定）；改名 |
| N8 | 3 | 伪造计数；**计数正确且哈希自洽**（由真实重跑暴露）；命令藏在注释后 |
| N9 | 3 | 未申报的兄弟副本；处置翻转为 AUTHORITATIVE；处置文件缺失 |
| N10 | 1 | manifest 自身进入 normative 集 |
| N11 | 2 | 取代链指向旧目录；西里尔字母形近路径 |
| N12 | 1 | investigation_source 指向旧目录 |
| N13 | 2 | 删条目；`baseline/plan/nested/` 嵌套文件 |
| N14 | 1 | `.gitattributes` 移出冻结集 |
| N15 | 1 | capture manifest 的 generation 改为 v6 |
| N16 | 1 | 治理件标签改为 `v4_exact` |
| N17 | 2 | 证据工具哈希改零；证据输出哈希改零 |

## 4. 与合同/既有语料的偏差与决策

| 编号 | 偏差 | 理由与影响 |
|---|---|---|
| D1 | 历史哈希钉按布局解析 | 基线 `IMMUTABLE_HISTORY_SHA256` 期望 `plan_manifest.v3.json` 位于 checker 的 `ROOT`；v5 导入把它放在 `baseline/history/`。checker 用同一期望哈希做布局感知解析（实测 `9ee84acd…` 等于钉值）。不改导入字节、不改冻结集。 |
| D2 | 禁止字节码写入 | 用 `importlib` 加载基线 checker 会在冻结目录内生成 `baseline/plan/__pycache__/*.pyc`。checker 置 `sys.dont_write_bytecode = True`，B3 断言 `baseline/plan/__pycache__` 与 `tools/__pycache__` 均不存在；证据工具永久排除 `__pycache__`。 |
| D3 | 预冻结输出强制 LF | Windows 文本模式 stdout 产出 CRLF。checker 统一 `reconfigure(encoding="utf-8", newline="\n")`；生成器在捕获含 CR 时中止。现产物 172 字节、0 个 CR。 |
| D4 | 证据范围收紧 | v5-1 证据范围含 v5 根目录活动文档（合同 §88 明确它们「活动，可更新」），冲突会使每次状态更新都让冻结证据失效。现范围 = `baseline/**`（54）＋ v5 根冻结输入（`.gitattributes`、`plan_manifest.schema.v5.json`）＝ **56**；排除活动文档、`v5-freeze-*` 记录与审查、两个冻结产物、`reviews/`、`tools/`、`import_manifest.v5.json`、`verify_import.py`、`__pycache__`。代价：活动文档中的旧目录引用（合同 §3 的 11→8）不受机器检查覆盖，已列入 §6 残余风险。 |
| D5 | 生成器不入冻结集 | `tools/v5_freeze_manifest_build.py` 有写权限，不进入 48+3=51；manifest 的判定由 `--verify-manifest` 与 `--self-test` 承担。 |
| D6 | schema 路径正则放宽首位 `.` | `.gitattributes` 以点开头；改为 `^[A-Za-z0-9._]…`。只放宽合法路径集合。 |
| D7 | 合同计数行更新 | 合同 §3 的计数改为冻结时点实测值（41/11/8/9/30、`:v5`=3），并指向冻结证据 `totals`。 |
| D8 | 证据产物纳入 manifest 绑定（新增 `evidence` 字段） | 复审 TST-P1-2 指出证据输出未绑定、可被重新生成后与 manifest 自相矛盾。现 manifest 新增 `evidence`（两份证据的 path/sha256/size），N17 逐件比对。 |
| D9 | N9 载荷化（新增机器可读处置块） | 复审 LIF-P1-1 指出"文件存在即通过"不足。现 `v5-freeze-boundary.md` 携带 `disposition`/`retired_dirs` JSON 块，N9 复算 file_count 与 inventory 摘要，并要求任何含计划标记的兄弟目录都被申报。 |
| D10 | import 式加载的写入边界 | 以脚本执行零写入；以 import 加载本模块时，CPython 可能在模块体执行前为其自身写 `tools/__pycache__`。已在模块 docstring 声明，且该目录被 B3 断言与证据范围排除。 |
| D11 | N8 的重跑比对依赖真实 Git 树 | `N8` 的"重跑默认模式逐字节比对"在 `external=True`（真实树）时生效；自测用 N8.1（计数不符）、N8.2（临时 Git 仓库上的自洽伪造）、N8.3（注释藏命令）三个变异证明该编码有效。 |

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
2. 旧目录是**独立第三份副本**（38 文件，干净）。V5-2.1 把它变成"申报 + 摘要复算 + 禁止并列权威"，但仍未删除、未加锁；有写权限者仍可改动它（改动会被 N9 摘要比对发现）。
3. `plan_manifest.v5.json` 与 51 个冻结项的不可变性依赖 Git（N10 对 52 个对象做 `hash-object` vs `HEAD:blob`，未跟踪即 red）；**提交后**的静默改写会被发现，但一次新的提交本身不会被 N10 拦截（提交历史是唯一的最终账本）。
4. 证据可复现性依赖"冻结后不变的扫描范围"；若修改 `baseline/**` 或两个冻结输入，`--check` 会失败——这是设计意图。
5. 活动文档（`README.md`/`task_plan.md`/`findings.md`/`progress.md`）中的旧目录引用不受证据或机器检查覆盖（D4 的代价）。
6. 本记录、三份审查记录与边界记录本身不在冻结集与证据范围内（避免自指），其完整性由 Git 与独立审查背书。
7. `.githooks/pre-commit` 仍会整仓 checkout + patch 恢复（v4 漂移事故的机制）。冻结窗口内 51 项零变化已实测，但该机制仍是并发写风险；审查期间已出现并发写入（活动文档），因此"稳定审查边界"在时间上依赖该窗口。
8. `reviews/old-plan-retirement-inventory.json` 含绝对个人路径（用户名 + 盘符）。该文件是历史记录，合同 §88 规定 `reviews/` 不改字节，故**按设计保留**；其中不含任何凭据。

## 7. V5-2.1 复审整改（9 条 P1 逐条关闭）

| P1 | 来源 | 根因 | 整改 | 验证 |
|---|---|---|---|---|
| SQL-P1-1 / TST-P1-1 | SQL/性能、测试/DAG | N6 只核对标签计数，从不复算等价类别，计数守恒的标签互换可通过 | N6 对每个导入件用字节 + `historical_v4_sha256` 复算类别，并与 `v5-baseline-equivalence.json` 的 `groups` 逐件交叉核对 | 自测 N6.1 计数守恒互换被拒（全检查 + 隔离） |
| TST-P1-2 | 测试/DAG | 导入字节只锚在可写的 capture 记录上，全协同改写可通过 | N7 增补 **v4 冻结 manifest** 锚（`v4_exact` 字节相等 / `crlf_only` LF 归一化相等 / `unproven` 必须与 v4 不等）；新增 `evidence` 字段把两份证据输出纳入 manifest 绑定；N10 对 51 项 + manifest 做 Git blob 比对 | 自测 N7.2（改字节 + 同步全部可写记录）被拒；N17.2 证据哈希改零被拒 |
| TST-P1-3 | 测试/DAG | N8 不把预冻结产物绑定到本 checker 的真实运行 | N8 解析产物内嵌计数并与复算比对；在真实树上重跑默认模式并**逐字节**比对；命令改为 schema `const` | 自测 N8.1/N8.2/N8.3 全拒（N8.2 在临时 Git 仓库上验证重跑分支） |
| TST-P1-4 / SQL-P3-1 | 测试/DAG、SQL/性能 | command 只做子串匹配，注释可藏第二个脚本 | command 必须是 schema `const` 的精确串；另解析唯一 `.py` token 并归一化比对；`#` 一律拒绝 | 自测 N8.3 被拒 |
| TST-P1-5 | 测试/DAG | `baseline/plan/*` 非递归枚举，子目录内容不可见 | `frozen_entries` 改递归；新增 `V5-SET-NESTED`（默认模式）与 N13 的嵌套检查 | 自测 N13.2 被拒 |
| TST-P1-6 | 测试/DAG | N11 用后缀匹配 + 静默回退，可指向旧目录或形近路径 | `supersedes` 改为 schema `enum` + 恰好两条；N11 要求路径是规范 ASCII 相对路径、不含旧目录名、无回退 | 自测 N11.1/N11.2 被拒 |
| LIF-P1-1 | 生命周期/安全 | N9 只判"路径存在 + 文件存在"，改名即静默失效，处置内容不可验 | N9 改为：枚举 `docs/plans/` 下所有含计划标记的目录 → 必须被机器可读处置块申报 → 复算 file_count 与 inventory 摘要 → 禁止冻结项落入其中 | 自测 N9.1/N9.2/N9.3 被拒 |
| LIF-P1-2 | 生命周期/安全 | v4 的 `MANIFEST-PATH-SAFETY`（resolve 在计划目录内、无 symlink/reparse）在 v5 被整体丢弃 | 新增 `V5-PATH-SAFETY`：51 项逐项 resolve 包含关系 + 逐段 reparse 检查 | 默认模式新增 102 项检查；junction 重定向会使该项 red |

## 8. P2 处置

| P2 | 处置 |
|---|---|
| SQL-P2-1 / LIF-P2-1（8866 vs 8867 计数） | 已在 §2 明确：计数是运行环境观测值，唯一冻结断言是产物字节；本记录与提交信息中的 8866 属首轮冻结（`454f632`），V5-2.1 为 9174 |
| SQL-P2-2 / D10（import 写 pycache） | 模块 docstring + D10 声明；B3 断言两个 `__pycache__` 均不存在 |
| SQL-P2-3（审查窗口内记录被改写） | 本记录头部声明"不是冻结锚"；V5-2.1 的冻结产物与记录同一次提交入库 |
| SQL-P3-2（子进程缺超时） | 所有 git 子进程已加 `timeout`（60/120s） |
| SQL-P3-3 / LIF-P1-1（旧目录缺失即静默） | N9 改为申报式枚举，缺失/新增/改名都会 red 或要求申报 |
| LIF-P2-2（N10 未跟踪时静默跳过） | 改为 fail-closed：未跟踪即 red |
| LIF-P2-3（合同计数未同步） | 合同 §3 已按冻结证据更新 |
| LIF-P2-4（活动文档引用不受覆盖） | 列入 §6 残余风险 5 |
| LIF-P2-5（绝对个人路径） | 按设计保留（合同 §88：`reviews/` 不改字节），列入 §6 残余风险 8 |
| LIF-P2-6（pre-commit hook 机制） | 列入 §6 残余风险 7 |
| LIF-P2-7（旧证据哈希时点） | 证据由 manifest `evidence` 绑定；历史引用以提交号标注 |
