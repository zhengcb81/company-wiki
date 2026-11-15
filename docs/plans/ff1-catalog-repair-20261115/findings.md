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

## F4 与任务书/契约的偏离（均已在报告登记）

1. base commit 用 ac8841c55（任务书 66c97834d 之后 master 另有 4 个 docs-only 提交，src 零差异）。
2. `register_groups` 签名为 `register_groups(catalog, root_id, relative_paths, *, budget=None)`（任务书
   `register_groups(root_id, relative_paths)`——库函数需要 catalog 句柄；CLI/service 均委托，行为不变）。
3. 修复 journal：独立 append-only `catalog_repairs.jsonl`（事件 `catalog_repair_applied`，含 root_id/
   relative_path/sidecar_kind/filing_date/data_source），不改 acquisition attempt journal 的冻结 outcome
   词表（其 CSV 读模型是既有契约）。
4. B4 未知 reason（词表外）：省略可选字段，不臆造映射（契约允许缺省；拒绝整个载荷对加法式消费方更糟）。
5. B4 被 after_as_of 排除的候选 exclusion_reason="other_excluded"（闭集无 future 码；
   publication_status 字段承载 "future"）。
6. B2 范围注记：存量被 2026-11-08 显式未知断言 pin 的行（真实 catalog 4 个 MDB 行），仅靠定向登记
   不会清除 scanner 的 verified-fact pin（`_merge_document_row` effective 逻辑）；B3 堵住新增缺口，
   存量 pin 行需要独立的 facts 修正 pass（不在本 lane 四件套内）。B2 验收按任务书在无 pin 的隔离实例上通过。

## F5 预存失败清单（干净 baseline worktree 实测，非本 lane 回归）

- test_activation_transaction.py::test_cli_activation_apply_rollback_roundtrip
- test_source_version_reader_cli.py::test_ensure_cli_latest_as_of_projects_gap_without_fetch_or_raw_change
- test_source_version_reader_cli.py::test_ensure_cli_latest_as_of_preserves_provider_unavailable_gap
- test_fc1301_reason_taxonomy.py::test_every_emitted_reason_is_registered（60+ 既有未注册 code，非本 lane 引入）
- test_source_catalog_gap_plan.py 3 例（latest_as_of gap 流，invalid_source_ref，同基线失败）
- test_lt_uj_e2e.py 5 例（同基线失败）
- contract 套件全量对照：分支与基线各 51 failed，逐名一致（自动化 store_boundary/cross_root/fc1201 前身/layer_public/location_switch×4/gp002/portfolio_promoter×4/cn_stockinfo×5/download_authorization×2/download_suppression/gap_plan×3/long_running/parser_liveness×2(子进程 flaky)/pilot_receipt×2/source_system_docs×5/zr404/zr501×2/lt_uj(_real)×12/ensure CLI×2 等），甄别过程中发现的 2 个真回归（root-kind 硬编码门禁）已由 aa35d8609 修复。

## F6 架构门禁修复记录（真回归 → 正当修复，未绕过）

- 初版 catalog_repair.py 内联 `root.kind == "dayu_portfolio"` / `in {"company_raw","directory"}`
  分派，触发 fc1201_root_hardcode_gate 与 future_root_config_only 两门禁（这两门禁在基线通过）。
- 修复：声明判定上移 scanner.py（layout owner，`_ROOT_HARDCODE_ALLOWED_FILES` 成员）新增
  `declared_group_publication_date(root, relative_path) -> (sidecar_kind, filing_date) | None`，
  只读、仅认 ISO 日期声明（filing_date→published_date 顺序与 _DECLARING_KEYS 一致）；
  planner 泛化调用，零 root token。门禁与全部 B2 测试转绿（aa35d8609）。

## F7 独立重审结论与 F-R3 修复（2026-11-15）

- 重审结论：0 个 OPEN P1/P2 成立；自报偏离 4 项（base commit、register_groups 签名、独立 repair
  journal、词表外 reason 省略）全部获批。
- OPEN P3 共 3 项：
  - **F-R3（本 lane 修复）**：CWP 投影放行未 trim 的 title——matches 分支与 excluded 分支都透传
    documents.title 原值，FF 消费方 `fetch_filing.py::_validated_operation_candidates` 以
    `value.strip() and value == value.strip()` 严格校验（title 分支，filing-fetch
    scripts/fetch_filing.py 约 923-925 行），违规整载荷拒收（upstream_error）。生产目录当前未
    观察到该形状（潜在配对断裂）。修复（生产方对齐，不改 documents 数据）：
    `operation_projection._project_candidate` 的 title 改经 `_candidate_title`（strip 后输出，
    空白-only fail-closed），B1 排除候选路径 `resolver._excluded_candidate` title 输出 strip——
    与既有 provider/form_type 等 strip 一致。测试：补 2 用例（"  mdb-2025 " 双分支投影后 trim
    断言 + 注释引用消费方形状规则；空白-only title 拒绝发射），56 通过。
  - **F-R1 / F-R2：随 handoff 交回**（不在本 lane 分支修复，按 §8 规矩移交）。

## F8 facts 修正 pass（2026-11-15 晚，用户全授权修改生产 catalog）

**授权**：用户 2026-11-15 明确授权对生产 `.source_catalog/catalog.sqlite3` 的 4 个 MDB 文档行做 facts 修正（仅新增 superseding 断言，严禁裸 SQL / 删除断言 / 触碰这 4 行之外数据——红线全程遵守）。

### 机制（superseding 断言如何压过旧 None pin）

研究确认（assertion_service.py / scanner.py / resolver.py / cli.py + test_ff1_import_published_date.py）：

1. 旧 pin 的成因：`source_fact_projection`（assertion_service.py:546）按 `ORDER BY created_at DESC LIMIT 1` 取最新 verified source-facts 断言并投影其 `source_fact_patch`（None 也投影）；scanner `_merge_document_row`（scanner.py:1842-1861）的 `effective` 判定在 sidecar 声明值未变（`new_raw == old_raw`）时让事实值生效——于是 None 压住声明值，定向登记（register_groups）无法回填（与 Lane B 隔离重放结论一致）。
2. 设计内修正路径：CLI `source-facts --request`（cli.py:902）→ `record_source_facts`（assertion_service.py:385）：
   - `validate_source_facts`：facts/evidence 逐字段校验（每字段需 locator+value 匹配，published_date 必须 ISO 日期）；
   - `reader.verify_version(ref, purpose="source_export")`：对盘上原件做字节校验（sha256+size 对 sources 行）；
   - `prepare_source_fact_write`（:410）：`patch.update(facts)` 把合并后的 patch 从 `published_date: None` 变为声明值；新断言带 `supersedes_assertion_id=<旧>`、`decision=verified`、`evidence_basis=source-facts`；旧断言记录原样保留（append-only）；
   - `write_source_fact_projection`（:454）：同一事务内 INSERT 断言 + `UPDATE documents SET published_date=?`；
   - 此后 `source_fact_projection` 读到的是新断言 → 投影声明值 → scanner effective 判定（`_declaration_matches(new_raw, value)` 或声明缺省）放行 → resolve 走正常复用分支。
3. `record_source_facts` 的 docstring "Explicit unknowns survive later corrections" 指**其他字段**修正不连带清 published_date；显式给出非 None 的 `published_date` fact 正是该机制设计内的覆盖路径（test_prior_known_publication_date_still_wins 同理反证）。

### 执行证据

- 前置（只读快照 + 独立预校验）：4 行 `published_date=NULL`、各行恰 1 条 2026-11-08T06:09 断言（patch `published_date: null, filing_date: null`）；对每行盘上原件独立重哈希（sha256+size 全对上 sources 行）并核对 sidecar meta.json `filing_date` 声明后才发请求。注意 mdb-* 是 documents.title（团队速记），document_id 实为 sha256 URN。
- 修正（2026-11-15T17:08Z，CLI source-facts，全部 `status: recorded`）：

| title | 旧断言 | 新断言（supersedes） | published_date 前→后 |
|---|---|---|---|
| mdb-20220131 | sa-708eeb5419a342ecb23e3761a55adabd | sa-2dadd762f04f4acc864113f41095e650 | NULL → 2022-03-18 |
| mdb-20230131 | sa-6dcefacab568426fb6600b244a2a6be6 | sa-17a828f4ed5b4f42a26ccbb8ad79f035 | NULL → 2023-03-17 |
| mdb-20240131 | sa-5aa65c9a4d134f4f9910b9691c3e95f3 | sa-354fe846b8c84c6982c33b0fd81446ab | NULL → 2024-03-15 |
| mdb-20260131 | sa-30c42c679b9549928f1c224e6cc9824d | sa-a04a90d3f7e9461d8a0c225a9b5af42d | NULL → 2026-03-11 |

- 溯源完整性：每条新断言 evidence 的 published_date 字段带 `locator=dayu-portfolio-sidecar:MDB/filings/<组>/meta.json#filing_date`、`extraction_method=sidecar-declaration-repair/1`、`content_sha256`、`byte_size`、`observed_at`、`repair_pass=ff1-catalog-repair-20261115/facts-correction`、`authorized_by=user-approval-2026-11-15`。
- 本 pass 未追加 catalog_repairs.jsonl（该 journal 属 B2 定向登记自愈；facts 修正的审计落在 source_metadata_assertions 表）。现存唯一一条 16:47:05Z 事件是当日 16:47 ensure job 失败尝试时的 B2 自愈，先于本 pass。
- resolve 探针（--company-query "MONGODB, INC." --market US --annual_report --form-type 10-K --as-of 2025-07-18）：
  - 前：FY2022/2023/2024 均 `ambiguous / unique_match_published_date_unknown`（unknown_date_match_count=1，对应行 published_date_unknown）；
  - 后：三者均 `reused_equivalent / one_existing_source_satisfies_semantic_request`，match published_date 正确，bundle_status=available。

### FY2026 遗留（超范围，非本 pass 失败）

- mdb-20260131 行的 pin 已清（2026-03-11 已回填），但 resolve FY2026 仍 `blocked: fiscal_period_unresolved`。在盘上原件独立复现（dayu_fiscal_metadata）：primary 内含两个 DEI 日期观测，`ixt:date-month-day-year`（文本 `1/31/2026`）**不在** `_inline_date` 的闭集变换表（仅收录 monthname-en 三个 TR4 变换），`complete_sec_primary` 要求全部观测归一 → 抛 "SEC primary inline date cannot be normalized"。即重审 F-R6 的独立预存问题（代码缺口，非数据缺口），需另行 lane 处理。
