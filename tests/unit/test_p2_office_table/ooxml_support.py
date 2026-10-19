"""Synthetic OOXML package builders for the P2 office-table structure card.

Every package here is generated from literals in this module; nothing is copied
from a production directory and no real filing material is read.  Packages are
built deterministically (fixed member order, fixed ``ZipInfo`` timestamps) so
their SHA-256 values are stable across runs and platforms.

Card: ``docs/plans/parallel-packages-2026-10-18/P2-OFFICE-TABLE/card.md`` §6.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import hashlib
import io
import zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
PPTX_MIME = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)

DOCX_CONTENT_TYPES = (
    f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<Types xmlns="{CT}">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.'
    'wordprocessingml.document.main+xml"/>'
    "</Types>"
)

DOCX_ROOT_RELS = (
    f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<Relationships xmlns="{PKG_REL}">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/officeDocument" Target="word/document.xml"/>'
    "</Relationships>"
)


def _zip(members: Iterable[tuple[str, bytes]]) -> bytes:
    """Build a byte-identical ZIP archive from ordered ``(name, bytes)`` pairs."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in members:
            info = zipfile.ZipInfo(filename=name, date_time=(2026, 10, 18, 0, 0, 0))
            # ``create_system`` defaults to 0 on Windows and 3 on Unix, which
            # changes the central directory and makes the same fixture hash
            # differently per platform; pin it so the committed bytes are
            # reproducible everywhere.
            info.create_system = 0
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o600 << 16
            archive.writestr(info, payload)
    return buffer.getvalue()


def sha256_of(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


# --------------------------------------------------------------------------- DOCX


def run(text: str) -> str:
    return f"<w:r><w:t xml:space=\"preserve\">{text}</w:t></w:r>"


def paragraph(text: str = "", *, runs: Sequence[str] = (), props: str = "") -> str:
    """One ``w:p``; ``text`` becomes a single run unless ``runs`` is given."""
    body = "".join(run(item) for item in runs) if runs else (run(text) if text else "")
    prefix = f"<w:pPr>{props}</w:pPr>" if props else ""
    return f"<w:p>{prefix}{body}</w:p>"


def page_break_run() -> str:
    return "<w:r><w:lastRenderedPageBreak/></w:r>"


def cell(
    *paragraphs: str,
    grid_span: int | None = None,
    vmerge: str | None = None,
    width: int | None = None,
) -> str:
    """One ``w:tc``.

    ``vmerge``: ``None`` (no ``w:vMerge``), ``"restart"``, ``"continue"`` (explicit
    ``w:val="continue"``), or ``""`` (bare ``w:vMerge`` with no ``w:val``).
    """
    props: list[str] = []
    if width is not None:
        props.append(f'<w:tcW w:w="{width}" w:type="dxa"/>')
    if grid_span is not None:
        props.append(f'<w:gridSpan w:val="{grid_span}"/>')
    if vmerge is not None:
        props.append(
            "<w:vMerge/>" if vmerge == "" else f'<w:vMerge w:val="{vmerge}"/>'
        )
    prefix = f"<w:tcPr>{''.join(props)}</w:tcPr>" if props else ""
    body = "".join(paragraphs) if paragraphs else ""
    return f"<w:tc>{prefix}{body}</w:tc>"


def empty_cell(**kwargs: object) -> str:
    """A cell that carries no paragraph at all (no locator can exist)."""
    return cell(**kwargs)  # type: ignore[arg-type]


def row(*cells: str, header: bool = False, height: int | None = None) -> str:
    props: list[str] = []
    if height is not None:
        props.append(f'<w:trHeight w:val="{height}"/>')
    if header:
        props.append("<w:tblHeader/>")
    prefix = f"<w:trPr>{''.join(props)}</w:trPr>" if props else ""
    return f"<w:tr>{prefix}{''.join(cells)}</w:tr>"


def table(
    *rows: str,
    widths: Sequence[int] | None = (2880, 2880),
) -> str:
    """One ``w:tbl``; ``widths`` are the declared ``w:tblGrid`` columns (twips).

    ``widths=None`` omits ``w:tblGrid`` entirely, so the grid column count is
    unknown.
    """
    grid = ""
    if widths is not None:
        cells = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
        grid = f"<w:tblGrid>{cells}</w:tblGrid>"
    return f"<w:tbl><w:tblPr/>{grid}{''.join(rows)}</w:tbl>"


def docx(body: str, *, extra: Mapping[str, bytes | str] | None = None) -> bytes:
    members: list[tuple[str, bytes]] = [
        ("[Content_Types].xml", DOCX_CONTENT_TYPES.encode("utf-8")),
        ("_rels/.rels", DOCX_ROOT_RELS.encode("utf-8")),
        (
            "word/document.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<w:document xmlns:w="{W}" xmlns:r="{R}">'
                f"<w:body>{body}<w:sectPr/></w:body></w:document>"
            ).encode("utf-8"),
        ),
    ]
    for name, payload in (extra or {}).items():
        members.append(
            (name, payload.encode("utf-8") if isinstance(payload, str) else payload)
        )
    return _zip(members)


def docx_footnotes(notes: Mapping[str, str]) -> bytes:
    """``word/footnotes.xml``; ``notes`` maps ``w:id`` to visible footnote text."""
    entries = []
    for footnote_id, text in notes.items():
        entries.append(
            f'<w:footnote w:id="{footnote_id}">{paragraph(text)}</w:footnote>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:footnotes xmlns:w="{W}">{"".join(entries)}</w:footnotes>'
    ).encode("utf-8")


def footnote_reference(footnote_id: str) -> str:
    return (
        "<w:r><w:footnoteReference "
        f'w:id="{footnote_id}"/></w:r>'
    )


# --------------------------------------------------------------------------- PPTX

PPTX_CONTENT_TYPES = (
    f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<Types xmlns="{CT}">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/ppt/presentation.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.'
    'presentationml.presentation.main+xml"/>'
    '<Override PartName="/ppt/slides/slide1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.'
    'presentationml.slide+xml"/>'
    "</Types>"
)

PPTX_ROOT_RELS = (
    f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<Relationships xmlns="{PKG_REL}">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/officeDocument" Target="ppt/presentation.xml"/>'
    "</Relationships>"
)

PPTX_PRESENTATION_RELS = (
    f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<Relationships xmlns="{PKG_REL}">'
    '<Relationship Id="rId3" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/slide" Target="slides/slide1.xml"/>'
    "</Relationships>"
)

PPTX_PRESENTATION = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<p:presentation xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}">'
    '<p:sldIdLst><p:sldId id="256" r:id="rId3"/></p:sldIdLst>'
    '<p:sldSz cx="9144000" cy="6858000"/>'
    '<p:notesSz cx="6858000" cy="9144000"/>'
    "</p:presentation>"
)


def pptx_text(text: str) -> str:
    body = f"<a:p><a:r><a:t>{text}</a:t></a:r></a:p>" if text else "<a:p/>"
    return f'<a:txBody><a:bodyPr/><a:lstStyle/>{body}</a:txBody>'


def pptx_cell(
    text: str = "",
    *,
    grid_span: int | None = None,
    hmerge: bool = False,
    vmerge: bool = False,
) -> str:
    attributes = ""
    if grid_span is not None:
        attributes += f' gridSpan="{grid_span}"'
    if hmerge:
        attributes += ' hMerge="1"'
    if vmerge:
        attributes += ' vMerge="1"'
    return f"<a:tc{attributes}>{pptx_text(text)}<a:tcPr/></a:tc>"


def pptx_table(
    grid_widths: Sequence[int],
    rows: Sequence[Sequence[str]],
) -> str:
    """One ``a:tbl`` (a ``p:graphicFrame``'s payload)."""
    grid = "".join(f'<a:gridCol w="{width}"/>' for width in grid_widths)
    body = "".join(
        f'<a:tr h="370840">{"".join(cells)}</a:tr>' for cells in rows
    )
    return f"<a:tbl><a:tblGrid>{grid}</a:tblGrid>{body}</a:tbl>"


def pptx_graphic_frame(table_xml: str, *, shape_id: int = 2) -> str:
    return (
        "<p:graphicFrame>"
        "<p:nvGraphicFramePr>"
        f'<p:cNvPr id="{shape_id}" name="Table {shape_id}"/>'
        "<p:cNvGraphicFramePr/>"
        "<p:nvPr/>"
        "</p:nvGraphicFramePr>"
        '<p:xfrm><a:off x="0" y="0"/><a:ext cx="6096000" cy="1828800"/></p:xfrm>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/'
        'drawingml/2006/table">'
        f"{table_xml}"
        "</a:graphicData></a:graphic></p:graphicFrame>"
    )


def pptx_slide(*shapes: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sld xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}">'
        f"<p:cSld><p:spTree>{''.join(shapes)}</p:spTree></p:cSld>"
        "</p:sld>"
    )


def pptx(*tables: str, extra_shapes: Sequence[str] = ()) -> bytes:
    """A one-slide PPTX whose slide holds ``tables`` (as graphic frames)."""
    shapes = list(extra_shapes)
    for index, table_xml in enumerate(tables, start=1):
        shapes.append(pptx_graphic_frame(table_xml, shape_id=index + 1))
    return _zip(
        [
            ("[Content_Types].xml", PPTX_CONTENT_TYPES.encode("utf-8")),
            ("_rels/.rels", PPTX_ROOT_RELS.encode("utf-8")),
            ("ppt/presentation.xml", PPTX_PRESENTATION.encode("utf-8")),
            (
                "ppt/_rels/presentation.xml.rels",
                PPTX_PRESENTATION_RELS.encode("utf-8"),
            ),
            ("ppt/slides/slide1.xml", pptx_slide(*shapes).encode("utf-8")),
        ]
    )


def encrypt_member(payload: bytes, member: str) -> bytes:
    """Set the ZIP "encrypted" general-purpose bit on one member.

    ``zipfile.writestr`` clears ``flag_bits``, so the bit is patched into the
    produced archive's local file header and central directory instead.
    """
    marker = member.encode("utf-8")
    data = bytearray(payload)
    # Local file header:  PK\x03\x04 + ... ; general purpose bit flag at offset 6.
    for signature, flag_offset in (
        (b"PK\x03\x04", 6),
        (b"PK\x01\x02", 8),
    ):
        start = 0
        while True:
            index = data.find(signature, start)
            if index < 0:
                break
            name_length_offset = (
                index + 26 if signature == b"PK\x03\x04" else index + 28
            )
            name_length = int.from_bytes(
                data[name_length_offset : name_length_offset + 2], "little"
            )
            name_start = (
                index + 30 if signature == b"PK\x03\x04" else index + 46
            )
            name = bytes(data[name_start : name_start + name_length])
            if name == marker:
                flags = int.from_bytes(
                    data[index + flag_offset : index + flag_offset + 2], "little"
                )
                data[index + flag_offset : index + flag_offset + 2] = (
                    flags | 0x1
                ).to_bytes(2, "little")
            start = index + 4
    return bytes(data)


__all__ = [
    "A",
    "DOCX_MIME",
    "P",
    "PPTX_MIME",
    "R",
    "W",
    "cell",
    "docx",
    "docx_footnotes",
    "empty_cell",
    "encrypt_member",
    "footnote_reference",
    "page_break_run",
    "paragraph",
    "pptx",
    "pptx_cell",
    "pptx_graphic_frame",
    "pptx_slide",
    "pptx_table",
    "run",
    "sha256_of",
    "table",
    "row",
]
