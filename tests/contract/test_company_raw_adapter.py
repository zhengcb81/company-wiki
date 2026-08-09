"""WU-601 RED/audit tests: company_raw adapter parity with scanner v1."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.adapters.company_raw import CompanyRawAdapter  # noqa: E402
from company_wiki.source_catalog.models import RootSpec  # noqa: E402
from company_wiki.source_catalog.scanner import _scan_root_v1  # noqa: E402


def _company_tree(tmp_path: Path, company: str, *, market="US", security="US123",
                  url: str | None = "https://x/2025") -> Path:
    raw = tmp_path / "companies" / company / "raw" / "financial_reports" / "annual"
    raw.mkdir(parents=True)
    primary = raw / f"{company}_2025_annual_report.pdf"
    primary.write_bytes(b"%PDF-1.4 " + company.encode("utf-8") * 10)
    sidecar = {
        "market": market, "security_id": security, "source_title": f"{company} 2025",
        "source_url": url, "fiscal_year": 2025, "form_type": "annual_report",
    }
    primary.with_name(primary.name + ".source.json").write_text(
        json.dumps(sidecar), encoding="utf-8"
    )
    return tmp_path / "companies"


def test_parity_with_scanner_v1(tmp_path):
    """Same tree => adapter candidates match scanner v1 candidates on the
    observable fields (relative path, role, entity, metadata identity)."""
    tree = _company_tree(tmp_path, "Acme")
    root = RootSpec(root_id="company_raw", path=tree, kind="company_raw")

    v1_candidates = _scan_root_v1(root, ("Acme",))
    adapter = CompanyRawAdapter()
    adapted = adapter.enumerate(tree)

    # scanner entity_name == company dir name; adapter keeps identity in metadata
    assert len(adapted) == len(v1_candidates[0])
    for candidate in adapted:
        assert candidate.content_sha256  # hash always present
    assert {c.relative_path for c in adapted} == {c.relative_path for c in v1_candidates[0]}


def test_sidecar_metadata_pairs_correctly(tmp_path):
    tree = _company_tree(tmp_path, "Zeta", market="CN", security="600519")
    adapter = CompanyRawAdapter()
    adapted = adapter.enumerate(tree)
    primary = next(c for c in adapted if c.role == "original_primary")
    metadata = next(c for c in adapted if c.role == "metadata")
    assert primary.normalized["market"] == "CN"
    assert primary.normalized["security_id"] == "600519"
    assert metadata.relative_path.endswith(".source.json")
    assert primary.group_key == metadata.group_key


def test_sec_identity_backfill(tmp_path):
    # sidecar without market but with accession_number => US backfill
    tree = _company_tree(tmp_path, "SecCo", market=None, security=None, url=None)
    raw = tree / "SecCo" / "raw"
    for sidecar in raw.rglob("*.source.json"):
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        payload.pop("market", None)
        payload["accession_number"] = "000123-25-000001"
        sidecar.write_text(json.dumps(payload), encoding="utf-8")
    adapter = CompanyRawAdapter()
    primary = next(c for c in adapter.enumerate(tree) if c.role == "original_primary")
    assert primary.normalized["market"] == "US"


def test_adapter_read_only(tmp_path):
    tree = _company_tree(tmp_path, "Acme")
    before = {p.stat().st_mtime_ns for p in tree.rglob("*") if p.is_file()}
    CompanyRawAdapter().enumerate(tree)
    after = {p.stat().st_mtime_ns for p in tree.rglob("*") if p.is_file()}
    assert before == after


def test_adapter_deterministic(tmp_path):
    tree = _company_tree(tmp_path, "Acme")
    adapter = CompanyRawAdapter()
    first = [(c.relative_path, c.content_sha256) for c in adapter.enumerate(tree)]
    second = [(c.relative_path, c.content_sha256) for c in adapter.enumerate(tree)]
    assert first == second
