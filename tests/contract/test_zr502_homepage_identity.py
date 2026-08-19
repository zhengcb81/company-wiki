"""ZR-502 acceptance tests: sidecar/primary role separation closure +
homepage identity verification.

  C1  role separation closure: a ``.source.json`` file never becomes an
      annual/broker document — standalone sidecars produce no candidate
      and no filing request can match a sidecar file.
  C2  homepage identity verification: ``assess_homepage_identity`` is a
      pure function over the first-page text + declared title/publisher —
      consistent / contradiction / unverifiable (no fabricated pass).
  C3  contradiction fail/review: normalize wiring — a first page that
      contradicts the declared title/publisher yields
      ``homepage_identity=contradiction`` in the normalized frontmatter
      plus the ``homepage_identity_contradiction`` quality flag; a
      matching page yields consistent; no page text stays unverifiable.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.homepage_identity import (  # noqa: E402
    assess_homepage_identity,
    homepage_identity_quality_flag,
)
from company_wiki.source_catalog.normalizer import (  # noqa: E402
    _Normalized,
    _frontmatter,
)


# ---------------------------------------------------------------------------
# C1 — sidecar/primary role separation closure
# ---------------------------------------------------------------------------


def _sidecar_tree(tmp_path: Path, *, sidecar: dict | None, orphan_sidecar: bool = False):
    from company_wiki.source_catalog.adapters.sidecar import SidecarFilingAdapter

    root = tmp_path / "stock"
    root.mkdir()
    body = b"%PDF-1.4 broker"
    (root / "report.pdf").write_bytes(body)
    if sidecar is not None:
        payload = dict(sidecar)
        payload.setdefault("content_sha256", hashlib.sha256(body).hexdigest())
        (root / "report.pdf.source.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    if orphan_sidecar:
        (root / "orphan.pdf.source.json").write_text(
            json.dumps({
                "schema_version": "1.0",
                "canonical_entity_id": "ent-x",
                "market": "CN",
                "security_id": "600000",
                "document_kind": "annual_report",
                "content_sha256": "0" * 64,
            }, ensure_ascii=False),
            encoding="utf-8",
        )
    return root, SidecarFilingAdapter()


def test_c1_standalone_sidecar_never_a_candidate(tmp_path):
    """An orphan ``.source.json`` produces NO candidate — it can never be a
    document (annual or broker).  The paired primary (if any) is the only
    original_primary."""
    root, adapter = _sidecar_tree(tmp_path, sidecar=None, orphan_sidecar=True)
    candidates = adapter.enumerate(root)
    assert all(not c.relative_path.endswith(".source.json") for c in candidates)
    assert all(
        c.role != "original_primary" or not c.relative_path.endswith(".source.json")
        for c in candidates
    )


def test_c1_filing_request_never_matches_sidecar_file(tmp_path):
    """End-to-end: a filing request cannot resolve to a sidecar file — only
    the paired primary document is indexed."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
    from company_wiki.source_catalog.resolver import (
        ResolutionStatus,
        SourceRequest,
        SourceResolver,
    )

    body = b"%PDF-1.4 annual"
    project = tmp_path / "project"
    raw = project / "companies" / "Acme" / "raw" / "financial_reports" / "annual"
    raw.mkdir(parents=True)
    (raw / "2025.pdf").write_bytes(body)
    (raw / "2025.pdf.source.json").write_text(json.dumps({
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "CN",
        "security_id": "600519",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "provider": "cninfo",
        "provider_document_id": "acc-2025",
        "filing_date": "2026-04-30",
        "source_url": "https://static.cninfo.com.cn/x/2025.pdf",
        "content_sha256": hashlib.sha256(body).hexdigest(),
    }, ensure_ascii=False), encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", project / "companies", "company_raw",
                            priority=10, adapter_id="company_raw_v1",
                            read_only=False, reusable_for_filing=True,
                            canonical_write_target="companies"),),
        )
    )
    catalog.scan()
    result = SourceResolver(catalog).resolve(
        SourceRequest(
            entity="Acme",
            market="CN",
            security_id="600519",
            document_kind="annual_report",
            fiscal_year=2025,
            provider="cninfo",
            provider_document_id="acc-2025",
            as_of_date="2026-08-01",
            mode="exact",
        )
    )
    assert result.status is ResolutionStatus.REUSED_EXACT
    assert result.matches[0].canonical_path.endswith("2025.pdf")
    # the sidecar file itself is never a match
    assert not result.matches[0].canonical_path.endswith(".source.json")


# ---------------------------------------------------------------------------
# C2 — homepage identity pure function
# ---------------------------------------------------------------------------


def test_c2_consistent_on_declared_title_token():
    verdict = assess_homepage_identity(
        "中信证券 紫金矿业集团股份有限公司 深度报告",
        title="紫金矿业集团股份有限公司2025年年度报告",
        publisher="中信证券",
    )
    assert verdict["verdict"] == "consistent"
    assert "matched_tokens" in verdict["evidence"]


def test_c2_consistent_on_publisher_token():
    verdict = assess_homepage_identity(
        "中信证券研究部 2026-03-01",
        title="某公司深度报告",
        publisher="中信证券",
    )
    assert verdict["verdict"] == "consistent"


def test_c2_contradiction_on_foreign_cover():
    """The first page clearly names a DIFFERENT company than declared —
    fail/review."""
    verdict = assess_homepage_identity(
        "陕西煤业股份有限公司 2025年年度报告",
        title="紫金矿业集团股份有限公司2025年年度报告",
        publisher="cninfo",
    )
    assert verdict["verdict"] == "contradiction"
    assert homepage_identity_quality_flag(verdict["verdict"]) == (
        "homepage_identity_contradiction"
    )


def test_c2_unverifiable_no_text():
    verdict = assess_homepage_identity(
        None,
        title="紫金矿业2025年年度报告",
        publisher="cninfo",
    )
    assert verdict["verdict"] == "unverifiable"
    assert homepage_identity_quality_flag(verdict["verdict"]) is None


def test_c2_unverifiable_no_cover_framing():
    verdict = assess_homepage_identity(
        "附件：财务报表附注",
        title="紫金矿业2025年年度报告",
        publisher="cninfo",
    )
    # page exists but carries no strong cover/report framing and no
    # declared identity value -> unverifiable (never a fabricated fail or
    # pass)
    assert verdict["verdict"] == "unverifiable"


# ---------------------------------------------------------------------------
# C3 — normalize wiring: contradiction fail/review, consistent pass
# ---------------------------------------------------------------------------


def _doc(title: str, publisher: str | None) -> dict:
    metadata = {"acquisition": {"publisher": publisher}} if publisher else {}
    return {
        "document_id": "doc-1",
        "primary_source_id": "src-1",
        "content_sha256": "a" * 64,
        "title": title,
        "document_kind": "broker_research",
        "published_date": "2026-03-01",
        "metadata_json": metadata,
    }


def _norm(first_page_text: str | None) -> _Normalized:
    return _Normalized(
        body="# b",
        parser_results=(),
        parser_name="pdf_page_aware_core",
        parser_version="1.0.0",
        status="completed",
        quality_flags=(),
        error=None,
        page_count=3,
        first_page_text=first_page_text,
    )


def test_c3_contradiction_flags_frontmatter_and_quality():
    import yaml

    frontmatter = _frontmatter(
        _doc("紫金矿业集团股份有限公司2025年年度报告", "cninfo"),
        _norm("陕西煤业股份有限公司 2025年年度报告"),
    )
    payload = yaml.safe_load(frontmatter.split("---\n", 2)[1])
    assert payload["homepage_identity"]["verdict"] == "contradiction"
    assert "homepage_identity_contradiction" in payload["quality_flags"]


def test_c3_consistent_no_flag():
    import yaml

    frontmatter = _frontmatter(
        _doc("紫金矿业集团股份有限公司2025年年度报告", "cninfo"),
        _norm("紫金矿业集团股份有限公司 2025年年度报告"),
    )
    payload = yaml.safe_load(frontmatter.split("---\n", 2)[1])
    assert payload["homepage_identity"]["verdict"] == "consistent"
    assert "homepage_identity_contradiction" not in payload["quality_flags"]


def test_c3_unverifiable_no_flag_no_fabrication():
    import yaml

    frontmatter = _frontmatter(
        _doc("紫金矿业集团股份有限公司2025年年度报告", "cninfo"),
        _norm(None),
    )
    payload = yaml.safe_load(frontmatter.split("---\n", 2)[1])
    assert payload["homepage_identity"]["verdict"] == "unverifiable"
    assert "homepage_identity_contradiction" not in payload["quality_flags"]


def test_c3_page_count_still_present_alongside_identity():
    """The ZR-501 contract field coexists with the new identity verdict."""
    import yaml

    frontmatter = _frontmatter(
        _doc("紫金矿业集团股份有限公司2025年年度报告", "cninfo"),
        _norm("紫金矿业集团股份有限公司 2025年年度报告"),
    )
    payload = yaml.safe_load(frontmatter.split("---\n", 2)[1])
    assert payload["page_count"] == 3
    assert payload["homepage_identity"]["verdict"] == "consistent"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
