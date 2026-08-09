"""WU-601: company_raw adapter — mechanically extracted from scanner v1.

Enumerates ``companies/{company}/raw/`` trees with sidecar pairing.  The
decision/identity/hash semantics are byte-for-byte what scanner v1 produced
(parity tests lock this); known-bad behaviors are NOT fixed here — they get
separate RED owners (WU-603).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .common import (
    _ACQUISITION_SIDECAR_SUFFIX,
    _load_acquisition_metadata,
    _relative,
    _walk_files,
)
from .interface import NormalizedCandidate


class CompanyRawAdapter:
    """company_raw layout: companies/{company}/raw/... + .source.json."""

    adapter_id = "company_raw_v1"
    version = "1.0.0"

    def __init__(self, *, portfolio_urls: dict[str, str] | None = None):
        self._portfolio_urls = portfolio_urls or {}

    def enumerate(self, root_path: Path, *, limit: int | None = None) -> list[NormalizedCandidate]:
        candidates: list[NormalizedCandidate] = []
        for company in sorted(
            (item for item in root_path.iterdir() if item.is_dir()),
            key=lambda item: item.name,
        ):
            raw = company / "raw"
            if not raw.is_dir():
                continue
            paths = sorted(_walk_files(raw))
            sidecars = {
                str(path)[: -len(_ACQUISITION_SIDECAR_SUFFIX)]: path
                for path in paths
                if path.name.endswith(_ACQUISITION_SIDECAR_SUFFIX)
            }
            primary_paths = [
                path for path in paths
                if not path.name.endswith(_ACQUISITION_SIDECAR_SUFFIX)
            ]
            for path in primary_paths:
                relative = _relative(path, root_path)
                sidecar = sidecars.get(str(path))
                metadata = _load_acquisition_metadata(sidecar) if sidecar else {}
                # Phase 16.1: sidecar without URL enriched from dayu meta
                if not metadata.get("source_url") and not metadata.get("https_url"):
                    portfolio_url = self._portfolio_urls.get(company.name)
                    if portfolio_url:
                        metadata = dict(metadata)
                        metadata["source_url"] = portfolio_url
                # Phase 18.4: SEC company_raw identity backfill
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
                candidates.append(NormalizedCandidate(
                    relative_path=relative,
                    content_sha256=_sha256_file(path),
                    group_key=relative,
                    role="original_primary",
                    normalized=metadata,
                    evidence={"entity": {"origin": "directory",
                                         "source_pointer": "company-name"}},
                ))
                if sidecar is not None:
                    candidates.append(NormalizedCandidate(
                        relative_path=_relative(sidecar, root_path),
                        content_sha256=_sha256_file(sidecar),
                        group_key=relative,
                        role="metadata",
                        normalized=metadata,
                    ))
            primary_names = {str(path) for path in primary_paths}
            for target, sidecar in sorted(sidecars.items()):
                if target in primary_names:
                    continue
                relative = _relative(sidecar, root_path)
                candidates.append(NormalizedCandidate(
                    relative_path=relative,
                    content_sha256=_sha256_file(sidecar),
                    group_key=relative[: -len(_ACQUISITION_SIDECAR_SUFFIX)],
                    role="metadata",
                    normalized=_load_acquisition_metadata(sidecar),
                ))
            if limit is not None and len(candidates) >= limit:
                break
        return candidates


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
