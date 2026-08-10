"""FC-602: dayu portfolio adapter — group semantics + v1 enrichment.

Enumerates ``portfolio/{ticker}/filings/...`` groups: the group
``meta.json`` is merged with the v1 enrichment (provider/language
mapping, security_id/market backfill, EDGAR URL construction), the
preferred primary is selected by the same rules as scanner v1, and
metadata-only groups (byte-less placeholders — the real capture-
incomplete cause) never become candidates.  The enrichment lives here,
single source of truth; scanner v1 imports it (behavior unchanged).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .common import _walk_files
from .interface import NormalizedCandidate


def enrich_dayu_metadata(path: Path, metadata: dict) -> dict:
    """Merge the rich dayu filing ``meta.json`` (sibling of the primary
    document) into the document metadata (v1 ADR-008 Strategy B)."""
    meta_path = path.parent / "meta.json"
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return metadata
    if not isinstance(payload, dict):
        return metadata
    enriched: dict[str, object] = {}
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


def construct_edgar_url(metadata: dict) -> str | None:
    """Deterministically construct an SEC EDGAR URL from dayu SEC metadata
    (accession_number + company_id + primary_document)."""
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


def _group_key(relative: str) -> str:
    """v1 group-key rule: ticker/filings/{filing-id} (+ .rejections)."""
    parts = Path(relative).parts
    if len(parts) >= 3 and parts[1] == "filings":
        if len(parts) >= 4 and parts[2] == ".rejections":
            return str(Path(*parts[:4]).as_posix())
        return str(Path(*parts[:3]).as_posix())
    return relative


class DayuAdapter:
    """dayu layout: portfolio/{ticker}/filings/... + meta.json enrichment."""

    adapter_id = "dayu_filing_v1"
    version = "1.0.0"

    def enumerate(self, root_path: Path, *, limit: int | None = None) -> list[NormalizedCandidate]:
        candidates: list[NormalizedCandidate] = []
        groups: dict[str, list[Path]] = {}
        for path in sorted(_walk_files(root_path)):
            groups.setdefault(
                _group_key(path.relative_to(root_path).as_posix()), []
            ).append(path)
        for group_key, paths in sorted(groups.items()):
            parts = Path(group_key).parts
            group_dir = (
                root_path.joinpath(*parts)
                if len(paths) > 1 or Path(group_key).suffix == ""
                else paths[0].parent
            )
            metadata: dict = {}
            meta_path = group_dir / "meta.json"
            if meta_path.is_file():
                try:
                    loaded = json.loads(meta_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        metadata = loaded
                except (OSError, UnicodeError, json.JSONDecodeError):
                    metadata = {"meta_parse_error": True}
            names = {path.name: path for path in paths}
            preferred: Path | None = None
            for name in (
                str(metadata.get("selected_primary_document") or ""),
                str(metadata.get("primary_document") or ""),
            ):
                if name and name in names and not name.endswith("_docling.json"):
                    preferred = names[name]
                    break
            if preferred is None:
                preferred = next(
                    (path for path in paths if path.suffix.lower() == ".pdf"),
                    None,
                )
            if preferred is None:
                preferred = next(
                    (path for path in paths
                     if path.suffix.lower() in {".htm", ".html"}
                     and path.name != "meta.json"),
                    None,
                )
            if preferred is None:
                preferred = next(
                    (path for path in paths
                     if path.name != "meta.json"
                     and not path.name.endswith("manifest.json")
                     and not path.name.endswith("_docling.json")),
                    None,
                )
            if preferred is None:
                # metadata-only group (no preferred file): never ingest a
                # byte-less placeholder (v1 Phase 15.4 rule).
                continue
            metadata = enrich_dayu_metadata(preferred, metadata)
            if not metadata.get("source_url") and not metadata.get("https_url"):
                edgar_url = construct_edgar_url(metadata)
                if edgar_url is not None:
                    metadata.setdefault("source_url", edgar_url)
            if not metadata.get("market") and metadata.get("accession_number"):
                metadata["market"] = "US"
            if not metadata.get("security_id") and metadata.get("ticker"):
                metadata["security_id"] = str(metadata["ticker"])
            if not metadata.get("market") and parts:
                ticker = parts[0]
                entity_meta_path = root_path / ticker / "meta.json"
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
            for path in sorted(paths):
                if path.name == "meta.json" or path.name.endswith("manifest.json"):
                    role = "metadata"
                elif path.name.endswith("_docling.json"):
                    role = "processed_docling"
                elif path == preferred:
                    role = "original_primary"
                else:
                    role = "original_attachment"
                candidates.append(NormalizedCandidate(
                    relative_path=path.relative_to(root_path).as_posix(),
                    content_sha256=_sha256_file(path),
                    group_key=group_key,
                    role=role,
                    normalized=metadata,
                ))
            if limit is not None and len(candidates) >= limit:
                break
        return candidates


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


__all__ = ["DayuAdapter", "construct_edgar_url", "enrich_dayu_metadata"]
