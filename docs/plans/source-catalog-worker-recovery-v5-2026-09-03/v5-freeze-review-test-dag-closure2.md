# V5-2.2 冻结三审（测试 / DAG 轴）— 二轮新 P1 关闭裁定

审查者：独立审查代理（测试/DAG 轴；未参与本计划任何文档或工具的编写）
复审对象：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03`，V5-2.2 冻结提交（仓库 `HEAD 9418e72`；记录声明冻结时点 `85044ed`）
被复审的二轮结论：`v5-freeze-review-test-dag-closure.md`（NEW-P1-1 N8 重跑可劫持；NEW-P1-2 v4 锚未锚定；7 条新 P2）
方法：不采信 `v5-freeze-record.md` §8 的整改声明；逐条重跑二轮公开配方并针对新机制（子进程 `-I`、`V5-TOOLS-EXACT`、`PINNED-HISTORY`、`boundary_record` 绑定、N10 祖先/语料校验）构造新对抗。破坏性试验只在 `C:\v5rev3` 临时副本；真实冻结树只读。
环境：Windows + PowerShell 7，Python 3.13.9，jsonschema 4.26.0。

## 结论

**axis verdict: `accepted_with_findings`**

二轮 2 条 P1 中：**NEW-P1-2 CLOSED**（`PINNED-HISTORY` 6 项在冻结内代码钉扎，原配方及 EOL/硬链接变体全部被拒）；**NEW-P1-1 PARTIAL**——N8 的**子进程**劫持已闭合（`-I` + `V5-TOOLS-EXACT` 实测拒绝 `tools/json.py` 与 `tools/json/__init__.py` 两种植入），但**同一原语仍能伪造 checker 自身的判定**：把影子模块放在 `tools/` 后，**父进程**在 `import json`（checker 第 30 行）阶段就被劫持，0.2s 内打印伪造的 `PASS: 9188 checks` 并 `exit 0`，`V5-TOOLS-EXACT` 永远没有机会执行；改用**无源码字节码** `tools/json.pyc`（不是 `*.py`，枚举不到）同样伪造成功（0.1s），且植入文件无需提交（`?? tools/json.py` 即可）。这属于 P1 级验证力缺口，记录 §8 声称 `V5-TOOLS-EXACT` 已修复该根因，与实测不符。其余 P2：N9 处置载荷已由 manifest 绑定（未同步的改写被拒），但"无标记且不改名"的副本与"移出 `docs/plans/`"的副本仍不可见（记录 §6.3 已如实声明为残余）；空目录、`evidence_tools` 精确集、畸形 manifest→`N4`、`plan_freeze_git_head` 祖先校验、`tools/*.py` 枚举、N10.2 自测均已闭合；`V5-SET-GOVERNING` 的计数合取项仍恒真（记录称"已修"不准确）；`frozen_at` 无锚（已声明为残余）。冻结产物本身完全自洽：51/51 哈希、`PINNED-HISTORY` 6/6、manifest+51 的 Git blob 全等、产物 172B/0CR/`5e60611c…`、`7720`/`9188` 计数算术可解释、自测 17 例/31 变异+3 项全拒。

## 1. 逐条裁定表

| ID | 裁定 | 证据（命令 + 观测） | 说明 |
|---|---|---|---|
| NEW-P1-1（N8 重跑劫持） | **PARTIAL** | ① 子进程臂：`python C:\v5rev3\harness.py child_hijack_py verify` → `exit=1`，`V5-TOOLS-EXACT: tools/ scripts must be exactly […4 项…], found ['tools/json.py', …]`、`B3-BOUNDARY-DRIFT: …tools\__pycache__`、`N8: a fresh default-mode run does not reproduce …`；`child_hijack_pkg`（`tools/json/__init__.py`）→ `exit=1`，`V5-TOOLS-EXACT … found ['tools/json/__init__.py', …]`。② **父进程臂仍可伪造**：`harness.py parent_hijack_py verify` → `exit=0 elapsed=0.2s`，输出 `PASS: 9188 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}`；`harness.py parent_hijack_pyc verify`（`tools/json.pyc`）→ `exit=0 elapsed=0.1s`，同样伪造 `PASS: 9188`；③ 未跟踪植入：在 `parent_hijack_py` 副本内 `git rm --cached tools/json.py` 后 `git status` 显示 `?? …/tools/json.py`，再运行 → 仍 `PASS: 9188` `exit=0`；④ `.pyc` 枚举缺口：在该副本上 `python -I …/v5_plan_consistency_check.py --verify-manifest` → `FAIL: 2 error(s)`，仅 `N8`/`N10`，**无 `V5-TOOLS-EXACT`**（`tools/json.pyc` 不在 `rglob("*.py")` 内）。 | 子进程侧已闭合；父进程侧未闭合。修法：checker 自身也应以 `-I -P` 语义启动（或在入口处先 `sys.path` 自净），并且 `V5-TOOLS-EXACT` 应枚举 `tools/**` 的**全部**文件（排除已知清单）而非仅 `*.py`；同时记录 §8 的"已修"表述需更正为"仅闭合子进程臂"。 |
| NEW-P1-2（v4 锚未锚定） | **CLOSED** | `harness.py v4anchor_bypass verify` → `exit=1`：`PINNED-HISTORY: baseline/history/plan_manifest.v4.json: expected c34b849475…, got 25c2a317…` + `N8`；`harness.py v4anchor_eol verify`（仅改 EOL）→ `exit=1`：`PINNED-HISTORY … expected c34b849475…, got a38a6fbf…`、`N11: supersedes hash mismatch`、`V5-EVIDENCE-CHECK`；`harness.py v4anchor_hardlink verify`（硬链接 + 改写）→ `exit=1`：`PINNED-HISTORY … got 2a2647b1…`、`N11`、`V5-EVIDENCE-CHECK`。 | 6 份历史/来源文件在冻结内 checker 里钉哈希，字节严格（无 EOL 归一化）；改写它们必须同时改冻结 checker + manifest（见 §2 的 irreducible 类）。 |
| P2：N9 处置载荷未锚定 | **CLOSED** | `harness.py n9_boundary_rewrite verify`（新增副本 + 改写处置块、不同步 manifest）→ `exit=1`：`N9: manifest does not bind v5-freeze-boundary.md bytes`。 | 同步 manifest 后再提交属于"新提交"类（`n9_boundary_rewrite_synced` → `PASS: 9241`），记录 §6.4 已声明。 |
| P2：N9 标记改名绕过 | **PARTIAL** | ① 具名副本（`source-catalog-worker-recovery-2026-08-22` 内标记改名、申报为空）`harness.py n9_marker_renamed_named verify` → `exit=1`：`N9: retired plan copy not declared …`；② **无标记且不改名**的副本 `harness.py n9_unnamed_extra verify`（保留原申报，新增 `docs/plans/archive-2027/`）→ **`PASS: 9188`**。 | 记录 §6.3 已把"同时改名"列为残余；实测确认。 |
| P2：副本移出 `docs/plans/` | NOT CLOSED（已声明） | `harness.py n9_outside_plans_synced verify`（副本移到 `docs/retired-copy/`、处置块申报为空并同步 manifest 绑定）→ **`PASS: 9135`**。 | 记录 §6.3 已声明；建议把候选扫描扩展到 `docs/**`。 |
| P2：空子目录不可见 | **CLOSED** | `harness.py n9_empty_dir verify` → `exit=1`：`V5-SET-NESTED: unexpected files below baseline/plan/**: ['empty_subdir/']`、`N13: files below baseline/plan/** are not enumerated`。 | 递归枚举含目录 |
| P2：N10 Git 臂无自测 | **CLOSED** | 真实树 `--self-test` → `SELF-TEST N10.1/N10.2 PASS: rejected (full+isolated)`；`SELF-TEST: 17 cases / 31 mutations + 3 default-mode checks; failures=none`。 | 新增 `_n10_git_rewrite`（提交后改写冻结件） |
| P2：`tools/` 未枚举 | **PARTIAL** | `harness.py tools_extra_py verify`（新增 `tools/extra_helper.py`）→ `exit=1`：`V5-TOOLS-EXACT … found ['tools/extra_helper.py', …]`；但 `tools/json.pyc`/`tools/json.pyd` 等非 `*.py` 文件不被枚举（见 NEW-P1-1 ④）。 | 枚举范围应覆盖全部文件 |
| P2：`V5-SET-GOVERNING` 恒真 | **PARTIAL** | checker line ~280：`tuple(ctx.governing) == GOVERNING and len(GOVERNING) == EXPECTED_GOVERNING and len(set(ctx.governing)) == EXPECTED_GOVERNING`；`ctx.governing` 在 `main()` 与 `self_test` 中恒为模块常量 `GOVERNING`，三个合取项恒真；新增的 3 条逐件存在性检查（`V5-SET-GOVERNING` 计数 4）确有价值。 | 记录 §8 称"已修"不准确；应改为从 `declared`/`entries` 统计 `v5_own` 数。 |
| P2：`evidence_tools` 非精确集 | **CLOSED** | `harness.py extra_evidence verify` → `exit=1`：`N17: evidence_tools must be exactly ['tools/v5_version_reference_scan.py', 'tools/v5_equivalence_check.py'], got ['tools/does_not_exist.py', …]`。 | |
| P2：畸形 manifest 崩溃 | **CLOSED** | `harness.py malformed_manifest verify` → `exit=1`：`N4: manifest verification crashed: JSONDecodeError: …`；`harness.py entry_missing_path verify` → `exit=1`：`N4: manifest verification crashed: KeyError: 'path'`。 | 无 traceback，稳定编码 |
| P2：`plan_freeze_git_head` 未锚定 | **CLOSED** | `harness.py fake_head verify` → `exit=1`：`N10: plan_freeze_git_head '000…0' is not an ancestor of HEAD containing the corpus`；`fake_head_nonancestor`（`111…1`）→ 同样 `N10`。 | 祖先 + 语料存在性双判据 |
| P2：`frozen_at` 无锚 | NOT CLOSED（已声明） | `harness.py fake_frozen_at verify`（1999-01-01）→ **`PASS: 9188`**。 | 记录 §6.4 已如实声明无法机器锚定 |
| P2：N6 路径错配误导归因 | NOT CLOSED | `harness.py case_variant_path verify` → `exit=1`：`N13: missing=['baseline/plan/README.md'] extra=['baseline/plan/Readme.md']` 与 `N6: equivalence_summary … != recomputed {… 'unproven_new_baseline': 9, 'v5_own': 3}` 同时出现。 | 记录 §8 称"已修（capture 无记录时交给 N7 报告）"针对的是另一种情形；路径错配仍误报为 N6 |
| P2：N2 子串误报 | **CLOSED**（代码级；未构造反例） | 代码改为 `retired_refs = [f"docs/plans/{name}"]` 前缀匹配；`supersedes_retired`/`lookalike` 等场景 N2/N11 均按预期触发（见附录 A）。 | 本轴未构造"无关兄弟目录名导致误报"的反例 |
| P2：非 `.py` 文件可致 checker 崩溃 | **NEW P2** | `harness.py pyd_plant verify`（植入非法 `tools/json.pyd`）→ `exit=1`，traceback：`File "…v5_plan_consistency_check.py", line 30, in <module> import json`（扩展模块优先于源码，加载失败即中断）。 | fail-closed（exit 1），但无稳定编码；且与 NEW-P1-1-R 同根因（`tools/` 影子模块）。修法同 NEW-P1-1-R。 |

## 2. 新增 findings

| ID | Sev | Finding | 证据 | Required fix |
|---|---|---|---|---|
| NEW-P1-1-R | **P1** | **`V5-TOOLS-EXACT` 无法保护 checker 自身进程**：`-I` 只作用于 N8 子进程；审查者按 manifest `pre_freeze_check.command` 运行的**父进程**仍以 `tools/` 为 `sys.path[0]`，`import json`（第 30 行）即执行植入模块，在任何检查之前打印伪造结论并 `exit 0`。植入无需提交；`tools/json.pyc`（无源码字节码）连枚举都逃过（`rglob("*.py")`）。 | `harness.py parent_hijack_py verify` → `exit=0 elapsed=0.2s`，`PASS: 9188 checks; …`；`parent_hijack_pyc verify` → `exit=0 elapsed=0.1s`，同样输出；`git rm --cached` 后未跟踪植入仍 `PASS`；`python -I` 下 `tools/json.pyc` 存在却无 `V5-TOOLS-EXACT` 报错。 | ① 在 checker 入口最前部（导入 stdlib 之前）用 `-P` 语义自净 `sys.path` 不可行（进程已启动），因此**文档化命令应改为 `python -I <checker>`**（或提供一个 `-I` 包装脚本，并把 manifest `command` 改为该包装）；② `V5-TOOLS-EXACT` 枚举 `tools/` 下**所有**文件（含 `.pyc`/`.pyd`/包目录），白名单化；③ 记录 §8 更正为"仅闭合子进程臂，父进程臂依赖 `-I` 启动"。 |
| NEW-P2-A | P2 | 记录 §8 的两处"已修"表述与实测不符：`V5-SET-GOVERNING` 的计数合取仍恒真；N6 在路径错配时仍误报等价性。 | 见 §1 对应行。 | 更正记录；或按 §1 的修法实现。 |
| NEW-P2-B | P2 | `tools/` 下非 `*.py` 文件既不被枚举、又可影响进程（非法 `.pyd` → 崩溃；合法 `.pyd`/`.pyc` → 劫持）。 | `harness.py pyd_plant verify`（traceback at `import json`）；`parent_hijack_pyc verify`（伪造 PASS）。 | 同 NEW-P1-1-R ②。 |

## 3. 独立复算与再验证（全部通过）

| 项目 | 命令 | 观测 |
|---|---|---|
| 51/51 冻结项哈希 | `python C:\v5rev3\verify_new.py` | `51-entry hash check: entries=51 mismatches=none` |
| 预冻结产物 | 同上 | `bytes=172 CR=0 sha=5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83 matches_manifest=True` |
| `PINNED-HISTORY` 6/6 | 同上 | `PINNED-HISTORY: 6/6 match` |
| 边界记录绑定 | 同上 | `boundary binding: manifest=b5a8a67a2c7c0b8f file=b5a8a67a2c7c0b8f match=True` |
| manifest+51 的 Git blob | 同上（`git ls-files -s` + `hash-object --stdin-paths`） | `git blob equality: targets=52 missing=none mismatches=none` |
| coverage 独立复算 | 同上 | 8 项与 manifest `coverage_counts` **相等**（115/315/18/140/29/60/44/105） |
| 自测 | 真实树 `--self-test` | `17 cases / 31 mutations + 3 default-mode checks; failures=none`（含 `N10.2`、`V5-TOOLS-EXACT`、`V5-SET-NESTED`、`V5-PATH-SAFETY`），exit 0 |
| 默认 / verify | 真实树 `…` / `… --verify-manifest` | `PASS: 7720 checks; …`（exit 0）／`PASS: 9188 checks; …`（exit 0） |
| 计数算术 | `probe_counts2.py` | `baseline_suite 7500`（=7494+6 `PINNED-HISTORY`）+ `v5_checks 220`（=216+1 `V5-TOOLS-EXACT`+3 治理件存在性）= **7720**；`verify_manifest 1468 = 486（N1–N17）+ 982（N13 coverage 复算的第二次 `dag_checks`）` → **9188** |
| 红旗 exit 1 | 各场景 | 全部 `exit=1`（含 `N10` fail-closed：未跟踪/改写/非祖先/无 Git） |
| 确定性 | 真实树 `PYTHONHASHSEED=0/1` | 默认模式两次 stdout 逐字节相同 |

## 4. 残余风险（含记录已声明的）

1. **父进程劫持（NEW-P1-1-R，未闭合）**：只要 `tools/` 可写且文档化命令不加 `-I`，checker 的判定即可被伪造。
2. "改写 + 同步全部记录 + 改冻结内钉扎 + 提交"的协同改写仍可通过（`v4anchor_full` → `PASS: 9188`；`n9_boundary_rewrite_synced` → `PASS: 9241`）；记录 §6.4 已声明"新提交不被拦截"。
3. N9 判据边界：无标记且不改名、或移出 `docs/plans/` 的副本不可见（`n9_unnamed_extra`、`n9_outside_plans_synced` 均 PASS）；记录 §6.3 已声明。
4. `frozen_at` 无机器锚（记录 §6.4 已声明）。
5. 本轴未做内容级语义审查、未评估 Windows 权限拒绝路径；未编译合法 `.pyd` 验证劫持（仅验证非法 `.pyd` 崩溃 + `.pyc` 劫持）。

## 附录 A — 全部对抗场景与结果（`C:\v5rev3\harness.py`，临时副本，均先 commit）

| 场景 | 结果 | 判定 |
|---|---|---|
| `child_hijack_py`（`tools/json.py` 只答子进程） | `exit=1`：`V5-TOOLS-EXACT` + `B3`(tools/__pycache__) + `N8` | 子进程臂 CLOSED |
| `child_hijack_pkg`（`tools/json/__init__.py`） | `exit=1`：`V5-TOOLS-EXACT` + `N8` | 子进程臂 CLOSED |
| `parent_hijack_py` | **`exit=0 elapsed=0.2s`，伪造 `PASS: 9188`** | **NEW-P1-1-R** |
| `parent_hijack_pyc` | **`exit=0 elapsed=0.1s`，伪造 `PASS: 9188`** | **NEW-P1-1-R** |
| `sitecustomize_plant`（`tools/sitecustomize.py`+`usercustomize.py`） | `exit=1`：`V5-TOOLS-EXACT`（文件被枚举；未被导入） | 无劫持 |
| `pyd_plant`（非法 `tools/json.pyd`） | `exit=1`，traceback at `import json` | NEW-P2-B |
| `wrapper_python`（`tools/python.exe`） | `exit=1`（`N8`/`N10`；`sys.executable` 为绝对路径，未使用） | 无劫持 |
| `v4anchor_bypass` | `exit=1`：`PINNED-HISTORY` + `N8` | **NEW-P1-2 CLOSED** |
| `v4anchor_eol` | `exit=1`：`PINNED-HISTORY` + `N11` + `V5-EVIDENCE-CHECK` | 字节严格 |
| `v4anchor_hardlink` | `exit=1`：`PINNED-HISTORY` + `N11` + `V5-EVIDENCE-CHECK` | 硬链接无效 |
| `v4anchor_full`（连钉扎一起改） | `PASS: 9188` | 已声明的"新提交"类 |
| `n9_boundary_rewrite`（不同步绑定） | `exit=1`：`N9: manifest does not bind v5-freeze-boundary.md bytes` | CLOSED |
| `n9_boundary_rewrite_synced` | `PASS: 9241` | 已声明的"新提交"类 |
| `n9_marker_renamed_named` | `exit=1`：`N9: retired plan copy not declared …` | 具名副本 CLOSED |
| `n9_unnamed_extra`（无标记+不改名副本，原申报保留） | **`PASS: 9188`** | 残余（§6.3） |
| `n9_outside_plans_synced`（副本移出 `docs/plans/`） | **`PASS: 9135`** | 残余（§6.3） |
| `n9_named_declared`（控制：具名副本 + 申报 + 绑定） | `PASS: 9241` | 合规（合同允许已申报副本） |
| `n9_empty_dir` | `exit=1`：`V5-SET-NESTED` + `N13` | CLOSED |
| `extra_evidence` | `exit=1`：`N17` | CLOSED |
| `malformed_manifest` / `entry_missing_path` | `exit=1`：`N4`（无 traceback） | CLOSED |
| `fake_head` / `fake_head_nonancestor` | `exit=1`：`N10` 祖先校验 | CLOSED |
| `fake_frozen_at` | `PASS: 9188` | 残余（§6.4） |
| `case_variant_path` | `exit=1`：`N13` + `N6`（误归因） | NOT CLOSED |
| `tools_extra_py` | `exit=1`：`V5-TOOLS-EXACT` | `*.py` 范围 CLOSED |

## 附录 B — 复现配方（NEW-P1-1-R 最小复现）

```powershell
# 1) 复制真实 plan 目录到临时 ASCII 路径（含退役副本），并做成 git 仓库
$t="C:\v5rev3\poc"; Remove-Item -Recurse -Force $t -EA 0
robocopy "<repo>\docs\plans\source-catalog-worker-recovery-v5-2026-09-03" "$t\docs\plans\source-catalog-worker-recovery-v5-2026-09-03" /E /NFL /NDL /NJH /NJS /NP
robocopy "<repo>\docs\plans\source-catalog-worker-recovery-2026-08-22" "$t\docs\plans\source-catalog-worker-recovery-2026-08-22" /E /NFL /NDL /NJH /NJS /NP
cd $t; git init -q; git config user.email r@example.com; git config user.name r; git config core.autocrlf false
git add -A; git commit -q -m base
# （可选）把 manifest 的 plan_freeze_git_head 改成本仓库 HEAD 并再提交，以满足 N10 祖先校验
# 2) 植入影子模块：只在 checker 被调用且非 --self-test 时伪造结论
$p="$t\docs\plans\source-catalog-worker-recovery-v5-2026-09-03\tools\json.py"
@'
import os, sys, sysconfig
_argv = sys.argv; _script = os.path.basename(_argv[0]) if _argv else ''
if _script == 'v5_plan_consistency_check.py' and '--self-test' not in _argv:
    sys.stdout.write('PASS: 9188 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}\n'
                     'READ_ONLY: no production database, registry, process, source, config, or network access\n')
    sys.stdout.flush(); os._exit(0)
_real = os.path.join(sysconfig.get_paths()['stdlib'], 'json', '__init__.py')
g = globals(); g['__file__']=_real; g['__name__']='json'; g['__package__']='json'
g['__path__']=[os.path.dirname(_real)]
exec(compile(open(_real,'rb').read(), _real, 'exec'), g)
'@ | Set-Content -Path $p -Encoding utf8
# 3) 按文档化命令运行（父进程 sys.path[0]=tools/ → 劫持）
python "$t\docs\plans\source-catalog-worker-recovery-v5-2026-09-03\tools\v5_plan_consistency_check.py" --verify-manifest
# 观测：立即打印 PASS: 9188 checks; … 并 exit 0（未执行任何检查）
# 变体：把上述 json.py 编译成 tools/json.pyc（无源码），效果相同且不被 V5-TOOLS-EXACT 枚举：
#   python -c "import py_compile;py_compile.compile(r'<json.py>', cfile=r'<tools>\json.pyc', doraise=True)"
# 缓解验证：python -I <checker> --verify-manifest 时该植入不被导入（此时 V5-TOOLS-EXACT 会以 *.py 枚举报错，
#           但对 tools/json.pyc 仍无报错）。
```

`PINNED-HISTORY` / N9 / 其余场景的复现脚本为 `C:\v5rev3\harness.py`（用法 `python harness.py <scenario> verify`，场景名见附录 A）。
