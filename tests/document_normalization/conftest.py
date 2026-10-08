"""Shared fixtures for the document-normalization test package.

All inputs are synthetic bytes built in memory; no network, no model, no
repository state.  Real originals are exercised only through
``run_real_originals.py`` (see the construction card).
"""

from __future__ import annotations

import hashlib
import io

import pytest

from company_wiki.document_normalization import (
    NormalizationLimits,
    normalize_document,
)

# Deterministic 1x1 red PNG built via PIL so python-pptx accepts it.
def tiny_png() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), (255, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_id_for(data: bytes) -> str:
    return "urn:company-wiki:source:sha256:" + sha256_hex(data)


def normalize_html(html: str, *, limits: NormalizationLimits | None = None):
    data = html.encode("utf-8")
    return normalize_document(
        data,
        source_id=source_id_for(data),
        source_sha256=sha256_hex(data),
        mime_type="text/html",
        limits=limits,
    )


def html_page(body: str) -> str:
    return f"<!DOCTYPE html><html><head><title>t</title></head><body>{body}</body></html>"


def build_pptx(
    *,
    with_table: bool = False,
    with_group: bool = False,
    with_picture_only_slide: bool = False,
    with_mixed_slide: bool = False,
    with_notes: str | None = None,
    with_duplicate_picture: bool = False,
    with_chart: bool = False,
) -> bytes:
    """Build a small deterministic deck covering the card's PPTX scenarios."""
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.util import Emu, Inches

    presentation = Presentation()
    blank = presentation.slide_layouts[6]

    slide_one = presentation.slides.add_slide(blank)
    box = slide_one.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(2))
    frame = box.text_frame
    frame.text = "Segment revenue grew 18% in FY2025"
    paragraph = frame.add_paragraph()
    paragraph.text = "Server products lead growth"

    if with_table:
        table_shape = slide_one.shapes.add_table(2, 2, Inches(1), Inches(3), Inches(4), Inches(1))
        table = table_shape.table
        table.cell(0, 0).text = "Segment"
        table.cell(0, 1).text = "Revenue"
        table.cell(1, 0).text = "Intelligent Cloud"
        table.cell(1, 1).text = "$105 billion"

    if with_notes:
        slide_one.notes_slide.notes_text_frame.text = with_notes

    if with_group:
        slide_two = presentation.slides.add_slide(blank)
        group = slide_two.shapes.add_group_shape()
        left = group.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
        left.text_frame.text = "Grouped caption A"
        right = group.shapes.add_textbox(Inches(4), Inches(1), Inches(3), Inches(1))
        right.text_frame.text = "Grouped caption B"

    if with_chart:
        chart_slide = presentation.slides.add_slide(blank)
        chart_data = CategoryChartData()
        chart_data.categories = ["FY2024", "FY2025"]
        chart_data.add_series("Revenue", (95.0, 105.0))
        chart_slide.shapes.add_chart(
            1,  # XL_CHART_TYPE.COLUMN_CLUSTERED
            Inches(1),
            Inches(2),
            Inches(4),
            Inches(3),
            chart_data,
        )

    if with_picture_only_slide:
        image_slide = presentation.slides.add_slide(blank)
        image_slide.shapes.add_picture(
            io.BytesIO(tiny_png()), Emu(0), Emu(0), Emu(9144000), Emu(5143500)
        )

    if with_mixed_slide:
        mixed = presentation.slides.add_slide(blank)
        title = mixed.shapes.add_textbox(Inches(1), Inches(0.5), Inches(4), Inches(1))
        title.text_frame.text = "Mixed slide headline"
        mixed.shapes.add_picture(
            io.BytesIO(tiny_png()), Inches(1), Inches(2), Inches(3), Inches(2)
        )

    if with_duplicate_picture:
        dup = presentation.slides.add_slide(blank)
        dup.shapes.add_picture(io.BytesIO(tiny_png()), Inches(1), Inches(1), Inches(2), Inches(2))
        dup.shapes.add_picture(io.BytesIO(tiny_png()), Inches(4), Inches(1), Inches(2), Inches(2))

    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def normalize_pptx(
    data: bytes, *, limits: NormalizationLimits | None = None
):
    return normalize_document(
        data,
        source_id=source_id_for(data),
        source_sha256=sha256_hex(data),
        mime_type=(
            "application/vnd.openxmlformats-officedocument."
            "presentationml.presentation"
        ),
        limits=limits,
    )


@pytest.fixture
def png_bytes() -> bytes:
    return tiny_png()


__all__ = [
    "build_pptx",
    "html_page",
    "normalize_html",
    "normalize_pptx",
    "sha256_hex",
    "source_id_for",
    "tiny_png",
]
