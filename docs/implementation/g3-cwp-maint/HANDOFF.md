# G3-CWP-MAINT Handoff — 旧维护后端退休与只读库存

Lane: `G3-CWP-MAINT` · base `5930a644453ed46494c2c83c5ecfb97767fa9492` · branch `codex/g3-cwp-maint`
worktree `C:/Users/郑曾波/Projects/_g3/CWP-MAINT/company-wiki`

本包交付**稳定库层接口 + 接线说明**。公共CLI/help退休、工程清单与源码指纹同步属于 MAIN 的 G2-12 同次集成责任，**本卡不声称已发布完成**（见 `main_wiring.md`）。

## 1. 保留的 API（真实caller）

| API | 责任 | 真实caller（写集外） |
|---|---|---|
| `maintenance_retirement.RetiredMaintenanceError(RuntimeError)` | 统一退休异常：`code="MAINTENANCE_OPERATION_RETIRED"`（类属性+实例）、`operation: str`；消息只讲退休+只读inventory，不提示补签收/token/backup，且不含 error_taxonomy 标记词（CLI侧按 `fatal` 呈现，待MAIN按operation转具名非零） | 新增，供 MAIN CLI 接线 |
| `focus_cleanup.FocusScopeCleanupService` / `FOCUS_CLEANUP_SCHEMA_VERSION` | ctor 不解引用catalog；`preview/apply/restore_files/restore_database` 全部立即退休 | `cli.py:31,203-213,897-931`；`__init__.py:81-84`；`code_identity.CORE_SOURCE_PATHS` 含该文件（文件必须存在） |
| `archive_retired_evidence.archive_retired_evidence(db, root, *, now=None, progress=None)` | 立即退休；`now` 改可选以兼容CLI（不传now）与测试（传now）两种旧caller形状，先于TypeError | `cli.py:1024-1030`（无now）；本卡测试 |
| `prune_retired_evidence.prune_retired_evidence(config, root, *, apply=False, retention_days=90, now=None, plan=None)` + `RETENTION_DAYS` | 立即退休（dry-run/--apply/缺now/任意plan同一结果） | `cli.py:1031-1037`（无now）；本卡测试 |
| `duplicate_cleanup.DuplicateCleanupService.list_groups(text=None, limit=50, offset=0, include_semantic=False)` | **只读清单入口**：两SQL改 `catalog.reader`（0 Store构造）；`eligible_for_recycle` 全false；新增 `inventory_only`/`original_delete_count=0`/`reclaimable_is_upper_bound`；reclaimable数值保留为注册逻辑上界 | `cli.py:1049-1055`（`duplicates`命令）；`test_r4b02_candidate_selection.py:778,839`；`test_source_catalog_semantic_duplicates.py:109,142` |
| `duplicate_cleanup.DuplicateCleanupJournal.read_all()` | 历史journal读取（缺文件`()`、坏行/缺字段/坏schema→ValueError），读不改字节 | `service.py:1032-1034`（export_indexes CSV） |
| `duplicate_cleanup.DuplicateCleanupService` ctor / `DuplicateCleanupError` / `DuplicateCleanupJournal` ctor / `DUPLICATE_CLEANUP_SCHEMA_VERSION` | 兼容保留：ctor只做isinstance+路径，不碰store/journal文件 | `__init__.py:74-80`；`test_source_catalog_semantic_duplicates.py` |
| `dropbox_governance.inventory_dropbox(root, *, catalog=None, other_root_ids=(), company_names=())` | 只读API保留；**公司特例throw已取消**——同证据同分类，`pingan` 降级为诊断计数；新增 `inventory_only: True`；`writes=0` 不变；缺身份仍走通用分类器 unprovable，不伪造verified；真实读取异常不吞；无写回 | `tools/dropbox_governance_replay.py`；`test_dropbox_governance_fc503.py` |
| `dropbox_governance.GovernanceError` | 仅导入兼容（不再被抛出），docstring已标注 | `test_dropbox_governance_fc503.py`（issubclass 断言） |

`include_semantic` 链已核为只读：`catalog.semantic_duplicate_groups()` 用 `self.reader`，`_annotate_locations` 是无DB静态纯函数——**无需修改禁止写的catalog实现**。

## 2. 删除的 API/实现（不再可达）

- `archive_retired_evidence`：`ArchiveReport`、`_row_digest/_sha256_file/_atomic_write_text/_publish/_verify_snapshot/_validate_required_now/_target_paths/_write_snapshot_rows/_check_reconciliation/_verify_and_publish/_write_manifest` 与整个快照/manifest算法（gzip发布、复核、目录创建、只读连接）。
- `prune_retired_evidence`：`PrunePlan/PruneRefused/PruneReport/VerifiedArchive`、`_load_verified_archives` 验证梯、`_build_plan/_apply_prune/_delete_batch/_pending_receipt` 等破坏链与锁/收据/删除实现。
- `focus_cleanup`：`_scope/_filesystem_plan/_database_plan/_build_plan/_public_plan/_archive_files/_atomic_write/_sha256_file/_load_metadata/_rows/_in_clause`、`apply` 的锁/事务删除/归档/快照、`restore_files/restore_database` 的重建算法（751→53行）。
- `duplicate_cleanup`：`_prepare/_validated_path/_confirmation_token/_utc_now/_sha256_file`、confirmation-token 链、`recycle_to_windows_bin` 的 ctypes SHFileOperation 实现、`Journal.record` 的写盘实现（签名保留，调用即退休）、`CatalogOperationLock`/`canonical_json` 依赖。
- `dropbox_governance`：`raise GovernanceError(...)` 公司特例（`_is_pingan_candidate` 保留仅作诊断计数）。
- `tools/dropbox_governance_replay.py`：真实生产root双扫、`CONFIG_PATH/CATALOG_PATH` 生产耦合、`_pingan_retired_invariants` 人工签收、`pingan eligible != 0` 断言；改为**只读报告入口**（无参=打印只读契约不解析任何root；`--root`=显式路径只读双扫+确定性摘要）。未执行真实Dropbox扫描。
- 历史测试中“批准后成功删除/归档/恢复”断言全部替换为退休断言；过期 `scripts/source_catalog_control.ps1` 断言删除（脚本不重建）。

## 3. RED → GREEN

1. **RED**：新增 `test_g3_retired_maintenance.py`、`test_g3_readonly_inventory.py`；改写5个历史测试。观察到：5文件 collection `ModuleNotFoundError: maintenance_retirement`；readonly 4 failed（`catalog._store is not None`、`KeyError inventory_only`、positional TypeError）；fc503 同证据测试 `GovernanceError: 中国平安 candidate ... eligible`。
2. **GREEN**：责任命令（卡片§5原样7文件）**35 passed / 0 failed / 0 skipped，exit 0，39.72s**。
3. 写集外 sanity：semantic_duplicates / r4b02 / fc1201 / fc1203 / code_identity / architecture / future_root / three_root / r9 / fc1204 / unique_symbols / dropbox* / export_index / control / pipeline / background_reliability —— **全绿**（52+22+11+32+19 等批次）。
   唯一红：`test_zr203_reader_rewire.py::test_write_paths_still_use_store` —— **预存在**（原仓master HEAD同样失败，`service.py` 自18da250起 `self.store,` 计数=3<4；该测试不在本卡写集，不在CI fast集合，报给MAIN）。
4. 静态：ruff 全CI范围通过；mypy 六改动模块通过；host-assumption-guard new=0；unique test symbols OK；compileall 通过。

## 4. 0副作用证据

- 单元：`_ExplodingCatalog`（任何属性访问即断言失败）构造 focus service 并调全部四入口 → 只见退休异常；prune/archive 以缺失DB、缺now、apply、假plan 调用 → 全部退休，`tmp_path` 树为空（0文件0目录）。
- duplicate：真实 `SourceCatalog`（不存在的库）ctor 后 `catalog._store is None`；preview/recycle/recycle-bin/journal.record 全退休且 `catalog_dir` 未创建、journal文件不存在、目标文件sha不变、recycler零调用。
- 集成：真catalog fixture（scan+normalize+retire 为合法写阶段）→ 关闭writer（`_store=None`）→ 记录目录/DB sha/schema/journal/raw sha+mtime 指纹 → 只读 `list_groups`+`read_all` 各两轮 → `_store` 仍为 None、指纹逐项相等。
- E2E：scratch内两份相同字节原件 + 一份同大小不同字节 + canonical/semantic/retired 记录；先实际读取清单（exact组2份、semantic组1份、near文件不在exact组、journal空）→ 逐个调用13个旧写/restore入口 → 每个抛具名退休（operation逐项断言）→ 两原件sha、DB sha、整棵目录树逐字节不变。
- CLI（库层视角，MAIN未接线前的现状）：`focus-cleanup` dry-run/--apply-with-guards、`duplicate-preview`、`duplicate-recycle` 均 exit 1 + stderr `status=failed` + 消息含 retired/operation，receipt/snapshot/journal零创建；`duplicates`（只读）仍 exit 0。
- 生产原件删除0、网络0、模型0、真实Dropbox扫描0、回收站执行0。

## 5. 兼容与限制

- **D1 双基类**：duplicate 写入口抛 `DuplicateMaintenanceRetired(RetiredMaintenanceError, DuplicateCleanupError)`——MAIN按 `RetiredMaintenanceError` 接线不受影响；写集外 `test_source_catalog_semantic_duplicates.py::test_semantic_member_is_not_recyclable` 的 `pytest.raises(DuplicateCleanupError)` 因此保持绿（该文件不在写集）。若MAIN将来去掉双基类，需同步替换该测试断言（见 main_wiring）。
- 真实CLI的help/子命令删除与具名非零映射**尚未接线**（cli.py不在写集）；当前行为=fail closed `fatal`，不是最终形态。
- `fc1204` 覆盖率门禁需完整coverage run 才判定；本卡未跑全量（按卡不跑跨仓包）。stub化只会提高这些模块覆盖，CI覆盖率轮次应无风险，但由MAIN在覆盖率轮次复核。
- editable安装指向原仓src：worktree代码只经 `tests/conftest.py` 的 `sys.path` 注入生效（与其它worktree一致）；`tools/dropbox_governance_replay.py` 自行插入本仓 `src`。
