# V5 冻结独立审查 — 生命周期 / 安全轴

- 审查者：independent lifecycle/security reviewer（非作者，未参与任何 V5 产出）
- 审查对象：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03/` 的 V5-2 冻结（HEAD `454f632c046880980df5ce53bdaccdef88ca762a`，branch `fcap`）
- 日期（UTC）：2026-09-09，只读窗口 `20:44Z – 20:53Z`
- 环境：Windows + PowerShell 7；Python 3.13.9；jsonschema 4.26.0；`core.autocrlf=true`、`core.symlinks=false`、`core.ignorecase` 未设置（Windows 默认 true）；NTFS
- 方法：全部结论由本审查者**自行复算**，不采信任何文档中的哈希/计数/结论；作者提供的 checker/工具只作为**被检查对象**运行。所有写入仅落在 `%TEMP%`，仓库内只新增本文件。

## 0. 结论

**verdict: `accepted_with_findings`**

冻结的**核心可验证主张全部复现**：预冻结 stdout 字节哈希逐字节相同、0 个 CR、`reported_check_count` 一致、51/51 冻结项哈希与字节数一致、B1–B6 全部重现、N1–N17 自测 17/17、取代链指向真实 v3/v4 字节、manifest 自排除、`--check` 只读无写盘、旧目录状态与文档所述逐项一致。**没有 P0**：当前树中冻结集与 manifest 唯一、字节自洽、不可被静默指向已退役目录。

但存在 **2 个 P1**：N9 的机器实现只认字面路径且只校验「处置文件存在」，一次改名即可让全部 N9 检查消失；v5 生成线**丢掉了 v4 的路径安全不变量**（`MANIFEST-PATH-SAFETY` / reparse 遍历），已实测 junction 重定向可通过全部检查。二者都属「冻结保护壳存在缺口」，不影响当前字节，但必须在 P0/P1 全关的流程里关闭后才能作为实施输入。

## 1. Findings

| ID | Sev | Finding | Evidence（命令 + 实测输出，节选） | Required fix |
|---|---|---|---|---|
| LIF-P1-1 | P1 | N9 的机器判据是「硬编码路径存在 + 处置文件存在」，**不校验内容、不识别改名/移动**；退役目录改名后 104 项 N9 检查静默消失（PASS 无告警）。且该目录自带一整套 manifest 载体（`plan_manifest.v3.json` / `plan_manifest.schema.json` / `plan_consistency_check.py`），"非权威副本、不删除" 的处置因此缺少机器约束。 | 临时副本 harness（见 §A9）：`E2 rename retired dir on disk → [E2] checks=1263 codes=[]`（E1 基线 `checks=1367 codes=[]`；E3 删处置文件 → `codes=['N9','N9-DISPOSITION']`；E4 处置文件内容改为「退役目录才是权威」→ `codes=[]`）。目录自带 manifest：`plan_manifest.v3.json` 2861 B `d4bf559b…` ≠ 取代链 v3 `9ee84acd…`。 | ① 以「任何位于 v5 目录之外、含 `plan_manifest.*.json` 的目录」为判据枚举，而非单一字面路径；② 处置记录须带机器可验载荷（例如 `disposition: non_authoritative` + 退役目录库存 sha256），不能只判 `is_file()`；③ 把退役目录库存哈希写入 manifest 并在 N9 中比对。 |
| LIF-P1-2 | P1 | v5 checker **未实现任何 reparse / 路径包含检查**：基线 `plan_manifest_checks()`（含 `MANIFEST-PATH-SAFETY`：`candidate.resolve(strict=True).parent == ROOT` 且 `not has_reparse_component`）既未被调用也未被等价实现；N9-PARALLEL 只用字面 `ctx.old_dir not in path.parents`。v4 schema 的语义规则「…resolve beneath plan_directory **without symlink or reparse traversal**」在 v5 schema 的 `x-semantic-rules` 中已被删除，且 D1–D7 未记录此删除。 | `grep` 结果：v5 checker 仅 `Path(__file__).resolve()`（第 43 行），无 `reparse/is_symlink/st_file_attributes`；基线中 `has_reparse_component` 仅被 `plan_manifest_checks`（1589 行）使用，而 v5 `baseline_suite()` 不调用它。实测：把 `baseline/plan` 换成指向外部目录的 junction → `[E9] entries: 51 … codes: []`（全部检查通过）。 | ① 对 51 个冻结项（及 `.gitattributes`）补 `resolve().parent == 计划目录` + 逐段 reparse 检查，或在 D 表显式记录该 v4 不变量被移除并说明理由；② 让 N9-PARALLEL 用 `resolve()` 后的真实路径判断。 |
| LIF-P2-1 | P2 | HEAD 上提交的冻结记录与 commit message 写 `--verify-manifest → PASS: 8866 checks`，独立实测为 **8867**，差 1 项正是 N10 的 Git-tracking 分支（manifest 入库后才激活）。该数字在冻结提交状态下**不可复现**。 | `python …/v5_plan_consistency_check.py --verify-manifest` → `PASS: 8867 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}`（exit 0）。`git show 454f632 --stat` 与 commit body 写 8866；`git show HEAD:…/v5-freeze-record.md` 第 36 行写 8866。工作树中作者已自行修正为 8867（未提交）。 | 记录「计数随 manifest 是否被 Git 跟踪而变（8866 未跟踪 / 8867 已跟踪）」并提交修正；把该计数从「冻结断言」降级为「运行环境相关观测」。 |
| LIF-P2-2 | P2 | N10 的不可变性判定完全依赖 Git，且 manifest **未被跟踪时静默跳过**（无任何告警，仍打印 `PASS` + `read_only_confirmed: true`）；大小写改名在大小写敏感文件系统（Linux CI）上同样会使 `ls-files --error-unmatch` 失败而跳过。 | 代码路径：`if tracked.returncode == 0:` 内才 `check(...)`（checker 313–324 行）。实证：`--verify-manifest` 计数 8866→8867 恰为该分支的有无（见 LIF-P2-1）。已实测 `git hash-object` 用 `-C repo_root` 锚定、不受 cwd 影响（从计划目录/镜像目录运行均返回 `0150f4ea…`），故**不存在** cwd 绕过。 | fail-closed 或显式降级：输出 `IMMUTABILITY: UNCHECKED (manifest untracked)` 并让 manifest 记录 `immutability_checked`；或对 51 项冻结集也做 blob-vs-worktree 比对。 |
| LIF-P2-3 | P2 | 合同 §1/§3 的计数 bullet 在 D4 收窄证据范围后未同步：§3 写「44 份含 v4、14 份含 v3、11 份引用旧目录」、§1 写「29 个 `$id`…`:v5`=2」，冻结证据实测为 **41 / 11 / 8 / 30 / `:v5`=3**。D7 只改了同一节的「扫描范围」行。 | `python %TEMP%\v5_inv_check.py` → `files_with_v4: 41`、`files_with_v3: 11`、`files_referencing_old_dir: 8`、`distinct_ids: n=30`、`id_suffix_counts {'v1':12,'v2':1,'v4':14,'v5':3}`。 | 用 inventory `totals` 重生成这些 bullet，或标注为 rev2 时点值；`:v5`=3 的第三个是新增的 `plan-manifest:v5`，应显式说明。 |
| LIF-P2-4 | P2 | D4 把证据范围收窄为「冻结后不变的文件」，代价是**恰好排除了引用已退役目录最多的 4 份活动文档**（`README.md` 2 处、`task_plan.md` 1 处等），旧目录引用计数由 11 降为 8；这些引用现在没有任何机器检查覆盖。该权衡只在 D4 中说明，未进入 §6 残余风险。 | 冻结前工具版本（`git show 436ecd3:…/tools/v5_version_reference_scan.py`）范围确为「baseline/** (54) + v5 root planning documents (5)」=59，D4 理由属实；收窄后 `files_referencing_old_dir` 8 < 合同 §3 的 11。 | 把「活动文档中的旧目录引用不受证据/机器检查覆盖」写入 §6 残余风险；如需覆盖，另加一条只读、允许漂移的提示性扫描（不参与冻结哈希）。 |
| LIF-P2-5 | P2 | 跟踪在库文件中存在**绝对个人路径**（含用户名 `郑曾波`、`C:\` 盘符）：`reviews/old-plan-retirement-inventory.json` 的 `exact_target`/`preserved_v5`/`preserved_report` 三个字段。未发现任何凭据/令牌（见 §A11）。 | `grep -E '郑曾波\|C:\\\\Users'` → `reviews/old-plan-retirement-inventory.json:6-8` 三行绝对路径；`baseline/investigation/worker-investigation-2026-08-20.md` 内亦有历史绝对路径（该文件被 `investigation_source.sha256` 绑定，**不得修改**）。 | 对非冻结的 review 文件改为仓库相对路径（该文件不在任何哈希绑定集合内，改动安全）；在计划约定中禁止新产出写入绝对个人路径。 |
| LIF-P2-6 | P2 | 冻结记录 §6 残余风险**未列入**造成 v4 事故的机制，而该机制当前仍然活跃：`.githooks/pre-commit` 仍以 `core.hooksPath=.githooks` 调用 pre-commit（`staged_files_only` 整仓 checkout + patch 恢复），而 v5 目录现已全部被跟踪。审查期间实测到并发写入者。 | `git config --get core.hooksPath` → `.githooks`；`.githooks/pre-commit` → `exec "$INSTALL_PYTHON" -mpre_commit hook-impl --config=.pre-commit-config.yaml`。审查窗口内计划目录非冻结文件被改写：`v5-freeze-record.md` mtime `20:48:02.8096667Z`（8151→8373 B）、`task_plan.md` mtime `20:50:12.9404Z`；仓库根 `.ruff_cache/.pytest_cache` 于 `20:46` 被写。51 个冻结项在窗口内 sha/len/mtime **全部未变**。 | 在 §6 增列该机制；每份审查记录声明「审查窗口内无 commit/hook 触发」并要求作者在审查期间冻结提交；把 B1→B3 的快照窗口说明扩展为「跨审查窗口」。 |
| LIF-P2-7 | P2 | `progress.md` / `v5-version-contract-review-rev4.md` 引用的证据哈希（`b7612e0f…`、`0240a85f…`）指向 rev4 时点字节，冻结时证据已按 D4 重生成，现冻结值为 `b64b9e67…` / `7c074cee…`；按当前树复核会「不匹配」。 | `git cat-file blob 2fbbe5e:…/v5-version-reference-inventory.json` → sha256 `b7612e0f617f…`（与 rev4 审查记录一致，**当时为真**）；`454f632` 同路径 → `b64b9e67c011…`。 | 给这些哈希加时点标注（「rev4 @2fbbe5e」），避免被误读为当前冻结值。 |

### 1.1 逐项证据（完整命令与输出）

**LIF-P1-1**（N9 机器判据不足）— harness 逐条变异，每条都在 `%TEMP%` 的 v5 副本上执行，仓库只读：

```
python %TEMP%\v5_review_harness.py
[E1] checks=1367 entries=51 codes=[]                      # 基线（旧目录字面名 + 处置文件存在）
[E2] checks=1263 entries=51 codes=[]                      # 仅把退役目录改名，ctx.old_dir 仍为字面路径
[E3] checks=1367 entries=51 codes=['N9','N9-DISPOSITION'] # 对照：删处置文件 → 被拒
[E4] checks=1367 entries=51 codes=[]                      # 处置文件内容改为「退役目录才是权威」→ 仍通过
```
（E2 比 E1 少 104 项 = `v5_checks` 与 `verify_manifest` 各 52 项 N9 检查全部消失；目录本身仍是 38 文件的完整副本。）

退役目录自带 manifest 载体（`Get-ChildItem` + 结构比对）：
```
plan_manifest.v3.json  2861 B  d4bf559b65d2b4903087c787555e7cd19d4f6abc91d0a45576e95f36aaddeec9
plan_manifest.schema.json（const plan_revision v4 / plan_directory 旧目录）
plan_consistency_check.py 39110 B 72d65c8acd5f45a2…
baseline/history/plan_manifest.v3.json 2778 B 9ee84acd…（取代链与 IMMUTABLE_HISTORY_SHA256 的钉值）
```

**LIF-P1-2**（路径安全不变量丢失）：

```
python %TEMP%\v5_junction_probe.py
mklink rc: 0
entries: 51 baseline/plan is junction: True
resolved baseline/plan: C:\Users\…\Temp\v5junction_i8s24xjo\external_plan
checks: 1263
codes: []
```
即：48 个「冻结」文件已不在仓库树内，全部检查仍通过。v4 侧对照（`baseline/plan/plan_manifest.schema.json` 的 `x-semantic-rules`）：
```
"normative file paths are unique after Windows case-folding and resolve beneath
 plan_directory without symlink or reparse traversal"
```
v5 侧 `plan_manifest.schema.v5.json` 的 5 条 `x-semantic-rules` 中**没有**这一条（casefold 唯一性由 N13 保留，reparse 遍历没有替代）。

**LIF-P2-1**：
```
python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py --verify-manifest
PASS: 8867 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}
READ_ONLY: no production database, registry, process, source, config, or network access
exit=0
```
对照：`git show HEAD:…/v5-freeze-record.md | Select-String 8866` → 第 36 行 `8866`；`git show 454f632` commit body → `manifest verify 8866 checks`。

**LIF-P2-2**：`git -C <repo> hash-object` 在三种 cwd 下均返回 `0150f4eaf078928eb3dcbd448f9a2129447a1c17`（repo 根 / 计划目录 / 含同相对路径镜像的目录），证明 `-C repo_root` 已锚定、**无 cwd 绕过**；唯一缺口是 `ls-files --error-unmatch` 失败即整段跳过。

**LIF-P2-6**：并发写实测（`Get-ChildItem -Recurse -Force -File | ? LastWriteTimeUtc -gt now-45min`）：
```
.ruff_cache\0.15.18\6516895124640508795                 20:46:15Z
.pytest_cache\v\cache\nodeids                           20:46:50Z
…/v5-freeze-record.md                                   20:48:02.8096667Z
…/task_plan.md                                          20:50:12.9404Z
```
冻结集 51 项在同一窗口内零变化（§A3）。

## 2. 明确核验为「无问题」的项（含作者主张的独立证伪/证实）

| 项 | 独立结论 | 证据 |
|---|---|---|
| 预冻结 stdout 字节哈希 | **证实**：`88f407ae28477df99c8f1f6aa14242e040d3ff478dba390f79db528d1de8f083`，172 B，CR=0，LF=2 | §A1 |
| `plan_freeze_check.v5.txt` 与 stdout 同源 | **证实**：字节完全相同（Base64 相等） | §A2 |
| `reported_check_count` | **证实**：7658 = 实测 | §A1 |
| 51/51 冻结项 sha256+size | **证实**：51/51 一致；equivalence 复算 21/17/10 + 3 `v5_own` | §A4 |
| B4 `.gitattributes` 属性 | **证实**：204 行全部 `unset`（注意：必须用**仓库相对**或**绝对**路径；用 v5 目录相对路径会得到 `unspecified`，是误用） | §A5 |
| B5 旧目录状态 | **证实**：38 tracked / 38 on-disk / clean / mtime `2026-09-07T18:08:52.8971277Z` / 无 reparse / 与 51 项及 v5 全部 81 文件 **0/38** 字节重合 | §A6 |
| B6 HEAD 与产物 | **证实**：`454f632` 含全部冻结产物；`436ecd3` 时 v5 目录 74 个已跟踪文件，`454f632` 后 81 | §A7 |
| `frozen_at` / `plan_freeze_git_head` 可信 | **证实**：`436ecd3` 为冻结时 HEAD；`frozen_at` 与产物 mtime 相差 4.16 ms，由本机 FS 时间戳滞后墙钟 1.3 ms 解释（实测探针） | §A8 |
| `--self-test` 17/17 | **证实**：逐条 `SELF-TEST N<n> PASS`，汇总 `17/17 negative cases rejected` | §A9 |
| 只读性 | **证实**：81 文件 sha+len+mtime 三次运行前后完全一致；计划目录内无 `__pycache__`/`.pyc`/`.tmp`；两个证据工具 `--check` 只读 | §A3 |
| manifest 不能被静默指向旧目录 | **证实**：`plan_directory`/`investigation_source.path`/`capture_manifest.path` 均为 schema `const`；`pre_freeze_check.command` 被 N2+N8 拒绝（E7/E8 实测 `codes=['N2','N4']` / `['N2','N8']`）；`supersedes[].path` 虽自由但哈希必须匹配解析到的 history 文件 | §A9 |
| 取代链指向真实字节 | **证实**：v4 `c34b8494…`、v3 `9ee84acd…` 与 `baseline/history/` 实际字节一致；v3 钉值等于退役目录 v3 的 **LF 归一化**结果（纯 EOL 差异） | §A10 |
| 自排除 | **证实**：`self_exclusion` 正确、`plan_manifest.v5.json` 不在 `normative_files`、N10 含该断言 | §A10 |
| `.gitattributes` 不锁文件 | **证实**：文件自述「does not lock files」；Git 无文件锁属性；`-text -eol -filter -working-tree-encoding` 只关闭转换。它确实阻断了 v4 事故的 EOL 转换机制 | §A11 |
| 另一 checkout / Linux CI 的字节可复现性 | **证实**：51 项全部 `HEAD:blob == git hash-object <worktree>`，即提交字节 = 工作树字节；`-text` 下任何平台 checkout 均逐字节一致 | §A11 |
| 凭据/密钥 | **证实无**：全目录扫描只命中 schema 字段名/占位符（`contains_secret: const false`、`secret_scan_result: const "PASS_NO_SECRETS"`、测试 ID `GL-F09-EVIDSECRET`）与散文用词 | §A11 |
| GBK/控制台编码 | **未发现产出缺陷**：被怀疑非 UTF-8 的 `worker-investigation-2026-08-20.md` 实为**合法 UTF-8**（36300 B，`utf-8` 解码 OK，`gb18030` 解码失败）；checker 对 stdout 与全部 `subprocess` 均显式 `encoding="utf-8"`，并 `reconfigure(newline="\n")` | §A11 |
| 环境依赖的机器特定值 | **未发现**：冻结集与工具中无 hostname/MAC/temp 绝对路径；checker 只在 `--self-test` 使用 `tempfile.TemporaryDirectory()`（OS 临时目录） | §A11 |

## 3. 与 D1–D7 诚实性审计

| D | 声明 | 独立判定 |
|---|---|---|
| D1 | 历史哈希按布局解析，实测 `9ee84acd…` 等于钉值 | **成立**：基线 `IMMUTABLE_HISTORY_SHA256 = {"plan_manifest.v3.json": "9ee84acd…"}`；v5 内联实现改为在 `baseline/plan` 与 `baseline/history` 两处查找，语义等价且更宽。未记录的是：基线 `immutable_history_checks()` 被内联取代（等价）、`plan_manifest_checks()` 被整体弃用（见 LIF-P1-2）。 |
| D2 | 禁止字节码写入 | **成立且必要**：模块级 `sys.dont_write_bytecode = True`；三次运行后 `baseline/plan/__pycache__` 不存在、`tools/__pycache__` 不存在。 |
| D3 | 预冻结输出强制 LF | **成立**：`reconfigure(encoding="utf-8", newline="\n")`；产物 172 B、CR=0；生成器在含 CR 时中止。 |
| D4 | 证据范围收紧至 56 份 | **理由属实**（rev4 时范围确为 59，含 5 份活动文档），**但**：(a) 合同同节计数未同步（LIF-P2-3）；(b) 被排除的恰是引用旧目录最多的文档（LIF-P2-4）；(c) 该偏差**不削弱 N17 本身**——N17 只要求两个证据工具在 `evidence_tools[]` 中且哈希相符，与扫描范围无关；但它确实使「旧目录引用面」的证据不再完整。 |
| D5 | 生成器不入冻结集 | **成立**：`tools/v5_freeze_manifest_build.py` 既不在 51 项也不在 `evidence_tools[]`，其哈希仅出现在记录 §1（实测 `38137c46…` 相符）。代价：manifest 的**产出者**无任何绑定，只能靠 `--verify-manifest`/`--self-test` 自证——对当前 51 项字节成立。 |
| D6 | schema 路径正则放宽首位 `.` | **成立且不越界**：`^[A-Za-z0-9._][A-Za-z0-9._/-]*$` 仍禁止绝对路径/盘符/`~`/空白/非 ASCII；路径穿越片段（如 `..`）被 N13 的集合相等判据封死（实测 E5/E6 被拒）。 |
| D7 | 合同计数行更新 | **成立**：`git show 454f632 -- v5-version-contract.md` 显示 `59 份` 行被改为 `56 份` 并指向 `totals` + D4；**但只改了这一行**，同节 bullet 计数仍为旧值（LIF-P2-3）。 |

**残余风险 §6 是否隐藏实质内容**：5 条中第 2、3、5 条与本审查独立结论一致（旧目录未删未锁、未跟踪改写不可检、记录本身不在冻结集）。**未列入**的实质项：v4 路径安全不变量被删除（LIF-P1-2）、N9 判据只认字面路径（LIF-P1-1）、仍活跃的 pre-commit `staged_files_only` 机制（LIF-P2-6）、证据范围排除旧目录引用文档（LIF-P2-4）。这四项都可在本目录其他文档中间接读到（`v5-freeze-boundary.md` §2 提到 hook 机制与「本目录已被跟踪」，README 第 27–31 行提到旧目录复活），但**冻结记录本身**应显式列出。

## 4. 审查局限（不夸大结论）

1. 未创建任何临时 Git 仓库，因此 `git update-index --assume-unchanged` / `--skip-worktree` 的绕过与否**只由代码路径 + Git 管道语义推断**（`hash-object` 直读工作树文件、`ls-files --error-unmatch` 只判索引成员资格 → 二者均不构成绕过）；未做实测。
2. 未修改索引、未 commit/push，故无法实测「未跟踪状态下改写 manifest」；该结论来自代码条件分支 + 8866/8867 的计数差。
3. 未做进程级文件写事件审计（本次范围外）；「只读」结论是「可观测状态无变化」，不是「不可能有任何写」。
4. 审查窗口内存在并发写入者（LIF-P2-6），因此「稳定审查边界」在时间上依赖该窗口；冻结集 51 项在窗口内零变化已实测。
5. 未评估 SQL/性能与测试/DAG 轴。

---

# 附录 A：复现的边界测量

## A1. 预冻结 stdout 字节复现

```
cd <repo>
cmd /c "python docs\plans\source-catalog-worker-recovery-v5-2026-09-03\tools\v5_plan_consistency_check.py > %TEMP%\v5_default_stdout.bin 2> %TEMP%\v5_default_stderr.bin"
exit=0  elapsed_ms=2261
stdout_bytes=172
stdout_sha256=88f407ae28477df99c8f1f6aa14242e040d3ff478dba390f79db528d1de8f083
CR_count=0  LF_count=2
---stdout---
PASS: 7658 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}
READ_ONLY: no production database, registry, process, source, config, or network access
---stderr--- (empty)
```
与 `plan_manifest.v5.json.pre_freeze_check.stdout_sha256` **完全相同**；`reported_check_count=7658` 一致；无 CR。

## A2. 产物与 stdout 同源

```
[IO.File]::ReadAllBytes(stdout)  ==  [IO.File]::ReadAllBytes(plan_freeze_check.v5.txt)   → True
plan_freeze_check.v5.txt sha256 = 88f407ae28477df99c8f1f6aa14242e040d3ff478dba390f79db528d1de8f083
```

## A3. 只读性证明（快照 = 相对路径 + 字节数 + LastWriteTimeUtc + sha256，81 个文件）

```
before=81 after=81
ADDED: (none)   REMOVED: (none)
CHANGED (sha or len or mtime): (none)      # 默认模式运行后
# 再跑 --verify-manifest 与 --self-test 后重新快照：
before=81 after=81   ADDED: (none)  REMOVED: (none)  CHANGED: (none)
pycache under baseline/plan: False     pycache under tools: False
*.pyc / *.tmp under plan dir: (none)
```
证据工具单独 `--check`（只读、字节级）：
```
python …/tools/v5_version_reference_scan.py --check   → rc=0  "CHECK OK: inventory .json and .md reproduce byte-for-byte"
python …/tools/v5_equivalence_check.py --check        → rc=0  "CHECK OK: v5-baseline-equivalence.json reproduces byte-for-byte"
```
本审查自身写入：仅 `%TEMP%`（stdout 捕获文件、快照 JSON、三个只读分析脚本、`--self-test` 的 `tempfile` 目录），仓库内仅新增本文件。

## A4. B1/B3：51 项独立重算（`python %TEMP%\v5_b13_verify.py`）

```
frozen entries: 51  hash+size match: 51  mismatch: 0
any resolved path inside the retired dir: False
any symlink/junction among frozen entries: False
reparse components on frozen paths: none
equivalence recount: {"crlf_only":17,"unproven_new_baseline":10,"v4_exact":21,"v5_own":3}
declared equivalence_summary: {"crlf_only":17,"unproven_new_baseline":10,"v4_exact":21}
composition: {"imported":48,"self_excluded":1,"total":51,"v5_own_governing":3}  normative_file_count: 51
```

| # | path | size | sha256（前 16） | 判定 |
|---|---|---|---|---|
| 1 | `.gitattributes` | 172 | `88182b266065f970` | OK |
| 2 | `baseline/plan/acceptance_thresholds.md` | 23396 | `d6f3068498c8c6d8` | OK |
| 3 | `baseline/plan/agent_review_gates.md` | 33410 | `bbab56f39b7a9392` | OK |
| 4 | `baseline/plan/authorization_manifest.schema.json` | 43788 | `4c9458d6e3da59d2` | OK |
| 5 | `baseline/plan/authorization_revalidation_receipt.schema.json` | 4522 | `26b56990b29cddd1` | OK |
| 6 | `baseline/plan/bootstrap_verifier_manifest.schema.json` | 5553 | `768eab57571e3108` | OK |
| 7 | `baseline/plan/budget_reservation_bundle.schema.json` | 7399 | `44f39cb504a6e5c7` | OK |
| 8 | `baseline/plan/budget_settlement_receipt.schema.json` | 5999 | `6c9ee6aebc4111a1` | OK |
| 9 | `baseline/plan/evidence_manifest.schema.json` | 36739 | `561a0c289751e5f1` | OK |
| 10 | `baseline/plan/execution_playbook.md` | 68362 | `14bfca6216acc8f4` | OK |
| 11 | `baseline/plan/findings.md` | 59304 | `e246b222fac6da76` | OK |
| 12 | `baseline/plan/gate_dag.schema.json` | 10146 | `b8fd02ae712f3e1c` | OK |
| 13 | `baseline/plan/gate_dag.v4.json` | 22771 | `c06b20d040eb8c7a` | OK |
| 14 | `baseline/plan/gate_ledger.schema.json` | 24511 | `f9f14cc3f73bd34b` | OK |
| 15 | `baseline/plan/gate_ledger_transcript.schema.json` | 1673 | `d32e15b03b53aef5` | OK |
| 16 | `baseline/plan/gate_ledger_validator_vectors.schema.json` | 11487 | `d1395630ad941969` | OK |
| 17 | `baseline/plan/gate_ledger_validator_vectors.v4.json` | 59567 | `7e2472d76ae93e93` | OK |
| 18 | `baseline/plan/gate_state_machine.md` | 28269 | `49940700b4ee1172` | OK |
| 19 | `baseline/plan/implementation_agent_prompts.md` | 20526 | `ab5c2fbc28996f5d` | OK |
| 20 | `baseline/plan/journal_manifest.schema.json` | 7197 | `0b1d690c3ab88090` | OK |
| 21 | `baseline/plan/journal_record.schema.json` | 6539 | `6b18298ddabae66d` | OK |
| 22 | `baseline/plan/ledger_head_anchor.schema.json` | 3364 | `247fa1cdf7d5e412` | OK |
| 23 | `baseline/plan/ledger_validator_contract.md` | 20105 | `c5b94e63b055ef6a` | OK |
| 24 | `baseline/plan/operation_contract.schema.json` | 79656 | `7e44a159d8380156` | OK |
| 25 | `baseline/plan/operation_contracts.schema.json` | 11677 | `e4924cfbad3087fc` | OK |
| 26 | `baseline/plan/operation_contracts.v4.json` | 22890 | `4cf7dab5c2ced9f0` | OK |
| 27 | `baseline/plan/operation_execution_receipt.schema.json` | 8877 | `128cc8f5c986f095` | OK |
| 28 | `baseline/plan/operation_intent_manifest.schema.json` | 16503 | `57363a15c67498a3` | OK |
| 29 | `baseline/plan/operation_intent_template.schema.json` | 14022 | `d1a8ec48d648257b` | OK |
| 30 | `baseline/plan/parser_route_manifest.schema.json` | 7091 | `7eb962bab81d76c0` | OK |
| 31 | `baseline/plan/plan_consistency_check.py` | 71496 | `0f008bad07297c4f` | OK |
| 32 | `baseline/plan/plan_freeze_check.v4.txt` | 172 | `ca47be86a15d94c6` | OK |
| 33 | `baseline/plan/plan_manifest.schema.json` | 4062 | `23086172e96c10f0` | OK |
| 34 | `baseline/plan/plan_review_findings.md` | 32595 | `17206a816de688af` | OK |
| 35 | `baseline/plan/README.md` | 18875 | `200e618179a360bc` | OK |
| 36 | `baseline/plan/review_confirmation.schema.json` | 2471 | `6765641ff37ee556` | OK |
| 37 | `baseline/plan/review_result.schema.json` | 4767 | `05099f08435fe7e9` | OK |
| 38 | `baseline/plan/rollout_rollback_runbook.md` | 32836 | `2728be56f758a53d` | OK |
| 39 | `baseline/plan/schema_registry.schema.json` | 2564 | `771dfa72a6f03706` | OK |
| 40 | `baseline/plan/task_plan.md` | 57300 | `46634bec14cf3046` | OK |
| 41 | `baseline/plan/test_acceptance_plan.md` | 54832 | `8f0a86919e60d1ca` | OK |
| 42 | `baseline/plan/test_id_registry.schema.json` | 12830 | `7f61d64464437b83` | OK |
| 43 | `baseline/plan/test_id_registry.v4.json` | 123062 | `b2040c1557ed6b4e` | OK |
| 44 | `baseline/plan/traceability_matrix.md` | 23780 | `7a6865532489f878` | OK |
| 45 | `baseline/plan/user_approval_receipt.schema.json` | 7619 | `ec6f4863f7a583fc` | OK |
| 46 | `baseline/plan/validator_fixture_manifest.schema.json` | 7511 | `4d1b313e1d48a62b` | OK |
| 47 | `baseline/plan/validator_release_manifest.schema.json` | 9247 | `f1148f53cf27e8ab` | OK |
| 48 | `baseline/plan/validator_request.schema.json` | 2546 | `1d7c52c4c3994981` | OK |
| 49 | `baseline/plan/validator_scenario_fixture.schema.json` | 7507 | `7dbd6c8e438d0716` | OK |
| 50 | `plan_manifest.schema.v5.json` | 6486 | `aa3897a007086e51` | OK |
| 51 | `tools/v5_plan_consistency_check.py` | 25638 | `97084c1e0cbbe3e9` | OK |

## A5. B4：`git check-attr`（51 项 × 4 属性）

```
git check-attr text eol filter working-tree-encoding -- <51 repo-relative paths>
attr_lines=204   non_unset=0
# 绝对路径形式（checker 内部用法）同样：attr_lines2=204  non_unset2=0
git check-attr text eol filter working-tree-encoding -- .gitattributes docs/plans/…-v5-…/.gitattributes
.gitattributes: text: unspecified …                     # 仓库根文件（不适用，正常）
docs/plans/…-v5-…/.gitattributes: text: unset / eol: unset / filter: unset / working-tree-encoding: unset
```
`.gitattributes` 内容（172 B，sha `88182b26…`）：
```
# Preserve exact bytes only within this v5 planning directory.
# This does not lock files or replace a stable review boundary.
* -text -eol -filter -working-tree-encoding
```
> 复现提示：`git check-attr` 的路径必须相对**仓库根**或绝对；用「相对 v5 目录」的写法会得到 `unspecified`（本审查初次误用，已纠正）。

## A6. B5：退役目录状态

```
exists=True            mtime_utc=2026-09-07T18:08:52.8971277Z   attrs=Directory   reparse=False
tracked=38             on_disk=38      git status --porcelain -- <old>: (empty)
reparse points under docs/plans: (none)
overlap old-dir bytes vs 51 frozen entries : 0/38
overlap old-dir bytes vs all 81 v5 files   : 0/38
```
退役目录内含 38 个文件，其中有独立 manifest 载体：`plan_manifest.v3.json`(2861 B, `d4bf559b…`)、`plan_manifest.schema.json`(4139 B)、`plan_consistency_check.py`(39110 B)、`plan_review_revision.md`、`progress.md`。

## A7. B6：HEAD 与冻结产物

```
HEAD=454f632c046880980df5ce53bdaccdef88ca762a   branch=fcap
git show --stat 454f632 → 含 plan_manifest.v5.json(378+)、plan_manifest.schema.v5.json(163+)、
  plan_freeze_check.v5.txt(2+)、tools/v5_plan_consistency_check.py(543+)、
  tools/v5_freeze_manifest_build.py、v5-freeze-boundary.md、v5-freeze-record.md、
  v5-version-contract.md(1 行)、v5-version-reference-inventory.{json,md}（11 files changed）
git ls-tree -r --name-only 436ecd3 -- <plan> | count = 74
git ls-tree -r --name-only HEAD    -- <plan> | count = 81
git diff --name-status 436ecd3 454f632 -- <plan> = A×7 / M×4
```

## A8. `frozen_at` / `plan_freeze_git_head` 可信度

```
manifest: frozen_at=2026-09-09T20:45:08.683056Z   plan_freeze_git_head=436ecd38509ef87199b2a3133f08994bfdaec18f
mtime:    plan_manifest.v5.json     20:45:08.678900Z  (ctime 20:43:51.986724Z → builder 至少跑过两次)
          plan_freeze_check.v5.txt  20:45:08.501192Z
          v5-baseline-equivalence.json / inventory  20:45:06.5Z
          tools/v5_version_reference_scan.py 20:45:04.6Z  tools/v5_plan_consistency_check.py 20:44:28.7Z
commit 436ecd3 = 21:28:33+01:00 (20:28:33Z) ; commit 454f632 = 21:46:18+01:00 (20:46:18Z)
```
`frozen_at` 比 manifest 自身 mtime 晚 4.16 ms；本机探针（`%TEMP%` 写入一枚文件）显示 FS 时间戳落后墙钟约 1.3 ms，故该 4 ms 反转由环境时钟/落盘延迟解释，**无回填（backdating）证据**。HEAD 时序、产物 mtime 顺序（工具→证据→checker→manifest→commit）自洽。

## A9. N1–N17 与定向绕过实验

```
python …/tools/v5_plan_consistency_check.py --self-test   (exit=0, 11862 ms, 1218 B)
SELF-TEST N1 … N17 逐条 PASS
SELF-TEST: 17/17 negative cases rejected
```
定向绕过实验（临时副本；`external=False` 跳过 git/证据工具子进程，其余与真实运行同路径）：

| 实验 | 变异 | 结果 | 结论 |
|---|---|---|---|
| E1 | 基线（旧目录字面名 + 处置文件） | `codes=[]` checks=1367 | 正常通过 |
| E2 | **仅把退役目录改名** | `codes=[]` checks=1263 | **N9 静默失效（P1-1）** |
| E3 | 删处置文件（对照） | `codes=['N9','N9-DISPOSITION']` | N9 只判存在 |
| E4 | 处置文件内容改为「旧目录才是权威」 | `codes=[]` | **处置内容不校验（P1-1）** |
| E5 | 向 `baseline/plan` 注入第 49 个文件（硬链接） | `codes=['N13','N7','V5-SET-IMPORTED','V5-SET-TOTAL']` | 成员集合受控 ✓ |
| E6 | 用硬链接替换冻结文件 | `codes=['N5','N7']` | 字节受控 ✓ |
| E7 | `plan_directory` 指向旧目录 | `codes=['N2','N4']` | const 封死 ✓ |
| E8 | `pre_freeze_check.command` 指向旧目录 checker | `codes=['N2','N8']` | ✓ |
| E9 | **`baseline/plan` 改为指向外部目录的 junction** | `codes=[]` | **无 reparse 检查（P1-2）** |

## A10. 取代链 / 自排除 / 钉值

```
plan_manifest.v5.json.supersedes:
  baseline/history/plan_manifest.v4.json  c34b849475f1efeb0a3237af2d4a748a6e36c276f7c91b6ad07cae8ea3004711  (9598 B)  ✅ 实测一致
  baseline/history/plan_manifest.v3.json  9ee84acdbe65a294925de004125f37b62b9e4b1c95655a04cd2344bc6bd270cc  (2778 B)  ✅ 实测一致
基线 checker IMMUTABLE_HISTORY_SHA256["plan_manifest.v3.json"] = 9ee84acd…   ✅ 与上一致
退役目录 v3 = CRLF 变体 d4bf559b…（2861 B）；其 CRLF→LF 归一化 = 9ee84acd…  ✅ 纯 EOL 差异
investigation_source.sha256 8e6166ba…  ✅ 实测一致（36300 B，合法 UTF-8）
capture_manifest.sha256 da7d116e…      ✅ 实测一致（34238 B）
self_exclusion = "plan_manifest.v5.json"；normative_files 不含自身  ✅
N10 git 分支：HEAD:blob == hash-object == 0150f4eaf078928eb3dcbd448f9a2129447a1c17  ✅
```

## A11. 环境 / 编码 / 卫生测量

```
python -V → 3.13.9 ; jsonschema 4.26.0 ; core.autocrlf=true ; core.symlinks=false ; NTFS
git check-attr 全 51 项 text/eol/filter/working-tree-encoding = unset（204/204）
HEAD:blob == git hash-object <worktree>   : 51/51 frozen ✅（全部 81 个目录文件仅 1 项不符 =
                                          并发改写的 v5-freeze-record.md，非冻结项）
仓库根 .gitattributes 仅含 /.githooks/** text eol=lf（不影响 v5 目录，已实测）
CI (.github/workflows/ci.yml) 未引用 v5 计划目录/checker（未被 CI 执行）
pre-push hook → tools/pre_push_gate.py（只读子进程，无 write_text/write_bytes）
凭据扫描：仅命中 schema 字段名与占位符（contains_secret / secret_scan_result / GL-F09-EVIDSECRET）
绝对个人路径：reviews/old-plan-retirement-inventory.json:6-8；baseline/investigation/…（历史、哈希绑定）
非 UTF-8 文件：无（含 baseline/investigation 报告亦为 UTF-8）
BOM：无
控制台编码：checker 对 stdout/stderr 与全部 subprocess 显式 utf-8；冻结产物为纯 ASCII
```

## A12. 并发写入观测（审查窗口内）

```
20:46:15Z  .ruff_cache/0.15.18/6516895124640508795
20:46:50Z  .pytest_cache/v/cache/nodeids
20:48:02Z  …/v5-freeze-record.md   8151 → 8373 B（新增一行 8867 复验说明）
20:50:12Z  …/task_plan.md          （V5-2 行改为 8867）
51 个冻结项：sha / size / mtime 全部未变（§A3）
```
`.githooks/pre-commit` 仍调用 pre-commit（`staged_files_only` = 整仓 `git checkout -- .` + patch 恢复），即 v4 漂移事故的机制在当前被跟踪状态下依然存在；`.gitattributes -text` 关闭了其中的 EOL 转换环节，但**不构成文件锁**（与文档自述一致）。

---

**审查者声明**：本审查只读，除本文件外未在仓库内创建/修改/删除任何文件；未 `git add/commit/push`；未触碰 worker、数据库、计划任务或其他仓库；未请求或执行任何实施动作。本 verdict 只绑定**规划文档冻结**的生命周期/安全面，不构成实施授权；P0/P1 全关前该冻结不得作为实施输入。
