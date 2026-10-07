# G3-CWP-MAINT Findings（只读调研，未改生产）

## 写集与基线
- 基线 `5930a644453ed46494c2c83c5ecfb97767fa9492`；其上 321c97d/7f678f7/12ba61b/8bb1b6c 全为 docs-only，src/tests 与 master HEAD 等价。
- 原仓脏文件（MAIN）：`config/source_acquisition.yaml`、`src/.../acquisition.py|acquisition_service.py|close_gap.py`、未跟踪 `tests/contract/test_single_intent_latest_acquisition.py` — 不借用。
- 新worktree `C:/Users/郑曾波/Projects/_g3/CWP-MAINT/company-wiki`，分支 `codex/g3-cwp-maint`，原目录/分支均空闲。

## 模块与真实caller
| 模块 | 行数 | 真实caller（写集外） |
|---|---|---|
| focus_cleanup.py | 751 | `cli.py:31` import、`cli.py:203-213` parser、`cli.py:898-931` handler（preview/apply）；`code_identity.py:18` CORE_SOURCE_PATHS（文件必须存在）；`architecture_gate.py:158` 与 `test_fc1201` 冻结allowlist（含focus_cleanup.py，不能动） |
| archive_retired_evidence.py | 295 | `cli.py:1025-1030`（**不传now** → 今天会TypeError）；测试 archive/prune 文件（写集内） |
| prune_retired_evidence.py | 659 | `cli.py:1032-1037`（**不传now**）；测试文件（写集内） |
| duplicate_cleanup.py | 572 | `cli.py:28` import + `duplicates/duplicate-preview/duplicate-recycle` 分支；`service.py:1032-1034` `DuplicateCleanupJournal.read_all()`（export读路径，必须保留）；`__init__.py:74-80` 导出5个名字必须继续可导入；`test_source_catalog_semantic_duplicates.py:154/156` 调 `preview()` 且期望 `DuplicateCleanupError`（**写集外，必须保持绿**）；`test_r4b02_candidate_selection.py:778/839` 调 `list_groups()`（断言 total_reclaimable_copies≥1） |
| dropbox_governance.py | 198 | `tools/dropbox_governance_replay.py`；`test_dropbox_governance_fc503.py`（写集内） |

- `scripts/source_catalog_control.ps1` 不存在，`test_control_center_...` 是过期断言（基线即红），按卡删除不重造脚本。
- 基线责任测试：5文件 25 passed / 1 failed（即上述过期断言）；`test_source_catalog_semantic_duplicates.py` 6 passed。

## 只读链现状
- `SourceCatalog.store` 惰性构造 CatalogStore（不存在路径会 mkdir+DDL+seed）；`SourceCatalog.reader` 惰性构造 `ReadOnlyCatalogReader`（mode=ro + query_only，缺库即 CatalogReaderUnavailable 且不落盘）。
- `list_groups` 现有两处 `self.catalog.store.fetchall` → 按卡改 `catalog.reader.fetchall`（reader.fetchall 签名相同，返回 sqlite3.Row）。
- `include_semantic` 链：`catalog.semantic_duplicate_groups()` 已经用 `self.reader`（service.py:839+），只读；`_annotate_locations` 是静态纯函数，无DB。**无需改禁止写的catalog实现**。
- `FocusScopeCleanupService.__init__` 今天执行 `self.store = catalog.store` → 构造即开写Store，必须去掉。
- `DuplicateCleanupService.__init__` 不碰store（isinstance + journal路径），`DuplicateCleanupJournal.__init__` 只设path不mkdir；`record()` 才写盘。
- `recycle_to_windows_bin` 直接动文件（SHFileOperationW），无写集外caller（仅 `__init__` 导出 + 写集内测试monkeypatch）。

## 门禁/清单约束（不改它们）
- `code_identity.CORE_SOURCE_PATHS` 含 focus_cleanup.py → 文件必须保留（保留薄stub即可）；指纹动态计算，无pinned hash测试。
- `test_fc1204_coverage_ratchet` 读 coverage.json，仅在完整coverage跑后判定（不在责任命令内）；stub全被覆盖只会更高。
- `test_fc1201` 冻结 allowlist 相等断言 —— 不动 architecture_gate.py 即可。
- `test_fc1203_dead_helpers_absent` 只针对 entity_resolver/reuse_latest_policy 等 —— 不受影响。
- `test_zr203_reader_rewire::test_read_entrypoints_never_construct_catalog_store` 的 READ_ENTRYPOINTS 只含 service.py/resolver.py。
- Ruff CI 范围：src、tests/unit、tests/contract、tests/e2e、scripts（tools/ 不在ruff范围，但仍保持整洁）；mypy CI 固定文件列表不含本卡模块。
- pre-commit（提交时）：ruff(staged) + mypy(固定列表) + config-doctor(不匹配) + host-assumption-guard(scans tests/与src/：测试禁止绝对主机路径字面量、未守卫capability调用)。
- pre-push：`--fast-contracts-only`（固定curated集合，不含本卡测试）；ruff全scope、compileall、config_doctor、host guard、unit套件不在fast-only路径（fast-only只跑fast gate）。

## CLI错误形态
- `cli.main` 统一 `except Exception → structured_error(exc)` 打 stderr JSON 并 return 1；`classify_exception` 对 RetiredMaintenanceError（RuntimeError且文本无 timeout/paused/locked 标记）→ `error_type="fatal"`，`retryable=false`。退休消息必须避开 taxonomy 标记词（timeout/timed out/deadline/busy/locked/paused）。
- MAIN 后续按 `RetiredMaintenanceError.operation` 转具名非零结果 —— 本卡只保证异常与operation语义。

## 关键决策依据
1. 卡§1把 `duplicate-preview/recycle` 与 confirmation token 明确列入退休对象；§3.2 要求“写操作被调用即抛统一退休异常，在打开Store/锁/文件/记录journal之前退出”。
2. 卡§4.1 “archive/prune未传now” = 旧caller形状；因此 now 必须改成可选，先于校验抛退休异常。
3. 卡§6要求 main_wiring 列“应替换的历史测试”；但写集外唯一受阻测试是 semantic preview 期望 DuplicateCleanupError —— 用双基类异常保持其绿，比留给MAIN更安全（见 D1）。
4. `GovernanceError` 无写集外raise caller（仅fc503测试import），保留类作导入兼容、不再抛出（卡§3.5 取消公司特例throw）。
