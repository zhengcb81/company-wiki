# V5-2.2 三审关闭复核（SQL/性能轴：数据完整性 + 验证机制成本）

日期：2026-09-09。审查者：**independent reviewer（SQL/性能轴）**，非作者。范围：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03/`（`fcap` HEAD `9418e72`，V5-2.2 冻结提交；上轮 `85044ed`）。
方法：全部独立重算，不采信记录中的任何"实测值"；只读复算脚本在 `%TEMP%\v5sqlreview\`（仓库外）。本文件是本轮唯一写入仓库的文件。未 `git add/commit/push`。

结论：**accepted_with_findings**

> 上轮我提的 3 项观察中 **SQL-P3-4 与 SQL-OBS-2 已 CLOSED**，**SQL-OBS-1 的成本目标达成**（verify 11.3–13.2 s → 4.84–5.89 s，git 子进程 156 → 5）；任务 4 的数据完整性**全部通过**（51/51 哈希+字节、等价性 21/17/10 三方零分歧、产物 172 B/0 CR/`5e60611c…`、`--verify-manifest` 9188 rc 0、`--self-test` 17 例/31 变异+3 全拒、manifest+51 项与 `HEAD` blob 相等、PINNED-HISTORY 6/6）。但本轮**发现 2 条新问题**：SQL-OBS-1 的批量化把 N10 的比较对象从 `HEAD` 换成了**索引**（可检测性回归），以及**文档化调用路径仍可被 `tools/` 下的同名模块影子化并伪造出逐字节正确的 PASS**。二者都不改变已冻结字节，故判定为 `accepted_with_findings` 而非 `rejected`。

---

## 1. 逐项判定

| 项 | 判定 | 证据（精确命令 + 实测输出） |
|---|---|---|
| **SQL-P3-4** N9 处置载荷未锚定 | **CLOSED** | manifest 新增 `boundary_record{path,sha256}`，schema 将其列入 `required`（`plan_manifest.schema.v5.json:43`、定义于 `:163`），N9 逐字节校验（`checker:545-549`）。实测 `python %TEMP%\v5sqlreview\closure2_probe.py`：<br>· 改退役副本 + 同步申报摘要 → `codes ["N9"]`，`N9: manifest does not bind v5-freeze-boundary.md bytes`（**拒**）<br>· 再同步 `manifest.boundary_record.sha256`（verify 单跑）→ 0 错误；**但在真实 git 树上**同一攻击 → `codes ["N10"]`，`N10: tracked file was rewritten after freeze: …/plan_manifest.v5.json`（**拒**）<br>链条完整：载荷 → manifest 绑定 → Git。独立复算 `boundary_record` 绑定 = `b5a8a67a2c7c0b8f654a95e07a787c59dc102f5dd100a9ac14f962caabbe9720`（6009 B），与磁盘一致。 |
| **SQL-OBS-2** `V5_PREFREEZE_CHILD` 死代码 | **CLOSED** | `Select-String -Path tools\*.py -Pattern V5_PREFREEZE_CHILD` → **0 命中**；子进程改为 `[sys.executable, "-I", str(ctx.root / CHECKER_REL)]`（`checker:501`）。隔离不改变默认输出：同一真实树上 `python <checker>` 与 `python -I <checker>` stdout **逐字节相同**（`PASS: 7720 checks; …`，且等于冻结产物 `5e60611c…`）。 |
| **SQL-OBS-1** 成本（156 次 git 子进程） | **CLOSED（成本）**，**但引入回归（见 SQL-P1-2）** | N10 改为 5 次 git 调用（`rev-parse --show-toplevel`、`ls-files -s`、`hash-object --stdin-paths`、`merge-base --is-ancestor`、`cat-file -e`）。实测 `python %TEMP%\v5sqlreview\run_modes.py plan_runs2.json runs3.json`：default **1.96/1.98 s**、`--verify-manifest` **4.84/5.89 s**（上轮 11.3/13.2 s）、`--self-test` **54.6/59.0 s**（上轮 46.6/53.0 s，变异数 27→31+3）。audit hook：verify 的 `subprocess.Popen` **9 次**（上轮 161 次）、读 9.84 MB、写模式打开 1 次（fd `"3"`，即 `hash-object --stdin-paths` 的 stdin 管道，非文件）、FS 变更 0、网络 0、SQLite 0。成本可接受。 |
| **任务 4 独立复验** | **CLOSED（全绿）** | 见 §2。 |
| **SQL-P1-2（新）** N10 的批量化把"worktree↔**HEAD**"降为"worktree↔**索引**" | **NEW · P1** | `git ls-files -s` 返回的是**索引** blob；`hash-object --stdin-paths` 返回工作树 blob。因此"改写冻结文件 + `git add`（已暂存、未提交）"**通过 N10**。对照实验（同一临时 git 仓库、同一场景，`python %TEMP%\v5sqlreview\n10_regression.py`）：<br>`{"checker":"V5-2.2 (HEAD, ls-files -s)","staged":false,"rewrite_detected":true}`<br>`{"checker":"V5-2.2 (HEAD, ls-files -s)","staged":true,"rewrite_detected":false}` ← **回归**<br>`{"checker":"V5-2.1 (85044ed, rev-parse HEAD:)","staged":true,"rewrite_detected":true}`<br>同源验证（`closure2_probe2.py`）：`N10 staged rewrite (isolated)` → `codes []`；`N10 unstaged rewrite (isolated)` → `N10: tracked file was rewritten after freeze`。**manifest 自身同受影响**（同一 `rels` 列表）：暂存改写 manifest 后 N10 隔离运行 `{"n_errors": 0}`。<br>记录 §6.4 写"N10 对 manifest + 51 个冻结项做 worktree↔HEAD blob 比对"——**与实现不符**（实为索引）。自测的 N10.2（`_n10_git_rewrite`，`checker:808-818`）改写后**不暂存**，因此无法暴露该语义变化。<br>**必须的修复**：把 `git ls-files -s` 换成 `git ls-tree -r HEAD -- <rels>`（仍是 1 次调用，成本不变），使比较对象回到 `HEAD`；并给自测补一个"暂存后改写"的变异。 |
| **SQL-P1-3（新）** 文档化调用可被 `tools/` 同名模块影子化 → 伪造逐字节正确的 PASS | **NEW · P1（按 NEW-P1-1 的同一先决条件与同一类别；若项目把"计划目录可写"视为范围外，可降为 P2）** | 记录 §5 的复现命令是 `python docs/…/tools/v5_plan_consistency_check.py`——这会把 `tools/` 放到 `sys.path[0]`，于是 `tools/json.py` **或** `tools/json.pyc` 会遮蔽标准库 `json`（checker 自身 `import json` 在 `:30`，先于任何检查）。实测 `python %TEMP%\v5sqlreview\pyc_forge.py`：植入 `tools/json.pyc`（其代码先输出冻结产物字节再 `SystemExit(0)`）→<br>`{"rc": 0, "stdout_equals_frozen_artifact": true, "stdout_head": "PASS: 7720 checks; {\"fixed_nodes\": 115, …"}`<br>即**逐字节完美的伪造 PASS，checker 根本没有运行**。`V5-TOOLS-EXACT` 无法阻止（影子发生在任何检查之前，且它只枚举 `*.py`，`.pyc` 不可见：实测 `tools_py_glob` 仅 4 个 `.py`）。`-I` 只加在 N8 子进程上；实测 `python -I <checker>` 时父进程**不受影响**（跑满 7720 检查），但两个证据工具子进程仍被影子化 → 以 `V5-EVIDENCE-CHECK` 变红（fail-closed，非静默）。<br>**建议修复**：① checker 启动时自检 `sys.path[0]` 是否为脚本目录，若是则用 `-I` 自我重启（或直接拒绝运行）；② 记录 §5 的复现命令改为 `python -I …`；③ `V5-TOOLS-EXACT` 改为枚举 `tools/` 下**全部**文件（仅豁免 `__pycache__`）；④ 证据工具子进程同样加 `-I`。 |

## 2. 任务 4：独立复验（`python %TEMP%\v5sqlreview\closure2_verify.py`，2026-09-09T21:22:44Z）

| 项 | 实测 | 结论 |
|---|---|---|
| 51 项哈希+字节数 | `hash_size_mismatches: []` | 51/51 一致 |
| Git 跟踪 / blob | `untracked: []`、`blob_mismatches: []`；manifest `HEAD:blob == hash-object == 75a51509f147e589f12d86ebe2701bc3377623e0` | 52/52 与 `HEAD` 相等 |
| 等价性（从字节重算） | `{v4_exact: 21, crlf_only: 17, unproven_new_baseline: 10}`；`label_mismatches: []`；`capture_vs_v4manifest_mismatches: []`；`evidence_group_mismatches: []` | 与 manifest、`v5-baseline-equivalence.json`、v4 冻结 manifest **三方零分歧** |
| 预冻结产物 | 172 B、**0 CR**、`5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83`、首行 `PASS: 7720 checks; …`、`binding_ok: true`；与现场默认运行逐字节相同 | 绑定成立 |
| `--verify-manifest` | `PASS: 9188 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}`，rc 0 | 一致 |
| `--self-test` | `SELF-TEST: 17 cases / 31 mutations + 3 default-mode checks; failures=none`，rc 0 | 全拒 |
| **PINNED-HISTORY** | 冻结内代码钉 6 项；6/6 磁盘哈希命中（v3/v4 manifest、`plan_review_revision.v4.md`、`progress.v4.md`、事故报告、原调查报告）；`baseline_suite` 实测 6 项检查；改写 v4 manifest / 事故报告 → `PINNED-HISTORY` 拒 | **6/6** |
| 其它绑定 | `evidence` 2/2、`evidence_tools` 2/2、`capture_ok`、`supersedes` 2/2、`investigation_ok`、`boundary_record` ok、`composition {48,3,51,1}`、`counts (51,51)` | 全绿 |
| 属性 / 缓存 | `git check-attr` × 51 路径 = 204 行、**204 unset**；计划目录内 `__pycache__` 为空 | 与 B4 一致 |
| 计数可分解（无静默跳过） | `python %TEMP%\v5sqlreview\count_by_code.py`：`baseline_suite 7500`（含 `IMMUTABLE-HISTORY 1` + `PINNED-HISTORY 6`）+ `v5_checks 220` = **7720**；`verify_manifest 1468`（N1 1、N2 1、N3 1、N4 1、N5 51、**N6 145**、**N7 145**、N8 6、**N9 57**、**N10 55**、N11 5、N12 1、N13 6、N14 1、N15 2、N16 3、N17 5）→ **9188** | 两个计数**完全分解**，无未解释检查项 |
| 与上轮冻结的差异 | 仅 2 个 `v5_own` 治理件（checker/schema）与记录/证据变化；48 份导入语料的 manifest 条目（sha/size/label）与 `imported_paths_touched_by_commits` 仍为零改动（上轮已验证，本轮 51/51 哈希复核覆盖） | 语料零改动 |
| 变更安全 | 15 个对抗用例 + 3 模式运行前后全目录快照 diff 全空；audit hook 零文件系统写入、零网络、零 SQLite | 无仓库污染 |

## 3. 声明与残余

- 本复核只读、非作者；唯一写入仓库的文件即本文件。未提交、未推送、未运行旧 checker/worker、未触碰数据库/计划任务/其他仓库。PLAN_ONLY 未授权任何实施。
- 复算脚本（仓库外）：`closure2_probe.py`、`closure2_probe2.py`、`n10_regression.py`、`pyc_forge.py`、`pyc_hijack.py`、`closure2_verify.py`、`count_by_code.py`、`closure_probe.py`（上轮 13 用例回归全绿）、`group_activity.py`、`audit_io.py`、`run_modes.py`、`snapshot.py`。
- 残余（如实）：① v4 冻结**字节**仍无第三方来源，EOL-only 结论依赖"LF 归一化字节 sha256 == v4 冻结哈希 且 长度 == v4 冻结字节数"的抗碰撞论证；② 冻结只覆盖规划文档完整性；③ 记录 §6.3 已声明 N9 判据边界（`docs/plans/` 之外或目录名与全部标记同时改名的副本不在范围内）；④ 记录本身不是冻结锚，本轮复核期间它仍被并发改写（`git status` 显示 `M v5-freeze-record.md`），不影响 51 项冻结条目（21:22:44Z 复核全绿）。
