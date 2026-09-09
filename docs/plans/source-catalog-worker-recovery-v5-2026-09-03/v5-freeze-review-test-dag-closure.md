# V5-2.1 冻结复审（测试 / DAG 轴）— 首轮 P1 关闭裁定 + 新发现

审查者：独立审查代理（测试/DAG 轴；未参与本计划任何文档或工具的编写）
复审对象：`docs/plans/source-catalog-worker-recovery-v5-2026-09-03`，冻结提交 `917b8d8`，仓库 `HEAD 85044ed`
被复审的首轮结论：`v5-freeze-review-test-dag.md`（verdict `accepted_with_findings`；6 条 P1 + 13 条 P2）
方法：不采信 `v5-freeze-record.md` 的整改声明；逐条重跑首轮公开配方，并针对新增机制（隔离自测、`V5-SET-NESTED`、`V5-PATH-SAFETY`、N9 载荷、N10 全量 Git 锚、N8 真实重跑）构造新对抗。所有破坏性试验只在 `C:\v5rev2` 临时副本上进行；真实冻结树只读。
环境：Windows + PowerShell 7，Python 3.13.9，jsonschema 4.26.0。

## 结论

**axis verdict: `accepted_with_findings`**

首轮 6 条 P1 中 **5 条 CLOSED、1 条 PARTIAL**：N6 逐件复算、N8 真实重跑、命令精确匹配、递归冻结集、`supersedes` 精确枚举均已实测生效，首轮公开配方全部被拒。但整改新增的两个机制各有一个可复现缺口：**N8 的"真实重跑"可被 checker 同目录下的 stdlib 影子模块劫持**（伪造产物仍 PASS 9174，且被植入文件无需提交），**N6/N7 新引入的 v4 冻结 manifest 锚自身不受任何检查保护**（改写该锚 + 同步记录即可让 manifest 继续声称 v4 等价，PASS 9174）。另有 7 条 P2（N9 处置载荷可被改写/标记改名/移出 `docs/plans` 绕过、`evidence_tools` 非精确集、畸形输入崩溃而非稳定编码、N10 Git 分支无自测变异、`V5-SET-GOVERNING` 仍恒真、`plan_freeze_git_head`/`frozen_at` 仍无锚、合同 §5.2 command 句未闭合）。冻结产物本身自洽：17 例/27 变异自测可复现，`7710`/`9174` 计数算术完全可解释，全部 12 个产物哈希与冻结记录逐位一致，独立复算的 8 项 coverage 与 manifest 相等。

## 1. 逐条裁定表（首轮 findings）

| 首轮 ID | 裁定 | 证据（命令 + 观测） | 说明 |
|---|---|---|---|
| TST-P1-1（N6 不重算逐件等价类） | **CLOSED** | `python C:\v5rev2\harness.py n6swap verify` → `exit=1`；`N6: baseline/plan/acceptance_thresholds.md: declared unproven_new_baseline, recomputed crlf_only from bytes`；`N6: … label crlf_only contradicts v5-baseline-equivalence.json`；`N7: artifact … is labelled unproven but matches the v4 frozen bytes` | 计数守恒的标签互换现在由**逐件字节复算**（checker line 363）+ 证据 `groups` 交叉核对（368）+ v4 锚（398）三重拒绝；隔离审计显示 N6 在 `ONLY={"N6"}` 下即由 363/368 触发（附录 B） |
| TST-P1-2（导入字节无可再生锚） | **PARTIAL** | ① 原配方 `harness.py importrewrite verify` → `exit=1`：`V5-EVIDENCE-CHECK: … inventory.json differ`、`N8: a fresh default-mode run does not reproduce plan_freeze_check.v5.txt`；② 全协同配方 `harness.py importrewrite_v2 verify` → **`PASS: 9174 checks`**；③ 锚绕过 `harness.py v4anchor_bypass verify` → **`PASS: 9174 checks`** | 原配方被拒（证据未同步 + N8 重跑不一致）；但"改写字节 + 同步 capture/manifest/evidence + 重生成证据 + 提交"仍 PASS，且新增的 v4 锚可被改写（见 NEW-P1-2）。N10 已覆盖 51 冻结项 + manifest（未跟踪/被改写即 red，见 §3），故剩余暴露面 = 记录 §6.3 自述的"新提交"类 |
| TST-P1-3（N8 未绑定本 checker 输出） | **CLOSED** | `harness.py fake_prefreeze verify` → `exit=1`；`N8: a fresh default-mode run does not reproduce plan_freeze_check.v5.txt`（line 441） | 伪造 `PASS: 12345 checks`（计数 JSON 正确、哈希自洽）被真实重跑逐字节比对拒绝。**但重跑预言机本身可被劫持 → NEW-P1-1** |
| TST-P1-4（command 只做子串匹配） | **CLOSED** | `harness.py cmd_comment verify` → `exit=1`；`N4: 'python …/v5_plan_consistency_check.py' was expected`；`N8: command must invoke exactly the frozen checker entry: ['…/baseline/plan/plan_consistency_check.py', 'v5_plan_consistency_check.py']` | schema `const` + 唯一 `.py` token + 禁 `#` 三重判据 |
| TST-P1-5（非递归 glob） | **CLOSED** | `harness.py nested verify` → `exit=1`；`V5-SET-NESTED: unexpected files below baseline/plan/**: ['nested/plan_manifest.v4.json']`；`N13: files below baseline/plan/** are not enumerated`；`V5-SET-IMPORTED: found 49` | 递归枚举 + 专用编码；junction 变体 `harness.py baseline_junction verify` 亦被 `V5-SET-NESTED` + `V5-PATH-SAFETY` 拒绝（`frozen entry traverses a symlink/reparse point`） |
| TST-P1-6（`supersedes` 后缀匹配 + 回退） | **CLOSED** | `harness.py supersedes_retired verify` → `exit=1`：`N2: manifest references a retired plan directory`、`N4: … not one of […]`、`N11: supersedes must be exactly ['baseline/history/plan_manifest.v4.json', 'baseline/history/plan_manifest.v3.json']`；`harness.py supersedes_lookalike verify` → `exit=1`：`N11: supersedes path is not a canonical in-tree path` | schema `enum` + `maxItems: 2`，N11 无回退分支 |
| TST-P2-1（`V5-SET-GOVERNING` 恒真） | NOT CLOSED | checker line 230 仍为 `len(ctx.governing) == EXPECTED_GOVERNING`（模块常量自比）；`probe_counts2.py` 显示该码调用 1 次且恒真 | 建议：从 `declared`/`entries` 统计 `v5_own` 条目数并与 3 比对 |
| TST-P2-2（自测断言过弱） | **CLOSED** | `--self-test` → `17 cases / 27 mutations; failures=none`，每条 `rejected (full+isolated)`；隔离逐行审计（附录 B）显示每个变异的目编码均在语义正确的行触发 | 隔离模式证明"目标编码单独即可拒绝"，已消除"别的检查顺手拦住"的假阳性 |
| TST-P2-3（自测 `external=False` 跳过 N10 Git 臂） | NOT CLOSED | 附录 B：N10 变异只在 line 484（自包含）触发；`_n10` 的 `needs_git=False`；27 个变异中只有 N8.2 建 Git 仓库 | N10 的 Git 臂是本次最重要的新机制之一，却没有任何自测变异覆盖（实测可触发，见 §3 的 red_exit/未跟踪用例） |
| TST-P2-4（N9 锚定单一目录名） | **PARTIAL** | 控制组 `harness.py n9_undeclared verify` → `exit=1`：`N9: retired plan copy not declared …`、`N9: declared 1 retired dirs but found 2`；但 `n9_marker_renamed` / `n9_outside_plans` / `n9_boundary_rewrite` 均 `PASS`（见 NEW-P2-1/2/3） | 检测面从"单一路径"升级为"含标记的兄弟目录 + 申报 + 摘要复算"，但标记定义、扫描范围与申报文本都仍可被规避 |
| TST-P2-5（`plan_freeze_git_head`/`frozen_at` 无锚） | NOT CLOSED | `harness.py fake_head verify` → `PASS: 9174`；`harness.py fake_frozen_at verify` → `PASS: 9174` | checker 仍未与 `git rev-parse HEAD` 比对，`frozen_at` 仅格式校验 |
| TST-P2-6（`evidence_tools` 非精确集） | NOT CLOSED | `harness.py extra_evidence verify` → `PASS: 9174`（追加 `{"path":"tools/does_not_exist.py","sha256":"0"*64,"size_bytes":1}`） | N17 仍只校验两条固定工具；schema 只有 `minItems: 2`，无 `maxItems` |
| TST-P2-7（8866 vs 8867 计数不可复现） | **CLOSED** | 真实树 `--verify-manifest` → `PASS: 9174 checks`（14.5s）；`--self-test` 与记录 §2/§7 一致 | 记录 §2 已声明计数是"运行环境观测值"，并给出首轮 8866 → 本轮 9174 |
| TST-P2-8（被取代的 v4 manifest 无锚） | NOT CLOSED → **升级为 NEW-P1-2** | `harness.py v4anchor_bypass verify` → `PASS: 9174` | 整改把该文件变成 N6/N7 的**承重锚**，但它既不在冻结集、也不在 N10 目标集内 |
| TST-P2-9（畸形输入崩溃而非稳定编码） | NOT CLOSED | `harness.py malformed_manifest verify` → exit 1 + `json.decoder.JSONDecodeError`；`harness.py entry_missing_path verify` → exit 1 + `KeyError: 'path'`（checker line 298） | 仍 fail-closed（exit 1），但无可机读编码 |
| TST-P2-10（丢弃 baseline 组） | **PARTIAL** | AST：`plan_manifest_checks` 仍为 0 次调用；`V5-PATH-SAFETY` 新增 102 条检查（line 242/245） | reparse/symlink 安全面已由 `V5-PATH-SAFETY` 补上（junction 实测被拒）；`MANIFEST-EXCLUSIONS` 仍无等价物 |
| TST-P2-11（N6 诊断误归因） | NOT CLOSED | `harness.py case_variant_path verify` → `N13: missing=['baseline/plan/README.md'] extra=['baseline/plan/Readme.md']` 与 `N6: equivalence_summary … != recomputed {… 'unproven_new_baseline': 9, 'v5_own': 3}` 同时出现 | 路径缺项仍被 N6 报成"等价性不符" |
| TST-P2-12（casefold/重复检查被遮蔽） | NOT CLOSED（信息性） | 同首轮；schema `uniqueItems` 先于 N13 触发 | 属纵深防御，非缺陷 |
| TST-P2-13（§5.2 "schema 须同时出现在 command"） | NOT CLOSED | `git diff 454f632..HEAD -- v5-version-contract.md` 只改了 §3 计数，§5.2 该句未改；manifest `pre_freeze_check.command` 仍只含 checker 路径 | 合同文本与交付物的字面冲突未消除 |

## 2. 新增 findings

| ID | Sev | Finding | 证据（命令 + 观测） | Required fix |
|---|---|---|---|---|
| NEW-P1-1 | **P1** | **N8 的"真实重跑"可被劫持**：重跑以 `[sys.executable, <plan>/tools/v5_plan_consistency_check.py]` 启动子进程，因此子进程 `sys.path[0]` = `tools/`；在该目录植入任何影子 stdlib 模块（如 `json`）即可在 `V5_PREFREEZE_CHILD=1` 时输出任意字节并 `os._exit(0)`，而 `tools/` 除 checker 外**不在冻结集、不在 N10 目标、不在 `V5-SET-NESTED`、不在证据范围**——植入文件甚至**无需提交**（实测：把植入物 `git rm --cached` 后仍是 `?? tools/json/`、`?? tools/_n8_fake.txt`，检查器仍 `PASS: 9174`）。 | ① `harness.py n8_hijack_pkg verify`（植入 `tools/json/__init__.py` + 伪造产物）→ **`PASS: 9174 checks`**，产物内容实测为 `PASS: 12345 checks; {"fixed_nodes": 115, …}`，pyc 落在 `tools/json/__pycache__`（B3 不检查该路径）；② `harness.py n8_hijack_clean verify`（`tools/json.py` 自删 `tools/__pycache__`）→ **`PASS: 9174`**；③ 朴素变体 `harness.py n8_hijack verify`（`tools/json.py` 不自清）→ `exit=1`，仅因 `B3-BOUNDARY-DRIFT: verification left __pycache__ behind: …tools\__pycache__`；④ 植入物改为未跟踪后重跑 → 仍 `PASS: 9174`；⑤ 修复可行性实测：`python -P tools\script.py` 与 `python -I tools\script.py` 均导入 stdlib `json`（`RAN C:\Miniconda\Lib\json\__init__.py`），不加参数则 `SHADOWED`。 | 重跑子进程改用 `-I`（或 `-P`）并清空 `PYTHONPATH`；同时把 `tools/` 纳入枚举/冻结（或断言其不含除已知集合外的 `.py`，尤其不得与 stdlib 模块同名）。 |
| NEW-P1-2 | **P1** | **v4 冻结 manifest 锚可被绕过**：N6/N7 用 `baseline/history/plan_manifest.v4.json` 作为"独立、不可再生"的字节锚，但该文件不在 51 项冻结集、不在 N10 的 Git 目标集、也不像 v3 那样在代码中钉哈希；改写它 + 同步 `capture` 的 `historical_v4_sha256`、manifest 条目、`capture_manifest.sha256`、`supersedes[].sha256`、两份证据与其绑定哈希，manifest 就能继续**声称** `crlf_only`/`v4_exact` 等价于 v4 冻结，而实际字节已变。 | `harness.py v4anchor_bypass verify` → **`PASS: 9174 checks`**（改写 `baseline/plan/gate_state_machine.md` 首行、把 v4 manifest 中该件的 sha256 改为新字节的 LF 归一化哈希、同步全部可写记录并重生成证据后提交）；对照：自测 N7.2 只同步"可写记录"而未改 v4 锚，故被 `N7`（line 398）拒绝。 | 把 v4 manifest 的期望 sha256 也硬编码进 checker（与 `IMMUTABLE_HISTORY_SHA256` 对 v3 的做法一致），并把 `baseline/history/**` 纳入 N10 目标集；在记录中明确"该锚可被同一次提交整体改写"这一残余（现有 §6.3 只覆盖 manifest 与 51 项）。 |
| NEW-P2-1 | P2 | N9 处置载荷可被改写：`v5-freeze-boundary.md` 不在冻结集、不在 N10 目标集，任何并列副本都可以被"申报"为 `NON_AUTHORITATIVE` 而 PASS。 | `harness.py n9_boundary_rewrite verify`（新增一份含标记的兄弟副本 + 重写 JSON 块，`file_count`/`inventory_sha256` 按实测填写）→ **`PASS: 9227 checks`**；对照 `n9_undeclared`（同副本不申报）→ `exit=1`。 | 把 `v5-freeze-boundary.md` 加入 N10 目标集（或在其 manifest 中做哈希绑定），使"申报"本身不可被静默替换。 |
| NEW-P2-2 | P2 | N9 标记改名即失效：`RETIRED_MARKERS` 是三个固定文件名，重命名它们后该目录不再被视为候选。 | `harness.py n9_marker_renamed verify`（把副本内 `plan_consistency_check.py`/`gate_dag.v4.json`/`plan_manifest.v3.json` 改名，并把处置块改为 `retired_dirs: []`）→ **`PASS: 9121 checks`**。`v5-freeze-boundary.md` §5 声称"改名、复制、新建副本都会触发 N9"，该断言对"改目录名"成立、对"改标记文件名"不成立。 | 判据改为内容/结构特征（如"含 4 个 `.v4.json` 实例 + 29 个 schema"）或直接对 `docs/plans/` 下所有目录做清单比对；同时修正边界记录的措辞。 |
| NEW-P2-3 | P2 | N9 只扫描 `docs/plans/` 的直接子目录，副本移到该目录之外即不可见。 | `harness.py n9_outside_plans verify`（把副本移到 `<repo>/docs/retired-copy/`，处置块改为 `retired_dirs: []`）→ **`PASS: 9121 checks`**。 | 扫描范围扩展到 `docs/**`（或仓库内任何含计划标记的目录）。 |
| NEW-P2-4 | P2 | `baseline/plan/` 下的**空目录**不可见：`nested_plan_files` 只统计文件。 | `harness.py n9_empty_dir verify`（`mkdir baseline/plan/empty_subdir`）→ **`PASS: 9174 checks`**。 | 一并统计目录（或断言 `baseline/plan` 下无子目录）。 |
| NEW-P2-5 | P2 | N10 的 Git 臂没有自测变异：27 个变异中只有 N8.2 建 Git 仓库，N10 只由 line 484 的自包含检查触发。 | 附录 B 隔离审计：N10 变异的触发行号只有 `[484]`。 | 增补"改写已跟踪冻结件后断言 N10 red"的变异（真实树已实测可触发）。 |
| NEW-P2-6 | P2 | `tools/`（除 checker 外）不被任何检查枚举：既不在冻结集/N10，也被证据范围排除——这是 NEW-P1-1 的根因，也意味着新增 `.py` 完全隐形。 | 见 NEW-P1-1 的植入物；`frozen_entries` 仅 `baseline/plan/**` + 3 个治理件。 | 在 `v5_checks` 中断言 `tools/` 的文件集合等于已知清单（两个证据工具 + checker + 生成器），或把生成器一并纳入绑定。 |
| NEW-P2-7 | P2 | `v5-version-contract.md` §5.2 的 command 句仍未闭合（同 TST-P2-13）：合同要求 schema 与 checker"同时出现在 `pre_freeze_check.command`"，交付 command 仍只含 checker。 | `git diff 454f632..HEAD -- v5-version-contract.md` 只改 §3 计数；manifest `pre_freeze_check.command` = `python docs/plans/…/tools/v5_plan_consistency_check.py`。 | 修改 command（双文件校验形式）或修订合同措辞。 |

## 3. 独立复算与再验证（全部通过）

| 项目 | 命令 | 观测 |
|---|---|---|
| 自测 17 例 / 27 变异 | 真实树 `… --self-test` | 27 行 `rejected (full+isolated)`；`SELF-TEST: 17 cases / 27 mutations; failures=none`；exit 0 |
| 默认模式 | 真实树 `…` | `PASS: 7710 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}`（3.4s） |
| `--verify-manifest` | 真实树 `… --verify-manifest` | `PASS: 9174 checks; …`（14.5s） |
| coverage 独立复算 | 独立脚本解析冻结 JSON | `fixed_dag_nodes 115`、`stable_test_ids 315`、`validator_vector_groups 18`、`validator_vector_cases 140`、`schemas 29`、`requirements 60`、`risks 44`、`plan_review_findings 105` — 与 manifest `coverage_counts` **逐字段相等** |
| 产物哈希 | `Get-FileHash` × 12 | 与记录 §1 表格逐位一致（manifest `afedfdd8…`、产物 `8c01b9dc…`、schema `4e7ce1e6…`、checker `a40a3d7a…`、生成器 `459b7c7d…`、inventory `150ae6a4…`、equivalence `79ac6ca4…`、boundary `f14f8cfc…`、capture `da7d116e…`） |
| baseline 组继承 | AST + 触发实验 | 8 组各 1 次（`dag_checks` 2 次）；`immutable_history_checks`/`plan_manifest_checks` 仍 0 次；无 `base.*` 函数重绑（仅 self_test 830/835 的 ERRORS/CHECKS 保存恢复）。`harness.py baseline_groups verify` → `SCHEMA-ID-BINDING`/`INSTANCE-SCHEMA`/`PROSE-DUAL-AUTH`/`VECTOR-OUTCOME`/`VECTOR-REASON-RULE`；`harness.py dag_mutation verify` → `DAG-ROLLBACK-STATE`/`REVIEW-OVERRIDE`/`TEST-LIFECYCLE-NODE`（22 条错误） |
| 计数算术 | `probe_counts2.py` | `7710 = 7494（baseline 套件）+ 216（v5_checks）`；`216 = 164 首轮 + 1 V5-SET-NESTED + 102 V5-PATH-SAFETY + 1 tools/__pycache__ B3 − 52 迁出的 N9`；`9174 = 7710 + 482（N1–N17 检查）+ 982（N13 coverage 复算的第二次 dag_checks）` |
| N 码可达性 | `probe_counts2.py` 逐码计数 | 每条码 ≥1 次（N1 1、N2 1、N3 1、N4 1、N5 51、N6 145、N7 145、N8 6、N9 56、N10 53、N11 5、N12 1、N13 6、N14 1、N15 2、N16 3、N17 4）；无死码 |
| 红旗必 exit 1 | `red_exit`/`malformed`/`entry_missing_path`/无 Git/未跟踪 | 全部 exit 1；`N10: tracked file was rewritten after freeze`、`N10: not tracked at HEAD …`、`N10: cannot resolve the git repository root` 三类 fail-closed 均实测 |
| 输出确定性 | `PYTHONHASHSEED=0/1` × 默认/verify | 两次 stdout 逐字节相同 |
| 静默异常 | AST | 6 处 `except`：1 处 stdout 兼容 `pass`（无检查语义），其余 5 处均 fail-closed（`check(False)`/回退为不一致值） |

## 4. 残余风险 / 未覆盖

1. `importrewrite_v2` / `v4anchor_bypass` 这类"改写 + 同步全部记录 + 提交"的协同改写，超出任何树内 checker 的检测能力；记录 §6.3 已声明该残余，审查防线落在 Git 提交 diff。
2. NEW-P1-1 的植入物在真实仓库中会出现在 `git status`/提交 diff 里；本轴只评估 checker 的判定能力，不评估人工 diff 复核的可靠性。
3. 未实测 Windows 权限拒绝（不可读目录）对 `retired_candidates`/`inventory_digest` 的影响（预期 fail-closed 崩溃）。
4. 未对 48 个导入件做内容级语义审查（本轴只覆盖字节/哈希/集合/计数/负例）。
5. 本次所有实验在 `C:\v5rev2\*` 副本上进行；真实冻结树未被写入（`baseline/**`、`tools/**`、冻结产物均无改动，`git status` 仅显示本审查文件为新增）。

## 附录 A — 全部对抗场景与结果

模式 `verify` = 真实 CLI `--verify-manifest`；全部先 `git init + commit`，再变异、再提交（模拟"冻结产物已入库、审查者 checkout 后验证"）。

| 场景 | 变异 | 结果 | 判定 |
|---|---|---|---|
| `n6swap` | 同类内互换 `crlf_only`↔`unproven` 标签（计数守恒） | `exit=1`：N6(363/368) + N7(398) | TST-P1-1 CLOSED |
| `importrewrite` | 改写未证明件 + 同步 capture/manifest 条目（不重生成证据） | `exit=1`：`V5-EVIDENCE-CHECK` + `N8`(441) | 原配方被拒 |
| `importrewrite_v2` | 同上 + 重生成证据 + 同步 `evidence` 绑定 | **`PASS: 9174`** | TST-P1-2 PARTIAL |
| `fake_prefreeze` | 伪造 `PASS: 12345 checks`（计数 JSON 正确、哈希自洽） | `exit=1`：`N8`(441) | TST-P1-3 CLOSED |
| `n8_hijack` | 伪造产物 + `tools/json.py`（不自清） | `exit=1`：仅 `B3-BOUNDARY-DRIFT`（tools/__pycache__） | 朴素劫持被 B3 挡住 |
| `n8_hijack_pkg` | 伪造产物 + `tools/json/__init__.py` | **`PASS: 9174`** | **NEW-P1-1** |
| `n8_hijack_clean` | 伪造产物 + 自清 `tools/json.py` | **`PASS: 9174`** | **NEW-P1-1** |
| `cmd_comment` | command 改为调用旧 checker，v5 名藏在注释 | `exit=1`：N4 + N8(408/411) | TST-P1-4 CLOSED |
| `nested` | `baseline/plan/nested/…` + 重生成证据 | `exit=1`：`V5-SET-NESTED`/`V5-SET-IMPORTED`/`V5-SET-TOTAL`/N13/N7/N8 | TST-P1-5 CLOSED |
| `baseline_junction` | `baseline/plan/junction_sub` 指向外部目录 | `exit=1`：`V5-SET-NESTED` + `V5-PATH-SAFETY`（resolve 越界 + reparse 链） | 无缺陷（被正确拒绝） |
| `supersedes_retired` | 追加旧目录内链节 | `exit=1`：N2 + N4 + N11 | TST-P1-6 CLOSED |
| `supersedes_lookalike` | 西里尔字母形近路径 | `exit=1`：N4 + N11 | TST-P1-6 CLOSED |
| `v4anchor_bypass` | 改写 `crlf_only` 件 + 改写 v4 锚 + 同步全部记录 | **`PASS: 9174`** | **NEW-P1-2** |
| `red_exit` | 仅漂移一个冻结件（不提交） | `exit=1`：`N10`(rewritten) + N5/N6/N7/N8/证据 | 红旗 exit 1 + N10 生效 |
| `n9_undeclared`（控制） | 新增含标记的兄弟副本、不申报 | `exit=1`：`N9`(469/479) | N9 基本功能有效 |
| `n9_boundary_rewrite` | 新增副本 + 重写处置块申报 | **`PASS: 9227`** | **NEW-P2-1** |
| `n9_marker_renamed` | 副本标记改名 + 申报为空 | **`PASS: 9121`** | **NEW-P2-2** |
| `n9_outside_plans` | 副本移出 `docs/plans/` + 申报为空 | **`PASS: 9121`** | **NEW-P2-3** |
| `n9_empty_dir` | `baseline/plan/` 下空目录 | **`PASS: 9174`** | **NEW-P2-4** |
| `baseline_groups` | 改 schema `$id` + prose 令牌 + vector 期望码 | `exit=1`：`SCHEMA-ID-BINDING`/`INSTANCE-SCHEMA`/`PROSE-DUAL-AUTH`/`VECTOR-*` | 继承组仍生效 |
| `dag_mutation` | 删 DAG 节点 + 同步 coverage | `exit=1`：`DAG-ROLLBACK-STATE`/`REVIEW-OVERRIDE`/`TEST-LIFECYCLE-NODE` | 继承组仍生效 |
| `extra_evidence` | 追加不存在的 evidence_tools 条目 | **`PASS: 9174`** | TST-P2-6 NOT CLOSED |
| `malformed_manifest` | manifest 非法 JSON | `exit=1` + `JSONDecodeError` | TST-P2-9 NOT CLOSED |
| `entry_missing_path` | 条目缺 `path` | `exit=1` + `KeyError: 'path'`(line 298) | TST-P2-9 NOT CLOSED |
| `case_variant_path` | 路径改大小写 | `exit=1`：N13 + N6（误归因） | TST-P2-11 NOT CLOSED |
| `fake_head` | `plan_freeze_git_head` 置全 0 | **`PASS: 9174`** | TST-P2-5 NOT CLOSED |
| `fake_frozen_at` | `frozen_at` 置 1999-01-01 | **`PASS: 9174`** | TST-P2-5 NOT CLOSED |
| 无 Git 副本 | 删除 `.git` 后运行 | `exit=1`：`N10: cannot resolve the git repository root` | fail-closed |
| 未跟踪冻结件 | `git rm --cached findings.md` | `exit=1`：`N10: not tracked at HEAD …` | fail-closed |
| `unproven_restore_v4` | 用退役副本覆盖 v5 的 `README.md` 并保持 unproven 标签 | `exit=1`，但由 `SCHEMA-README-CLOSED-SET`/`PROSE-DUAL-AUTH` 触发 | 场景构造无效（退役副本字节与 v4 冻结哈希不符），不计入；N7 的"unproven 却匹配 v4"分支已由 `n6swap` 的 line 398 实测覆盖 |

## 附录 B — 隔离模式逐行审计（`probe_isolation2.py`）

对 checker 自测的 27 个变异，在 `ONLY={code}` 下记录触发检查的**行号**：

```
N1 [291]   N2 [304]   N3 [308]   N4 [314]   N5 [336]
N6.1 [363,368]        N6.2 [363,368,371]
N7.1 [386,398]        N7.2 [398]            N7.3 [378,386,388,392]
N8.1 [432]            N8.2 [441]            N8.3 [408,411]
N9.1 [469,479]        N9.2 [461]            N9.3 [459,461,469,479]
N10 [484]
N11.1 [522,528,532]   N11.2 [522,528,532]
N12 [538]             N13.1 [317,325]       N13.2 [317,323]
N14 [543]             N15 [546,549]         N16 [555]
N17.1 [563]           N17.2 [570]
```

判读：每个变异的目编码都命中**语义正确**的检查行（例：N6.1 命中 363「逐件字节复算」与 368「证据 groups 交叉核对」；N8.2 命中 441「真实重跑逐字节比对」；N13.2 命中 323「嵌套文件」）。未发现"编码因无关原因触发"的隔离漏洞；唯一覆盖缺口是 N10 只由 484 触发（其 Git 臂无变异，NEW-P2-5）。

## 附录 C — 计数算术

| 分量 | 条数 | 来源 |
|---|---|---|
| baseline 套件 | 7494 | 1825 schema + 982 dag + 224 operation + 3852 registry + 569 vector + 6 pointer + 32 prose + 3 prefreeze + 1 内联 history |
| v5 冻结集/路径安全/边界/证据 | 216 | 首轮 164 + `V5-SET-NESTED` 1 + `V5-PATH-SAFETY` 102 + `tools/__pycache__` B3 1 − 迁出的 N9 52 |
| **默认模式** | **7710** | 与 `plan_freeze_check.v5.txt` 的 `reported_check_count` 一致 |
| N1–N17 | 482 | 逐码计数见 §3 |
| 第二次 `dag_checks()`（N13 coverage 复算） | 982 | `verify_manifest` line 329 |
| **`--verify-manifest`** | **9174** | 7710 + 482 + 982 |

## 附录 D — 复现脚本（保存为任意 ASCII 路径；只写临时副本）

`harness.py` 的骨架（完整脚本见审查者临时目录 `C:\v5rev2\harness.py`）：

```python
# 1) 复制真实 plan 目录到 <work>/repo/docs/plans/<plan>，并复制退役副本为兄弟目录
# 2) git init + commit（使 N10 的 Git 臂激活）
# 3) 应用一个变异；再 git add/commit（red_exit 除外）
# 4) 运行 [sys.executable, <plan>/tools/v5_plan_consistency_check.py, "--verify-manifest"]
# 关键变异（节选）：
def n8_hijack_pkg(plan):            # NEW-P1-1
    fake_prefreeze(plan)            # 伪造 PASS: 12345 checks 并同步 manifest 绑定
    (plan/"tools"/"_n8_fake.txt").write_bytes((plan/"plan_freeze_check.v5.txt").read_bytes())
    pkg = plan/"tools"/"json"; pkg.mkdir()
    (pkg/"__init__.py").write_text(
        "import os, sys, sysconfig\n"
        "if os.environ.get('V5_PREFREEZE_CHILD') == '1':\n"
        "    sys.stdout.buffer.write(open(os.path.join(os.path.dirname("
        "os.path.dirname(__file__)), '_n8_fake.txt'), 'rb').read())\n"
        "    sys.stdout.flush(); os._exit(0)\n"
        "_real = os.path.join(sysconfig.get_paths()['stdlib'], 'json', '__init__.py')\n"
        "g = globals(); g['__file__']=_real; g['__name__']='json'; g['__package__']='json'\n"
        "g['__path__']=[os.path.dirname(_real)]\n"
        "exec(compile(open(_real,'rb').read(), _real, 'exec'), g)\n",
        encoding="utf-8", newline="\n")

def v4anchor_bypass(plan):          # NEW-P1-2
    rel = "baseline/plan/gate_state_machine.md"; f = plan/rel
    raw = f.read_bytes().replace(b"# ", b"#  ", 1); f.write_bytes(raw)
    hist = sha(raw.replace(b"\r\n", b"\n"))
    hp = plan/"baseline"/"history"/"plan_manifest.v4.json"; v4 = load(hp)
    for e in v4["normative_files"]:
        if e["path"] == "gate_state_machine.md": e["sha256"] = hist
    dump(hp, v4)                     # 改写承重锚
    sync_capture(plan, rel, raw, historical=hist)   # capture + manifest 条目 + capture_manifest.sha256
    for e in load(plan/"plan_manifest.v5.json")["supersedes"]:
        if e["path"].endswith("plan_manifest.v4.json"): e["sha256"] = sha(hp.read_bytes())
    regen(plan); sync_evidence_binding(plan)        # 重生成两份证据并同步 manifest.evidence
```

运行：`python harness.py <scenario> verify`；`<scenario>` ∈ `n6swap/importrewrite/importrewrite_v2/fake_prefreeze/n8_hijack/n8_hijack_pkg/n8_hijack_clean/cmd_comment/nested/baseline_junction/supersedes_retired/supersedes_lookalike/v4anchor_bypass/red_exit/n9_undeclared/n9_boundary_rewrite/n9_marker_renamed/n9_outside_plans/n9_empty_dir/baseline_groups/dag_mutation/extra_evidence/malformed_manifest/entry_missing_path/case_variant_path/fake_head/fake_frozen_at`。
