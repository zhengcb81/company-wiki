# G3-CWP-MAINT → MAIN 接线清单（本卡未修改以下任何文件）

基线 `5930a64` / 分支 `codex/g3-cwp-maint`。以下逐条是 MAIN 在 G2-12 + 公共CLI 同次集成里需要同步的文件、分支与清单；本卡只交付库层与本说明，**不声称CLI/help/工程清单已发布**。

## 1. `src/company_wiki/source_catalog/cli.py`（parser / import / handler）

| 位置 | 现状 | MAIN 动作 |
|---|---|---|
| `cli.py:31` `from .focus_cleanup import FocusScopeCleanupService` | handler 构造后 preview/apply 必抛 `RetiredMaintenanceError` | 删除 focus-cleanup 子命令（parser+handler）或改为 `except RetiredMaintenanceError` → 具名非零；从help去掉旧写引导 |
| `cli.py:203-213` focus-cleanup parser（`--apply/--confirmation-token/--snapshot-path/--receipt-path/--archive-dir`） | `--apply` 缺守卫仍走 cli.py 自身 `ValueError "requires"`（cli.py:905-913），有守卫则落到库层退休 | 同上；help 文案含 "dry-run or apply ... admission cleanup" 属旧写引导 |
| `cli.py:897-931` focus-cleanup handler | dry-run/apply 两分支都命中库层退休（exit 1，`structured_error` → `fatal`） | 改为按 `exc.operation`（`focus-cleanup` / `focus-cleanup-restore-*`）映射具名非零结果 |
| `cli.py:289-293` archive-retired-evidence parser + `cli.py:1024-1030` handler | 调 `archive_retired_evidence(config.database_path, project_root/"source_manifests")`（不传now）→ 库层退休异常 | 删除该子命令或映射具名非零；help "export retired documents' evidence spans..." 属旧写引导 |
| `cli.py:294-298` prune-retired-evidence parser（`--apply`）+ `cli.py:1031-1037` handler | 调 `prune_retired_evidence(..., apply=args.apply)`（不传now）→ 库层退休异常 | 同上；help "physically delete retired evidence spans..." 属旧写引导 |
| `cli.py:329-333` duplicate-preview parser + `cli.py:1056-1057` handler | `service.preview(...)` → `DuplicateMaintenanceRetired`（is-a RetiredMaintenanceError + DuplicateCleanupError） | 删除子命令或具名非零；help "issue a confirmation token" 属token引导，需去除 |
| `cli.py:335-340` duplicate-recycle parser + `cli.py:1058-1061` handler | `service.recycle(..., confirmation_token=...)` → 退休异常 | 同上；`--confirmation-token` 参数与 help "Recycle Bin" 引导需去除 |
| `cli.py:314-327` duplicates parser + `cli.py:1049-1055` handler | **只读，仍可用**（`list_groups` 走 reader；返回 `inventory_only` 等新字段） | 可保留；help 可注明 inventory-only（可选） |
| `cli.py:28` `from .duplicate_cleanup import DuplicateCleanupService` | `duplicates` 仍需要 | 保留（若 MAIN 同时删除 preview/recycle 分支，import 仍被 duplicates 使用） |
| `cli.py` error 路径 `except Exception → structured_error` (cli.py:1385-1393) | 退休异常当前呈 `error_type="fatal"` | 在此之前加 `except RetiredMaintenanceError as exc:` → 具名结果（用 `exc.code`/`exc.operation`） |

## 2. `code_identity` 源码指纹

- `src/company_wiki/source_catalog/code_identity.py:18` 的 `CORE_SOURCE_PATHS` 含 `src/company_wiki/source_catalog/focus_cleanup.py`；本卡改动了该文件内容（751→53行）→ **bundle 指纹必然变化**。无 pinned-hash 测试（`test_source_catalog_code_identity.py` 动态计算，已绿）；MAIN 需在集成时确认 worker `loaded_code_fingerprint` 按既有机制重新加载/比对（属“源码指纹同步”），并决定是否把 `maintenance_retirement.py` 加入 CORE_SOURCE_PATHS（**本卡未改该清单**）。

## 3. package 导出（`source_catalog/__init__.py`，本卡未改）

- 现有导出全部保持可用：`DUPLICATE_CLEANUP_SCHEMA_VERSION`、`DuplicateCleanupError`、`DuplicateCleanupJournal`、`DuplicateCleanupService`、`recycle_to_windows_bin`、`FOCUS_CLEANUP_SCHEMA_VERSION`、`FocusScopeCleanupService`（`:74-84`）。
- 新模块 `maintenance_retirement` **未**加入 `__init__` 导出（不在写集）；MAIN 若希望 `from company_wiki.source_catalog import RetiredMaintenanceError`，需在自己线添加导出 + `__all__`。
- `DuplicateMaintenanceRetired` 只在 `duplicate_cleanup` 模块内导出（`__all__`），同样未上包级。

## 4. mypy / hook / CI 工程清单

| 清单 | 状态 | MAIN 动作 |
|---|---|---|
| `.pre-commit-config.yaml` / CI `mypy` 固定文件列表 | 六个改动模块不在列表内；本卡本地 `python -m mypy` 六模块全绿 | 若MAIN要把 `maintenance_retirement.py` 纳入严格检查，加入列表（本卡未改hook/CI） |
| CI/pre-push `ruff check src tests/unit tests/contract tests/e2e scripts` | 本卡已全量跑过，全绿 | 无 |
| `tests/contract/test_fc1204_coverage_ratchet.py` FROZEN/TIER1 floors | `dropbox_governance.py:95(TIER1)`、`archive_retired_evidence.py:95`、`duplicate_cleanup.py:74`、`focus_cleanup.py:86`、`prune_retired_evidence.py:87` 未改；stub化通常只升不降 | 在CI覆盖率轮次复核实测值；本卡未跑全量coverage（按卡不跑跨仓包） |
| `tests/contract/test_fc1201_root_hardcode_gate.py` `FC_1201_FROZEN_ALLOWLIST` 与 `architecture_gate._ROOT_HARDCODE_ALLOWED_FILES` | 均含 `focus_cleanup.py`，本卡未动二者 | 若MAIN日后清理focus_cleanup残留allowlist，须**同时**改两处冻结基线（本卡未改） |
| `tools/pre_push_gate.py` fast集合 | 含 `test_zr203_reader_rewire.py::test_read_entrypoints_never_construct_catalog_store`（绿）；不含本卡7文件 | MAIN 若要把新g3测试纳入CI fast/smoke集合，自行添加（本卡未改） |
| 预存在红灯（与本卡无关，报备） | `test_zr203_reader_rewire.py::test_write_paths_still_use_store`：master HEAD同样失败（`service.py` 中 `self.store,` 计数 3 < 4，源于18da250重构） | 归属 MAIN（service.py 不在本卡写集） |

## 5. 应替换的历史测试

| 测试 | 状态 | 说明 |
|---|---|---|
| `test_source_catalog_focus_cleanup.py` / `test_source_catalog_archive_retired.py` / `test_source_catalog_prune_retired.py` / `test_source_catalog_duplicate_cleanup.py` / `test_dropbox_governance_fc503.py` | **本卡已替换**（在写集内） | “批准后成功删除/归档/恢复/公司特例阻断”断言改为退休/同证据同分类断言；读责任（source/SHA/locator/排序/分页/journal读/语义区别）未删 |
| `test_source_catalog_duplicate_cleanup.py::test_control_center_exposes_browse_preview_and_single_copy_recycle_flow` | **本卡已删** | 过期入口断言（`scripts/source_catalog_control.ps1` 不存在，按卡不重建） |
| `test_source_catalog_semantic_duplicates.py::test_semantic_member_is_not_recyclable` | 保持绿（未改该文件） | 其 `pytest.raises(DuplicateCleanupError)` 靠 `DuplicateMaintenanceRetired` 双基类成立；**若MAIN移除双基类**，需把该断言替换为 `RetiredMaintenanceError` |
| `test_r4b02_candidate_selection.py`（list_groups 两处） | 保持绿（未改） | 仍断言 `total_reclaimable_copies>=1`（本卡保留该字段并加了上界标注） |
| CLI 级历史断言（focus/duplicate CLI 测试） | 本卡已按“未接线现状”更新为 fail-closed | MAIN 接线后需把这些断言改为具名非零结果（`error_type`/exit 形态由MAIN定） |

## 6. 集成验收口径

MAIN 在 G2-12 完成后，把本包（库层）与公共CLI接线作为**同一个发布写集**验收：不为每个stub增签收；一次跑本卡责任命令 + MAIN更新后的CLI断言；`handoff.json.main_integration` 字段已给出 `retirement_error`/`cli_branches`/`code_identity_paths`/`engineering_lists` 摘要。
