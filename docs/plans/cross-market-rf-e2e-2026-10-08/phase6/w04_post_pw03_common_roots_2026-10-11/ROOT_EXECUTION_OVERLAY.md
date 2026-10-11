# W04 ROOT 实施接口补充

本文件是 ROOT 对已封存专家包的实施补充；不改 handoff 的21个原文件及其 SHA。实施者同时读取本文件与自己的 WP 卡。所有新测试仍进入既有测试入口，不新增人工签收或小节点门禁。

## 负责人和路径

- WP01 的新增测试改为 `tests/unit/test_w04_source_transport.py`，WP02 改为 `tests/unit/test_w04_narrative_semantics.py`，因为 CWP 正常 CI 执行 `tests/unit`。
- WP01 同时独占 `src/company_wiki/automation/narrative_evidence_view.py` 的 v3 分支；保留其旧 /1、/2 行为。
- WP05 可新增 `skills/revenue-forecast-audit/scripts/audit_blob_store.py`，只实现所需的不可变 CAS、private workcopy、现有 scope 空间计量；无第二任务库或 registry。WP05 不改 `audit_run.py`。
- ROOT WP07 的 `audit_run.py` 范围明确为 opt-in freeze/capture/CAS/private-copy/deadline/cleanup 接线。保留默认 legacy API、错误优先级、旧59测试；原“不改 W11”只禁止 leaf 无授权跨 owner 修改，不禁止 ROOT 实施已计划的 opt-in 边界。
- RF 在干净隔离目录施工，不使用 canonical 中 assurance/output WIP：`C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/revenue-forecast`，base `47f497ad9dee9dc47f66fca37016e9ba6b6b6f33`。
- FF 隔离目录 `C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/filing-fetch` 已 clean ff 至 `e1e3ad8679e21264258e48006786fbf01a6991bd`。canonical 密钥不读、复制或提交。
- Audit 施工目录为已交付且停止写入的 P7 worktree，base `40b38103f4b96860617e9bae98ec5b4ea8ee08d5`。新施工分支由 ROOT 从此创建。

## compact 运输精确接口（WP01 producer，WP03 consumer）

SourceRef 仍精确 `2.0`。CWP 现有 `narrative-ref/1` raw 和 `narrative-ref/2` projected、全部旧 request/read/receipt 字符串及字段保持。RF 过去只接 /1，不能宣称已支持旧 /2。新实现是显式 /3 分支，不能把旧常量直接替换。

新 subject_ref 四键：`schema_version='narrative-subject-ref/1'`, `kind='official_json'`, `item_key`, `subject_sha256`。`item_key` 必须等于现有 `urn:company-wiki:source-projection:sha256:` + 原 projection SHA。

新 narrative_ref 六键：`schema_version='narrative-ref/3'`, `artifact_version_id`, `artifact_sha256`, `byte_size`, `generation_sha256`, `subject_ref`。

reference 请求三键：`schema_version='narrative-reference-request/3'`, `subject_ref`, `generation_sha256`。reference stdout 是新 compact ref；stderr 三键 `schema_version='narrative-read-receipt/3'`, `status='metadata_only'`, `narrative_ref`。

read 请求四键：`schema_version='narrative-read-request/3'`, `narrative_ref`, `as_of_date`, `expected_issuer`。issuer 约束沿既有 EXPECTED_ISSUER_FIELDS/类型；null 仍允许。read stdout 保留真实已 pin `narrative-bundle/3.0` 原字节，不重生成旧 bundle 或改 generation。

read 成功 stderr 十一键：`schema_version='narrative-read-receipt/3'`, `status='ok'`, `narrative_ref`, `as_of_date`, `observed_at`, `locator_count`, `parent_count`, `lineage_sha256`, `selection_status`, `quality_status`, `replay_status='verified'`。`lineage_sha256=SHA256(canonical_json(bundle.subject.to_dict()).encode('utf-8'))`，canonical_json 使用现有 CWP helper；`parent_count=len(bundle.subject.parent_source_refs)`。这不是 raw SHA 或 projection SHA 的别名。

所有 /3 请求、ref stdout、各 stderr 均含换行后不超过16384B；完整 bundle/read body 仍保持现有限额1310720B。不要提高 cap、截断 lineage 或只保留首父来源。

新 evidence view 为 `narrative-evidence-view/3`，除 schema 和 compact ref 外保留现有 projected view /2 的完整字段、父refs、pointers、items、分页。新 evidence receipt 为 `narrative-evidence-read-receipt/3`，保留当前 projected evidence receipt /2 的九个字段（schema/status/view_sha256/byte_size/narrative_ref/as_of_date/observed_at/replay_status/locator_count），再增加 `parent_count` 和 `lineage_sha256`。read/receipt 与 body 的 full subject/parents 必须一致。ref3 返回不能虚构 source_ref 锚。

resolver 复用现有 projection catalog/load/open_verified_projection 和 artifact store。可给 reader 新增 optional compact-ref resolver，返回完整 VerifiedProjectionView；同一 read 中 exact parent 校验一次，然后用这份 buffer 回放，避免 load 完再次重复 reopen。旧 projection_loader(NarrativeSubject) 默认兼容。没有额外来源 registry/身份证明链。

## 其他公共边界

- metadata 老四键和 optional declared_language 保持类型校验。official_json 的真实 source_class/document_kind/language='unknown' 走显式投影分支，不能用 raw-only gate 强拒。
- 新 snapshot 取实际 input/result schema；当前 native run_forecast 保留3.7/3.8/3.9，沿既有 engine/schema policy。历史 header 元数据与内部不同仅诊断，不重写旧 snapshot/registry，也不增加旧输入升级门。
- FF request_diagnostic sibling 沿专家定义四 reason/path；旧六键 filing-upstream-cause/1 保持。RF WP03 接收 optional sibling，audit WP05只诊断，未知字段/未观测 enforcement 不猜。
- purpose 名称可观察；effective prompt/model/endpoint/options 相同允许原安全复用。当前 config 没 generation_policy，不把规划 disabled 当已有配置；新增策略由 ROOT 明确配置，测试只用 tmp。实际 thinking/effort/output 变化必须失效；null/omitted 的无效差异由统一 canonical seam 修复，历史 artifact/账不改。
- audit expected_digests 在真正保留的 streamed bytes 边界比较，mismatch 不启动 child。CAS 与 mutable copy 分开，legacy 默认不变。仅实现第一版 immutable CAS/private copy，不建设 Windows immutable-CLI lease。

## 验收和交接

ROOT 集中验接口/共享集成后再一次正常发布与定点安装。每包只保存自身 RED→GREEN、diff/SHA/实际未执行项；不重复已收48/3206/96/真实9收费。真实摘要 G2 与新公司执行/四审 G4/G5 分阶段合理有界，母账不重置，原 sealed partial 不补签。
