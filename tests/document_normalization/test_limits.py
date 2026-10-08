"""Strict finite limits: invalid values and named refusal on exceed."""

from __future__ import annotations

import time

import pytest

from company_wiki.document_normalization import (
    DEFAULT_LIMITS,
    MAX_ZIP_MEMBERS,
    NormalizationLimitError,
    NormalizationLimits,
    normalize_document,
)

from conftest import build_pptx, html_page, normalize_html, sha256_hex, source_id_for


class TestLimitValidation:
    def test_zero_and_negative_integers_rejected(self):
        for bad in (0, -1):
            with pytest.raises(ValueError):
                NormalizationLimits(max_source_bytes=bad)

    def test_bool_and_float_rejected(self):
        with pytest.raises(TypeError):
            NormalizationLimits(max_units=True)
        with pytest.raises(TypeError):
            NormalizationLimits(max_text_output_bytes=1.5)

    def test_non_finite_deadline_rejected(self):
        with pytest.raises(ValueError):
            NormalizationLimits(deadline=float("nan"))

    def test_deadline_must_be_number_or_none(self):
        with pytest.raises(TypeError):
            NormalizationLimits(deadline="soon")

    def test_defaults_are_finite_positive(self):
        limits = DEFAULT_LIMITS
        for name in (
            "max_source_bytes",
            "max_total_uncompressed_bytes",
            "max_text_output_bytes",
            "max_units",
            "max_pages",
            "max_media_bytes",
        ):
            value = getattr(limits, name)
            assert isinstance(value, int) and value > 0
        assert limits.deadline is None
        assert MAX_ZIP_MEMBERS == 10_000

    def test_expired_deadline_raises_named_error(self):
        limits = NormalizationLimits(deadline=time.monotonic() - 1)
        with pytest.raises(NormalizationLimitError) as excinfo:
            limits.check_deadline("unit_test")
        assert excinfo.value.limit_name == "deadline"


class TestLimitEnforcementHtml:
    def test_source_bytes_limit_names_the_limit(self):
        html = html_page("<p>hello</p>")
        data = html.encode("utf-8")
        with pytest.raises(NormalizationLimitError) as excinfo:
            normalize_document(
                data,
                source_id=source_id_for(data),
                source_sha256=sha256_hex(data),
                mime_type="text/html",
                limits=NormalizationLimits(max_source_bytes=8),
            )
        assert excinfo.value.limit_name == "max_source_bytes"

    def test_unit_limit_refuses_instead_of_truncating(self):
        html = html_page("<p>a</p><p>b</p><p>c</p>")
        with pytest.raises(NormalizationLimitError) as excinfo:
            normalize_html(html, limits=NormalizationLimits(max_units=2))
        assert excinfo.value.limit_name == "max_units"

    def test_text_output_limit_refuses(self):
        body = "<p>" + ("word " * 500) + "</p>"
        with pytest.raises(NormalizationLimitError) as excinfo:
            normalize_html(
                html_page(body),
                limits=NormalizationLimits(max_text_output_bytes=64),
            )
        assert excinfo.value.limit_name == "max_text_output_bytes"


class TestLimitEnforcementPptx:
    def test_slide_count_limit(self):
        data = build_pptx(with_group=True, with_mixed_slide=True)
        with pytest.raises(NormalizationLimitError) as excinfo:
            normalize_document(
                data,
                source_id=source_id_for(data),
                source_sha256=sha256_hex(data),
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                limits=NormalizationLimits(max_pages=1),
            )
        assert excinfo.value.limit_name == "max_pages"

    def test_zip_total_uncompressed_limit(self):
        # A real compressed payload that expands past the configured budget.
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("ppt/slides/slide1.xml", b"\x00" * 300_000)
        data = buffer.getvalue()
        with pytest.raises(NormalizationLimitError) as excinfo:
            normalize_document(
                data,
                source_id=source_id_for(data),
                source_sha256=sha256_hex(data),
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                limits=NormalizationLimits(max_total_uncompressed_bytes=100_000),
            )
        assert excinfo.value.limit_name == "max_total_uncompressed_bytes"

    def test_media_budget_limit(self):
        data = build_pptx(with_picture_only_slide=True)
        with pytest.raises(NormalizationLimitError) as excinfo:
            normalize_document(
                data,
                source_id=source_id_for(data),
                source_sha256=sha256_hex(data),
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                limits=NormalizationLimits(max_media_bytes=16),
            )
        assert excinfo.value.limit_name == "max_media_bytes"
