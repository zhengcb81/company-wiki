# G3-CWP-MAINT：旧维护后端退休与只读库存 — Task Plan

卡片：`docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/g3_cwp_maintenance_retirement.md`
工作树：`C:/Users/郑曾波/Projects/_g3/CWP-MAINT/company-wiki`，分支 `codex/g3-cwp-maint`，基线 `5930a644453ed46494c2c83c5ecfb97767fa9492`。

## Phase 1 基线与worktree — Status: complete
- [x] 核对原仓脏文件（MAIN未提交acquisition/close_gap），不借用
- [x] 创建独占worktree+分支（目录/分支原本空闲，未覆盖他人）
- [x] 读五模块+caller（cli.py分支、__init__导出、service.py journal读、code_identity、architecture_gate、fc1201/fc1204门禁）
- [x] 基线测试：5个相关contract文件 25 passed / 1 failed（`scripts/source_catalog_control.ps1` 缺失的过期断言）

## Phase 2 RED — Status: complete
- [x] 新增 `tests/contract/test_g3_retired_maintenance.py`（统一异常、写入口0副作用、CLI形状、E2E五类旧写）
- [x] 新增 `tests/contract/test_g3_readonly_inventory.py`（list_groups只读/分页/排序、journal读、dropbox同证据同分类）
- [x] 改写5个历史测试到新公开责任（删除批准后成功删除/归档/恢复断言与过期ps1断言）
- [x] 运行责任命令确认RED（记录在progress.md）

## Phase 3 GREEN — Status: complete
- [x] 新增 `src/company_wiki/source_catalog/maintenance_retirement.py`（RetiredMaintenanceError）
- [x] 五个旧模块收缩为薄stub：写入口立即退休（开Store/锁/文件/journal之前）
- [x] `list_groups` 两处SQL → `catalog.reader`；`eligible_for_recycle` 全false + inventory_only/上界标注
- [x] `dropbox_governance` 去掉公司特例throw，公司统计仅诊断
- [x] `tools/dropbox_governance_replay.py` 改只读报告入口（不扫真实Dropbox）
- [x] 责任命令 GREEN（35 passed / 0 failed，39.72s）

## Phase 4 验证与交接 — Status: complete
- [x] 邻接测试sanity（唯一红为预存在 test_write_paths_still_use_store）（semantic/r4b02/zr203/fc1201/fc1203/architecture/code_identity/control）
- [x] Ruff全CI范围/mypy六模块/host-guard new=0/unique symbols/compileall 全过
- [ ] `docs/implementation/g3-cwp-maint/{task_plan,findings,progress,HANDOFF,handoff.json,main_wiring}.md`
- [ ] 正常commit（不合master，push自己的分支）

## Decisions Made
- **D1** duplicate模块的退休异常用 `DuplicateMaintenanceRetired(RetiredMaintenanceError, DuplicateCleanupError)`：canonical信号仍是 RetiredMaintenanceError（MAIN按此映射），双基类让写集之外的 `test_source_catalog_semantic_duplicates.py` 既有 `pytest.raises(DuplicateCleanupError)` 继续为真（该文件不在本卡写集，不能改）。focus/archive/prune 直接抛统一异常。
- **D2** `focus-cleanup` 的 preview 也退休（卡片§1明确列 duplicate-preview 与 confirmation token；preview 是token/签收链的起点），apply/restore 同样退休。
- **D3** archive/prune 入参 `now` 改为可选（默认None）：旧caller（CLI不传now、测试传now）都要先命中退休异常而不是TypeError。
- **D4** `eligible_for_recycle` 统一false；新增 `inventory_only`/`original_delete_count=0`/`reclaimable_is_upper_bound` 顶层字段，不删 `total_reclaimable_*`（r4b02测试仍断言其≥1）。
- **D5** `GovernanceError` 类保留为导入兼容但不再被抛出；`inventory_dropbox` 的 `pingan` 统计保留为诊断键。

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| rg 在bash不可用 | 1 | 改用Grep工具/PowerShell等价命令 |
| 基线commit早于卡片发布docs commit | 1 | 卡片指定基线5930a64，其后4个commit均为docs-only，src等价；维持卡片基线 |

## Next Step
无 —— 本卡完成（commits 245a7f7 / 53cb25b / e00208d + 收口commit，已push `codex/g3-cwp-maint`，不合master）；交 MAIN 按 main_wiring.md 集成。
