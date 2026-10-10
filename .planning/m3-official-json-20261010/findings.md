# M3-JSON findings

历史 seed：接管 W02（原内置 agent terminal errored，源码无更改）。2026-10-10 外部 harness 接管。
Seed 原文（保留）：当前官方 JSON 走 transcript extractor 单 content；多 issuer raw 被旧单 entity import 拒绝/误表征。新 source subject 及 projection 显式版本，不伪装 transcript。冻结合同沿用 expert W02；MAIN 排他 runtime。

## 必读依据核验（2026-10-10）

- DATA_CONTRACT.md SHA `2d80afeeac0946f91e18dccc6008eab734dcb1d727aac6f2dbe2870e7b4f08b3`、JSON_EVIDENCE_INDEX.json SHA `4969a5239e15b71f2e8d83e3107dd7a9f80ab78b9673b710a2158906b35285fc`，与卡一致。完整阅读。
- worktree HEAD=3c791e3c2a16c12627cc25d0bd8681cc9458e48b（=base），branch codex/m3-official-json-20261010，初始只有 untracked W02 计划目录。
- sealed run `C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/m3-20261009T184946-cn-688012/execution/sources` 有 135 个文件（86 成功页 + 3 个 500 error control + qa-chunks-3.raw + 其他）。只读。

## 现有代码事实（worktree 实读，非索引行号）

### 拒绝链三层共因（与 DATA_CONTRACT §2 一致）

1. `official_source_flow.py::_validate_bytes`（~150）：`text/plain|application/json` 一律 `transcript_material.extract_transcript_material`；多记录分页 JSON 抛 `invalid_text_original`（经 transcript_json_extract `_record_content` 的 "expected exactly one transcript record"）。
2. `_metadata`（~92）：source metadata 必填 `entity/document_kind/title/publisher/source_url`，单一 entity 文本，kind 必须 ∈ SOURCE_FACT_KINDS；`import_original_staged` 用 `SourceRequest(entity=...)` 生成 `_destination` → `companies/{entity}/raw/{subdir}/`，单 issuer 存储意图。
3. AUTO `narrative_formats.source_class_for`：TXT/JSON → transcript（MAIN 保留文件，本线只交接线包）。

### 关键既有接口（不能悄悄改语义）

- `SourceRef` 2.0（source_reader.py:73）：document_id/source_id/content_sha256/byte_size/mime_type；source_id=`urn:company-wiki:source:sha256:{sha}`，document_id 同构 document: 前缀。
- `SourceVersionReader.open_version`（620）：purpose ∈ {preview, filing_reuse, source_export, narrative_derivation}；验 catalog + root policy + 实际 bytes。`verify_version` 流式不保 bytes。
- `SourceRequest`（resolver.py:510）：entity 必填文本 → `_destination` 与 resolver `_entity_matches` 的查询资格。
- `CanonicalSourceWriter.import_original_staged`（315）：staged bytes → `_commit_staged`（CatalogOperationLock + SHA 去重 `_existing_original` + `_destination` + provenance sidecar + register_catalog_sources）。`_destination`（437）＝ company_root/{safe_entity}/raw/{subdir}/{sha}{ext}。
- `official_source_flow._persist_capture/_import_retained/recover_official_source`：staging/journal/AcquisitionJournal/`official-source-retained-capture/1`、`.result.json` 幂等重放已存在，可复用。
- `official_source_cli.main`：operations = import/discover/capture/recover；import 需 `--config --input-file`（绝对路径）+ `--request` JSON ≤64KiB（重复键/NaN 拒绝）。project/read/export 等 operation 不存在。
- `SourceManifest` 1.0.0（source_manifest.py）：entity_ids 至少一个（`_normalize_entity_ids` 拒绝空）；strict 字段。manifest 2.0 需允许 unknown/partial attribution。
- `EvidenceSpan` 1.0.0（evidence_span.py）：EvidenceCoordinates loc:v1（page/paragraph/table/row/column/chars），locator 由 coordinates 决定；`structured_value` 可携带任意 JSON（source_locator 等）；span_id/output_sha256 绑定。**注意**：`_is_groundable_text_shape`（source_export_v2）只接受 text/plain+char 坐标；JSON 页 evidence span 不能进 v2 export 的 grounding 路径 → 需要 export 2.1/独立 projection export（显式版本，不偷偷改 2.0）。
- `SourceExportBundleV2` 2.0.0（source_export_v2.py）：build 需要 SourceVersionReader + refs + spans；`_MANIFEST_FIELDS` 精确集合（compat 层 fail-closed）。
- `compatibility.py`：SOURCE_CONTRACT_NAMES=(evidence_span, source_export, source_manifest)，packaged policy JSON 校验 current_version 必须匹配 runtime 常量。加新合同要动 schemas/source_contract_compatibility.v1.json + 常量（schemas/ 在写集内）。
- `transcript_json_extract.py`：单 content 合同（`transcript-original-json/1.0.0` 侧），历史算法不改。
- `normalized_meta.py` 只是 NormalizedFilingMetadata 的 hash 助手（WU-401）。
- capture 侧 GET：`capture_official_source` 固定 `client.stream("GET", source_url)`。捕获侧 POST 支持属 capture request /2 —— 本卡 import /2 复用已捕获原页、0 公网（DATA_CONTRACT §5），不改 capture。

### 封存反例锚点（JSON_EVIDENCE_INDEX）

- 4 代表页：latest-01（sha 416542b0…,5119B,page1/65,total195）、latest-18（fc1c2a8e…,7316B,page18/65, 2508385 中微答复发问颠倒 answer[5037,5557) question[6703,6766)）、questions-01（509bcbcd…,5925B,page1/11）、precollect-10（784217fb…,3871B,page10/10, ID36395 Q+A companyId=145565 stockCode=688012）。
- 旧错误定位反例：latest-01 `/datas/0/records/2` = 2508409 清溢（activityCompanyId 57808）；2508385 在 latest-18 同 pointer。测试必须固定此错误页不能通过冒充目标公司。
- 3 个 500 error payload（138/138/141B）：`status=500,error="Internal Server Error"`。
- 24 条目标记录 / 257 总记录 / 86 页 668,749 bytes。

## 布局事实（SSE paged-qa envelope）

- 页 envelope：`{"success":true,"code":200,"datas":[{"records":[…],"current":1,"size":3,"pages":65,"total":195}]}`（`/datas/0/records`）。分页字段在 datas[0] 内（current/size/pages/total）。
- 记录身份/状态字段：activityId、(a|q)activityCompanyId、companyId、stockCode、companyName、guestCompanyName、questionId、questionType、isAnswered、crtTime、updTime、auditTime、questionDate、questionUpdDate、collectType、content/questionContent/question/answer、contentEn/questionContentEn（provider 译文）。

## 待办探查

- tests/ 现有 official/transcript 测试夹具与 TEMP catalog 构造方式（tests/unit、tests/contract、tests/integration 分层）。
- store.record_source_facts / observe_metadata 元数据边界（多 issuer 关联主体怎么进 catalog 元数据）。
- automation/narrative_formats.source_class_for 只读确认（MAIN 接线包依据）。
