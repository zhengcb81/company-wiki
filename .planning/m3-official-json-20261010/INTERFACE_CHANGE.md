# M3-JSON 接口变更与 MAIN 共享接线包

Lane：M3-JSON。工作树 `C:/Users/郑曾波/.codex/worktrees/m3-official-json-20261010/company-wiki`，branch `codex/m3-official-json-20261010`，base=3c791e3c2a16c12627cc25d0bd8681cc9458e48b。

## 1 新公开接口（本线已实现并测试）

### 1.1 official-source-import-request/2（public CLI `--operation import`）

- 请求字段（严格，unknown 拒绝）：`schema_version="official-source-import-request/2"`、`request_id`、`max_bytes`(1..128MiB)、`content_sha256`、`mime_type="application/json"`、`document_kind`（SOURCE_FACT_KINDS，缺省 `other`）、`source_subject`、`capture_receipt`（沿用 /1 的 receipt 校验）、可选 `expected_content_sha256`。
- `source_subject`：`kind ∈ {single_issuer, multi_issuer_event, unattributed}`；`multi_issuer_event` 必带 `event_namespace/event_id`；`issuer_refs[]` 仅含身份字段（provider_company_id / provider_activity_company_id / stock_code / company_name / market / security_id / canonical_name），是“原页关联主体”不是 owner；`attribution_status ∈ {none,partial,full,unknown}`；unknown 字段拒绝。
- 结果 `official-source-import-result/2`：`status ∈ {imported_new, deduplicated}`、`source_ref`(2.0)、`source_subject`、`layout {layout_id, parse_status ∈ {parsed, unsupported_layout}, layout_fingerprint?}`。
- 语义：合法 JSON 一律入库为共享 raw（`companies/_shared/raw/<kind>/<sha>.json`，由存储层决定）；语法/编码错误与 error envelope 保留 staging capture + journal failed，不入库；`/1` 请求路径完全不变（TXT/FMP 单 content JSON 走旧单 issuer 路径）。

### 1.2 official-json-layout/1 声明式布局（`official_json_layout.py`）

- 注册布局：`official-paged-qa/1.0.0`（SSE 三流 envelope success/message/code/datas；collection `/datas/0/records`；分页 current/size/pages/total；记录 ID `id`；issuer 字段 activityCompanyId/a|qactivityCompanyId、companyId、stockCode、companyName/companyShortName/shortName/guestCompanyName；文本 content/questionContent、precollect question/answer；译文 contentEn/questionContentEn 单列；时间 crtTime/updTime/auditTime/questionDate/questionUpdDate；状态 isAnswered/questionType/questionId/collectType；致辞 questionType=3）与 `official-flat-list/1.0.0`（第二声明布局，未见夹具验证通用性）。
- `unsupported_json_layout`/`layout_pointer_not_found` typed 拒绝；`response_is_error`（status≥400 或 error 字段非空）不是业务证据。
- 记录分类 `classify_record`：precollected_question_with_answer / unanswered_question / answered_qa / closing_remark / event_remark_unattributed / other_statement——只按声明状态字段，不按文本、公司、页号。

### 1.3 source-projection-ref/1 投影（`official_json_projection.py`）

- `official-json-projection-request/1`（CLI `--operation project`）：`parent_source_refs[]`(SourceRef2.0)、`layout_id`、`issuer`、`as_of_date`、可选 `persist`。
- 投影 identity：parent refs + adapter(parser/structure/layout+fingerprint) + issuer + as_of + records + coverage 的 canonical SHA；`projection_id=urn:company-wiki:source-projection:sha256:<sha>`；同页多 issuer 各自投影共享同一 parent ref，不触发 owner 冲突、不复制 raw。
- 记录字段绑定：pointer + token range(含引号/括号) + encoded body range(不含引号) + token SHA + decoded SHA + 字符数 + `cwp-json-pointer/1|p=…|b=…|d=…|x=json-string-decode/1` locator；角色 investor_question / management_answer / company_statement(closing_remark) / company_official_answer(precollect，speaker 未知) / event_remark；译文角色带 `_provider_translation` 后缀。
- 时间：原字段原值保留；`answer_first_publication_known=false`（无独立答复发布字段时不冒充已知）；`record_created_date>crtTime` 按 as-of 排除并计数；`as_of_eligibility ∈ {eligible, after_as_of, unknown}`。
- coverage 分列：pages[]（envelope/分页/记录数）、`page_envelope_complete`、`pagination_complete`（页码唯一连续+页数+总数一致才 true）、`issuer_records_selected/other_issuer_records/unattributed_records/as_of_excluded_records/total_records`。
- issuer proof：每个提供的身份字段必须与记录观测字段一致（合取），至少一个匹配；`issuer_not_on_page` 拒绝。
- 投影存储：`catalog_dir/projections/<sha>.json`（幂等、store-owned、无 DB）。

### 1.4 read / replay / export（CLI）

- `read`（`official-source-read-request/1`）：stdout 严格等于 parent 原始 bytes（open_version purpose=source_export）。
- `replay`（`official-json-replay-request/1`，投影 payload 或 `projection_id`）：按记录 parser version 重解析 + pointer/token/body/双 SHA/locator/角色全验后输出文本；篡改 pointer/母页 bytes 具名拒绝。
- `export`（`source-projection-export-request/1`）：`source-projection-export/1` bundle = source_refs + projection + EvidenceSpan v1（coordinates=loc:v1 paragraph_index 词法序，structured_value.source_locator=JSON locator，parser=cwp_official_json/1.0.0）+ counts + bundle_sha256/export_id。旧 `source_export` v1/v2 合同未动。

### 1.5 合同层（source_contract）

- `source_manifest.py` 新增 `SourceSubjectManifest` 2.0.0：允许 unknown/partial attribution 的空 issuer 集合与 provider/event 身份；strict 字段；`SourceManifest` 1.0.0 严格读不变（空 entity_ids 仍拒绝）。
- `evidence_span.py`/`source_export.py`/`compatibility.py` 未改语义；compatibility policy JSON 未改（新合同未注册进 packaged policy——见 §3 MAIN 决策点）。

## 2 MAIN 共享接线包（本线不改 automation/*，全部待 MAIN）

按 INTERFACES.md，以下文件 MAIN 保留；本线提供最小 patch 与测试命令：

1. `automation/narrative_formats.py::source_class_for`：JSON+document_kind=共享事件页 仍返回 "transcript"。MAIN 新增 `official_json` class（按 mime=application/json + provenance `official_json_layout`/subject 判定，或按 document_kind 白名单），filing/transcript 旧类不变。
2. `automation/narrative_select.py`/`narrative_replay.py`：`official_json` class 走 projection 输入（source_ref+projection_id），不进入 transcript line binding；replay 调 `replay_projection`（本模块已公开）验证 span。
3. `automation/models.py`/`NarrativeBatchRequest`：批内去重键从 document_id 扩为 source+projection identity（同页两 issuer 两个 generation 项，不互相覆盖）——建议 event/select/bundle 新 3.0 合同显式带 projection_ref；2.0 原语义不动。
4. generation 绑定：parser/adapter（cwp_official_json/1.0.0 composition：structure 1.0.0 + layout id/version/fingerprint）、projection id/as-of/filter、selector/profile；旧结果只按其记录版本 replay。
5. `source_catalog/cli.py` 总入口：如需把 official JSON ops 挂到统一入口，直接转发到 `company_wiki.source_catalog.official_source_cli.main`（本线未改 cli.py）。

**MAIN 测试命令（合并后重跑）**：

```
python -X utf8 -B -m pytest -q tests/unit/test_m3_official_json_parser.py tests/contract/test_m3_official_json_contract.py tests/contract/test_m3_official_json_frozen_pages.py tests/integration/test_m3_official_json_projection.py
python -X utf8 -B -m pytest -q tests/contract/test_official_capture_recovery.py tests/integration/test_official_source_flow.py
```

预期：107+ 全绿；旧 transcript/FMP/manifest1/export2.0 兼容项保持。

## 3 未定/留给 MAIN 的接口决策

- `official_json` 是否进 packaged compatibility policy（新合同名注册需动 schemas/source_contract_compatibility.v1.json + `SOURCE_CONTRACT_NAMES`，是 MAIN 级版本发布动作）。
- AUTO generation 新 3.0 合同字段定稿（本包只给约束：source+projection 去重、绑定 parser/projection/as-of）。
- server companyfilter 实测、provider 时区语义、answer 首发时刻、历史 revision 接口（见 HANDOFF remaining；不猜参数发公网）。

## 4 受改文件清单（git diff 摘要）

- 新增：`src/company_wiki/source_catalog/official_json_structure.py`、`official_json_layout.py`、`official_json_subject.py`、`official_json_import.py`、`official_json_projection.py`；`tests/unit/test_m3_official_json_parser.py`、`tests/contract/test_m3_official_json_contract.py`、`tests/contract/test_m3_official_json_frozen_pages.py`、`tests/integration/test_m3_official_json_projection.py`。
- 修改：`src/company_wiki/source_catalog/official_source_flow.py`（/2 staging/recovery 分发、_journal 容缺 source、completed 记录带 /2 附件、_load_retained 接受 /2）、`official_source_cli.py`（import /2 分发 + project/read/replay/export 操作）、`canonical_writer.py`（`_SharedOriginal`/`_SharedImportIntent`/`import_shared_original_staged`/共享 `_destination`/provenance 无 owner 分支）、`src/company_wiki/source_contract/source_manifest.py`（SourceSubjectManifest 2.0.0）。
