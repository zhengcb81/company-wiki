# PDF Extract v3 Adapter v1

## 目的

`company_wiki.parser_adapters.adapt_pdf_extract_v3` 是一个纯进程内兼容层，把已经执行完成的 legacy `extract_pdf_text_v3` aggregate mapping 转为 canonical `ParserResult`。它不导入或调用 legacy parser，不读取 PDF、不下载、不调用 LLM，也不写 raw、extract、Wiki、review、state 或 StockWiki。

## 输入合同

调用者必须提供：

- 一个 `immutable_status=verified`、`mime_type=application/pdf` 的 canonical `SourceManifest`；
- legacy v3 的精确八字段 mapping：`text`、`pages_read`、`total_pages`、`total_chars`、`quality_score`、`is_scanned`、`scan_confidence`、`error`；
- 显式 semantic `parser_version`。

mapping 不携带 source path、hash 或 source ID；adapter 只使用 manifest 的 canonical `source_id`，不从文件名、derived extract 或 entity 名称推断身份。缺字段、多字段、类型/计数不一致、非 NFC、非 LF、错误、扫描版或空输出均 fail closed。

## Locator 语义

v3 aggregate output 已把所有非空页面拼成单个文本，并丢失原 physical page/table identity。因此本 adapter 只按空行切分 normalized document：

- `paragraph_index` 是 0-based global paragraph index；
- `char_start`/`char_end` 是原 aggregate `text` 的全局 `[start, end)`；
- `page_number`、`table_index`、`row_index`、`column_index` 必须为 `null`。

adapter 不允许用 block 序号猜测 physical page。`[TABLE N]` 只作为 raw text 保留，并标记 `table_structure_ambiguous`；它不是 canonical table locator。

## 质量映射

- `pages_read < total_pages`：`partial + truncated`；
- `quality_score < 0.30`：`partial + parser_warning`；
- paragraph 含 `[TABLE N]`：该 paragraph 为 `partial + table_structure_ambiguous`；
- 无 flags：`parsed`。

`is_scanned=true` 不会伪造 parser output；调用者必须使用另一个经过审计、带明确版本和质量信息的 OCR parser。

## 组合方式

```python
from company_wiki.ingest import IngestService
from company_wiki.parser_adapters import adapt_pdf_extract_v3

parser_results = adapt_pdf_extract_v3(
    manifest=manifest,
    extraction=legacy_result,
    parser_version="3.0.0",
)
bundle = IngestService(root=root).ingest(
    manifest=manifest,
    parser_results=parser_results,
)
```

`IngestService` 在发布 bundle 前重新校验 manifest 指向的 raw path、size 和 SHA-256。相同输入重放字节一致；raw 漂移、source mismatch 或 locator output 冲突继续 fail closed。
