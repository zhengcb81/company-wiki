# Canonical IngestService v1

## 目的

`company_wiki.ingest.IngestService` 是 company-wiki 唯一公开的 canonical source ingest 边界。它把已经由 create-once collector 保存并由 `SourceManifest` 标识的 immutable raw，与 parser 输出绑定为 `EvidenceSpan`，最终返回只读 `SourceExportBundle`。

该服务不下载资料、不创建或改写 raw、不写数据库/Wiki/StockWiki、不调用 LLM，也不生成 claim、评级、估值、仓位、研究结论或 accepted/rejected 投资状态。

## 分层合同

1. Collector 首次创建 immutable raw、source manifest 和 provenance。
2. Parser 读取 raw，返回一个或多个 `ParserResult`；每个结果必须带同一 canonical `source_id`、结构化坐标、原文/结构化值、parser/version、parse status 与 extraction-quality flags。
3. `IngestService` 校验 parser result 的 source identity，并通过 `EvidenceSpan.create()` 生成稳定 locator、output hash 和 span ID。
4. `SourceExportBundle.build()` 重新校验 raw path、size 与 SHA-256，执行确定性排序、去重、locator 冲突检测和可选 add-only replay。

`SourceManifest`、`EvidenceSpan` 和 `SourceExportBundle` 的序列化字段与版本仍分别受各自 v1 合同约束；`ParserResult` 是进程内的不可变适配值，不建立第二套持久化 schema。

## 最小调用

```python
from pathlib import Path

from company_wiki.ingest import IngestService, ParserResult
from company_wiki.source_contract import (
    EvidenceCoordinates,
    ParseStatus,
    SourceManifest,
)

root = Path(".")
manifest = SourceManifest.from_dict(manifest_payload)
parser_result = ParserResult(
    source_id=manifest.source_id,
    coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
    raw_text="公告正文……",
    structured_value={"document_type": "announcement"},
    parser_name="pdf_parser",
    parser_version="1.0.0",
    parse_status=ParseStatus.PARSED,
    quality_flags=(),
)

bundle = IngestService(root=root).ingest(
    manifest=manifest,
    parser_results=(parser_result,),
)
```

增量重放时传入上一版 `SourceExportBundle`：

```python
next_bundle = IngestService(root=root).ingest(
    manifest=manifest,
    parser_results=(parser_result,),
    base=previous_bundle,
)
```

相同 manifest 与 parser result 的重复执行会产生字节一致的 canonical bundle。相同 source/locator 出现不同 parser output 时 fail closed。

## Announcement adapter

官方公告 collector 已返回 `AnnouncementCollectionReceipt` 时，使用：

```python
bundle = IngestService(root=root).ingest_announcement(
    receipt=receipt,
    parser_results=(parser_result,),
    base=previous_bundle,
)
```

adapter 会重新校验 receipt 的 collection ID、official URL、source type 和 manifest metadata，再进入通用 ingest 路径；它不会重新下载公告或读取/改写 provenance。

## 失败语义

- raw 缺失、路径漂移、size/hash 改变：`SourceManifestMismatchError`。
- parser result 的 `source_id` 与当前 manifest 不同：`IngestSourceMismatchError`。
- 同一 ID 内容不一致或同一 source/locator 输出冲突：`SourceExportConflictError`。
- receipt collection ID 或公告元数据无效：`AnnouncementCollectionError`。
- 非 `ParserResult`、`SourceManifest`、`SourceExportBundle` 等类型：`TypeError`。

所有成功与失败路径均为只读；错误不会降级为 legacy writer、SQLite state 或研究语义输出。

## Legacy compatibility

旧版 claim/`KnowledgePatch` 编译器已隔离为 `company_wiki.legacy_research_ingest.LegacyResearchIngestService`，仅用于历史兼容测试。它不是 canonical ingest，不得接入新 collector、parser、scheduler 或 production pipeline。
