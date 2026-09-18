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
#: The legacy metadata CONTAINERS.  FC-502: the sidecar adapter builds its normalized output
#: from the sidecar's own flat facts and never borrows these (a sidecar carrying them must not
#: become a second metadata source).
_LEGACY_CONTAINER_KEYS = frozenset({"acquisition", "dayu_meta"})
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


def _sidecar_fiscal_year(value: object) -> int | str | None:
    """Keep the CONTAINER type the SQL filter needs.

    `query_filing_candidates(fiscal_year=N)` filters in SQL with
    `json_extract(metadata_json, '$.acquisition.fiscal_year') = ?` bound to an INTEGER, and
    SQLite compares types strictly - so a year stored as the string "2025" silently matches
    nothing.  The legacy walk wrote the sidecar's own JSON (an int) and the first version of
    this mapping stringified it, which is a real defect for any adapter-scanned root
    (measured 2026-09-18 while fixing F-BAR-10: `test_r4b05_container_shape_...` asserts the
    int, and the filtered query returned nothing).  Ints pass through, digit strings are
    coerced, and nothing is invented from a filename.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):  # bool is an int subclass - never a year
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    return int(text) if text.isdigit() else text


def _normalized_from_sidecar(payload: dict, primary: Path) -> dict:
    """Map sidecar facts into a NormalizedFilingMetadata-shaped dict.

    CONTRACT NOTE (F-BAR-14, measured 2026-09-18): the adapter path REPLACES the legacy walk
    for a root that declares an adapter, and the legacy walk wrote the WHOLE sidecar into the
    document's `acquisition` block.  A fixed mapping therefore silently narrowed the metadata:
    the first version of this function dropped `form_type` (resolver's form gate answered
    `form_type_mismatch`), `company_name` (entity anchoring), `source_title` (the title
    derivation, which also made B05's provenance stop seeing a declared-title conflict) and
    the older `filing_date` spelling (`published_date_unknown`).

    The rule now: **declared keys pass through, the canonical mapping below overlays the keys
    this adapter owns.**  That restores the legacy information set while keeping the
    normalized type fixes (fiscal_year stays an int so the SQL filter matches, the two date
    spellings are aliased, and the adapter identity is declared).
    """
    if payload.get("_parse_error"):
        return {}
    # FC-502: the adapter must NOT echo the legacy containers.  A sidecar that happens to
    # carry `acquisition`/`dayu_meta` keys must not have them borrowed into the normalized
    # output - those containers belong to the legacy walk, and copying them would let a
    # sidecar inject a second, contradictory metadata source.  Everything else declared in
    # the sidecar DOES pass through (F-BAR-14).
    normalized: dict = {
        key: value for key, value in payload.items()
        if key not in _LEGACY_CONTAINER_KEYS and key != "_parse_error"
    }
    normalized.update({
        "schema_version": "2.0",
        "canonical_entity_id": payload.get("canonical_entity_id"),
        "display_name": payload.get("display_name"),
        # Entity anchoring reads `company_name` (B08 level 2 measured that the sidecar's own
        # name is the only honest anchor for an external root); the sidecar may spell it
        # `company_name` or only `display_name`, so the first non-empty one wins.
        "company_name": payload.get("company_name") or payload.get("display_name"),
        "market": payload.get("market"),
        "security_id": payload.get("security_id"),
        "document_kind": payload.get("document_kind"),
        "fiscal_year": _sidecar_fiscal_year(payload.get("fiscal_year")),
        "fiscal_period": payload.get("fiscal_period"),
        "period_end": payload.get("period_end"),
        # Both spellings reach the container: the scanner derives the document's published
        # date from `filing_date` (falling back to `published_date`), and sidecars in the wild
        # use either `published_at` or `filing_date`.
        "filing_date": payload.get("published_at") or payload.get("filing_date"),
        "form_type": payload.get("form_type"),
        "provider": payload.get("provider"),
        "provider_document_id": payload.get("provider_document_id"),
        "source_url": payload.get("source_url"),
        "published_at": payload.get("published_at") or payload.get("filing_date"),
        "filed_at": payload.get("filed_at"),
        "accepted_at": payload.get("accepted_at"),
        "language": payload.get("language"),
        "revision_id": payload.get("revision_id"),
        "content_sha256": payload.get("content_sha256"),
        "adapter_id": "sidecar_filing_v1",
        "adapter_version": "1.0.0",
        "normalization_status": "capture_ready",
        # ZR-501: broker_research metadata contract - additive passthrough;
        # absent keys stay absent (never invented from the filename).
        "publisher": payload.get("publisher"),
        "authors": tuple(payload.get("authors") or ()),
        "security_ids": tuple(payload.get("security_ids") or ()),
    })
    return normalized


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
