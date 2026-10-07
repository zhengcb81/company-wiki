# G3-CWP-MAINT Progress Log

## Session 2026-10-07 — complete

### Baseline
- Worktree `C:/Users/郑曾波/Projects/_g3/CWP-MAINT/company-wiki`, branch `codex/g3-cwp-maint`, base `5930a644453ed46494c2c83c5ecfb97767fa9492`（目录/分支原空闲，未覆盖）。
- Baseline related tests (5 historical files): **25 passed / 1 failed** — the failure is the stale `scripts/source_catalog_control.ps1` assertion (card: 过期入口断言，不重造脚本).
- `.planning/g3-cwp-maint/scratch`：**absent at start**（本卡创建）；`docs/implementation/g3-cwp-maint/` 不存在（本卡创建）。

### RED（先写测试）
| Evidence | Result |
|---|---|
| `test_g3_retired_maintenance.py` | collection ERROR：`ModuleNotFoundError: maintenance_retirement` |
| 其余4个新/改写文件（focus/archive/prune/duplicate） | 同上，5 collection errors |
| `test_g3_readonly_inventory.py` | 4 failed / 2 passed：`catalog._store is not None`（list_groups构造了Store）、`KeyError: 'inventory_only'`、positional调用 TypeError |
| `test_dropbox_governance_fc503.py` 新同证据测试 | 1 failed：`GovernanceError: FC-503: 中国平安 candidate ... classified eligible`（公司特例throw仍在） |

### GREEN（实现后）
- 责任命令（卡片§5的一次集中责任命令，7文件）：**35 passed / 0 failed / 0 skipped，exit 0，39.72s**（记录运行）。
- 实现：新增 `maintenance_retirement.py`；`focus_cleanup`/`archive_retired_evidence`/`prune_retired_evidence` 收缩为薄stub（751→53、295→31、659→33行）；`duplicate_cleanup` 保留只读清单+journal读（572→约360行，写入口退休，两SQL转`catalog.reader`）；`dropbox_governance` 去公司特例throw+`inventory_only`；`tools/dropbox_governance_replay.py` 改只读报告入口。

### Collateral sanity（写集外回归检查）
| 命令 | 结果 |
|---|---|
| `pytest tests/contract/test_source_catalog_semantic_duplicates.py test_zr203_reader_rewire.py test_fc1201_root_hardcode_gate.py test_fc1203_dead_helpers_absent.py test_source_catalog_code_identity.py` | 22 passed / **1 failed — `test_zr203_reader_rewire.py::test_write_paths_still_use_store`：在原仓master HEAD同样失败（service.py自18da250起 `self.store,` 计数=3<4），与本卡无关，预存在** |
| `pytest test_r4b02_candidate_selection.py test_architecture_gate.py unit/test_architecture_gate.py test_future_root_config_only.py test_three_root_consistency_fc604.py test_r9_v1_removal_gate.py test_fc1204_coverage_ratchet.py test_check_unique_test_symbols.py` | 52 passed / 6 skipped |
| `pytest test_dropbox_config_invariants.py test_dropbox_root_policy_fc501.py test_source_catalog_dropbox_probe.py` | 11 passed / 1 skipped |
| `pytest test_source_catalog_export_index.py test_source_catalog_control.py` | 32 passed |
| `pytest test_source_catalog_pipeline.py test_source_catalog_background_reliability.py` | 19 passed |
| `ruff check src tests/unit tests/contract tests/e2e scripts` | All checks passed |
| `ruff check` 逐文件（含 tools/ + 新测试） | All checks passed |
| `python -m mypy` 六个改动src模块 | Success: no issues in 6 files |
| `python scripts/host_assumption_guard.py` | violations=89; **new=0**（baseline 71 + registered 11），exit 0 |
| `python tools/check_unique_test_symbols.py`（7个测试文件） | OK，no duplicate definitions |
| `python -m compileall -q src scripts tests tools` | exit 0 |
| `python tools/dropbox_governance_replay.py`（无参数） | 打印只读报告契约，exit 0，未解析任何root |

### Decisions (from task_plan D1–D5)
- duplicate写入口抛 `DuplicateMaintenanceRetired(RetiredMaintenanceError, DuplicateCleanupError)`：canonical信号 + 旧catcher兼容（写集外 `test_source_catalog_semantic_duplicates.py::test_semantic_member_is_not_recyclable` 因此保持绿，未改该文件）。
- focus preview/apply/restore、archive/prune、recycle-bin、journal.record 全部退休；`now` 改可选；`eligible_for_recycle` 全false + `inventory_only`/`original_delete_count=0`/`reclaimable_is_upper_bound`。

### External effects
- network_requests=0, model_posts=0, raw_deleted=0, production_writes=0；真实Dropbox未扫描；回收站未执行；生产库/原件未动。

### Cleanup
- `.planning/g3-cwp-maint/`（含空scratch）：本卡创建、结束时删除恢复absent（删除前核对绝对路径包含 `.planning/g3-cwp-maint` 且无reparse）。
- 测试数据库/日志均在pytest临时目录与本卡worktree `__pycache__`（gitignored）。

### Commits & push
- `245a7f773a75a7e757ce71b9fca093d99788a9e6` 代码+测试+文档（pre-commit: ruff Passed、host guard Passed）
- `53cb25b` handoff.json（g3-handoff/1，head_commit=245a7f7）
- 首推在lane worktree被 pre-push basetemp≤60字符规则拦下（64字符，未跑任何测试；同 N5-DOCSET/N6-BUDGET 根因）→ 按既定裁定从主检出上下文 `git -C C:/Users/郑曾波/Projects/company-wiki push -u origin codex/g3-cwp-maint` → gate GREEN，推送成功；未用 --no-verify，未改任何门/CI文件。

## Next Step
本卡完成；交 MAIN 集成（见 main_wiring.md）。
