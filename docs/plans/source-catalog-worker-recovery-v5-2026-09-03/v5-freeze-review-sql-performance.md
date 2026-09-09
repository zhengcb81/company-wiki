# V5-2 冻结：独立审查（SQL/性能轴 —— 数据完整性 + 验证机制成本）

日期：2026-09-09。审查者：**independent reviewer（SQL/性能轴：data-integrity + performance）**，非作者，未参与本计划任何写作或生成。
范围：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03/`（HEAD `454f632`，分支 `fcap`）的 48 份导入基线 + 3 份 v5 治理件 + `plan_manifest.v5.json` / `import_manifest.v5.json` / `v5-freeze-record.md` / `v5-freeze-boundary.md` / 4 个工具。
方法：**全部独立重算**，不引用任何文档中的"实测值"；作者声明一律当作待验证命题。只读复算脚本置于 `%TEMP%\v5sqlreview\`（仓库外），本文件是唯一写入仓库的文件。未 `git add/commit/push`，未触碰 worker/数据库/任务/其他仓库。

结论：**accepted_with_findings**

> 数据完整性本身**通过**：48/48 等价性分类与我的独立复算逐件一致（21 `v4_exact` / 17 `crlf_only` / 10 `unproven_new_baseline`），51/51 冻结项哈希与字节数一致，17 份 `crlf_only` 逐件证明"仅 EOL 变化、无任何非 EOL 字节改动"，SQL/DB 相关语料（operation_contracts / gate_dag / gate_ledger* / test_id_registry / vectors）全部被实际运行的 schema/DAG/registry/vector 检查组覆盖且全部通过。**无 P0**。阻断级问题是 1 条 P1：**N6 并未按合同 §7 复算等价类别**，计数守恒的标签互换会被接受——这正是 v4 事故（语义改动伪装成 EOL 漂移）所要拦截的类别。另有 3 条 P2、3 条 P3，均不改变已冻结字节。

---

## 1. 任务 1-3 的独立复算结果（摘要）

| 项 | 我的独立结果 | 与 manifest / 证据文件是否一致 |
|---|---|---|
| 48 份导入文件等价性 | `v4_exact` 21 / `crlf_only` 17 / `unproven_new_baseline` 10（`unresolved` 0） | **一致**，48/48 逐件标签相同（附录 A） |
| `equivalence_summary` | `{21,17,10}` | 一致（manifest + `v5-baseline-equivalence.json` + 我的复算三者相同） |
| 磁盘集合 vs manifest 集合 | 48 = 48，无缺失、无多余 | 一致 |
| `historical_v4_sha256` vs v4 冻结 manifest | 48/48 相同（`baseline/history/plan_manifest.v4.json`） | 一致 |
| 51 冻结项哈希/字节数 | 51/51 一致（`final_verify.json`，2026-09-09T20:54:54Z） | 一致 |
| 17 份 `crlf_only` 的 EOL-only 证明 | 17/17 成立（附录 B） | 一致 |
| SQL/DB 语料 | 全部被 schema/DAG/registry/vector 组覆盖并通过（附录 C） | 一致 |

**方法要点（可复现）**：对每份文件取当前字节 `C`、`N = C.replace(b"\r\n", b"\n")`，以 `import_manifest.v5.json` 的 `historical_v4_sha256` 为锚：`sha256(C)==hist → v4_exact`；否则 `sha256(N)==hist → crlf_only`；否则 `unproven_new_baseline`。**额外**以 `baseline/history/plan_manifest.v4.json` 的 `sha256`+`size_bytes` 做第二锚（`len(N)==v4_size`），这是作者工具没有做的交叉验证。

```powershell
# 仓库根目录，只读
python %TEMP%\v5sqlreview\recompute_equivalence.py %TEMP%\v5sqlreview\recompute.json
# 观察输出：
# {"v4_exact": 21, "crlf_only": 17, "unproven_new_baseline": 10, "unproven_no_hist": 0}
# {"v4_exact": 21, "crlf_only": 17, "unproven_new_baseline": 10}
# {"crlf_only": 17, "unproven_new_baseline": 10, "unresolved": 0, "v4_exact": 21}
# disagreements: []
```

---

## 2. Findings

| ID | 严重度 | 问题 | 证据（精确命令 + 实测输出） | 必须的修复 |
|---|---|---|---|---|
| **SQL-P1-1** | **P1** | **N6 没有"复算"等价类别，只做了标签计数核对**：`verify_manifest()` 从不读取 `historical_v4_sha256`（全文件无该标识符），`counted[]` 只统计 manifest 自己的标签，再与 `equivalence_summary` 比。因此**计数守恒的标签互换被接受**：把一份真实 `unproven_new_baseline`（字节不可由 v4 哈希经 EOL 归一化得到）标成 `crlf_only`，同时把一份真实 `crlf_only` 标成 `unproven_new_baseline`，21/17/10 不变、N4/N5/N6/N13 全部通过。这正是合同 §7 N6「`equivalence` 类别与复算不符 → 拒绝」要拦截的类别（v4 事故同型：语义改动伪装成 EOL 漂移）。 | `python %TEMP%\v5sqlreview\n6_probe.py`（在 `%TEMP%` 副本上改 manifest，调用真 checker 的 `verify_manifest`）：<br>`{"case": "N6-swap-crlf_only<->unproven_new_baseline", "mutation": "swapped labels: baseline/plan/acceptance_thresholds.md <-> baseline/plan/authorization_manifest.schema.json (crlf_only <-> unproven_new_baseline)", "checks": 1156, "codes": [], "rejected": false}`<br>`{"case": "N6-swap-v4_exact<->crlf_only", ... "codes": [], "rejected": false}`<br>对照：单件改标签（计数变化）→ `"codes": ["N6"], "rejected": true`；无改动对照 → `"codes": [], "checks": 1156`。 | 在 `verify_manifest()` 内对每个 `equivalence ∈ {v4_exact,crlf_only,unproven_new_baseline}` 的条目**从字节复算**：用 `captured[rel]["historical_v4_sha256"]`，`sha(raw)==hist → v4_exact`；`sha(raw.replace(b"\r\n",b"\n"))==hist → crlf_only`；否则 `unproven_new_baseline`；与声明标签不符即 `base.check(False, "N6", ...)`。并让 `--self-test` 的 N6 用例改成上述**计数守恒互换**（当前用例只改一个标签，无法暴露该空档）。 |
| **SQL-P2-1** | P2 | **冻结记录中的"实测"检查计数不可复现，且本质上是环境状态函数**：`v5-freeze-record.md` §2 写「后冻结复验：`--verify-manifest` → PASS: 8866 checks」，我在同一目录实测为 **8867**；差异来自 N10 的 Git 分支（`checker:316-324`：仅当 `git ls-files --error-unmatch` 返回 0 时才多出 1 个 `base.check`），即 manifest 入库后被跟踪 → +1。另外默认模式的 7658 也依赖旧目录存在：`v5_checks` 在旧目录存在时贡献 164 项、不存在时仅 112 项（N9 的两组检查消失）→ 默认模式将变为 7606。作者本人在审查窗口内追加了一行承认 8867（该行未提交）。 | `python docs\plans\source-catalog-worker-recovery-v5-2026-09-03\tools\v5_plan_consistency_check.py --verify-manifest` → `PASS: 8867 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}`；<br>`v5-freeze-record.md:36`（HEAD 版本）→ `PASS: 8866 checks`；<br>`python %TEMP%\v5sqlreview\count_dependence.py` → `{"label": "real (retired dir present)", "v5_checks_only": 164}` / `{"label": "simulated (retired dir absent)", "v5_checks_only": 112}`。<br>逐项计数自洽：7494（基线全套，含 1 项 history 锚）+ 164（v5_checks）= 7658；8867 − 7658 = 1209 = 第二次 `dag_checks()` 982 + N1–N17 的 227。 | 冻结记录改为只声明**可复现的产物绑定**（`plan_freeze_check.v5.txt` = 172 字节、sha256 `88f407ae…`、0 个 CR——我已逐字节复现），并显式写明「live 检查计数依赖旧目录存在性与 manifest 的 Git 跟踪态」；或让 N9/N10 的分支变为**无条件检查**（例如旧目录缺失时也记 1 项「absent」断言），使计数成为不变量。 |
| **SQL-P2-2** | P2 | **checker 并非无条件"不写盘"**：以脚本方式运行确实零写入（实测 0 次写打开、0 次 FS 变更），但**以 import 方式加载会写入计划目录** `tools/__pycache__/v5_plan_consistency_check.cpython-313.pyc`——模块体里的 `sys.dont_write_bytecode = True`（`checker:36`）在自身 `.pyc` 落盘之后才执行，无法自保。模块 docstring 第 16 行「Read-only: performs no writes」因此只在脚本执行路径成立。任何未来的 import 式验证/单测框架都会污染计划目录（并使 B6 记录的 `git status` 变脏；B3 只断言 `baseline/plan/__pycache__`，未覆盖 `tools/__pycache__`）。 | 在 `%TEMP%` 副本上做无 `dont_write_bytecode` 前置的 import：<br>`python -c "...importlib...exec_module(mod)"` → `dont_write_bytecode after import = True`，`pycache created in copy by importing the checker: ['tools\\__pycache__\\v5_plan_consistency_check.cpython-313.pyc']`。<br>对照（脚本运行）：`python %TEMP%\v5sqlreview\audit_io.py default` → `write_mode_open_count = 0`、`fs_mutation_count = 0`；全目录快照前后 diff 为 `{"added": [], "removed": [], "changed_paths": []}`。 | 在 docstring 与 `v5-freeze-record.md` D2 中写明「**只保证以脚本方式执行时零写入；import 式调用方必须自行先置 `sys.dont_write_bytecode = True`**」；并把 B3 断言扩展为 `tools/__pycache__` 与 `baseline/plan/__pycache__` 均不存在。 |
| **SQL-P2-3** | P2 | **冻结记录/活动文档在独立审查窗口内被并发修改，其"实测值"未与任何提交绑定**：会话开始时 `git status` 为空；审查过程中 `v5-freeze-record.md`（+1 行）、`task_plan.md`（11+/5−）被改写，并新增两份未跟踪审查文件。冻结记录是承载 D1–D7 与全部"实测哈希"的文件，却不在冻结集内、且其内容可在审查期间变化——即**审查对象在移动**。51 项冻结条目本身未受影响（我在 20:54:54Z 复核全部一致）。 | 会话开始：`git status --porcelain` → 空；`git rev-parse HEAD` → `454f632c046880980df5ce53bdaccdef88ca762a`。<br>审查中：`git status --porcelain` → `M task_plan.md` / `M v5-freeze-record.md` / `?? v5-freeze-review-lifecycle-security.md`（随后又出现 `?? v5-freeze-review-test-dag.md`）；`Get-Item v5-freeze-record.md` → `LastWriteTime 2026/9/9 21:48:02, Length 8373`（HEAD 版本为 8151 字节）。<br>`python %TEMP%\v5sqlreview\final_verify.py` → `frozen_mismatches: []`、`pins` 三项全 true、`label_mismatches: []`。 | 把记录中的"实测值"（尤其 §1 哈希表与 §2 计数）随冻结产物**同一次提交**入库，或在审查开始前把记录也提交并冻结；此后对记录的更正以**追加新文件/新 generation** 表达，而不是原地改写。至少应在记录头部标注"本文件在冻结后仍可被更正，其数值不构成冻结锚"。 |
| **SQL-P3-1** | P3 | N8 只做**子串**匹配：`"v5_plan_consistency_check.py" in command`。合同 §5.2 规定「v5 checker 入口的路径**必须等于** `pre_freeze_check.command` 中调用的脚本路径」，该等值规则未实现——指向任意同名的另一份脚本仍可通过。 | `python %TEMP%\v5sqlreview\n6_probe.py` → `{"case": "N8-command-points-elsewhere", "mutation": "pre_freeze_check.command points at another copy of the checker", "codes": [], "rejected": false}`。 | 解析 command 的最后一个路径参数并与 `ctx.governing` 中的 checker 相对路径做**规范化相等**比较（大小写、正反斜杠归一后），不等即 N8 拒绝。 |
| **SQL-P3-2** | P3 | 成本可接受但结构上是 `O(负例数 × 语料规模)`，且子进程缺超时：`--self-test` 每个负例复制一次 `baseline/`+`tools/`（1,312,499 B × 17 = 22,312,483 B 写入临时目录），实测 11.4–12.1 s；`verify_manifest` 内的 `subprocess.run([sys.executable, tool, "--check"], timeout=600)` 有超时，但 3 条 `git …`（`check-attr`/`rev-parse`/`ls-files`/`hash-object`，共 4 条）**没有超时**，git 挂起会让检查无限阻塞。所有循环均为有界集合上的有限遍历（唯一 `while` 是 `dag_checks` 的 Kahn 拓扑排序，`checker:467`），未发现二次复杂度或不受限循环。 | 三轮计时（`python %TEMP%\v5sqlreview\run_modes.py plan_runs.json runs.json`）：default 2.58/2.71/2.94 s、`--verify-manifest` 2.49/2.93/3.00 s、`--self-test` 11.40/12.06 s；峰值 RSS（`peak_ws.py`，psutil 采样）default 32.1 MB、verify 32.2 MB、self 31.7 MB。<br>I/O（`audit_io.py`，audit hook 统计）：default 263 次读打开 / 5.31 MB / 148 个文件；verify 334 / 6.69 MB / 155；self 1,288 / 26.47 MB / 169 + 124 次写打开。单文件峰值读 162,784 B（`typing_extensions` 的 `.pyc`）；语料单文件最大 `test_id_registry.v4.json` 123,062 B（每次运行被读 3 次）。 | 给 4 条 git 调用加 `timeout`（如 60 s）并在超时时以稳定编码失败；self-test 若将来语料或负例增多，改为"复制一次 + 逐例回滚"或只复制被引用文件，避免 22 MB 级重复写。 |
| **SQL-P3-3** | P3 | N9 的两组检查（`N9-DISPOSITION`、51 项 `N9-PARALLEL`）**仅在旧目录存在时执行**；旧目录一旦被删除，52 项检查静默消失且没有任何"旧目录不存在"的断言记录，与边界记录 B5「校验旧目录存在性并记录其状态」不完全对应。 | `python %TEMP%\v5sqlreview\count_dependence.py` → 旧目录存在 `v5_checks_only = 164`，指向不存在路径时 `112`（差 52 = 1 + 51）。 | 旧目录缺失时也记录一项显式检查（例如 `N9-RETIRED-ABSENT: 记录已退役目录不存在`），使状态可观测且计数稳定。 |

---

## 3. 成本/性能实测（任务 4）

| 模式 | 墙钟（3 次） | 峰值 RSS | 读打开 / 读字节 / 文件数 | 写打开 | FS 变更 | 子进程 | 网络 / SQLite |
|---|---|---|---|---|---|---|---|
| default | 2.58 / 2.71 / 2.94 s | 32.1 MB | 263 / 5.31 MB / 148 | **0** | **0** | 3（`git check-attr` ×1、两个证据工具 `--check`） | 0 / 0 |
| `--verify-manifest` | 2.49 / 2.93 / 3.00 s | 32.2 MB | 334 / 6.69 MB / 155 | **0** | **0** | 7（+`git rev-parse --show-toplevel`、`git ls-files --error-unmatch`、`git rev-parse HEAD:<manifest>`、`git hash-object`） | 0 / 0 |
| `--self-test` | 11.40 / 12.06 s | 31.7 MB | 1,288 / 26.47 MB / 169 | 124（**全部在 `%TEMP%`**） | 1,486（**全部在 `%TEMP%`**，`outside_temp = 0`） | 0（`external=False`） | 0 / 0 |

- **`--self-test` 是否可接受**：是。17 次临时树复制共写 22.3 MB、12 s、零仓库写入，对一次冻结级验证完全可接受（`--verify-manifest` 仅 3 s）。成本随负例数与语料规模线性增长，目前无二次/不受限行为。
- **零生产访问**：静态上，v5 checker 只 import `hashlib/importlib/json/re/shutil/subprocess/sys/tempfile/dataclasses/pathlib` + `jsonschema`；无 `sqlite3`、`socket`、`urllib`、`http`、`winreg`、`psutil`、`os.system`。基线的 `baseline/plan/plan_consistency_check.py` 同样无 `open(...,"w")`/`write_*`/`sqlite3`/`socket`/`subprocess`。经验上，audit hook 在三种模式下记录到的 `network_events = []`、`sqlite_events = []`，子进程仅 3/7 条且全部为只读 git 查询与自有证据工具。
- **"no process" 的精确表述**：checker 确实**启动子进程**（3/7 条），因此 docstring 的「starts no process」只在"不启动生产进程"意义上成立；建议措辞改为「不启动生产进程，仅调用只读 git 与自身证据工具」。

## 4. 变更安全（任务 5）

- **静态**：checker 中所有写 API（`write_text`/`write_bytes`/`unlink`/`mkdir`/`shutil.copytree`/`shutil.rmtree`）只出现在 `_n1`–`_n17` 与 `self_test()` 内；`self_test()` 总是用 `tempfile.TemporaryDirectory()` 构造 `Ctx`，`_n9` 的 `ctx.old_dir` 也在该临时目录下。REAL 模式路径（`main → baseline_suite → v5_checks → verify_manifest`）无任何写调用。
- **`sys.dont_write_bytecode`**：在 `load_baseline()`（`checker:528`）之前于模块级设置（`checker:36`），因此加载基线模块不会产生 `baseline/plan/__pycache__`——实测三次运行后 `pycache_in_plan_dir: []`。（唯一例外见 SQL-P2-2：import checker 自身会写 `tools/__pycache__`。）
- **经验快照**：每轮运行前后对计划目录全部 81→83 个文件做 `sha256 + size + mtime_ns` 快照；三种模式共 8 次运行，`plan_dir_added/removed/changed` **全为空**。audit hook 亦确认 `write_mode_open_count_outside_temp = 0`、`fs_mutation_count_outside_temp = 0`。
- **Git 层面**：`git hash-object` 与 `git rev-parse HEAD:<manifest>` 均为 `0150f4eaf078928eb3dcbd448f9a2129447a1c17`（N10 分支激活且成立）；`.gitattributes` 内容为 `* -text -eol -filter -working-tree-encoding`，对 51 个冻结路径 `git check-attr text eol filter working-tree-encoding` 共 **204 行、全部 `unset`**（独立复现）。

## 5. 声明与残留

- 本审查只读、非作者；唯一写入仓库的文件即本文件。未提交、未推送、未运行旧 checker/worker、未触碰数据库/计划任务/其他仓库。PLAN_ONLY 上下文未授权任何实施，本审查也不构成实施授权。
- 复算脚本全部位于 `%TEMP%\v5sqlreview\`（仓库外，临时）：`recompute_equivalence.py`、`eol_proof.py`、`olddir_probe.py`、`claims.py`、`final_verify.py`、`group_activity.py`、`n6_probe.py`、`audit_io.py`、`count_dependence.py`、`run_modes.py`、`peak_ws.py`、`snapshot.py`。
- 残留（不隐瞒）：① 我无法独立取得大多数文件的 v4 冻结**字节**（旧目录 38 份与 v4 哈希 0/38 相同；git 历史仅能解析 3/48 个 v4 目标），故 EOL-only 证明依赖"`sha256(LF 归一化字节)==v4 冻结哈希` 且 `len(LF 归一化)==v4 冻结字节数`"这一抗碰撞论证，而非逐字节 diff；② 冻结只覆盖规划文档完整性，不覆盖 worker/配置/数据库/任务；③ 旧目录仍是可复活的第三份副本（38 份、已跟踪、clean、mtime `2026-09-07T18:08:52.8971277Z`），本冻结未删除、未加锁。

---

## 附录 A：48 份导入文件等价性逐件复算（哈希来自我独立计算）

| # | 文件 | 字节 | sha256(当前字节) | historical_v4_sha256 | 复算类别 | manifest 标签 | 一致 |
|---|---|---|---|---|---|---|---|
| 1 | README.md | 18875 | 200e618179a360bc558b8c0e50140cca2b4858a846b3172d9fb0bcb229567e7e | e39d86bbe87bf5243c7097ab243133d6e6b864d54c168680f98af3aabe920c3a | unproven_new_baseline | unproven_new_baseline | ✅ |
| 2 | acceptance_thresholds.md | 23396 | d6f3068498c8c6d8064c0babae809afbb320916da240567805f9a4cab20c96af | d8feb22e26378924a611e5aa6cdecf3b54270671ede0a5c4b6ecaf15aaf871db | crlf_only | crlf_only | ✅ |
| 3 | agent_review_gates.md | 33410 | bbab56f39b7a9392295bca855f65ad99c5f7372dc54f4d4039adf909a3641a26 | 51923c8576f4c5441353af12e40d29abe5fb7a804087316bc4cf5a8827a77da6 | crlf_only | crlf_only | ✅ |
| 4 | authorization_manifest.schema.json | 43788 | 4c9458d6e3da59d2ed3e588051ed4f393183e3ccc25606a150567b310e28d446 | 7bc50fb71eb4ee4840286fb33aac9707289f6279b8ac65a5dc38ffbe1cf81bb7 | unproven_new_baseline | unproven_new_baseline | ✅ |
| 5 | authorization_revalidation_receipt.schema.json | 4522 | 26b56990b29cddd1284ad444e4838feaa4b64c547145ed1c4461780a2a3e14c8 | 26b56990b29cddd1284ad444e4838feaa4b64c547145ed1c4461780a2a3e14c8 | v4_exact | v4_exact | ✅ |
| 6 | bootstrap_verifier_manifest.schema.json | 5553 | 768eab57571e310811a3897f2f7d9b4b554972953e2e24397a5bb03846c11ce7 | 768eab57571e310811a3897f2f7d9b4b554972953e2e24397a5bb03846c11ce7 | v4_exact | v4_exact | ✅ |
| 7 | budget_reservation_bundle.schema.json | 7399 | 44f39cb504a6e5c73959c66555c9ca5ad383cf7a93c80b6644d460cb7cb243df | 44f39cb504a6e5c73959c66555c9ca5ad383cf7a93c80b6644d460cb7cb243df | v4_exact | v4_exact | ✅ |
| 8 | budget_settlement_receipt.schema.json | 5999 | 6c9ee6aebc4111a1873a4f7a1f237f909637b654c7bd758b21862b32675723b2 | 6c9ee6aebc4111a1873a4f7a1f237f909637b654c7bd758b21862b32675723b2 | v4_exact | v4_exact | ✅ |
| 9 | evidence_manifest.schema.json | 36739 | 561a0c289751e5f1e0cda4f203c3393dc4a175051c439c03f983b79b180bfd3a | a60bfe37fd1ddee6ee4cac4a2f14d68c6ca397909a9bed42e7033d1452209a33 | unproven_new_baseline | unproven_new_baseline | ✅ |
| 10 | execution_playbook.md | 68362 | 14bfca6216acc8f4de49ec59b58e11906f40dd9d416e9da15493322e8696ecba | 77503ad91939595d7dc01594b1c26e11c82f96626ec32ede8a5d52451fa1cc32 | crlf_only | crlf_only | ✅ |
| 11 | findings.md | 59304 | e246b222fac6da7682f6af680029eb8d5dc9e36a05714eae15ea5f6074e090f1 | 4bd0b89fb25a786e8297162a450ee33ebf7be8861b691c0d8284bc603dba5505 | unproven_new_baseline | unproven_new_baseline | ✅ |
| 12 | gate_dag.schema.json | 10146 | b8fd02ae712f3e1c509c230e2a0c30e222985fddd11327e7187397cce3d88188 | b8fd02ae712f3e1c509c230e2a0c30e222985fddd11327e7187397cce3d88188 | v4_exact | v4_exact | ✅ |
| 13 | gate_dag.v4.json | 22771 | c06b20d040eb8c7adcb4186986c6e0ddffb83b1d122e9773ea415d9bf038dee1 | 3183cd016ed4bdd8ad7883afdd65f1991471e2f46f57654ec49c495a26542992 | crlf_only | crlf_only | ✅ |
| 14 | gate_ledger.schema.json | 24511 | f9f14cc3f73bd34b4cd56a17454be80b40b1ea83ae0bedf450e2723106588b55 | 7cfc8abd3ad7fc32d6d0fd2bf952bb76a3d10008ba1910f9ff023816c25037af | crlf_only | crlf_only | ✅ |
| 15 | gate_ledger_transcript.schema.json | 1673 | d32e15b03b53aef53549c825f4f19c1cdf13c876481b16c79effc75a0b5d173e | d32e15b03b53aef53549c825f4f19c1cdf13c876481b16c79effc75a0b5d173e | v4_exact | v4_exact | ✅ |
| 16 | gate_ledger_validator_vectors.schema.json | 11487 | d1395630ad9419692ba37be3b40ff4e55701560c6c4dbf1557a1f71063b2ed10 | 7a0891291345bda03ccf6850326935faf7566e30960f3e8e33a463fd9e2ffc77 | crlf_only | crlf_only | ✅ |
| 17 | gate_ledger_validator_vectors.v4.json | 59567 | 7e2472d76ae93e9338d5c5b8ec02ec5f44806b9da3e159ccc4cebb46cee1fcef | b932f9c879b1254be973cdffe615c0689a94315191b8257b8067179d17e8dfc4 | crlf_only | crlf_only | ✅ |
| 18 | gate_state_machine.md | 28269 | 49940700b4ee117211bbafef50b8d0c55c2f1045a324a29f06bfce2fea3b3c47 | 860c3472ab35708fe0caef1b4a0af17752bab0e24b18c23317e6ce6ce4285700 | crlf_only | crlf_only | ✅ |
| 19 | implementation_agent_prompts.md | 20526 | ab5c2fbc28996f5d501fff39e2a314030886857b5f246db58293df283f00c73d | 8b805ec7a1799ac7cc988e521a2b98b516b1f3f18086359f65414463f875e92a | crlf_only | crlf_only | ✅ |
| 20 | journal_manifest.schema.json | 7197 | 0b1d690c3ab88090554a270d79c31233f01bb3ccf6b059a10d2def9210e8777f | 0b1d690c3ab88090554a270d79c31233f01bb3ccf6b059a10d2def9210e8777f | v4_exact | v4_exact | ✅ |
| 21 | journal_record.schema.json | 6539 | 6b18298ddabae66d7c55c76c1a55618def5155e9f250525fb063dd3b5bfc4a60 | 6b18298ddabae66d7c55c76c1a55618def5155e9f250525fb063dd3b5bfc4a60 | v4_exact | v4_exact | ✅ |
| 22 | ledger_head_anchor.schema.json | 3364 | 247fa1cdf7d5e412654039359e0d50e6e1cb952fa541dd3b997272563ab34cff | 247fa1cdf7d5e412654039359e0d50e6e1cb952fa541dd3b997272563ab34cff | v4_exact | v4_exact | ✅ |
| 23 | ledger_validator_contract.md | 20105 | c5b94e63b055ef6a989cb77282e2ade13cd5ae330899c90ee32567fbcf877978 | 441a3276ebcd049efa738c602a98fe102a02634cbd8f8f4e9dbefe75b2ecefab | crlf_only | crlf_only | ✅ |
| 24 | operation_contract.schema.json | 79656 | 7e44a159d83801565478bf0fc34ce6809d0871d68f4d140020af2110d91d07f8 | 9a074cba494e9ce8e670ab3940201280aacfe01d0aa880a52873e42b238b1721 | unproven_new_baseline | unproven_new_baseline | ✅ |
| 25 | operation_contracts.schema.json | 11677 | e4924cfbad3087fceafc6d5a9f60216a325d31ec768d557775c3c5c407b58b31 | 5f3350756c169582076091cbed3017544017a0c72cc3e85111f70fd65aa6808a | unproven_new_baseline | unproven_new_baseline | ✅ |
| 26 | operation_contracts.v4.json | 22890 | 4cf7dab5c2ced9f0ddb73319d1ef278467ba00fc4e36fb126fb37bb3cfe9f187 | ea5350c66b701b34888bb4197e56e79f64e8e421004a96a01194ec159c462098 | unproven_new_baseline | unproven_new_baseline | ✅ |
| 27 | operation_execution_receipt.schema.json | 8877 | 128cc8f5c986f095d209f4cca666cf8ac4d82f100950ded9f046ba12f969b6b9 | 128cc8f5c986f095d209f4cca666cf8ac4d82f100950ded9f046ba12f969b6b9 | v4_exact | v4_exact | ✅ |
| 28 | operation_intent_manifest.schema.json | 16503 | 57363a15c67498a384800aa0b8bf9140b9a8cc77edc4bbf80c1bc18965053a9d | 36e41bc0c6bdbbd9d14e2f2d3c6d6c38fbb09ae66368197d863a4872c77412ee | unproven_new_baseline | unproven_new_baseline | ✅ |
| 29 | operation_intent_template.schema.json | 14022 | d1a8ec48d648257bf32ae014dfe9e8fb788400a2d30657ec6261317494001b9a | 50ef54451e389c66ce1efeb297da80b359048f00bf1213b2e4cf718e080e7fd9 | unproven_new_baseline | unproven_new_baseline | ✅ |
| 30 | parser_route_manifest.schema.json | 7091 | 7eb962bab81d76c05ec04f257b5895d17897fa0c1217c046c7c6cd612459c8f7 | 7eb962bab81d76c05ec04f257b5895d17897fa0c1217c046c7c6cd612459c8f7 | v4_exact | v4_exact | ✅ |
| 31 | plan_consistency_check.py | 71496 | 0f008bad07297c4fa86261a3473dd0dbdccd4f86f64821e2014710be1618661f | 3897ee37d67765846ab72b3826a2725944236b934cb28a4c0ff8b8e21988698b | unproven_new_baseline | unproven_new_baseline | ✅ |
| 32 | plan_freeze_check.v4.txt | 172 | ca47be86a15d94c68787c637d08567cdf57b2be51e27ee67f2cdff84b9137af7 | ca47be86a15d94c68787c637d08567cdf57b2be51e27ee67f2cdff84b9137af7 | v4_exact | v4_exact | ✅ |
| 33 | plan_manifest.schema.json | 4062 | 23086172e96c10f010b3a6a0f9c55c85af04172c487c1b5ba5e934dbb0c252a7 | 23086172e96c10f010b3a6a0f9c55c85af04172c487c1b5ba5e934dbb0c252a7 | v4_exact | v4_exact | ✅ |
| 34 | plan_review_findings.md | 32595 | 17206a816de688afa29bfeff734e0abc79954cef7964f0d4de568f6e07dd9559 | c7c120beb76598c6256ef7874681562dd8127ab5e1bddef4d28fe4f04c61b183 | crlf_only | crlf_only | ✅ |
| 35 | review_confirmation.schema.json | 2471 | 6765641ff37ee5561211641520be1c45c85b86769a5c0720c4ded5c19675efd9 | 6765641ff37ee5561211641520be1c45c85b86769a5c0720c4ded5c19675efd9 | v4_exact | v4_exact | ✅ |
| 36 | review_result.schema.json | 4767 | 05099f08435fe7e9b28d240e7a2c6d18067db14b33863b4180faddcb5cfe4e0f | 05099f08435fe7e9b28d240e7a2c6d18067db14b33863b4180faddcb5cfe4e0f | v4_exact | v4_exact | ✅ |
| 37 | rollout_rollback_runbook.md | 32836 | 2728be56f758a53d9a91631707909ff88e0a5d394760bccdbbaaed67c64786a4 | 1fe062b08e778eb9a468eabcfaa3ee86d3aebb6fd703f32ac552fe6fae2576d9 | crlf_only | crlf_only | ✅ |
| 38 | schema_registry.schema.json | 2564 | 771dfa72a6f037067dbda12cb62b96f81d77a646009ff967b41259f9da276189 | 771dfa72a6f037067dbda12cb62b96f81d77a646009ff967b41259f9da276189 | v4_exact | v4_exact | ✅ |
| 39 | task_plan.md | 57300 | 46634bec14cf3046c30b4b0159413b91ea66e00fb8833c3ab046dc7b14f2e336 | 2bd0aa046a8f71ab17df69fdb498fb1709fc2fcc95272583bed5c90ae2ccf305 | crlf_only | crlf_only | ✅ |
| 40 | test_acceptance_plan.md | 54832 | 8f0a86919e60d1cac6b022cb2bb26a284748c707bdf35972a0938a8a609bffc3 | fad4e438de826cdf68ffbe6ca3cdc8087c3eef88f8713aa7c2d289887ddd2fed | crlf_only | crlf_only | ✅ |
| 41 | test_id_registry.schema.json | 12830 | 7f61d64464437b83b2bc14da06b33acc53691263859679fd9ca8093f7c0c1d74 | 73f7d9dbb4ace209d76df95b91f11e4a8a770dee9a96911879b01e8f8d6500cb | crlf_only | crlf_only | ✅ |
| 42 | test_id_registry.v4.json | 123062 | b2040c1557ed6b4efb1fa9cee029375594c0bc9285c1d7ccb566937a6ac85add | 673dc7a6526c7b02c7944727a1c6d4f570b5e61971d8b0d7a192ea19b8299629 | crlf_only | crlf_only | ✅ |
| 43 | traceability_matrix.md | 23780 | 7a6865532489f8783b34cd62e138f4f2de8ce8fb89bbf56d819a7c3567626ef4 | 90d96446a5a67fa34c358ce82326a2c55d02839875d68249b3ec939e19689595 | crlf_only | crlf_only | ✅ |
| 44 | user_approval_receipt.schema.json | 7619 | ec6f4863f7a583fc929a2508913065df8aba7fa6099c5bcf8b6bb0bfb8bcb0c8 | ec6f4863f7a583fc929a2508913065df8aba7fa6099c5bcf8b6bb0bfb8bcb0c8 | v4_exact | v4_exact | ✅ |
| 45 | validator_fixture_manifest.schema.json | 7511 | 4d1b313e1d48a62b7a3c5e2c32b00c571823758c83cd9360e4c06d5f7900c9a9 | 4d1b313e1d48a62b7a3c5e2c32b00c571823758c83cd9360e4c06d5f7900c9a9 | v4_exact | v4_exact | ✅ |
| 46 | validator_release_manifest.schema.json | 9247 | f1148f53cf27e8abcded4b7a8e248689a416fb78a71bad10ea6c88f5efc7f639 | f1148f53cf27e8abcded4b7a8e248689a416fb78a71bad10ea6c88f5efc7f639 | v4_exact | v4_exact | ✅ |
| 47 | validator_request.schema.json | 2546 | 1d7c52c4c39949818334e327fe038041183b7417aec21eb2caac64b00b2635ee | 1d7c52c4c39949818334e327fe038041183b7417aec21eb2caac64b00b2635ee | v4_exact | v4_exact | ✅ |
| 48 | validator_scenario_fixture.schema.json | 7507 | 7dbd6c8e438d07168a5cbe5ccd391d449347bc4934a9d82447fbf09d1fae29d3 | 7dbd6c8e438d07168a5cbe5ccd391d449347bc4934a9d82447fbf09d1fae29d3 | v4_exact | v4_exact | ✅ |

**不一致项：0。** 另核：`import_manifest.v5.json` 的 `historical_v4_sha256` 与 `baseline/history/plan_manifest.v4.json` 的 `sha256` 48/48 相同；`import_manifest` 的 `sha256`/`size_bytes`/`source_sha256_before`/`source_sha256_after` 对 48 份文件全部等于磁盘字节（0 处偏差）。

## 附录 B：17 份 `crlf_only` 的"仅 EOL 变化"证明（任务 2）

对每份文件：`N = C.replace(b"\r\n", b"\n")`。

1. `sha256(N) == historical_v4_sha256`（独立计算）——`N` 即 v4 冻结字节（抗碰撞假设下）；
2. `len(N) == plan_manifest.v4.json 的 size_bytes`（第二独立锚，作者工具未做）；
3. `C.count(b"\r") == C.count(b"\r\n")`（`lone_cr = 0`）——`C` 中不存在孤立 CR；
4. 因此 `C` 与 `N` 的唯一差异是：在某些 `\n` 前插入了 `\r`。**非 EOL 字节逐字节相同**（`N` 由 `C` 仅删除紧邻 `\n` 的 `\r` 得到）。

| 文件 | v4 字节数 | LF 归一化后字节数 | Δ（=插入的 CR 数） | 孤立 CR | 证明 |
|---|---|---|---|---|---|
| acceptance_thresholds.md | 23060 | 23060 | 336 | 0 | ✅ |
| agent_review_gates.md | 32843 | 32843 | 567 | 0 | ✅ |
| execution_playbook.md | 67191 | 67191 | 1171 | 0 | ✅ |
| gate_dag.v4.json | 22486 | 22486 | 285 | 0 | ✅ |
| gate_ledger.schema.json | 24127 | 24127 | 384 | 0 | ✅ |
| gate_ledger_validator_vectors.schema.json | 11317 | 11317 | 170 | 0 | ✅ |
| gate_ledger_validator_vectors.v4.json | 59297 | 59297 | 270 | 0 | ✅ |
| gate_state_machine.md | 27816 | 27816 | 453 | 0 | ✅ |
| implementation_agent_prompts.md | 20138 | 20138 | 388 | 0 | ✅ |
| ledger_validator_contract.md | 19856 | 19856 | 249 | 0 | ✅ |
| plan_review_findings.md | 32408 | 32408 | 187 | 0 | ✅ |
| rollout_rollback_runbook.md | 32321 | 32321 | 515 | 0 | ✅ |
| task_plan.md | 56471 | 56471 | 829 | 0 | ✅ |
| test_acceptance_plan.md | 54039 | 54039 | 793 | 0 | ✅ |
| test_id_registry.schema.json | 12657 | 12657 | 173 | 0 | ✅ |
| test_id_registry.v4.json | 117091 | 117091 | 5971 | 0 | ✅ |
| traceability_matrix.md | 23553 | 23553 | 227 | 0 | ✅ |

```powershell
python %TEMP%\v5sqlreview\eol_proof.py %TEMP%\v5sqlreview\eol_proof.json
# counts: {"v4_exact": 21, "crlf_only": 17, "unproven_new_baseline": 10}
# problems: []
# hist_vs_v4manifest_mismatches: []
# （17 行 crlf_only 全部 proved=True）
```

**未发现任何"以 EOL 归一化之名"的语义改动。** 附注：旧目录 `docs/plans/source-catalog-worker-recovery-2026-08-22/` 的 38 份文件**不是** v4 冻结字节（0/38 命中 v4 原始哈希、3/38 命中 v4 的 LF 归一化哈希；git 历史仅解析出 3/48 个 v4 目标），故无法提供逐字节 diff 的第三锚，证明依赖上述哈希+长度论证。

## 附录 C：SQL/DB 相关冻结语料核验（任务 3）

哈希三重一致（磁盘字节 / `import_manifest.sha256` / `plan_manifest.v5.json` 条目），且 LF 归一化后等于 v4 冻结哈希：

| 文件 | 字节 | 磁盘 sha256 | 类别 | 三方哈希一致 |
|---|---|---|---|---|
| operation_contracts.v4.json | 22890 | 4cf7dab5c2ced9f0ddb73319d1ef278467ba00fc4e36fb126fb37bb3cfe9f187 | unproven_new_baseline | ✅ |
| operation_contract.schema.json | 79656 | 7e44a159d83801565478bf0fc34ce6809d0871d68f4d140020af2110d91d07f8 | unproven_new_baseline | ✅ |
| operation_contracts.schema.json | 11677 | e4924cfbad3087fceafc6d5a9f60216a325d31ec768d557775c3c5c407b58b31 | unproven_new_baseline | ✅ |
| gate_dag.v4.json | 22771 | c06b20d040eb8c7adcb4186986c6e0ddffb83b1d122e9773ea415d9bf038dee1 | crlf_only | ✅ |
| gate_dag.schema.json | 10146 | b8fd02ae712f3e1c509c230e2a0c30e222985fddd11327e7187397cce3d88188 | v4_exact | ✅ |
| gate_ledger.schema.json | 24511 | f9f14cc3f73bd34b4cd56a17454be80b40b1ea83ae0bedf450e2723106588b55 | crlf_only | ✅ |
| gate_ledger_transcript.schema.json | 1673 | d32e15b03b53aef53549c825f4f19c1cdf13c876481b16c79effc75a0b5d173e | v4_exact | ✅ |
| gate_ledger_validator_vectors.schema.json | 11487 | d1395630ad9419692ba37be3b40ff4e55701560c6c4dbf1557a1f71063b2ed10 | crlf_only | ✅ |
| gate_ledger_validator_vectors.v4.json | 59567 | 7e2472d76ae93e9338d5c5b8ec02ec5f44806b9da3e159ccc4cebb46cee1fcef | crlf_only | ✅ |
| test_id_registry.v4.json | 123062 | b2040c1557ed6b4efb1fa9cee029375594c0bc9285c1d7ccb566937a6ac85add | crlf_only | ✅ |
| test_id_registry.schema.json | 12830 | 7f61d64464437b83b2bc14da06b33acc53691263859679fd9ca8093f7c0c1d74 | crlf_only | ✅ |
| plan_manifest.schema.json（v4 冻结 schema，仅历史） | 4062 | 23086172e96c10f010b3a6a0f9c55c85af04172c487c1b5ba5e934dbb0c252a7 | v4_exact | ✅ |

**检查组是否真的运行（无跳过）——三重证据**：

1. **代码路径**：`tools/v5_plan_consistency_check.py:125-143` 的 `baseline_suite()` 依次调用 `schema_checks / dag_checks / operation_checks / registry_checks / vector_checks / catalog_pointer_checks / active_prose_semantic_checks / pre_freeze_output_checks`，并另加布局感知的 `IMMUTABLE-HISTORY` 锚（`plan_manifest.v3.json` = `9ee84acd…`，我已独立复现该哈希）。它**不**调用 `base.main()`（因此不含 v4 专属的 `plan_manifest_checks`），这一点与 v5 语义一致。
2. **分组计数**（`python %TEMP%\v5sqlreview\group_activity.py`，在临时副本上重放同一序列）：`schema_checks 1825 / dag_checks 982 / operation_checks 224 / registry_checks 3852 / vector_checks 569 / catalog_pointer_checks 6 / active_prose_semantic_checks 32 / pre_freeze_output_checks 3`，合计 7493；加上 history 锚 1 项 = 7494，再加 `v5_checks` 的 164 项 = **7658**，与默认模式实测完全吻合——**没有任何一组是 0 项**。
3. **定向变异必被拒**（同一脚本，每例只改临时副本）：`gate_ledger.schema.json` 改 `$id` → `SCHEMA-ID-BINDING/SCHEMA-REF-CLOSURE/SCHEMA-REGISTRY-LOOKUP`；`gate_ledger.schema.json` 改 `type` → `SCHEMA-META/SCHEMA-SHAPE/SCHEMA-REGISTRY`；`gate_ledger_transcript/…vectors/test_id_registry/operation_contract(s)` 各改 `$id` → `SCHEMA-ID/SCHEMA-ID-BINDING`；`gate_dag.v4.json` 改 `plan_revision` → `DAG-REV/INSTANCE-SCHEMA`，删节点 → `DAG-DANGLING/DAG-ENTRY/TEST-LIFECYCLE-NODE`；`test_id_registry.v4.json` 改版本 → `TEST-REV/INSTANCE-SCHEMA`，删用例 → `TEST-COUNT/TEST-UNRESOLVED/INSTANCE-SCHEMA`；`gate_ledger_validator_vectors.v4.json` 改版本 → `VECTOR-REV/INSTANCE-SCHEMA`，删向量 → `VECTOR-ID/INSTANCE-SCHEMA`；`operation_contracts.v4.json` 断指针 → `POINTER/INSTANCE-SCHEMA`。**14/14 变异全部被拒，对照组 0 错误。**

## 附录 D：复现命令（全部从仓库根目录执行）

```powershell
# 三种模式（墙钟/退出码/产物哈希）
python docs\plans\source-catalog-worker-recovery-v5-2026-09-03\tools\v5_plan_consistency_check.py
python docs\plans\source-catalog-worker-recovery-v5-2026-09-03\tools\v5_plan_consistency_check.py --verify-manifest
python docs\plans\source-catalog-worker-recovery-v5-2026-09-03\tools\v5_plan_consistency_check.py --self-test
# 实测：7658 / 8867 checks；self-test 17/17；默认模式 stdout 172 B、sha256 88f407ae…、0 个 CR，
# 与 plan_freeze_check.v5.txt 逐字节相同（pre_freeze_check.stdout_sha256 绑定成立）。

# 证据工具只读复核
python docs\plans\source-catalog-worker-recovery-v5-2026-09-03\tools\v5_version_reference_scan.py --check
python docs\plans\source-catalog-worker-recovery-v5-2026-09-03\tools\v5_equivalence_check.py --check

# 属性与 N10
git check-attr text eol filter working-tree-encoding -- <51 个冻结路径>   # 204 行、全 unset
git rev-parse HEAD:docs/plans/source-catalog-worker-recovery-v5-2026-09-03/plan_manifest.v5.json
git hash-object docs/plans/source-catalog-worker-recovery-v5-2026-09-03/plan_manifest.v5.json
# 两者相同：0150f4eaf078928eb3dcbd448f9a2129447a1c17
```

自包含的等价性复算片段（不依赖本审查的临时脚本）：

```python
import hashlib, json, pathlib
V5 = pathlib.Path("docs/plans/source-catalog-worker-recovery-v5-2026-09-03")
imp = json.loads((V5/"import_manifest.v5.json").read_text(encoding="utf-8"))
sha = lambda b: hashlib.sha256(b).hexdigest()
out = {"v4_exact": [], "crlf_only": [], "unproven_new_baseline": []}
for e in imp["files"]:
    if e.get("role") != "prior_plan_current_content":
        continue
    raw = (V5/e["target"]).read_bytes()
    hist = (e.get("historical_v4_sha256") or "").lower()
    if hist and sha(raw) == hist:
        out["v4_exact"].append(e["target"])
    elif hist and sha(raw.replace(b"\r\n", b"\n")) == hist:
        out["crlf_only"].append(e["target"])
    else:
        out["unproven_new_baseline"].append(e["target"])
print({k: len(v) for k, v in out.items()})
# {'v4_exact': 21, 'crlf_only': 17, 'unproven_new_baseline': 10}
```
