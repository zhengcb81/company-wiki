"""Promote dayu-portfolio documents into company_raw canonical sources.

A dayu portfolio document is already scanned and indexed as a read-only
``dayu_portfolio`` root location, but the reuse pipeline (resolver +
filing-fetch handle contract) only serves ``company_raw`` locations.  This
module copies the portfolio bytes into ``companies/{entity}/raw/...`` through
the validated :class:`CanonicalSourceWriter.import_staged` path, carrying the
canonical identity (resolved upstream — security-id normalization included),
so the promoted document becomes a capture-ready, reusable source without
re-downloading.

Portfolio provenance is read from each filing directory's ``meta.json`` (the
rich dayu record); the ``.pdf.source.json`` sidecar is only a minimal
``{market, security_id, source_title}`` marker and is not used here.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .acquisition import DownloadCandidate, DownloadReceipt
from .canonical_writer import CanonicalSourceWriter
from .resolver import SourceRequest


class PortfolioPromotionError(RuntimeError):
    """Raised when a portfolio document cannot be promoted."""


# form_type -> catalog document_kind (portfolio meta.json carries form_type,
# not document_kind; destination subdirectories follow document_kind).
_KIND_BY_FORM_TYPE = {
    "FY": "annual_report",
    "H1": "semi_annual_report",
    "Q1": "quarterly_report",
    "Q2": "quarterly_report",
    "Q3": "quarterly_report",
}


@dataclass(frozen=True)
class PromotionIdentity:
    """Canonical, verified identity for the promotion (from identity resolution)."""

    canonical_name: str
    market: str
    security_id: str


@dataclass(frozen=True)
class PortfolioPromotionResult:
    document_id: str
    status: str
    content_sha256: str
    canonical_path: str
    source_url: str
    fiscal_year: int | None
    document_kind: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "status": self.status,
            "content_sha256": self.content_sha256,
            "canonical_path": self.canonical_path,
            "source_url": self.source_url,
            "fiscal_year": self.fiscal_year,
            "document_kind": self.document_kind,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_ticker(value: str) -> str:
    """``03896`` -> ``3896``; ``KC`` -> ``kc``.  Portfolio dirs use the bare
    ticker while the security master stores the zero-padded HKEX form."""
    return value.strip().lstrip("0").casefold()


def find_entity_doc_dirs(
    portfolio_root: Path, identity: PromotionIdentity
) -> list[Path]:
    """Portfolio filing dirs (``<ticker>/filings/<doc_id>/``) for the identity."""
    wanted_tickers = {_normalized_ticker(identity.security_id)}
    wanted_name = identity.canonical_name.casefold()
    entity_dirs: list[Path] = []
    for meta_path in sorted(portfolio_root.glob("*/meta.json")):
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        ticker = _normalized_ticker(str(payload.get("ticker") or ""))
        name = str(payload.get("company_name") or "").casefold()
        if ticker in wanted_tickers or (name and name == wanted_name):
            entity_dirs.append(meta_path.parent)
    doc_dirs: list[Path] = []
    for entity_dir in sorted(entity_dirs):
        for filing_meta in sorted((entity_dir / "filings").glob("*/meta.json")):
            doc_dirs.append(filing_meta.parent)
    return doc_dirs


def find_doc_dir(portfolio_root: Path, identity: PromotionIdentity, document_id: str) -> Path:
    for doc_dir in find_entity_doc_dirs(portfolio_root, identity):
        if doc_dir.name == document_id:
            return doc_dir
    raise PortfolioPromotionError(f"portfolio document {document_id!r} not found for {identity.canonical_name}")


def _document_kind(meta: dict[str, Any]) -> str:
    kind = _KIND_BY_FORM_TYPE.get(str(meta.get("form_type") or "").upper())
    if kind is None:
        raise PortfolioPromotionError(
            f"unsupported portfolio form_type {meta.get('form_type')!r}"
        )
    return kind


def promote_from_portfolio(
    catalog: Any,
    writer: CanonicalSourceWriter,
    portfolio_root: Path,
    identity: PromotionIdentity,
    *,
    document_id: str,
    as_of_date: str,
    dry_run: bool = False,
) -> PortfolioPromotionResult:
    """Promote one portfolio document into company_raw through import_staged."""
    doc_dir = find_doc_dir(portfolio_root, identity, document_id)
    meta_path = doc_dir / "meta.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise PortfolioPromotionError(f"cannot read {meta_path}: {exc}") from exc
    if not isinstance(meta, dict):
        raise PortfolioPromotionError(f"{meta_path} is not a JSON object")

    pdf = doc_dir / f"{meta.get('document_id', document_id)}.pdf"
    if not pdf.is_file():
        raise PortfolioPromotionError(f"portfolio PDF missing: {pdf}")

    content_sha = _sha256(pdf)
    stored_sha = str(meta.get("pdf_sha256") or "").lower()
    if stored_sha and content_sha != stored_sha:
        raise PortfolioPromotionError("portfolio PDF bytes do not match meta.json pdf_sha256")

    source_url = str(meta.get("source_url") or "").strip()
    if not source_url.startswith("https://"):
        raise PortfolioPromotionError(f"portfolio source_url is not HTTPS: {source_url!r}")

    document_kind = _document_kind(meta)
    request = SourceRequest(
        entity=identity.canonical_name,
        market=identity.market,
        security_id=identity.security_id,
        document_kind=document_kind,
        form_type=str(meta.get("form_type") or "").strip() or None,
        fiscal_year=int(meta["fiscal_year"]),
        fiscal_period=str(meta.get("fiscal_period") or "").strip() or None,
        language=str(meta.get("source_language") or "").strip() or None,
        provider=str(meta.get("source_provider") or "").strip() or None,
        provider_document_id=str(meta.get("source_id") or "").strip() or None,
        as_of_date=as_of_date,
        allow_download=False,
    )

    if dry_run:
        destination = (
            writer.company_root.path
            / identity.canonical_name
            / "raw"
            / ("financial_reports/annual"
               if document_kind == "annual_report"
               else "financial_reports/semi_annual" if document_kind == "semi_annual_report"
               else "financial_reports/quarterly" if document_kind == "quarterly_report"
               else "other")
        )
        return PortfolioPromotionResult(
            document_id=document_id,
            status="dry_run",
            content_sha256=content_sha,
            canonical_path=str(destination),
            source_url=source_url,
            fiscal_year=request.fiscal_year,
            document_kind=document_kind,
        )

    staged = writer.staging_root / f"promote-{request.request_id.rsplit(':', 1)[-1][:16]}.pdf"
    staged.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pdf, staged)
    try:
        candidate = _build_candidate(meta, identity, source_url, document_kind)
        retrieved = (str(meta.get("first_ingested_at") or "")[:19] + "Z")
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
        imported = writer.import_staged(request, candidate, receipt)
        return PortfolioPromotionResult(
            document_id=document_id,
            status=imported.status.value,
            content_sha256=content_sha,
            canonical_path=imported.canonical_path,
            source_url=source_url,
            fiscal_year=request.fiscal_year,
            document_kind=document_kind,
        )
    finally:
        if staged.exists():
            staged.unlink()


def _build_candidate(
    meta: dict[str, Any],
    identity: PromotionIdentity,
    source_url: str,
    document_kind: str,
) -> DownloadCandidate:
    return DownloadCandidate(
        candidate_id="portfolio:" + str(meta.get("document_id") or ""),
        provider=str(meta.get("source_provider") or "").strip() or None,
        provider_document_id=str(meta.get("source_id") or "").strip() or None,
        market=identity.market,
        entity=identity.canonical_name,
        title=str(meta.get("source_title") or "").strip() or "untitled",
        source_url=source_url,
        document_kind=document_kind,
        filing_date=str(meta.get("filing_date") or "").strip(),
        fiscal_year=int(meta["fiscal_year"]),
        form_type=str(meta.get("form_type") or "").strip() or None,
        fiscal_period=str(meta.get("fiscal_period") or "").strip() or None,
        language=str(meta.get("source_language") or "").strip() or None,
        amended=bool(meta.get("amended")),
    )


def promote_all_for_entity(
    catalog: Any,
    writer: CanonicalSourceWriter,
    portfolio_root: Path,
    identity: PromotionIdentity,
    *,
    as_of_date: str,
    dry_run: bool = False,
    document_kind: str | None = None,
    fiscal_year: int | None = None,
) -> list[PortfolioPromotionResult]:
    """Promote every (filtered) portfolio document of the entity, idempotently."""
    results: list[PortfolioPromotionResult] = []
    for doc_dir in find_entity_doc_dirs(portfolio_root, identity):
        try:
            meta = json.loads((doc_dir / "meta.json").read_text(encoding="utf-8"))
            kind = _document_kind(meta)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, PortfolioPromotionError):
            continue
        if document_kind and kind != document_kind:
            continue
        if fiscal_year is not None and int(meta["fiscal_year"]) != fiscal_year:
            continue
        results.append(
            promote_from_portfolio(
                catalog,
                writer,
                portfolio_root,
                identity,
                document_id=doc_dir.name,
                as_of_date=as_of_date,
                dry_run=dry_run,
            )
        )
    return results
