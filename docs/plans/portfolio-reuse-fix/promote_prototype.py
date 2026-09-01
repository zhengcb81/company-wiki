"""Phase 2 prototype: promote a dayu-portfolio document to company_raw.

Full flow proven by Phase 1 spike, parameterized + identity-resolved:
  1. Resolve identity (company_query -> canonical market/security_id/entity) —
     same SecurityIdentityResolver the CLI and filing-fetch use. This makes
     security_id canonical (e.g. "03896", not the portfolio's "3896").
  2. Stage the portfolio PDF into staging_root.
  3. Synthesize DownloadCandidate + DownloadReceipt from the portfolio meta.json.
  4. import_staged() -> canonical file under companies/<entity>/raw/... +
     provenance sidecar (now with top-level market) + rescan.
  5. Resolve: expect REUSED_EXACT + capture_ready.

Usage:
  python docs/plans/portfolio-reuse-fix/promote_prototype.py \
      --company-query "金山云" --market HK --doc-id fil_cn_4827932faaa0b289e04e4929f265082c7eee45d2
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

CW_ROOT = Path(r"C:\Users\郑曾波\Projects\company-wiki")
sys.path.insert(0, str(CW_ROOT / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from company_wiki.source_catalog.config import load_catalog_config  # noqa: E402
from company_wiki.source_catalog.acquisition_config import load_acquisition_config  # noqa: E402
from company_wiki.source_catalog.service import SourceCatalog  # noqa: E402
from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter  # noqa: E402
from company_wiki.source_catalog.resolver import (  # noqa: E402
    SourceRequest, SourceResolver, ResolutionStatus,
)
from company_wiki.source_catalog.acquisition import DownloadCandidate, DownloadReceipt  # noqa: E402
from company_wiki.source_catalog.security_identity import (  # noqa: E402
    SecurityIdentityResolver, SecurityMasterStore, load_identity_master,
    IdentityStatus, SecurityIdentityResolutionError,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--company-query", default="金山云")
    ap.add_argument("--market", default="HK")
    ap.add_argument("--doc-id", required=True)
    ap.add_argument("--as-of-date", default="2026-08-02")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    portfolio = CW_ROOT.parent / "dayu-agent" / "workspace" / "portfolio"
    doc_dir = next((p for p in portfolio.rglob("meta.json")
                    if p.parent.name == args.doc_id), None)
    if doc_dir is None:
        print(f"ERROR: portfolio doc {args.doc_id} not found")
        return 2
    doc_dir = doc_dir.parent
    meta = json.loads((doc_dir / "meta.json").read_text(encoding="utf-8"))
    pdf = doc_dir / f"{args.doc_id}.pdf"
    assert pdf.is_file(), f"PDF missing: {pdf}"

    # --- 1. resolve identity (canonical market/security_id/entity) ---
    store = SecurityMasterStore(CW_ROOT / ".source_catalog" / "security_master")
    result = SecurityIdentityResolver(
        load_identity_master(store, market=args.market)
    ).identify(args.company_query, market=args.market)
    if result.status is not IdentityStatus.RESOLVED or result.resolved is None:
        raise SecurityIdentityResolutionError(result)
    identity = result.resolved
    print(f"[proto] identity: {identity.canonical_name} "
          f"market={identity.market} security_id={identity.security_id}")

    config = load_catalog_config(CW_ROOT / "config" / "source_catalog.yaml", project_root=CW_ROOT)
    acq = load_acquisition_config(CW_ROOT / "config" / "source_acquisition.yaml", project_root=CW_ROOT)
    staging_root = Path(acq.staging_root)
    staging_root.mkdir(parents=True, exist_ok=True)
    catalog = SourceCatalog(config)
    writer = CanonicalSourceWriter(catalog, staging_root=staging_root)

    request = SourceRequest(
        entity=identity.canonical_name,
        market=identity.market,
        security_id=identity.security_id,          # canonical form (e.g. 03896)
        document_kind="annual_report",
        form_type=meta.get("form_type"),
        fiscal_year=int(meta["fiscal_year"]),
        fiscal_period=meta.get("fiscal_period"),
        language=meta.get("source_language"),
        provider=meta.get("source_provider"),
        provider_document_id=str(meta.get("source_id")),
        as_of_date=args.as_of_date,
        allow_download=False,
    )

    content_sha = sha256(pdf)
    assert content_sha == meta["pdf_sha256"], "portfolio PDF bytes changed"
    if args.dry_run:
        dest = (config.roots[0].path / identity.canonical_name / "raw" /
                "financial_reports" / "annual")
        print(f"[proto] DRY-RUN: would promote {pdf.name} -> {dest}/ "
              f"content_sha={content_sha[:12]}")
        return 0

    staged = staging_root / f"promote-{request.request_id.rsplit(':',1)[-1][:16]}.pdf"
    shutil.copyfile(pdf, staged)
    retrieved = (meta.get("first_ingested_at") or "")[:19] + "Z"
    candidate = DownloadCandidate(
        candidate_id="portfolio:" + meta["document_id"],
        provider=meta["source_provider"],
        provider_document_id=str(meta["source_id"]),
        market=identity.market,
        entity=identity.canonical_name,
        title=meta.get("source_title") or Path(pdf).stem,
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
        byte_size=pdf.stat().st_size,
        mime_type="application/pdf",
        retrieved_at=retrieved,
        http_status=200,
        adapter_name="dayu-portfolio-promoter",
        adapter_version="1.0.0",
    )

    result = writer.import_staged(request, candidate, receipt)
    print(f"[proto] import_staged status = {result.status.value}")
    print(f"[proto] canonical_path       = {result.canonical_path}")
    if staged.exists():
        staged.unlink()

    resolution = SourceResolver(catalog).resolve(request)
    print(f"[proto] resolve status       = {resolution.status.value}")
    if resolution.matches:
        h = resolution.matches[0]
        print(f"[proto] capture_ready       = {h.capture_ready}")
        print(f"[proto] canonical_path      = {h.canonical_path}")
        print(f"[proto] https_url           = {h.https_url}")
    ok = (
        resolution.status is ResolutionStatus.REUSED_EXACT
        and resolution.matches and resolution.matches[0].capture_ready
        and "companies" in str(resolution.matches[0].canonical_path).replace("\\", "/")
    )
    print(f"[proto] RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
