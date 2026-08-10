"""WU-602 RED/audit tests: dayu adapter parity + enrichment."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.adapters.dayu import DayuAdapter  # noqa: E402


def _dayu_tree(tmp_path: Path, ticker: str = "600519") -> Path:
    filing = tmp_path / "portfolio" / ticker / "filings"
    filing.mkdir(parents=True)
    primary = filing / f"{ticker}_2025_annual.pdf"
    primary.write_bytes(b"%PDF-1.4 dayu")
    primary.with_name(primary.name + ".source.json").write_text(
        json.dumps({"provider": "dayu"}), encoding="utf-8"
    )
    (filing / "meta.json").write_text(json.dumps({
        "form_type": "annual_report",
        "fiscal_year": 2025,
        "source_url": "https://provider.example/600519/2025",
        "provider": "dayu",
        "language": "zh",
        "filing_date": "2026-06-30",
    }), encoding="utf-8")
    return tmp_path / "portfolio"


def test_enumerate_with_meta_enrichment(tmp_path):
    tree = _dayu_tree(tmp_path)
    candidates = DayuAdapter().enumerate(tree)
    primary = next(c for c in candidates if c.role == "original_primary")
    assert primary.normalized["fiscal_year"] == 2025
    assert primary.normalized["form_type"] == "annual_report"
    assert primary.normalized["source_url"].startswith("https://")
    # files directly under filings/ form one group per file (v1 group-key
    # semantics): the pdf is the single original_primary, meta.json's own
    # group has no preferred file and is skipped
    assert all(c.role == "original_primary" for c in candidates)


def test_deterministic_and_read_only(tmp_path):
    tree = _dayu_tree(tmp_path)
    adapter = DayuAdapter()
    first = [(c.relative_path, c.content_sha256) for c in adapter.enumerate(tree)]
    second = [(c.relative_path, c.content_sha256) for c in adapter.enumerate(tree)]
    assert first == second
    before = {p.stat().st_mtime_ns for p in tree.rglob("*") if p.is_file()}
    adapter.enumerate(tree)
    after = {p.stat().st_mtime_ns for p in tree.rglob("*") if p.is_file()}
    assert before == after


def test_missing_meta_degrades_gracefully(tmp_path):
    tree = _dayu_tree(tmp_path)
    (tree / "600519" / "filings" / "meta.json").unlink()
    candidates = DayuAdapter().enumerate(tree)
    primary = next(c for c in candidates if c.role == "original_primary")
    assert primary.normalized == {}


def test_multiple_tickers(tmp_path):
    tree = _dayu_tree(tmp_path, "600519")
    second = tree / "1548" / "filings"
    second.mkdir(parents=True)
    (second / "1548_2024_annual.pdf").write_bytes(b"%PDF-1.4 hk")
    candidates = DayuAdapter().enumerate(tree)
    assert {c.relative_path.split("/")[0] for c in candidates} == {"600519", "1548"}
