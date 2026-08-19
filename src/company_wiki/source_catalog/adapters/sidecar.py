"""WU-701: sidecar_filing_v1 adapter — Dropbox-shaped roots with
``.source.json`` sidecars.

A complete sidecar (schema_version, identity, kind, period, content hash,
provenance) yields a candidate for admission.  Missing fields degrade to
indexed_only with an exact remediation reason — never guessed from the
filename (F-043).  Paths inside sidecars must be relative to the current
file group; absolute paths and ``..`` are rejected.  A standalone sidecar
is never an original document.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .interface import NormalizedCandidate

SIDECAR_SCHEMA_VERSION = "1.0"
_REQUIRED_IDENTITY = ("canonical_entity_id", "market", "security_id")
_REQUIRED_FACTS = ("document_kind", "fiscal_year", "period_end", "content_sha256")
_REQUIRED_PROVENANCE = ("provider", "provider_document_id")

_ABSOLUTE_PATH = re.compile(r"^([A-Za-z]:[\\/]|/|\\\\)")


class SidecarFilingAdapter:
    """sidecar layout: files + ``<name>.source.json`` sidecars."""

    adapter_id = "sidecar_filing_v1"
    version = "1.0.0"

    def __init__(self, *, sidecar_suffix: str = ".source.json"):
        self._suffix = sidecar_suffix

    def enumerate(
        self, root_path: Path, *, limit: int | None = None
    ) -> list[NormalizedCandidate]:
        candidates: list[NormalizedCandidate] = []
        for path in sorted(root_path.rglob("*")):
            if not path.is_file():
                continue
            if path.name.endswith(self._suffix):
                continue
            sidecar = path.with_name(path.name + self._suffix)
            if not sidecar.is_file():
                candidates.append(
                    NormalizedCandidate(
                        relative_path=path.relative_to(root_path).as_posix(),
                        content_sha256=_sha256_file(path),
                        group_key=path.relative_to(root_path).as_posix(),
                        role="original_primary",
                        normalized={},
                        evidence={"remediation": "missing_sidecar"},
                    )
                )
                continue
            sidecar_payload = _parse_sidecar(sidecar)
            problems = _validate_sidecar(sidecar_payload, path)
            role = "original_primary" if not problems else "indexed_only"
            candidates.append(
                NormalizedCandidate(
                    relative_path=path.relative_to(root_path).as_posix(),
                    content_sha256=_sha256_file(path),
                    group_key=path.relative_to(root_path).as_posix(),
                    role=role,
                    normalized=_normalized_from_sidecar(sidecar_payload, path),
                    evidence={"remediation": ";".join(problems)} if problems else {},
                )
            )
            if limit is not None and len(candidates) >= limit:
                break
        return candidates


def _parse_sidecar(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return {"_parse_error": True}
    return payload if isinstance(payload, dict) else {"_parse_error": True}


def _validate_sidecar(payload: dict, primary: Path) -> list[str]:
    """Return remediation reasons; [] = complete sidecar."""
    problems: list[str] = []
    if payload.get("_parse_error"):
        return ["sidecar_parse_failed"]
    if payload.get("schema_version") != SIDECAR_SCHEMA_VERSION:
        problems.append("unknown_schema_version")
    for field in _REQUIRED_IDENTITY:
        if not payload.get(field):
            problems.append(f"missing_identity:{field}")
    for field in _REQUIRED_FACTS:
        if not payload.get(field):
            problems.append(f"missing:{field}")
    for field in _REQUIRED_PROVENANCE:
        if not payload.get(field):
            problems.append(f"missing_provenance:{field}")
    # DBX-03: the declared content hash must match the primary file bytes
    declared = payload.get("content_sha256")
    if declared:
        actual = _sha256_file(primary)
        if declared != actual:
            problems.append("content_hash_mismatch")
    # path rules: only relative paths inside the current file group
    for key in ("primary_relative_path", "canonical_path"):
        value = payload.get(key)
        if not isinstance(value, str):
            continue
        if _ABSOLUTE_PATH.match(value) or ".." in value.replace("\\", "/").split("/"):
            problems.append(f"path_escape:{key}")
    return problems


def _normalized_from_sidecar(payload: dict, primary: Path) -> dict:
    """Map sidecar facts into a NormalizedFilingMetadata-shaped dict."""
    if payload.get("_parse_error"):
        return {}
    return {
        "schema_version": "2.0",
        "canonical_entity_id": payload.get("canonical_entity_id"),
        "display_name": payload.get("display_name"),
        "market": payload.get("market"),
        "security_id": payload.get("security_id"),
        "document_kind": payload.get("document_kind"),
        "fiscal_year": str(payload.get("fiscal_year", "")) or None,
        "period_end": payload.get("period_end"),
        "provider": payload.get("provider"),
        "provider_document_id": payload.get("provider_document_id"),
        "source_url": payload.get("source_url"),
        "published_at": payload.get("published_at"),
        "filed_at": payload.get("filed_at"),
        "accepted_at": payload.get("accepted_at"),
        "language": payload.get("language"),
        "revision_id": payload.get("revision_id"),
        "content_sha256": payload.get("content_sha256"),
        "adapter_id": "sidecar_filing_v1",
        "adapter_version": "1.0.0",
        "normalization_status": "capture_ready",
        # ZR-501: broker_research metadata contract — additive passthrough;
        # absent keys stay absent (never invented from the filename).
        "publisher": payload.get("publisher"),
        "authors": tuple(payload.get("authors") or ()),
        "security_ids": tuple(payload.get("security_ids") or ()),
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
