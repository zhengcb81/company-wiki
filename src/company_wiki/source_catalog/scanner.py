"""Read-only scanners for company raw trees, generic directories, and dayu portfolios."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import unicodedata
import uuid
from typing import Any, Callable

from company_wiki.source_contract import SourceManifest, SourceType

from .admission import (
    AdmissionDecision,
    FOCUS_RELATIVE_PREFIX,
    FOCUS_ROOT_ID,
    evaluate_admission,
)
from .adapters.common import (
    _ACQUISITION_SIDECAR_SUFFIX,
    _SKIP_DIRS,
    _load_acquisition_metadata,
    _relative,
    _walk_files,
)
from .models import CatalogConfig, DOCUMENT_EXTENSIONS, SCANNER_VERSION, RootSpec, ScanReport
from .store import CatalogStore, canonical_json


_DATE_RE = re.compile(r"(?<!\d)(20\d{2})[-_.年](0[1-9]|1[0-2]|[1-9])[-_.月](0[1-9]|[12]\d|3[01]|[1-9])")


@dataclass(frozen=True)
class _Candidate:
    root: RootSpec
    path: Path
    relative_path: str
    group_key: str
    role: str
    entity_name: str | None
    group_metadata: dict[str, Any]
    source_status: str
    admission: AdmissionDecision | None = None


@dataclass(frozen=True)
class _ObservedFile:
    candidate: _Candidate
    source_id: str | None
    content_sha256: str | None
    size: int
    mtime_ns: int
    mime_type: str
    manifest_json: str | None
    reused: bool
    error: str | None
    known_error: bool = False


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _location_id(root_id: str, relative_path: str) -> str:
    return "urn:company-wiki:location:sha256:" + _sha256_text(root_id + "\0" + relative_path)


def _document_id_for_source(source_id: str) -> str:
    return "urn:company-wiki:document:sha256:" + source_id.rsplit(":", 1)[-1]


def _logical_document_id(root_id: str, group_key: str) -> str:
    return "urn:company-wiki:document-logical:sha256:" + _sha256_text(root_id + "\0" + group_key)


def _mime_type(path: Path) -> str:
    extension = path.suffix.lower()
    overrides = {
        ".md": "text/markdown",
        ".mht": "multipart/related",
        ".xsd": "application/xml",
        ".xml": "application/xml",
        ".json": "application/json",
    }
    if extension in overrides:
        return overrides[extension]
    guessed = mimetypes.guess_type(path.name)[0]
    return (guessed or "application/octet-stream").lower()


def _published_date(text: str) -> str | None:
    match = _DATE_RE.search(text)
    if not match:
        return None
    try:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date().isoformat()
    except ValueError:
        return None


def _classification(path: Path, *, root_kind: str, metadata: dict[str, Any]) -> tuple[str, SourceType]:
    form = str(metadata.get("form_type") or "").casefold()
    text = re.sub(
        r"[_-]+",
        " ",
        path.stem + " " + str(metadata.get("source_title") or "") + " " + form,
    ).casefold()
    # --- trust order: sidecar > form_type > precise keywords > weak keywords ---
    # 1. explicit sidecar document_kind (highest trust)
    sidecar_kind = str(metadata.get("document_kind") or "").strip().lower()
    if sidecar_kind:
        _SIDECAR_MAP = {
            "annual_report": (SourceType.REGULATORY_FILING, "annual_report"),
            "semi_annual_report": (SourceType.REGULATORY_FILING, "semi_annual_report"),
            "quarterly_report": (SourceType.REGULATORY_FILING, "quarterly_report"),
            "regulatory_filing": (SourceType.REGULATORY_FILING, "regulatory_filing"),
            "broker_research": (SourceType.BROKER_RESEARCH, "broker_research"),
            "investor_relations": (SourceType.INVESTOR_RELATIONS, "investor_relations"),
            "investor_call_transcript": (
                SourceType.INVESTOR_RELATIONS,
                "investor_call_transcript",
            ),
            "prospectus": (SourceType.PROSPECTUS, "prospectus"),
            "news": (SourceType.ORIGINAL_NEWS, "news"),
        }
        if sidecar_kind in _SIDECAR_MAP:
            st, kind = _SIDECAR_MAP[sidecar_kind]
            return kind, st
    # 2. broker research commentary must precede annual/semi/quarterly checks
    if any(token in text for token in ("点评", "深度报告", "调研报告")):
        return "broker_research", SourceType.BROKER_RESEARCH
    # 3. explicit form_type (regulatory filing)
    if form in {"10-k", "20-f", "40-f"} or "20f" in text or "10k" in text or "40f" in text:
        return "annual_report", SourceType.REGULATORY_FILING
    # 3b. dayu portfolio form_type codes (FY/H1/Q1-Q3) — the portfolio
    # meta.json carries these; titles are Traditional Chinese (年報 etc.).
    if form in {"fy", "10k"}:
        return "annual_report", SourceType.REGULATORY_FILING
    if form in {"h1", "h2"}:
        return "semi_annual_report", SourceType.REGULATORY_FILING
    if form in {"q1", "q2", "q3", "q4"}:
        return "quarterly_report", SourceType.REGULATORY_FILING
    # 4. semi-annual BEFORE annual (半年度 contains 年度)
    if any(token in text for token in ("半年度", "半年报", "中期報告", "中期报告", "interim report")):
        return "semi_annual_report", SourceType.REGULATORY_FILING
    # 5. quarterly
    if any(
        token in text
        for token in ("季度报告", "季度報告", "一季报", "三季报", "quarterly report")
    ):
        return "quarterly_report", SourceType.REGULATORY_FILING
    # 6. annual report (after semi/quarterly exclusion)
    if any(token in text for token in ("年度报告", "年报", "年報", "annual report")):
        return "annual_report", SourceType.REGULATORY_FILING
    if root_kind == "dayu_portfolio":
        return "regulatory_filing", SourceType.REGULATORY_FILING
    if any(
        token in text
        for token in ("电话会议纪要", "业绩电话会", "earnings call transcript")
    ):
        return "investor_call_transcript", SourceType.INVESTOR_RELATIONS
    if any(token in text for token in ("投资者关系", "调研", "路演", "业绩说明会", "investor relation")):
        return "investor_relations", SourceType.INVESTOR_RELATIONS
    if any(token in text for token in ("招股", "prospectus")):
        return "prospectus", SourceType.PROSPECTUS
    if root_kind == "directory":
        return "broker_research", SourceType.BROKER_RESEARCH
    if path.suffix.lower() == ".md" and "news" in {part.casefold() for part in path.parts}:
        return "news", SourceType.ORIGINAL_NEWS
    return "other", SourceType.OTHER


def _entity(entity_name: str | None, root_id: str) -> tuple[str, str, str, float, str]:
    if entity_name:
        if re.fullmatch(r"[A-Za-z0-9._-]+", entity_name):
            return f"ticker:{entity_name.upper()}", entity_name, "ticker", 1.0, "path_ticker"
        return f"company-name:{entity_name}", entity_name, "company", 1.0, "company_raw_path"
    return f"unresolved:{root_id}", f"Unresolved ({root_id})", "unresolved", 0.0, "unresolved"


def _company_names(config: CatalogConfig) -> tuple[str, ...]:
    names: set[str] = set()
    for root in config.roots:
        if root.kind != "company_raw" or not root.path.is_dir():
            continue
        for child in root.path.iterdir():
            if child.is_dir() and (child / "raw").is_dir():
                names.add(unicodedata.normalize("NFC", child.name))
    return tuple(sorted(names, key=lambda value: (-len(value), value.casefold())))


def _infer_company(relative_path: str, names: tuple[str, ...]) -> str | None:
    folded = relative_path.casefold()
    matches = [name for name in names if name.casefold() in folded]
    return matches[0] if len(matches) == 1 else None


def _enrich_dayu_portfolio_metadata(
    path: Path, metadata: dict[str, Any]
) -> dict[str, Any]:
    """Merge the rich dayu filing ``meta.json`` (sibling of the primary
    document) into the document metadata so raw portfolio documents are
    directly reusable: document_kind via form_type mapping, fiscal_year,
    source_url, provider, language, filing_date (ADR-008 Strategy B).

    The ``.pdf.source.json`` sidecar only carries a minimal marker; the rich
    record lives in the filing directory's ``meta.json``.
    """
    meta_path = path.parent / "meta.json"
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return metadata
    if not isinstance(payload, dict):
        return metadata
    enriched: dict[str, Any] = {}
    for key in (
        "document_id",
        "form_type",
        "fiscal_year",
        "fiscal_period",
        "source_url",
        "source_title",
        "source_language",
        "filing_date",
        "source_id",
        "provider_company_id",
        "amended",
    ):
        if key in payload and payload[key] not in (None, ""):
            enriched[key] = payload[key]
    if "source_provider" in payload and payload["source_provider"] not in (None, ""):
        enriched["provider"] = payload["source_provider"]
    if "source_language" in enriched:
        enriched["language"] = enriched["source_language"]
    # Identity: portfolio filing meta.json carries the bare ticker only; the
    # entity-level meta.json (portfolio/<ticker>/meta.json) carries the
    # market. The resolver's security_id comparison normalizes leading zeros
    # (HKEX "02020" == "2020"), so the bare ticker suffices as security_id.
    if not enriched.get("security_id"):
        filing_ticker = str(payload.get("ticker") or "").strip()
        if filing_ticker:
            enriched["security_id"] = filing_ticker
    if not enriched.get("market"):
        entity_meta_path = path.parents[2] / "meta.json"
        try:
            entity_meta = json.loads(entity_meta_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            entity_meta = {}
        if isinstance(entity_meta, dict):
            market = str(entity_meta.get("market") or "").strip()
            if market:
                enriched["market"] = market
            if not enriched.get("security_id"):
                entity_ticker = str(entity_meta.get("ticker") or "").strip()
                if entity_ticker:
                    enriched["security_id"] = entity_ticker
    if not enriched:
        return metadata
    merged = dict(metadata)
    merged["dayu_meta"] = enriched
    merged.update(enriched)  # top level too, so the classifier sees form_type etc.
    return merged


def _construct_edgar_url(metadata: dict[str, Any]) -> str | None:
    """Deterministically construct an SEC EDGAR URL from dayu SEC metadata
    (accession_number + company_id + primary_document), Phase 16.1."""
    acc = str(metadata.get("accession_number") or "").strip()
    cik = str(metadata.get("company_id") or "").strip()
    primary = str(metadata.get("primary_document") or "").strip()
    if not (acc and cik and primary):
        return None
    cik10 = cik.zfill(10)
    return (
        f"https://www.sec.gov/Archives/edgar/data/{cik10}/"
        f"{acc.replace('-', '')}/{primary}"
    )


def _load_dayu_portfolio_urls(config: CatalogConfig) -> dict[str, str]:
    """Build company_name -> source_url from dayu portfolio meta.json files,
    so company_raw documents whose sidecar lacks a URL can be enriched
    (Phase 16.1).  Only entries that carry a source_url are indexed."""
    mapping: dict[str, str] = {}
    for root in config.roots:
        if root.kind != "dayu_portfolio" or not root.path.is_dir():
            continue
        for meta_path in root.path.rglob("meta.json"):
            try:
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            url = str(payload.get("source_url") or "").strip()
            if not url:
                continue
            company_name = str(payload.get("company_name") or "").strip()
            if company_name:
                mapping.setdefault(company_name, url)
    return mapping


def _load_security_master_identity(catalog_dir: Path) -> dict[str, tuple[str, str]]:
    """Build provider org id → (market, security_id) from the security-master
    snapshots, so a dayu meta.json's provider_company_id can propagate
    identity into ingested documents (Phase 15.4)."""
    mapping: dict[str, tuple[str, str]] = {}
    master_dir = catalog_dir / "security_master"
    if not master_dir.is_dir():
        return mapping
    for market in ("cn", "hk", "us"):
        master_file = master_dir / f"{market}.json"
        if not master_file.is_file():
            continue
        try:
            payload = json.loads(master_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        records = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            identifiers = record.get("identifiers")
            if not isinstance(identifiers, dict):
                identifiers = {}
            org = str(
                record.get("source_record_id") or identifiers.get("org_id") or ""
            ).strip()
            market_value = str(record.get("market") or "").strip().upper()
            security_id = str(record.get("security_id") or "").strip()
            if org and market_value and security_id:
                mapping.setdefault(org, (market_value, security_id))
    return mapping


def _scan_root_v1(
    root: RootSpec,
    company_names: tuple[str, ...],
    *,
    progress: Callable[..., None] | None = None,
    master_identity: dict[str, tuple[str, str]] | None = None,
    portfolio_urls: dict[str, str] | None = None,
) -> tuple[list[_Candidate], int, int]:
    candidates: list[_Candidate] = []
    excluded = 0
    policy_excluded = 0
    if root.kind == "company_raw":
        companies = sorted(
            (item for item in root.path.iterdir() if item.is_dir()),
            key=lambda item: item.name,
        )
        for company_index, company in enumerate(companies, start=1):
            raw = company / "raw"
            if not raw.is_dir():
                continue
            if progress is not None:
                progress(
                    current_path=str(raw.resolve(strict=False)),
                    current=company_index,
                    total=len(companies),
                    detail=f"enumerating root {root.root_id}",
                )
            paths = sorted(_walk_files(raw))
            sidecars = {
                str(path)[: -len(_ACQUISITION_SIDECAR_SUFFIX)]: path
                for path in paths
                if path.name.endswith(_ACQUISITION_SIDECAR_SUFFIX)
            }
            primary_paths = [
                path for path in paths if not path.name.endswith(_ACQUISITION_SIDECAR_SUFFIX)
            ]
            for path in primary_paths:
                relative = _relative(path, root.path)
                sidecar = sidecars.get(str(path))
                metadata = _load_acquisition_metadata(sidecar) if sidecar else {}
                # Phase 16.1: a sidecar without any source URL is enriched
                # from the matching dayu portfolio meta.json (by company name).
                if not metadata.get("source_url") and not metadata.get("https_url"):
                    portfolio_url = (portfolio_urls or {}).get(company.name)
                    if portfolio_url:
                        metadata = dict(metadata)
                        metadata["source_url"] = portfolio_url
                # Phase 18.4: SEC company_raw documents are deterministically
                # US-listed (same rule as the dayu portfolio pilot): backfill
                # market/security identity when the sidecar omits it, so
                # capture-ready handles resolve by market.
                form_type = str(metadata.get("form_type") or "").upper()
                is_sec = bool(
                    metadata.get("accession_number")
                    or str(metadata.get("provider") or "").strip().lower() == "sec"
                    or form_type.startswith(("10-", "20-", "6-"))
                )
                if not metadata.get("market") and is_sec:
                    metadata = dict(metadata)
                    metadata["market"] = "US"
                if not metadata.get("security_id") and metadata.get("ticker"):
                    metadata = dict(metadata)
                    metadata["security_id"] = str(metadata["ticker"])
                candidates.append(
                    _Candidate(
                        root,
                        path,
                        relative,
                        relative,
                        "original_primary",
                        company.name,
                        metadata,
                        "active",
                    )
                )
                if sidecar is not None:
                    candidates.append(
                        _Candidate(
                            root,
                            sidecar,
                            _relative(sidecar, root.path),
                            relative,
                            "metadata",
                            company.name,
                            metadata,
                            "active",
                        )
                    )
            primary_names = {str(path) for path in primary_paths}
            for target, sidecar in sorted(sidecars.items()):
                if target in primary_names:
                    continue
                relative = _relative(sidecar, root.path)
                candidates.append(
                    _Candidate(
                        root,
                        sidecar,
                        relative,
                        relative[: -len(_ACQUISITION_SIDECAR_SUFFIX)],
                        "metadata",
                        company.name,
                        _load_acquisition_metadata(sidecar),
                        "incomplete",
                    )
                )
    elif root.kind == "directory":
        for directory_index, (current, directories, files) in enumerate(
            os.walk(root.path),
            start=1,
        ):
            directories[:] = [name for name in directories if name not in _SKIP_DIRS]
            current_path = Path(current)
            if progress is not None:
                progress(
                    current_path=str(current_path.resolve(strict=False)),
                    current=directory_index,
                    total=0,
                    detail=f"enumerating root {root.root_id}",
                )
            supported: list[Path] = []
            for name in files:
                path = current_path / name
                if path.suffix.lower() not in DOCUMENT_EXTENSIONS:
                    excluded += 1
                    continue
                supported.append(path)
            relative_dir = _relative(current_path, root.path)
            # WU-702: route-configured focus scope; legacy FOCUS constants
            # remain only for v1 configs without routes
            if root.routes:
                focus_scope = root.route_matches(relative_dir)
            else:
                focus_scope = root.root_id == FOCUS_ROOT_ID and (
                    relative_dir == FOCUS_RELATIVE_PREFIX
                    or relative_dir.startswith(FOCUS_RELATIVE_PREFIX + "/")
                )
            if not focus_scope:
                # Legacy behavior for every directory outside the exact
                # 重点关注 subtree: each supported file (including .source.json)
                # is a standalone primary document with no sidecar pairing.
                for path in supported:
                    relative = _relative(path, root.path)
                    candidates.append(
                        _Candidate(
                            root,
                            path,
                            relative,
                            relative,
                            "original_primary",
                            _infer_company(relative, company_names),
                            {},
                            "active",
                            None,
                        )
                    )
                continue
            sidecars = {
                str(path)[: -len(_ACQUISITION_SIDECAR_SUFFIX)]: path
                for path in supported
                if path.name.endswith(_ACQUISITION_SIDECAR_SUFFIX)
            }
            primary_paths = [
                path
                for path in supported
                if not path.name.endswith(_ACQUISITION_SIDECAR_SUFFIX)
            ]
            for path in primary_paths:
                relative = _relative(path, root.path)
                sidecar = sidecars.get(str(path))
                metadata = _load_acquisition_metadata(sidecar) if sidecar else {}
                if root.kind == "dayu_portfolio":
                    metadata = _enrich_dayu_portfolio_metadata(path, metadata)
                admission = evaluate_admission(
                    root_id=root.root_id,
                    relative_path=relative,
                    metadata=metadata,
                )
                if admission is not None and not admission.admitted:
                    policy_excluded += 1
                    excluded += 1
                    if sidecar is not None:
                        policy_excluded += 1
                        excluded += 1
                    continue
                entity_name = _infer_company(relative, company_names)
                candidates.append(
                    _Candidate(
                        root,
                        path,
                        relative,
                        relative,
                        "original_primary",
                        entity_name,
                        metadata,
                        "active",
                        admission,
                    )
                )
                if sidecar is not None:
                    candidates.append(
                        _Candidate(
                            root,
                            sidecar,
                            _relative(sidecar, root.path),
                            relative,
                            "metadata",
                            entity_name,
                            metadata,
                            "active",
                            admission,
                        )
                    )
            primary_names = {str(path) for path in primary_paths}
            for target, sidecar in sidecars.items():
                if target in primary_names:
                    continue
                excluded += 1
                orphan_decision = evaluate_admission(
                    root_id=root.root_id,
                    relative_path=_relative(sidecar, root.path),
                    metadata=_load_acquisition_metadata(sidecar),
                )
                if orphan_decision is not None:
                    policy_excluded += 1
    else:
        raw_groups: dict[str, list[Path]] = defaultdict(list)
        for file_index, path in enumerate(_walk_files(root.path), start=1):
            if progress is not None and file_index % 100 == 1:
                progress(
                    current_path=str(path.resolve(strict=False)),
                    current=file_index,
                    total=0,
                    detail=f"enumerating root {root.root_id}",
                )
            relative = _relative(path, root.path)
            parts = Path(relative).parts
            if len(parts) >= 3 and parts[1] == "filings":
                if len(parts) >= 4 and parts[2] == ".rejections":
                    group_key = Path(*parts[:4]).as_posix()
                else:
                    group_key = Path(*parts[:3]).as_posix()
            else:
                group_key = relative
            raw_groups[group_key].append(path)
        for group_key, paths in sorted(raw_groups.items()):
            parts = Path(group_key).parts
            ticker = parts[0] if parts else None
            group_dir = root.path.joinpath(*parts) if len(paths) > 1 or Path(group_key).suffix == "" else paths[0].parent
            meta_path = group_dir / "meta.json"
            metadata: dict[str, Any] = {}
            if meta_path.is_file():
                try:
                    loaded = json.loads(meta_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        metadata = loaded
                except (OSError, UnicodeError, json.JSONDecodeError):
                    metadata = {"meta_parse_error": True}
            # Phase 15.4: propagate identity that exists upstream but is not
            # carried in the dayu meta.json (provider_company_id ↔ security
            # master org id), so ingested documents are not identity-less.
            if master_identity and (
                not metadata.get("market") or not metadata.get("security_id")
            ):
                org = str(metadata.get("provider_company_id") or "").strip()
                org = org.rsplit(":", 1)[-1] if org else ""
                resolved = master_identity.get(org) if org else None
                if resolved is not None:
                    market_value, security_id = resolved
                    metadata.setdefault("market", market_value)
                    metadata.setdefault("security_id", security_id)
            # Phase 16.1: SEC documents without a source URL get a
            # deterministically constructed EDGAR URL (accession_number).
            if not metadata.get("source_url") and not metadata.get("https_url"):
                edgar_url = _construct_edgar_url(metadata)
                if edgar_url is not None:
                    metadata.setdefault("source_url", edgar_url)
            # Phase 17 pilot: SEC dayu documents are deterministically
            # US-listed; carry market/security identity when the upstream
            # meta.json omits it, so capture-ready handles can resolve
            # (Alphabet 10-K capture_ready deadlock).
            if not metadata.get("market") and metadata.get("accession_number"):
                metadata["market"] = "US"
            if not metadata.get("security_id") and metadata.get("ticker"):
                metadata["security_id"] = str(metadata["ticker"])
            # ADR-008 Strategy B: HK/CN dayu documents carry the bare ticker
            # only; backfill market from the entity-level meta.json
            # (portfolio/<ticker>/meta.json) and security_id from the ticker.
            # The resolver normalizes leading zeros ("02020" == "2020").
            if not metadata.get("security_id") and metadata.get("ticker"):
                metadata["security_id"] = str(metadata["ticker"])
            if not metadata.get("market") and ticker:
                entity_meta_path = root.path / ticker / "meta.json"
                if entity_meta_path.is_file():
                    try:
                        entity_payload = json.loads(
                            entity_meta_path.read_text(encoding="utf-8")
                        )
                    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
                        entity_payload = {}
                    if isinstance(entity_payload, dict):
                        market_value = str(entity_payload.get("market") or "").strip()
                        if market_value:
                            metadata["market"] = market_value
            names = {path.name: path for path in paths}
            selected = str(metadata.get("selected_primary_document") or "")
            primary = str(metadata.get("primary_document") or "")
            preferred: Path | None = None
            for name in (selected, primary):
                if name and name in names and not name.endswith("_docling.json"):
                    preferred = names[name]
                    break
            if preferred is None:
                preferred = next((path for path in paths if path.suffix.lower() == ".pdf"), None)
            if preferred is None:
                preferred = next(
                    (path for path in paths if path.suffix.lower() in {".htm", ".html"} and path.name != "meta.json"),
                    None,
                )
            if preferred is None:
                preferred = next(
                    (
                        path
                        for path in paths
                        if path.name != "meta.json"
                        and not path.name.endswith("manifest.json")
                        and not path.name.endswith("_docling.json")
                    ),
                    None,
                )
            if preferred is None:
                # Metadata-only group (no preferred file): do not ingest a
                # document (Phase 15.4).  dayu stages meta.json before bytes
                # exist; byte-less placeholder documents polluted the catalog
                # with identity-less records that blocked reuse and download.
                # The group is re-evaluated on the next scan once a preferred
                # file appears.
                continue
            rejected = ".rejections" in parts
            complete = metadata.get("ingest_complete") is True
            if rejected:
                source_status = "upstream_rejected"
            elif preferred is None:
                source_status = "incomplete"
            else:
                source_status = "active" if complete or len(paths) == 1 else "incomplete"
            for path in sorted(paths):
                if path.name == "meta.json" or path.name.endswith("manifest.json"):
                    role = "metadata"
                elif path.name.endswith("_docling.json"):
                    role = "processed_docling"
                elif preferred is not None and path == preferred:
                    role = "original_primary"
                else:
                    role = "original_attachment"
                candidates.append(
                    _Candidate(
                        root,
                        path,
                        _relative(path, root.path),
                        group_key,
                        role,
                        ticker,
                        metadata,
                        source_status,
                    )
                )
    return candidates, excluded, policy_excluded


def _observe_file(
    candidate: _Candidate,
    *,
    existing: Any,
    scan_time: str,
    document_kind: str,
    source_type: SourceType,
    entity_id: str,
) -> _ObservedFile:
    stat = candidate.path.stat()
    if (
        existing is not None
        and existing["source_id"]
        and existing["manifest_json"]
        and existing["observed_size"] == stat.st_size
        and existing["observed_mtime_ns"] == stat.st_mtime_ns
    ):
        manifest = SourceManifest.from_dict(json.loads(existing["manifest_json"]))
        return _ObservedFile(
            candidate,
            manifest.source_id,
            manifest.content_sha256,
            stat.st_size,
            stat.st_mtime_ns,
            manifest.mime_type,
            manifest.canonical_json(),
            True,
            None,
            False,
        )
    mime_type = _mime_type(candidate.path)
    try:
        collector_name = f"filesystem-catalog-{candidate.root.root_id}"
        collector_version = SCANNER_VERSION
        retrieved_at = scan_time
        if candidate.role == "original_primary" and candidate.group_metadata:
            collector_name = str(
                candidate.group_metadata.get("adapter_name") or collector_name
            )
            collector_version = str(
                candidate.group_metadata.get("adapter_version") or collector_version
            )
            retrieved_at = str(
                candidate.group_metadata.get("retrieved_at") or retrieved_at
            )
        manifest = SourceManifest.from_file(
            root=candidate.root.path,
            file_path=candidate.path,
            entity_ids=(entity_id,),
            source_type=source_type if candidate.role == "original_primary" else SourceType.OTHER,
            published_date=(
                str(candidate.group_metadata.get("filing_date"))
                if candidate.group_metadata.get("filing_date")
                else _published_date(candidate.path.name)
            ),
            retrieved_at=retrieved_at,
            collector_name=collector_name,
            collector_version=collector_version,
            mime_type=mime_type,
        )
        expected_sha256 = candidate.group_metadata.get("content_sha256")
        if (
            candidate.role == "original_primary"
            and expected_sha256
            and manifest.content_sha256 != expected_sha256
        ):
            raise ValueError("acquisition sidecar SHA-256 does not match source bytes")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        known_error = bool(
            existing is not None
            and existing["location_status"] == "quarantined"
            and existing["observed_size"] == stat.st_size
            and existing["observed_mtime_ns"] == stat.st_mtime_ns
            and existing["error"] == error
        )
        return _ObservedFile(
            candidate,
            None,
            None,
            stat.st_size,
            stat.st_mtime_ns,
            mime_type,
            None,
            False,
            error,
            known_error,
        )
    return _ObservedFile(
        candidate,
        manifest.source_id,
        manifest.content_sha256,
        stat.st_size,
        stat.st_mtime_ns,
        manifest.mime_type,
        manifest.canonical_json(),
        False,
        None,
        False,
    )


def _select_roots(
    config: CatalogConfig,
    root_ids: set[str] | None,
) -> tuple[RootSpec, ...]:
    selected_roots = tuple(
        root for root in config.roots if root_ids is None or root.root_id in root_ids
    )
    if not selected_roots:
        raise ValueError("no configured roots matched root_ids")
    if root_ids is not None:
        unknown = root_ids - {root.root_id for root in config.roots}
        if unknown:
            raise ValueError(f"unknown root_ids: {sorted(unknown)}")
    return selected_roots


def _begin_scan_run(store: CatalogStore, run_id: str, scan_time: str) -> None:
    with store.transaction() as connection:
        connection.execute(
            "UPDATE scan_runs SET completed_at=?,status='interrupted' WHERE status='running'",
            (scan_time,),
        )
        connection.execute(
            "INSERT INTO scan_runs(run_id,started_at,status) VALUES(?,?,?)",
            (run_id, scan_time, "running"),
        )


def _interrupt_scan_run(store: CatalogStore, run_id: str) -> None:
    with store.transaction() as connection:
        connection.execute(
            """UPDATE scan_runs SET completed_at=?,status='interrupted'
            WHERE run_id=? AND status='running'""",
            (_utc_now(), run_id),
        )


def _scan_catalog_impl(
    config: CatalogConfig,
    store: CatalogStore | None,
    *,
    dry_run: bool = False,
    root_ids: set[str] | None = None,
    progress: Callable[..., None] | None = None,
    run_id: str | None = None,
    scan_time: str | None = None,
    selected_roots: tuple[RootSpec, ...] | None = None,
    scan_run_started: bool = False,
) -> ScanReport:
    run_id = run_id or "scan-" + uuid.uuid4().hex
    scan_time = scan_time or _utc_now()
    names = _company_names(config)
    files_seen = files_hashed = files_reused = files_excluded = errors = 0
    policy_excluded = 0
    new_errors = known_quarantined = 0
    error_details: list[dict[str, Any]] = []
    if selected_roots is None:
        selected_roots = _select_roots(config, root_ids)
    if not dry_run:
        if store is None:
            raise TypeError("store is required for a non-dry-run scan")
        if not scan_run_started:
            _begin_scan_run(store, run_id, scan_time)

    master_identity = _load_security_master_identity(config.catalog_dir)
    portfolio_urls = _load_dayu_portfolio_urls(config)
    for root in selected_roots:
        if not root.path.is_dir():
            errors += 1
            new_errors += 1
            if len(error_details) < 5:
                error_details.append(
                    {
                        "root_id": root.root_id,
                        "relative_path": "",
                        "error": "root directory is unavailable",
                        "unchanged": False,
                    }
                )
            continue
        candidates, excluded, policy_count = scan_root_strategy(
            root,
            names,
            progress=progress,
            master_identity=master_identity,
            portfolio_urls=portfolio_urls,
        )
        files_seen += len(candidates)
        files_excluded += excluded
        policy_excluded += policy_count
        if dry_run:
            continue
        with store.transaction() as connection:
            connection.execute(
                """INSERT INTO roots(root_id,path,kind,priority,last_scan_run,last_scanned_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(root_id) DO UPDATE SET
                path=excluded.path,kind=excluded.kind,priority=excluded.priority,
                last_scan_run=excluded.last_scan_run,last_scanned_at=excluded.last_scanned_at""",
                (root.root_id, str(root.path.resolve()), root.kind, root.priority, run_id, scan_time),
            )
        groups: dict[str, list[_Candidate]] = defaultdict(list)
        for candidate in candidates:
            groups[candidate.group_key].append(candidate)
        existing_locations = {
            row["relative_path"]: row
            for row in store.fetchall(
                """SELECT relative_path,source_id,document_id,observed_size,observed_mtime_ns,
                manifest_json,location_status,error
                FROM locations WHERE root_id=?""",
                (root.root_id,),
            )
        }
        group_items = sorted(
            groups.items(),
            key=lambda item: (
                min(
                    (
                        candidate.admission.priority
                        for candidate in item[1]
                        if candidate.admission is not None
                    ),
                    default=1000,
                ),
                item[0],
            ),
        )
        for group_index, (group_key, group) in enumerate(group_items, start=1):
            primary_candidate = next((item for item in group if item.role == "original_primary"), None)
            classification_path = primary_candidate.path if primary_candidate else group[0].path
            if progress is not None:
                progress(
                    current_path=str(classification_path.resolve(strict=False)),
                    current=group_index,
                    total=len(group_items),
                    detail=f"scanning root {root.root_id}",
                )
            metadata = primary_candidate.group_metadata if primary_candidate else group[0].group_metadata
            admission = (
                primary_candidate.admission
                if primary_candidate is not None
                else group[0].admission
            )
            if admission is not None and admission.admitted:
                if admission.document_kind is None or admission.source_type is None:
                    raise RuntimeError("admitted source is missing classification")
                document_kind, source_type = (
                    admission.document_kind,
                    admission.source_type,
                )
            else:
                document_kind, source_type = _classification(
                    classification_path, root_kind=root.kind, metadata=metadata
                )
            entity_name = (primary_candidate or group[0]).entity_name
            entity_id, entity_label, entity_kind, confidence, method = _entity(entity_name, root.root_id)
            observed: list[_ObservedFile] = []
            for candidate in group:
                try:
                    item = _observe_file(
                        candidate,
                        existing=existing_locations.get(candidate.relative_path),
                        scan_time=scan_time,
                        document_kind=document_kind,
                        source_type=source_type,
                        entity_id=entity_id,
                    )
                except OSError as exc:
                    errors += 1
                    new_errors += 1
                    if len(error_details) < 5:
                        error_details.append(
                            {
                                "root_id": root.root_id,
                                "relative_path": candidate.relative_path,
                                "error": f"{type(exc).__name__}: {exc}",
                                "unchanged": False,
                            }
                        )
                    continue
                observed.append(item)
                if item.reused:
                    files_reused += 1
                elif item.source_id:
                    files_hashed += 1
                if item.error:
                    errors += 1
                    if item.known_error:
                        known_quarantined += 1
                    else:
                        new_errors += 1
                    if len(error_details) < 5:
                        error_details.append(
                            {
                                "root_id": root.root_id,
                                "relative_path": candidate.relative_path,
                                "error": item.error,
                                "unchanged": item.known_error,
                            }
                        )
            primary = next((item for item in observed if item.candidate.role == "original_primary" and item.source_id), None)
            document_id = (
                _document_id_for_source(primary.source_id)
                if primary and primary.source_id
                else _logical_document_id(root.root_id, group_key)
            )
            obsolete_document_ids = {
                str(existing["document_id"])
                for candidate in group
                if (existing := existing_locations.get(candidate.relative_path))
                and existing["document_id"]
                and existing["document_id"] != document_id
            }
            title = str(metadata.get("source_title") or "").strip() or classification_path.stem
            published = (
                str(metadata.get("filing_date") or metadata.get("published_date") or "")
                .strip()
                or _published_date(classification_path.name)
                or None
            )
            source_status = (primary_candidate or group[0]).source_status
            if primary is None:
                source_status = (
                    "quarantined" if any(item.error for item in observed) else "incomplete"
                )
            document_metadata = {
                "root_id": root.root_id,
                "group_key": group_key,
                "scanner_version": SCANNER_VERSION,
                "dayu_meta": metadata if root.kind == "dayu_portfolio" else None,
                "acquisition": metadata if root.kind == "company_raw" and metadata else None,
                "admission": (
                    {
                        "reason": admission.reason,
                        "evidence": list(admission.evidence),
                        "processing_priority": admission.priority,
                    }
                    if admission is not None
                    else None
                ),
            }
            with store.transaction() as connection:
                for item in observed:
                    if item.source_id:
                        connection.execute(
                            "INSERT OR IGNORE INTO sources(source_id,content_sha256,byte_size,mime_type,first_seen_at) VALUES(?,?,?,?,?)",
                            (item.source_id, item.content_sha256, item.size, item.mime_type, scan_time),
                        )
                existing_document = connection.execute(
                    "SELECT metadata_priority, source_status, metadata_json FROM documents WHERE document_id=?", (document_id,)
                ).fetchone()
                if existing_document is None:
                    connection.execute(
                        """INSERT INTO documents(document_id,primary_source_id,title,source_type,document_kind,
                        published_date,source_status,metadata_priority,metadata_json,first_seen_at,last_seen_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            document_id,
                            primary.source_id if primary else None,
                            title,
                            source_type.value,
                            document_kind,
                            published,
                            source_status,
                            root.priority,
                            canonical_json(document_metadata),
                            scan_time,
                            scan_time,
                        ),
                    )
                elif existing_document["source_status"] == "retired":
                    # Retirement is terminal: a rescan must never revive a
                    # retired document even while its files remain on disk
                    # (Phase 15.6 batch governance).  Its locations stay
                    # retired as well, so a partially-active location can
                    # never exist (see the location_status computation below).
                    connection.execute(
                        "UPDATE documents SET last_seen_at=? WHERE document_id=?",
                        (scan_time, document_id),
                    )
                elif root.priority <= existing_document["metadata_priority"]:
                    existing_meta = {}
                    try:
                        existing_meta = json.loads(existing_document["metadata_json"] or "{}")
                    except json.JSONDecodeError:
                        pass
                    existing_inner = existing_meta.get("dayu_meta") or existing_meta.get("acquisition") or {}
                    new_inner = document_metadata.get("dayu_meta") or document_metadata.get("acquisition") or {}
                    # Phase 16.5: when the same content-addressed document is
                    # re-ingested from another path, prefer the metadata that
                    # carries a source URL (an old bare sidecar must not
                    # overwrite a complete one).
                    # Phase 17 pilot: likewise prefer metadata that carries
                    # market/security identity when the stored copy predates
                    # the identity backfill (Alphabet 10-K capture_ready
                    # deadlock).
                    # ADR-008 Strategy B: and prefer metadata that carries a
                    # provider document id when the stored copy lacks one —
                    # otherwise the scanner's ticker identity backfill would
                    # block the promotion's acquisition metadata (whose
                    # provider identity the REUSED_EXACT assert requires).
                    prefer_new = (
                        (
                            not (existing_inner.get("source_url") or existing_inner.get("https_url"))
                            and (new_inner.get("source_url") or new_inner.get("https_url"))
                        )
                        or (
                            not (existing_inner.get("market") and existing_inner.get("security_id"))
                            and (new_inner.get("market") and new_inner.get("security_id"))
                        )
                        or (
                            not existing_inner.get("provider_document_id")
                            and bool(new_inner.get("provider_document_id"))
                        )
                    )
                    update_metadata = (
                        canonical_json(document_metadata)
                        if prefer_new
                        else existing_document["metadata_json"]
                    )
                    connection.execute(
                        """UPDATE documents SET primary_source_id=COALESCE(?,primary_source_id),title=?,source_type=?,
                        document_kind=?,published_date=COALESCE(?,published_date),source_status=?,metadata_priority=?,
                        metadata_json=?,last_seen_at=? WHERE document_id=?""",
                        (
                            primary.source_id if primary else None,
                            title,
                            source_type.value,
                            document_kind,
                            published,
                            source_status,
                            root.priority,
                            update_metadata,
                            scan_time,
                            document_id,
                        ),
                    )
                else:
                    connection.execute(
                        "UPDATE documents SET last_seen_at=? WHERE document_id=?",
                        (scan_time, document_id),
                    )
                connection.execute(
                    "INSERT OR IGNORE INTO entities(entity_id,name,entity_kind) VALUES(?,?,?)",
                    (entity_id, entity_label, entity_kind),
                )
                connection.execute(
                    """INSERT INTO document_entities(document_id,entity_id,confidence,method) VALUES(?,?,?,?)
                    ON CONFLICT(document_id,entity_id) DO UPDATE SET confidence=MAX(confidence,excluded.confidence),method=excluded.method""",
                    (document_id, entity_id, confidence, method),
                )
                retired_group = (
                    existing_document is not None
                    and existing_document["source_status"] == "retired"
                )
                for item in observed:
                    candidate = item.candidate
                    location_status = (
                        "retired"
                        if retired_group
                        else ("active" if item.source_id else "quarantined")
                    )
                    connection.execute(
                        """INSERT INTO locations(location_id,root_id,relative_path,absolute_path,source_id,document_id,
                        role,location_status,observed_size,observed_mtime_ns,last_seen_run,manifest_json,metadata_json,error)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(root_id,relative_path) DO UPDATE SET
                        absolute_path=excluded.absolute_path,source_id=excluded.source_id,document_id=excluded.document_id,
                        role=excluded.role,
                        location_status=CASE WHEN locations.location_status='retired'
                                             THEN locations.location_status
                                             ELSE excluded.location_status END,
                        observed_size=excluded.observed_size,
                        observed_mtime_ns=excluded.observed_mtime_ns,last_seen_run=excluded.last_seen_run,
                        manifest_json=excluded.manifest_json,metadata_json=excluded.metadata_json,error=excluded.error""",
                        (
                            _location_id(root.root_id, candidate.relative_path),
                            root.root_id,
                            candidate.relative_path,
                            str(candidate.path.resolve()),
                            item.source_id,
                            document_id,
                            candidate.role,
                            location_status,
                            item.size,
                            item.mtime_ns,
                            run_id,
                            item.manifest_json,
                            canonical_json({"group_key": group_key, "source_status": source_status}),
                            item.error,
                        ),
                    )
                for obsolete_document_id in sorted(obsolete_document_ids):
                    if not obsolete_document_id.startswith(
                        "urn:company-wiki:document-logical:sha256:"
                    ):
                        continue
                    removable = connection.execute(
                        """SELECT 1 FROM documents d
                        WHERE d.document_id=?
                        AND d.primary_source_id IS NULL
                        AND d.source_status IN ('quarantined','incomplete')
                        AND NOT EXISTS (
                            SELECT 1 FROM locations l WHERE l.document_id=d.document_id
                        )
                        AND NOT EXISTS (
                            SELECT 1 FROM artifacts a WHERE a.document_id=d.document_id
                        )
                        AND NOT EXISTS (
                            SELECT 1 FROM llm_summary_failures f
                            WHERE f.document_id=d.document_id
                        )
                        AND NOT EXISTS (
                            SELECT 1 FROM evidence_spans e
                            WHERE e.document_id=d.document_id
                        )
                        AND NOT EXISTS (
                            SELECT 1 FROM document_fingerprint_state s
                            WHERE s.document_id=d.document_id
                        )
                        AND NOT EXISTS (
                            SELECT 1 FROM source_metadata_assertions a
                            WHERE a.document_id=d.document_id
                        )
                        AND NOT EXISTS (
                            SELECT 1 FROM document_retire_audit a
                            WHERE a.document_id=d.document_id
                        )
                        AND NOT EXISTS (
                            SELECT 1 FROM document_restore_audit a
                            WHERE a.document_id=d.document_id
                        )""",
                        (obsolete_document_id,),
                    ).fetchone()
                    if removable is None:
                        continue
                    connection.execute(
                        "DELETE FROM document_entities WHERE document_id=?",
                        (obsolete_document_id,),
                    )
                    connection.execute(
                        "DELETE FROM documents WHERE document_id=?",
                        (obsolete_document_id,),
                    )
        with store.transaction() as connection:
            connection.execute(
                "UPDATE locations SET location_status='missing' WHERE root_id=? AND last_seen_run<>? AND location_status<>'missing'",
                (root.root_id, run_id),
            )

    if dry_run:
        return ScanReport(
            run_id=run_id,
            files_seen=files_seen,
            files_excluded=files_excluded,
            policy_excluded=policy_excluded,
            dry_run=True,
            errors=errors,
            new_errors=new_errors,
            known_quarantined=known_quarantined,
            error_details=tuple(error_details),
        )
    active = store.fetchone("SELECT COUNT(*) AS count FROM locations WHERE location_status='active'")["count"]
    missing = store.fetchone("SELECT COUNT(*) AS count FROM locations WHERE location_status='missing'")["count"]
    report = ScanReport(
        run_id=run_id,
        files_seen=files_seen,
        files_hashed=files_hashed,
        files_reused=files_reused,
        files_excluded=files_excluded,
        policy_excluded=policy_excluded,
        locations_active=int(active),
        locations_missing=int(missing),
        errors=errors,
        new_errors=new_errors,
        known_quarantined=known_quarantined,
        error_details=tuple(error_details),
    )
    with store.transaction() as connection:
        completed_at = _utc_now()
        connection.execute(
            "UPDATE scan_runs SET completed_at=?,status=?,report_json=? WHERE run_id=?",
            (completed_at, "completed_with_errors" if errors else "completed", canonical_json(report.to_dict()), run_id),
        )
    return report


def scan_catalog(
    config: CatalogConfig,
    store: CatalogStore | None,
    *,
    dry_run: bool = False,
    root_ids: set[str] | None = None,
    progress: Callable[..., None] | None = None,
) -> ScanReport:
    if dry_run:
        return _scan_catalog_impl(
            config,
            store,
            dry_run=True,
            root_ids=root_ids,
            progress=progress,
        )
    if store is None:
        raise TypeError("store is required for a non-dry-run scan")
    selected_roots = _select_roots(config, root_ids)
    run_id = "scan-" + uuid.uuid4().hex
    scan_time = _utc_now()
    _begin_scan_run(store, run_id, scan_time)
    try:
        with store.coalesced_transactions(max_operations=250):
            return _scan_catalog_impl(
                config,
                store,
                dry_run=False,
                root_ids=root_ids,
                progress=progress,
                run_id=run_id,
                scan_time=scan_time,
                selected_roots=selected_roots,
                scan_run_started=True,
            )
    except Exception:
        _interrupt_scan_run(store, run_id)
        raise


__all__ = ["scan_catalog"]


class ScannerFacadeError(RuntimeError):
    """WU-500: the scanner seam failed closed."""


def scan_root_strategy(
    root: RootSpec,
    company_names: tuple[str, ...],
    *,
    progress: Callable[..., None] | None = None,
    master_identity: dict[str, tuple[str, str]] | None = None,
    portfolio_urls: dict[str, str] | None = None,
    v2_scan_shadow: bool = False,
) -> tuple[list[_Candidate], int, int]:
    """WU-500: scanner facade seam.  Default = v1 with identical behavior;
    the v2 shadow stub fails closed until implemented (SEAM-02)."""
    if v2_scan_shadow:
        raise ScannerFacadeError("v2 scanner unavailable (fail closed)")
    return _scan_root_v1(
        root,
        company_names,
        progress=progress,
        master_identity=master_identity,
        portfolio_urls=portfolio_urls,
    )
