"""Format adapters that create traceable Markdown without modifying source files."""

from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import subprocess
import unicodedata
from typing import Any, Callable, Iterable

import yaml

from company_wiki.canonical_ingest import IngestService, ParserResult
from company_wiki.parser_adapters import (
    PAGE_AWARE_PDF_PARSER_NAME,
    PageAwarePDFResult,
    adapt_pdf_pages,
)
from company_wiki.source_contract import (
    EvidenceCoordinates,
    ParseStatus,
    QualityFlag,
    SourceManifest,
)

from .models import CatalogConfig, NORMALIZER_VERSION, ProcessingReport
from .store import CatalogStore, canonical_json


_NORMALIZER_NAME = "source_catalog_normalizer"
_SENTENCE_BREAK_RE = re.compile(r"\n\s*\n+")


def _utc_iso(epoch: float | None = None) -> str:
    """UTC timestamp as a second-precision ISO-8601 string (sortable as text)."""
    import time as _time
    from datetime import datetime, timezone

    if epoch is None:
        epoch = _time.time()
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


@dataclass(frozen=True)
class _Normalized:
    body: str
    parser_results: tuple[ParserResult, ...]
    parser_name: str
    parser_version: str
    status: str
    quality_flags: tuple[str, ...]
    error: str | None = None


def _nfc_lf(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def compute_text_fingerprint(text: str) -> str | None:
    """SHA-256 of normalized text, or None for empty/whitespace-only text.

    Normalization is NFC followed by collapsing every run of whitespace to a
    single space and stripping the ends. Two documents whose extracted text is
    identical after this normalization share a fingerprint regardless of
    byte-level differences (re-encoding, watermarking, line-ending differences),
    which is the basis for semantic (non-exact) duplicate detection. Empty or
    whitespace-only text yields None so unreadable or scanned files are excluded
    from semantic grouping.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    collapsed = " ".join(unicodedata.normalize("NFC", text).split())
    if not collapsed:
        return None
    return hashlib.sha256(collapsed.encode("utf-8")).hexdigest()


def _decode(data: bytes) -> tuple[str, bool]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return _nfc_lf(data.decode(encoding)), encoding not in {
                "utf-8-sig",
                "utf-8",
            }
        except UnicodeDecodeError:
            continue
    return _nfc_lf(data.decode("latin-1", errors="replace")), True


def _paragraphs(text: str) -> list[str]:
    values = [item.strip() for item in _SENTENCE_BREAK_RE.split(_nfc_lf(text))]
    return [item for item in values if item]


def _parser_result(
    *,
    source_id: str,
    raw_text: str,
    parser_name: str,
    parser_version: str,
    page_number: int | None = None,
    paragraph_index: int | None = None,
    table_index: int | None = None,
    structured_value: Any = None,
    flags: Iterable[QualityFlag | str] = (),
) -> ParserResult:
    normalized_flags = tuple(flags)
    return ParserResult(
        source_id=source_id,
        coordinates=EvidenceCoordinates(
            page_number=page_number,
            paragraph_index=paragraph_index,
            table_index=table_index,
        ),
        raw_text=_nfc_lf(raw_text),
        structured_value=structured_value,
        parser_name=parser_name,
        parser_version=parser_version,
        parse_status=ParseStatus.PARTIAL if normalized_flags else ParseStatus.PARSED,
        quality_flags=normalized_flags,
    )


def _text_markdown(
    path: Path, source_id: str, *, parser_name: str, parser_version: str
) -> _Normalized:
    text, repaired = _decode(path.read_bytes())
    values = _paragraphs(text)
    if not values:
        raise ValueError("empty text output")
    flags = (QualityFlag.ENCODING_REPAIRED,) if repaired else ()
    results = tuple(
        _parser_result(
            source_id=source_id,
            raw_text=value,
            paragraph_index=index,
            parser_name=parser_name,
            parser_version=parser_version,
            flags=flags,
        )
        for index, value in enumerate(values)
    )
    parts = []
    for result in results:
        parts.extend(
            (
                f"<!-- locator: {result.coordinates.locator()} -->",
                result.raw_text or "",
                "",
            )
        )
    return _Normalized(
        body="\n".join(parts).rstrip() + "\n",
        parser_results=results,
        parser_name=parser_name,
        parser_version=parser_version,
        status="partial" if flags else "completed",
        quality_flags=tuple(item.value for item in flags),
    )


def _bbox(value: Any) -> tuple[float, float, float, float] | None:
    try:
        coordinates = tuple(float(item) for item in value)
    except (TypeError, ValueError):
        return None
    if len(coordinates) != 4 or not all(math.isfinite(item) for item in coordinates):
        return None
    x0, y0, x1, y1 = coordinates
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def _bbox_intersects(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> bool:
    return (
        left[0] < right[2]
        and left[2] > right[0]
        and left[1] < right[3]
        and left[3] > right[1]
    )


def _pymupdf_page_snapshots(document: Iterable[Any]) -> tuple[dict[str, Any], ...]:
    """Extract strict page snapshots without inventing missing table coordinates."""

    snapshots: list[dict[str, Any]] = []
    for page_number, page in enumerate(document, start=1):
        layout_ambiguous = False
        tables: list[dict[str, Any]] = []
        table_bboxes: list[tuple[float, float, float, float]] = []
        find_tables = getattr(page, "find_tables", None)
        if not callable(find_tables):
            layout_ambiguous = True
        else:
            try:
                found_tables = tuple(getattr(find_tables(), "tables", ()))
            except Exception:
                found_tables = ()
                layout_ambiguous = True
            for table in found_tables:
                try:
                    table_bbox = _bbox(getattr(table, "bbox", None))
                    data = tuple(
                        tuple(value for value in row) for row in table.extract()
                    )
                    rows = int(table.row_count)
                    cols = int(table.col_count)
                    markdown_method = getattr(table, "to_markdown", None)
                    if table_bbox is None or not callable(markdown_method):
                        raise ValueError(
                            "table geometry or Markdown API is unavailable"
                        )
                    markdown = _nfc_lf(str(markdown_method())).strip()
                    if not markdown:
                        raise ValueError("table Markdown is empty")
                    tables.append(
                        {
                            "markdown": markdown,
                            "rows": rows,
                            "cols": cols,
                            "data": data,
                        }
                    )
                    table_bboxes.append(table_bbox)
                except Exception:
                    layout_ambiguous = True
        try:
            blocks = page.get_text("blocks", sort=True)
            narrative: list[str] = []
            for block in blocks:
                if not isinstance(block, (list, tuple)) or len(block) < 7:
                    layout_ambiguous = True
                    continue
                if block[6] != 0:
                    continue
                block_bbox = _bbox(block[:4])
                if block_bbox is None:
                    layout_ambiguous = True
                    continue
                if any(
                    _bbox_intersects(block_bbox, table_bbox)
                    for table_bbox in table_bboxes
                ):
                    continue
                text = _nfc_lf(str(block[4])).strip()
                if text:
                    narrative.append(text)
            page_text = "\n\n".join(narrative)
            error = None
        except Exception as exc:
            page_text = ""
            tables = []
            error = f"{type(exc).__name__}: {str(exc)[:500]}"
        snapshots.append(
            {
                "page_number": page_number,
                "text": page_text,
                "tables": tuple(tables),
                "quality_score": 1.0,
                "ocr_used": False,
                "ocr_confidence": None,
                "layout_ambiguous": layout_ambiguous,
                "encoding_repaired": False,
                "error": error,
            }
        )
    return tuple(snapshots)


def _render_page_aware_markdown(result: PageAwarePDFResult) -> str:
    body: list[str] = []
    for page_number in range(1, result.page_count + 1):
        body.extend((f"## Page {page_number}", ""))
        page_results = tuple(
            item
            for item in result.parser_results
            if item.coordinates.page_number == page_number
        )
        for item in page_results:
            body.extend((f"<!-- locator: {item.coordinates.locator()} -->", ""))
            if item.coordinates.paragraph_index is not None:
                body.extend((item.raw_text or "", ""))
            elif item.coordinates.table_index is not None:
                row = item.coordinates.row_index
                column = item.coordinates.column_index
                value = item.raw_text if item.raw_text is not None else "null"
                body.extend((f"- Table cell [{row}, {column}]: {value}", ""))
            elif QualityFlag.EMPTY_OUTPUT in item.quality_flags:
                body.extend(("_No extractable text or table on this page._", ""))
            else:
                body.extend(("_Page extraction failed._", ""))
    return "\n".join(body).rstrip() + "\n"


def _pdf_markdown(path: Path, manifest: SourceManifest) -> _Normalized:
    import fitz

    parser_version = str(getattr(fitz, "VersionBind", "1.0.0"))
    with fitz.open(str(path)) as document:
        if bool(getattr(document, "needs_pass", False)):
            raise ValueError("PDF is password protected")
        pages = _pymupdf_page_snapshots(document)
    result = adapt_pdf_pages(
        manifest=manifest,
        pages=pages,
        parser_version=parser_version,
    )
    flags = tuple(
        dict.fromkeys(
            flag.value if isinstance(flag, QualityFlag) else str(flag)
            for parser_result in result.parser_results
            for flag in parser_result.quality_flags
        )
    )
    status = (
        "partial"
        if any(
            item.parse_status is not ParseStatus.PARSED
            for item in result.parser_results
        )
        else "completed"
    )
    return _Normalized(
        body=_render_page_aware_markdown(result),
        parser_results=result.parser_results,
        parser_name=PAGE_AWARE_PDF_PARSER_NAME,
        parser_version=parser_version,
        status=status,
        quality_flags=flags,
    )


def _docling_markdown(path: Path, source_id: str) -> _Normalized:
    from docling_core.types.doc.document import DoclingDocument

    document = DoclingDocument.load_from_json(str(path))
    parser_version = str(getattr(document, "version", "1.0.0"))
    markdown = _nfc_lf(document.export_to_markdown()).strip()
    if not markdown:
        raise ValueError("Docling export is empty")
    pages: dict[int, list[str]] = {}
    for item in document.texts:
        text = _nfc_lf(str(getattr(item, "text", ""))).strip()
        provenance = getattr(item, "prov", None) or []
        page_number = int(provenance[0].page_no) if provenance else 0
        if text and page_number > 0:
            pages.setdefault(page_number, []).append(text)
    results: list[ParserResult] = []
    for page_number, values in sorted(pages.items()):
        results.append(
            _parser_result(
                source_id=source_id,
                raw_text="\n\n".join(values),
                page_number=page_number,
                parser_name="dayu_docling",
                parser_version=parser_version,
                structured_value={"source": "dayu_docling", "page_number": page_number},
            )
        )
    table_index_by_page: dict[int, int] = {}
    locator_lines = ["", "## Locator index", ""]
    for result in results:
        locator_lines.append(f"- `{result.coordinates.locator()}`")
    for table in document.tables:
        provenance = getattr(table, "prov", None) or []
        if not provenance:
            continue
        page_number = int(provenance[0].page_no)
        table_index = table_index_by_page.get(page_number, 0)
        table_index_by_page[page_number] = table_index + 1
        table_text = _nfc_lf(table.export_to_markdown(doc=document)).strip()
        if not table_text:
            continue
        result = _parser_result(
            source_id=source_id,
            raw_text=table_text,
            page_number=page_number,
            table_index=table_index,
            parser_name="dayu_docling",
            parser_version=parser_version,
            structured_value={
                "kind": "table",
                "page_number": page_number,
                "table_index": table_index,
            },
        )
        results.append(result)
        locator_lines.append(f"- `{result.coordinates.locator()}`")
    if not results:
        raise ValueError("Docling provenance contains no page-aware output")
    return _Normalized(
        body=markdown + "\n" + "\n".join(locator_lines) + "\n",
        parser_results=tuple(results),
        parser_name="dayu_docling",
        parser_version=parser_version,
        status="completed",
        quality_flags=(),
    )


def _html_text_markdown(
    text: str, source_id: str, *, format_name: str, repaired: bool
) -> _Normalized:
    from bs4 import BeautifulSoup
    from markdownify import markdownify

    soup = BeautifulSoup(text, "lxml")
    for item in soup(["script", "style", "noscript"]):
        item.decompose()
    markdown = _nfc_lf(markdownify(str(soup), heading_style="ATX")).strip()
    flags = (QualityFlag.ENCODING_REPAIRED,) if repaired else ()
    result = _parser_result(
        source_id=source_id,
        raw_text=soup.get_text("\n", strip=True),
        paragraph_index=0,
        parser_name="html_markdownify",
        parser_version="1.0.0",
        structured_value={"format": format_name},
        flags=flags,
    )
    return _Normalized(
        body=f"<!-- locator: {result.coordinates.locator()} -->\n\n{markdown}\n",
        parser_results=(result,),
        parser_name="html_markdownify",
        parser_version="1.0.0",
        status="partial" if flags else "completed",
        quality_flags=tuple(item.value for item in flags),
    )


def _html_markdown(path: Path, source_id: str) -> _Normalized:
    text, repaired = _decode(path.read_bytes())
    return _html_text_markdown(
        text,
        source_id,
        format_name=path.suffix.lower(),
        repaired=repaired,
    )


def _mht_markdown(path: Path, source_id: str) -> _Normalized:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    for part in message.walk():
        if part.get_content_type() == "text/html":
            charset = part.get_content_charset() or "utf-8"
            payload = part.get_payload(decode=True) or b""
            return _html_text_markdown(
                _nfc_lf(payload.decode(charset, errors="replace")),
                source_id,
                format_name=".mht",
                repaired=False,
            )
    return _text_markdown(
        path, source_id, parser_name="mht_text", parser_version="1.0.0"
    )


def _docx_markdown(path: Path, source_id: str) -> _Normalized:
    from docx import Document

    document = Document(path)
    body: list[str] = []
    raw: list[str] = []
    for paragraph in document.paragraphs:
        value = _nfc_lf(paragraph.text).strip()
        if not value:
            continue
        style = str(getattr(paragraph.style, "name", ""))
        if style.startswith("Heading"):
            try:
                level = max(1, min(6, int(style.split()[-1])))
            except ValueError:
                level = 2
            body.append("#" * level + " " + value)
        else:
            body.append(value)
        raw.append(value)
    for table in document.tables:
        rows = [
            [_nfc_lf(cell.text).strip() for cell in row.cells] for row in table.rows
        ]
        if rows:
            body.append(_markdown_table(rows))
            raw.append("\n".join(" | ".join(row) for row in rows))
    text = "\n\n".join(raw)
    if not text:
        raise ValueError("DOCX contains no extractable text")
    result = _parser_result(
        source_id=source_id,
        raw_text=text,
        paragraph_index=0,
        parser_name="python_docx",
        parser_version="1.0.0",
    )
    return _Normalized(
        body=f"<!-- locator: {result.coordinates.locator()} -->\n\n"
        + "\n\n".join(body)
        + "\n",
        parser_results=(result,),
        parser_name="python_docx",
        parser_version="1.0.0",
        status="completed",
        quality_flags=(),
    )


def _escape_cell(value: Any) -> str:
    return (
        str(value if value is not None else "")
        .replace("\n", " ")
        .replace("|", "\\|")
        .strip()
    )


def _markdown_table(rows: list[list[Any]]) -> str:
    width = max((len(row) for row in rows), default=0)
    if width == 0:
        return ""
    normalized = [
        [_escape_cell(row[index] if index < len(row) else "") for index in range(width)]
        for row in rows
    ]
    header = normalized[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in normalized[1:])
    return "\n".join(lines)


def _xlsx_markdown(path: Path, source_id: str) -> _Normalized:
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    parts: list[str] = []
    raw_parts: list[str] = []
    results: list[ParserResult] = []
    for sheet_index, sheet in enumerate(workbook.worksheets):
        rows = [list(row) for row in sheet.iter_rows(values_only=True)]
        while rows and not any(value not in (None, "") for value in rows[-1]):
            rows.pop()
        if not rows:
            continue
        table = _markdown_table(rows)
        parts.extend((f"## Sheet: {sheet.title}", "", table, ""))
        raw = "\n".join(
            " | ".join(_escape_cell(value) for value in row) for row in rows
        )
        raw_parts.append(raw)
        results.append(
            _parser_result(
                source_id=source_id,
                raw_text=raw,
                table_index=sheet_index,
                parser_name="openpyxl",
                parser_version=str(openpyxl.__version__),
                structured_value={"sheet": sheet.title},
            )
        )
    workbook.close()
    if not results:
        raise ValueError("XLSX contains no non-empty sheets")
    return _Normalized(
        "\n".join(parts),
        tuple(results),
        "openpyxl",
        str(openpyxl.__version__),
        "completed",
        (),
    )


def _xls_markdown(path: Path, source_id: str) -> _Normalized:
    import xlrd

    workbook = xlrd.open_workbook(path, on_demand=True)
    parts: list[str] = []
    results: list[ParserResult] = []
    for sheet_index, sheet in enumerate(workbook.sheets()):
        rows = [sheet.row_values(index) for index in range(sheet.nrows)]
        if not rows:
            continue
        parts.extend((f"## Sheet: {sheet.name}", "", _markdown_table(rows), ""))
        raw = "\n".join(
            " | ".join(_escape_cell(value) for value in row) for row in rows
        )
        results.append(
            _parser_result(
                source_id=source_id,
                raw_text=raw,
                table_index=sheet_index,
                parser_name="xlrd",
                parser_version=str(xlrd.__version__),
                structured_value={"sheet": sheet.name},
            )
        )
    workbook.release_resources()
    if not results:
        raise ValueError("XLS contains no non-empty sheets")
    return _Normalized(
        "\n".join(parts), tuple(results), "xlrd", str(xlrd.__version__), "completed", ()
    )


def _pptx_markdown(path: Path, source_id: str) -> _Normalized:
    from pptx import Presentation
    import pptx

    deck = Presentation(path)
    parts: list[str] = []
    results: list[ParserResult] = []
    for slide_index, slide in enumerate(deck.slides):
        values: list[str] = []
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                value = _nfc_lf(shape.text).strip()
                if value:
                    values.append(value)
        if not values:
            continue
        page_number = slide_index + 1
        raw = "\n\n".join(values)
        parts.extend(
            (
                f"## Slide {page_number}",
                "",
                f"<!-- locator: loc:v1/page:{page_number} -->",
                "",
                raw,
                "",
            )
        )
        results.append(
            _parser_result(
                source_id=source_id,
                raw_text=raw,
                page_number=page_number,
                parser_name="python_pptx",
                parser_version=str(pptx.__version__),
            )
        )
    if not results:
        raise ValueError("PPTX contains no extractable text")
    return _Normalized(
        "\n".join(parts),
        tuple(results),
        "python_pptx",
        str(pptx.__version__),
        "completed",
        (),
    )


def _doc_markdown(path: Path, source_id: str) -> _Normalized:
    completed = subprocess.run(
        ["antiword", str(path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    if completed.returncode != 0:
        raise ValueError(
            "antiword failed: "
            + completed.stderr.decode("utf-8", errors="replace")[:300]
        )
    text, _ = _decode(completed.stdout)
    temporary = _paragraphs(text)
    if not temporary:
        raise ValueError("antiword returned empty text")
    result = _parser_result(
        source_id=source_id,
        raw_text="\n\n".join(temporary),
        paragraph_index=0,
        parser_name="antiword",
        parser_version="1.0.0",
    )
    return _Normalized(
        f"<!-- locator: {result.coordinates.locator()} -->\n\n{result.raw_text}\n",
        (result,),
        "antiword",
        "1.0.0",
        "completed",
        (),
    )


def _json_xml_markdown(path: Path, source_id: str) -> _Normalized:
    text, repaired = _decode(path.read_bytes())
    language = "json" if path.suffix.lower() == ".json" else "xml"
    flag_values = (QualityFlag.ENCODING_REPAIRED,) if repaired else ()
    result = _parser_result(
        source_id=source_id,
        raw_text=text,
        paragraph_index=0,
        parser_name="structured_text",
        parser_version="1.0.0",
        structured_value={"language": language},
        flags=flag_values,
    )
    return _Normalized(
        f"<!-- locator: {result.coordinates.locator()} -->\n\n```{language}\n{text}\n```\n",
        (result,),
        "structured_text",
        "1.0.0",
        "partial" if repaired else "completed",
        tuple(item.value for item in flag_values),
    )


def _unsupported(path: Path, reason: str) -> _Normalized:
    body = (
        "## Extraction status\n\n"
        "This source was cataloged, but no trustworthy text adapter is available.\n\n"
        f"- Format: `{path.suffix.lower() or '[none]'}`\n"
        f"- Quality flag: `unsupported_format`\n"
        f"- Reason: {html.escape(reason)}\n"
    )
    return _Normalized(
        body,
        (),
        "unsupported_format",
        "1.0.0",
        "unsupported",
        ("unsupported_format",),
        reason,
    )


def _normalize_source(
    path: Path, manifest: SourceManifest, docling_path: Path | None
) -> _Normalized:
    source_id = manifest.source_id
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        if docling_path is not None:
            try:
                return _docling_markdown(docling_path, source_id)
            except Exception:
                pass
        return _pdf_markdown(path, manifest)
    if suffix in {".txt", ".md", ".csv"}:
        return _text_markdown(
            path, source_id, parser_name="plain_text", parser_version="1.0.0"
        )
    if suffix in {".html", ".htm"}:
        return _html_markdown(path, source_id)
    if suffix == ".mht":
        return _mht_markdown(path, source_id)
    if suffix == ".docx":
        return _docx_markdown(path, source_id)
    if suffix == ".doc":
        return _doc_markdown(path, source_id)
    if suffix == ".xlsx":
        return _xlsx_markdown(path, source_id)
    if suffix == ".xls":
        return _xls_markdown(path, source_id)
    if suffix == ".pptx":
        return _pptx_markdown(path, source_id)
    if suffix in {".json", ".xml", ".xsd"}:
        return _json_xml_markdown(path, source_id)
    return _unsupported(path, "No audited parser is installed for this format")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _frontmatter(document: Any, normalized: _Normalized) -> str:
    payload = {
        "schema_version": "1.0.0",
        "artifact_role": "normalized",
        "document_id": document["document_id"],
        "source_id": document["primary_source_id"],
        "source_sha256": document["content_sha256"],
        "title": document["title"],
        "document_kind": document["document_kind"],
        "published_date": document["published_date"],
        "normalization_status": normalized.status,
        "parser_name": normalized.parser_name,
        "parser_version": normalized.parser_version,
        "quality_flags": list(normalized.quality_flags),
    }
    return (
        "---\n"
        + yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).rstrip()
        + "\n---\n\n"
    )


def normalize_catalog(
    config: CatalogConfig,
    store: CatalogStore,
    *,
    limit: int | None = None,
    force: bool = False,
    progress: Callable[..., None] | None = None,
) -> ProcessingReport:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    sql = """SELECT d.*,s.content_sha256,s.byte_size,s.mime_type FROM documents d
        JOIN sources s ON s.source_id=d.primary_source_id"""
    params: tuple[Any, ...] = ()
    if not force:
        sql += """ WHERE NOT EXISTS (
            SELECT 1 FROM artifacts existing
            WHERE existing.document_id=d.document_id
            AND existing.artifact_role='normalized'
            AND existing.generator_name=? AND existing.generator_version=?
        )"""
        params = (_NORMALIZER_NAME, NORMALIZER_VERSION)
    sql += " ORDER BY d.document_id"
    if limit is not None:
        sql += " LIMIT ?"
        params += (limit,)
    documents = store.fetchall(sql, params)
    completed = skipped = partial = unsupported = failed = 0
    for document_index, document in enumerate(documents, start=1):
        source_id = document["primary_source_id"]
        locations = store.fetchall(
            """SELECT l.*,r.path AS root_path,r.priority FROM locations l JOIN roots r ON r.root_id=l.root_id
            WHERE l.document_id=? AND l.location_status='active' ORDER BY r.priority,l.relative_path""",
            (document["document_id"],),
        )
        primary = next(
            (
                item
                for item in locations
                if item["role"] == "original_primary" and item["source_id"] == source_id
            ),
            None,
        )
        if primary is None:
            failed += 1
            continue
        source_path = Path(primary["absolute_path"])
        if progress is not None:
            progress(
                current_path=str(source_path.resolve(strict=False)),
                current=document_index,
                total=len(documents),
                detail="extracting Markdown",
            )
        manifest = SourceManifest.from_dict(json.loads(primary["manifest_json"]))
        docling_path: Path | None = None
        metadata = json.loads(document["metadata_json"])
        dayu_meta = metadata.get("dayu_meta") or {}
        expected_pdf_sha = dayu_meta.get("pdf_sha256")
        if (
            source_path.suffix.lower() == ".pdf"
            and expected_pdf_sha == document["content_sha256"]
        ):
            sidecar = next(
                (item for item in locations if item["role"] == "processed_docling"),
                None,
            )
            if sidecar is not None:
                possible = Path(sidecar["absolute_path"])
                if possible.is_file():
                    docling_path = possible
        try:
            normalized = _normalize_source(source_path, manifest, docling_path)
            bundle = IngestService(root=Path(primary["root_path"])).ingest(
                manifest=manifest,
                parser_results=normalized.parser_results,
            )
        except Exception as exc:
            normalized = _unsupported(
                source_path, f"{type(exc).__name__}: {str(exc)[:500]}"
            )
            bundle = IngestService(root=Path(primary["root_path"])).ingest(
                manifest=manifest, parser_results=()
            )
            failed += 1
        raw_text = "\n\n".join(
            result.raw_text or "" for result in normalized.parser_results
        )
        text_fingerprint = compute_text_fingerprint(raw_text)
        output_path = (
            config.derived_dir
            / document["content_sha256"][:2]
            / document["content_sha256"]
            / "normalized.md"
        )
        content = (
            _frontmatter(document, normalized)
            + f"# {document['title']}\n\n"
            + normalized.body
        )
        _atomic_write(output_path, content)
        artifact_hash = _sha256_file(output_path)
        artifact_id = (
            "urn:company-wiki:artifact:sha256:"
            + hashlib.sha256(
                (
                    document["document_id"] + "\0normalized\0" + NORMALIZER_VERSION
                ).encode("utf-8")
            ).hexdigest()
        )
        with store.transaction() as connection:
            connection.execute(
                "DELETE FROM evidence_spans WHERE document_id=?",
                (document["document_id"],),
            )
            for span in bundle.evidence_spans:
                data = span.to_dict()
                coordinates = data["coordinates"]
                connection.execute(
                    """INSERT INTO evidence_spans(span_id,document_id,source_id,locator,page_number,
                    paragraph_index,table_index,raw_text,span_json,parser_name,parser_version,parse_status)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        span.span_id,
                        document["document_id"],
                        span.source_id,
                        span.locator,
                        coordinates["page_number"],
                        coordinates["paragraph_index"],
                        coordinates["table_index"],
                        span.raw_text,
                        span.canonical_json(),
                        span.parser_name,
                        span.parser_version,
                        span.parse_status.value,
                    ),
                )
            connection.execute(
                """INSERT INTO artifacts(artifact_id,document_id,source_id,artifact_role,path,content_sha256,
                byte_size,mime_type,generator_name,generator_version,status,error,metadata_json,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
                ON CONFLICT(document_id,artifact_role,generator_name,generator_version) DO UPDATE SET
                path=excluded.path,content_sha256=excluded.content_sha256,byte_size=excluded.byte_size,
                status=excluded.status,error=excluded.error,metadata_json=excluded.metadata_json,created_at=excluded.created_at""",
                (
                    artifact_id,
                    document["document_id"],
                    source_id,
                    "normalized",
                    str(output_path.resolve()),
                    artifact_hash,
                    output_path.stat().st_size,
                    "text/markdown",
                    _NORMALIZER_NAME,
                    NORMALIZER_VERSION,
                    normalized.status,
                    normalized.error,
                    canonical_json(
                        {
                            "parser_name": normalized.parser_name,
                            "parser_version": normalized.parser_version,
                            "quality_flags": list(normalized.quality_flags),
                            "span_count": len(bundle.evidence_spans),
                        }
                    ),
                ),
            )
            connection.execute(
                "UPDATE documents SET text_fingerprint=? WHERE document_id=?",
                (text_fingerprint, document["document_id"]),
            )
        if normalized.status == "completed":
            completed += 1
        elif normalized.status == "partial":
            partial += 1
        elif normalized.status == "unsupported":
            unsupported += 1
    return ProcessingReport(
        "normalize", completed, skipped, partial, unsupported, failed
    )


def backfill_text_fingerprints(
    config: CatalogConfig,
    store: CatalogStore,
    *,
    limit: int | None = None,
    progress: Callable[..., None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    retry_limit: int = 3,
    retry_backoff_seconds: int = 900,
    now_epoch: float | None = None,
) -> ProcessingReport:
    """Compute and persist ``text_fingerprint`` via the persistent state machine.

    CW-2.28 §12.3 / §12.4.3.3. Dispatch reads from ``document_fingerprint_state``
    (pending + due retryable_failed) instead of re-selecting every NULL row, so
    terminal documents are never re-attempted and retryable failures respect a
    bounded retry/backoff. Each document's outcome is written atomically
    (``documents.text_fingerprint`` + state row in one transaction), so a crash
    cannot split the two writes. No normalized/summary artifacts are written.

    Outcome classification:
      * parseable non-empty text  → ``completed`` (+ fingerprint);
      * empty/whitespace text     → ``unsupported_terminal`` (reason ``empty_text``);
      * no original_primary location → ``unsupported_terminal`` (``no_original_location``);
      * parser/I-O exception      → ``retryable_failed`` with backoff, or
                                    ``failed_terminal`` (``retry_exhausted:<code>``)
                                    once ``attempt_count`` reaches ``retry_limit``.

    ``should_stop`` is checked before each document; when it returns True the
    current file completes cleanly and the batch stops (partial, not failed).
    """
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    if retry_limit < 1:
        raise ValueError("retry_limit must be >= 1")
    if retry_backoff_seconds < 0:
        raise ValueError("retry_backoff_seconds must be >= 0")

    import time as _time

    now = now_epoch if now_epoch is not None else _time.time()
    now_iso = _utc_iso(now)

    # Global backlog before the batch (pending + due retryable_failed).
    status_before = store.fingerprint_status(now_iso=now_iso)
    eligible_total = status_before["eligible"]

    batch = store.select_fingerprint_batch(limit=limit, now_iso=now_iso)
    completed = skipped = partial = unsupported = failed = 0
    terminal_reasons: dict[str, int] = {}
    for document_index, document in enumerate(batch, start=1):
        if should_stop is not None and should_stop():
            partial += max(0, len(batch) - document_index + 1)
            break
        document_id = document["document_id"]
        source_id = document["source_id"]
        source_sha256 = document["source_sha256"]
        attempt_count = int(document["attempt_count"])
        locations = store.fetchall(
            """SELECT l.*,r.path AS root_path FROM locations l JOIN roots r ON r.root_id=l.root_id
            WHERE l.document_id=? AND l.location_status='active' AND l.role='original_primary'
            AND l.source_id=? ORDER BY r.priority,l.relative_path""",
            (document_id, source_id),
        )
        if not locations:
            store.record_fingerprint_outcome(
                document_id=document_id,
                source_id=source_id,
                source_sha256=source_sha256,
                fingerprint=None,
                status="unsupported_terminal",
                attempt_count=attempt_count + 1,
                terminal_reason="no_original_location",
                updated_at=now_iso,
            )
            unsupported += 1
            terminal_reasons["no_original_location"] = (
                terminal_reasons.get("no_original_location", 0) + 1
            )
            continue
        source_path = Path(locations[0]["absolute_path"])
        if progress is not None:
            progress(
                current_path=str(source_path.resolve(strict=False)),
                current=document_index,
                total=len(batch),
                detail="backfilling text fingerprint",
            )
        manifest = SourceManifest.from_dict(json.loads(locations[0]["manifest_json"]))
        try:
            normalized = _normalize_source(source_path, manifest, None)
            raw_text = "\n\n".join(
                result.raw_text or "" for result in normalized.parser_results
            )
            fingerprint = compute_text_fingerprint(raw_text)
        except Exception as exc:
            next_attempt = attempt_count + 1
            error_code = type(exc).__name__
            if next_attempt >= retry_limit:
                store.record_fingerprint_outcome(
                    document_id=document_id,
                    source_id=source_id,
                    source_sha256=source_sha256,
                    fingerprint=None,
                    status="failed_terminal",
                    attempt_count=next_attempt,
                    terminal_reason=f"retry_exhausted:{error_code}",
                    error_code=error_code,
                    error_message=str(exc),
                    updated_at=now_iso,
                )
                terminal_reasons[f"retry_exhausted:{error_code}"] = (
                    terminal_reasons.get(f"retry_exhausted:{error_code}", 0) + 1
                )
            else:
                next_retry_iso = _utc_iso(now + retry_backoff_seconds)
                store.record_fingerprint_outcome(
                    document_id=document_id,
                    source_id=source_id,
                    source_sha256=source_sha256,
                    fingerprint=None,
                    status="retryable_failed",
                    attempt_count=next_attempt,
                    error_code=error_code,
                    error_message=str(exc),
                    next_retry_at=next_retry_iso,
                    updated_at=now_iso,
                )
            failed += 1
            continue
        if fingerprint is None:
            store.record_fingerprint_outcome(
                document_id=document_id,
                source_id=source_id,
                source_sha256=source_sha256,
                fingerprint=None,
                status="unsupported_terminal",
                attempt_count=attempt_count + 1,
                terminal_reason="empty_text",
                updated_at=now_iso,
            )
            unsupported += 1
            terminal_reasons["empty_text"] = terminal_reasons.get("empty_text", 0) + 1
            continue
        store.record_fingerprint_outcome(
            document_id=document_id,
            source_id=source_id,
            source_sha256=source_sha256,
            fingerprint=fingerprint,
            status="completed",
            attempt_count=attempt_count + 1,
            updated_at=now_iso,
        )
        completed += 1

    status_after = store.fingerprint_status(now_iso=now_iso)
    report = ProcessingReport(
        "backfill_text_fingerprints",
        completed=completed,
        skipped=skipped,
        partial=partial,
        unsupported=unsupported,
        failed=failed,
        eligible=eligible_total,
        terminal_reasons=terminal_reasons if terminal_reasons else None,
        due_retry=status_after["due_retry"],
        terminal=status_after["terminal"],
    )
    return report


__all__ = [
    "backfill_text_fingerprints",
    "compute_text_fingerprint",
    "normalize_catalog",
]
