# W13-CWP-GATES 独立审查报告（review）

- 审查者角色：**独立审查 agent**（非实现者；由 C 节点独审要求派出，绑定最终代码 commit 与变更文件 SHA）。
- 被审代码 commit：`56baea4cdd8c89b5cf778d0bda948c31ec5af162`（分支 `codex/w13-cwp-gates-20261024`，base `a31300a7`；其后仅证据/文档 commit cab4ed82/bf0cc52f/a8045416，不改被审代码）。
- 审查方式：逐条对照需求卡 `docs/plans/du11-source-closure-2026-10-18/harness_lanes/20261024/W13-CWP-GATES.md`（读自主仓，worktree 未包含该卡文件）与同目录 `INTERFACES.md`；所有命令本人实际执行，不采信交接自述。审查期间未修改任何产品/测试文件；scratch 全部位于系统 TEMP（`%TEMP%\w13-review\`、`w13-g07-*`），worktree `git status` 前后均干净（0 行未提交变更）。

## 1. 实际执行的命令与退出码

| # | 命令 | 退出码 | 结果 |
|---|---|---|---|
| C1 | `git diff a31300a7..56baea4c --name-status` / `--stat` | 0 | 10 文件，535+/145-；仅写范围内文件；`src/ scripts/ config/ .github/` diff 为空 |
| C2 | `git diff a31300a7..56baea4c -- tools/changed_unit_tests.py` | 0 | 空输出（未改动；base/HEAD blob 均 `d341b386ce6`） |
| C3 | FAST_CONTRACT_CASES / CURRENT_CI_REGRESSION_CASES 的 AST dump 对比（base vs HEAD） | 0 | 两组常量逐成员一致；29 成员、内部零重复 |
| C4 | 复制真实 `.githooks/pre-push` 到 `%TEMP%\w13-review\hooktest\`（无 tools/）后 `sh .githooks/pre-push` | **1** | 输出 `pre-push gate: tools/pre_push_gate.py missing - cannot validate this push`；退出 1 |
| C5 | `echo "refs/heads/x <a8045416> refs/heads/x <56baea4c>" \| python tools/pre_push_gate.py --push-checks`（真实 SHA、真实子进程） | **0** | `Push scope: no behavior changes; ran 29 target(s) (local_fast_pass); full_validation_pending: …`；154 passed（本机 130.32s）；绿文案 `Push fast gate GREEN (local_fast_pass for the ran scope only)` |
| C6 | `python -m pytest -q -p no:cacheprovider tests/unit/test_daily_push_policy.py -k real_push` | 0 | 3 passed in 31.24s |
| C7 | 卡内全量测试命令（7 个文件，见卡 C 节） | 0 | **145 passed in 69.56s** |
| C8 | 卡内 ruff 命令（9 个文件） | 0 | All checks passed! |
| C9 | `python scripts/config_doctor.py` | **1** | `CONFIG-PROBLEM: catalog_dir is not a directory: …\.source_catalog`（worktree 无该数据目录；脚本与 base 逐字节一致 → 环境限制，先于本包存在） |
| C10 | 串行重跑 3 个 xdist 失败文件（test_narrative_selector_binding.py、test_w04_source_transport.py、test_reading_structured_qa.py） | 0 | **58 passed in 80.81s**（证实 19 例为 xdist tmp-file 抖动类） |
| C11 | `python -m pytest -q tests/contract/test_b10_read_chain.py` | **1** | 3 failed, 13 passed（`test_b10_no_new_column_value_handoff` 等 3 个 ratchet；`src/` 与 base 逐字节一致 → 基线已红，先于本包） |
| C12 | 全树 `grep -rn "_run_parallel_pytest_gates"`（排除 .git） | 0 | 代码/测试零残留；仅历史 plan/review 文档提及（docs/plans/document-understanding-2026-10-13/**、w13 子 PWF 说明） |
| C13 | `grep -rn "safe to push"`（tools/ tests/ .githooks/ .pre-commit-config.yaml .github/ scripts/ src/） | 0 | 仅新测试的两处反向断言（test_daily_push_policy.py:160,169）；产品代码零残留 |
| C14 | G07 矩阵 scratch（系统 TEMP 自建 Git 仓，import `tools.changed_unit_tests` + `_push_targets`，12 场景） | 0 | 结果见 §3-G07 |
| C15 | `git ls-tree 56baea4c -- <7 文件>` + `git hash-object` 工作区文件 | 0 | 全部被审文件 blob 前缀与任务给定一致；工作区与 commit 内容一致 |

被审文件 SHA 绑定（blob@56baea4c / sha256 前 12 位，sha256 取自 committed blob 字节）：

| 文件 | git blob | sha256 前缀 |
|---|---|---|
| tools/pre_push_gate.py | 61b09b3ee83f | 879905f697de |
| .githooks/pre-push | 3f7f309e8690 | ce4822bb5a08 |
| .pre-commit-config.yaml | cdfcbc06903d | be244d4c63e5 |
| tests/unit/test_daily_push_policy.py | 82d8b57e1949 | 7aaab7779e71 |
| tests/unit/test_ci_push_selection.py | 8ada4baa0b67 | 5740e2dc4b7c |
| tests/unit/test_pre_push_parallel_phases.py | c500e6810977 | e259bc8052fa |
| tools/changed_unit_tests.py（未改，base 同 blob） | d341b386ce63 | 6774558e8fdc |

## 2. 逐需求结论

### G01 — PASS（保留入口与真实 stdin，无绕过面）
- `.githooks/pre-push:23` 保持 `python "$ROOT/tools/pre_push_gate.py" --push-checks`；hook 不消费 stdin，Git ref stdin 原样到达 `pre_push_gate.py:274`（`sys.stdin.read()`）。diff 中该行为 context 未动。
- 无跳过环境变量、无人工授权文件、无缓存绿灯：hook 全文与 `tools/pre_push_gate.py` 均无 skip env/授权文件/缓存逻辑；`tests/unit/test_daily_push_policy.py:207-211` 反向断言 hook 无 `--fast-contracts-only`、无 SKIP。

### G02 — PASS（日常 push 永不隐式启动整个 tests/unit）
- `tools/pre_push_gate.py:190-206 _push_targets`：`selected` 含 `"tests/unit"`（全量建议，精确元素匹配）→ 只跑 `FAST_CONTRACT_CASES` 并显式声明 defer（:200-201）；closed 受影响集 → 完整保留 selected 文件 + 去重后的 smoke（:202-205），**无任何截断逻辑**（无切片/限额）。
- `select_unit_tests`/`changed_unit_tests.py` 零改动（C2：diff 空、blob 相同）→ 未新造依赖证明系统。
- 我的 C5 真实调用与 C14 矩阵确认：任何场景 targets 中都不出现裸 `"tests/unit"`。

### G03 — PASS（共享常量逐成员一致）
- C3：`FAST_CONTRACT_CASES`（29 成员，含 `*CURRENT_CI_REGRESSION_CASES` 6 条）与 `CURRENT_CI_REGRESSION_CASES` 的 AST 在 base↔HEAD 完全一致；无内部重复。
- 远端合同 `--fast-contracts-only` 仍直接消费同一常量（`pre_push_gate.py:266-271`）；去重只发生在 push 命令组装（`_push_targets` :203-205），共享常量本身未动。

### G04 — PASS（完整本地模式与远端调用合同原样）
- diff 中 `gates` 静态五阶段、`focused_contract_gate`、`fast_contract_gate`、`_run`、`_run_pytest_gate` 无任何 hunk：完整模式仍 ruff/compileall/config_doctor/host guard/full units/focused contracts（`pre_push_gate.py:239-265`），集合未缩。
- 有界 worker 规则（`-n 2 --dist=loadfile` 仅当 `"tests/unit" in cmd` 或显式 targets>200，:160-168）与自有 TEMP 清理（`TemporaryDirectory(dir=PROJECT_ROOT)` + TEMP/TMP/TMPDIR/SQLITE_TMPDIR 覆写，:173-187）原样；对应未改测试仍在（test_pre_push_full_unit_workers.py 4 项、test_pre_push_temp_scope.py 5 项）。
- `--fast-contracts-only [--junitxml]` 合同不变（:287-294）；新增回归测试 `test_full_local_mode_runs_every_existing_stage_in_order`（test_daily_push_policy.py:191-204）与 `test_remote_and_full_mode_sets_are_unchanged_by_the_push_policy`（:173-188）固化该合同。

### G05 — PASS（输出语义诚实）
- C5 实测输出三要素齐全：scope+原因（`Push scope: no behavior changes`）、ran targets 数（29）、defer 声明；`local_fast_pass`/`full_validation_pending` 两个语义 token 均出现（:276-277, :284-285）。
- "safe to push" 在产品/测试路径零残留（C13；仅新测试反向断言 + 历史 planning 日志/旧 handoff 文档）。
- 完整模式绿文案（`full local gate GREEN — full validation ran locally…` :305）与快速模式绿文案（`Push fast gate GREEN (local_fast_pass for the ran scope only)…` :284-285 / fast-contracts `full_validation_pending — full suites stay with CI…` :296-298）互不相同，且 `test_green_full_local_mode_keeps_its_own_wording`（:152-160）反向锁定两种文案不相交；`--skip-contract` 绿也注明非完整验收（:302-303）。

### G06 — PASS（失败必非零、首失败保留）
- C4：缺 runner 的 hook 实测 **exit 1**（消息含 "missing"；`.githooks/pre-push:17-20` 由 base 的 `exit 0` 修正）。
- `_run` 的 TimeoutExpired → 打印子进程尾部证据后返回 124（:124-132）；启动失败（FileNotFoundError/OSError）自 `_run` 传播，由 `_dispatch_gate` 统一捕获转 **1**（:209-217）——机制在 dispatch 层而非 `_run` 内，可观察合同（非零）成立，且有测试 `test_runner_start_failure_returns_nonzero`（test_daily_push_policy.py:141-149）、`test_gate_exception_is_reported_not_swallowed`（test_pre_push_parallel_phases.py:49-57）。
- 首失败保留：完整模式逐 gate 早退返回首个红码（:307-312，delivery/w13/logs/full-local-mode.log 实证 GATE RED at config_doctor）；`_run` 失败时打印完整输出而非仅尾部（:135-137）。push 模式单 gate 直接回传子进程退出码（:278-286），E2E 证明 ran-scope 真失败拒推。

### G07 — PASS（行为矩阵清晰，政策层显式决定）
- C14 矩阵（真实临时 Git 仓，changed_paths→select_unit_tests→_push_targets 全链）：

| 场景 | select 结果 | push 实跑 | 裸 tests/unit 进 targets？ |
|---|---|---|---|
| 空 stdin / 新分支(old 全零) / 未知 old SHA | `["tests/unit"]` "unknown push range" | 29 smoke + defer | 否 |
| 仅 ref 删除(new 全零) / docs-only | `[]` "no behavior changes" | 29 smoke + defer | 否 |
| config 变更 / tools 变更 | `["tests/unit"]`（config/tooling reason） | 29 smoke + defer | 否 |
| 删除模块 / rename（--no-renames 双路径） | `["tests/unit"]` "deleted or unknown dependency" | 29 smoke + defer | 否 |
| 窄 src 变更 / 仅测试变更 / 多 ref | closed 受影响文件集 | 完整文件 + 29 smoke（如 30 targets） | 否 |

- 政策层显式决策体现在 `_push_targets`，选择函数的建议不再被当作命令执行；矩阵另有单测固化（test_daily_push_policy.py:46-113）。

### G08 — PASS（真实临时 Git E2E，旧断言按卡 TDD 调整）
- C6：`-k real_push` **3 passed（31.24s）**。三个 E2E（test_daily_push_policy.py:293-344）在 pytest `tmp_path` 建真实 work 仓 + bare remote + 真实 `git push` 过真实 hook：绿 push 放行且文案含 defer 语义；ran-scope 真失败（probe 断言失败）push 被拒且远端未收到 local head；缺 runner push 被拒且远端为空；宽范围（config+隐藏失败）defer 放行后串行 `pytest tests/unit` 抓到快集合外失败。
- TDD 顺序实证：dc19595a（test-freeze）对 `tools/pre_push_gate.py`/hook 的 diff 为空（测试先行 RED），且 test_daily_push_policy.py 在实现 commit 后未再改动；两条被调整旧断言（test_ci_push_selection.py 原“push 必跑 full units 两阶段”、test_pre_push_parallel_phases.py 原并行调度器合同）均属卡 G08 授权范围，其余旧断言保留（test_pre_push_temp_scope/full_unit_workers/changed_*_scope 零改动）。

### G09 — PASS（实测诚实、无墙钟审批阈值）
- `delivery/w13/scope-report.json` 四类范围同机实测：docs 44.5s / unknown 46.6s / 真实新分支 push 42.2s 均与日志吻合（scope-docs.log 内层 pytest 37.93s、scope-unknown.log 39.09s）→ “通常 ≤60s” 按其测量为诚实结论；narrow 66.8s 未达标也被如实记录并归因（46.49s 为共享 smoke 集，符合 G03“不借本卡删业务测试”）。
- wide 628.6s exit 124：scope-wide.log 尾部有 `FAILED: … (timeout after 600s)` + `PUSH CHECKS RED`；该 600s 为既有子进程上限（`pre_push_gate.py:107` 默认值，基线即有），closed 宽集改造前后同执行器同上限，非回归，且按 G09 未拉长超时——解释无 hand-waving。
- 产品代码零墙钟审批阈值：`pre_push_gate.py` 无 time/perf_counter/monotonic/elapsed 逻辑（仅上述预存 timeout 常量）。
- 审查人独立复测同一 docs 范围 pytest 耗 130.32s（vs 证据 37.93s）：墙钟随本机负载大幅波动，恰证明“≤60s”只能作为实测优化目标而非门限，而包内确实没有把它做进产品——方向正确。

## 3. 质量维度

- 模块化/泛化：无公司名/旧 hash/目录特判（diff 关键字扫描零命中）；`_push_targets` 只依赖选择语义（`"tests/unit"` 全量建议元素）而非具体调用方。
- 错误路径：launch 失败/异常/超时三类均非零且留诊断（见 G06）；hook 缺 runner 非零。
- 测试卫生：全部 E2E 用 pytest 自有 `tmp_path`（新根，无需 sentinel），无仓内文件创建；我的全部运行后 worktree `git status` 干净；scratch 位于系统 TEMP。
- 掩盖缺陷/同义反复检查：未发现。新测试驱动真实 gate/hook 代码；fixture 仓的 smoke stub 仅使共享常量在合成仓可运行（真实 smoke 集由真实仓执行，C5 已证）；对输出文案的断言为行为断言而非重言。
- `_run_parallel_pytest_gates` 退役无悬挂引用（C12：仅历史文档提及）；`concurrent.futures` import 一并移除，无死 import（ruff 过）。
- 写范围合规：10 个变更文件均在卡允许清单内；`.pre-commit-config.yaml` 仅注释同步（hook entry 数量与内容零变化）；无 `.github/workflows`、`src/**`、业务脚本/配置改动。

## 4. 发现（全部为 minor，无 blocker/major）

| ID | 严重度 | 位置 | 内容 | 建议 |
|---|---|---|---|---|
| F1 | minor | tools/pre_push_gate.py:279-280 | push 模式 gate 标签恒为 "daily push fast feedback: affected units and CI contract smoke"，即使 targets 为纯 smoke（defer/无变更路径，零 affected units）也如此；诊断标签与实跑集合略有不符（其上的 Push scope 行是准确的）。 | 可按 defer 分支选择更精确的标签；纯诊断改进，不影响退出码或集合。 |
| F2 | minor | tools/pre_push_gate.py:203-205 | 去重仅覆盖“selected 整文件 ⊇ smoke case”方向；若 selected 含与 FAST 成员完全相同的 node-id 会在命令行重复（pytest 对相同 node-id 会去重，实害为零）。当前 `select_unit_tests` 只返回整文件路径（changed_unit_tests.py:236 "Select whole test files"），该输入不可达，属潜在防御性问题。 | 无需本包处理；若未来选择函数可返回 node-id，可在命令组装处做全量 set 去重。 |
| F3 | minor | delivery/w13/scope-report.json | ≤60s 结论对宿主机负载敏感：审查人同机复测同一 docs 范围 pytest 耗 130.32s（证据 37.93s）。报告按当次测量是诚实的，且产品未引入墙钟阈值（正确），但交接措辞可补一句“墙钟随负载波动，以 CI/完整模式为准”。 | 仅文档措辞；不改代码。 |

## 5. 总结论

**APPROVE（通过）**。G01–G09 全部 PASS；卡内测试 145 passed（exit 0）、卡内 ruff 通过（exit 0）、`-k real_push` 3 passed（exit 0）、缺 runner hook 实测 exit 1。三项已知环境事实（config_doctor 因 worktree 缺 `.source_catalog` 必红、19 例 xdist tmp-file 抖动串行 58/58 绿、test_b10_read_chain 3 例 ratchet）均经本人复核且证实先于本包存在（`src/ scripts/ config/` 对 base 零 diff），属 EXTERNAL_LIMIT 而非包缺陷，已由实现者在 handoff 中如实报告。F1–F3 为 minor，不阻塞交付，可由 ROOT 并线时顺手处理或留档。

---

## 6. Delta 补审（commit `852dff28`，仅针对 F1–F3 修复）

- 补审范围：`git show 852dff28` —— 仅 2 文件：`tools/pre_push_gate.py`（blob `94eb1003`，sha256 前缀 `bdcc6294cb4f`）与 `delivery/w13/scope-report.json`（blob `c79431fd`）；`a31300a7..852dff28` 全部变更仍落在卡允许写集合内。补审期间未修改任何产品/测试文件（scratch 位于系统 TEMP）。

### F1 — 已修复（RESOLVED，附一条残留观察）
- `tools/pre_push_gate.py:283-284`：`selected` 为空时标签为 `daily push fast feedback: CI contract smoke (no affected unit files)`，否则维持原文。进程内三场景实测（空集 / 窄集 / 全量建议）：标签分别正确切换，exit 0。
- 残留（cosmetic，不阻塞）：全量建议 defer 路径（`selected == ["tests/unit"]`）实跑同样只有 29 条 smoke，标签仍含 "affected units"；但其上一行 `Push scope: … full unit suite recommendation deferred to CI` 已无歧义，诊断不受影响。

### F2 — 已修复（RESOLVED，经穷举 + 实测证明无成员丢失、无重复）
- 新去重逻辑（`tools/pre_push_gate.py:202-207`）：`whole_files = {path for path in selected if "::" not in path}`；FAST case 仅当其所属文件 ∈ whole_files 或其精确字符串 ∈ selected 时跳过。
- 系统临时 scratch 实测 7 场景（精确 node 命中、整文件、空集、whole-file 型 FAST 成员的 node 兄弟、文件+node 混合、合成目录防御、全量建议早退）：`dupes=[]`、`lost_fast_members=[]` 全场景成立；精确 node 命中时 `targets` 中该 node 恰出现 1 次且同文件 sibling FAST case 保留（G03 成员语义保持）。
- 正确性论证：selected 整文件覆盖其全部 node（跳过其 FAST case 不丢覆盖）；selected node 仅覆盖自身（同文件 sibling 必须保留，已保留）；扩展生成器对 FAST_CONTRACT_CASES（自身零重复）单次遍历且排除已在 selected 中的串 → targets 不可能重复。旧目录前缀去重的移除只会使 targets 变大（覆盖只增不减），且 `select_unit_tests` 本就不返回目录；pytest node 缓存保证目录+node 双指定不双跑。
- 观察（不阻塞）：node-id 去重分支无新增单测；该输入在当前 `select_unit_tests`（只返回整文件）下不可达，属纯防御代码，可不补测。

### F3 — 已修复（RESOLVED）
- `delivery/w13/scope-report.json:79` 新增 `measurement_caveat`：如实记录墙钟随负载波动（引本审查 docs 范围 pytest 130.3s 复测）、数字仅为当次测量证据、产品中无墙钟审批门（G09）。JSON 校验通过。

### Delta 命令与退出码
| # | 命令 | 退出码 | 结果 |
|---|---|---|---|
| D1 | `git show 852dff28`（含 --stat） | 0 | 仅 2 文件，14+/5-（pre_push_gate.py）+1 行 caveat |
| D2 | F2 去重 scratch（系统 TEMP，7 场景） | 0 | dupes=[] lost=[] 全过；精确 node 无重复、sibling 保留 |
| D3 | F1 标签 scratch（进程内三场景） | 0 | 空集→新标签；其余→原标签；exit 0 |
| D4 | 卡内测试集（7 文件） | 0 | **145 passed in 74.03s**（与实现者 145 一致） |
| D5 | 卡内 ruff（9 文件） | 0 | All checks passed! |
| D6 | `python -c "json.load(scope-report.json)"` | 0 | JSON 有效 |

（附注：全仓 ruff 存在 1 处先于本包的 F401/E401，位于 `.planning/du3-quality/` 历史规划 scratch（commit 9f1a27bd），不在卡文件清单与写范围内，与本包无关。）

### Delta 结论

**APPROVE（维持通过）**。F1/F2/F3 全部 RESOLVED；卡内测试 145 passed、ruff 干净（均本人复跑）。残留仅两条 cosmetic/信息性观察（defer 路径标签措辞、防御分支无单测），不构成 follow-up 义务。最终被审代码 commit 更新为 `852dff28`。
