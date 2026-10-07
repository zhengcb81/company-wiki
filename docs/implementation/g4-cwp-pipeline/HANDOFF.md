# G4-CWP-PIPELINE — HANDOFF

**Lane**：G4-CWP-PIPELINE（冻结旧处理链整体退休）
**卡**：`docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/g4_cwp_frozen_pipeline_retirement.md`
**Base**：`5930a644453ed46494c2c83c5ecfb97767fa9492`
**实现 commit**：`306ecf9b2ef17da6952512226a9f623c107eff08`（Retire frozen pipeline gate family and stub full_pipeline entry）
**交接 commit**：见 `handoff.json.commits`（实现与交接分别列）
**分支**：`codex/g4-cwp-pipeline`（未合 master、未跳 hook）
**Worktree**：`C:/Users/郑曾波/Projects/_g4/CWP-PIPELINE/company-wiki`

## 1. 删除 / 保留 / 迁移的 API

### 删除（整体退休，无兼容层）
- `scripts/gate_system/**`（11 文件）：`Gate`、`GateResult`、`PipelineContext`、`GateRegistry`、`DiagnosticsEngine`、`RetryOrchestrator`、`load_pipeline_rules`/`validate_rules`、`create_passed/failed/needs_review_result`、5 个 Gate 类（extraction_quality / data_contract / llm_output / financial_analyst / wiki_integrity）。无合法现行 import → 不重造 GateResult/GateRegistry/RetryOrchestrator 兼容层。
- `config/pipeline_rules.yaml`：Gate0–5 规则、approval_threshold、human_review/escalation 路由。唯一消费者 `gate_system/config_loader.py` 同批删除。
- `tests/unit/test_gate_system.py`：旧框架/配置/重试/人工评审断言整体退休。
- `scripts/full_pipeline.py` 旧实现（377 行：common+gate_system 导入、argparse、stage 子进程编排、Gate 执行、dashboard 生成）。

### 保留（保护文件，0 修改）
- `scripts/common.py`、`scripts/writer_policy.py`（`PERMANENTLY_RETIRED_SCRIPTS` 仍含 `full_pipeline.py`，环境变量依旧不能放行）。
- hook/CI/`tools/pre_push_gate.py`/`pyproject.toml`/`pytest.ini`、总 PWF、`config/source_acquisition.yaml`（原仓 owner 配置未复制）、生产配置/库/raw、别仓。
- `tests/integration/test_full_pipeline.py`（真实 PDF `classify→extract→validate`，页数/max_pages/质量分责任未动）。
- `tests/contract/test_legacy_caller_reachability.py`、`tests/unit/test_common.py`（写集外，实跑保持绿色：26 passed）。
- `artifacts/gates/*.json` 历史审计快照（只读事实）。

### 迁移（来源价值反例 → 现行接口）
- 页数 / `max_pages` / 提取质量分 / validate：`tests/integration/test_full_pipeline.py` 两项（集中命令内继续运行）。
- classify doc_type/置信度/skip（坏 doc_type 反例）：`tests/unit/test_pdf_classify.py`；stage1 提取：`tests/integration/test_stage1_extract.py`。
- 因此**未创建** `tests/contract/test_g4_preserved_source_behavior.py`（D3：不抄现成测试凑数）。
- 逐条映射见 `retirement_map.json`（15 条：13 retired / 2 preserved_in_current_test）。

### 新增 API（行为）
- `scripts/full_pipeline.py`（stub）：`main(argv=None) -> int` 程序化路径打印完整退休说明并返回 78；direct CLI 先输出 `LEGACY_PIPELINE_RETIRED` 行，再由共享 `writer_policy.enforce_direct_cli` 输出 `LEGACY WRITER BLOCKED - PERMANENTLY RETIRED` 并 exit 78（含 `python -S`、任意参数、旧授权环境变量）。
- `DeploymentManager.generate_retirement_report()`：形状不变（generated_at/current_stage/legacy_entries/failure_drills/metrics_history），4 条 legacy_entries `status="retired"`，替代推荐只含 `company-wiki-source-catalog`（+read/query/export-v2 口径、叙述 pilot 说明），不再出现 scheduler/ingest/migration，rollback 仍声明不支持回滚。

## 2. 真实 RED → GREEN

| 责任 | RED（改前实跑） | GREEN（改后实跑） |
|------|-----------------|-------------------|
| `-S` 直接启动卡命令 exit 78 + 双标记 | rc=1（`No module named 'yaml'` + NameError traceback） | rc=78，双标记（E2E 直接进程用例） |
| 普通启动/`--help`/旧参数/未知 flag 退休一致 | rc=78 但缺 `LEGACY_PIPELINE_RETIRED`；`main()` 返回 1 | 全部 rc=78 + 双标记；`main(argv)` 返回 78 |
| import 无副作用（plain + `-S`） | `-S` import 崩溃（PRE_GUARD_CRASH 例外） | 两模式 `G4-IMPORT-OK`、trap 零触发 |
| 旧族不再可 import / 配置退休 | `gate_system` 可 find_spec、`pipeline_rules.yaml` 存在 | find_spec 全 None、配置文件不存在、stub 源码无 gate/common/yaml 字样 |
| 退役报告不再推荐冻结 writer | 4 条推荐 scheduler/ingest/migration、status=blocked | status=retired、只推荐现行 CLI、无旧 writer 字样 |
| RED 总计 | `pytest tests/unit/test_g4_pipeline_retirement.py tests/unit/test_deployment.py` → **17 failed / 27 passed / rc=1**（`.planning/g4-cwp-pipeline/red_receipt.txt`） | 见下节 GREEN |

## 3. GREEN 证据（小收据）

| 命令 | exit | passed | failed | seconds | 收据 |
|------|------|--------|--------|---------|------|
| `python -B -m pytest -q -p no:cacheprovider tests/unit/test_g4_pipeline_retirement.py tests/integration/test_g4_pipeline_retirement_e2e.py tests/unit/test_deployment.py tests/unit/test_legacy_entrypoint_simplification.py tests/unit/test_writer_freeze.py tests/integration/test_full_pipeline.py` | 0 | 185 | 0 | 31 | `.planning/g4-cwp-pipeline/consolidated_receipt.txt` |
| `python -B -m pytest -q -p no:cacheprovider tests/unit` | 0 | 1916 | 0 | 127 | `.planning/g4-cwp-pipeline/unit_suite_receipt.txt` |
| `python -B -m pytest -q -p no:cacheprovider tests/contract/test_legacy_caller_reachability.py` | 0 | 26 | 0 | 3 | 本文件 §3 |
| `python -B -m pytest -q -p no:cacheprovider tests/integration/test_g4_pipeline_retirement_e2e.py` | 0 | 13 | 0 | 3 | 本文件 §3 |
| `ruff check src tests/unit tests/contract tests/e2e scripts tests/integration` | 0 | — | 0 | — | 本文件 §3 |
| `python -m compileall -q src scripts tests` | 0 | — | 0 | — | 本文件 §3 |

- 集中收据首行含 `CW-BASETEMP-DECISION {"relocated": false, "reason": "no-explicit-basetemp"}`：CWP pytest 未重定位 basetemp；本包短测试根自行分配、未使用 basetemp。

## 4. 临时根恢复 / 生产零写

- 集成/E2E 独立根：`%TEMP%/cw4p-<hex12>`（先断言 absent，child cwd/输出只落该 owned 根）；测试结束后 finally 删除，复核 `ls $TEMP/cw4p-*` → **none**；删除前校验绝对路径包含 TEMP、非 symlink/非 junction。
- trap（写入/open-w+、os、shutil、子进程、网络、yaml 配置、LLM 客户端）在真实子进程内**零触发**；sentinel 原件字节、`state.db` schema+行、目录结构快照**前后一致**。
- 外部效应：`network_requests=0`、`model_posts=0`、`raw_deleted=0`、`production_writes=0`；原件删除 0；原仓（含 G2 脏区）与开工时 `git status` 一致，未触碰。

## 5. 真正 RED→GREEN 清单（逐条）

1. `test_direct_cli_retires_representative_command[no-site-*]`：RED rc=1 崩溃 → GREEN rc=78 双标记。
2. `test_direct_cli_retires_representative_command[plain-*]`、`test_direct_cli_retires_every_legacy_argument_form[*]`（6 参数形）：RED 缺 `LEGACY_PIPELINE_RETIRED` → GREEN 齐全。
3. `test_import_is_silent_without_any_initialization[no-site]`：RED ImportError → GREEN 零 trap。
4. `test_main_only_prints_retirement_notice_and_returns_78` / `test_main_result_does_not_depend_on_argv`：RED 返回 1 → GREEN 返回 78。
5. `test_gate_family_is_no_longer_importable` / `test_pipeline_rules_config_is_retired` / `test_removed_family_is_not_referenced_by_the_stub`：RED 旧族存在 → GREEN 删除完成。
6. `test_retirement_report_recommends_current_source_cli_only`：RED 旧 writer 推荐 → GREEN 现行 CLI。
7. `test_permanently_retired_entry_exits_before_initialization[full_pipeline.py,no-site]`（既有 G1 反例，`PRE_GUARD_CRASH` 例外移除后）：RED 记录的 import 崩溃 → GREEN 真正 exit 78 + `PERMANENTLY RETIRED` + 零 trap。

## 6. MAIN 接线建议（详见 main_wiring.md / retirement_map.json）

1. 职责文档改写：`docs/GATE_SYSTEM.md`（整篇）、`docs/使用说明书.md`（44-50/115-118/181-213/253/262/481/529 行）。
2. 残余 caller 决定：`scripts/test_framework.py:109,139`、`scripts/batch_process.py:110`（自身冻结，不可执行）、`scripts/stage1_extract.py`/`stage2_structure.py`（mixed-frozen 旧阶段脚本）。
3. `docs/DEPLOYMENT.md` 对已不存在 `scripts/ingest.py` 的引用为**先于本包**的历史遗留，顺手核对。
4. hook/CI/mypy/pre_push/pyproject/pytest 收集：**当前没有引用** gate_system/pipeline_rules（逐项实测表在 main_wiring.md §1）。
5. MAIN 统一接线后才宣称全项目发布通过；本包不宣称。

## 7. 已知环境备注

- 本 worktree 缺原仓的未跟踪 `.source_catalog` 运行目录 → `config_doctor` **全量**模式 rc=1（先于本包的工作树状态差异，与 G4 变更无关）；commit hook 使用的 `--structure-only` 实跑 rc=0。
- LSP 对 `scripts/`、`tests/` 内 import 的“could not be resolved”为未挂 sys.path 的既有环境噪音；以 ruff/compileall/pytest 实跑为准。
- **分支未推远端（未跳 hook）**：`.githooks/pre-push` 的 `pre_push_gate.py --fast-contracts-only` 把 basetemp 建在 `PROJECT_ROOT/tmp/pp<8hex>`，本卡指定 worktree 根（50 字符）使 basetemp=64 字符，超过脚本自带 60 字符上限，gate 在运行 pytest 前即红。可复现：`python tools/pre_push_gate.py --fast-contracts-only` → `FAILED: pytest basetemp exceeds the 60-character limit: ...\company-wiki\tmp\ppds2wrrht`。该共享 gate 属保护文件，本包不改、不 `--no-verify`；同一 gate 的 12 个用例直接运行 **12 passed**（`.planning/g4-cwp-pipeline/fast_contracts_direct_receipt.txt`）。交付方式为本地分支 `codex/g4-cwp-pipeline`，交 MAIN 在短路径合并或按主机假设协议修 gate 落点（与 G3 两个 lane 未推远端一致）。
