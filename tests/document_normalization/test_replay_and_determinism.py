"""Replay refusals, cross-process determinism, and EvidenceSpan bridging."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from company_wiki.document_normalization import (
    NormalizationLimits,
    replay_unit,
)
from company_wiki.source_contract.evidence_span import EvidenceSpan, ParseStatus

from conftest import (
    build_pptx,
    html_page,
    normalize_html,
    normalize_pptx,
    sha256_hex,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _html_bytes() -> bytes:
    return html_page(
        "<h1>Annual Report</h1>"
        "<p>Fiscal year 2025 revenue reached $245 billion.</p>"
        "<table><tr><th>Year</th><th>Revenue</th></tr>"
        "<tr><td>FY2025</td><td>$245 billion</td></tr></table>"
        '<p class="footnote">1. Revenue includes cloud services</p>'
    ).encode("utf-8")


class TestReplayVerificationHtml:
    def test_exact_replay_returns_text(self):
        data = _html_bytes()
        doc = normalize_html(data.decode("utf-8"))
        for unit in doc.units:
            assert (
                replay_unit(
                    data,
                    source_sha256=sha256_hex(data),
                    unit=unit,
                    limits=NormalizationLimits(),
                )
                == unit.raw_text
            )

    def test_wrong_sha_refused(self):
        data = _html_bytes()
        doc = normalize_html(data.decode("utf-8"))
        with pytest.raises(ValueError, match="source_sha256"):
            replay_unit(
                data,
                source_sha256="0" * 64,
                unit=doc.units[0],
                limits=NormalizationLimits(),
            )

    def test_tampered_locator_refused(self):
        data = _html_bytes()
        doc = normalize_html(data.decode("utf-8"))
        unit = doc.units[0]
        tampered_metadata = dict(unit.metadata)
        tampered_metadata["source_locator"] = (
            "cwp-html-dom/1|n=999999.999999.999999"
        )
        from company_wiki.document_normalization.units import compute_unit_id

        tampered_id = compute_unit_id(
            source_id=unit.source_id,
            source_sha256=unit.metadata["source_sha256"],
            format_name=unit.metadata["format"],
            source_locator=tampered_metadata["source_locator"],
            text_sha256=unit.text_sha256,
            unit_kind=unit.unit_kind,
            source_role=unit.source_role,
        )
        tampered = type(unit)(
            unit_id=tampered_id,
            source_id=unit.source_id,
            parser_name=unit.parser_name,
            parser_version=unit.parser_version,
            coordinates=unit.coordinates,
            raw_text=unit.raw_text,
            unit_kind=unit.unit_kind,
            source_role=unit.source_role,
            language=unit.language,
            quality_flags=unit.quality_flags,
            metadata=tampered_metadata,
        )
        # A fully self-consistent unit whose locator points nowhere.
        with pytest.raises(ValueError):
            replay_unit(
                data,
                source_sha256=sha256_hex(data),
                unit=tampered,
                limits=NormalizationLimits(),
            )

    def test_unknown_parser_version_refused(self):
        data = _html_bytes()
        doc = normalize_html(data.decode("utf-8"))
        unit = doc.units[0]
        stale = type(unit)(
            unit_id=unit.unit_id,
            source_id=unit.source_id,
            parser_name=unit.parser_name,
            parser_version="0.0.9",
            coordinates=unit.coordinates,
            raw_text=unit.raw_text,
            unit_kind=unit.unit_kind,
            source_role=unit.source_role,
            language=unit.language,
            quality_flags=unit.quality_flags,
            metadata=unit.metadata,
        )
        with pytest.raises(ValueError, match="parser_version"):
            replay_unit(
                data,
                source_sha256=sha256_hex(data),
                unit=stale,
                limits=NormalizationLimits(),
            )

    def test_forged_unit_text_refused_even_with_valid_id(self):
        # Same locator, honestly recomputed id, but different text: the
        # original bytes do not contain this text at that locator.
        data = _html_bytes()
        doc = normalize_html(data.decode("utf-8"))
        unit = next(u for u in doc.units if u.unit_kind == "html_heading")
        from company_wiki.document_normalization.units import build_unit

        forged = build_unit(
            source_id=unit.source_id,
            source_sha256=unit.metadata["source_sha256"],
            format_name="html",
            coordinates=unit.coordinates,
            raw_text="Fiscal year 2030 revenue reached $999 billion",
            unit_kind=unit.unit_kind,
            source_locator=unit.metadata["source_locator"],
            transform=unit.metadata["transform"],
        )
        with pytest.raises(ValueError):
            replay_unit(
                data,
                source_sha256=sha256_hex(data),
                unit=forged,
                limits=NormalizationLimits(),
            )

    def test_media_sha_cannot_replace_unit_binding(self):
        # A unit's metadata must bind its own source; pasting a valid media
        # SHA in as the source hash breaks the identity chain.
        data = _html_bytes()
        doc = normalize_html(data.decode("utf-8"))
        unit = doc.units[0]
        forged_metadata = dict(unit.metadata)
        forged_metadata["source_sha256"] = sha256_hex(b"not the source")
        forged = type(unit)(
            unit_id=unit.unit_id,
            source_id=unit.source_id,
            parser_name=unit.parser_name,
            parser_version=unit.parser_version,
            coordinates=unit.coordinates,
            raw_text=unit.raw_text,
            unit_kind=unit.unit_kind,
            source_role=unit.source_role,
            language=unit.language,
            quality_flags=unit.quality_flags,
            metadata=forged_metadata,
        )
        with pytest.raises(ValueError):
            replay_unit(
                data,
                source_sha256=sha256_hex(data),
                unit=forged,
                limits=NormalizationLimits(),
            )


class TestReplayVerificationPptx:
    def test_exact_replay_table_cell_and_paragraph(self):
        data = build_pptx(with_table=True, with_notes="note text")
        doc = normalize_pptx(data)
        assert doc.units
        for unit in doc.units:
            assert (
                replay_unit(
                    data,
                    source_sha256=sha256_hex(data),
                    unit=unit,
                    limits=NormalizationLimits(),
                )
                == unit.raw_text
            )

    def test_modified_original_refused(self):
        data = build_pptx()
        doc = normalize_pptx(data)
        modified = data[:-1] + bytes([data[-1] ^ 0xFF])
        with pytest.raises(ValueError):
            replay_unit(
                modified,
                source_sha256=sha256_hex(data),
                unit=doc.units[0],
                limits=NormalizationLimits(),
            )


class TestEvidenceSpanBridge:
    def test_units_create_valid_evidence_spans(self):
        data = _html_bytes()
        doc = normalize_html(data.decode("utf-8"))
        unit = next(u for u in doc.units if u.unit_kind == "html_table_cell")
        span = unit.to_evidence_span(
            topics=["revenue"], selection_reasons=["financial_table_cell"]
        )
        assert isinstance(span, EvidenceSpan)
        assert span.parse_status is ParseStatus.PARSED
        assert span.structured_value["normalization_schema"] == (
            "cwp-document-normalization/1"
        )
        assert span.structured_value["source_locator"].startswith("cwp-html-dom/1")
        assert span.structured_value["format"] == "html"
        assert span.coordinates.table_index == unit.metadata["table_index"]
        assert span.raw_text == unit.raw_text

    def test_evidence_span_matches_replay(self):
        data = _html_bytes()
        doc = normalize_html(data.decode("utf-8"))
        unit = doc.units[0]
        span = unit.to_evidence_span(
            topics=["overview"], selection_reasons=["first_block"]
        )
        replayed = replay_unit(
            data,
            source_sha256=sha256_hex(data),
            unit=unit,
            limits=NormalizationLimits(),
        )
        assert replayed == span.raw_text
        assert span.structured_value["text_sha256"] == sha256_hex(
            replayed.encode("utf-8")
        )


class TestUnitIdentityContract:
    def test_metadata_contract_fields(self):
        data = _html_bytes()
        doc = normalize_html(data.decode("utf-8"))
        for unit in doc.units:
            assert unit.metadata["normalization_schema"] == (
                "cwp-document-normalization/1"
            )
            assert unit.metadata["source_sha256"] == sha256_hex(data)
            assert unit.metadata["transform"]
            assert unit.metadata["source_locator"].startswith("cwp-html-dom/1")

    def test_unit_id_is_sha_urn_bound_to_locator_and_text(self):
        data = _html_bytes()
        doc = normalize_html(data.decode("utf-8"))
        for unit in doc.units:
            assert unit.unit_id.startswith("urn:company-wiki:narrative-unit:sha256:")
        # Two same-text units at different locators keep different ids.
        doc2 = normalize_html(
            html_page("<p>same words</p><div><p>same words</p></div>")
        )
        same = [u for u in doc2.units if u.raw_text == "same words"]
        assert len(same) == 2
        assert len({u.unit_id for u in same}) == 2


_DETERMINISM_SCRIPT = r"""
import hashlib, json, sys
sys.path.insert(0, {repo_src!r})
from company_wiki.document_normalization import normalize_document

payload = json.loads(sys.stdin.read())
data = bytes.fromhex(payload["data"])
mime = payload["mime"]
limits_seed_note = payload.get("note", "")
doc = normalize_document(
    data,
    source_id="urn:company-wiki:source:sha256:" + hashlib.sha256(data).hexdigest(),
    source_sha256=hashlib.sha256(data).hexdigest(),
    mime_type=mime,
    limits=None,
)
identity = hashlib.sha256(
    "\n".join(u.unit_id for u in doc.units).encode("utf-8")
).hexdigest()
assets = hashlib.sha256(
    "\n".join(
        f"{{a.asset_kind}}|{{a.slide_number}}|{{a.shape_path}}|{{a.media_sha256}}"
        for a in doc.opaque_assets
    ).encode("utf-8"),
).hexdigest() if doc.opaque_assets else "no-assets"
print(json.dumps({{"units": len(doc.units), "identity": identity, "assets": assets}}))
"""


class TestCrossProcessDeterminism:
    def _run_child(self, data: bytes, mime: str, seed: str) -> dict:
        script = _DETERMINISM_SCRIPT.format(
            repo_src=os.path.join(REPO_ROOT, "src")
        )
        payload = json.dumps(
            {"data": data.hex(), "mime": mime, "note": seed}
        )
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            input=payload,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONDONTWRITEBYTECODE": "1"},
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_html_identity_stable_across_hash_seeds_and_renames(self):
        data = _html_bytes()
        runs = [
            self._run_child(data, "text/html", seed)
            for seed in ("0", "1", "12345", "random")
        ]
        assert len({run["identity"] for run in runs}) == 1
        assert len({run["units"] for run in runs}) == 1

    def test_pptx_identity_stable_across_hash_seeds(self):
        data = build_pptx(with_table=True, with_duplicate_picture=True)
        runs = [
            self._run_child(
                data,
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation",
                seed,
            )
            for seed in ("0", "999", "random")
        ]
        assert len({run["identity"] for run in runs}) == 1
        assert len({run["assets"] for run in runs}) == 1

    def test_inprocess_repeat_is_identical(self):
        data = build_pptx(with_table=True, with_group=True)
        doc_a = normalize_pptx(data)
        doc_b = normalize_pptx(data)
        assert [u.unit_id for u in doc_a.units] == [u.unit_id for u in doc_b.units]
        assert doc_a.metadata == doc_b.metadata
        html_doc_a = normalize_html(_html_bytes().decode("utf-8"))
        html_doc_b = normalize_html(_html_bytes().decode("utf-8"))
        assert [u.unit_id for u in html_doc_a.units] == [
            u.unit_id for u in html_doc_b.units
        ]
