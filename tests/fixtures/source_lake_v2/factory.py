"""WU-102: build the source-lake fixture tree (synthetic bytes only).

Builds company_raw / dayu / sidecar_root / future_root trees plus a sha256
manifest.  The future_root is produced by the exact same parameterized
function as the sidecar root (same adapter/profile, different root name) —
no future_root special case may ever appear here (FIX-03).

All file contents are synthetic bytes; no real path, credential or content
ever enters the tree (FIX-01).  The builder writes only under tmp_path
(FIX-04) and is fully deterministic (FIX-02 manifest).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

PDF = b"%PDF-1.4 " + b"x" * 90
MD = b"# synthetic markdown\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _sidecar(path: Path, payload: dict) -> None:
    _write(path.with_name(path.name + ".source.json"),
           json.dumps(payload, ensure_ascii=False).encode("utf-8"))


@dataclass
class SourceLake:
    roots: dict[str, Path] = field(default_factory=dict)
    manifest: dict[str, dict] = field(default_factory=dict)


def _build_company_raw(root: Path) -> list[dict]:
    """companies/{company}/raw/financial_reports/{kind}/ + sidecar + processed."""
    entries: list[dict] = []
    for company, market, security in (
        ("Acme", "US", "US12345"),
        ("Alpha", "HK", "HK0001"),
        ("Zeta", "CN", "600519"),
    ):
        for kind, year, filename in (
            ("annual", "2025", f"{company}_2025_annual_report.pdf"),
            ("quarterly", "2025", f"{company}_2025_q1_report.pdf"),
        ):
            path = root / "companies" / company / "raw" / "financial_reports" / kind / filename
            _write(path, PDF)
            _sidecar(path, {
                "market": market,
                "security_id": security,
                "source_title": f"{company} {year} {kind} report",
                "source_url": f"https://www.example-filing.com/{security}/{year}/{kind}",
                "fiscal_year": year,
                "period_kind": kind,
            })
            entries.append({
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(PDF),
                "entity": company,
                "kind": kind,
                "period": year,
                "expected_admission": "admitted",
                "expected_canonical_location": "company_raw",
            })
        # processed artifact (synthetic markdown)
        md = root / "companies" / company / "processed" / f"{company}_2025_annual.md"
        body = MD + company.encode("utf-8")
        _write(md, body)
        entries.append({
            "path": md.relative_to(root).as_posix(),
            "sha256": _sha256(body),
            "entity": company, "kind": "markdown", "period": "2025",
            "expected_admission": "processed", "expected_canonical_location": "company_raw",
        })
    return entries


def _build_dayu(root: Path) -> list[dict]:
    """portfolio/{ticker}/filings|materials|processed/ with provider metadata."""
    entries: list[dict] = []
    for ticker, market in (("600519", "CN"), ("1548", "HK")):
        for year in ("2024", "2025"):
            path = root / ticker / "filings" / f"{ticker}_{year}_annual.pdf"
            _write(path, PDF)
            _sidecar(path, {
                "provider": "dayu",
                "market": market,
                "ticker": ticker,
                "fiscal_year": year,
                "source_url": f"https://provider.example/{ticker}/{year}",
                "accepted_at": f"{year}-06-30",
            })
            entries.append({
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(PDF),
                "entity": f"ticker-{ticker}",
                "kind": "annual",
                "period": year,
                "expected_admission": "admitted",
                "expected_canonical_location": "dayu",
            })
    return entries


def _build_sidecar_root(root: Path, root_label: str) -> list[dict]:
    """Dropbox-shaped root: files + .source.json sidecars, mixed paths,
    focus/non-focus subtrees, new/duplicate company, missing fields,
    malicious paths.  Used for BOTH sidecar_root and future_root (FIX-03)."""
    entries: list[dict] = []
    cases = [
        ("berkshire2007.pdf", PDF,
         {"market": "US", "security_id": "BRK-A", "source_title": "berkshire2007",
          "fiscal_year": "2007"},
         "admitted"),
        ("互联网/哔哩哔哩/2025年报.pdf", PDF,
         {"market": "CN", "security_id": "BILI", "source_title": "哔哩哔哩 2025 年报",
          "fiscal_year": "2025",
          "source_url": "https://www.example-filing.com/bili/2025"},
         "admitted"),
        ("重点/新能源/新公司年报.pdf", PDF,
         {"market": "CN", "security_id": "NEWCO", "source_title": "NewCo 年报",
          "fiscal_year": "2025",
          "source_url": "https://www.example-filing.com/newco/2025"},
         "admitted"),
        ("非重点/普通文档/notes.pdf", PDF,
         {"source_title": "internal notes"},
         "indexed_only"),
        ("缺字段/missing_identity.pdf", PDF,
         {"source_title": "no identity at all"},
         "indexed_only"),
        ("恶意路径/..%2fescape.pdf", PDF,
         {"source_title": "malicious", "canonical_path": "../../etc/passwd"},
         "rejected"),
    ]
    for relative, body, sidecar, admission in cases:
        path = root / relative
        _write(path, body)
        _sidecar(path, sidecar)
        entries.append({
            "path": path.relative_to(root).as_posix(),
            "sha256": _sha256(body),
            "entity": sidecar.get("security_id", "unknown"),
            "kind": "annual" if admission == "admitted" else "generic",
            "period": sidecar.get("fiscal_year", "unknown"),
            "expected_admission": admission,
            "expected_canonical_location": root_label,
        })
    return entries


def build_source_lake(tmp_path: Path) -> SourceLake:
    """Build all four roots under tmp_path; deterministic manifest."""
    if not isinstance(tmp_path, Path):
        raise TypeError("tmp_path must be pathlib.Path")
    lake = SourceLake()
    builders = {
        "company_raw": _build_company_raw,
        "dayu": _build_dayu,
        "sidecar_root": lambda root: _build_sidecar_root(root, "sidecar_root"),
        "future_root": lambda root: _build_sidecar_root(root, "future_root"),
    }
    for root_name, builder in builders.items():
        root = tmp_path / root_name
        entries = builder(root)
        lake.roots[root_name] = root
        for entry in entries:
            lake.manifest[entry["path"]] = {
                k: v for k, v in entry.items() if k != "path"
            }
    return lake
