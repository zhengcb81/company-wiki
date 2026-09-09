# V5 冻结独立复审（生命周期 / 安全轴）— 第三轮关闭复核（V5-2.2）

- 审查者：independent lifecycle/security reviewer（非作者，未参与任何 V5 产出）
- 复核对象：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03/` 的 V5-2.2 整改冻结
- 状态锚点：`git rev-parse HEAD` = `9418e725929c6b7879b6955ded8eff9ae5887638`；上一轮 `85044ed`；`fcap` == `origin/master` == `9418e72`（本地 `master` 仍为 `109a1a6`，非本次对象）
- 日期（UTC）：2026-09-09，只读窗口约 `21:15Z – 21:22Z`
- 环境：Windows + PowerShell 7；Python 3.13.9；jsonschema 4.26.0；`core.autocrlf=true`；NTFS
- 方法：**不采信记录自述**。所有结论自行复算；作者工具仅作为被检查对象；全部变异实验在 `%TEMP%` 副本上执行；仓库内只新增本文件。

## 0. 轴结论

**verdict: `accepted_with_findings`**

- 本轮核对的 **4 条开放项中 3 条 CLOSED**（LIF-P2-3、LIF-P2-7、LIF-P2-9），**1 条 CLOSED 且残留按设计如实声明**（LIF-P2-8：载荷锚定已修；两条规避路径现在被显式声明为判据边界，不再是静默缺口）。
- 上一轮已闭的 LIF-P2-1/P2-2/P2-4/P2-6 仍然成立；**LIF-P2-5 的实体理由仍成立，但其行号引用并未按记录自述改正**（见新发现 LIF-P2-10）。
- 任务 6 的独立复验全部通过：51/51 冻结项、预冻结产物 172 B / `5e60611c…` / 0 CR / 与隔离重跑逐字节相同、`--verify-manifest` 9188、`--self-test` 17 例/31 变异+3 默认模式检查、manifest+51 项在 HEAD 的 blob 等值（52/52）、PINNED-HISTORY 6/6、`boundary_record` 绑定、零写盘、无 `__pycache__`。
- **无 P0、无 P1、无阻断性 P2**。唯一未闭项是 1 条 P2 文档级引用错误（LIF-P2-10）。

## 1. 判定表

| 项 | 上轮 | 本轮判定 | 证据（命令 + 实测输出） |
|---|---|---|---|
| **LIF-P2-3** 合同 §3 计数与冻结证据不符 | PARTIAL | **CLOSED** | 自建范围+正则独立重算：`files 56 / v4 41 / v3 12 / old 8 / chk 10 / ids 30 / suffix {v1:12,v2:1,v4:14,v5:3} / schema_version ['1','2']` —— 与冻结证据 `v5-version-reference-inventory.json.totals` **逐项相同**；合同第 31 行 `- **41 份含 v4、12 份含 v3**；**8 份引用已退役旧目录**；**10 份引用旧 checker**；`、第 32 行 `$id 共 30 个…:v5=3…schema_version ∈ {1,2}` **完全一致** |
| **LIF-P2-7** 历史证据哈希无时点标注 | PARTIAL | **CLOSED** | `progress.md:7` 现为「…inventory.json `b7612e0f…`…——**这三个哈希是 V5-1 时点（提交 `2fbbe5e`）的值**，V5-2 冻结时证据已按 D4 重生成…」；另 `manifest.evidence` 绑定实测 True（两文件哈希相符） |
| **LIF-P2-8** N9 载荷未锚定 / 标记规避 / 目录外副本 | open | **CLOSED**（载荷锚定已修；两条残留按设计声明） | ① `E-SYNC`（改退役副本 + 同步改写申报摘要，即旧规避配方）→ `RED codes=['N9']  - N9: manifest does not bind v5-freeze-boundary.md bytes`；② `E-BR`（只改边界记录 file_count）→ 同 RED；③ `E-N6`（名字含 `source-catalog-worker-recovery` 的副本删光 3 个标记）→ `RED ['N9']`；④ `E-N6c`（不匹配名 + 保留标记）→ `RED ['N9']`；⑤ `E2`（改名但保留标记子串）→ `RED ['N9']`；⑥ `E-N7`（旧目录删标记 + 同步申报）→ `RED`（绑定失败）；⑦ `E-N6b`（不匹配名 + 删光标记）→ `GREEN`、`E-N8`（整份副本移出 `docs/plans/`）→ `GREEN`，**恰与边界记录 §5「判据边界」与记录 §6.3 的表述一致** |
| **LIF-P2-9** N2 子串误报 | open | **CLOSED** | 复跑原探针：`docs/plans/a/` 内放 `gate_dag.v4.json` → `[P-N2] GREEN checks=983 codes=[]`（N2 已改为 `docs/plans/<name>` 前缀匹配，代码 359–365 行） |
| **LIF-P2-1** 计数是观测值而非断言 | accepted | **accepted-with-reason（维持）** | `--verify-manifest` → `PASS: 9188 checks` rc 0（4.5 s，较上轮 12.8 s 下降）；记录 §2 明确唯一冻结断言是产物字节；我实测默认模式 stdout 172 B、sha `5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83`、与产物**逐字节相同**，N8 以 `-I` 隔离重跑比对 |
| **LIF-P2-2** N10 未跟踪静默跳过 | CLOSED | **仍 CLOSED** | 探针（`external=True`，树不在 git 仓库内，`ONLY={'N10'}`）→ `RED codes=['N10'] - cannot resolve the git repository root`；真实树 52 个对象 blob 等值（见 §3） |
| **LIF-P2-4** 活动文档旧目录引用不受覆盖 | accepted | **accepted-with-reason（维持）** | 记录 §6 第 5 条在列（`v5-freeze-record.md:114`） |
| **LIF-P2-5** `reviews/` 绝对个人路径 | accepted | **accepted-with-reason（实体）；引用未改正** | 记录 §6 第 8 条在列（`:117`），WONTFIX 理由（历史记录、不改字节）成立；**但引用的行号仍是 §88**，而合同第 88 行是「活动，可更新」行、`reviews/` 行在第 91 行 → 见 LIF-P2-10 |
| **LIF-P2-6** pre-commit 整仓 checkout 机制 | accepted | **accepted-with-reason（维持）** | 记录 §6 第 7 条在列（`:116`）；本窗口内未再观测到并发写入（87 文件快照前后零变化） |

## 2. 新发现

| ID | 级别 | 发现 | 复现配方与实测 | 要求修复 |
|---|---|---|---|---|
| **LIF-P2-10** | P2（文档） | 冻结记录把「`reviews/` 不改字节」这条合同规则引用成 **§88**，并在 §8 处置表声称已改；实测合同第 88 行是**活动文档行**（内容恰为「活动，可更新」，与引用内容相反），`reviews/` 规则在**第 91 行**。 | `Select-String -LiteralPath docs/plans/source-catalog-worker-recovery-v5-2026-09-03/v5-version-contract.md -Pattern 'reviews/\|活动，可更新'` → `line 88: \| v5 自有规划/记录 \| … \| 活动，可更新 \|`、`line 91: \| 导入审查记录 \| reviews/（3 份） \| 历史；不改字节 \|`；`v5-freeze-record.md:117` 写「合同 §88（`reviews/` 行）规定不改字节」、`:153` 写「本记录已改为 §88（`reviews/` 行）」。 | 把记录 `:117` 与 `:153` 的行号改为 **§91**（或直接写「合同 §6.2 `reviews/` 行」），并撤销「已改为 §88」这一不成立的自述。 |

> 说明：LIF-P2-8 的两条残留（不匹配名 + 删光标记的副本、`docs/plans/` 之外的副本）**不是新的静默缺口**——它们与边界记录 §5「判据边界（如实声明）」和记录 §6.3 的文字逐字对应。若未来要求覆盖，需要把判据从「兄弟目录启发式」改为「仓库全树 + 跨仓扫描」，那会与「不改 `reviews/`、不扫描其他计划目录」的现有约束冲突，属设计取舍而非本轮缺陷。

## 3. 独立复验（任务 6）

```
# 1) 51/51 冻结项（自建脚本，不调用作者工具）
frozen entries=51 hash+size_ok=51 bad=0
reparse components: none          entries resolving inside retired dir: none
equivalence recount: {"crlf_only":17,"unproven_new_baseline":10,"v4_exact":21,"v5_own":3}

# 2) 预冻结产物（raw bytes 捕获）
DEFAULT rc=0 bytes=172 sha=5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83 CR=0 LF=2
PASS: 7720 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}
artifact_byte_identical=True
--verify-manifest -> PASS: 9188 checks (rc=0)
--self-test       -> 17 cases / 31 mutations + 3 default-mode checks; failures=none (rc=0, 54.2 s)

# 3) git blob 等值（HEAD 9418e72，manifest + 51）
checked=52 missing=none mismatch=none

# 4) PINNED-HISTORY 6/6（从 checker 源码提取钉值后自行重算）
baseline/history/plan_manifest.v3.json / plan_manifest.v4.json / plan_review_revision.v4.md /
progress.v4.md / v4-freeze-integrity-incident-2026-09-03.md / baseline/investigation/worker-investigation-2026-08-20.md
→ 6/6 match=True

# 5) manifest 绑定逐项
capture_manifest True / investigation_source True / supersedes v4,v3 True /
evidence ×2 True / evidence_tools ×2 True / boundary_record v5-freeze-boundary.md True /
pre_freeze artifact True / self_exclusion True / plan_freeze_git_head=85044ed…

# 6) 边界处置摘要（自建算法复算）
disposition NON_AUTHORITATIVE；declared=(38, da927ee29497…) == measured=(38, da927ee29497…)

# 7) 记录 §1 的 8 个哈希/字节断言
plan_manifest.v5.json(14122) / plan_freeze_check.v5.txt(172) / plan_manifest.schema.v5.json(7324) /
tools/v5_plan_consistency_check.py(52485) / tools/v5_freeze_manifest_build.py(6577) /
v5-version-reference-inventory.json(30088) / v5-baseline-equivalence.json(2970) /
v5-freeze-boundary.md(6009)  → 8/8 match=True

# 8) 只读性（87 文件：相对路径 + 字节数 + mtime + sha256）
before=87 after=87 ADDED:(none) REMOVED:(none) CHANGED:(none)
pycache_baseline_plan=False pycache_tools=False *.pyc/*.tmp=0
v5_version_reference_scan.py --check -> rc=0 "CHECK OK: inventory .json and .md reproduce byte-for-byte"
v5_equivalence_check.py --check      -> rc=0 "CHECK OK: v5-baseline-equivalence.json reproduces byte-for-byte"
```

计数自洽性核对（供交叉验证）：默认模式 7710 → **7720**（+10 = `V5-SET-GOVERNING` 由 1 项改为 1+3 项 +3、`V5-TOOLS-EXACT` +1、`PINNED-HISTORY` +6）；`--verify-manifest` 9174 → **9188**（verify 侧新增 +4 = N9 `boundary_record` 绑定 +1、N17 工具集精确匹配 +1、N10 的 missing 清单 +1 与祖先/语料 +1）。

## 4. 复核局限

1. 未创建持久 Git 仓库；N10「已跟踪但被改写」分支由代码路径 + 自测 N10.2（临时仓库提交后改写）证明，我未在临时仓库中重复该提交实验。
2. 未做进程级写事件审计；「只读」= 可观测状态无变化。
3. 未评估 SQL/性能与测试/DAG 轴；仅核对与生命周期/安全相关的新 P1（`V5-TOOLS-EXACT` 与 `-I` 隔离）确实生效（`E-TOOLS` → `RED codes=['V5-TOOLS-EXACT']`）。

**审查者声明**：本复核只读，除本文件外未在仓库内创建/修改/删除任何文件；未 `git add/commit/push`；未触碰 worker、数据库、计划任务或其他仓库。本结论只绑定规划文档冻结的生命周期/安全面，不构成实施授权。
