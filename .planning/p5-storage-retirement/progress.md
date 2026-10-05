# P5-STORAGE progress

- [x] Worktree/分支建立：codex/p5-storage-retirement @ a2563f9（含 f775406）
- [x] Desk survey：schema/artifact/span/reader/旧 prune 模块（结论见 task_plan.md）
- [x] RED 边界单测（收集失败确认）→ 单元 26 项 GREEN：
  - tests/unit/test_p5_storage_retirement_boundary.py（13）
  - tests/unit/test_p5_storage_retirement_spans.py（8）
  - tests/unit/test_p5_storage_retirement_vacuum.py（5）
  - 共享 fixture：tests/unit/test_p5_storage_retirement_common.py（真实 CatalogStore + 真实 normalizer/summary/sections/章节生产者 + 新 narrative final）
- [x] 系统实现：tools/legacy_storage/{core,selection,inventory,retirement,spans,shrink,facts}.py + tools/legacy_storage_retirement.py（inventory / retire-derived / prune-spans / vacuum；mutating 需 --apply）
- [x] 关键行为证明：inventory 零写；status='retired' 句柄必拒于 validate_artifact；hash 不匹配/逃生路径/未知 generator 具名排除；rerun 幂等不夸大释放（sections/index.json 归为 managed_files 一并退库）
- [x] 真实原文 E2E（tests/integration/test_p5_storage_retirement_e2e.py，-m slow，168.59s）：拷贝中微2025年报（SHA d64c4108…48af）+ TXT；真实 scan/normalize（pdf_page_aware_core spans）/summary/sections；公开 NarrativeArtifactStore graft 新 final（Replay 离线真实 bundle）；四操作顺序执行；source_reader_cli（source_export）与 narrative_transport_cli reference+read 前后均通过且 stdout SHA 一致；prune 删除全部 pdf spans 0 泄漏、keep ref 存活；receipts 实测
- [x] 回归：tests/contract/test_source_version_reader.py + test_narrative_artifact_store.py + test_narrative_transport_cli.py + tests/integration/test_narrative_transport.py → 79 passed / 1 failed，该失败 test_current_public_producer_regenerates_normalized_txt_golden 在 MAIN checkout 同样失败（selector 0.3.0 vs golden 0.1.0，pre-existing，与本线无关）
- [x] ruff：新方法 ruff check 通过
- [x] handoff 样本：docs/implementation/handoffs/P5-STORAGE/samples/*.json（1953/12120/5173/5067 B，全为 fixture 实测值）
- [x] 提交到 codex/p5-storage-retirement；HANDOFF.md + handoff.json
- 测试临时 root：pytest basetemp 与 tempdir 均自动清理；本根开始"absent"，结束恢复 absent（pytest 清理）


## MAIN integration node 1 (2026-10-05)

- Candidate integration tree: .codex/worktrees/p5-storage-integration/company-wiki,
  branch codex/p5-storage-integration, baseline MAIN 18da250 plus original
  delivery code/docs cherry-picks d6b6e36 / 4387661.
- Eight real-schema original/path/managed-byte/resume/unlink behavior tests first
  RED (8 failed / 26.63s). Fixed current-record bindings, sections index scope,
  pinned child hashes, lock+metadata-first retirement, bounded resume metadata,
  missing-file handle retirement, actual unlink failure statuses; removed global
  index sweep. No source/raw/new-final mutations, no production clean-up.
- Recovery+existing boundary package: 20 passed / 1 failed / 60.48s. Failure was a
  missing artifact_id=None on managed child report, fixed; exact idempotent case
  GREEN / 3.64s. Eight safety tests and all 13 boundary cases green in combined
  runs. Ruff all tool files/helper/recovery test green after removing unused var.
- These tests invoke real parser subprocesses and SQLite: moved boundary/spans/
  vacuum/recovery to tests/integration/test_p5_storage_retirement_*.py. Common
  fixture moved to tests/support/p5_storage_catalog_fixture.py. Thus everyday
  tests/unit collection gains no parser suite. Original HANDOFF remains the
  historical delivery evidence; final acceptance must cite current paths.
- Node 2 pending: true read-only dry-run/WAL handling; streaming exact span prune
  (no million-entry set/list/JSON); actual pre/post VACUUM snapshots/disk space;
  protected object root accuracy; consolidated real annual/TXT raw/final E2E.
  Tools NOT ACCEPTED for main or production deletion yet.
