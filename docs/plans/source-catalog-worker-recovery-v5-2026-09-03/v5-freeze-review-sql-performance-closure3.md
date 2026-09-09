# V5-2.3 四审关闭复核（SQL/性能轴：数据完整性 + 验证机制成本）

日期：2026-09-09。审查者：**independent reviewer（SQL/性能轴）**，非作者。审查对象：**提交 `89c0862`（V5-2.3 冻结）**，上一轮 `9418e72`。
方法：全部独立重算；本轮特别之处在于**工作树在复核过程中被作者推进到下一轮**（见 §4），因此最终结论以 **git 对象**（`git cat-file blob 89c0862:<path>`）为准，而非工作树。只读复算脚本在 `%TEMP%\v5sqlreview\`（仓库外）。本文件是本轮唯一写入仓库的文件。未 `git add/commit/push`。

结论：**accepted**

> 我上轮提的 2 条新 P1 **全部 CLOSED**：N10 已改比 `HEAD` blob（7 个"必须检出"的变体全部检出）；import 期劫持由"启动守卫 + 全链路 `-I` + `tools/` 全文件枚举"关闭（`tools/json.py`、`tools/json.pyc`、`tools/sitecustomize.py` 三条路径在无 `-I` 时均**无法伪造 PASS**，带 `-I` 时均被 `V5-TOOLS-EXACT` 报出）。成本未因 N10 改动回退（verify 5.21/5.49 s）。数据完整性从提交对象独立复验全绿。仅 1 条 P3 成本趋势观察（非阻断）。

---

## 1. 判定表

| 项 | 判定 | 证据（命令 + 实测） |
|---|---|---|
| **SQL-P1-2** N10 索引比对回归 | **CLOSED** | 代码：`git ls-tree -r HEAD -- <rels>`（`checker:585-596`，取 `fields[2]` = HEAD blob），与 `hash-object --stdin-paths` 的工作树 blob 比对。`python %TEMP%\v5sqlreview\n10_regression2.py`（每个变体独立临时 git 仓库，`plan_freeze_git_head` 设为该仓库 HEAD，仅 `N10` 编码生效）：<br>`unstaged → detected`、`staged → detected`、`intent_to_add → detected`、`assume_unchanged → detected`、`skip_worktree → detected`、`manifest_staged → detected`、`crlf_staged → detected`、`committed → not detected`（**设计内**：新提交是唯一账本，记录 §6.4 已声明）；V5-2.1 参考实现 `staged → detected`（一致性）。7/7 应检出的变体全部检出。 |
| **SQL-P1-3 / NEW-P1-1-R** 父进程 import 劫持 | **CLOSED** | 代码：启动守卫只依赖内建 `sys`，在任何标准库导入之前比较 `sys.path[0]` 与脚本目录（`checker:28-40`）；`EXPECTED_COMMAND` 含 `-I`（`:71`），N8 重跑、两个证据工具子进程均带 `-I`（`:515`、`:338`）；`V5-TOOLS-EXACT` 枚举 `tools/` 下**全部文件**（含 `.pyc`，仅豁免 `__pycache__`，`:299-303`）。实测（对**提交树** `git archive 89c0862` 解包后植入，`hijack_committed.py`）：<br>· `tools/json.py` 伪造 → 无 `-I`：`plain_rc 1`、`plain_forged_pass false`（守卫消息）；带 `-I`：`isolated_flags_tools true`、无伪造<br>· `tools/json.pyc` 伪造 → 同上<br>· `tools/sitecustomize.py` 伪造 → `sitecustomize_ran false`（启动期未执行）、无 `-I` 被守卫拒、带 `-I` 被 `V5-TOOLS-EXACT` 报出<br>真实树上：`python docs/…/tools/v5_plan_consistency_check.py` → rc 1 + 守卫消息；`python -I …` → `PASS: 7720` rc 0；从 v5 目录内相对路径调用 → rc 1。<br>证据工具自身：植入 `tools/json.pyc` 后 `python -I tools/v5_equivalence_check.py --check` → rc 0 `CHECK OK`（**未被劫持**）；记录 §5 的复现命令已全部改为 `python -I`。 |
| **成本（SQL-OBS-1 收尾）** | **CLOSED** | `python %TEMP%\v5sqlreview\run_modes.py plan_runs2.json runs5.json`（`-I`）：default **2.15/2.98 s**、`--verify-manifest` **5.21/5.49 s**（V5-2.2 为 4.84/5.89 s → **未回退**）、`--self-test` 75.5/87.7 s。提交树重跑（`extract_head.py`，`git archive 89c0862`）：default **3.24 s / 7720**，self-test **89.4 s / rc 0**。verify 仍为 9 次子进程（check-attr、2 证据工具、N8 重跑、5 次 git）。 |
| **数据完整性（任务 4）** | **CLOSED（全绿）** | 见 §2，全部取自 `git cat-file blob 89c0862:*`。 |
| SQL-OBS-3（新，P3，非阻断） | 观察 | `--self-test` 墙钟随轮次增长：首轮 11 s → V5-2.1 50 s → V5-2.2 55 s → **V5-2.3 89 s**（变异 27→31→34，且每次变异都要复制 `baseline/`+`tools/`+退役目录并 spawn `-I` 子进程）。仍是**一次性冻结门禁**成本、有界，可接受；但若每轮继续翻倍会成为 CI 负担。可选优化：一个临时树 + 逐例回滚，或把 GUARD/GUARD-I 之外的用例合并复制。**无需在本次冻结前修改。** |

## 2. 独立复验（`python %TEMP%\v5sqlreview\verify_from_head.py 89c0862`，2026-09-09T21:35:51Z，全部读 git 对象）

| 项 | 实测 | 结论 |
|---|---|---|
| 51 项哈希+字节数 | `frozen.mismatches: []`；manifest 自身 `55a2d2cb452a7620cd3c9d8b60ffecd54df7272feee4db7e571b40ec305f3d4e` / 14125 B | 51/51 一致 |
| 等价性（从提交字节重算） | `{v4_exact: 21, crlf_only: 17, unproven_new_baseline: 10}`；`label_mismatches: []`；`capture_vs_v4manifest_mismatches: []`；`evidence_group_mismatches: []` | 与 manifest、`v5-baseline-equivalence.json`、v4 冻结 manifest **三方零分歧** |
| 预冻结产物 | 172 B、**0 CR**、`5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83`、`PASS: 7720 checks; …`、`binding_ok: true` | 与上轮逐字节相同（记录已声明） |
| `--verify-manifest` | 干净树实测 `PASS: 9188 checks; …` rc 0（`runs5.json`，stdout sha `6ab6255c…`，运行期间 `plan_dir_changed: []`） | 一致 |
| `--self-test` | 提交树实测 `SELF-TEST: 17 cases / 32 mutations + 4 default-mode checks + 2 guard checks; failures=none`，rc 0 | 与记录一致 |
| **PINNED-HISTORY** | 提交内 checker 钉 6 项；6/6 提交 blob 哈希命中 | **6/6** |
| boundary_record 绑定 | 声明 `69db267e16cef004c3049960e7fa58724f5f0c8afa00dd38cc21e59c605e9255` == 提交 blob | 一致 |
| 其它绑定 | `evidence` 2/2、`evidence_tools` 2/2、`capture_ok`、`supersedes` 2/2、`investigation_ok`、命令 `python -I …` | 全绿 |
| 记录 §1 哈希声明 | 8/8 全部命中（manifest、产物、schema、checker、生成器、inventory、等价性、边界记录；sha 与字节数均一致） | 全部可复现 |
| 语料零改动 | 48 份导入文件的 manifest 条目（sha/size/label）自首轮冻结起未变（上轮 `imported_48_identical: true`，本轮 51/51 提交哈希复核覆盖） | 零改动 |

## 3. 复现配方（本轮新观察）

```powershell
# SQL-P1-2：N10 必须检出"改写 + 暂存"
python %TEMP%\v5sqlreview\n10_regression2.py      # 7 个应检出变体全部 detected；committed 变体按设计不检出

# SQL-P1-3：三种植入模块在提交树上都无法伪造 PASS
python %TEMP%\v5sqlreview\hijack_committed.py 89c0862

# 提交对象级完整性（不受工作树漂移影响）
python %TEMP%\v5sqlreview\verify_from_head.py 89c0862
```

## 4. 声明与观察

- 本复核只读、非作者；唯一写入仓库的文件即本文件。未提交、未推送、未运行旧 checker/worker、未触碰数据库/计划任务/其他仓库。PLAN_ONLY 未授权任何实施。
- **工作树漂移（过程观察，非 findings）**：复核期间作者在 22:34 开始推进下一轮，工作树出现未提交修改（`plan_manifest.v5.json`、`tools/v5_plan_consistency_check.py`、`v5-freeze-boundary.md`；checker 已增至 58 055 B）。因此：① 我对 `89c0862` 的结论全部由 **git 对象**独立复验；② 实时模式运行（default/verify/self-test）均在树仍干净时采集，并额外用 `git archive 89c0862` 的独立解包重跑了 default 与 self-test 以交叉确认。
- 残余（如实）：① v4 冻结**字节**仍无第三方来源，EOL-only 结论依赖"LF 归一化字节 sha256 == v4 冻结哈希 且 长度 == v4 冻结字节数"的抗碰撞论证；② 冻结只覆盖规划文档完整性；③ N10 不拦截"一次新的提交"（提交历史是最终账本，记录 §6.4 已声明）；④ 记录/审查文件本身不是冻结锚。
