"""Read-only observation of the *existing* public parser/selector.

This module is the only place that touches ``company_wiki``. It never writes,
never re-implements selection, and never fabricates a field the current
implementation does not produce. Anything the baseline cannot produce (route
family, semantic units, claims) is reported as absent so the oracle says
``NOT_EVALUATED`` instead of pretending the baseline passed.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

OBSERVED_ENTRY_POINT = "company_wiki.source_catalog.narrative_evidence"

# The baseline selector may report a document kind, but it has no du-route/1
# family/regime axis. Mapping is therefore explicit and intentionally narrow:
# an unmapped kind stays None and the route check reports NOT_EVALUATED.
_KIND_TO_FAMILY: dict[str, str] = {
    "annual_report": "annual",
    "semi_annual_report": "interim",
    "quarterly_report": "quarterly",
    "prospectus": "prospectus",
    "convertible_bond_prospectus": "offering",
    "equity_offering_prospectus": "offering",
    "investor_relations": "investor_qa",
    "investor_call_transcript": "earnings_call",
    "ir_policy": "administrative",
    "meeting_notice": "administrative",
}


class ObserverUnavailable(RuntimeError):
    """The observation surface itself is missing (refused run, not a FAIL)."""


def _import_evidence() -> Any:
    try:
        from company_wiki.source_catalog import narrative_evidence
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ObserverUnavailable(f"cannot import the observation surface: {exc}") from exc
    return narrative_evidence


def _suffix(path: Path) -> str:
    return path.suffix.casefold()


def _decode_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _parse(module: Any, path: Path, source_id: str, sha: str) -> tuple[Any, str]:
    """Parse through the existing public entry point for the real carrier."""

    suffix = _suffix(path)
    if suffix == ".pdf":
        data = path.read_bytes()
        parsed = module.parse_pdf_bytes(
            data,
            source_id=source_id,
            source_sha256=sha,
            language="zh",
        )
        return parsed, "parse_pdf_bytes"
    if suffix in {".txt", ".md"}:
        text = _decode_text(path)
        parsed = module.parse_transcript_text(
            text,
            source_id=source_id,
            source_sha256=sha,
            language="en",
        )
        return parsed, "parse_transcript_text"
    raise ObserverUnavailable(f"no existing public parser for suffix {suffix!r}")


def _span_locator(span: Any) -> str:
    locator = getattr(span, "locator", None)
    if isinstance(locator, str) and locator:
        return locator
    coordinates = getattr(span, "coordinates", None)
    if coordinates is not None and hasattr(coordinates, "locator"):
        return coordinates.locator()
    return ""


def _unit_locator(unit: Any) -> str:
    coordinates = getattr(unit, "coordinates", None)
    if coordinates is not None and hasattr(coordinates, "locator"):
        return coordinates.locator()
    return ""


def observe_native(
    path: Path,
    *,
    sha256: str,
    sample_id: str,
    existing_kind: str = "unknown",
) -> dict[str, Any]:
    """Observe one original with the existing public parser and selector.

    Only reads ``path``; the SHA is verified before parsing, so a changed
    original becomes ``UNAVAILABLE`` rather than a silently different result.
    """

    module = _import_evidence()
    target = Path(path)

    started = time.monotonic()
    actual_sha = hashlib.sha256(target.read_bytes()).hexdigest()
    read_seconds = time.monotonic() - started
    if actual_sha != sha256:
        return {
            "schema_version": "du-observed/1",
            "sample_id": sample_id,
            "source_sha256": sha256,
            "route": None,
            "selected_locators": [],
            "selected_text": "",
            "semantic_units": [],
            "claims": [],
            "coverage": {
                "native_scan": "unavailable",
                "complete": False,
                "opaque_pages": [],
                "deferred_unit_ids": [],
                "unassigned_unit_ids": [],
            },
            "metrics": {},
            "execution": {
                "entry_point": OBSERVED_ENTRY_POINT,
                "parser_version": None,
                "selector_version": None,
                "calls": 0,
                "elapsed_seconds": round(read_seconds, 3),
                "mode": "native",
                "reason": "source SHA-256 changed before parsing",
            },
        }

    source_id = f"urn:company-wiki:source:sha256:{sha256}"
    started = time.monotonic()
    parsed, parse_entry = _parse(module, target, source_id, sha256)
    parse_seconds = time.monotonic() - started

    started = time.monotonic()
    package = module.select_narrative_evidence(
        parsed,
        title=target.name,
        existing_kind=existing_kind,
        selector_version=module.NARRATIVE_SELECTOR_VERSION,
    )
    select_seconds = time.monotonic() - started

    spans: Sequence[Any] = tuple(package.evidence_spans)
    selected_locators = [_span_locator(span) for span in spans]
    selected_text = "\n".join(
        span.raw_text for span in spans if getattr(span, "raw_text", None)
    )

    units = tuple(getattr(parsed, "units", ()) or ())
    opaque_pages = sorted(int(page) for page in (getattr(parsed, "opaque_pages", ()) or ()))
    page_count = int(getattr(parsed, "page_count", 0) or 0)
    pages_read = int(getattr(parsed, "pages_read", 0) or 0)
    native_scan = "complete" if getattr(parsed, "coverage_complete", False) else "partial"
    if page_count == 0 and not units:
        native_scan = "unavailable"

    document_kind = getattr(package, "document_kind", None)
    family = _KIND_TO_FAMILY.get(document_kind or "")

    # The baseline produces no du-route/1, no semantic units and no claims.
    # Reporting them as absent is the honest observation; it is what makes the
    # oracle return NOT_EVALUATED for those dimensions.
    route = (
        {
            "family": family,
            "regime": None,
            "confidence": None,
            "document_kind": document_kind,
            "profile_id": None,
            "raw_source": "baseline_document_kind",
        }
        if document_kind
        else None
    )

    return {
        "schema_version": "du-observed/1",
        "sample_id": sample_id,
        "source_sha256": sha256,
        "route": route,
        "selected_locators": selected_locators,
        "selected_text": selected_text,
        "semantic_units": [],
        "claims": [],
        "coverage": {
            "native_scan": native_scan,
            "complete": bool(getattr(package, "coverage_complete", False)),
            "structured_unit_count": len(units),
            "opaque_pages": opaque_pages,
            "deferred_unit_ids": [],
            "unassigned_unit_ids": [],
        },
        "metrics": {
            "selected_spans": len(spans),
            "candidate_count": int(getattr(package, "candidate_count", 0) or 0),
            "source_units": int(getattr(package, "source_units", len(units)) or 0),
            "dropped_financial_count": int(getattr(package, "dropped_financial_count", 0) or 0),
            "omitted_candidate_count": int(getattr(package, "omitted_candidate_count", 0) or 0),
            "selection_limit": int(getattr(package, "selection_limit", 0) or 0),
            "page_count": page_count,
            "pages_read": pages_read,
            "selected_text_bytes": len(selected_text.encode("utf8")),
            "parse_seconds": round(parse_seconds, 3),
            "select_seconds": round(select_seconds, 3),
            "selector_status": getattr(package, "status", None),
        },
        "execution": {
            "entry_point": OBSERVED_ENTRY_POINT,
            "parse_entry": parse_entry,
            "parser_version": getattr(parsed, "parser_version", None)
            or getattr(module, "NARRATIVE_PARSER_VERSION", None),
            "selector_version": getattr(module, "NARRATIVE_SELECTOR_VERSION", None),
            "calls": 0,
            "elapsed_seconds": round(parse_seconds + select_seconds, 3),
            "mode": "native",
        },
        "raw": {
            "carrier": _suffix(target),
            "selector_status": getattr(package, "status", None),
        },
    }


def observe_du_adapter(
    adapter: Any,
    observation: Mapping[str, Any],
    *,
    sample_id: str,
    sha256: str,
) -> dict[str, Any]:
    """Observe through a ROOT-injected adapter once one exists.

    ``adapter`` is any callable taking a ``du-input/1`` mapping and returning
    either a ``du-observed/1`` mapping or a mapping with ``route`` /
    ``semantic_units`` / ``claims`` keys. Until ROOT injects one, native runs
    report the baseline and mark the new-structure dimensions NOT_EVALUATED.
    """

    if not callable(adapter):
        raise ObserverUnavailable("adapter must be callable")
    produced = adapter(dict(observation))
    if not isinstance(produced, Mapping):
        raise ObserverUnavailable("adapter must return a mapping")
    merged = dict(produced)
    merged.setdefault("schema_version", "du-observed/1")
    merged.setdefault("sample_id", sample_id)
    merged.setdefault("source_sha256", sha256)
    return dict(merged)
