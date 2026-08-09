"""WU-403 RED/audit tests: document-level strong-key URL binding.

Same company, three periods, only one document carries a URL: any
company-name broadcast must fail.  Backfill binds URLs only via
provider_document_id / content hash / verified one-to-one immutable keys.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.url_binding import (  # noqa: E402
    bind_url,
    detect_url_broadcast,
)


def _doc(provider_document_id: str, company: str = "Acme",
         period: str = "2025", url: str | None = None) -> dict:
    doc = {
        "provider_document_id": provider_document_id,
        "company_name": company,
        "fiscal_year": period,
        "source_url": url,
    }
    return doc


def test_url_bound_via_provider_document_id_only():
    docs = [
        _doc("acc-2023", period="2023", url="https://x/2023"),
        _doc("acc-2024", period="2024"),
        _doc("acc-2025", period="2025"),
    ]
    binding = bind_url(docs)
    # URL must bind ONLY to acc-2023 (its own provider_document_id)
    assert binding["acc-2023"] == "https://x/2023"
    assert "acc-2024" not in binding
    assert "acc-2025" not in binding


def test_company_name_broadcast_detected():
    docs = [
        _doc("acc-2023", period="2023", url="https://x/2023"),
        _doc("acc-2024", period="2024"),
    ]
    # a broadcast implementation would assign the URL to both documents
    problems = detect_url_broadcast(docs, {"acc-2024": "https://x/2023"})
    assert any("acc-2024" in p for p in problems)
    assert detect_url_broadcast(docs, {"acc-2023": "https://x/2023"}) == []


def test_same_period_different_documents_no_cross_binding():
    docs = [
        _doc("acc-2025-v1", period="2025", url="https://x/2025v1"),
        _doc("acc-2025-v2", period="2025"),
    ]
    binding = bind_url(docs)
    assert binding == {"acc-2025-v1": "https://x/2025v1"}


def test_hash_key_binding_allowed():
    docs = [
        {"provider_document_id": "acc-1", "content_sha256": "h1",
         "source_url": "https://x/1"},
        {"provider_document_id": "acc-2", "content_sha256": "h2"},
    ]
    binding = bind_url(docs, key="content_sha256")
    assert binding == {"h1": "https://x/1"}


def test_no_url_no_binding():
    docs = [_doc("acc-2024"), _doc("acc-2025")]
    assert bind_url(docs) == {}


def test_company_name_key_rejected():
    """F-052 first gate: company_name is NEVER a valid binding key."""
    import pytest

    docs = [_doc("acc-2023", url="https://x/2023")]
    with pytest.raises(ValueError, match="company_name"):
        bind_url(docs, key="company_name")
