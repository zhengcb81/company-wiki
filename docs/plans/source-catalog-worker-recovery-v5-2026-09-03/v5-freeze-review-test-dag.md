# V5-2 冻结独立审查 — 测试 / DAG 轴（verification power + gate-DAG integrity）

审查者：独立审查代理（测试/DAG 轴；未参与本计划任何文档或工具的编写）
审查对象：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03` 冻结时点 `HEAD 454f632c046880980df5ce53bdaccdef88ca762a`
方法：全部结论由本次独立复算/复现得出，不采信 `v5-freeze-record.md` 的任何自述；所有破坏性试验只作用于 `C:\v5rev*`、`C:\v5review` 下的临时副本，真实冻结树只读。
环境：Windows + PowerShell 7，Python 3.13.9，jsonschema 4.26.0，`git` 可用。

## 结论

**verdict: `accepted_with_findings`**

冻结产物本身是自洽的：`--self-test` 17/17 可复现；`--verify-manifest` 在真实树通过；51 项冻结集、DAG/registry/vector/schema 计数、`coverage_counts`、预冻结 stdout 字节、以及冻结记录 §1 表格的全部 11 个 sha256 均由本次独立复算得到一致结果。**但 N1–N17 中至少 6 条负例没有实现合同 §5/§7 的语义**：我构造的 6 个"通过全部 N1–N17 却违反合同规则"的 manifest/环境变体全部被 `PASS`（附录 A），其中 2 个是"导入字节被改写且所有记录同步更新"这类冻结机制本应拦截的核心场景。这些是验证力缺口（P1），不改变当前交付产物的正确性，故判定 `accepted_with_findings` 而非 `rejected`。

## 1. 冻结自述的可复现性（全部通过）

| 自述 | 复现命令 | 本次实测 |
|---|---|---|
| `--self-test` 17/17 | `python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/tools/v5_plan_consistency_check.py --self-test` | `SELF-TEST: 17/17 negative cases rejected`（exit 0） |
| 默认模式 7658 | 同上，无参数 | `PASS: 7658 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}` |
| `--verify-manifest` | 同上，`--verify-manifest` | `PASS: 8867 checks; …`（**记录写 8866**，见 TST-P2-7） |
| §1 哈希表 11 项 | `Get-FileHash … -Algorithm SHA256` | 11/11 字节数 + sha256 与记录表格逐位一致 |
| 预冻结 stdout 172B/0 CR | `[IO.File]::ReadAllBytes(...)` | 172 字节、CR=0、LF=2、`sha256=88f407ae…`，与 manifest `stdout_sha256`、`reported_check_count=7658` 一致 |
| B4 属性 204 行 unset | 真实树 `--verify-manifest`（内含 `git check-attr`） | `V5-ATTRS-UNSET` 通过（204 行全 `unset`） |
| B5 旧目录 | `git ls-files docs/plans/source-catalog-worker-recovery-2026-08-22` 等 | 38 已跟踪、`git status` 0 项、mtime `2026-09-07T18:08:52.8971277Z` 与记录一致 |
| D4 证据范围 56=54+2 | 读 `v5-version-reference-inventory.json` + 独立计数 | `files_scanned=56, baseline=54, root=2`；`baseline/**` 实测 54 文件（plan 48 + history 5 + investigation 1） |
| 等价性 21/17/10 | 独立读 `v5-baseline-equivalence.json` + manifest 逐件标签计数 | 21/17/10，`unresolved=0`，与 manifest `equivalence_summary` 一致 |
| B3 无字节漂移 | 每次运行 | `B3-BOUNDARY-DRIFT` 通过；真实树 `baseline/plan/__pycache__` 不存在 |

## 2. 计数独立复算（不调用 checker 代码）

独立脚本（附录 B）直接解析冻结 JSON：

| 指标 | 独立复算 | manifest `coverage_counts` | 冻结记录 |
|---|---|---|---|
| `fixed_dag_nodes` | 115（节点条目 115，重复 0） | 115 | 115 |
| `stable_test_ids` | 315（重复 0） | 315 | 315 |
| `validator_vector_groups` | 18 | 18 | 18 |
| `validator_vector_cases` | 140 | 140 | — |
| `schemas` | 29（`*.schema.json`，`$id` 去重后仍 29） | 29 | 29 |
| `requirements` | 60（`RQ-\d{3}` 去重） | 60 | — |
| `risks` | 44（`RK-\d{2}` 去重） | 44 | — |
| `plan_review_findings` | 105（`PR-\d{3}` 去重） | 105 | — |

`coverage_counts` 8 个字段与独立复算**逐字段相等**。计数还被 baseline 硬编码锚定：`TEST-COUNT==315`（`baseline/plan/plan_consistency_check.py:1032`）、`EXPECTED_VECTOR_IDS` 18 组（:119）、`pre_freeze_output_checks` 的 `{"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}` 全匹配（:1517-1523）。我另做 DAG 完整性对抗试验（附录 A `s18`）：删掉 `gate_dag.v4.json` 一个节点 `G12C-RB` 并同步 `coverage_counts.fixed_dag_nodes=114`，baseline 语义检查立刻报错（`DAG-ROLLBACK-STATE`/`REVIEW-OVERRIDE`/`TEST-LIFECYCLE-NODE` 共 18 条）——DAG 计数与语义不是"仅靠 manifest 自述"。

## 3. baseline 套件继承性（任务 3）

AST 扫描 `tools/v5_plan_consistency_check.py`（附录 B 命令）确认：

| baseline 组 | v5 checker 调用次数 |
|---|---|
| `schema_checks` | 1 |
| `dag_checks` | **2**（`baseline_suite` 1 次 + `verify_manifest` 内 N13 的 `coverage_counts` 复算 1 次） |
| `operation_checks` | 1 |
| `registry_checks` | 1 |
| `vector_checks` | 1 |
| `catalog_pointer_checks` | 1 |
| `active_prose_semantic_checks` | 1 |
| `pre_freeze_output_checks` | 1 |
| `immutable_history_checks` | **0**（改为 1 条布局感知内联等价检查） |
| `plan_manifest_checks` | **0**（整体丢弃） |

- 8 个被点名的组全部被调用，且**没有任何 monkeypatch**：全文件对 `base.*` 的赋值只有 `self_test` 内的 `base.ERRORS, base.CHECKS = [], 0` / `= saved`（line 512、517，`finally` 恢复），未重绑任何组函数、未改 `base.ROOT`、未过滤 `base.check`。组函数以 baseline 自己的 `ROOT`（即冻结树 `baseline/plan`）就地校验，不是副本。
- 未继承的两组影响（TST-P2-10）：`plan_manifest_checks` 共 **202** 条检查被丢弃，其中 `MANIFEST-EXCLUSIONS`、`MANIFEST-PATH-SAFETY`（`has_reparse_component` 的 symlink/reparse 检测）、逐件 `MANIFEST-FILE/BYTES` 在 v5 侧**没有等价物**；`immutable_history_checks` 的替换是必要的（直接跑 baseline `main()` 在本布局下必失败：`FAIL: 1 error(s) after 7695 checks - IMMUTABLE-HISTORY: plan_manifest.v3.json: [Errno 2] …`，即 D1 描述属实），替换后期望哈希仍是硬编码 `9ee84acd…`，等价。
- **继承未被削弱（正向证明）**：在临时副本上同时破坏 schema `$id`、`gate_state_machine.md` 的 `D12C-RT` 令牌与 vectors 首例的 `expected_primary_code`，真实 CLI 立刻由继承的组报错：`SCHEMA-ID-BINDING`、`INSTANCE-SCHEMA`（schema_checks）、`VECTOR-REASON-RULE`/`VECTOR-OUTCOME`（vector_checks）、`PROSE-DUAL-AUTH`（active_prose_semantic_checks），共 14 条错误 exit 1（附录 A `s29`）；`s18` 另证明 DAG/operation/registry 组在 v5 下同样生效。因此"v5 checker 让 baseline 套件空转"的假设不成立。

## 4. N1–N17 ↔ 代码映射与检查计数算术（任务 4）

- **ID 完备**：`"N1"…"N17"` 每个字符串在 checker 中各出现 ≥2 次（定义 + 自测表），无 `N18+`、无其它 N 前缀码（附录 B 命令）。`--verify-manifest` 实测每条码的**调用次数**均 ≥1（N1=1, N2=1, N3=1, N4=1, N5=51, N6=1, N7=97, N8=2, N9=52, N10=1, N11=4, N12=1, N13=5, N14=1, N15=2, N16=3, N17=2），**无死码**；每条码在真实树被求值过，且 `--self-test` 证明其可触发。
- **检查计数算术（完全可解释）**：

  | 分量 | 条数 | 来源 |
  |---|---|---|
  | baseline 套件 | 7494 | 1825 schema + 982 dag + 224 operation + 3852 registry + 569 vector + 6 pointer + 32 prose + 3 prefreeze + 1 内联 history |
  | v5 冻结集/边界/证据 | 164 | `v5_checks` |
  | **默认模式合计** | **7658** | 与 `plan_freeze_check.v5.txt` 的 `reported_check_count` 逐字一致 |
  | N1–N17 | 227 | 226 + 1（N10 的 git 已跟踪分支） |
  | 重复 `dag_checks()`（N13 coverage 复算） | 982 | `verify_manifest` 内 `base.current_coverage_counts(base.dag_checks()[1])` |
  | **`--verify-manifest` 合计** | **8867** | 7658 + 227 + 982 |

  8867 与记录中的 8866 差 1，唯一来源是 N10 的 `git ls-files --error-unmatch` 分支：冻结时 manifest 尚未入库（记录 §2 B6 自述），该分支未执行；入库后激活 → +1。对照证据：在临时树删除 `.git` 后同一命令报 8866，且删掉退役目录后报 8763（= 8867 − 104 = 8867 − (v5_checks 52 + verify_manifest 52) 条 N9 检查）。

## 5. checker 自身质量（任务 5）

- **无静默吞异常**：全文件仅 `except (AttributeError, ValueError): pass`（line 40，`stdout.reconfigure` 的兼容分支，与检查无关）；`jsonschema` 缺失走 `base.check(False, "N4", …)`（fail-closed）；baseline 的 3 处 `except Exception` 全部 `ERRORS.append`。
- **红旗必为 exit 1**：`s19`（单字节漂移）真实 CLI exit 1；`s27`/`s28` 亦 exit 1（但为 traceback，见 TST-P2-9）。`report()` 对 `base.ERRORS` 非空即返回 1。
- **输出确定性**：`PYTHONHASHSEED=0` 与 `=1` 下 `--verify-manifest` stdout 逐字节相同；默认模式连跑两次逐字节相同；失败样例（4 条错误的 s19 副本）在两个 seed 下也逐字节相同（错误顺序稳定，消息内集合均 `sorted`）。
- **存在 1 条恒真检查**：`base.check(len(ctx.governing) == EXPECTED_GOVERNING, "V5-SET-GOVERNING", …)`（line 151）两侧都取自模块常量（`GOVERNING` 3 项），任何输入都无法令其为假（TST-P2-1）。
- 另有 2 条防御性检查被更早的检查遮蔽（casefold 冲突、重复路径），不构成缺陷，但属"永不触发"代码（TST-P2-12）。

## 6. Findings

| ID | Sev | Finding | Evidence（命令 + 观测） | Required fix |
|---|---|---|---|---|
| TST-P1-1 | P1 | **N6 不重算逐件等价类**：`equivalence` 只被聚合成 `equivalence_summary` 再与 manifest 自身标签计数比对；同一类内互换标签（v4_exact↔crlf_only）保持 21/17/10 不变即通过，合同 §7 N6「类别与**复算**不符」未实现。 | 附录 A `n6swap`（`python evade.py n6swap`）：`PASS: 8867 checks`。自测 `_n6` 只改一个标签使总数变 20/18/10，故仅聚合比较即可命中——`probe_isolation.py` 显示 N6 关闭后该变异不再被拒，说明它**只**测了聚合比较。 | 对每个 `normative_files` 条目用 `historical_v4_sha256` 复算类（`sha==hist` → v4_exact；`sha(LF 归一化)==hist` → crlf_only；否则 unproven），逐件比对 manifest 标签；并把 manifest 的 `equivalence_summary` 与冻结证据 `v5-baseline-equivalence.json` 的 `groups` 交叉核对。 |
| TST-P1-2 | P1 | **导入字节没有不可再生的锚**：N7 把字节与 `import_manifest.v5.json` 里可写的 `sha256` 比、N5 与 manifest 自述比，两者都可被同步改写；两个证据工具的输出（`v5-baseline-equivalence.json`、`v5-version-reference-inventory.{json,md}`）按设计可被默认模式重新生成，且**未在 manifest 中做哈希绑定**（`grep -n 'baseline-equivalence\|inventory' plan_manifest.v5.json` → 无匹配）。 | 附录 A `importrewrite`：改写 `baseline/plan/findings.md` + 同步 capture 的 `sha256/size_bytes/historical_v4_sha256` + manifest 条目 + `capture_manifest.sha256` + 重跑两个证据工具 → `PASS: 8867 checks`。副证：该副本重算出的证据 JSON 为 `{'v4_exact': 22, 'unproven_new_baseline': 9}`，与 manifest `equivalence_summary`（21/10）矛盾，却仍然 PASS。 | ① 把 48 个导入件 sha256 硬编码进 checker（同 `IMMUTABLE_HISTORY_SHA256` 模式），或 ② 把 N10 的 git blob 比对扩展到 51 个冻结件 + 2 个证据 JSON/MD（工作树 vs `HEAD:`），或 ③ 至少把证据 JSON/MD 纳入 manifest 哈希绑定，并断言 manifest 等价类与证据 `groups` 逐件一致。 |
| TST-P1-3 | P1 | **N8 未把预冻结产物绑定到"本 checker 自己的输出"**：只要求 `plan_freeze_check.v5.txt` 以 `PASS: <n> checks; ` 开头且与 manifest 记录的 hash/计数自洽，既不与本次运行的 `base.CHECKS` 比，也不校验产物内嵌的 `{"fixed_nodes":115,…}`。 | 附录 A `fake_prefreeze`：写入 `PASS: 12345 checks; {"fixed_nodes": 115, …}` 并同步 manifest 的 `reported_check_count=12345`/`stdout_sha256` → `PASS: 8867 checks`。 | 解析产物中的计数 JSON 并与本次复算比对；要求 `reported_check_count` 等于本 checker 默认模式的确定值（7658）或由一次真实默认模式运行字节复现产物；发现 CR/格式偏差即拒。 |
| TST-P1-4 | P1 | **合同 §5.2「v5 checker 入口路径必须等于 `pre_freeze_check.command` 中调用的脚本路径」未实现**：N2/N8 只做子串判断（`"v5_plan_consistency_check.py" in command` 且 `"2026-08-22" not in command`），不解析实际被调用的脚本。 | 附录 A `cmd_comment`：`command` 改为调用 `baseline/plan/plan_consistency_check.py  # v5_plan_consistency_check.py` → `PASS`。另：交付 manifest 的 command 脚本路径含目录前缀，与 normative 条目 `tools/v5_plan_consistency_check.py` 并非字面相等，该规则即便按字面也未满足。 | 从 command 解析出被调用的 `.py` 路径，要求其归一化后以 normative 集中 `v5_own` 的 checker 条目结尾（并拒绝 `#` 注释内的提及）；或在合同 §5.2 明确"以结尾匹配"的判据。 |
| TST-P1-5 | P1 | **冻结集用非递归 glob 枚举**（`frozen_entries`: `ctx.baseline.glob("*")`），`baseline/plan/` 下新增**子目录**内容完全不可见：`V5-SET-IMPORTED/TOTAL` 计数不变、N13 集合相等仍成立，与合同 §5.2「导入的计划输入 = `baseline/plan/**`」冲突。 | 附录 A `nested`：新建 `baseline/plan/nested/plan_manifest.v4.json` 并重生成证据 → `PASS: 8867 checks`。（未重生成证据时仅 `V5-EVIDENCE-CHECK` 报警，见附录 A `s13`。） | 用 `rglob`/显式 48 项清单，断言 `baseline/plan/**` 下不存在未列名文件/目录；或对 `baseline/plan` 递归计数并与 capture 记录比对。 |
| TST-P1-6 | P1 | **N11 用后缀匹配 + 静默回退**：`matches = [k for k in superseded if k.endswith(name)]`，随后 `path = ctx.root/key`，不存在则回退 `baseline/history/<name>`。于是"取代链"可以指向已退役旧目录、可以追加任意条目、可用 unicode 形近路径，均满足字面检查。 | 附录 A `supersedes_retired`：向 `supersedes` 追加 `docs/plans/source-catalog-worker-recovery-2026-08-22/plan_manifest.v4.json`（hash 取 history 中 v4 的值）→ `PASS: 8868 checks`；`s09`（把 v4 链节路径整体替换为旧目录路径）同样 PASS；`s07`（西里尔字母 `а` 形近路径）PASS。合同 §6.3「旧目录任何文件都不在取代链内」被直接违反。 | `supersedes` 必须恰好是 `baseline/history/plan_manifest.v4.json` 与 `…v3.json` 两条，路径等于期望字符串（或位于 v5 目录内的规范化路径），去掉回退分支，并对 `supersedes[].path` 施加与 `normative_file.path` 相同的字符集约束。 |
| TST-P2-1 | P2 | `V5-SET-GOVERNING` 恒真（模块常量自比），不校验冻结集中治理件数量。 | checker line 151；`ctx.governing` 在 `main()` 与 `self_test` 中均赋 `GOVERNING` 常量。 | 改为从 `declared`/`entries` 统计 `equivalence=="v5_own"` 的条目数并与 3 比对。 |
| TST-P2-2 | P2 | 自测断言过弱 + 17 条变异中 9 条不隔离：`if code in codes` 只要求目标码"在"错误集合里。用 `probe_isolation.py` 把目标码的检查禁用后，N2/N3/N7/N10/N11/N12/N13/N14/N16 的变异**仍被其它码拒绝**——即使对应检查被删空，`--self-test` 依然 17/17。 | `python probe_isolation.py C:\v5review\pristine` 输出表（附录 C）；例：`N3 \| N15,N3,N4 \| N15,N4 \| NO`。 | 断言目标码是唯一/首要拒绝原因（如"禁用目标码后必须不再被拒"），或把变异改造成只有目标码能拦。 |
| TST-P2-3 | P2 | 自测以 `external=False` 运行，**跳过** N10 的 git 分支、`V5-ATTRS-UNSET` 与两个证据工具检查；而冻结记录 §3 把 N10 记为"manifest 自身进入 normative 集 / 覆盖写既有 manifest"均已测。 | `self_test` 构造 `Ctx(..., external=False)`（line 505）；`_n10` 只追加自身条目。 | 自测对 N10 增加"改写已跟踪 manifest 后断言 N10 触发"的变异，并在临时 git 仓库下跑 `external=True` 的边界臂。 |
| TST-P2-4 | P2 | N9 锚定单一硬编码目录名，且"显式处置"只判文件存在：把旧目录改名（并列副本仍在）或清空 `v5-freeze-boundary.md` 均通过。 | 附录 A `rename_olddir`：`PASS: 8763 checks`（N9 的 104 条检查整体不执行）。 | 枚举同级 `source-catalog-worker-recovery-*` 目录并要求处置记录逐一列名；对边界记录做哈希绑定并检查非空/含目录名。 |
| TST-P2-5 | P2 | `plan_freeze_git_head` 从不与 `git rev-parse HEAD` 比对；`frozen_at` 只做格式校验。 | 附录 A `fake_head`（全 0 的 40 hex）→ `PASS: 8867 checks`；`s23`（`frozen_at=1999-01-01T00:00:00Z`）→ `PASS`。 | 与 `git -C root rev-parse HEAD` 比对，或要求其为 HEAD 的祖先并记录比对结果。 |
| TST-P2-6 | P2 | `evidence_tools` 不是精确集合：N17 只校验两条固定工具的哈希，额外条目（指向不存在文件、假哈希）不受任何检查。 | 附录 A `extra_evidence`：追加 `{"path":"tools/does_not_exist.py","sha256":"0"*64,"size_bytes":1}` → `PASS: 8867 checks`。 | 断言 `evidence_tools` 恰为两条且逐条 `path.is_file()` + 哈希匹配。 |
| TST-P2-7 | P2 | 冻结记录"后冻结复验 `--verify-manifest` → 8866"在入库后不可复现（现为 8867）。 | 真实树 `python … --verify-manifest` → `PASS: 8867 checks`；临时树去 `.git` 后为 8866（N10 分支未激活）。工作区已有一处未提交的修订行（`git diff v5-freeze-record.md`）。 | 提交该修订（或把 `reported_check_count` 改为与模式无关的口径）。 |
| TST-P2-8 | P2 | 被取代的 v4 manifest 在冻结集内没有哈希锚（v3 由 baseline 的 `IMMUTABLE_HISTORY_SHA256` 钉住，v4 仅由可再生的证据清单间接覆盖）：改写 `baseline/history/plan_manifest.v4.json` 并同步 `supersedes[].sha256`，只要重生成证据即可通过。 | 附录 A `s22`（不重生成证据）仅 `V5-EVIDENCE-CHECK` 报错；`s26`（重生成证据）→ `PASS: 8867 checks`。 | 把 v4 manifest 的期望 sha256 也硬编码进 checker，或把 `baseline/history/**` 纳入冻结集/哈希绑定。 |
| TST-P2-9 | P2 | 畸形输入以 traceback 崩溃而非稳定编码报告：`normative_files` 条目缺 `path` → `KeyError`（line 216）；manifest 非法 JSON → `JSONDecodeError`。二者仍 exit 1（fail-closed），但不产出可机读的 N 码。 | 附录 A `s27`/`s28`：`KeyError: 'path'` / `json.decoder.JSONDecodeError`，exit 1。 | 在构建 `declared` 前用 try/except 包裹并 `check(False, "N4"/"N13", …)`。 |
| TST-P2-10 | P2 | v5 checker 丢弃 baseline `plan_manifest_checks` 全部 202 条检查（含 `MANIFEST-EXCLUSIONS`、`MANIFEST-PATH-SAFETY` 的 symlink/reparse 检测），且无 v5 等价物；`immutable_history_checks` 改为内联 1 条（等价但需人工比对）。 | `decompose_baseline.py`：`plan_manifest_checks delta=202`；AST 表（第 3 节）。 | 至少移植 `has_reparse_component` 路径安全臂到 51 项冻结集，并明确记录被丢弃的检查面（含理由）。 |
| TST-P2-11 | P2 | N6 的诊断信息会误归因：任何路径不匹配都会让某类计数下降并报 `equivalence_summary != recomputed`（真正的错误是路径）。 | 附录 A `s06`：`- N13: missing=['baseline/plan/README.md'] extra=['baseline/plan/Readme.md']` 与 `- N6: … != recomputed {… 'unproven_new_baseline': 9, 'v5_own': 3}` 同时出现。 | N6 只在集合相等成立时执行，或把"缺项导致计数下降"从 N6 中排除。 |
| TST-P2-12 | P2 | 两条 N13 检查被更早的检查永久遮蔽：casefold 冲突在"集合严格相等"下不可能触发；重复路径先被 schema `uniqueItems` 以 N4 拦下。 | `s05` 观测到 `N4: … has non-unique elements` + `N13: duplicate path`；casefold 行（line 239-240）在任何输入下都不会是首个拒绝原因。 | 保留但注明为纵深防御，或调整为独立可触发场景（如大小写不敏感文件系统上的镜像清单）。 |
| TST-P2-13 | P2 | 合同 §5.2「`plan_manifest.schema.v5.json` 与 v5 checker 必须**同时**出现在 normative 集与 `pre_freeze_check.command` 中」未满足：交付 command 只出现 checker。 | manifest `pre_freeze_check.command` = `python docs/plans/…/tools/v5_plan_consistency_check.py`（无 schema 路径）。 | 修改 command（例如 `python -c` 形式的双文件校验）或在合同中明确该句仅约束"冻结集成员"，避免字面冲突。 |

## 7. 未覆盖 / 残余风险（本次未验证）

1. 未对 48 个导入件做**内容级**（语义）审查——本次只验证字节/哈希/集合/计数与 baseline 全套语义检查的通过性。
2. symlink/junction 场景未实测（Windows 创建符号链接需权限）；仅指出 v5 侧缺失 baseline 的 reparse 检测（TST-P2-10）。
3. 未评估 `baseline/plan` 之外（`baseline/history`、`baseline/investigation`）被改写后的语义影响，只验证了其哈希锚的强度（TST-P2-8）。
4. 本次所有破坏性试验均在 `C:\v5rev*`/`C:\v5review` 副本上进行；真实冻结树未被写入（`git status` 中 `baseline/**`、`tools/**`、两个冻结产物均无改动）。

## 附录 A — 全部对抗/规避尝试与结果

模式说明：`full` = 真实 CLI `--verify-manifest`；`fast` = 跳过 baseline 套件的等价探针（`v5_checks` + `verify_manifest`，`external=True`）。两者在无变异副本上分别报 `PASS: 8867` 与 `PASS: 1373`，与真实树一致。全部在临时副本执行，且变异后先 `git commit` 再运行（模拟"冻结产物已入库、审查者 checkout 后验证"的状态，使 N10 的 git 分支保持激活）。

| # | 变异 | 模式 | 结果 | 判定 |
|---|---|---|---|---|
| s01 / `n6swap` | 同类内互换 v4_exact↔crlf_only 标签（21/17/10 不变） | full | `PASS: 8867` | **假阴性 → TST-P1-1** |
| s02 | 改写导入件字节 + 更新 capture/manifest 条目哈希（未更新 `capture_manifest.sha256`） | fast | `FAIL`：`N15`（capture hash）＋`V5-EVIDENCE-CHECK` | 拦截（但见 s24） |
| s03 | 同 s02 且更新 `historical_v4_sha256`（仍未更新 `capture_manifest.sha256`） | full | `FAIL`：`N15`、两个 `V5-EVIDENCE-CHECK` | 拦截（测试设计缺口，非机制） |
| s24 / `importrewrite` | 全协同改写：字节 + capture `sha256/size/historical_v4_sha256` + manifest 条目 + `capture_manifest.sha256` + 重生成两份证据 | full | `PASS: 8867` | **假阴性 → TST-P1-2** |
| s04 | 反转 `normative_files` 顺序 | fast | `PASS` | 无合同规则禁止顺序（信息性） |
| s05 | 追加重复条目 | fast | `FAIL`：`N4`（uniqueItems）+`N13`（重复路径） | 拦截 |
| s06 | 路径改大小写（`Readme.md`） | fast | `FAIL`：`N13`（缺/多）+`N6`（计数误报） | 拦截（诊断质量见 TST-P2-11） |
| s07 | `supersedes` 追加西里尔字母形近路径 | fast | `PASS` | **假阴性 → TST-P1-6** |
| s08 / `supersedes_retired` | `supersedes` 追加旧目录内条目（hash 取 history 中 v4） | full | `PASS: 8868` | **假阴性 → TST-P1-6** |
| s09 | 把 v4 链节路径整体替换为旧目录路径 | fast | `PASS` | **假阴性 → TST-P1-6** |
| s10 / `fake_prefreeze` | 伪造预冻结产物（`PASS: 12345 checks`）并同步 manifest 计数/hash | full | `PASS: 8867` | **假阴性 → TST-P1-3** |
| s11 / `cmd_comment` | command 改为调用 baseline checker，v5 checker 名只出现在注释 | fast | `PASS` | **假阴性 → TST-P1-4** |
| s12 | `baseline/plan` 增顶层文件 + 记入 manifest + 调整计数 | fast | `FAIL`：`V5-SET-IMPORTED/TOTAL`、`N4`、`N6`、`N7`、证据 | 拦截 |
| s12b | 仅增顶层文件（不改 manifest） | fast | `FAIL`：`V5-SET-IMPORTED/TOTAL`、`N13`、`N7`、证据 | 拦截 |
| s13 | `baseline/plan/nested/` 增嵌套文件（不重生成证据） | full | `FAIL`：仅 `V5-EVIDENCE-CHECK` | 部分拦截（见 s25） |
| s25 / `nested` | 同 s13 且重生成证据 | full | `PASS: 8867` | **假阴性 → TST-P1-5** |
| s14 / `rename_olddir` | 旧目录改名（并列副本仍在，无处置） | full | `PASS: 8763` | **假阴性 → TST-P2-4** |
| s15 | 删除旧目录 | fast | `PASS: 1269` | 合规（并列权威消失） |
| s16 | 删除冻结件 `baseline/plan/findings.md` | fast | `FAIL`：`V5-SET-IMPORTED/TOTAL`、`N13`、`N6`、`N7`、证据 | 拦截 |
| s17 / `extra_evidence` | `evidence_tools` 追加指向不存在文件的条目 | full | `PASS: 8867` | **假阴性 → TST-P2-6** |
| s18 | 删 DAG 节点 `G12C-RB` + 同步 `coverage_counts` | full | `FAIL`：`DAG-ROLLBACK-STATE`、`REVIEW-OVERRIDE`、`TEST-LIFECYCLE-NODE`×多、`N5`/`N7`（未同步哈希） | 拦截（DAG 语义+计数有锚） |
| s19 | 仅漂移一个冻结件字节 | full | `FAIL` exit 1：`N5`、`N7`、两个证据检查 | 拦截 + **红旗 exit 1** |
| s20 | `normative_files` 路径含西里尔字母 | fast | `FAIL`：`N4`（pattern）+`N13`+`N6` | 拦截 |
| s21 / `fake_head` | `plan_freeze_git_head` 置全 0 | full | `PASS: 8867` | **假阴性 → TST-P2-5** |
| s22 | 改写 `baseline/history/plan_manifest.v4.json` + 同步 `supersedes`（不重生成证据） | full | `FAIL`：仅 `V5-EVIDENCE-CHECK` | 部分拦截（见 s26） |
| s26 | 同 s22 且重生成证据 | full | `PASS: 8867` | **假阴性 → TST-P2-8** |
| s23 | `frozen_at` 置 1999-01-01 | full | `PASS: 8867` | **假阴性 → TST-P2-5** |
| s27 | 条目缺 `path` | fast | exit 1，`KeyError: 'path'`（无稳定码） | **TST-P2-9** |
| s28 | manifest 非法 JSON | fast | exit 1，`JSONDecodeError`（无稳定码） | **TST-P2-9** |
| s29 | 破坏 schema `$id` + prose 令牌 + vector 期望码 | full | `FAIL` exit 1：`SCHEMA-ID-BINDING`、`INSTANCE-SCHEMA`、`PROSE-DUAL-AUTH`、`VECTOR-OUTCOME`、`VECTOR-REASON-RULE`、`N5`、`N7`、证据 | 继承组**未被削弱**（正向证明） |

复现方式：附录 D 的自包含脚本 `evade.py`（复制计划目录到 ASCII 临时路径 → 应用变异 → 提交 → 运行 `--verify-manifest`），用法 `python evade.py <scenario> [full|fast]`，scenario 取 `n6swap/importrewrite/nested/supersedes_retired/fake_prefreeze/cmd_comment/rename_olddir/fake_head/extra_evidence/baselinerun`。真实冻结树始终只读。

## 附录 B — 独立复算与静态审计命令

```powershell
# 计数独立复算（不 import checker）
python -c "import json,re;from pathlib import Path;R=Path(r'<plan>\baseline\plan');d=json.loads((R/'gate_dag.v4.json').read_text(encoding='utf-8'));t=json.loads((R/'test_id_registry.v4.json').read_text(encoding='utf-8'));v=json.loads((R/'gate_ledger_validator_vectors.v4.json').read_text(encoding='utf-8'));tr=(R/'traceability_matrix.md').read_text(encoding='utf-8');pr=(R/'plan_review_findings.md').read_text(encoding='utf-8');print({'fixed':len({n['id'] for n in d['nodes']}),'tests':len(t['tests']),'groups':len(v['vectors']),'cases':sum(len(g['cases']) for g in v['vectors']),'schemas':len(list(R.glob('*.schema.json'))),'rq':len(set(re.findall(r'\bRQ-[0-9]{3}\b',tr))),'rk':len(set(re.findall(r'\bRK-[0-9]{2}\b',tr))),'pr':len(set(re.findall(r'\bPR-[0-9]{3}\b',pr)))})"

# baseline 组调用 / 无 monkeypatch（AST）
python -c "import ast;t=ast.parse(open(r'<plan>\tools\v5_plan_consistency_check.py',encoding='utf-8').read());print(sorted({n.func.attr for n in ast.walk(t) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr.endswith('_checks')}))"

# N 码字面量集合
Select-String -Path <plan>\tools\v5_plan_consistency_check.py -Pattern '"N([0-9]+)"' -AllMatches |
  ForEach-Object { $_.Matches } | ForEach-Object { $_.Value } | Group-Object | Sort-Object Name

# 逐码调用次数（临时副本探针，不写真实树）
python probe_counts.py <temp-tree>\plan verify
```

## 附录 C — 自测变异隔离性（`probe_isolation.py` 输出）

```
case | full_codes | codes_with_target_disabled | isolated?
N1  | N1            | -            | YES
N2  | N2,N4         | N4           | NO (still rejected by N4)
N3  | N15,N3,N4     | N15,N4       | NO
N4  | N4            | -            | YES
N5  | N5            | -            | YES
N6  | N6            | -            | YES
N7  | N5,N7         | N5           | NO
N8  | N8            | -            | YES
N9  | N9            | -            | YES
N10 | N10,N13       | N13          | NO
N11 | N11,N4        | N4           | NO
N12 | N12,N4        | N4           | NO
N13 | N13,N16       | N16          | NO
N14 | N13,N14,N16   | N13,N16      | NO
N15 | N15           | -            | YES
N16 | N16,N6,N7     | N6,N7        | NO
N17 | N17           | -            | YES
```

判读：N2/N3/N7/N10/N11/N12/N13/N14/N16 的变异在目标检查被禁用后**仍被拒**，说明 `--self-test` 的 `code in codes` 断言不足以证明这些检查有效；N6 虽然隔离，但其检查只覆盖聚合计数（TST-P1-1）。

复现该表的脚本（只读真实树、只写系统临时目录）：

```python
# probe_isolation.py — 用法: python probe_isolation.py <含 plan/ 的临时副本根>
import importlib.util, json, shutil, sys, tempfile
from pathlib import Path
PRISTINE = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location(
    "v5probe", PRISTINE / "plan" / "tools" / "v5_plan_consistency_check.py")
mod = importlib.util.module_from_spec(spec); sys.modules["v5probe"] = mod
spec.loader.exec_module(mod)
base = mod.load_baseline(); ORIG = base.check
def make_ctx(tmp):
    root = tmp / "v5"
    shutil.copytree(PRISTINE / "plan" / "baseline", root / "baseline")
    shutil.copytree(PRISTINE / "plan" / "tools", root / "tools")
    for n in (".gitattributes", "plan_manifest.v5.json", "plan_manifest.schema.v5.json",
              "plan_freeze_check.v5.txt", "import_manifest.v5.json", "v5-freeze-boundary.md"):
        if (PRISTINE / "plan" / n).is_file():
            (root / n).write_bytes((PRISTINE / "plan" / n).read_bytes())
    return mod.Ctx(root=root, baseline=root / "baseline" / "plan",
                   manifest=root / "plan_manifest.v5.json", schema=root / "plan_manifest.schema.v5.json",
                   freeze_output=root / "plan_freeze_check.v5.txt",
                   import_manifest=root / "import_manifest.v5.json",
                   boundary_record=root / "v5-freeze-boundary.md",
                   old_dir=tmp / "source-catalog-worker-recovery-2026-08-22",
                   governing=mod.GOVERNING, evidence_tools=mod.EVIDENCE_TOOLS, external=False)
def run(mutate, drop=None):
    with tempfile.TemporaryDirectory() as td:
        ctx = make_ctx(Path(td)); m = json.loads(ctx.manifest.read_text(encoding="utf-8"))
        mutate(ctx, m)
        ctx.manifest.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8", newline="\n")
        saved = (base.ERRORS, base.CHECKS); base.ERRORS, base.CHECKS = [], 0
        def filtered(cond, code, msg):
            if code == drop: base.CHECKS += 1; return
            ORIG(cond, code, msg)
        base.check = filtered
        try:
            mod.verify_manifest(base, ctx, mod.frozen_entries(ctx))
            codes = sorted({e.split(":", 1)[0] for e in base.ERRORS})
        finally:
            base.check = ORIG; base.ERRORS, base.CHECKS = saved
        return codes
for code, label, mutate in mod.N_CASES:
    full = run(mutate); without = run(mutate, drop=code)
    print(f"{code} | {','.join(full)} | {','.join(without) or '-'} | "
          f"{'YES' if not without else 'NO'}")
```

逐码调用次数（证明"无死码"）用同一套 `Ctx` 结构，把 `base.check` 换成计数器后调用 `mod.v5_checks` + `mod.verify_manifest` 即可（本次在临时副本上执行，得到第 4 节的 227 条 N 码分布）。

## 附录 D — 自包含复现脚本（保存为任意路径后运行；只写 `C:\v5rev*`）

```python
# evade.py — 用法: python evade.py <scenario> [full|fast]
import hashlib, json, shutil, subprocess, sys
from pathlib import Path
REPO = Path(r"C:\Users\郑曾波\Projects\company-wiki")
PLAN = REPO / "docs/plans/source-catalog-worker-recovery-v5-2026-09-03"
OLD = "source-catalog-worker-recovery-2026-08-22"
WORK = Path(r"C:\v5rev")
sha = lambda b: hashlib.sha256(b).hexdigest()
load = lambda p: json.loads(p.read_text(encoding="utf-8"))
def dump(p, o): p.write_text(json.dumps(o, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
def ent(m, path): return next(e for e in m["normative_files"] if e["path"] == path)
def regen(plan):
    for t in ("v5_version_reference_scan.py", "v5_equivalence_check.py"):
        subprocess.run([sys.executable, str(plan / "tools" / t)], capture_output=True, timeout=300)
def n6swap(plan):
    mp = plan / "plan_manifest.v5.json"; m = load(mp)
    a = ent(m, "baseline/plan/authorization_revalidation_receipt.schema.json")
    b = ent(m, "baseline/plan/gate_dag.v4.json")
    a["equivalence"], b["equivalence"] = b["equivalence"], a["equivalence"]; dump(mp, m)
def importrewrite(plan):
    mp, cp = plan / "plan_manifest.v5.json", plan / "import_manifest.v5.json"
    t = "baseline/plan/findings.md"; f = plan / t
    f.write_bytes(f.read_bytes() + b"\n<!-- evasion marker -->\n"); raw = f.read_bytes()
    m, c = load(mp), load(cp); e = ent(m, t); e["sha256"], e["size_bytes"] = sha(raw), len(raw)
    ce = next(x for x in c["files"] if x["target"] == t)
    ce["sha256"], ce["size_bytes"], ce["historical_v4_sha256"] = sha(raw), len(raw), sha(raw)
    dump(cp, c); m["capture_manifest"]["sha256"] = sha(cp.read_bytes()); dump(mp, m); regen(plan)
def nested(plan):
    d = plan / "baseline" / "plan" / "nested"; d.mkdir()
    (d / "plan_manifest.v4.json").write_bytes(b'{"fake": "parallel authority"}\n'); regen(plan)
def supersedes_retired(plan):
    mp = plan / "plan_manifest.v5.json"; m = load(mp)
    v4 = (plan / "baseline" / "history" / "plan_manifest.v4.json").read_bytes()
    m["supersedes"].append({"path": f"docs/plans/{OLD}/plan_manifest.v4.json", "sha256": sha(v4)}); dump(mp, m)
def fake_prefreeze(plan):
    mp = plan / "plan_manifest.v5.json"
    payload = (b'PASS: 12345 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}\n'
               b"READ_ONLY: no production database, registry, process, source, config, or network access\n")
    (plan / "plan_freeze_check.v5.txt").write_bytes(payload); m = load(mp)
    m["pre_freeze_check"]["reported_check_count"] = 12345
    m["pre_freeze_check"]["stdout_sha256"] = sha(payload); dump(mp, m)
def cmd_comment(plan):
    mp = plan / "plan_manifest.v5.json"; m = load(mp)
    m["pre_freeze_check"]["command"] = ("python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/"
        "baseline/plan/plan_consistency_check.py  # v5_plan_consistency_check.py"); dump(mp, m)
def rename_olddir(plan):
    new = plan.parent / (OLD + "-copy"); shutil.move(str(plan.parent / OLD), str(new))
    (new / "plan_manifest.v4.json").write_bytes(b'{"fake": "parallel authority"}\n')
def fake_head(plan):
    mp = plan / "plan_manifest.v5.json"; m = load(mp); m["plan_freeze_git_head"] = "0" * 40; dump(mp, m)
def extra_evidence(plan):
    mp = plan / "plan_manifest.v5.json"; m = load(mp)
    m["evidence_tools"].append({"path": "tools/does_not_exist.py", "sha256": "0" * 64, "size_bytes": 1}); dump(mp, m)
def baselinerun(plan):
    (plan / "baseline" / "plan" / "zzz_extra_input.txt").write_bytes(b"extra\n")
SCENARIOS = {"n6swap": n6swap, "importrewrite": importrewrite, "nested": nested,
             "supersedes_retired": supersedes_retired, "fake_prefreeze": fake_prefreeze,
             "cmd_comment": cmd_comment, "rename_olddir": rename_olddir, "fake_head": fake_head,
             "extra_evidence": extra_evidence, "baselinerun": baselinerun}
sid = sys.argv[1]
if WORK.exists(): shutil.rmtree(WORK, ignore_errors=True)
n = 1
while WORK.exists():
    n += 1; WORK = Path(rf"C:\v5rev{n}")
WORK.mkdir(parents=True); tree = WORK / "tree"
shutil.copytree(PLAN, tree / "plan"); (tree / OLD).mkdir()
(tree / OLD / "task_plan.md").write_bytes(b"retired copy\n")
subprocess.run(["git", "init", "-q"], cwd=str(tree), capture_output=True)
for k, v in (("user.email", "r@example.com"), ("user.name", "reviewer"), ("core.autocrlf", "false")):
    subprocess.run(["git", "config", k, v], cwd=str(tree), capture_output=True)
subprocess.run(["git", "add", "-A"], cwd=str(tree), capture_output=True)
subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=str(tree), capture_output=True)
SCENARIOS[sid](tree / "plan")
subprocess.run(["git", "add", "-A"], cwd=str(tree), capture_output=True)
subprocess.run(["git", "commit", "-q", "-m", sid], cwd=str(tree), capture_output=True)
p = subprocess.run([sys.executable, str(tree / "plan" / "tools" / "v5_plan_consistency_check.py"),
                    "--verify-manifest"], cwd=str(tree), capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=900)
print(f"scenario={sid} exit={p.returncode}"); print(p.stdout.strip()[:1200])
```
