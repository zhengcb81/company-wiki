# V5-2.3 冻结四审（测试 / DAG 轴）— 三轮 P1 关闭裁定

审查者：独立审查代理（测试/DAG 轴；未参与本计划任何文档或工具的编写）
复审对象：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03`，V5-2.3 冻结提交（仓库 `HEAD 89c0862`）
被复审的三轮结论：`v5-freeze-review-test-dag-closure2.md`（NEW-P1-1-R 父进程 import 劫持；NEW-P2-A 记录措辞；NEW-P2-B 非 `.py` 植入）
方法：不采信 `v5-freeze-record.md` §8 的整改声明；重跑三轮公开配方并针对新守卫（`sys.path[0]` 自检、全链路 `-I`、`tools/` 全文件枚举）构造新对抗。破坏性试验只在 `C:\v5rev4` 临时副本；真实冻结树只读。
环境：Windows + PowerShell 7，Python 3.13.9，jsonschema 4.26.0。

## 结论

**axis verdict: `accepted_with_findings`**

**无 P0/P1 残留**：三轮的 P1 已闭合——`python <checker>`（不带 `-I`）现在在**任何标准库导入之前**由内建 `sys` 自检并 `exit 1`（0.1s，无伪造输出），带 `-I` 时 `tools/json.py`、`tools/json.pyc`、`tools/json.pyd`、`tools/sitecustomize.py`、`tools/extra.pyc` 全部被 `V5-TOOLS-EXACT` 全文件枚举拒绝，`PYTHONPATH` 被 `-I` 的 `-E` 语义忽略；`NEW-P1-2`（v4 锚）在四审回归中仍被 `PINNED-HISTORY` 拒绝。剩余 3 条 P2：**NEW-P2-C**——守卫只比较"脚本目录"，`python -m tools.v5_plan_consistency_check`（cwd 进 `sys.path[0]`）可绕过，在 plan 根植入 `json.py`/`json.pyc` 仍能伪造 `PASS: 9188` 并 `exit 0`（0.1s）；**NEW-P2-D**——记录 §8 对 N6 的"不再误报等价类别"在 summary 层面仍不准确（路径错配时 N6 仍报 `equivalence_summary != recomputed`）；**NEW-P2-E**——记录 §6.9 只声明"另一个解释器包装脚本"不覆盖，未把 `-m` 调用方式列入。冻结产物本身完全自洽：51/51 哈希、`PINNED-HISTORY` 6/6、manifest+51 的 HEAD blob 全等、产物 172B/0CR/`5e60611c…`、`--verify-manifest` 9188 rc 0、自测 17 例/32 变异+4 项默认检查+2 项守卫检查全拒。

## 1. 逐条裁定表

| ID | 裁定 | 证据（命令 + 观测） | 说明 |
|---|---|---|---|
| NEW-P1-1-R（父进程 import 劫持） | **CLOSED**（文档化流程） | ① 守卫：真实树 `python docs/plans/…/tools/v5_plan_consistency_check.py --verify-manifest` → `exit=1`，stderr `FAIL: run with an isolated interpreter - \`python -I <checker>\`.` + `The script directory on sys.path[0] would allow stdlib shadowing.`；② `python -I … --verify-manifest` → `PASS: 9188 checks; …` `exit=0`；③ `harness.py hijack_py_isolated`（植入 `tools/json.py`，`-I` 运行）→ `exit=1`：`V5-TOOLS-EXACT: tools/ must be exactly […4 项…], found ['tools/json.py', …]` + `N8`；④ `hijack_pyc_isolated`（`tools/json.pyc`）→ `exit=1`：`V5-TOOLS-EXACT … found ['tools/json.pyc', …]` + `N8`；⑤ `hijack_py_noisolate`（同植入，不带 `-I`）→ `exit=1 elapsed=0.1s`，仅守卫信息，**无伪造 PASS**；⑥ `hijack_relative_noisolate`（相对路径调用、不带 `-I`）→ 守卫同样触发；⑦ `hijack_pythonpath`（`PYTHONPATH=tools` + `-I`）→ `exit=1`：`V5-TOOLS-EXACT` + `N8`。 | 守卫只用内建 `sys`（`import sys as _sys` 在守卫前，其后才导入其余 stdlib）；`-I` 同时忽略 `PYTHONPATH`/用户 site 且不前置脚本目录 |
| NEW-P2-A（记录措辞） | **CLOSED**（1 处仍偏窄，见 NEW-P2-D） | 记录 §8 现写 `V5-SET-GOVERNING`「已修（断言等于预期三元组且三个文件存在；计数 conjunct 本身恒真，仅作一致性声明——如实标注，不声称它本身是判据）」——与代码一致（checker 第 292 行计数 conjunct + 第 295 行起 3 条存在性检查，`V5-SET-GOVERNING` 共 4 次调用）；N6 现写「部分修：capture 无记录时由 N7 报告、manifest 声明但磁盘缺失由 N13 报告（N6 不再误报等价类别）；不再声称覆盖'路径错配'全部场景」。 | `V5-SET-GOVERNING` 的表述已准确；N6 的表述仍偏窄（见 NEW-P2-D） |
| NEW-P2-B（非 `.py` 植入） | **CLOSED** | `harness.py pyd_plant`（`tools/json.pyd`，`-I`）→ `exit=1`：`V5-TOOLS-EXACT … found ['tools/json.pyd', …]` + `N8`；`tools_extra_pyc`（`tools/extra.pyc`）→ `exit=1`：`V5-TOOLS-EXACT … found ['tools/extra.pyc', …]`；`sitecustomize_plant`（`tools/sitecustomize.py`+`usercustomize.py`）→ `exit=1`：`V5-TOOLS-EXACT … found ['tools/sitecustomize.py', …]`。 | `V5-TOOLS-EXACT` 改为 `rglob("*")` 全文件枚举（仅豁免 `__pycache__`），自测含 `.py` 与 `.pyc` 两个变异 |
| closure2：N9 无标记/不改名副本 | NOT CLOSED（已声明 §6.3） | `harness.py n9_unnamed_extra`（保留原申报，新增 `docs/plans/archive-2027/`）→ **`PASS: 9188`**。 | 记录 §6.3 已如实声明 |
| closure2：副本移出 `docs/plans/` | NOT CLOSED（已声明 §6.3） | `harness.py n9_outside_plans_synced`（副本移到 `docs/retired-copy/`、申报为空并同步 manifest 绑定）→ **`PASS: 9135`**。 | 同上 |
| closure2：`frozen_at` 无锚 | NOT CLOSED（已声明 §6.4） | `harness.py fake_frozen_at` → **`PASS: 9188`**。 | 同上 |
| closure2：N6 路径错配归因 | NOT CLOSED（表述已收窄） | `harness.py case_variant_path` → `exit=1`：`N13: missing=['baseline/plan/README.md'] extra=['baseline/plan/Readme.md']` 与 `N6: equivalence_summary … != recomputed {… 'unproven_new_baseline': 9, 'v5_own': 3}` 同时出现。 | 见 NEW-P2-D |
| 回归：N9 载荷绑定 | **CLOSED** | `harness.py n9_boundary_rewrite`（不同步绑定）→ `exit=1`：`N9: manifest does not bind v5-freeze-boundary.md bytes`。 | 无回归 |
| 回归：N9 具名标记改名 | **CLOSED** | `harness.py n9_marker_renamed_named`（含同步绑定）→ `exit=1`：`N9: retired plan copy not declared …`、`N9: declared 0 retired dirs but found 1`。 | 无回归 |
| 回归：v4 锚 | **CLOSED** | `harness.py v4anchor_bypass` → `exit=1`：`PINNED-HISTORY: baseline/history/plan_manifest.v4.json: expected c34b849475…, got 25c2a317…` + `N8`。 | 无回归 |
| 回归：`evidence_tools` 精确集 | **CLOSED** | `harness.py extra_evidence` → `exit=1`：`N17: evidence_tools must be exactly […], got ['tools/does_not_exist.py', …]`。 | 无回归 |
| 回归：`plan_freeze_git_head` 祖先校验 | **CLOSED** | `harness.py fake_head` → `exit=1`：`N10: plan_freeze_git_head '000…0' is not an ancestor of HEAD containing the corpus`。 | 无回归 |
| 回归：畸形 manifest | **CLOSED** | `harness.py malformed_manifest` → `exit=1`：`N4: manifest verification crashed: JSONDecodeError: …`。 | 无回归 |
| 新增：N10 索引回归修复 | **CLOSED**（正向验证） | 真实树 `--self-test` → `SELF-TEST N10.3 PASS: rejected (full+isolated)`；代码改为 `git ls-tree -r HEAD`（对比 HEAD blob 而非索引）。 | 覆盖"改写 + `git add` 未提交"场景 |

## 2. 新增 findings

| ID | Sev | Finding | 证据 | Required fix |
|---|---|---|---|---|
| NEW-P2-C | P2 | **启动守卫只比较"脚本目录"，`-m` 调用方式可绕过**：`python -m tools.v5_plan_consistency_check` 时 `sys.path[0]` 是 cwd（plan 根），守卫的 `_FIRST == _HERE_DIR` 不成立而放行；plan 根可写，植入 `json.py` 或 `json.pyc` 即可在 `import json` 阶段伪造 `PASS: 9188` 并 `exit 0`。 | `harness.py hijack_module_mode`（`python -m tools.v5_plan_consistency_check --verify-manifest`，cwd=plan 根，植入 `<plan>/json.py`）→ **`exit=0 elapsed=0.1s`，`PASS: 9188 checks; …`**；把植入改为 `<plan>/json.pyc` 重跑 → 同样 **`exit=0`，伪造 `PASS: 9188`**；对照 `python -I -m tools.v5_plan_consistency_check` 与 `python -P -m …` → `ModuleNotFoundError: No module named 'tools'`（`-I/-P` 不前置 cwd，fail-closed）。 | 守卫改为以解释器标志为准：`if not sys.flags.isolated: refuse`（`-I` 时 `sys.flags.isolated==1`），或除 `sys.path[0]` 外再校验"stdlib 之前的任何 `sys.path` 项都不得位于仓库内/可写"。 |
| NEW-P2-D | P2 | 记录 §8 对 N6 的表述「（N6 不再误报等价类别）」在 **summary** 层面仍不准确：路径错配时 N6 仍以 `equivalence_summary != recomputed` 报错（真正原因是路径）。 | `harness.py case_variant_path` → `N13` 与 `N6: equivalence_summary … != recomputed {… 'unproven_new_baseline': 9, 'v5_own': 3}` 同时出现。 | 把 N6 的 summary 比较改为只在 `set(declared) == set(entries)` 成立时执行，或在记录中补一句"summary 臂在路径错配时仍会误报"。 |
| NEW-P2-E | P2 | 记录 §6.9 只声明"若有人用**另一个**解释器包装脚本运行，防御不覆盖"，未覆盖"同一解释器 + `-m` 调用"这一实测可行的绕过路径。 | 见 NEW-P2-C。 | 记录 §6.9 补充 `-m` 情形；或按 NEW-P2-C 的修法从机制上关闭。 |

## 3. 独立复算与再验证（全部通过）

| 项目 | 命令 | 观测 |
|---|---|---|
| 51/51 冻结项哈希 | `python C:\v5rev4\verify_new.py` | `51-entry hash check: entries=51 mismatches=none` |
| 预冻结产物 | 同上 | `bytes=172 CR=0 sha=5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83 matches_manifest=True` |
| `PINNED-HISTORY` 6/6 | 同上 | `PINNED-HISTORY: 6/6 match` |
| 边界记录绑定 | 同上 | `boundary binding: manifest=69db267e16cef004 file=69db267e16cef004 match=True` |
| manifest+51 的 HEAD blob | 同上（`git ls-tree -r HEAD` + `hash-object --stdin-paths`） | `git blob equality: targets=52 missing=none mismatches=none` |
| coverage 独立复算 | 同上 | 8 项与 manifest `coverage_counts` 相等（115/315/18/140/29/60/44/105） |
| 守卫（无 `-I`） | 真实树 `python …/v5_plan_consistency_check.py --verify-manifest` | `exit=1` + 守卫信息（无任何检查执行） |
| 隔离运行 | 真实树 `python -I …/v5_plan_consistency_check.py --verify-manifest` | `PASS: 9188 checks; …` `exit=0` |
| 自测 | 真实树 `python -I … --self-test` | `SELF-TEST: 17 cases / 32 mutations + 4 default-mode checks + 2 guard checks; failures=none`（含 `N10.3`、`V5-TOOLS-EXACT.py/.pyc`、`GUARD`、`GUARD-I`），exit 0 |
| 确定性（前轮） | 真实树 `PYTHONHASHSEED=0/1` | 逐字节相同（本轴四审未复跑，未发现影响确定性的改动） |

## 4. 残余风险

1. **NEW-P2-C**：非 `-I` 的 `-m` 调用可绕过守卫（P2，需调用方偏离文档化命令）。
2. N9 判据边界：无标记且不改名、或移出 `docs/plans/` 的副本不可见（记录 §6.3 已声明；四审复跑仍 PASS）。
3. `frozen_at` 无机器锚（记录 §6.4 已声明）。
4. "改写 + 同步全部记录 + 改冻结内钉扎 + 提交"的协同改写仍不可被树内检查拦截（记录 §6.4 已声明；本轴未复跑 `v4anchor_full`，其结论与前轮一致）。
5. 本轴未做内容级语义审查、未评估 Windows 权限拒绝路径、未编译合法 `.pyd` 验证劫持（`-I` 下 tools/ 不在 `sys.path`，预期不可劫持）。

## 附录 A — 四审场景与结果（`C:\v5rev4\harness.py`，临时副本，均先 commit）

| 场景 | 调用方式 | 结果 | 判定 |
|---|---|---|---|
| `hijack_py_isolated`（`tools/json.py`） | `python -I <checker>` | `exit=1`：`V5-TOOLS-EXACT` + `N8` | 子进程/父进程均安全 |
| `hijack_pyc_isolated`（`tools/json.pyc`） | `python -I <checker>` | `exit=1`：`V5-TOOLS-EXACT`（found `tools/json.pyc`）+ `N8` | 全文件枚举生效 |
| `hijack_py_noisolate` | `python <checker>` | `exit=1`（0.1s）守卫信息，无伪造输出 | **CLOSED** |
| `hijack_relative_noisolate` | `python docs/plans/…/tools/<checker>`（相对路径，无 `-I`） | `exit=1` 守卫信息 | **CLOSED** |
| `hijack_pythonpath`（`PYTHONPATH=tools`） | `python -I <checker>` | `exit=1`：`V5-TOOLS-EXACT` + `N8` | `-E` 语义生效 |
| `hijack_module_mode`（`<plan>/json.py`） | `python -m tools.v5_plan_consistency_check`（cwd=plan 根） | **`exit=0`（0.1s）伪造 `PASS: 9188`** | **NEW-P2-C** |
| 同上，植入 `<plan>/json.pyc` | 同上 | **`exit=0` 伪造 `PASS: 9188`** | **NEW-P2-C** |
| 同上，`python -I -m` / `python -P -m` | — | `ModuleNotFoundError`（exit 1，fail-closed） | 修复方向验证 |
| `pyd_plant`（`tools/json.pyd`） | `python -I <checker>` | `exit=1`：`V5-TOOLS-EXACT` + `N8` | **CLOSED**（NEW-P2-B） |
| `tools_extra_pyc`（`tools/extra.pyc`） | `python -I <checker>` | `exit=1`：`V5-TOOLS-EXACT` | **CLOSED** |
| `sitecustomize_plant`（`tools/sitecustomize.py`+`usercustomize.py`） | `python -I <checker>` | `exit=1`：`V5-TOOLS-EXACT` | **CLOSED** |
| `n9_unnamed_extra` | `python -I <checker>` | `PASS: 9188` | 残余（§6.3） |
| `n9_outside_plans_synced` | 同上 | `PASS: 9135` | 残余（§6.3） |
| `fake_frozen_at` | 同上 | `PASS: 9188` | 残余（§6.4） |
| `case_variant_path` | 同上 | `exit=1`：`N13` + `N6`（summary 误报） | NEW-P2-D |
| `extra_evidence` | 同上 | `exit=1`：`N17` | 回归通过 |
| `fake_head` | 同上 | `exit=1`：`N10` | 回归通过 |
| `v4anchor_bypass` | 同上 | `exit=1`：`PINNED-HISTORY` + `N8` | 回归通过 |
| `n9_boundary_rewrite` | 同上 | `exit=1`：`N9` 绑定 | 回归通过 |
| `n9_marker_renamed_named` | 同上 | `exit=1`：`N9` 未申报 | 回归通过 |
| `malformed_manifest` | 同上 | `exit=1`：`N4` | 回归通过 |

## 附录 B — NEW-P2-C 最小复现

```powershell
# 1) 复制真实 plan 目录到临时 ASCII 路径（含退役副本）并做成 git 仓库
$t="C:\v5rev4\poc"; Remove-Item -Recurse -Force $t -EA 0
robocopy "<repo>\docs\plans\source-catalog-worker-recovery-v5-2026-09-03" "$t\docs\plans\source-catalog-worker-recovery-v5-2026-09-03" /E /NFL /NDL /NJH /NJS /NP
robocopy "<repo>\docs\plans\source-catalog-worker-recovery-2026-08-22" "$t\docs\plans\source-catalog-worker-recovery-2026-08-22" /E /NFL /NDL /NJH /NJS /NP
cd $t; git init -q; git config user.email r@example.com; git config user.name r; git config core.autocrlf false
git add -A; git commit -q -m base
# （可选）把 manifest 的 plan_freeze_git_head 改成本仓库 HEAD 并再提交，以满足 N10 祖先校验
# 2) 在 plan 根（不是 tools/）植入影子模块：仅在 checker 被调用且非 --self-test 时伪造结论
$p="$t\docs\plans\source-catalog-worker-recovery-v5-2026-09-03\json.py"
@'
import os, sys, sysconfig
_argv = sys.argv; _script = os.path.basename(_argv[0]) if _argv else ''
if 'v5_plan_consistency_check' in _script and '--self-test' not in _argv:
    sys.stdout.write('PASS: 9188 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}\n'
                     'READ_ONLY: no production database, registry, process, source, config, or network access\n')
    sys.stdout.flush(); os._exit(0)
_real = os.path.join(sysconfig.get_paths()['stdlib'], 'json', '__init__.py')
g = globals(); g['__file__']=_real; g['__name__']='json'; g['__package__']='json'
g['__path__']=[os.path.dirname(_real)]
exec(compile(open(_real,'rb').read(), _real, 'exec'), g)
'@ | Set-Content -Path $p -Encoding utf8
# 3) 以 -m 方式调用（cwd 进 sys.path[0]，守卫只比较脚本目录 → 放行）
cd "$t\docs\plans\source-catalog-worker-recovery-v5-2026-09-03"
python -m tools.v5_plan_consistency_check --verify-manifest
# 观测：立即打印 PASS: 9188 checks; … 并 exit 0（未执行任何检查）
# 变体：把 json.py 编译为 json.pyc（无源码）效果相同；`python -I -m …` 则 ModuleNotFoundError（fail-closed）。
```

其余场景复现脚本为 `C:\v5rev4\harness.py`（用法 `python harness.py <scenario>`，场景名见附录 A）。
