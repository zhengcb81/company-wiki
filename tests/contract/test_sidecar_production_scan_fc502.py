"""FC-502 RED/acceptance tests: SidecarAdapter production scan.

Dropbox candidates must flow registry -> adapter -> admission -> a
normalized assertion; the adapter must NOT borrow acquisition/dayu_meta
containers.  Ordinary research docs in the same directory may still be
indexed but can never become filings.  Rescanning must not rewrite real
sidecars or modify Dropbox bytes/mtime.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _dropbox_root(tmp_path: Path) -> RootSpec:
    root_dir = tmp_path / "Dropbox" / "Stock"
    root_dir.mkdir(parents=True)
    return RootSpec(
        root_id="dropbox_stock",
        path=root_dir,
        kind="directory",
        adapter_id="sidecar_filing_v1",
        admission_profile_id="financial_evidence_v1",
        read_only=True,
        reusable_for_filing=True,
        allowed_document_kinds=("annual_report",),
        symlink_policy="reject",
        priority=30,
        cohort="dropbox-cohort",
        canonical_write_target=None,
    )


def _sidecar_for(name: str, body: bytes, **overrides) -> dict:
    payload = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-moutai",
        "display_name": "贵州茅台",
        "market": "CN",
        "security_id": "600519",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "provider": "example-filing",
        "provider_document_id": "acc-2025",
        "source_url": "https://www.example-filing.com/600519/2025",
        "content_sha256": hashlib.sha256(body).hexdigest(),
    }
    payload.update(overrides)
    return payload


# --- registry -> adapter -> admission -> normalized assertion ---------------


def test_fc502_dropbox_candidate_flows_full_chain(tmp_path):
    """A complete sidecar candidate flows registry dispatch -> adapter ->
    normalized assertion with capture_ready status (no legacy borrow)."""
    from company_wiki.source_catalog.adapter_dispatch import (
        scan_root_via_adapter,
    )
    from company_wiki.source_catalog.admission import evaluate_candidate

    root = _dropbox_root(tmp_path)
    body = b"%PDF-1.4 moutai"
    (root.path / "2025年报.pdf").write_bytes(body)
    (root.path / "2025年报.pdf.source.json").write_text(
        json.dumps(_sidecar_for("2025年报.pdf", body), ensure_ascii=False),
        encoding="utf-8",
    )
    candidates = scan_root_via_adapter(root, ())
    primary = next(c for c in candidates
                   if c.role == "original_primary")
    # the scanner-shaped _Candidate carries the adapter's normalized facts
    # in group_metadata (normalized is the adapter-layer field)
    assert primary.group_metadata.get("normalization_status") == "capture_ready"
    assert primary.group_metadata.get("provider") == "example-filing"
    # admission accepts the filing candidate
    decision = evaluate_candidate(
        primary.group_metadata,
        policy_allows_filing=True,
        profile_allows_filing=True,
        content_hash_matches=(
            primary.group_metadata.get("content_sha256")
            == hashlib.sha256(body).hexdigest()
        ),
    )
    assert decision.admitted


def test_fc502_adapter_never_borrows_legacy_containers(tmp_path):
    """The sidecar adapter must not read acquisition/dayu_meta containers —
    the normalized output is built purely from the sidecar facts."""
    from company_wiki.source_catalog.adapters.sidecar import SidecarFilingAdapter

    root = _dropbox_root(tmp_path)
    body = b"%PDF-1.4 moutai"
    (root.path / "2025年报.pdf").write_bytes(body)
    sidecar = _sidecar_for("2025年报.pdf", body)
    sidecar["acquisition"] = {"fiscal_year": 1999, "provider": "wrong-source"}
    sidecar["dayu_meta"] = {"security_id": "000001"}
    (root.path / "2025年报.pdf.source.json").write_text(
        json.dumps(sidecar, ensure_ascii=False), encoding="utf-8",
    )
    candidates = SidecarFilingAdapter().enumerate(root.path)
    primary = next(c for c in candidates if c.role == "original_primary")
    # the legacy containers are NOT borrowed into the normalized output
    # (fiscal_year is stringified by the adapter convention)
    assert str(primary.normalized.get("fiscal_year")) == "2025"
    assert primary.normalized.get("provider") == "example-filing"
    assert "acquisition" not in primary.normalized
    assert "dayu_meta" not in primary.normalized


# --- ordinary research docs: indexable but never filing ---------------------


def test_fc502_research_doc_indexable_but_not_filing(tmp_path):
    """A research PDF without a sidecar may be indexed (role
    original_primary with empty normalized) but admission must reject it
    as a filing."""
    from company_wiki.source_catalog.adapter_dispatch import (
        scan_root_via_adapter,
    )
    from company_wiki.source_catalog.admission import evaluate_candidate

    root = _dropbox_root(tmp_path)
    (root.path / "某券商_行业研究.pdf").write_bytes(b"%PDF-1.4 research")
    candidates = scan_root_via_adapter(root, ())
    research = next(c for c in candidates
                    if c.relative_path.endswith("研究.pdf"))
    assert research.group_metadata == {}  # no filing evidence
    # admission rejects the empty-evidence candidate as a filing
    decision = evaluate_candidate(
        research.group_metadata,
        policy_allows_filing=True,
        profile_allows_filing=True,
        content_hash_matches=True,
    )
    assert not decision.admitted


# --- rescan never rewrites real sidecars or modifies bytes/mtime ------------


def test_fc502_rescan_does_not_modify_dropbox(tmp_path):
    """Two scans over the same root must leave the real files (bytes and
    mtime) untouched."""
    from company_wiki.source_catalog.adapter_dispatch import (
        scan_root_via_adapter,
    )

    root = _dropbox_root(tmp_path)
    body = b"%PDF-1.4 moutai"
    pdf_path = root.path / "2025年报.pdf"
    pdf_path.write_bytes(body)
    sidecar_path = root.path / "2025年报.pdf.source.json"
    sidecar_path.write_text(
        json.dumps(_sidecar_for("2025年报.pdf", body), ensure_ascii=False),
        encoding="utf-8",
    )
    time.sleep(0.05)  # ensure mtime resolution separates the writes
    before = {
        "pdf_bytes": pdf_path.read_bytes(),
        "pdf_mtime": pdf_path.stat().st_mtime_ns,
        "sidecar_bytes": sidecar_path.read_bytes(),
        "sidecar_mtime": sidecar_path.stat().st_mtime_ns,
    }
    scan_root_via_adapter(root, ())
    scan_root_via_adapter(root, ())
    after = {
        "pdf_bytes": pdf_path.read_bytes(),
        "pdf_mtime": pdf_path.stat().st_mtime_ns,
        "sidecar_bytes": sidecar_path.read_bytes(),
        "sidecar_mtime": sidecar_path.stat().st_mtime_ns,
    }
    assert before == after, "rescan modified Dropbox files"
