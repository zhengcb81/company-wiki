# G4-CWP-PIPELINE — main_wiring（交 MAIN 的工程接线清单）

**基准**：`5930a644453ed46494c2c83c5ecfb97767fa9492`，worktree `C:/Users/郑曾波/Projects/_g4/CWP-PIPELINE/company-wiki`，分支 `codex/g4-cwp-pipeline`。
本包未修改下列任何共享文件；以下逐项为实测清单（grep + 实跑），结论“当前没有引用”也是实测结果。

## 1. Hook / CI / 工具链（均无 gate_system / pipeline_rules / full_pipeline 引用）

| 位置 | 实测结论 | 建议 |
|------|----------|------|
| `.githooks/pre-commit` → `.pre-commit-config.yaml` | ruff（CI scope `src tests/unit tests/contract tests/e2e scripts`）本包实跑 **All checks passed**；`mypy-contract` 只在 source_catalog/automation 合同模块被 stage 时触发（本包不涉及，未触发）；`config-doctor` hook 触发条件是 `config/` 变更（本包删除 `config/pipeline_rules.yaml` 会触发），实跑 `--structure-only` **rc=0**；`host-assumption-guard` 实跑 **violations new=0** | 无需改动；commit 时 hooks 正常执行（未跳过） |
| `.githooks/pre-push` → `python tools/pre_push_gate.py --fast-contracts-only` | `tools/pre_push_gate.py` 内 **无** gate_system/pipeline_rules/full_pipeline 字样（grep 实测）。**但在卡指定 worktree 路径下该 gate 结构性无法通过**：`_run_pytest_gate` 把 basetemp 建在 `PROJECT_ROOT/tmp/pp<8hex>`，本 worktree 根 `C:\Users\郑曾波\Projects\_g4\CWP-PIPELINE\company-wiki`（50 字符）使 basetemp=64 字符 > 脚本内 60 字符上限，pytest 未运行即红。**可复现例子**：`python tools/pre_push_gate.py --fast-contracts-only` → `FAILED: pytest basetemp exceeds the 60-character limit: ...\company-wiki\tmp\ppds2wrrht`（与本包变更无关，属共享 gate 与长 worktree 路径的主机假设类问题）。同一 gate 的 12 个用例**直接运行 12 passed**（`.planning/g4-cwp-pipeline/fast_contracts_direct_receipt.txt`） | 本包不改该保护脚本、不 `--no-verify`（不跳 hook）；分支未推远端，交 MAIN：或在短路径合并、或按 F-B01-9 主机假设协议修 `pre_push_gate.py` 的 basetemp 落点 |
| `.github/workflows/ci.yml` | 无 gate_system/pipeline_rules 引用；`ruff check` scope 与本地一致（本包通过）；`compileall -q src scripts tests` 本包通过；`Unit tests (tests/unit)` 本包实跑 **1916 passed**；CLI smoke 只测 `collect_news.py` 退出 78（未受影响） | 无需改动 |
| `pyproject.toml`（`[tool.mypy]`、`[tool.ruff]`、`[project.scripts]`、pytest 配置） | 无 gate_system/pipeline_rules 引用；`[project.scripts]` 的 `company-wiki-source-catalog/-read/-query/-export-v2` 是退役报告推荐的真实命令 | 无需改动 |
| `pytest.ini`（`testpaths = tests`） | 无显式文件清单；`tests/unit/test_gate_system.py` 删除后自然不再收集 | 无需改动 |

## 2. 职责文档（超写集，建议 MAIN 删除或改写）

| 文件 | 实测引用 | 建议 |
|------|----------|------|
| `docs/GATE_SYSTEM.md` | 17、20、23、26、29（full_pipeline 用法）、117、255、259、278、281、290、309、317（pipeline_rules/gate_system）、343 行 | 整篇描述已删除的 Gate 族；建议删除或改为“已退休（G4）”一页并指向来源 CLI |
| `docs/使用说明书.md` | 44-50、115、118、181-213、253、262、481、529 行（full_pipeline/pipeline_rules 用法与目录树） | 改写为现行来源 CLI；目录树移除 `pipeline_rules.yaml` 条目 |
| `README.md`、`AGENTS.md`、`docs/ARCHITECTURE.md`、`docs/API.md`、`docs/OPERATIONS.md`、`docs/DEPLOYMENT.md`、`docs/TROUBLESHOOTING.md` | 对 `gate_system`/`pipeline_rules` **当前没有引用**（grep 实测） | 无需改动 |
| `docs/DEPLOYMENT.md` | 169、186、212、360、369 行仍写 `scripts/ingest.py`（该文件在 base 已不存在）——**先于本包的历史遗留** | 交 MAIN 顺手核对，不属于本包回归 |
| `artifacts/gates/*.json` | 历史审计快照内容提及旧路径（只读事实记录） | 保留不动 |

## 3. 代码层残余引用（均在写集外，交 MAIN 决定）

| 位置 | 事实 | 影响 |
|------|------|------|
| `scripts/test_framework.py:109,139` | 以子进程命令调用 `scripts/full_pipeline.py --company … --no-gates / --gate-log` | `test_framework.py` 自身是 mixed-frozen 入口（`require_legacy_writer_permission` 恒 False），永远不会执行到该命令；若执行则 stub 返回 78，不会启动任何 writer。建议 MAIN 后续整族退休时一并处理 |
| `scripts/batch_process.py:110` | 同上（`--no-gates`） | 自身 PERMANENTLY_RETIRED，不可执行；同上建议 |
| `src/company_wiki/deployment.py` | `generate_retirement_report()` 条目引用 `full_pipeline.py` | **本包已改**：status=`retired`、reason/替代推荐改为现行来源 CLI（见 `tests/unit/test_deployment.py::test_retirement_report_recommends_current_source_cli_only`） |
| `scripts/stage1_extract.py`、`scripts/stage2_structure.py` | 旧 Pipeline 阶段脚本，仍存在（mixed-frozen）；`stage3-6` 在 PERMANENTLY_RETIRED | 不在本包写集，保持现状；MAIN 决定后续处理 |
| `tests/contract/test_legacy_caller_reachability.py` | `EXPECTED_PERMANENTLY_RETIRED` 冻结清单含 `full_pipeline.py`；`test_every_retired_script_has_an_explicit_direct_cli_guard` 要求源码含 `enforce_direct_cli` 字面量 | **stub 已满足**（保留共享 guard 调用），本包实跑 26 passed；该文件未被修改 |
| `tests/unit/test_common.py:190` | `require_legacy_writer_permission("full_pipeline.py") is False` | `common.py`/`writer_policy.py` 保护未改，实跑全绿 |

## 4. 测试收集变化（本包内完成，MAIN 复核）

- 删除：`tests/unit/test_gate_system.py`（旧框架专属，无现行 import）。
- 新增：`tests/unit/test_g4_pipeline_retirement.py`、`tests/integration/test_g4_pipeline_retirement_e2e.py`。
- 修改：`tests/unit/test_deployment.py`（报告责任同步）、`tests/unit/test_legacy_entrypoint_simplification.py`（移除 `PRE_GUARD_CRASH[("full_pipeline.py","nosite")]` 例外——该入口现真正 exit 78）、`tests/unit/test_writer_freeze.py`（stub 不再计为金融 orchestrator；移除 `len(guarded)>=49` 人造数量门，改为“冻结或现行入口”行为检查，未换成另一个固定数字）。
- `tests/integration/test_full_pipeline.py` **未删未改**：确为 PDF `classify→extract→validate` 真实责任（页数/max_pages/质量分），集中命令内继续运行。

## 5. MAIN 统一接线后的发布检查建议

1. 全量 `pytest tests/unit`（本包 worktree 已 1916 passed，MAIN 合并后复跑一次即可）。
2. `ruff check`（CI scope）+ `compileall` + `config_doctor`（CI 等价命令，本包均通过）。
3. 决定 `docs/GATE_SYSTEM.md`、`docs/使用说明书.md` 的删除或改写。
4. 决定 `scripts/test_framework.py`、`scripts/batch_process.py`、`stage1/stage2` 是否随下一卡整族退休。
5. **本包不宣称全项目发布通过**；发布由 MAIN 统一接线后执行。
