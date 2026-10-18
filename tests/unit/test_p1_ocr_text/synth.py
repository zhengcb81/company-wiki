"""Synthetic-fixture helpers for the P1-OCR-TEXT unit suite.

Loads the synthetic ``ImageOCRResult`` JSON fixtures from ``fixtures/`` and
rebuilds the in-memory ``ImageOCRResult`` objects the pure component consumes.
No real originals, no IO beyond reading these tiny synthetic JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path

from company_wiki.document_normalization.local_ocr import (
    ImageOCRResult,
    OCRLine,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> ImageOCRResult:
    """Rebuild one synthetic ``ImageOCRResult`` from its JSON fixture."""
    payload = json.loads((FIXTURES / f"{name}.json").read_text("utf-8"))
    lines = tuple(
        OCRLine(
            text=item["text"],
            box=tuple(float(v) for v in item["box"]),
            confidence=float(item["confidence"]),
        )
        for item in payload["lines"]
    )
    return ImageOCRResult(
        width=int(payload["width"]),
        height=int(payload["height"]),
        lines=lines,
    )


def snapshot(result: ImageOCRResult) -> dict:
    """Field-by-field snapshot used to prove the input is not mutated."""
    return {
        "width": result.width,
        "height": result.height,
        "lines": tuple(
            (line.text, tuple(line.box), line.confidence) for line in result.lines
        ),
        "region_diagnostics": result.region_diagnostics,
    }


def build_manifest(tmp_path):
    """Build a synthetic verified-PDF SourceManifest for adapter tests."""
    from company_wiki.source_contract import (
        ImmutableStatus,
        SourceManifest,
        SourceType,
    )

    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"trailer<</Root 1 0 R>>\n%%EOF\n"
    )
    root = tmp_path / "repo"
    root.mkdir()
    raw_path = root / "companies" / "TestCo" / "raw" / "fixture.pdf"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(pdf_bytes)
    manifest = SourceManifest.from_file(
        root=root,
        file_path=raw_path,
        entity_ids=("TEST:000001",),
        source_type=SourceType.COMPANY_ANNOUNCEMENT,
        published_date="2026-03-25",
        retrieved_at="2026-07-19T12:00:00Z",
        collector_name="fixture_collector",
        collector_version="1.0.0",
        mime_type="application/pdf",
    )
    assert manifest.immutable_status is ImmutableStatus.VERIFIED
    return manifest


def ocr_page(page_number: int, text: str, lines) -> dict:
    """Wrap an OCR page payload in the ``{page_number, ocr}`` page shape."""
    return {"page_number": page_number, "ocr": {"text": text, "lines": lines}}
