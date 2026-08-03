"""Spike (Phase 1): promote one dayu-portfolio doc into company_raw via import_staged.

Throwaway proof that "copy portfolio PDF -> staging -> import_staged -> resolve REUSED_EXACT"
works end-to-end. This is the prototype for the future `import-portfolio` CLI.

Run from company-wiki root:
    python docs/plans/portfolio-reuse-fix/spike_promote.py
"""
from __future__ import annotations
import hashlib
import json
import shutil
import sys
from pathlib import Path

# --- company-wiki import path ---
CW_ROOT = Path(r"C:\Users\郑曾波\Projects\company-wiki")
sys.path.insert(0, str(CW_ROOT / "src"))

from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.acquisition_config import load_acquisition_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
from company_wiki.source_catalog.resolver import SourceRequest, SourceResolver, ResolutionStatus
from company_wiki.source_catalog.acquisition import DownloadCandidate, DownloadReceipt

PORTFOLIO = CW_ROOT.parent / "dayu-agent" / "workspace" / "portfolio"
DOC_DIR = PORTFOLIO / "3896" / "filings" / "fil_cn_48ec0d41eb244001f0f3795438c351495c196ada"
PDF = DOC_DIR / "fil_cn_48ec0d41eb244001f0f3795438c351495c196ada.pdf"
# Rich dayu provenance lives in meta.json; the .pdf.source.json sidecar is only a
# minimal {market, security_id, source_title} marker.
SRC = DOC_DIR / "meta.json"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    meta = json.loads(SRC.read_text(encoding="utf-8"))
    print(f"[spike] portfolio source_url: {meta.get('source_url')}")
    print(f"[spike] portfolio pdf_sha256: {meta.get('pdf_sha256')}")

    byte_size = PDF.stat().st_size
    content_sha = _sha256(PDF)
    assert content_sha == meta["pdf_sha256"], "portfolio PDF bytes changed!"
    assert content_sha == "efe2ccd923b744eb69166aebf5f9b32ab7560efe3f6c44f2c6bcf4672fec1fa8"

    config = load_catalog_config(CW_ROOT / "config" / "source_catalog.yaml", project_root=CW_ROOT)
    acq = load_acquisition_config(CW_ROOT / "config" / "source_acquisition.yaml", project_root=CW_ROOT)
    staging_root = Path(acq.staging_root)
    staging_root.mkdir(parents=True, exist_ok=True)
    catalog = SourceCatalog(config)
    writer = CanonicalSourceWriter(catalog, staging_root=staging_root)

    # --- build request (entity/market/security_id must be self-consistent) ---
    request = SourceRequest(
        entity=meta["company_name"],          # 金山雲
        market="HK",
        security_id=meta["ticker"],           # 3896
        document_kind="annual_report",
        form_type=meta.get("form_type"),      # FY
        fiscal_year=int(meta["fiscal_year"]), # 2025
        fiscal_period=meta.get("fiscal_period"),
        language=meta.get("source_language"),
        provider=meta.get("source_provider"), # hkexnews
        provider_document_id=str(meta.get("source_id")),  # 12118317
        as_of_date="2026-08-02",
        allow_download=False,
    )

    # --- stage the portfolio PDF into staging_root ---
    staged = staging_root / f"spike-{request.request_id.rsplit(':',1)[-1][:16]}.pdf"
    shutil.copyfile(PDF, staged)
    print(f"[spike] staged -> {staged} ({byte_size} bytes)")

    # --- synthesize candidate + receipt from portfolio provenance ---
    retrieved = (meta.get("first_ingested_at") or "2026-06-04T20:51:46+00:00")[:19] + "Z"
    candidate = DownloadCandidate(
        candidate_id="portfolio:" + meta["document_id"],
        provider=meta["source_provider"],
        provider_document_id=str(meta["source_id"]),
        market="HK",
        entity=meta["company_name"],
        title=meta.get("source_title") or "2025 年度報告",
        source_url=meta["source_url"],
        document_kind="annual_report",
        filing_date=meta["filing_date"],
        fiscal_year=int(meta["fiscal_year"]),
        form_type=meta.get("form_type"),
        fiscal_period=meta.get("fiscal_period"),
        language=meta.get("source_language"),
        amended=False,
    )
    receipt = DownloadReceipt(
        candidate_id=candidate.candidate_id,
        provider=candidate.provider,
        provider_document_id=candidate.provider_document_id,
        source_url=candidate.source_url,
        staged_path=str(staged),
        content_sha256=content_sha,
        byte_size=byte_size,
        mime_type="application/pdf",
        retrieved_at=retrieved,
        http_status=200,
        adapter_name="dayu-portfolio-promoter",
        adapter_version="1.0.0",
    )

    # --- commit through the validated single writer ---
    print("[spike] calling import_staged ...")
    result = writer.import_staged(request, candidate, receipt)
    print(f"[spike] import_staged status = {result.status.value}")
    print(f"[spike] canonical_path       = {result.canonical_path}")
    print(f"[spike] provenance_path      = {result.provenance_path}")

    # --- resolve: expect REUSED_EXACT, capture_ready, inside companies/ ---
    resolution = SourceResolver(catalog).resolve(request)
    status_val = resolution.status.value if hasattr(resolution.status, "value") else str(resolution.status)
    print(f"[spike] resolve status       = {status_val}")
    if resolution.matches:
        h = resolution.matches[0]
        print(f"[spike] handle.capture_ready = {h.capture_ready}")
        print(f"[spike] handle.canonical_path= {h.canonical_path}")
        print(f"[spike] handle.snapshot_sha256= {h.snapshot_sha256}")
        print(f"[spike] handle.https_url     = {h.https_url}")
    else:
        print("[spike] NO MATCHES returned")
    print(f"[spike] debug_trace (tail):\n  " + "\n  ".join(resolution.debug_trace[-12:]))

    # cleanup stray staged file if import left it
    if staged.exists():
        staged.unlink()

    ok = (
        resolution.status is ResolutionStatus.REUSED_EXACT
        and resolution.matches
        and resolution.matches[0].capture_ready
        and "companies" in str(resolution.matches[0].canonical_path).replace("\\", "/")
    )
    print(f"\n[spike] RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
