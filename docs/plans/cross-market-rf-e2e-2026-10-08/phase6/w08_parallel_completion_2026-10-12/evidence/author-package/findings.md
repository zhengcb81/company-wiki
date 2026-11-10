# W08-CWP-G2-REPLAY findings

## F1 — 卡上「18 既有边界 FAIL」的计数不成立（环境伪影，已证伪）

- 现象：首次在工区跑 `tests/integration/test_narrative_batch_cli_e2e.py`
  `test_narrative_generation_reuse.py` `test_narrative_runtime_e2e.py`，
  得到 26 failed / 13 errors，全部约 5s 内失败。
- 真实原因：会话沙箱只把 {session workspace, /tmp, tmpdir()} 作为可写根；
  当时 workspace root 是 `company-wiki`，本工区是其**兄弟目录**，
  因此工区整体只读。失败点是 `tempfile.TemporaryDirectory`/`mkdir` 的
  `PermissionError: [WinError 5]`，不是 W04 语义缺陷。
- 证据：ACL 诊断脚本对工区逐级返回 `verdict=NOT_THIS_CLASS`
  （每级 `writeDac=true/writeOwner=true`，owner 为当前用户，无外部包条目），
  即不是文件权限条目问题；同时 `New-Item <工区>\.tmp-probe` 被拒，
  而 `<workspace>\.tmp-probe` 成功。
- 处置：会话文件策略转为 `danger-full-access` 后可写。**重跑基线**得
  真实结果：`2 failed, 37 passed, 2 skipped`（331s）。卡上 18 的数字
  应视为该伪影的产物，不应写成期望，也不应算 W04 缺陷。
- 归属层：harness/环境层，非 company-wiki 产品层。

## F2 — 真实 W04 基线失败（只记录不修）

### F2a — narrative 集成基线（本包相关）

1. `tests/integration/test_narrative_batch_cli_e2e.py::
   test_cli_infers_sparse_languages_from_verified_pdf_and_transcript_bytes`
2. `tests/integration/test_narrative_runtime_e2e.py::
   test_runtime_e2e_read_identity_fails_automatically_and_transcript_needs_no_receipt`

基线实测：`2 failed, 37 passed, 2 skipped`（331s）。

### F2b — selector 单元基线（与本包无关，已证）

`tests/unit/test_narrative_evidence.py` 5 项失败：

1. `test_product_name_context_and_permit_milestone_survive_prospectus_budget`
2. `test_pdf_candidate_budget_reserves_first_pass_coverage_across_pages`
3. `test_visual_context_groups_are_atomic_and_never_exceed_the_span_budget`
4. `test_numbered_project_rationale_heading_survives_a_tight_budget`
5. `test_split_project_rationale_heading_keeps_its_short_continuation`

证明为本包之前既有：把 `tools/narrative_g2_replay/` 整个移开后
重跑仍为 `5 failed, 60 passed`。且 `git status --untracked-files=no`
为空 —— 本包**未修改任何已跟踪文件**（纯新增），故不可能是本包引入。

- 归属：ROOT（W04 core / src selector）。
- 本包只写 tools+tests+fixtures，不修 src，不改期望。

## F3 — 已确认的真实公开入口（非记忆，均实跑 --help）

- `python -m company_wiki.automation.narrative_batch_cli`
  （--project-root/--catalog-config/--automation-db/--work-dir/--request）
- `python -m company_wiki.source_catalog.narrative_transport_cli`
  （--config/--operation read|reference/--limit/--offset/--span-id/--locator/--query）
- `scripts/narrative_batch_configured.py` 是 config 组合层，非本包必须。
- RF 侧：`scripts/company_wiki_narrative_reader.py`（pathless，子进程 reader）
  与 `scripts/narrative_source_preparation.py`（stdin/stdout 契约）。

## F4 — 类型词汇表以真实代码为准（非卡上中文名）

卡上写「增发/可转债」，真实 scanner/routing 词表是：

- `equity_offering_prospectus`（标题含「向特定对象发行股票…募集说明书」）
- `convertible_bond_prospectus`（标题含「可转换公司债券…募集说明书」）
- `ir_policy` 只在 `narrative_routing._EMPTY_SKIP_KINDS` 里可空跳过；
  scanner 的 sidecar kind 是 `investor_relations`。
- 结论：fixture 的 sidecar kind 与**文件名**都必须按真实词表取名，
  否则 scanner 归为 `other`，路由拿不到 skip 政策。

## F5 — skip 需要一个「完整表格扫描」才成立（已实测，非缺陷）

- 现象：`ir_policy` 用 `parse_pdf(_bytes)` 默认扫描时，
  `deferred_table_pages=(1,2)` → `coverage_complete=False`
  → `narrative_finalize._status` 在 L119 先返回 `needs_review`（0 span），
  永远走不到 L122-123 的 `skipped_no_narrative`。
- 真实批次路径本来就做二次完整表格扫描
  （`narrative_select._parse_pdf` 在 `deferred_table_pages` 非空时
  用 `full_table_scan=True` 重解析）。照此路径后实测
  `deferred=() → coverage_complete=True → status='skipped_no_narrative'`。
- 处置：本包按真实批次路径做同样的二次扫描，不把默认单次解析的
  `needs_review` 写进期望。这不是产品缺陷，而是真实前置条件。

## F6 — 真实选择器对全矩阵的实测结论（作为固定期望依据）

按真实批次路径（含二次表格扫描）实测：

| case | status | spans | 必需业务句命中 |
|---|---|---|---|
| annual-report | selected | 1 | True |
| half-year-report | selected | 1 | True |
| quarterly-report | selected | 1 | True |
| prospectus | selected | 2 | True |
| placement | selected | 1 | - |
| convertible-bond | selected | 1 | - |
| ir-policy | skipped_no_narrative | 0 | - |
| call-txt-zh | selected | 1 | True |
| call-txt-en | selected | 2 | True |

即卡上 §5 的期望（业务内容可定位并进入 summary；纯套话 skip；
招股/融资 kind 保持；TXT 语言/SHA 不变）在本固定基线上全部可达。

