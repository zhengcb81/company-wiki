# HANDOFF — G5-CWP-CHECKS：旧工程门禁与批处理外壳整族退休

- **package_id**: `G5-CWP-CHECKS`
- **repo**: `C:/Users/郑曾波/Projects/company-wiki`（master）
- **worktree**: `C:/Users/郑曾波/Projects/_g5/cwp`
- **branch**: `codex/g5-cwp-checks`
- **base_commit**: `5d0ad75504a9815febc1bddbe76ae2f667c3e74a`
- **交接格式**: `g5-handoff/1`（`handoff.json`，字段由 `g5_handoff.schema.json` 约束）
- **delivery_status**: `ready_for_main`

## 1. 结果

六个旧 CLI 现在都是**纯 stdlib 退休薄壳**：

| 路径 | 之前 | 现在 |
|------|------|------|
| `scripts/semantic_gate.py` | 最少 30 来源/数值阈值资格门 + 收据写入 | 退休薄壳 |
| `scripts/architecture_gate.py` | regex/计数规则评估 + `control/architecture.json` | 退休薄壳 |
| `scripts/clean_env_gate.py` | 复制整候选树 + 建 venv + 跑旧 Gate 命令 + 收据 | 退休薄壳 |
| `scripts/gold_gate.py` | 评分 + 只允许 `artifacts/gates` 收据 | 退休薄壳 |
| `scripts/test_framework.py` | 统一测试运行器/报告/审核日志 | 退休薄壳 |
| `scripts/batch_process.py` | 分批跑旧 Pipeline | 退休薄壳 |

统一合同：

- 直接调用（**legacy 参数**、**`--help`**、**`python -S`**、独立空 cwd）→
  stdout 含 `LEGACY_ENGINEERING_TOOL_RETIRED`，**exit 78**，不解析 argv
  （stderr 无 `unrecognized arguments`、stdout 无 `usage:`），cwd 零新文件。
- `import` → 成功且零初始化；在**禁项目依赖**（`company_wiki`/`common`/`config`/
  `graph`/`llm_client`/`writer_policy`/`sitecustomize`/`helpers`/`yaml`/`requests`/
  `openai`/`dotenv`/…）的 meta_path 拦截下依然成功，且不暴露任何旧 gate API。
- `main()` → 返回 78、打印同一 marker；trap harness 证明零 `Path/os/shutil` 写、
  零 `socket/urllib` 连接、零模型/Store/下载器构造。
- 没有新增任何批准旧链的环境变量或 flag。

## 2. 实际写集

**改/删：**

```
scripts/architecture_gate.py            (改写为退休薄壳)
scripts/batch_process.py                (改写为退休薄壳)
scripts/clean_env_gate.py               (改写为退休薄壳)
scripts/gold_gate.py                    (改写为退休薄壳)
scripts/semantic_gate.py                (改写为退休薄壳)
scripts/test_framework.py               (改写为退休薄壳)
scripts/writer_policy.py                (仅这六个名字的类别/退休说明)
control/architecture.json               (删除，唯一消费者是退休工具)
control/README.md                       (历史/当前说明)
tests/support/isolated_environment.py   (新，迁移 sanitized_environment)
tests/unit/test_g5_legacy_checks_retirement.py        (新)
tests/integration/test_g5_legacy_checks_retirement_e2e.py (新)
tests/unit/test_hermetic_runtime.py                   (迁移 import + 补断言)
tests/unit/test_common.py                             (supported 名单 + 新退休断言)
tests/unit/test_legacy_entrypoint_simplification.py   (仅本族责任行)
tests/acceptance/test_control_bootstrap.py            (改写)
tests/contract/test_gold_evaluator.py                 (CLI 收据测试 → 退休零写)
tests/contract/test_gold_mutations.py                 (补来源引用反例)
tests/contract/test_legacy_caller_reachability.py     (仅本族责任行)
```

**删除的旧专属测试文件：** `tests/unit/test_semantic_gate.py`（regex/source-count 资格）、
`tests/unit/test_architecture_gate.py`（regex 门）、`tests/unit/test_clean_env_gate.py`
（候选整树复制；隔离用例迁入 `test_hermetic_runtime.py`）。**没有删除任何混合测试文件。**

**未改（no_change，已核）：** `tests/unit/test_writer_freeze.py`、
`tests/helpers/gold_evaluator.py`、`scripts/sitecustomize.py`、`scripts/common.py`、
`pyproject.toml`、`.pre-commit-config.yaml`、`.github/workflows/ci.yml`、
`.githooks/pre-push`、`tools/pre_push_gate.py`、`config/**`、`src/company_wiki/**`。

## 3. 有用行为的去向

| 旧行为 | 去向 |
|--------|------|
| clean_env 环境隔离（剥 `*_API_KEY`、dotenv 关闭、网络/LLM 关断、`PIP_NO_INDEX`、`NO_PROXY`） | `tests/support/isolated_environment.py`；`test_hermetic_runtime.py` 与两个 G5 测试继续消费 |
| dotenv 不回灌真实凭证、socket 默认阻断 | `test_hermetic_runtime.py` 原有两测保留 |
| 来源引用反例（routing/claim 指向不存在来源） | 新增 `test_gold_mutations.py::test_routing_source_reference_is_rejected` / `test_claim_source_reference_is_rejected` |
| 错误资料不得判成功 | `test_gold_mutations.py::_assert_metric_failed`、`test_threshold_file_is_definition_only`；新增 `test_control_bootstrap.py::test_quality_below_threshold_is_reported_as_failure_not_success` |
| gold evaluator 定位/缺来源/更正/未来公开/重复独立反例 | `tests/contract/test_gold_evaluator.py` + `test_gold_mutations.py` 全部保留，不再作为发布签收服务 |
| gold CLI 收据约束 | 改为退休零写（`TestRetiredGoldGateCli`） |
| 旧阈值 | 只作为历史指标计算讨论，不再是任何资格门；`min_sources`/regex/候选复制实现随 CLI 一起删除 |

## 4. RED → GREEN

真实 RED（实现前，`tests/unit/test_g5_legacy_checks_retirement.py`）：

```
53 failed, 1 passed in 11.36s
```

失败全部是产品断言（marker 缺失、`RETIRED_ENGINEERING_TOOL_SCRIPTS` 不存在、
`support.isolated_environment` 不存在、`control/architecture.json` 仍在、旧 gate API 泄漏），
**不是 pytest setup/collection 错误**；唯一通过的是 `test_writer_policy_still_freezes_the_research_writer_inventory`
（preserve 断言，按设计在基线上就该通过）。

实现后同命令：`54 passed in 9.24s`。

## 5. 可直接复制的完整测试命令

短测试根：先 `mkdir -p .planning/test-tmp` 并确认 `.planning/test-tmp/g5-checks` 不存在，
然后统一加 `--basetemp .planning/test-tmp/g5-checks`；跑完只删该根。

```bash
cd 'C:/Users/郑曾波/Projects/_g5/cwp'

# 本卡责任集中执行（新 unit/integration + 保留的 hermetic/common/writer-freeze/
# legacy caller + gold evaluator/mutations + 精确迁移的 legacy entrypoint 与 acceptance）
python -m pytest \
  tests/unit/test_g5_legacy_checks_retirement.py \
  tests/integration/test_g5_legacy_checks_retirement_e2e.py \
  tests/unit/test_hermetic_runtime.py \
  tests/unit/test_common.py \
  tests/unit/test_writer_freeze.py \
  tests/unit/test_legacy_entrypoint_simplification.py \
  tests/contract/test_legacy_caller_reachability.py \
  tests/contract/test_gold_evaluator.py \
  tests/contract/test_gold_mutations.py \
  tests/acceptance/test_control_bootstrap.py \
  -q --tb=short --basetemp .planning/test-tmp/g5-checks

# CI Unit 作用域
python -m pytest tests/unit -q --tb=short --basetemp .planning/test-tmp/g5-checks

# CI 快契约冒烟（含 ruff/compileall/… 的 gate 只跑 --fast-contracts-only 一项）
python tools/pre_push_gate.py --fast-contracts-only

# 静态
ruff check src tests/unit tests/contract tests/e2e scripts tests/integration/test_narrative_runtime_e2e.py tests/support/narrative_model_fixture.py
ruff check tests/support/isolated_environment.py tests/integration/test_g5_legacy_checks_retirement_e2e.py tests/acceptance/test_control_bootstrap.py
python -m compileall -q src scripts tests
python scripts/host_assumption_guard.py
CI=true PYTHONPATH=src python scripts/config_doctor.py
```

已删除的测试文件不再出现在任何命令里（`tests/unit/test_semantic_gate.py`、
`tests/unit/test_architecture_gate.py`、`tests/unit/test_clean_env_gate.py`）。

**实测结果**：见 `.planning/g5-cwp-checks/progress.md` 的 Test Results 表
（295 / 1955 全绿，契约冒烟 GREEN，静态全绿，`host_assumption_guard new=0`）。
不固定 pass 总数；未重跑全契约套件与真实模型用例。

## 6. 保护与清理

- `protection.owner_files`：13 个禁写文件逐个 `git diff --quiet <base> -- <path>` 复核
  **全部未变**，`before_sha256 == after_sha256`（详见 `handoff.json`）。
- `production_writes = 0`（未写 `companies/`、`sectors/`、`themes/`、`raw/`、`config/**`、
  `artifacts/**`、`stockwiki/`、外仓）。
- `raw_deletions = 0`、`paid_calls = 0`（无 LLM/下载调用）。
- 清理：`.planning/test-tmp/g5-checks` 与本卡创建的父目录 `.planning/test-tmp`
  已按 absolute/包含工作树/`basename`/非 reparse 校验后删除，复核 absent；
  诊断期间临时创建的 `.source_catalog` 已删除，复核 absent；
  `.planning/g5-cwp-checks/` 是交接文件，**已提交，未当 temp 删除**。

## 7. 环境事实（非本卡回归）

新鲜工作树没有被 `.gitignore` 的 `.source_catalog/`，本地直跑
`PYTHONPATH=src python scripts/config_doctor.py` 会报 `catalog_dir is not a directory`
并 exit 1；`scripts/config_doctor.py:57` 在 `CI=true` 时跳过该分支，
`CI=true PYTHONPATH=src python scripts/config_doctor.py` → exit 0，与 CI 环境一致。
原仓同命令（无 `CI`）exit 0。本卡未改 `config/**` 与 `config_doctor.py`。

## 8. Remaining / 交给 MAIN

1. **MAIN 合入**：`git log codex/g5-cwp-checks` 完整历史 → 集中验收 → 合 master →
   核精确代码 CI → 更新总 PWF。本卡不自行合 master、不推 master。
2. **`main_wiring.md` 11 条**：全部是 `no_change` / `verify`，没有需要 MAIN 追加的
   工程清单接线；`src/company_wiki/deployment.py` 的 `"batch_process.py"` 字面量、
   `docs/implementation/g4-cwp-pipeline/*` 与 `docs/contracts/legacy-caller-reachability-v1.md`
   的历史措辞是写集外 `verify` 项。
3. **其他族未完**：G2-12 在原仓仍未提交（8 改动 + 6 untracked），本卡未复制、未处理；
   MAIN 的总目标仍 `paused`。**不能宣称「全面门禁都已取消」** —— 本卡只退休这六个
   旧工程门禁/批处理外壳；`.pre-commit-config.yaml`、`.githooks/pre-push`、
   `tools/pre_push_gate.py`、`.github/workflows/ci.yml` 与 `src/company_wiki/source_catalog/architecture_gate.py`
   的现行检查全部保留且未改动。
4. 本卡未新增 CLI 入口、未改 `[project.scripts]`、未引入 quality service / 签名 schema /
   替代 Gate CLI。

## 9. 文件索引

- `handoff.json` — 机器可读交接（`g5-handoff/1`）
- `retirement_map.json` — 逐函数：原位置 / 真实 caller / 处理 / 替代位置 / 反例
- `main_wiring.md` — 写集外引用与接线结论
- `task_plan.md` / `findings.md` / `progress.md` — 计划、发现、日志与测试结果
