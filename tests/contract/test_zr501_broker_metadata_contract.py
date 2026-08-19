"""ZR-501 acceptance tests: broker_research document / admission /
metadata contract (publisher / authors / date / entities / security IDs /
page count; filename is ONLY a proposal).

  C1  filename is only a proposal: a broker_research file WITHOUT a sidecar
      (filename carrying date/publisher patterns) classifies as
      broker_research but carries NO invented metadata facts — published_date
      stays None, publisher stays absent; a sidecar's facts win over the
      filename.
  C2  metadata contract lands additively: sidecar publisher/authors/
      security_ids pass through `_normalized_from_sidecar` into the
      normalized metadata (then documents.metadata_json); the page-aware
      PDF parser's page_count lands in the normalized artifact frontmatter
      (None stays honest).
  C3  admission closure: a metadata-COMPLETE broker_research (all four
      contract fields present) is still NEVER admitted for filing —
      evaluate_candidate rejects with non_filing_kind; an annual_report
      filing request cannot be satisfied by it.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.adapters.sidecar import (  # noqa: E402
    SidecarFilingAdapter,
)


def _broker_sidecar(**overrides) -> dict:
    payload = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "CN",
        "security_id": "600519",
        "document_kind": "broker_research",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "published_at": "2026-03-01",
        "publisher": "中信证券",
        "authors": ["张三", "李四"],
        "security_ids": ["600519", "000858"],
        "provider": "cninfo",
        "provider_document_id": "acc-2025",
        "content_sha256": hashlib.sha256(b"x").hexdigest(),
    }
    payload.update(overrides)
    return payload


def _tree(tmp_path: Path, files: list[tuple[str, dict | None]]) -> Path:
    root = tmp_path / "stock"
    root.mkdir()
    for name, sidecar in files:
        primary = root / name
        primary.write_bytes(b"%PDF-1.4 broker")  # stable bytes (hash-pinned)
        if sidecar is not None:
            primary.with_name(primary.name + ".source.json").write_text(
                json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
            )
    return root


# ---------------------------------------------------------------------------
# C1 — filename is only a proposal
# ---------------------------------------------------------------------------


def test_c1_no_sidecar_filename_only_proposal(tmp_path):
    """A broker-research file without a sidecar — filename carrying date +
    publisher patterns — is surfaced with the missing-sidecar remediation
    and NO invented metadata facts (published_date stays None, no
    publisher)."""
    tree = _tree(tmp_path, [("20190311-阿里研究院-从连接到赋能.pdf", None)])
    candidates = SidecarFilingAdapter().enumerate(tree)
    primary = next(c for c in candidates)
    assert primary.role == "original_primary"
    assert "missing_sidecar" in primary.evidence.get("remediation", "")
    assert primary.normalized == {}  # nothing invented from the filename


def test_c1_sidecar_facts_win_over_filename(tmp_path):
    """With a sidecar, the sidecar's facts are the metadata — the filename
    is not consulted as a fact source."""
    body = b"%PDF-1.4 broker"
    sidecar = _broker_sidecar(content_sha256=hashlib.sha256(body).hexdigest())
    tree = _tree(tmp_path, [("2025年报.pdf", sidecar)])
    candidates = SidecarFilingAdapter().enumerate(tree)
    primary = next(c for c in candidates)
    assert primary.role == "original_primary"
    normalized = primary.normalized
    assert normalized["document_kind"] == "broker_research"
    assert normalized["publisher"] == "中信证券"
    assert normalized["published_at"] == "2026-03-01"
    # filename said "年报" but the sidecar is authoritative: broker_research
    assert normalized["security_id"] == "600519"


def test_c1_no_sidecar_published_date_never_invented(tmp_path):
    """DBX-04 extension: a broker report named 年报 without a sidecar must
    never surface a published_date from the filename (no fact invention)."""
    tree = _tree(tmp_path, [("某某证券_2025年报.pdf", None)])
    candidates = SidecarFilingAdapter().enumerate(tree)
    primary = next(c for c in candidates)
    assert primary.normalized.get("published_at") is None


# ---------------------------------------------------------------------------
# C2 — metadata contract lands additively
# ---------------------------------------------------------------------------


def test_c2_sidecar_contract_fields_passthrough(tmp_path):
    """publisher/authors/security_ids from the sidecar land in the
    normalized metadata (additive; absent keys stay absent)."""
    body = b"%PDF-1.4 broker"
    sidecar = _broker_sidecar(content_sha256=hashlib.sha256(body).hexdigest())
    tree = _tree(tmp_path, [("report.pdf", sidecar)])
    candidates = SidecarFilingAdapter().enumerate(tree)
    normalized = next(c for c in candidates).normalized
    assert normalized["publisher"] == "中信证券"
    assert normalized["authors"] == ("张三", "李四")
    assert normalized["security_ids"] == ("600519", "000858")


def test_c2_absent_contract_fields_stay_absent(tmp_path):
    """A sidecar without the broker contract fields does not gain null
    noise keys — absent stays absent (no fabrication)."""
    body = b"%PDF-1.4 broker"
    sidecar = {
        "schema_version": "1.0",
        "document_kind": "broker_research",
        "content_sha256": hashlib.sha256(body).hexdigest(),
    }
    tree = _tree(tmp_path, [("report.pdf", sidecar)])
    candidates = SidecarFilingAdapter().enumerate(tree)
    normalized = next(c for c in candidates).normalized
    assert normalized.get("publisher") is None
    assert normalized.get("authors") == ()
    assert normalized.get("security_ids") == ()


def test_c2_page_count_lands_in_normalized_artifact():
    """The page-aware parser's page_count reaches the normalized artifact
    frontmatter (ZR-501 metadata contract): a 3-page result yields 3."""
    import yaml

    from company_wiki.source_catalog import normalizer as module

    document = {
        "document_id": "doc-1",
        "primary_source_id": "src-1",
        "content_sha256": "a" * 64,
        "title": "t",
        "document_kind": "broker_research",
        "published_date": "2026-03-01",
    }

    class _Norm:
        status = "completed"
        parser_name = "pdf_page_aware_core"
        parser_version = "1.0.0"
        quality_flags = ()
        page_count = 3

    frontmatter = module._frontmatter(document, _Norm())
    payload = yaml.safe_load(frontmatter.split("---\n", 2)[1])
    assert payload["page_count"] == 3
    assert payload["document_kind"] == "broker_research"


def test_c2_page_count_none_when_unknown():
    """A non-PDF normalized path keeps page_count null/honest (no
    fabricated count)."""
    import yaml

    from company_wiki.source_catalog import normalizer as module

    document = {
        "document_id": "doc-1",
        "primary_source_id": "src-1",
        "content_sha256": "a" * 64,
        "title": "t",
        "document_kind": "broker_research",
        "published_date": "2026-03-01",
    }

    class _Norm:
        status = "completed"
        parser_name = "fixture"
        parser_version = "1.0.0"
        quality_flags = ()
        page_count = None

    frontmatter = module._frontmatter(document, _Norm())
    payload = yaml.safe_load(frontmatter.split("---\n", 2)[1])
    assert payload["page_count"] is None


# ---------------------------------------------------------------------------
# C3 — admission closure: complete broker metadata never satisfies filing
# ---------------------------------------------------------------------------


def test_c3_metadata_complete_broker_still_non_filing(tmp_path):
    """Even with ALL contract fields present, broker_research is never
    admitted for filing (non_filing_kind)."""
    from company_wiki.source_catalog.adapters.interface import NormalizedCandidate
    from company_wiki.source_catalog.admission import (
        evaluate_candidate,
    )

    body = b"%PDF-1.4 broker"
    sidecar = _broker_sidecar(content_sha256=hashlib.sha256(body).hexdigest())
    tree = _tree(tmp_path, [("report.pdf", sidecar)])
    candidates = SidecarFilingAdapter().enumerate(tree)
    primary = next(c for c in candidates)
    assert isinstance(primary, NormalizedCandidate)
    decision = evaluate_candidate(
        primary.normalized,
        policy_allows_filing=True,
        profile_allows_filing=False,  # generic profile: broker not filing
        content_hash_matches=True,
    )
    assert not decision.admitted
    assert "non_filing_kind" in decision.reason


def test_c3_filing_request_cannot_be_satisfied_by_broker(tmp_path):
    """End-to-end: an annual_report filing request must never resolve to a
    broker_research document, even when its metadata is complete."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
    from company_wiki.source_catalog.resolver import (
        ResolutionStatus,
        SourceRequest,
        SourceResolver,
    )

    body = b"%PDF-1.4 broker"
    project = tmp_path / "project"
    raw = project / "companies" / "Acme" / "raw" / "broker_reports"
    raw.mkdir(parents=True)
    (raw / "report.pdf").write_bytes(body)
    (raw / "report.pdf.source.json").write_text(
        json.dumps(
            _broker_sidecar(content_sha256=hashlib.sha256(body).hexdigest()),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec(
                    "company_raw",
                    project / "companies",
                    "company_raw",
                    priority=10,
                    adapter_id="company_raw_v1",
                    read_only=False,
                    reusable_for_filing=True,
                    canonical_write_target="companies",
                ),
            ),
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
            as_of_date="2026-08-01",
            mode="exact",
        )
    )
    assert result.status is not ResolutionStatus.REUSED_EXACT
    assert result.status is ResolutionStatus.MISSING
    # and the broker document IS indexed (as broker_research)
    row = catalog.store.fetchone(
        "SELECT document_kind FROM documents WHERE document_kind='broker_research'"
    )
    assert row is not None
