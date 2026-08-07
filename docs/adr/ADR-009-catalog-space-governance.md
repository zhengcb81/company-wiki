# ADR-009：catalog 空间治理（退役 / 归档 / 保留策略 / 粒度提案）

- 状态：Accepted（2026-08-07，D1–D5 全部拍板；Phase 1–2 已实施，Phase 2.2/3/4 为提案或远期）
- 关联：`docs/plans/catalog-space-remediation/`（task_plan/findings/progress）

## Context

`.source_catalog/catalog.sqlite3` 达 43.9 GB（evidence_spans 25,985,291 行），其中 **95% 挂 phase-15.6 审计文档**（9,578 份"审计但 active"）；软删除永不物理回收；归一化仅 11%（pending 20,728）；单元格级证据粒度导致体积倍数（原文 23.4 GB → 证据库 43.9 GB）。若全量按现状粒度归一化，粗估 100 GB+。

## 决策（D1–D5）

| # | 决策 | 选择 | 状态 |
|---|---|---|---|
| D1 | phase-15.6 审计文档处置 | **全部正式退役**（软删除 + audit 对齐） | ✅ 已实施（2026-08-07） |
| D2 | 证据粒度 | **表格级**（span 到整表） | 提案（Phase 3，上游 parser/schema） |
| D3 | 新闻（original_news 903）证据 | **免 span**（只保留 normalized.md） | 提案（Phase 3，上游 normalize 策略） |
| D4 | catalog 迁移 D: | **不迁**（留 C:，现余 164.5 GB） | ✅ 定案 |
| D5 | retired 归档保留期 | **90 天**后物理回收 | 定案（Phase 2.3 待实施） |

## 实施记录（Phase 1–2，2026-08-07）

- **Phase 1.1 对账**：9,578 份分类（A 2 retired / B 9,576 active 含 1,686 有 span / C 79 stub / D 7,892 无 span），可回收 ≈29.5 GB。
- **Phase 1.2 reconcile**（`reconcile_retire_state.py` + cli `reconcile-retire`，dry-run 默认 + `--apply` 显式）：生产 apply 退役 **9,499**、stub 物理删 **77**（79 中 2 个已 retired），**audit-vs-status 归零**；receipt `artifacts/gates/reconcile-retire-20260807T080844Z.jsonl`。
- **Phase 2.1 归档**（`archive_retired_evidence.py` + cli `archive-retired-evidence`）：streaming 导出 retired 文档 evidence_spans → gzip JSONL（`source_manifests/archive/{date}/retired-evidence.jsonl.gz`），**25,708,956 行 == 25,708,956，ok=true**，4.6 GB gzip。
- 证据保护：退役（软删除）**不碰 span**，90 天保留期内 DB 证据完整可查；归档为回收前的只读保护副本。

## 后果

- **正**：状态一致化（audit vs status = 0）；证据可追溯（归档完整）；90 天后可回收 ≈29.5 GB；DB 体积未来可控（D2/D3 提案落地后）。
- **负**：D2 表格级后无法定位到具体行/单元格（研究引用精度到表格级）；D4 不迁则 C: 需容量监控；D3 新闻无 span 级溯源。
- **待办**：Phase 2.2 `archived_at` schema 提案；Phase 2.3 scheduler 定期回收任务（90 天窗口）；Phase 3 parser 粒度提案（表格级 + 新闻免 span）；Phase 4 容量模型与监控；Phase 6 验收。

## 不变量保持

- 单线程治理（worker-pause 下执行写操作；只读查询/归档走只读连接不取锁）。
- 每次写操作：dry-run → apply → 验收归零 → receipt。
- 删除/退役前归档；绝不在无保护下物理删证据。
