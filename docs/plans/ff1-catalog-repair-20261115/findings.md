# 发现 — ff1-catalog-repair-20261115

## F1 undated 根因链（2026-11-15 只读实测）

1. 4 个 undated MDB documents 行全部带 2026-11-08 06:09 批量写入的 verified source-facts 断言，
   patch 里 `published_date: None, filing_date: None`（显式未知）。
2. ensure 导入路径 `canonical_writer._record_validated_capture`：facts（含
   `published_date=candidate.filing_date`）在存在 prior 断言时被
   `facts = {k:v ... if k not in previous}` 全键过滤——显式未知（None）也按"已记录"处理
   （注释"explicit correction/unknown is stronger"），所以 2026-11-10 导入 mdb-20260131 时
   声明值 2026-03-11 被丢弃，documents.published_date 仍 NULL。→ B3 修这里。
3. scanner `_merge_document_row` 的 verified fact pinning：`fact_columns` 来自
   `source_fact_projection`（patch 的 published_date=None 也算投影），`effective` 判定
   `new_raw == old_raw`（sidecar 声明值没变）→ 事实值 None 生效。带 None-patch 断言的
   存量行，单纯 re-register/re-scan 不会填 published_date。→ B2 按任务书实现定向登记自愈
   （对无断言的 fixture 行有效）；存量 pin 行需独立 facts 修正，超出本 lane。
4. dayu_portfolio 组目录 meta.json 与 company_raw .source.json 都带 filing_date 声明
   （scanner `_DECLARING_KEYS`: published_date ← filing_date/published_date）。

## F2 结构要点

- `ResolutionResult`（resolver.py:728）已带 debug_trace/excluded_candidates；
  `_excluded_candidate`（resolver.py:1889）目前只带 document_id/qualification/source_ref
  —— B1 需补 B4 白名单字段与 exclusion_reason 闭集码，B2 用 document_id+source_id 查
  reader.exact_source_locations 得 root/relative_path（不往 result 里塞物理路径）。
- register 链：cli(register) → SourceCatalog.register_sources（CatalogOperationLock
  operation="source_registration"）→ registration_scope.register_catalog_sources →
  scanner.scan_catalog(root_ids={one}, relative_paths={...})。B2 提取
  `register_groups(catalog, root_id, relative_paths)` 库函数放 registration_scope.py。
- ensure 锁序：`_ensure` 里 `_select_for_ensure` 在 acquisition_mutex 之前调用，自愈插在
  decision 返回后、SELECTED 分支（ensure 锁）之前——天然无嵌套；journal 写入用独立
  append-only 文件 + 自有文件锁（acquisition journal 的 outcome 闭集不动）。
- FC-1301 门禁：所有新 snake_case reason/exclusion_reason 字面量必须在
  observability.REASONS + STAGES_BY_REASON 注册（additive，不动 REASON_TAXONOMY_VERSION=1.1）。

## F3 契约对照（B4）

- 候选来源：ambiguous-multiple（matches≥2）→ matches 投影，exclusion_reason=multiple_candidates；
  ambiguous-unknown-date / missing → resolution.excluded_candidates 投影（B1 补齐白名单字段）。
- publication_status 映射：qualification unknown/invalid→unknown；known/eligible→known；
  after_as_of→future。matches（handle）有 published_date，按 as_of 归一。
- 数量 ≤5 按既有顺序截断；completed/gap 不携带；pathless guard 沿用 `_contains_physical_field`。
