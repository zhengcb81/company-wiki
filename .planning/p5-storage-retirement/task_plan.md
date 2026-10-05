# P5-STORAGE 施工计划（worktree: cwp-storage-tool）

任务卡：docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/p5_storage_retirement_engine.md
分支 codex/p5-storage-retirement（基线 a2563f9，含发布基线 f775406）。只新增 tools/legacy_storage*、tests/{unit,integration}/test_p5_storage_retirement*、.planning/p5-storage-retirement/、docs/implementation/handoffs/P5-STORAGE/。

## 关键事实（desk survey 结论）
- schema 主文件 src/company_wiki/source_catalog/store.py `_DDL`（v1.2.0）：artifacts(document_id,source_id,artifact_role,path,content_sha256,byte_size,generator_name,generator_version,status,...)，evidence_spans(span_id,document_id,source_id,locator,raw_text,span_json,parser_name,parser_version,parse_status)，narrative_artifact_versions(prepared/visible/retired/quarantined)。
- 旧派生目录 config.derived_dir = catalog_dir/derived；normalized: derived/{sha[:2]}/{sha}/normalized.md（generator source_catalog_normalizer@1.0.0）；summary: 同目录 summary.md（extractive 或 llm）；sections: derived/{normalized_sha[:2]}/{normalized_sha}/sections/{role}.md。
- artifacts.status 消费门槛：`validate_artifact` 仅接受 'completed'（artifact_handle.py:87）。工具用 status='retired' 作为现行 schema 支持的不可复用状态（DDL 对该列无 CHECK）。
- Writer 连接 PRAGMA foreign_keys=ON、WAL；evidence_spans/artifacts 无被引用 FK；producer_events/producer_attempts 无 FK，属不删事实。
- 事实表（保留）：catalog_meta, roots, sources, documents, locations, entities, document_entities, source_metadata_assertions, document_fingerprint_state, document_retire_audit, document_restore_audit, activation_journal, llm_summary_failures, remediation_proposals, producer_events, producer_attempts, migration_journal, migration_rollback_journal, artifact_bindings；保护：narrative_artifact_versions + objects/ 内容寻址文件；未知表保守保留并报告。
- 候选范围：artifacts.role∈{normalized,summary,sections} 且 generator∈{source_catalog_normalizer, source_catalog_extractive_summary, source_catalog_llm_summary, source_catalog_section_extractor}，路径必须实际落在 catalog_dir/derived 之下（含 escape/junction/hash不符具名排除）；derived 下无 DB 记录的松散文件=unreferenced，报告保留。原件永不入候选。
- prune-spans：显式 selection(parser_name/version+source/document ids)，keep-refs 保护 (source_id,locator)，evidence_spans 无 artifact_id 外键。
- vacuum：事务外 VACUUM；记录 file bytes、page_count、freelist_count 事实口径与磁盘实测分开。
- 报告 schema：cwp-storage-retirement/1。

## 步骤
1. [进行中] RED：边界保护单测（inventory 只读零写、原件/NewFinal/未知不入候选、bytes/hash 变化拒绝、幂等、escape 拒绝）。
2. 实现 inventory（A）：只读， 待遇=候选清单+manifest。
3. 实现 retire-derived（B）：事务内 status='retired'、核当前状态、提交后 unlink 精确文件、already_absent、重复执行幂等、completed 悬挂句柄核验。
4. RED→prune-spans（C）：显式 selection、keep 集验证、FK/integrity、中断幂等。
5. RED→vacuum（D）：VACUUM 前后实测、无活动 writer、错误具名停止。
6. 集成 E2E：拷贝中微2025年报(SHA d64c4108…48af) + 本地TXT 样本到独立短根；真实 scan/normalize/summary/sections、Replay 离线新 final（txt bundle）；四操作顺序执行；公开 source_reader_cli 实读 + narrative_transport_cli replay 前后通过。
7. 回归：既有 artifact/SourceRef/narrative reader 责任包 + 新测试；实 E2E opt-in。
8. 提交 + handoff（HANDOFF.md、handoff.json、示例 manifest/report）。

## 边界
- 不写 src/、现有测试、DDL、config、pyproject/CI；不建第二个 Store/Worker；不做生产删除、不备份全库；0 网络调用；报告只在收据里填实测值，不填伪 0/估值。


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
