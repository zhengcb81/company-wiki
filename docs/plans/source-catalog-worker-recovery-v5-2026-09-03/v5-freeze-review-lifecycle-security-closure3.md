# V5 冻结独立复审（生命周期 / 安全轴）— 第四轮关闭复核（V5-2.3）

- 审查者：independent lifecycle/security reviewer（非作者，未参与任何 V5 产出）
- 复核对象：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03/` 的 V5-2.3 整改冻结
- 状态锚点：`git rev-parse HEAD` = `89c0862d9a8b0fc9cc1edb0e243aa6aa39845b40`（`fcap` == `origin/master`；本地 `master` 仍为 `109a1a6`，非本次对象）；上一轮 `9418e72`
- 日期（UTC）：2026-09-09，只读窗口约 `21:26Z – 21:36Z`
- 环境：Windows + PowerShell 7；Python 3.13.9；jsonschema 4.26.0；NTFS
- 方法：不采信记录自述；所有结论自行复算；作者工具仅作为被检查对象；变异/守卫实验全部在 `%TEMP%` 副本上执行；仓库内只新增本文件。

## 0. 轴结论

**verdict: `accepted`**

- 上一轮唯一开放项 **LIF-P2-10 已 CLOSED**：记录 §6.8 改引「合同 §6.2 的 `reviews/` 行（合同文本第 91 行）」，我实测合同第 91 行确为「导入审查记录 | `reviews/`（3 份）| 历史；不改字节」，全目录已无「§88（reviews 行）」这类失效主张。
- V5-2.3 新增的两项诚实披露（记录 §6.9 守卫边界、§8 `V5-SET-GOVERNING` 恒真标注）**准确且充分**，并由我独立实验证实。
- 新生命周期属性（启动守卫）**按文档生效**：`python <checker>`（无 `-I`）→ rc 1 + 守卫消息；`python -I <checker>` → 172 B / `5e60611c…` / 与冻结产物逐字节相同。我另测了 5 种调用形态（相对、绝对、`./`、裸文件名、`tools\.\`、`tools\..\tools\`），守卫全部触发；未发现绕过。
- 任务 2 的全部独立复验通过（51/51、产物字节、9188、17/32+4+2、HEAD blob 等值、PINNED-HISTORY 6/6、`boundary_record` 绑定、零写盘、无 `__pycache__`）。
- **本轮无新发现**（P0/P1/P2 均为 0）。

## 1. 判定表

| 项 | 判定 | 证据（命令 + 实测输出） |
|---|---|---|
| **LIF-P2-10** 引用行号 | **CLOSED** | `Select-String v5-version-contract.md -Pattern '活动，可更新\|历史；不改字节'` → `line 88: …活动，可更新`、`line 91: \| 导入审查记录 \| reviews/（3 份） \| 历史；不改字节 \|`；`v5-freeze-record.md:123` 现写「合同 §6.2 的 `reviews/` 行（合同文本第 91 行）规定「历史；不改字节」」；全目录 grep `§88\|§91\|reviews 行` 仅剩（a）`tools/v5_version_reference_scan.py:12,46` 的「contract §88」——指**活动文档行**，正确；（b）我自己的历史审查记录在引述旧缺陷。**记录/边界/合同内已无失效引用** |
| 启动守卫（新生命周期属性） | **成立** | 无 `-I`：`python <checker>` / 绝对路径 / `.\tools\…` / 裸文件名（cwd=tools）/ `tools\.\…` / `tools\..\tools\…` → 全部 `rc=1`，stderr `FAIL: run with an isolated interpreter - python -I <checker>. / The script directory on sys.path[0] would allow stdlib shadowing.`；`python -I <checker>` → `rc=0`、172 B、`sha=5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83`、与 `plan_freeze_check.v5.txt` **逐字节相同** |
| 记录 §6.9（守卫边界披露） | **准确且充分** | 实测：`runpy.run_path(checker, run_name="__main__")` 包装脚本（`tools/` 不在 `sys.path`）→ `rc=0`、输出 `PASS: 7720 checks; …`，即**守卫不覆盖包装调用**，与 §6.9「若有人用另一个解释器包装脚本运行，防御不覆盖」一致；反向实测：包装脚本若 `sys.path.insert(0, tools/)` → `SystemExit 1`（守卫触发），且直接 `sys.path[0]=tools/` 后 `import` 该模块亦触发守卫——守卫覆盖**略多于**其自述，披露不夸大 |
| 记录 §8 `V5-SET-GOVERNING` 恒真标注 | **准确（有一处可更精确，非缺陷）** | 代码：`check(base, tuple(ctx.governing) == GOVERNING and len(GOVERNING) == EXPECTED_GOVERNING and len(set(ctx.governing)) == EXPECTED_GOVERNING, "V5-SET-GOVERNING", …)` + 随后对三个治理件逐个 `(ctx.root/rel).is_file()`。记录写「断言等于预期三元组且三个文件存在；计数 conjunct 本身恒真，仅作一致性声明——如实标注，不声称它本身是判据」：**属实**（计数 conjunct 为常量比较）。可更精确处：真实 `Ctx` 由 `GOVERNING` 构造，故三元组/去重两个 conjunct 同样恒真，真正有牙齿的是三个 `is_file()`；记录已明示「不声称它本身是判据」，故不构成虚假陈述 |
| 任务 2 独立复验 | **全部通过** | 见 §2 |
| `V5-TOOLS-EXACT` / `-I` 链路（上轮 NEW-P1-1 根因） | **仍闭合** | 代码 281–287 行改为 `rglob("*") + is_file()`（枚举 `tools/` 下**全部文件**，仅豁免 `__pycache__`）；证据工具子进程（338 行）与 N8 重跑（515 行）均带 `-I`；manifest `pre_freeze_check.command` 与 schema `const` 均为 `python -I …/v5_plan_consistency_check.py`；自测 `V5-TOOLS-EXACT.py`/`.pyc`、`GUARD`/`GUARD-I` 全 PASS |
| N10 改比 HEAD（上轮 SQL-P1-2） | **仍闭合** | 代码改为 `git ls-tree -r HEAD -- <rels>`（解析 `fields[2]`）与 `hash-object --stdin-paths` 比对；自测新增 `N10.3`（提交后改写并 `git add`）被拒；我用同语义独立复算真实树：`checked=52 missing=none mismatch=none` |

## 2. 独立复验（任务 2）

```
# 1) 51/51 冻结项（自建脚本）
frozen entries=51 hash+size_ok=51 bad=0；reparse=none；inside retired dir=none
equivalence recount: {"crlf_only":17,"unproven_new_baseline":10,"v4_exact":21,"v5_own":3}

# 2) 预冻结产物（python -I，raw bytes 捕获）
DEFAULT rc=0 bytes=172 sha=5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83 CR=0 LF=2
PASS: 7720 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}
artifact_byte_identical=True

# 3) --verify-manifest（python -I）
PASS: 9188 checks; … (rc=0, 5.3 s)

# 4) --self-test（python -I）
SELF-TEST: 17 cases / 32 mutations + 4 default-mode checks + 2 guard checks; failures=none (rc=0, 78.8 s)

# 5) git blob 等值（HEAD 89c0862，manifest + 51，ls-tree-HEAD 语义）
checked=52 missing=none mismatch=none

# 6) PINNED-HISTORY 6/6（从源码提取钉值后自行重算）
baseline/history/{plan_manifest.v3.json, plan_manifest.v4.json, plan_review_revision.v4.md,
progress.v4.md, v4-freeze-integrity-incident-2026-09-03.md} + baseline/investigation/worker-investigation-2026-08-20.md
→ 6/6 match=True

# 7) manifest 绑定
capture_manifest / investigation_source / supersedes v4,v3 / evidence ×2 / evidence_tools ×2 /
boundary_record(69db267e… 与文件字节相符) / pre_freeze artifact / self_exclusion → 全 True；
plan_freeze_git_head = 9418e725929c6b7879b6955ded8eff9ae5887638（N10 断言为 HEAD 祖先且含语料）

# 8) 边界处置摘要（自建算法）
NON_AUTHORITATIVE；declared=(38, da927ee29497…) == measured=(38, da927ee29497…)

# 9) 记录 §1 的 8 个哈希/字节断言 → 8/8 match=True

# 10) 只读性（90 文件：相对路径+字节数+mtime+sha256）
before=90 after=90 ADDED:(none) REMOVED:(none) CHANGED:(none)
pycache_baseline_plan=False pycache_tools=False *.pyc/*.tmp=0
v5_version_reference_scan.py --check / v5_equivalence_check.py --check（均带 -I）→ rc=0 CHECK OK
```

## 3. 观察（非发现，不影响 verdict）

1. 记录 §8 的 P2 表不再单列「§88 → §91 引用错位」一行（V5-2.2 的那行被移除而非改写）。实质修复在 §6.8，且全目录无失效主张，故不构成缺陷；若追求台账完整，可补一行「引用已改为 §6.2 `reviews/` 行（第 91 行）」。
2. 守卫依赖 `sys.path[0]` 与 `__file__` 具有相同文本形态。本机 Python 3.13/Windows 下二者均被规范化为绝对路径（实测裸文件名、`./`、`tools\.\`、`tools\..\tools\` 一致），故判定稳健；**其他平台/解释器版本**应在使用前重跑本复核的 §1「启动守卫」一行。
3. 冻结窗口内无并发写入者（90 文件快照前后零变化），与上一轮观测不同——本轮无第三方改写干扰。

## 4. 复核局限

1. 未创建持久 Git 仓库；N10 的「已跟踪但被改写 / 改写并暂存」两个分支由代码路径 + 自测 N10.2/N10.3 证明，我未在临时仓库中重复提交实验。
2. 未做进程级写事件审计；「只读」= 可观测状态无变化。
3. 未评估 SQL/性能与测试/DAG 轴；仅确认与本轴相关的新 P1（父进程 import 劫持、N10 索引退化）确实闭合。
4. 守卫的跨平台行为未实测（见 §3.2）。

**审查者声明**：本复核只读，除本文件外未在仓库内创建/修改/删除任何文件；未 `git add/commit/push`；未触碰 worker、数据库、计划任务或其他仓库。本结论只绑定规划文档冻结的生命周期/安全面，不构成实施授权。
