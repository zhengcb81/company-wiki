# V5 冻结独立复审（生命周期 / 安全轴）— 关闭复核（V5-2.1）

- 审查者：independent lifecycle/security reviewer（非作者，未参与任何 V5 产出）
- 复核对象：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03/` 的 V5-2.1 整改冻结
- 状态锚点：`git rev-parse HEAD` = `85044ed8ced021eeb77565564e455274d0a2a5ad`；整改冻结提交 = `917b8d8eb49f11c302dea273196d9042a0735b85`；manifest `plan_freeze_git_head` = `454f632…`
- 日期（UTC）：2026-09-09，只读窗口约 `21:02Z – 21:12Z`
- 环境：Windows + PowerShell 7；Python 3.13.9；jsonschema 4.26.0；`core.autocrlf=true`；NTFS
- 方法：**不采信记录与 manifest 的任何自述**。所有结论由本审查者自行复算；作者工具仅作为被检查对象运行；全部变异实验在 `%TEMP%` 副本上执行，仓库内只新增本文件。

> 注：委派信息称「master HEAD 85044ed」。实测本地 `master` = `109a1a6`（落后 258 提交），`fcap` = `origin/master` = `85044ed`。本复核以 `85044ed`（即 `fcap`）为准。

## 0. 轴结论

**verdict: `accepted_with_findings`**

- 上一轮本轴两条 P1 **均真实关闭**：LIF-P1-1（N9 判据）与 LIF-P1-2（路径安全不变量）。我用**自己的配方**逐条复现：改名、翻转处置、未申报副本、目录内文件被改、删除处置文件、删除目录——全部 RED；junction 重定向 `baseline/plan` 与 `tools/`——全部 RED。
- 任务 4 的四项独立复验全部通过：51/51 哈希+字节数、预冻结产物 172 B / `8c01b9dc…` / 0 CR / 与本 checker 默认模式重跑逐字节相同、manifest+51 项在 `85044ed` 的 `HEAD:blob == hash-object`（52/52）、checker 与证据工具零写盘且无 `__pycache__`。
- 仍有 **1 条 P2 的整改为 PARTIAL 且记录声称已修**（合同 §3 计数与冻结证据不符），另 1 条 P2 PARTIAL（progress.md 历史哈希未加时点标注），并有 **2 条新 P2**（N9 候选枚举是标记启发式、可被删标记规避；N2 用全 manifest 子串匹配会误红）。无 P0、无 P1 遗留。

## 1. 逐条 finding 判定

| ID | 原级 | 判定 | 证据（命令 + 实测输出） | 说明 |
|---|---|---|---|---|
| **LIF-P1-1** N9 判据只判「路径存在 + 文件存在」，改名即静默失效 | P1 | **CLOSED** | 见 §2 实验表：`E2`（改名）`RED codes=['N9']`；`E4`（处置翻转为 AUTHORITATIVE）`RED codes=['N9']`；`E-N1`（未申报兄弟副本）`RED`；`E-N2`（旧目录内文件被改）`RED`（`declared inventory … != measured (38, 78f09f38…)`）；`E-N3`（删处置文件）`RED`；`E-N4`（删旧目录但声明仍在）`RED`（`declared 1 retired dirs but found 0`）；独立复算处置摘要 `count 38 / digest da927ee294978a2578d459e285bbd00f7e7abea87ae6e42a0294a588f9a8c81b` = 声明值 | 上一轮四条子缺陷（硬编码路径、不校验内容、不识别改名、冻结项可落入旧目录）逐条消除；冻结项落入检查改用 `resolve()`（`E9` 系列同时覆盖）。残留见 **LIF-P2-8** |
| **LIF-P1-2** v5 丢弃 v4 的 `MANIFEST-PATH-SAFETY`（resolve 包含 + 无 reparse） | P1 | **CLOSED** | `E9`：把 `baseline/plan` 换成指向外部目录的 junction → `RED codes=['V5-PATH-SAFETY']`，逐条报 `frozen entry resolves outside the plan directory` 与 `traverses a symlink/reparse point … -> [...\baseline\plan]`；`E9b`：junction 掉 `tools/`（治理件自身）→ `RED codes=['V5-PATH-SAFETY']`；`E9c`：`baseline/plan/nested/extra.md` → `RED codes=['V5-SET-NESTED','V5-SET-IMPORTED','V5-SET-TOTAL','N13','N7']` | 计数自洽：默认模式 7658→7710 净 +52 = 移除旧 N9 边界臂 −52 + `V5-SET-NESTED` +1 + `V5-PATH-SAFETY` 2×51=102 + 第二处 `__pycache__` 断言 +1 |
| **LIF-P2-1** `--verify-manifest` 8866/8867 计数 | P2 | **accepted-with-reason** | 实测 `--verify-manifest` → `PASS: 9174 checks; {…}`（rc 0）；记录 §2 已把计数降级为「运行环境相关的观测值，不是冻结断言」，并声明唯一冻结断言是产物字节；我实测默认模式 stdout 172 B、sha `8c01b9dc011bda445fd6d055812105ff535205371b8dbf8e66d73a38ecd6197f`、与本 checker 重跑**逐字节相同**，且 N8 在真实树上执行该逐字节比对 | 处置诚实：不再声称计数是断言，且 9174 可复现 |
| **LIF-P2-2** N10 未跟踪时静默跳过 | P2 | **CLOSED** | 代码：`if tracked.returncode != 0: check(base, False, "N10", "not tracked at HEAD, so immutability is unverifiable")`；`if repo_root is None: check(base, False, "N10", "cannot resolve the git repository root")`。实测探针（`external=True`，树不在 git 仓库内，`ONLY={'N10'}`）→ `RED codes=['N10']  - N10: cannot resolve the git repository root`。真实树上 52 个对象（manifest + 51）逐一比对通过 | 已由「静默跳过」改为 fail-closed，并扩展到 51 项冻结集 |
| **LIF-P2-3** 合同 §3 计数与冻结证据不符 | P2 | **PARTIAL** | 我独立重算（`%TEMP%\v521_inv_recompute.py`，自建范围+正则）：`files_scanned 56 / baseline 54 / root 2 / with_v4 41 / with_v3 12 / old_dir 8 / old_checker 10 / ids 30 / :v5=3 / schema_version {1,2}` —— 与冻结证据 `v5-version-reference-inventory.json` **逐项相同**。但合同 §3 第 31–32 行写「**41** 份含 `v4`、**11** 份含 `v3`；**8** 份引用旧目录；**9** 份引用旧 checker」「`schema_version` ∈ {1,2,**3**}」 | 3 处不符：`v3` 11→应为 12、旧 checker 9→应为 10、`schema_version` {1,2,3}→证据为 {1,2}。原因可定位：新 `plan_manifest.schema.v5.json` 进入扫描范围后新增 `v3` 与 `plan_consistency_check.py` 两个 token（其 `supersedes` enum 与 `command` const），计数各 +1；作者把合同同步成了**上一轮（旧 schema）**的数值 |
| **LIF-P2-4** 活动文档旧目录引用不受覆盖 | P2 | **accepted-with-reason** | 记录 §6 第 5 条已列；D4 代价说明保留 | 权衡合理（活动文档可更新，纳入会使证据每次失效）；已显式披露 |
| **LIF-P2-5** `reviews/old-plan-retirement-inventory.json` 含绝对个人路径 | P2 | **accepted-with-reason** | 记录 §6 第 8 条已列；合同 §6.2 第 91 行确为「导入审查记录 \| `reviews/`（3 份）\| 历史；不改字节」；我复扫全目录：无凭据/令牌，仅用户名+盘符 | 理由可接受（改写历史记录字节会破坏「历史不改字节」原则；该文件不在 51 项、不在 `evidence`、不被任何哈希绑定）。**但记录引用的「合同 §88」实为活动文档行（第 88 行），`reviews/` 规则在第 91 行**——引用错位，建议改正 |
| **LIF-P2-6** 仍活跃的 pre-commit `staged_files_only` 机制 | P2 | **accepted-with-reason** | 记录 §6 第 7 条已列；`.githooks/pre-commit` 仍 `exec "$INSTALL_PYTHON" -mpre_commit hook-impl --config=.pre-commit-config.yaml`，`core.hooksPath=.githooks`；本复核窗口内再次实测到并发写入（`progress.md` mtime `21:03:09.7898161Z`、`findings.md` 亦被改写；51 项冻结文件零变化） | 该机制无法在「不改 hook/不改全局配置」的计划约束内消除；披露充分 |
| **LIF-P2-7** progress.md/rev4 引用旧证据哈希 | P2 | **PARTIAL** | 已实现 manifest `evidence` 绑定：我独立复算 `evidence v5-version-reference-inventory.json: True 30088`、`evidence v5-baseline-equivalence.json: True 2970`。但 `progress.md` 第 7 行仍写「inventory.json `b7612e0f…`、inventory.md `0240a85f…`、equivalence.json `79ac6ca4…`」**未带提交号/时点标注**（`v5-version-contract-review-rev4.md` 第 4 行已标注 `2fbbe5e`） | 我实测 `b7612e0f`/`0240a85f` 确实等于 `2fbbe5e` 处的字节，故当时为真；但现冻结值为 `150ae6a4…`/证据 .md 已重生成，读者按当前树核对会不匹配 |
| **LIF-P2-8**（新）N9 候选枚举是标记启发式，且处置载荷不在 manifest 绑定内 | P2 | **open** | `E-N6`：兄弟目录复制整份旧目录后**删除 3 个标记文件** → `GREEN codes=[]`（副本 35 文件，digest `9e06e473a779…`）；`E-N7`：旧目录删标记 + 清空声明 → `GREEN`；`E-N8`：整份副本放到 `docs/plans/` **之外** → `GREEN codes=[]`；反向探针：副本放在某个直接子目录内部（`some-other-plan/archive/old-copy/…`）→ 该子目录成为候选 → `RED codes=['N9']` | 边界记录 §5 的表述「改名、复制、新建副本都会触发 N9」**过宽**：只有「位于 `docs/plans/` 直接子目录（含其子树）且保留 `plan_consistency_check.py` / `gate_dag.v4.json` / `plan_manifest.v3.json` 之一」才触发。另：N9 的处置块位于 `v5-freeze-boundary.md`，该文件不在 51 项、不在 `evidence`、不在 `supersedes`，其完整性无 manifest 侧锚点（只能靠 N9 自身复算兜住） |
| **LIF-P2-9**（新）N2 用「退役目录名 ∈ 整份 manifest JSON」子串匹配 | P2 | **open** | 探针：在 `docs/plans/` 下建一个**名为 `a`** 的目录并放一个标记文件 → `RED codes=['N2']  - N2: manifest references a retired plan directory: ['a', 'source-catalog-worker-recovery-2026-08-22']` | 短名/常见名兄弟目录会让 N2 因无关原因永久红（误报，非绕过）。`plan_directory` 已由 schema `const` 封死，N2 的子串检查只是冗余加固；建议改为「manifest 的路径字段逐字段精确比对」而非全 JSON 子串 |

## 2. 实验表（全部在 `%TEMP%` 副本上执行；仓库只读）

harness：把 v5 树复制到 `%TEMP%`，用 `importlib` 载入**新** checker，构造 `Ctx(external=False)` 后依次调用 `v5_checks()` 与 `verify_manifest()`（与真实运行同代码路径）。`GREEN` = 无错误码。

| 实验 | 变异 | 结果 | 结论 |
|---|---|---|---|
| E1 | 基线（真实边界记录） | `GREEN checks=1622 codes=[]` | 对照 |
| E2 | **旧目录改名**（声明仍指旧路径） | `RED codes=['N9']` | LIF-P1-1 原名场景已闭 |
| E4 | 处置块 `NON_AUTHORITATIVE` → `AUTHORITATIVE` | `RED codes=['N9']` | 内容已校验 |
| E-N1 | 新增带标记的未申报兄弟副本 | `RED codes=['N9']` | 未申报即红 |
| E-N2 | 旧目录内改一个文件 | `RED codes=['N9']`（摘要不符） | 目录内容被锚定 |
| E-N3 | 删除边界记录 | `RED codes=['N9']` | 载荷缺失即红 |
| E-N4 | 删除旧目录但声明仍在 | `RED codes=['N9']`（declared 1 / found 0） | fail-closed |
| E-N5 | 删除旧目录并清空声明 | `GREEN` | 一致状态放行 |
| E-N6 | 兄弟副本删掉 3 个标记文件 | `GREEN` | **残留（LIF-P2-8）** |
| E-N7 | 旧目录删标记 + 清空声明 | `GREEN` | **残留（LIF-P2-8）** |
| E-N8 | 整份副本放到 `docs/plans/` 之外 | `GREEN` | 范围外（LIF-P2-8） |
| E9 | **junction 重定向 `baseline/plan`** | `RED codes=['V5-PATH-SAFETY']` | LIF-P1-2 已闭 |
| E9b | junction 重定向 `tools/` | `RED codes=['V5-PATH-SAFETY']` | 治理件自身亦覆盖 |
| E9c | `baseline/plan/nested/extra.md` | `RED codes=['V5-SET-NESTED','V5-SET-IMPORTED','V5-SET-TOTAL','N13','N7']` | 递归枚举 + 嵌套拒绝 |
| P-N10 | `external=True` 且树不在 git 仓库内 | `RED codes=['N10'] - cannot resolve the git repository root` | N10 fail-closed（LIF-P2-2） |
| P-N2 | 兄弟目录名为 `a` 且含标记 | `RED codes=['N2']` | 误报（LIF-P2-9） |

## 3. 独立复验（任务 4）

```
# 1) 51/51 冻结项（自建脚本，不调用作者工具）
frozen entries=51 hash+size_ok=51 bad=0
reparse components on frozen paths: none
frozen entries resolving inside retired dir: none
equivalence recount: {"crlf_only":17,"unproven_new_baseline":10,"v4_exact":21,"v5_own":3}
declared summary: {"crlf_only":17,"unproven_new_baseline":10,"v4_exact":21}
composition: {"imported":48,"self_excluded":1,"total":51,"v5_own_governing":3}

# 2) 预冻结产物（raw bytes 捕获，cmd 重定向）
DEFAULT rc=0 bytes=172 sha=8c01b9dc011bda445fd6d055812105ff535205371b8dbf8e66d73a38ecd6197f CR=0 LF=2
PASS: 7710 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}
byte_identical(重跑 stdout, plan_freeze_check.v5.txt) = True

# 3) git blob 等值（HEAD 85044ed）
HEAD: 85044ed8ced021eeb77565564e455274d0a2a5ad
checked=52 untracked=none mismatch=none
manifest HEAD:blob: 025402ecf22abd5d0e139b4515d53499d0438887

# 4) 只读性（84 文件快照：相对路径 + 字节数 + mtime + sha256）
before=84 after=84 ADDED: (none) REMOVED: (none)
CHANGED: progress.md mtime 20:28:28Z -> 21:03:09Z   ← 并发写入者，非冻结项
pycache_baseline_plan=False  pycache_tools=False  (*.pyc/*.tmp: none)
v5_version_reference_scan.py --check -> rc=0 "CHECK OK: inventory .json and .md reproduce byte-for-byte"
v5_equivalence_check.py --check      -> rc=0 "CHECK OK: v5-baseline-equivalence.json reproduces byte-for-byte"
--verify-manifest -> PASS: 9174 checks (rc=0, 12.8s)
--self-test       -> SELF-TEST: 17 cases / 27 mutations; failures=none (rc=0, 46.8s)

# 5) manifest 绑定逐项（自建脚本）
capture_manifest: True   investigation_source: True
supersedes v4: True      supersedes v3: True
evidence ×2: True        evidence_tools ×2: True
pre_freeze artifact: True    self_exclusion ok: True

# 6) 边界处置摘要（自建算法复算）
declared=(38, da927ee294978a2578d459e285bbd00f7e7abea87ae6e42a0294a588f9a8c81b)
measured=(38, da927ee294978a2578d459e285bbd00f7e7abea87ae6e42a0294a588f9a8c81b)  match=True

# 7) 记录 §1 的 8 个哈希断言
plan_manifest.v5.json / plan_freeze_check.v5.txt / plan_manifest.schema.v5.json /
tools/v5_plan_consistency_check.py / tools/v5_freeze_manifest_build.py /
v5-version-reference-inventory.json / v5-baseline-equivalence.json / v5-freeze-boundary.md
→ 8/8 match=True
```

`frozen_at` 与 HEAD 时序自洽：manifest `frozen_at=2026-09-09T20:59:18.525038Z`、文件 mtime `20:59:18.525735Z`；`917b8d8` 提交于 `21:00:23Z`，故生成时 HEAD 确为 `454f632`，与 `plan_freeze_git_head` 一致。

## 4. 记录 §7 / §8 处置诚实性

| 记录主张 | 独立判定 |
|---|---|
| §7 LIF-P1-1「枚举含标记目录 → 必须申报 → 复算 file_count/摘要 → 禁止冻结项落入」 | **属实**（代码逐条对应，实验全 RED）；唯一措辞问题在边界记录 §5「改名、复制、新建副本都会触发 N9」过宽（见 LIF-P2-8） |
| §7 LIF-P1-2「新增 V5-PATH-SAFETY：51 项 resolve + 逐段 reparse；默认模式新增 102 项」 | **属实**（102 项算术自洽，junction 实验 RED） |
| §8 LIF-P2-1 / P2-2 / P2-4 / P2-6 | **属实**（计数降级、fail-closed、§6.5、§6.7 均已落地并复现） |
| §8 LIF-P2-3「合同 §3 已按冻结证据更新」 | **不属实**（PARTIAL）：3 处数值与冻结证据不符（见上表） |
| §8 LIF-P2-7「证据由 manifest evidence 绑定；历史引用以提交号标注」 | **半属实**（PARTIAL）：绑定已落地；`progress.md:7` 未标注 |
| §8 LIF-P2-5「按设计保留（合同 §88：reviews/ 不改字节）」 | **理由成立、引用错位**：`reviews/` 规则在合同第 91 行，第 88 行是活动文档行 |
| §7 总述「9 条 P1 全部关闭」 | 本轴 2 条属实；其余 7 条属 SQL/测试轴，本复核不代判 |

**残余风险 §6 是否隐藏实质内容**：上一轮我指出的四项缺口现均已进入 §6（第 5、7、8 条）或 §7/§8；未列入的仅剩本复核新增的 LIF-P2-8（标记启发式与载荷未绑定）与 LIF-P2-9（N2 误报），建议补入 §6。

## 5. 复核局限

1. 未创建持久 Git 仓库，故「已跟踪但被改写」的 N10 分支由代码路径证明（`ls-files --error-unmatch` 失败即 red）+ 无仓库分支实测；未在临时仓库中提交后篡改来实测。
2. 未做进程级写事件审计；「只读」是「可观测状态无变化」。
3. 审查窗口内存在并发写入者（`progress.md`、`findings.md` 被第三方改写），冻结 51 项零变化已实测。
4. 未评估 SQL/性能与测试/DAG 轴，也不代判其余 7 条 P1。

**审查者声明**：本复核只读，除本文件外未在仓库内创建/修改/删除任何文件；未 `git add/commit/push`；未触碰 worker、数据库、计划任务或其他仓库。本结论只绑定规划文档冻结的生命周期/安全面，不构成实施授权。
