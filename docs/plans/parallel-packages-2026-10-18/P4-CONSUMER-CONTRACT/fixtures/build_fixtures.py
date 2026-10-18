"""Deterministic builder for the P4 synthetic catalog fixture.

Run from the repository root:

    python -B docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/fixtures/build_fixtures.py

The script rewrites ``catalog/`` and ``expected.json`` from the literals below so
the recorded SHA-256 values can never drift from the committed bytes.  It writes
nothing outside this card's ``fixtures/`` directory and contacts no network.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
CATALOG = HERE / "catalog"
SOURCES = CATALOG / "sources"

# --- synthetic originals -----------------------------------------------------

TEXT_BODY = (
    "P4 synthetic annual report 2025\n"
    "营业收入 120,000,000元，同比增长12%。\n"
    "单位：元\n"
)
PDF_BODY = b"%PDF-1.4\n% P4 synthetic fixture without evidence spans\n%%EOF\n"

TEXT_QUOTE = "120,000,000元"
GROWTH_QUOTE = "同比增长12%"

TEXT_SIDECAR = {
    "schema_version": "1.0",
    "canonical_entity_id": "ent-p4-synthetic",
    "display_name": "P4 Synthetic Co",
    "market": "CN",
    "security_id": "600519",
    "document_kind": "annual_report",
    "source_title": "P4 synthetic annual report 2025",
    "fiscal_year": 2025,
    "fiscal_period": None,
    "period_end": "2025-12-31",
    "published_date": None,
    "form_type": "annual",
    "provider": "synthetic",
    "provider_document_id": "p4-annual-2025-txt",
    "source_url": "https://example.invalid/p4/annual-2025.txt",
    "retrieved_at": "2026-03-01T00:00:00Z",
    "collector_name": "p4_fixture",
    "collector_version": "1.0",
}

PDF_SIDECAR = {
    "schema_version": "1.0",
    "canonical_entity_id": "ent-p4-synthetic",
    "display_name": "P4 Synthetic Co",
    "market": "CN",
    "security_id": "000001",
    "document_kind": "annual_report",
    "source_title": "P4 synthetic disclosure without spans",
    "fiscal_year": 2025,
    "fiscal_period": "FY",
    "period_end": "2025-12-31",
    "published_date": None,
    "form_type": "annual",
    "provider": "synthetic",
    "provider_document_id": "p4-disclosure-pdf",
    "source_url": "https://example.invalid/p4/disclosure.pdf",
    "retrieved_at": "2026-03-01T00:00:00Z",
    "collector_name": "p4_fixture",
    "collector_version": "1.0",
}

# The two tokens the catalog config and the tests read; ``${PROJECT_ROOT}``
# resolves to the config file's grandparent, so the very same bytes work both
# in the committed fixture and in a byte-identical copy under $TEMP.
CATALOG_CONFIG = {
    "schema_version": "1.0",
    "catalog_dir": "${PROJECT_ROOT}/catalog/state",
    "reusable_root_kinds": ["directory"],
    "roots": [
        {
            "root_id": "p4_fixture",
            "kind": "directory",
            "path": "${PROJECT_ROOT}/catalog/sources",
            "priority": 10,
            "adapter_id": "sidecar_filing_v1",
            "read_only": True,
            "reusable_for_filing": True,
        }
    ],
}

DOCUMENT_PREFIX = "urn:company-wiki:document:sha256:"
SOURCE_PREFIX = "urn:company-wiki:source:sha256:"

FACT_FIELDS = (
    "document_kind",
    "canonical_entity_id",
    "market",
    "security_id",
    "fiscal_year",
    "fiscal_period",
    "period_end",
    "published_date",
    "form_type",
    "language",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_json(path: Path, payload: object) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    write_bytes(path, (text + "\n").encode("utf-8"))


def facts_of(sidecar: dict) -> dict:
    """The ten observation ``facts`` keys, taken from the sidecar declaration."""
    return {
        "document_kind": sidecar["document_kind"],
        "canonical_entity_id": sidecar["canonical_entity_id"],
        "market": sidecar["market"],
        "security_id": sidecar["security_id"],
        "fiscal_year": sidecar["fiscal_year"],
        "fiscal_period": sidecar["fiscal_period"],
        "period_end": sidecar["period_end"],
        "published_date": sidecar["published_date"],
        "form_type": sidecar["form_type"],
        "language": sidecar.get("language"),
    }


def span_entry(text: str, quote: str, unit_tokens: list[str]) -> dict:
    char_start = text.index(quote)
    return {
        "char_start": char_start,
        "char_end": char_start + len(quote),
        "raw_text": quote,
        "unit_tokens": unit_tokens,
    }


def build() -> dict:
    text_bytes = TEXT_BODY.encode("utf-8")
    text_sha = sha256_bytes(text_bytes)
    pdf_sha = sha256_bytes(PDF_BODY)

    write_bytes(SOURCES / "annual-2025.txt", text_bytes)
    txt_sidecar = dict(TEXT_SIDECAR, content_sha256=text_sha)
    write_json(SOURCES / "annual-2025.txt.source.json", txt_sidecar)
    write_bytes(SOURCES / "disclosure.pdf", PDF_BODY)
    pdf_sidecar = dict(PDF_SIDECAR, content_sha256=pdf_sha)
    write_json(SOURCES / "disclosure.pdf.source.json", pdf_sidecar)

    config_path = CATALOG / "catalog.yaml"
    write_json(config_path, CATALOG_CONFIG)

    expectations = {
        "schema_version": "p4-fixture-expectations/1",
        "generated_by": "fixtures/build_fixtures.py",
        "catalog_config": {
            "path": "catalog/catalog.yaml",
            "sha256": sha256_bytes(config_path.read_bytes()),
        },
        "sources": [
            {
                "relative_path": "annual-2025.txt",
                "mime_type": "text/plain",
                "content_sha256": text_sha,
                "byte_size": len(text_bytes),
                "document_id": DOCUMENT_PREFIX + text_sha,
                "source_id": SOURCE_PREFIX + text_sha,
                "facts": facts_of(txt_sidecar),
                "spans": [
                    span_entry(TEXT_BODY, TEXT_QUOTE, ["元"]),
                    span_entry(TEXT_BODY, GROWTH_QUOTE, ["%"]),
                ],
            },
            {
                "relative_path": "disclosure.pdf",
                "mime_type": "application/pdf",
                "content_sha256": pdf_sha,
                "byte_size": len(PDF_BODY),
                "document_id": DOCUMENT_PREFIX + pdf_sha,
                "source_id": SOURCE_PREFIX + pdf_sha,
                "facts": facts_of(pdf_sidecar),
                "spans": [],
            },
        ],
    }
    write_json(HERE / "expected.json", expectations)
    return expectations


def main() -> int:
    expectations = build()
    print(json.dumps(
        {
            "catalog_config_sha256": expectations["catalog_config"]["sha256"],
            "sources": [
                {"path": item["relative_path"], "sha256": item["content_sha256"],
                 "bytes": item["byte_size"], "spans": len(item["spans"])}
                for item in expectations["sources"]
            ],
        },
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
