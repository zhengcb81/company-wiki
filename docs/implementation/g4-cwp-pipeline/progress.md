# G4-CWP-PIPELINE — Progress

## 2026-10-07 Session 1（全程）

### Phase 0 — 环境与基线
- worktree `C:/Users/郑曾波/Projects/_g4/CWP-PIPELINE/company-wiki`（分支 `codex/g4-cwp-pipeline`，base `5930a64`）；原仓未提交 G2 获取线未触碰（收尾复核 `git status` 与开工一致）。
- PWF 三份建于 `docs/implementation/g4-cwp-pipeline/`；`PLAN_ID=g4-cwp-pipeline`、`PWF_PLAN_ROOT=<worktree>/docs/implementation`，显式 resolver 传相同 PlanRoot。
- 调查结论入 `findings.md`；caller 清单入 `retirement_map.json`。
- 基线：`python -S scripts/full_pipeline.py …` → rc=1 ImportError/NameError；普通启动 → rc=78 但缺 `LEGACY_PIPELINE_RETIRED`；报告 4 条推荐 scheduler/ingest/migration。

### Phase 1 — 真实 RED
- `python -B -m pytest -q -p no:cacheprovider tests/unit/test_g4_pipeline_retirement.py tests/unit/test_deployment.py` → **17 failed, 27 passed, rc=1**
- 收据：`.planning/g4-cwp-pipeline/red_receipt.txt`
- 红灯均为产品行为缺口（-S 崩溃、缺标记、main 返回 1、旧族可 import、配置存在、报告旧推荐），非夹具/依赖错误。

### Phase 2 — stub 与删除
- `scripts/full_pipeline.py` 改为 stdlib+writer_policy 退役 stub；实测 `python -S`/普通/`--help` 全部 rc=78 双标记。
- `git rm -r scripts/gate_system`、`git rm config/pipeline_rules.yaml`、`git rm tests/unit/test_gate_system.py`；核验路径后单目录删除残留 `scripts/gate_system/**/__pycache__`（非 git clean）。

### Phase 3/4 — 测试与报告同步
- `test_legacy_entrypoint_simplification.py`：删 `PRE_GUARD_CRASH[("full_pipeline.py","nosite")]`。
- `test_writer_freeze.py`：full_pipeline 移出 orchestrator 清单；删 `len(guarded)>=49`；新增无固定数的“冻结或现行入口”行为检查。
- `test_deployment.py`：新增 `test_retirement_report_recommends_current_source_cli_only`（status=retired、只推荐现行 CLI、禁 scheduler/ingest/migration、无人工评审语义）。
- `deployment.py`：4 条 legacy_entries 换为准确 reason/replacement，形状与 rollback 字段不变。

### Phase 5 — 验证（全部一次通过）
| 命令 | 结果 | 证据 |
|------|------|------|
| 集中责任命令（卡 §6 六文件） | **185 passed / rc=0 / 31s**，含 `CW-BASETEMP-DECISION relocated=false` | `.planning/g4-cwp-pipeline/consolidated_receipt.txt` |
| `pytest tests/unit`（CI 对齐） | **1916 passed / rc=0 / 127s** | `.planning/g4-cwp-pipeline/unit_suite_receipt.txt` |
| `pytest tests/contract/test_legacy_caller_reachability.py` | **26 passed** | 本文件（见下） |
| `ruff check src tests/unit tests/contract tests/e2e scripts tests/integration` | All checks passed | 本文件 |
| `python -m compileall -q src scripts tests` | rc=0 | 本文件 |
| `config_doctor --structure-only`（commit hook 等价） | rc=0 | 本文件 |
| `python scripts/host_assumption_guard.py` | new=0 | 本文件 |
| 集成/E2E（独立 `cw4p-<random>` 根，trap+快照） | **13 passed**；finally 删除 owned 根，`ls $TEMP/cw4p-*` = none | 集成文件内 |

- 临时根：`Path(tempfile.gettempdir())/cw4p-<hex12>`，先记 absent，child cwd 只落 owned 根；pytest basetemp 未被本包重定位（relocated=false 记录于收据首行）。
- 外部效应：网络请求 0、模型调用 0、raw 删除 0、production 写 0（conftest 网络封锁 + trap 证明 + 快照比对）。

### 收尾核查
- `git status` 变更集 = 写集清单（含新增测试与 docs/implementation、.planning 收据）。
- 原仓 `C:/Users/郑曾波/Projects/company-wiki` 状态与开工一致（仍为 G2 获取线脏区，未触碰）。
- 环境备注：本 worktree 缺未跟踪 `.source_catalog` 运行目录 → `config_doctor` 全量模式 rc=1（先于本包的工作树状态差异；commit hook 的 `--structure-only` 通过；已记 findings）。

### 测试执行记录（汇总）

| # | 命令 | exit | passed | failed | seconds | 收据 |
|---|------|------|--------|--------|---------|------|
| 1 | `pytest tests/unit/test_g4_pipeline_retirement.py tests/unit/test_deployment.py`（RED） | 1 | 27 | 17 | 5 | `.planning/g4-cwp-pipeline/red_receipt.txt` |
| 2 | 集中责任命令（卡 §6） | 0 | 185 | 0 | 31 | `.planning/g4-cwp-pipeline/consolidated_receipt.txt` |
| 3 | `pytest tests/unit` | 0 | 1916 | 0 | 127 | `.planning/g4-cwp-pipeline/unit_suite_receipt.txt` |
| 4 | `pytest tests/contract/test_legacy_caller_reachability.py` | 0 | 26 | 0 | 3 | `.planning/g4-cwp-pipeline/green_misc_receipt.txt` |
| 5 | `pytest tests/integration/test_g4_pipeline_retirement_e2e.py` | 0 | 13 | 0 | 4 | `.planning/g4-cwp-pipeline/green_misc_receipt.txt` |
| 6 | ruff(CI scope)+compileall+config_doctor(--structure-only)+host_assumption_guard | 0 | — | 0 | — | `.planning/g4-cwp-pipeline/green_misc_receipt.txt` |

### 提交记录

| commit | 角色 | 说明 |
|--------|------|------|
| `306ecf9b2ef17da6952512226a9f623c107eff08` | implementation | Retire frozen pipeline gate family and stub full_pipeline entry |
| `4797a601f4e28ae432f6a7c1bd6e990d25117552` | handoff 文档 | Document G4-CWP-PIPELINE retirement handoff |
| （本文件与 handoff.json 所在提交） | 交接数据 | handoff.json 不写自身尚未生成的 SHA（按卡） |
