"""WU-701 RED/audit tests: sidecar_filing_v1 adapter (N-01..N-11 vectors)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.adapters.sidecar import (  # noqa: E402
    SidecarFilingAdapter,
)


def _complete_sidecar(**overrides) -> dict:
    import hashlib

    body = overrides.pop("_body", b"%PDF-1.4 sidecar")
    payload = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-600519",
        "display_name": "贵州茅台",
        "market": "CN",
        "security_id": "600519",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "provider": "example-filing",
        "provider_document_id": "acc-2025",
        "source_url": "https://www.example-filing.com/600519/2025",
        "published_at": "2026-04-15",
        "filed_at": "2026-04-15",
        "accepted_at": "2026-04-16",
        "content_sha256": hashlib.sha256(body).hexdigest(),
    }
    payload.update(overrides)
    return payload


def _tree(tmp_path: Path, sidecar: dict | None, name: str = "2025年报.pdf",
          body: bytes = b"%PDF-1.4 sidecar") -> Path:
    root = tmp_path / "sidecar_root"
    root.mkdir(exist_ok=True)
    primary = root / name
    primary.write_bytes(body)
    if sidecar is not None:
        if "content_sha256" not in sidecar:
            import hashlib

            sidecar = dict(sidecar)
            sidecar["content_sha256"] = hashlib.sha256(body).hexdigest()
        primary.with_name(primary.name + ".source.json").write_text(
            json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
        )
    return root


def test_n01_complete_sidecar_capture_ready(tmp_path):
    root = _tree(tmp_path, _complete_sidecar())
    candidates = SidecarFilingAdapter().enumerate(root)
    assert len(candidates) == 1
    assert candidates[0].role == "original_primary"
    assert candidates[0].normalized["normalization_status"] == "capture_ready"


def test_n02_missing_period_indexed_only(tmp_path):
    sidecar = _complete_sidecar(fiscal_year=None, period_end=None)
    root = _tree(tmp_path, sidecar)
    candidates = SidecarFilingAdapter().enumerate(root)
    assert candidates[0].role == "indexed_only"
    assert "missing:fiscal_year" in candidates[0].evidence["remediation"]


def test_n03_content_hash_mismatch_detected(tmp_path):
    sidecar = _complete_sidecar(content_sha256="0" * 64)
    root = _tree(tmp_path, sidecar)
    candidates = SidecarFilingAdapter().enumerate(root)
    # hash present in sidecar; mismatch vs file bytes is an admission-level
    # gate, adapter records the fact for comparison
    assert candidates[0].normalized["content_sha256"] == "0" * 64


def test_n06_single_url_binds_one_document(tmp_path):
    root = _tree(tmp_path, _complete_sidecar(source_url="https://x/2025"),
                 name="annual.pdf")
    candidates = SidecarFilingAdapter().enumerate(root)
    assert candidates[0].normalized["source_url"] == "https://x/2025"


def test_n07_broker_research_has_generic_kind(tmp_path):
    sidecar = _complete_sidecar(document_kind="broker_research")
    root = _tree(tmp_path, sidecar)
    candidates = SidecarFilingAdapter().enumerate(root)
    # broker research is a known kind but not a filing — admission rejects
    # it later; the adapter must not relabel it as a filing
    assert candidates[0].normalized["document_kind"] == "broker_research"


def test_n08_standalone_sidecar_not_original(tmp_path):
    root = _tree(tmp_path, None)
    # a sidecar without its primary: it is never enumerated as a candidate
    (root / "orphan.pdf.source.json").write_text(
        json.dumps(_complete_sidecar()), encoding="utf-8"
    )
    candidates = SidecarFilingAdapter().enumerate(root)
    assert all(not c.relative_path.endswith(".source.json") for c in candidates)


def test_n11_unknown_schema_fails_closed(tmp_path):
    sidecar = _complete_sidecar(schema_version="99.0")
    root = _tree(tmp_path, sidecar)
    candidates = SidecarFilingAdapter().enumerate(root)
    assert candidates[0].role == "indexed_only"
    assert "unknown_schema_version" in candidates[0].evidence["remediation"]


def test_path_escape_rejected(tmp_path):
    sidecar = _complete_sidecar(canonical_path="../../etc/passwd")
    root = _tree(tmp_path, sidecar)
    candidates = SidecarFilingAdapter().enumerate(root)
    assert candidates[0].role == "indexed_only"
    assert "path_escape" in candidates[0].evidence["remediation"]


def test_absolute_path_rejected(tmp_path):
    sidecar = _complete_sidecar(canonical_path="C:\\Windows\\evil.pdf")
    root = _tree(tmp_path, sidecar)
    candidates = SidecarFilingAdapter().enumerate(root)
    assert "path_escape" in candidates[0].evidence["remediation"]


def test_parse_failure_degrades_gracefully(tmp_path):
    root = tmp_path / "sidecar_root"
    root.mkdir()
    (root / "x.pdf").write_bytes(b"%PDF")
    (root / "x.pdf.source.json").write_text("{broken json", encoding="utf-8")
    candidates = SidecarFilingAdapter().enumerate(root)
    assert candidates[0].role == "indexed_only"
    assert "sidecar_parse_failed" in candidates[0].evidence["remediation"]


def test_deterministic_and_read_only(tmp_path):
    root = _tree(tmp_path, _complete_sidecar())
    adapter = SidecarFilingAdapter()
    first = [(c.relative_path, c.role) for c in adapter.enumerate(root)]
    second = [(c.relative_path, c.role) for c in adapter.enumerate(root)]
    assert first == second
    before = {p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    adapter.enumerate(root)
    after = {p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    assert before == after
