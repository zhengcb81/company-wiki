# G4-CWP-PIPELINE — 任务计划

**卡**：`docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/g4_cwp_frozen_pipeline_retirement.md`
**Worktree**：`C:/Users/郑曾波/Projects/_g4/CWP-PIPELINE/company-wiki` 分支 `codex/g4-cwp-pipeline`
**Base**：`5930a644453ed46494c2c83c5ecfb97767fa9492`
**PWF**：`PLAN_ID=g4-cwp-pipeline`、`PWF_PLAN_ROOT=<worktree>/docs/implementation`，计划文件与卡交付物同置 `docs/implementation/g4-cwp-pipeline/`；显式调用 resolver 时传相同 PlanRoot（fail-closed，不竞争根 task_plan，不改 CWP 总 PWF）。
**性质**：整体退休旧 Gate/金融 Pipeline 族；不恢复研究 writer、不加放行 flag、不保留 disabled 审批空壳、不复制大 archive。

## Goal

1. `scripts/full_pipeline.py` → stdlib 薄退休 stub：import 静默、direct CLI 任意参数 exit78、说明现行来源 CLI、标记 `LEGACY WRITER BLOCKED` + `LEGACY_PIPELINE_RETIRED`。
2. 整体删除 `scripts/gate_system/**`、`config/pipeline_rules.yaml` 及专属测试；来源价值反例映射到现行接口。
3. `generate_retirement_report()` 只推荐现行来源 CLI。
4. 移除 `PRE_GUARD_CRASH[(full_pipeline.py,nosite)]` 例外与 `len(guarded)>=49` 数量门。
5. 交 `retirement_map.json`、`main_wiring.md`、六份 PWF/交接文件与测试小收据。

## 独占写集（实际触碰）

- `scripts/full_pipeline.py`（377 行旧编排 → 57 行 stdlib+writer_policy stub）
- `scripts/gate_system/**`（11 文件删除）、`config/pipeline_rules.yaml`（删除）
- `src/company_wiki/deployment.py`（仅 generate_retirement_report 的 4 条 legacy_entries 内容）
- `tests/unit/test_gate_system.py`（删除）、`tests/unit/test_deployment.py`、`tests/unit/test_legacy_entrypoint_simplification.py`、`tests/unit/test_writer_freeze.py`
- 新 `tests/unit/test_g4_pipeline_retirement.py`、新 `tests/integration/test_g4_pipeline_retirement_e2e.py`
- `docs/implementation/g4-cwp-pipeline/**`、`.planning/g4-cwp-pipeline/`（小收据）

## 保护（未改，全部实测确认）

- `scripts/common.py`、`scripts/writer_policy.py`、hook/CI/pre_push_gate/pyproject/pytest.ini、总 PWF、生产配置/库/raw、别仓与原仓未提交内容
- `tests/integration/test_full_pipeline.py`（真实 PDF 责任，集中命令内继续运行）
- `tests/contract/test_legacy_caller_reachability.py`、`tests/unit/test_common.py`（写集外，实跑保持绿色）
- 未创建 `tests/contract/test_g4_preserved_source_behavior.py`（D3：现成 PDF/解析测试已覆盖，不抄现成凑数）

## Phases

### Phase 0 — 环境与基线
**Status:** complete
- worktree/分支/base 核定；AGENTS/planning-with-files 已读；PWF 三份建立
- caller 调查 + retirement_map 初稿（findings.md）

### Phase 1 — 真实 RED
**Status:** complete
- 新反例实跑：**17 failed, 27 passed**（`.planning/g4-cwp-pipeline/red_receipt.txt`）
- 红灯全部为产品行为缺口：`-S` 崩溃非 78、缺 `LEGACY_PIPELINE_RETIRED`、main() 返回 1、gate 族可 import、pipeline_rules 存在、报告推荐旧 writer；非夹具错误

### Phase 2 — stub 替换与旧族删除
**Status:** complete
- stub：`main(argv=None)->int` 返回 78；direct CLI 先打 `LEGACY_PIPELINE_RETIRED` 行再由共享 `enforce_direct_cli` 打 `LEGACY WRITER BLOCKED - PERMANENTLY RETIRED` 并 exit 78（D1/D2）
- `git rm` gate 族 + `pipeline_rules.yaml` + `test_gate_system.py`；清理删除后残留 `__pycache__`（路径核验后单目录删除，非 git clean）

### Phase 3 — 专属测试同步
**Status:** complete
- `test_legacy_entrypoint_simplification.py`：移除 full_pipeline 的 PRE_GUARD_CRASH 例外
- `test_writer_freeze.py`：full_pipeline 移出 explicit_orchestrators；删 `len(guarded)>=49`；新增“冻结或现行入口”行为检查（无新固定数）
- `test_deployment.py`：形状保留 + status=retired + 只推荐现行 CLI 反例
- `test_gate_system.py`：整体退休；价值反例映射见 retirement_map

### Phase 4 — 报告与契约
**Status:** complete
- 报告 4 条：replacement 全为 `company-wiki-source-catalog`（+read/query/export-v2 口径、叙述 pilot 说明），reason 准确，rollback 仍声明不支持回滚
- contract 层实跑：`tests/contract/test_legacy_caller_reachability.py` 26 passed（stub 保留 `enforce_direct_cli` 字面量）

### Phase 5 — 集中验证与恢复
**Status:** complete
- 集中命令 **185 passed**（31s，`.planning/g4-cwp-pipeline/consolidated_receipt.txt`，含 CW-BASETEMP-DECISION relocated=false）
- 全量 `tests/unit`：**1916 passed**（127s，`unit_suite_receipt.txt`）
- ruff（CI scope）All checks passed；compileall 通过；config_doctor `--structure-only` rc=0；host_assumption_guard new=0
- 独立 `cw4p-<random>` 根：13 项集成/E2E 全绿，finally 删除 owned 根，`ls $TEMP/cw4p-*` = none

### Phase 6 — 交接
**Status:** complete
- `retirement_map.json`（15 条：13 retired / 2 preserved_in_current_test，结构校验通过）
- `main_wiring.md`（hook/CI/mypy/pre_push/pyproject/职责文档/测试收集逐项实测）
- `HANDOFF.md`、`handoff.json`（g4-handoff/1）、进度与收据
- 实现 commit 与交接 commit 分列；不合 master、不跳 hook

## Decisions Made

| # | 决策 | 理由 |
|---|------|------|
| D1 | stub 仅 import stdlib + `writer_policy` | `writer_policy` 自身纯 stdlib 零初始化，是 `LEGACY WRITER BLOCKED`/`enforce_direct_cli` 的唯一权威；写集外 contract 测试要求源码含该字面量；forbidden 列表（common/Config/Gate/金融 writer）不含它 |
| D2 | direct CLI 顺序：先 `LEGACY_PIPELINE_RETIRED` 行 → 共享 guard 打完整退休通知并 exit 78；`main(argv)` 程序化路径打印完整通知返回 78 | 两标记齐全、guard 在任何初始化之前、无重复阻断语义 |
| D3 | 不新建 `test_g4_preserved_source_behavior.py` | 页数/max_pages/质量分/坏 doc_type 已由 `tests/integration/test_full_pipeline.py`、`test_pdf_classify.py`、`test_stage1_extract.py` 承担；避免抄现成凑数，映射写入 retirement_map |
| D4 | `tests/contract/test_legacy_caller_reachability.py` 不改，stub 满足其字面量契约 | 该文件不在写集；改 stub 而非改保护外测试 |
| D5 | 删除后残留 `scripts/gate_system/**/__pycache__` 单目录核验删除 | 否则 `find_spec("gate_system")` 仍命中空命名空间包；非 git clean、不触碰其他未跟踪文件 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| rg 不在 git-bash PATH | 1 | 改用 Grep 工具/`grep -rn` |
| resolver PWF_PLAN_ROOT 钉住后指向不存在的 `.planning/<id>` | 1 | 按卡 fail-closed：计划文件直接放 `docs/implementation/g4-cwp-pipeline/`，显式 resolver 传相同 PlanRoot |
| `find_spec("gate_system.registry")` 抛 ModuleNotFoundError（父包缺失语义） | 1 | 辅助 `_find_spec_or_none` 捕获后断言 None |
| config_doctor 全量模式在本 worktree 报 `.source_catalog` 缺失 | 1 | 先于本包的工作树状态差异（原仓有未跟踪运行目录）；commit hook 用 `--structure-only` 实跑 rc=0，记入 findings/handoff |
| LSP 报 `Iterator`/fixture 生成器注解与 scripts 路径 import 解析错误 | 1 | 注解改 `Iterator[Path]`；其余为 LSP 未挂 scripts/sys.path 的既有环境噪音（ruff/pytest 实跑通过） |

## Next Step

无——全部 Phase 完成；等 MAIN 按 `main_wiring.md` 统一接线与发布。
