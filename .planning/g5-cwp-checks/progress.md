# Progress Log — G5-CWP-CHECKS

## Session: 2026-10-07

### Phase 0: 基线与工作树

- **Status:** complete
- **Started:** 2026-10-07
- Actions taken:
  - `git -C <原仓> status --short`：8 个 G2-12 未提交改动 + 6 个 untracked，**未复制**进工作树。
  - `git worktree add -b codex/g5-cwp-checks C:/Users/郑曾波/Projects/_g5/cwp 5d0ad75504a9815febc1bddbe76ae2f667c3e74a`
  - 只建一处 PWF：`<工作树>/.planning/g5-cwp-checks/`；`resolve-plan-dir` 解析到该目录。
- Files created/modified: `.planning/g5-cwp-checks/{task_plan,findings,progress}.md`

### Phase 1: 读源与 caller 清单

- **Status:** complete
- Actions taken:
  - 读 `writer_policy.py`、六脚本、`test_hermetic_runtime.py`、`test_control_bootstrap.py`、
    `helpers/gold_evaluator.py`、`.pre-commit-config.yaml`、`.github/workflows/ci.yml`、`.githooks/pre-push`、
    `tools/pre_push_gate.py`、`scripts/sitecustomize.py`、`scripts/common.py`。
  - 全仓 grep 六模块的 `import` 与 `scripts/<name>.py` 路径引用 → 消费者全部在写集内测试。
  - 非 Python 引用（sh/ps1/cmd/yml/toml/ini）→ 0 命中。
- Files created/modified: `.planning/g5-cwp-checks/findings.md`、`retirement_map.json`

### Phase 2: 行为 RED

- **Status:** complete
- Actions taken:
  - 新增 `tests/unit/test_g5_legacy_checks_retirement.py`（54 项：六 CLI × legacy/help × plain/`-S`、
    trap harness、import 禁项目依赖、main 零初始化、writer_policy 类别、隔离 helper、control 目录）。
  - 真实 RED：`53 failed, 1 passed`，全部是产品断言失败（marker 缺失、gate API 泄漏、
    `RETIRED_ENGINEERING_TOOL_SCRIPTS` 不存在、`support.isolated_environment` 缺失、
    `control/architecture.json` 仍在），**无 pytest setup/collection 错误**。
- Files created/modified: `tests/unit/test_g5_legacy_checks_retirement.py`

### Phase 3: 实现

- **Status:** complete
- Actions taken:
  - 六脚本改纯 stdlib 退休薄壳（仅 `from __future__` + `sys` + `pathlib`）。
  - `writer_policy.py`：新增 `RETIRED_ENGINEERING_TOOL_SCRIPTS`；三 gate 移出
    `CONTROL_TOOL_ALLOWLIST`；`legacy_script_execution_allowed` 恒 False；
    `blocked_message` 工程退休分支前置。
  - 新 `tests/support/isolated_environment.py` 承接 `sanitized_environment`。
  - `git rm control/architecture.json`；改写 `control/README.md`。
- Files created/modified: `scripts/{semantic_gate,architecture_gate,clean_env_gate,gold_gate,test_framework,batch_process,writer_policy}.py`、
  `tests/support/isolated_environment.py`、`control/README.md`、`control/architecture.json`(deleted)

### Phase 4: 精确迁移既有测试

- **Status:** complete
- Actions taken:
  - 删除 regex/source-count 资格/候选整树复制专属测试：`tests/unit/test_semantic_gate.py`、
    `tests/unit/test_architecture_gate.py`、`tests/unit/test_clean_env_gate.py`（隔离用例迁入
    `test_hermetic_runtime.py`）。
  - `test_control_bootstrap.py` 改写为 fixture isolation + honest quality（gold evaluator）。
  - `test_hermetic_runtime.py` 改 import + 补 `CUSTOM_API_KEY`/`COMPANY_WIKI_*`/`PIP_NO_INDEX`/`NO_PROXY` 断言。
  - `test_common.py`：`clean_env_gate.py` 移出 supported，新增 `test_retired_engineering_shells_stay_denied`。
  - `test_legacy_entrypoint_simplification.py`：`test_framework.py` 移出 MIXED_SAMPLES 与 blocked 参数表；
    永久退休 harness 断言改为按 `RETIRED_ENGINEERING_TOOL_SCRIPTS` 选 marker（`batch_process.py`）。
  - `test_legacy_caller_reachability.py`：`test_every_retired_script_has_an_explicit_direct_cli_guard`
    对工程退休壳改为要求 marker（其余脚本仍要求 `enforce_direct_cli`）。
  - `test_gold_evaluator.py`：两个 CLI 收据测试改为 `TestRetiredGoldGateCli` 退休零写。
  - `test_gold_mutations.py`：新增 `test_routing_source_reference_is_rejected`、
    `test_claim_source_reference_is_rejected`（承接被删 semantic_gate 的来源引用反例）。
  - `test_writer_freeze.py`：**无需改动**（stub 不含 writer 正则且不在 allowlist，两条扫描自动跳过）。
- Files created/modified: 见上；另新增
  `tests/integration/test_g5_legacy_checks_retirement_e2e.py`

### Phase 5: 集中执行与交付

- **Status:** complete
- Actions taken: 见下方 Test Results；随后提交写集与 PWF 六件套。

## Test Results

短测试根：先确认 `<工作树>/.planning/test-tmp/g5-checks` absent，再以
`--basetemp .planning/test-tmp/g5-checks` 运行；结束后只删该根（已校验 absolute/
包含工作树/非 reparse），父目录 `.planning/test-tmp`（本卡创建）随后为空一并删除，
复核 `absent`。

| # | Test / command | Input | Expected | Actual | Status |
|---|----------------|-------|----------|--------|--------|
| 1 | `python -m pytest tests/unit/test_g5_legacy_checks_retirement.py -q --tb=line --basetemp .planning/test-tmp/g5-checks`（实现前 RED） | 冻结基线实现 | 产品断言失败 | exit 1；`53 failed, 1 passed`；11.36s；无 collection/setup 错误 | red |
| 2 | `python -m pytest tests/unit/test_g5_legacy_checks_retirement.py -q --tb=short --basetemp .planning/test-tmp/g5-checks` | 退休薄壳 | 全绿 | exit 0；`54 passed`；9.24s | green |
| 3 | `python -m pytest tests/unit/test_g5_legacy_checks_retirement.py tests/integration/test_g5_legacy_checks_retirement_e2e.py tests/unit/test_hermetic_runtime.py tests/unit/test_common.py tests/unit/test_writer_freeze.py tests/unit/test_legacy_entrypoint_simplification.py tests/contract/test_legacy_caller_reachability.py tests/contract/test_gold_evaluator.py tests/contract/test_gold_mutations.py tests/acceptance/test_control_bootstrap.py -q --tb=short --basetemp .planning/test-tmp/g5-checks` | 本卡责任集中集 | 全绿 | exit 0；`295 passed`；59.34s | green |
| 4 | `python -m pytest tests/unit -q --tb=short --basetemp .planning/test-tmp/g5-checks` | CI Unit 作用域 | 全绿 | exit 0；`1955 passed`；155.85s | green |
| 5 | `python tools/pre_push_gate.py --fast-contracts-only` | CI 冒烟契约 | GREEN | exit 0；`pre-push gate GREEN`；pytest basetemp verified（short/repository-local/not relocated） | green |
| 6 | `ruff check src tests/unit tests/contract tests/e2e scripts tests/integration/test_narrative_runtime_e2e.py tests/support/narrative_model_fixture.py` | CI lint scope | 0 问题 | exit 0；`All checks passed!` | green |
| 7 | `ruff check tests/support/isolated_environment.py tests/integration/test_g5_legacy_checks_retirement_e2e.py tests/acceptance/test_control_bootstrap.py` | 写集内但不在 CI scope 的新文件 | 0 问题 | exit 0；`All checks passed!` | green |
| 8 | `python -m compileall -q src scripts tests` | CI compile | 0 错误 | exit 0 | green |
| 9 | `python scripts/host_assumption_guard.py` | CI meta-gate FC-1307-a | 无新增违规 | exit 0；`violations=89; new=0; baseline=71; registered_hashes=11` | green |
| 10 | `CI=true PYTHONPATH=src python scripts/config_doctor.py` | CI 环境等价 | OK | exit 0；`OK: config/source_catalog.yaml healthy` | green |
| 11 | `PYTHONPATH=src python scripts/config_doctor.py`（无 `CI=true`，新鲜工作树） | 本地环境 | 记录为环境事实 | exit 1；`catalog_dir is not a directory: <worktree>/.source_catalog`。原因：`.source_catalog/` 被 `.gitignore` 忽略，原仓有、新工作树没有；`scripts/config_doctor.py:57` 在 `CI=true` 时跳过该分支（见第 10 行）。与本卡改动无关（`config/**`、`config_doctor.py` 未动，原仓同命令 exit 0）。 | blocked |

HTTP 替换边界：全部 subprocess 用例的 env 由 `_child_environment()` 构造（剔除 `*_API_KEY`、
去掉 `PYTHONPATH`、`PYTHON_DOTENV_DISABLED=1`、`COMPANY_WIKI_NETWORK=blocked`、
`COMPANY_WIKI_REAL_LLM=0`）；trap harness 把 `socket.socket.connect` /
`socket.create_connection` / `urllib.request.urlopen` 换成抛错桩；
`tests/conftest.py` 的 autouse fixture 在进程内阻断 socket。
所有用例 `external_network_requests = 0`，真实 LLM 配置与 `config/**` 未被任何用例写入。

## Error Log

| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-10-07 | `rg: command not found` | 1 | 改用 Grep 工具与 `grep -rn` |
| 2026-10-07 | Write 工具拒绝覆盖未读的 `.planning/g5-cwp-checks/task_plan.md` | 1 | 先 Read 模板再写入 |
| 2026-10-07 | 一次 `edit` 把 `test_retired_engineering_tool_is_never_allowed` 函数头吃掉，LSP 报 `environments/script is not defined` | 1 | 读回该区段，重新补回 decorator + def |
| 2026-10-07 | `shutil.rmtree(.planning/test-tmp/g5-checks)` 报 `PermissionError`（夹具 `.git/objects` 只读） | 1 | 换 `onexc` 回调先 `chmod` 再删；删前校验 absolute/包含工作树/`basename==g5-checks`/非 reparse |
| 2026-10-07 | `config_doctor` 在工作树 exit 1 | 1 | 定位为 `.source_catalog`（gitignored）缺失 + 非 CI 环境；`CI=true` 下 exit 0；记录为环境事实，未改配置 |

## 5-Question Reboot Check

| Question | Answer |
|----------|--------|
| Where am I? | Phase 5（complete） |
| Where am I going? | 提交写集 + PWF 六件套，交 MAIN 验收 |
| What's the goal? | 六旧 CLI 变纯 stdlib 退休薄壳（marker + exit 78，零初始化），有用行为迁移保留 |
| What have I learned? | 见 `findings.md` / `retirement_map.json` |
| What have I done? | 见上表：RED→GREEN、295/1955/契约冒烟全绿、静态全绿 |

---

*本文件随 Phase 推进、验证执行与错误发生而更新。*
