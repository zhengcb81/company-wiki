"""PPTX normalization mechanism tests (shapes, media gaps, package bounds)."""

from __future__ import annotations

import io
import zipfile

import pytest

from company_wiki.document_normalization import (
    NormalizationLimitError,
    NormalizationLimits,
    UnsupportedFormatError,
    normalize_document,
)

from conftest import (
    build_pptx,
    normalize_pptx,
    sha256_hex,
    source_id_for,
    tiny_png,
)


def texts(doc, kind=None):
    return [u.raw_text for u in doc.units if kind is None or u.unit_kind == kind]


class TestTextShapes:
    def test_paragraph_units_carry_slide_and_shape_path(self):
        doc = normalize_pptx(build_pptx())
        paragraphs = [u for u in doc.units if u.unit_kind == "pptx_paragraph"]
        assert len(paragraphs) == 2
        assert paragraphs[0].raw_text == "Segment revenue grew 18% in FY2025"
        for unit in paragraphs:
            locator = unit.metadata["source_locator"]
            assert locator.startswith("cwp-pptx-shape/2|s=")
            assert "|p=0|" in locator
            assert isinstance(unit.metadata["slide_number"], int)

    def test_notes_separate_from_slide_body(self):
        doc = normalize_pptx(
            build_pptx(with_notes="Prepared remarks for analysts")
        )
        notes = [u for u in doc.units if u.unit_kind == "pptx_notes_paragraph"]
        assert len(notes) == 1
        assert notes[0].raw_text == "Prepared remarks for analysts"
        assert notes[0].metadata["notes"] is True
        assert "|notes=1|" in notes[0].metadata["source_locator"]

    def test_group_members_get_nested_shape_paths(self):
        doc = normalize_pptx(build_pptx(with_group=True))
        group_units = [
            u for u in doc.units if u.raw_text.startswith("Grouped caption")
        ]
        assert len(group_units) == 2
        paths = sorted(u.metadata["shape_path"] for u in group_units)
        assert paths == ["0.0", "0.1"]

    def test_table_cells_have_row_column_identity(self):
        doc = normalize_pptx(build_pptx(with_table=True))
        cells = [u for u in doc.units if u.unit_kind == "pptx_table_cell"]
        assert len(cells) == 4
        by_position = {
            (u.metadata["row_index"], u.metadata["column_index"]): u.raw_text
            for u in cells
        }
        assert by_position[(1, 1)] == "$105 billion"
        for unit in cells:
            assert "|c=" in unit.metadata["source_locator"]


class TestMediaAndGaps:
    def test_picture_only_slide_is_honest_partial(self):
        doc = normalize_pptx(build_pptx(with_picture_only_slide=True))
        structure = doc.structure
        assert structure.page_count >= 2
        assert structure.pages_read == structure.page_count
        assert structure.opaque_pages  # the image slide
        assert structure.coverage_complete is False
        image_assets = [a for a in doc.opaque_assets if a.asset_kind == "image"]
        assert image_assets
        asset = image_assets[0]
        assert asset.gap_reason == "image_bytes_only_no_ocr"
        assert asset.media_sha256 == sha256_hex(tiny_png())
        assert asset.original_bytes == tiny_png()
        assert asset.mime_type == "image/png"

    def test_mixed_slide_keeps_text_and_registers_image(self):
        doc = normalize_pptx(build_pptx(with_mixed_slide=True))
        assert "Mixed slide headline" in texts(doc)
        assert any(a.asset_kind == "image" for a in doc.opaque_assets)
        # Both slides produced text, so no slide is opaque.
        assert doc.structure.opaque_pages == ()
        assert doc.structure.coverage_complete is True

    def test_duplicate_media_one_part_two_assets(self):
        doc = normalize_pptx(build_pptx(with_duplicate_picture=True))
        media_digest = sha256_hex(tiny_png())
        assert len(doc.metadata["media_parts"]) == 1
        same_media = [
            a for a in doc.opaque_assets if a.media_sha256 == media_digest
        ]
        assert len(same_media) == 2
        assert len({a.shape_path for a in same_media}) == 2

    def test_chart_is_named_gap(self):
        doc = normalize_pptx(build_pptx(with_chart=True))
        charts = [a for a in doc.opaque_assets if a.asset_kind == "chart"]
        assert len(charts) == 1
        assert charts[0].gap_reason == "chart_xml_not_renderable"

    def test_external_image_link_named_gap_no_fetch(self):
        data = build_pptx(with_picture_only_slide=True)
        # Rewrite the picture relationship as an external link.
        source = io.BytesIO(data)
        target = io.BytesIO()
        with zipfile.ZipFile(source) as archive_in, zipfile.ZipFile(
            target, "w", zipfile.ZIP_DEFLATED
        ) as archive_out:
            for info in archive_in.infolist():
                payload = archive_in.read(info.filename)
                if info.filename.startswith("ppt/slides/_rels/slide"):
                    payload = payload.replace(
                        b'TargetMode="External"', b""
                    )
                    # Point the image relationship at an external URL.
                    import re as _re

                    payload = _re.sub(
                        rb'Target="[^"]*image\d+\.png"',
                        b'Target="https://example.invalid/pic.png" '
                        b'TargetMode="External"',
                        payload,
                    )
                archive_out.writestr(info, payload)
        doc = normalize_document(
            target.getvalue(),
            source_id=source_id_for(target.getvalue()),
            source_sha256=sha256_hex(target.getvalue()),
            mime_type=(
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
            limits=NormalizationLimits(),
        )
        externals = [
            a for a in doc.opaque_assets if a.gap_reason == "external_media_not_fetched"
        ]
        assert externals
        assert all(a.original_bytes is None for a in externals)

    def test_unattached_media_is_named_gap(self):
        data = build_pptx()
        # Append a media part with no relationship referencing it.
        source = io.BytesIO(data)
        target = io.BytesIO()
        with zipfile.ZipFile(source) as archive_in, zipfile.ZipFile(
            target, "w", zipfile.ZIP_DEFLATED
        ) as archive_out:
            for info in archive_in.infolist():
                archive_out.writestr(info, archive_in.read(info.filename))
            archive_out.writestr("ppt/media/imageOrphan.png", tiny_png())
        doc = normalize_document(
            target.getvalue(),
            source_id=source_id_for(target.getvalue()),
            source_sha256=sha256_hex(target.getvalue()),
            mime_type=(
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
            limits=NormalizationLimits(),
        )
        orphans = [
            a
            for a in doc.opaque_assets
            if a.gap_reason == "media_relationship_without_shape"
        ]
        assert len(orphans) == 1
        assert orphans[0].media_sha256 == sha256_hex(tiny_png())


class TestPackageBounds:
    def test_non_zip_bytes_rejected(self):
        data = b"clearly not a zip package"
        with pytest.raises(UnsupportedFormatError):
            normalize_document(
                data,
                source_id=source_id_for(data),
                source_sha256=sha256_hex(data),
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                limits=NormalizationLimits(),
            )

    def test_zip_traversal_member_named_and_no_read_outside(self):
        data = build_pptx()
        source = io.BytesIO(data)
        target = io.BytesIO()
        with zipfile.ZipFile(source) as archive_in, zipfile.ZipFile(
            target, "w", zipfile.ZIP_DEFLATED
        ) as archive_out:
            for info in archive_in.infolist():
                archive_out.writestr(info, archive_in.read(info.filename))
            archive_out.writestr(
                zipfile.ZipInfo("../evil.txt"), b"outside the package"
            )
        doc = normalize_document(
            target.getvalue(),
            source_id=source_id_for(target.getvalue()),
            source_sha256=sha256_hex(target.getvalue()),
            mime_type=(
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
            limits=NormalizationLimits(),
        )
        assert any(e.startswith("zip_traversal:") for e in doc.structure.errors)
        assert doc.structure.page_count == 0

    def test_member_count_bound(self):
        data = build_pptx()
        source = io.BytesIO(data)
        target = io.BytesIO()
        with zipfile.ZipFile(source) as archive_in, zipfile.ZipFile(
            target, "w", zipfile.ZIP_DEFLATED
        ) as archive_out:
            for info in archive_in.infolist():
                archive_out.writestr(info, archive_in.read(info.filename))
            for index in range(10_001):
                archive_out.writestr(f"ppt/pad/{index}.txt", b"x")
        with pytest.raises(NormalizationLimitError) as excinfo:
            normalize_document(
                target.getvalue(),
                source_id=source_id_for(target.getvalue()),
                source_sha256=sha256_hex(target.getvalue()),
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                limits=NormalizationLimits(),
            )
        assert excinfo.value.limit_name == "max_zip_members"

    def test_media_sha_verified_against_actual_bytes_not_declaration(self):
        # The declared content type and the actual bytes disagree here;
        # the asset identity must come from the bytes.
        doc = normalize_pptx(build_pptx(with_picture_only_slide=True))
        asset = next(a for a in doc.opaque_assets if a.asset_kind == "image")
        assert asset.media_sha256 == sha256_hex(asset.original_bytes)
