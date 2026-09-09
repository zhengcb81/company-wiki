# V5-2.4 冻结五审（测试 / DAG 轴）— 四轮 3 条 P2 关闭裁定

审查者：独立审查代理（测试/DAG 轴；未参与本计划任何文档或工具的编写）
复审对象：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03`，V5-2.4 冻结提交（仓库 `HEAD 4f4dea1`）
被复审的四轮结论：`v5-freeze-review-test-dag-closure3.md`（NEW-P2-C `-m` 绕过守卫；NEW-P2-D N6 汇总误报；NEW-P2-E 记录 §6.9 未提 `-m`）
方法：不采信 `v5-freeze-record.md` §8 的整改声明；重跑四轮公开配方并针对新守卫（要求 `sys.flags.isolated`）构造新对抗。破坏性试验只在 `C:\v5rev5`、`C:\v5rev4` 临时副本；真实冻结树只读。
环境：Windows + PowerShell 7，Python 3.13.9，jsonschema 4.26.0。

## 结论

**axis verdict: `accepted`**

四轮 3 条 P2 **全部 CLOSED**，本轮**未发现新的 P0/P1/P2**。守卫现要求 `sys.flags.isolated`（并保留 `sys.path[0]` 比对），`python -m tools.<checker>`、`PYTHONPATH` 注入、`runpy.run_path`、`sitecustomize`（脚本目录与 cwd 两种植入）、相对路径与普通脚本调用六种形态全部 `exit=1` 并给出守卫信息，**无任何伪造输出**；带 `-I` 时所有 `tools/` 植入（`.py`/`.pyc`/`.pyd`/`sitecustomize.py`）均被 `V5-TOOLS-EXACT` 全文件枚举拒绝。N6 的汇总比较已门控在"声明集 == 冻结集"上，路径错配现在只报 `N13`。记录 §6.9 明确列出三种调用形态与平台前提，§8 P2 台账列出 NEW-P2-C/D/E 且处置与实测一致。冻结产物完全自洽：51/51 哈希、`PINNED-HISTORY` 6/6、manifest+51 的 HEAD blob 全等、产物 172B/0CR/`5e60611c…`、`--verify-manifest` 9188 rc 0、自测 17 例/32 变异+4 默认检查+3 守卫检查全拒、全部回归场景仍被拒。剩余仅记录已声明的三项残余（§6.3 副本判据边界、§6.4 `frozen_at` 与"新提交"类、§6.9 攻击者自控包装脚本），不构成 checker 缺陷。

## 1. 逐条裁定表

| ID | 裁定 | 证据（命令 + 观测） | 说明 |
|---|---|---|---|
| NEW-P2-C（`python -m` 绕过守卫） | **CLOSED** | ① `harness.py module_plant_py`（`python -m tools.v5_plan_consistency_check --verify-manifest`，cwd=plan 根，植入 `<plan>/json.py`）→ `exit=1 elapsed=0.1s`，`FAIL: run with an isolated interpreter - \`python -I <checker>\`.` + `Without -I, sys.path[0] (script dir or cwd under -m) can shadow the stdlib.`，**无 `PASS:` 输出**；② `module_plant_pyc`（植入 `<plan>/json.pyc`）→ 同样 `exit=1` 守卫信息；③ `module_pythonpath`（`PYTHONPATH=<plan>` + `-m`）→ `exit=1` 守卫；④ `runpy_plant`（`python -c "import runpy; runpy.run_path('<checker>', run_name='__main__')"` + 植入 `tools/json.py`）→ `exit=1` 守卫；⑤ `sitecustomize_script`（植入 `tools/sitecustomize.py`+`tools/json.py`，普通脚本调用）→ `exit=1` 守卫，且输出中**无 `SITECUSTOMIZE_RAN`**（守卫先于任何 site 注入执行）；⑥ `sitecustomize_cwd`（植入 `<plan>/sitecustomize.py`+`<plan>/json.py`，`-m` 调用）→ `exit=1` 守卫，同样无 `SITECUSTOMIZE_RAN`；⑦ `isolated_module`（`python -I -m …`）→ `ModuleNotFoundError` `exit=1`（fail-closed）；⑧ 真实树 `python -I … --verify-manifest` → `PASS: 9188 checks` `exit=0`。 | 守卫代码：`if not getattr(_sys.flags, "isolated", 0) or (_FIRST and _FIRST == _HERE_DIR):`（checker 第 36 行），只依赖内建 `sys` |
| NEW-P2-D（N6 汇总误报） | **CLOSED** | `harness.py case_variant_path`（把 `baseline/plan/README.md` 的声明路径改为 `Readme.md`）→ `exit=1`，**仅** `N13: missing=['baseline/plan/README.md'] extra=['baseline/plan/Readme.md']`，`after 9183 checks`；对照四轮同场景曾同时报 `N6: equivalence_summary … != recomputed …`。 | 代码：`if set(declared) == expected:` 门控后才比较 `equivalence_summary`（checker 第 443 行起） |
| NEW-P2-E（§6.9 未提 `-m`） | **CLOSED** | `git diff 89c0862..HEAD -- v5-freeze-boundary.md`：§6.9/§6 现写「守卫覆盖 `python <script>`、相对路径与 `python -m tools.<checker>` 三种形态；其它平台/解释器需重跑 `GUARD*` 自测确认」，并把 cwd 与 `.pyc`/`<plan>/json.py` 植入写入理由段；§8 P2 台账新增三行：`NEW-P2-C → D17（要求 sys.flags.isolated；自测 GUARD-M）`、`NEW-P2-D → 仅当声明集等于冻结集时才比较 equivalence_summary`、`NEW-P2-E → §6.9 明确三种调用形态与平台前提`。 | 与实测一致；`runpy` 括注偏保守（实测被守卫拒绝），不影响准确性 |
| 残余：N9 无标记/不改名副本 | NOT CLOSED（已声明 §6.3） | `harness.py n9_unnamed_extra` → `PASS: 9188`。 | 记录 §6.3 已如实声明 |
| 残余：副本移出 `docs/plans/` | NOT CLOSED（已声明 §6.3） | `harness.py n9_outside_plans_synced` → `PASS: 9135`。 | 同上 |
| 残余：`frozen_at` 无锚 | NOT CLOSED（已声明 §6.4） | `harness.py fake_frozen_at` → `PASS: 9188`。 | 同上 |
| 回归：v4 锚 | **CLOSED** | `v5rev4\harness.py v4anchor_bypass` → `exit=1`：`PINNED-HISTORY … expected c34b849475…, got 25c2a317…` + `N8`。 | 无回归 |
| 回归：N9 载荷绑定 / 具名改名 | **CLOSED** | `n9_boundary_rewrite` → `exit=1`：`N9: manifest does not bind v5-freeze-boundary.md bytes`；`n9_marker_renamed_named` → `exit=1`：`N9: retired plan copy not declared …`、`N9: declared 0 retired dirs but found 1`。 | 无回归 |
| 回归：`evidence_tools` / `plan_freeze_git_head` / 畸形 manifest | **CLOSED** | `extra_evidence` → `N17`；`fake_head` → `N10: … not an ancestor of HEAD containing the corpus`；`malformed_manifest` → `N4`。 | 无回归 |
| 回归：`tools/` 全文件枚举 | **CLOSED** | `pyd_plant`（`tools/json.pyd`）→ `V5-TOOLS-EXACT … found ['tools/json.pyd', …]`；`tools_extra_pyc` → `found ['tools/extra.pyc', …]`；`sitecustomize_plant` → `found ['tools/sitecustomize.py', …]`；`hijack_py_isolated`/`hijack_pyc_isolated` → 同上；`hijack_pythonpath`（`-I` + `PYTHONPATH`）→ 同上。 | 无回归 |
| 回归：普通脚本 / `-m` 调用 | **CLOSED** | `hijack_py_noisolate`（`python <checker>` + 植入）→ `exit=1 elapsed=0.1s` 守卫；`hijack_module_mode`（v5rev4 的四轮配方，`-m` + `<plan>/json.py`）→ `exit=1 elapsed=0.1s` 守卫（四轮时为伪造 PASS）。 | 无回归 |

## 2. 新增 findings

**无。** 本轮未发现 P0/P1/P2 级新问题。观察（非 finding）：
- `python -E -s -P <checker>` 与 `python -I -m tools.<checker>` 均被拒绝（前者因 `isolated` 为假，后者因模块不可达），属保守 fail-closed；文档化命令 `python -I <checker>` 与 manifest `pre_freeze_check.command`、schema `const` 一致。
- 守卫与 `V5-TOOLS-EXACT` 的覆盖边界仍以记录 §6.3/§6.4/§6.9 声明的残余为准（攻击者自控的包装脚本、`docs/plans/` 之外的副本、`frozen_at` 声明值、新提交类）。

## 3. 独立复算与再验证（全部通过）

| 项目 | 命令 | 观测 |
|---|---|---|
| 51/51 冻结项哈希 | `python C:\v5rev5\verify_new.py` | `51-entry hash check: entries=51 mismatches=none` |
| 预冻结产物 | 同上 | `bytes=172 CR=0 sha=5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83 matches_manifest=True` |
| `PINNED-HISTORY` 6/6 | 同上 | `PINNED-HISTORY: 6/6 match` |
| 边界记录绑定 | 同上 | `boundary binding: manifest=5e939d4646d23350 file=5e939d4646d23350 match=True` |
| manifest+51 的 HEAD blob | 同上（`git ls-tree -r HEAD` + `hash-object --stdin-paths`） | `git blob equality: targets=52 missing=none mismatches=none` |
| coverage 独立复算 | 同上 | 8 项与 manifest `coverage_counts` 相等（115/315/18/140/29/60/44/105） |
| 隔离运行 | 真实树 `python -I …/v5_plan_consistency_check.py --verify-manifest` | `PASS: 9188 checks; …` `exit=0` |
| 自测 | 真实树 `python -I … --self-test` | `SELF-TEST: 17 cases / 32 mutations + 4 default-mode checks + 3 guard checks; failures=none`（含 `GUARD-M`），exit 0 |
| 产物哈希 | `Get-FileHash` | 与记录 §1 逐位一致：manifest `f9735eb8…`(14125)、schema `d7218d36…`(7327)、checker `b5b2da6c…`(58055)、boundary `5e939d46…`(7262)、生成器 `5ece62bc…`(6586)、inventory `72db3a1a…`(29973) |

## 4. 残余风险（均为记录已声明，非本轮 finding）

1. §6.3：无标记且不改名、或移出 `docs/plans/` 的副本不在 N9 判据范围内（`n9_unnamed_extra`/`n9_outside_plans_synced` 仍 PASS）。
2. §6.4：`frozen_at` 是声明值（`fake_frozen_at` 仍 PASS）；"改写 + 同步全部记录 + 改冻结内钉扎 + 新提交"类不可被树内检查拦截。
3. §6.9：攻击者自控的包装脚本/解释器不覆盖（调用方须遵守 `-I` 约定）。
4. 本轴未做内容级语义审查、未评估 Windows 权限拒绝路径、未编译合法 `.pyd`（`-I` 下 `tools/` 不在 `sys.path`，预期不可劫持；`V5-TOOLS-EXACT` 已覆盖其存在性）。

## 附录 A — 五审场景与结果（临时副本，均先 commit）

| 场景 | 调用方式 | 结果 | 判定 |
|---|---|---|---|
| `module_plant_py`（`<plan>/json.py`） | `python -m tools.v5_plan_consistency_check` | `exit=1`（0.1s）守卫，无伪造 PASS | **NEW-P2-C CLOSED** |
| `module_plant_pyc`（`<plan>/json.pyc`） | 同上 | `exit=1`（0.1s）守卫 | **CLOSED** |
| `module_pythonpath`（`PYTHONPATH=<plan>`） | 同上（cwd=repo） | `exit=1`（0.2s）守卫 | **CLOSED** |
| `runpy_plant`（`tools/json.py`） | `python -c "import runpy; runpy.run_path(...)"` | `exit=1`（0.2s）守卫 | **CLOSED** |
| `sitecustomize_script`（`tools/sitecustomize.py`+`tools/json.py`） | `python <checker>` | `exit=1`（0.1s）守卫，无 `SITECUSTOMIZE_RAN` | **CLOSED** |
| `sitecustomize_cwd`（`<plan>/sitecustomize.py`+`<plan>/json.py`） | `python -m …` | `exit=1`（0.2s）守卫，无 `SITECUSTOMIZE_RAN` | **CLOSED** |
| `isolated_module` | `python -I -m …` | `ModuleNotFoundError` `exit=1` | fail-closed |
| `control_isolated`（`tools/json.py`） | `python -I <checker>` | `exit=1`：`V5-TOOLS-EXACT` + `N8` | 无劫持 |
| `case_variant_path` | `python -I <checker>` | `exit=1`：仅 `N13` | **NEW-P2-D CLOSED** |
| `n9_unnamed_extra` | 同上 | `PASS: 9188` | 残余（§6.3） |
| `n9_outside_plans_synced` | 同上 | `PASS: 9135` | 残余（§6.3） |
| `fake_frozen_at` | 同上 | `PASS: 9188` | 残余（§6.4） |
| 回归：`v4anchor_bypass`/`extra_evidence`/`fake_head`/`n9_boundary_rewrite`/`n9_marker_renamed_named`/`malformed_manifest`/`pyd_plant`/`tools_extra_pyc`/`sitecustomize_plant`/`hijack_py_isolated`/`hijack_pyc_isolated`/`hijack_pythonpath`/`hijack_py_noisolate`/`hijack_module_mode` | 见各行 | 全部 `exit=1`，编码与四审一致 | 无回归 |

## 附录 B — 复现配方（NEW-P2-C 关闭验证，最小）

```powershell
# 1) 复制真实 plan 目录到临时 ASCII 路径（含退役副本）并做成 git 仓库
$t="C:\v5rev5\poc"; Remove-Item -Recurse -Force $t -EA 0
robocopy "<repo>\docs\plans\source-catalog-worker-recovery-v5-2026-09-03" "$t\docs\plans\source-catalog-worker-recovery-v5-2026-09-03" /E /NFL /NDL /NJH /NJS /NP
robocopy "<repo>\docs\plans\source-catalog-worker-recovery-2026-08-22" "$t\docs\plans\source-catalog-worker-recovery-2026-08-22" /E /NFL /NDL /NJH /NJS /NP
cd $t; git init -q; git config user.email r@example.com; git config user.name r; git config core.autocrlf false
git add -A; git commit -q -m base
# （可选）把 manifest 的 plan_freeze_git_head 改成本仓库 HEAD 并再提交，以满足 N10 祖先校验
# 2) 在 plan 根植入影子模块（四轮时该植入可伪造 PASS）
$p="$t\docs\plans\source-catalog-worker-recovery-v5-2026-09-03\json.py"
@'
import os, sys, sysconfig
sys.stdout.write('PASS: 9188 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}\n'
                 'READ_ONLY: no production database, registry, process, source, config, or network access\n')
sys.stdout.flush(); os._exit(0)
'@ | Set-Content -Path $p -Encoding utf8
# 3) 以 -m 方式调用：现在被守卫拒绝（V5-2.4）
cd "$t\docs\plans\source-catalog-worker-recovery-v5-2026-09-03"
python -m tools.v5_plan_consistency_check --verify-manifest
# 观测（V5-2.4）：exit 1 + "FAIL: run with an isolated interpreter - `python -I <checker>`."，
# 不再出现伪造的 PASS 行；`python -I -m …` 亦 fail-closed（ModuleNotFoundError）。
# 四审对照（V5-2.3）：同一命令曾输出 PASS: 9188 checks 并 exit 0。
```

其余场景复现脚本：`C:\v5rev5\harness.py`（五审新增场景）与 `C:\v5rev4\harness.py`（四审回归场景），用法 `python harness.py <scenario>`。
