# V5-2.1 复审关闭复核（SQL/性能轴：数据完整性 + 验证机制成本）

日期：2026-09-09。审查者：**independent reviewer（SQL/性能轴）**，非作者。范围：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03/`（`fcap` HEAD `85044ed`，整改冻结提交 `917b8d8`，首轮冻结 `454f632`）。
方法：**全部独立重算**——不采信记录中的任何"实测值"；只读复算脚本置于 `%TEMP%\v5sqlreview\`（仓库外）。本文件是本轮唯一写入仓库的文件。未 `git add/commit/push`，未触碰 worker/数据库/任务/其他仓库。

结论：**accepted**

> 我上一轮的 7 条 findings（1 P1 + 3 P2 + 3 P3）**全部关闭**，处置诚实。独立复验：51/51 冻结项哈希+字节数一致且全部与 `HEAD` blob 相等；等价性从字节重算 = `21/17/10`，与 manifest、`v5-baseline-equivalence.json`、v4 冻结 manifest 三方零分歧；预冻结产物 172 字节、0 CR、sha `8c01b9dc…` 与 manifest 绑定一致；证据 `evidence` 绑定、取代链、investigation、capture 绑定全部命中。新增 3 条**非阻断**观察（1 条 P3 范围限定 + 2 条成本/死代码提示），不影响冻结。

---

## 1. 逐条 findings 关闭表

| ID | 首轮结论 | 本轮判定 | 处置诚实性 | 证据（精确命令 + 实测输出） |
|---|---|---|---|---|
| **SQL-P1-1** N6 只核对标签计数 | P1 | **CLOSED** | 诚实（`fixed`） | 代码：`checker:339-373` 对每个导入件用 `captured[rel]["historical_v4_sha256"]` 从字节复算，并**逐件**交叉核对 v4 冻结 manifest（`:366`）与 `v5-baseline-equivalence.json`（`:368`）。实测 `python %TEMP%\v5sqlreview\closure_probe.py`：<br>· 计数守恒互换 → `codes ["N6","N7"]`（`N6: … declared unproven_new_baseline, recomputed crlf_only from bytes`）<br>· 互换 + 同步证据 JSON → `codes ["N6","N7"]`<br>· 互换 + 同步 capture 历史哈希 → `codes ["N6","N7"]`<br>· **隔离 v4 锚**（标签/capture/证据 JSON 全同步，仅 v4 manifest 不同意）→ `N6: capture historical hash != the v4 frozen manifest entry`<br>· **隔离证据锚**（仅把文件在证据 JSON 中换组）→ `N6: label crlf_only contradicts v5-baseline-equivalence.json`（唯一编码）<br>对照组 0 错误。 |
| **SQL-P2-1** 记录计数不可复现 | P2 | **CLOSED** | 诚实（`fixed`） | 实测 `python …\v5_plan_consistency_check.py` → `PASS: 7710 checks`（产物 sha `8c01b9dc…`、172 B、0 CR）；`--verify-manifest` → `PASS: 9174 checks`（与记录 §2 一致）。记录 §2 已显式声明「计数是运行环境相关观测值，不是冻结断言；唯一冻结断言是产物字节」。计数算术可完全解释：基线 7494（含 history 锚 1）+ `v5_checks` 216 = **7710**；`verify_manifest` +1464（含 `dag_checks` 重跑 982、N5 51、N6 145、N7 145、N10 53、N9 56）= **9174**，无未解释检查项。N10 未跟踪即 red（见 P2 说明与探针 `N10 untracked fail-closed`）。 |
| **SQL-P2-2** import 写 `tools/__pycache__` | P2 | **CLOSED** | 诚实（`fixed`，含"无法根治"的如实声明） | docstring `:18-23` 明示"以脚本执行零写入；import 调用方必须先置 `sys.dont_write_bytecode=True`"；记录 D10 同述；B3 现断言**两个**缓存目录（`checker:277-279`）。实测 `python %TEMP%\v5sqlreview\closure_narrow.py b3`：注入 `tools/__pycache__` → `codes ["B3-BOUNDARY-DRIFT"]`；注入 `baseline/plan/__pycache__` → 同时触发 `V5-SET-NESTED` + `B3-BOUNDARY-DRIFT`。`closure_narrow.py import` 仍复现 `tools\__pycache__\v5_plan_consistency_check.cpython-313.pyc`（CPython 固有行为），但已被文档化且会变红而非静默。 |
| **SQL-P2-3** 审查窗口内记录被改写 | P2 | **CLOSED** | 诚实（`accepted-with-reason`） | 记录头部 `:5` 明确「本记录本身**不是冻结锚**……锚点是 manifest + 冻结集 + Git 提交」；V5-2.1 产物与记录同一次提交（`917b8d8`）。本轮复核期间仍观测到活动文档并发写入（`findings.md` mtime `22:03:15`、`progress.md` `22:03:09`），但 51 项冻结条目在其后（`2026-09-09T21:05:15Z` = 本地 22:05:15）复核全部一致——即并发写入**不触及冻结集**。 |
| **SQL-P3-1** N8 只做子串匹配 | P3 | **CLOSED** | 诚实（`fixed`） | `checker:408-413`：`command == EXPECTED_COMMAND` 且无 `#`，并解析唯一 `.py` token 归一化后必须等于冻结 checker；schema 亦为 `const`（`schema:144-146`）。实测探针：指向他处同名脚本 → `N8: pre_freeze_check.command must equal …` + `command must invoke exactly the frozen checker entry`；把命令藏在 `#` 注释后 → 同样被拒。 |
| **SQL-P3-2** git 子进程缺超时 | P3 | **CLOSED** | 诚实（`fixed`） | `grep -n "subprocess.run\|timeout="` 命中 7 处调用点，**全部带 timeout**（`git check-attr` 120 s、证据工具 600 s、N8 重跑 600 s、N10 各 60 s、self-test `git init` 60 s）。成本见 §3 观察（非阻断）。 |
| **SQL-P3-3** 旧目录缺失即静默 | P3 | **CLOSED** | 诚实（`fixed`） | N9 改为申报式枚举 + 摘要复算 + 双向计数相等（`checker:446-480`）。实测：删除退役目录但保留申报 → `N9: declared 1 retired dirs but found 0`；新增未申报兄弟副本 → `N9: retired plan copy not declared…` + `declared 1 … found 2`；改动退役副本内容 → `N9: declared inventory … != measured (38, cf76383a…)`。三者皆 red，不再静默。 |

**P1 一行状态：SQL-P1-1 = CLOSED**（计数守恒互换现被 N6 从字节复算拒绝，并另有 v4 冻结 manifest 与证据 JSON 两道逐件交叉核对）。

---

## 2. 独立复验（任务 3，全部重算，不采信记录）

命令：`python %TEMP%\v5sqlreview\closure_verify.py`（2026-09-09T21:05:15Z）

| 项 | 实测 | 结论 |
|---|---|---|
| 51 项哈希+字节数 | `hash_size_mismatches: []` | 51/51 一致 |
| Git 跟踪 / blob 相等 | `untracked: []`、`blob_mismatches: []`；manifest `HEAD:blob == hash-object == 025402ecf22abd5d0e139b4515d53499d0438887` | 52/52 对象与 `HEAD` 一致 |
| 等价性（从字节重算，双锚） | `{v4_exact: 21, crlf_only: 17, unproven_new_baseline: 10}`；`label_mismatches: []`；`capture_vs_v4manifest_mismatches: []`；证据计数同为 21/17/10 | 三方零分歧 |
| manifest `evidence` 绑定 | `v5-version-reference-inventory.json 150ae6a4… / 30088`、`v5-baseline-equivalence.json 79ac6ca4… / 2970`，`ok: true` | 2/2 |
| 其它绑定 | `evidence_tools` 2/2、`capture_manifest_ok: true`（`da7d116e…`）、`supersedes` 2/2、`investigation_ok: true`、`composition {48,3,51,1}`、`normative_file_count = len(normative_files) = 51` | 全绿 |
| 预冻结产物 | 172 字节、**0 个 CR**、sha `8c01b9dc011bda445fd6d055812105ff535205371b8dbf8e66d73a38ecd6197f`、首行 `PASS: 7710 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}`、`binding_ok: true`；且与**现场默认模式运行** stdout 逐字节相同 | 绑定成立且可复现 |
| `.gitattributes` | `git check-attr text eol filter working-tree-encoding` × 51 路径 = **204 行、204 unset、0 非 unset** | 与 B4 一致 |
| 退役目录 | 38 文件、`inventory_sha256 = da927ee294978a2578d459e285bbd00f7e7abea87ae6e42a0294a588f9a8c81b`（与边界记录申报值相同）、tracked 38、clean | N9 载荷可复算 |
| `__pycache__` | 计划目录内 `[]` | 无污染 |
| 记录 §1 哈希声明 | 8/8 全部命中（manifest `afedfdd8…`/13976、产物 `8c01b9dc…`/172、schema `4e7ce1e6…`/7039、checker `a40a3d7a…`/41389、生成器 `459b7c7d…`/6420、inventory `150ae6a4…`/30088、等价性 `79ac6ca4…`/2970、边界 `f14f8cfc…`/5489） | 全部可复现 |
| 与首轮冻结的差异 | `python %TEMP%\v5sqlreview\freeze_compare.py` → `imported_48_identical: true`、`imported_paths_touched_by_commits: []`；仅 `plan_manifest.schema.v5.json` 与 `tools/v5_plan_consistency_check.py` 两个 `v5_own` 治理件变化；`capture_same: true`、`evidence_tools_same: true`、summary/composition 不变 | 48 份导入语料**零改动**，与"仅列出的文件变化"一致 |
| SQL/DB 语料与检查组 | `python %TEMP%\v5sqlreview\group_activity.py`：`schema 1825 / dag 982 / operation 224 / registry 3852 / vector 569 / pointer 6 / prose 32 / prefreeze 3 = 7493`；14/14 定向变异全部被拒（`SCHEMA-ID-BINDING`、`DAG-REV`、`TEST-REV`、`VECTOR-REV`、`POINTER` …） | 基线组全部运行、无 0 项组 |

---

## 3. 新增观察（全部非阻断，不改变冻结结论）

| ID | 严重度 | 观察 | 证据 | 建议 |
|---|---|---|---|---|
| SQL-P3-4 | P3（范围限定） | **N9 的处置块本身没有哈希锚**：它保存在 `v5-freeze-boundary.md`（非冻结集、manifest 不绑定其哈希）。因此"改动退役副本 + 同步改写处置块的摘要"可保持 N9 全绿。记录 §6 残余风险 2 的措辞「改动会被 N9 摘要比对发现」只对"未同步改写申报"的情形成立。 | `python %TEMP%\v5sqlreview\n9_scope.py` → 仅改副本：`measured (38, 8d07ac88…)`；再同步边界记录申报后：`{"codes": [], "rejected": false}`（0 错误）。 | 若要覆盖该情形，把 `v5-freeze-boundary.md` 的 sha256 纳入 manifest 绑定（如扩展 `evidence` 或加专用字段），使协同改写触发 N17/N15 类红；或把 §6 残余风险 2 的措辞限定为"未同步改写申报时会被发现"。 |
| SQL-OBS-1 | P3（成本） | `--verify-manifest` 成本上升约 4×：N10 对 52 个对象逐个执行 3 次 git 子进程（共 156 次），另有 N8 的"真实树重跑默认模式"。实测 `--verify-manifest` 11.3/13.2 s（首轮 2.5–3.0 s）、`161` 次 `subprocess.Popen`；`--self-test` 46.6/53.0 s（首轮 11.4/12.1 s），因每个变异都复制 `baseline/`+`tools/`+**退役目录**（27 份），读 255 MB、写 253 次、FS 变更 3,737 次（**全部在 `%TEMP%`，outside_temp = 0**）。仍为有界、可接受的一次性冻结门禁成本。 | `python %TEMP%\v5sqlreview\run_modes.py plan_runs2.json runs2.json`；`python %TEMP%\v5sqlreview\audit_io.py {default,verify,self}` | 可选优化：把 N10 的 156 次 spawn 合并为 3 次（`git ls-files -z` + `git ls-tree -r HEAD` + `git hash-object --stdin-paths`）；self-test 改为"复制一次 + 逐例回滚"。 |
| SQL-OBS-2 | P3（死代码） | `checker:438` 设置 `env=dict(os.environ, V5_PREFREEZE_CHILD="1")`，但全文件**从未读取** `V5_PREFREEZE_CHILD`。默认模式不会进入 `verify_manifest`，本无递归风险，该变量为遗留。 | `grep -n "V5_PREFREEZE_CHILD" tools/v5_plan_consistency_check.py` → 仅 1 处（赋值处） | 删除或注明用途，避免误以为存在递归保护。 |

## 4. 声明

- 本复核只读、非作者；唯一写入仓库的文件即本文件。未提交、未推送、未运行旧 checker/worker、未触碰数据库/计划任务/其他仓库；PLAN_ONLY 上下文未授权任何实施，本复核也不构成实施授权。
- 所有复算脚本位于 `%TEMP%\v5sqlreview\`（仓库外）：`closure_probe.py`（13 个对抗用例）、`closure_verify.py`、`closure_narrow.py`、`n9_scope.py`、`freeze_compare.py`、`group_activity.py`、`audit_io.py`、`run_modes.py`、`snapshot.py`、`recompute_equivalence.py`、`eol_proof.py`、`count_dependence.py`。
- 变更安全实测：13 个对抗用例 + 3 种模式运行前后对计划目录全量快照，`added/removed/changed` 全为空；audit hook 记录 `write_mode_open_count_outside_temp = 0`、`fs_mutation_count_outside_temp = 0`、`network_events = 0`、`sqlite_events = 0`。
- 残余（不隐瞒）：① 仍无 v4 冻结**字节**的第三方来源（旧目录与 v4 哈希 0/38 相同），EOL-only 结论依赖"LF 归一化字节的 sha256 == v4 冻结哈希 **且** 长度 == v4 冻结字节数"的抗碰撞论证；② 冻结只覆盖规划文档完整性；③ 旧目录仍可被改动——N9 能发现"未同步申报"的改动，但见 SQL-P3-4 的范围限定；④ 记录/审查文件本身不是冻结锚，其完整性由 Git 与独立审查背书。
