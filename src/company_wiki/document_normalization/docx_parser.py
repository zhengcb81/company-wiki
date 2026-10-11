"""Pure bounded DOCX body parsing; immutable ZIP/XML locators replay exactly.

No package parts are extracted to disk and external relationships are never
resolved. Current visible body text is selected; tracked edits and unsupported
objects remain explicit source extraction diagnostics.
"""

from __future__ import annotations
from dataclasses import replace
import io
import posixpath
import re
import zipfile
from typing import Any
from lxml import etree
from company_wiki.source_contract.evidence_span import EvidenceCoordinates
from company_wiki.source_catalog.narrative_document import DocumentStructure
from .document import NormalizedDocument
from .errors import NormalizationLimitError, UnsupportedFormatError
from .limits import MAX_ZIP_MEMBERS
from .text import normalize_text
from .units import (
    FORMAT_DOCX,
    DOCX_LOCATOR_SCHEMA,
    DOCX_PARSER_VERSION,
    LEGACY_DOCX_PARSER_VERSION,
    require_parser_version,
    PARSER_NAME,
    build_unit,
)

SUPPORTED_MIME_TYPES = frozenset(
    {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
)
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
MAX_XML_PART_BYTES = 16 * 1024 * 1024
MAX_XML_DEPTH = 128
MAX_XML_ELEMENTS = 200000
MAX_STYLE_INHERITANCE = 128
MAX_STYLE_METADATA_CHARACTERS = 256
_StyleOutline = tuple[bool, int | None]
_StyleRecord = tuple[str | None, str | None, _StyleOutline]
_ResolvedOutline = tuple[int | None, str | None, str | None]
_FINANCIAL = re.compile(
    r"收入|利润|资产负债|现金流|金额|万元|亿元|revenue|income|cash flow|balance sheet|amount|million|billion",
    re.I,
)
_QUESTION = re.compile(
    r"^(?:问|问题|Q|Question)\s*[：:]|^\d+[、.．]\s*(?:问|问题)\s*[：:]", re.I
)
_QA_MARKER = re.compile(
    r"(?:^|[\s。！？!?；;])(?P<label>问|问题|答|答复|回答|Q|Question|A|Answer)\s*[:：]",
    re.I,
)
_ANSWER = re.compile(r"^(?:答|答复|回答|A|Answer)\s*[：:]", re.I)


def _inventory(data, limits):
    limits.check_deadline("docx:archive")
    try:
        package = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError) as exc:
        raise UnsupportedFormatError("invalid DOCX archive") from exc
    try:
        infos = package.infolist()
        if len(infos) > MAX_ZIP_MEMBERS:
            raise NormalizationLimitError("max_zip_members", MAX_ZIP_MEMBERS)
        parts = {}
        total = 0
        for info in infos:
            limits.check_deadline("docx:inventory")
            name = info.filename
            normalized = posixpath.normpath(name.replace("\\", "/"))
            if (
                normalized.startswith(("/", ".."))
                or ":" in normalized
                or (not info.is_dir() and normalized != name)
            ):
                raise UnsupportedFormatError("unsafe DOCX archive member")
            if normalized in parts:
                raise UnsupportedFormatError("duplicate DOCX archive member")
            if info.flag_bits & 1:
                raise UnsupportedFormatError("encrypted DOCX archive member")
            total += info.file_size
            limits.require_within("max_total_uncompressed_bytes", total)
            parts[normalized] = info
        return package, parts, total
    except Exception:
        package.close()
        raise


def _xml(package, info, limits):
    if info.file_size > MAX_XML_PART_BYTES:
        raise NormalizationLimitError("max_xml_part_bytes", MAX_XML_PART_BYTES)
    chunks = []
    actual = 0
    try:
        with package.open(info) as stream:
            while True:
                limits.check_deadline("docx:xml_read")
                chunk = stream.read(min(65536, MAX_XML_PART_BYTES - actual + 1))
                if not chunk:
                    break
                actual += len(chunk)
                if actual > MAX_XML_PART_BYTES or actual > info.file_size:
                    raise NormalizationLimitError(
                        "max_xml_part_bytes", min(MAX_XML_PART_BYTES, info.file_size)
                    )
                chunks.append(chunk)
        root = etree.fromstring(
            b"".join(chunks),
            parser=etree.XMLParser(
                resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False
            ),
        )
        if root.getroottree().docinfo.doctype:
            raise UnsupportedFormatError("DOCX XML doctype is unsupported")
        depth = 0
        count = 0
        for event, _node in etree.iterwalk(root, events=("start", "end")):
            limits.check_deadline("docx:xml_walk")
            if event == "start":
                depth += 1
                count += 1
                if depth > MAX_XML_DEPTH:
                    raise NormalizationLimitError("max_xml_depth", MAX_XML_DEPTH)
                if count > MAX_XML_ELEMENTS:
                    raise NormalizationLimitError("max_xml_elements", MAX_XML_ELEMENTS)
            else:
                depth -= 1
        return root
    except (zipfile.BadZipFile, RuntimeError, etree.XMLSyntaxError, OSError) as exc:
        raise UnsupportedFormatError("invalid DOCX XML/archive") from exc


def _visible_text(node, diagnostics):
    tag = node.tag
    if tag in {W + "del", W + "moveFrom"}:
        diagnostics.add("tracked_changes_present")
        return ""
    if tag in {W + "ins", W + "moveTo"}:
        diagnostics.add("tracked_changes_present")
    if tag == W + "r":
        hidden = node.find(W + "rPr/" + W + "vanish")
        if hidden is not None and hidden.get(W + "val", "true").casefold() not in {
            "false",
            "off",
            "0",
        }:
            return ""
    if tag in {W + "drawing", W + "pict", W + "object", W + "altChunk"}:
        diagnostics.add("docx_opaque_content")
        return ""
    if tag == W + "t":
        return node.text or ""
    if tag in {W + "tab", W + "br", W + "cr"}:
        return " "
    return "".join(_visible_text(child, diagnostics) for child in node)


class _DocxStyles:
    """Resolve only real paragraph outline properties, never title wording."""

    def __init__(self, root, limits, diagnostics):
        self.limits = limits
        self.diagnostics = diagnostics
        self.styles: dict[str, _StyleRecord] = {}
        self.default_style: str | None = None
        self.default_outline: _StyleOutline = (False, None)
        self.resolved: dict[str, _ResolvedOutline] = {}
        if root is None:
            return
        if root.tag != W + "styles":
            raise UnsupportedFormatError("DOCX paragraph styles root is invalid")
        self.default_outline = self.outline(
            root.find(W + "docDefaults/" + W + "pPrDefault/" + W + "pPr")
        )
        for style in root.findall(W + "style"):
            limits.check_deadline("docx:styles")
            if style.get(W + "type", "paragraph") != "paragraph":
                continue
            style_id = style.get(W + "styleId")
            if not style_id:
                diagnostics.add("docx_paragraph_style_missing_id")
                continue
            if style_id in self.styles:
                raise UnsupportedFormatError("duplicate DOCX paragraph style id")
            name = style.find(W + "name")
            based_on = style.find(W + "basedOn")
            self.styles[style_id] = (
                name.get(W + "val") if name is not None else None,
                based_on.get(W + "val") if based_on is not None else None,
                self.outline(style.find(W + "pPr")),
            )
            if style.get(W + "default", "false").casefold() in {"true", "on", "1"}:
                if self.default_style is not None:
                    raise UnsupportedFormatError("multiple default DOCX paragraph styles")
                self.default_style = style_id

    def outline(self, properties) -> _StyleOutline:
        node = properties.find(W + "outlineLvl") if properties is not None else None
        if node is None:
            return False, None
        try:
            level = int(node.get(W + "val", ""))
        except ValueError:
            level = -1
        if not 0 <= level <= 9:
            self.diagnostics.add("docx_invalid_outline_level")
            return True, None  # An invalid explicit value cannot inherit a guess.
        return True, level

    def metadata_text(self, value: str) -> str:
        if len(value) > MAX_STYLE_METADATA_CHARACTERS:
            self.diagnostics.add("docx_style_metadata_truncated")
        return value[:MAX_STYLE_METADATA_CHARACTERS]

    def resolve(self, style_id: str) -> _ResolvedOutline:
        if style_id in self.resolved:
            return self.resolved[style_id]
        seen: set[str] = set()
        chain: list[str] = []
        current: str | None = style_id
        result: _ResolvedOutline = (None, None, None)
        while current:
            self.limits.check_deadline("docx:style_inheritance")
            if current in seen:
                self.diagnostics.add("docx_style_inheritance_cycle")
                break
            if current in self.resolved:
                result = self.resolved[current]
                break
            if len(chain) >= MAX_STYLE_INHERITANCE:
                raise NormalizationLimitError(
                    "max_docx_style_inheritance", MAX_STYLE_INHERITANCE
                )
            seen.add(current)
            chain.append(current)
            style = self.styles.get(current)
            if style is None:
                self.diagnostics.add("docx_paragraph_style_missing")
                break
            _name, based_on, (present, level) = style
            if present:
                result = (level, "style_outline", current)
                break
            current = based_on
        else:
            if self.default_outline[0]:
                result = (self.default_outline[1], "document_default_outline", None)
        for item in chain:
            self.resolved[item] = result
        return result

    def paragraph(self, node):
        self.limits.check_deadline("docx:paragraph_structure")
        properties = node.find(W + "pPr")
        style_node = properties.find(W + "pStyle") if properties is not None else None
        style_id = style_node.get(W + "val") if style_node is not None else self.default_style
        metadata: dict[str, Any] = {}
        if style_id:
            metadata["paragraph_style_id"] = self.metadata_text(style_id)
            style = self.styles.get(style_id)
            if style is None:
                self.diagnostics.add("docx_paragraph_style_missing")
            elif style[0] is not None:
                metadata["paragraph_style_name"] = self.metadata_text(style[0])
        present, level = self.outline(properties)
        basis: str | None = "paragraph_outline"
        outline_style: str | None = None
        if not present:
            if style_id:
                level, basis, outline_style = self.resolve(style_id)
            elif self.default_outline[0]:
                level, basis = self.default_outline[1], "document_default_outline"
            else:
                level, basis = None, None
        if level is not None:
            metadata["outline_level"] = level
        if outline_style is not None:
            metadata["outline_style_id"] = self.metadata_text(outline_style)
        if level is not None and level < 9:
            metadata.update(heading_level=level + 1, heading_basis=basis)
            return "docx_heading", metadata
        return "docx_paragraph", metadata


class _DocxBody:
    def __init__(self, source_id, source_sha256, limits, *, parser_version):
        self.source_id = source_id
        self.sha = source_sha256
        self.limits = limits
        self.parser_version = parser_version
        self.styles: _DocxStyles | None = None
        self.units = []
        self.diagnostics = set()
        self.text_bytes = 0
        self.paragraphs = 0
        self.tables = 0
        self.qa_counter = 0
        self.active_qa = None

    def emit(self, node, *, coordinates, locator, kind, metadata=None):
        self.limits.check_deadline("docx:emit")
        text = normalize_text(_visible_text(node, self.diagnostics))
        if not text:
            return
        markers = list(_QA_MARKER.finditer(text))
        starts = sorted({0, *(m.start("label") for m in markers)})
        for start, end in zip(starts, (*starts[1:], len(text)), strict=True):
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            if start == end:
                continue
            self.limits.require_within("max_units", len(self.units) + 1)
            piece = text[start:end]
            self.text_bytes += len(piece.encode("utf-8"))
            self.limits.require_within("max_text_output_bytes", self.text_bytes)
            role = "company_filing"
            meta = dict(metadata or {})
            if _QUESTION.search(piece):
                self.qa_counter += 1
                self.active_qa = "docx-qa-" + str(self.qa_counter)
                role = "analyst"
            elif _ANSWER.search(piece):
                role = "management"
            else:
                self.active_qa = None
            if self.active_qa is not None and role in {"analyst", "management"}:
                meta.update(qa_group_id=self.active_qa, section="qa")
            piece_coordinates = coordinates
            piece_locator = locator
            if len(starts) > 1:
                piece_coordinates = replace(coordinates, char_start=start, char_end=end)
                piece_locator += f"|ch={start}:{end}"
            self.units.append(
                build_unit(
                    source_id=self.source_id,
                    source_sha256=self.sha,
                    format_name=FORMAT_DOCX,
                    parser_version=self.parser_version,
                    coordinates=piece_coordinates,
                    raw_text=piece,
                    unit_kind=kind,
                    source_role=role,
                    source_locator=piece_locator,
                    transform="docx_visible_body_v1",
                    extra_metadata=meta,
                )
            )

    def table(self, table):
        index = self.tables
        self.tables += 1
        rows = table.findall(W + "tr")
        if any(
            child.tag not in {W + "tblPr", W + "tblGrid", W + "tr"} for child in table
        ):
            self.diagnostics.add("docx_unsupported_table_element")
        if any(
            child.tag not in {W + "trPr", W + "tc"} for row in rows for child in row
        ):
            self.diagnostics.add("docx_unsupported_table_element")
        row_cells = [row.findall(W + "tc") for row in rows]
        headers = [
            normalize_text(_visible_text(cell, self.diagnostics))
            for cell in (row_cells[0] if row_cells else [])
        ]
        basis = tuple(sorted(set(_FINANCIAL.findall(" ".join(headers)))))
        for row_index, cells in enumerate(row_cells):
            for column_index, cell in enumerate(cells):
                para_index = 0
                for child in cell:
                    if child.tag == W + "p":
                        self.emit(
                            child,
                            coordinates=EvidenceCoordinates(
                                table_index=index,
                                row_index=row_index,
                                column_index=column_index,
                            ),
                            locator=f"{DOCX_LOCATOR_SCHEMA}|t={index}|r={row_index}|c={column_index}|p={para_index}",
                            kind="docx_table_cell",
                            metadata={
                                "table_class": "financial" if basis else "unknown",
                                "table_class_basis": list(basis),
                                "table_headers": headers,
                                "table_index": index,
                                "row_index": row_index,
                                "column_index": column_index,
                                "cell_paragraph_index": para_index,
                            },
                        )
                        para_index += 1
                    elif child.tag == W + "tbl":
                        self.table(child)
                    elif child.tag != W + "tcPr":
                        self.diagnostics.add("docx_unsupported_table_element")

    def body(self, body, *, visible=True):
        for child in body:
            self.limits.check_deadline("docx:body")
            if child.tag == W + "p":
                index = self.paragraphs
                self.paragraphs += 1
                if visible:
                    kind, metadata = (
                        self.styles.paragraph(child)
                        if self.styles is not None
                        else ("docx_paragraph", None)
                    )
                    self.emit(
                        child,
                        coordinates=EvidenceCoordinates(paragraph_index=index),
                        locator=f"{DOCX_LOCATOR_SCHEMA}|p={index}",
                        kind=kind,
                        metadata=metadata,
                    )
            elif child.tag == W + "tbl":
                self.active_qa = None
                if visible:
                    self.table(child)
                else:
                    self.tables += sum(1 for _ in child.iter(W + "tbl"))
                self.active_qa = None
            elif child.tag in {
                W + "sdt",
                W + "customXml",
                W + "ins",
                W + "del",
                W + "moveFrom",
                W + "moveTo",
            }:
                if child.tag in {W + "del", W + "moveFrom"}:
                    self.diagnostics.add("tracked_changes_present")
                    self.body(child, visible=False)
                else:
                    if child.tag in {W + "ins", W + "moveTo"}:
                        self.diagnostics.add("tracked_changes_present")
                    self.body(
                        child.find(W + "sdtContent")
                        if child.tag == W + "sdt"
                        and child.find(W + "sdtContent") is not None
                        else child,
                        visible=visible,
                    )
            elif child.tag not in {
                W + "sectPr",
                W + "bookmarkStart",
                W + "bookmarkEnd",
                W + "proofErr",
            }:
                self.diagnostics.add("docx_unsupported_body_element")


def parse_docx(
    original, *, source_id, source_sha256, mime_type, limits,
    parser_version=DOCX_PARSER_VERSION,
):
    require_parser_version(FORMAT_DOCX, parser_version)
    package, parts, total = _inventory(original, limits)
    try:
        if "word/document.xml" not in parts:
            raise UnsupportedFormatError("DOCX main document is missing")
        if any(name.lower().endswith("vbaproject.bin") for name in parts):
            raise UnsupportedFormatError("DOCX macro package is unsupported")
        root = _xml(package, parts["word/document.xml"], limits)
        body = root.find(W + "body")
        if root.tag != W + "document" or body is None:
            raise UnsupportedFormatError("DOCX document body is missing")
        external = 0
        for name, info in parts.items():
            if name.endswith(".rels"):
                relations = _xml(package, info, limits)
                external += sum(
                    1
                    for r in relations
                    if r.tag == REL + "Relationship"
                    and r.get("TargetMode") == "External"
                )
        state = _DocxBody(
            source_id, source_sha256, limits, parser_version=parser_version
        )
        if parser_version != LEGACY_DOCX_PARSER_VERSION:
            styles = (
                _xml(package, parts["word/styles.xml"], limits)
                if "word/styles.xml" in parts else None
            )
            state.styles = _DocxStyles(styles, limits, state.diagnostics)
        state.body(body)
        if not state.units:
            state.diagnostics.add("docx_no_visible_text")
        if any(re.fullmatch(r"word/(?:header|footer)\d+\.xml", name) for name in parts):
            state.diagnostics.add("docx_header_footer_not_parsed")
        structure = DocumentStructure(
            source_id,
            source_sha256,
            "und",
            tuple(state.units),
            line_count=max(1, state.paragraphs + state.tables),
            errors=tuple(sorted(state.diagnostics)),
        )
        return NormalizedDocument(
            source_id,
            source_sha256,
            FORMAT_DOCX,
            PARSER_NAME,
            parser_version,
            structure,
            metadata={
                "archive_member_count": len(parts),
                "uncompressed_bytes": total,
                "external_relationship_count": external,
                "body_paragraph_count": state.paragraphs,
                "table_count": state.tables,
            },
        )
    finally:
        package.close()
