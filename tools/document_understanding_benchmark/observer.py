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

from .schema import UNUSABLE_BLOCKS

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

    # Measure legibility over everything the parser read, so a broken font
    # mapping is visible even when the selector retains only a small sample. A
    # real garbled PDF produced 9,618 units and 270k unusable characters while
    # the selection held only 195 characters.
    read_text = "".join(getattr(unit, "raw_text", "") or "" for unit in units)
    unusable_ratio, unusable_chars, dense_chars = _unusable_block_ratio(read_text)

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
            "read_text_dense_chars": dense_chars,
            "unusable_block_ratio": (
                round(unusable_ratio, 5) if unusable_ratio is not None else None
            ),
            "unusable_block_chars": unusable_chars,
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


def _unusable_block_ratio(text: str) -> tuple[float | None, int, int]:
    """Share of characters in blocks legitimate prose never uses.

    Measured over everything the parser read, not just what the selector kept:
    a garbled document can have hundreds of thousands of unusable characters
    while the selector retains only a couple of hundred, and judging only the
    selection would miss it entirely.
    """

    dense = [char for char in text if not char.isspace()]
    if not dense:
        return (None, 0, 0)
    unusable = sum(1 for char in dense if _in_unusable_block(char))
    return (unusable / len(dense), unusable, len(dense))


def _in_unusable_block(char: str) -> bool:
    code = ord(char)
    return any(low <= code <= high for low, high in UNUSABLE_BLOCKS)


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


# Carriers the existing public observation path can actually take in. Measured,
# not assumed: `narrative_retrieval` offers exactly two replay formats (PDF, and
# transcript_txt/transcript_html), so a non-transcript HTML document has no
# route into the selector.
SUPPORTED_CARRIERS: dict[str, dict[str, Any]] = {
    ".pdf": {"entry_point": "parse_pdf_bytes", "kind": "pdf", "supported": True},
    ".txt": {"entry_point": "parse_transcript_text", "kind": "transcript", "supported": True},
    ".md": {"entry_point": "parse_transcript_text", "kind": "transcript", "supported": True},
    ".htm": {
        "entry_point": None,
        "kind": "html",
        "supported": False,
        "reason": (
            "the only HTML path is transcript_html, which expects a transcript "
            "layout; an SEC filing HTML has no route into the selector"
        ),
    },
    ".html": {
        "entry_point": None,
        "kind": "html",
        "supported": False,
        "reason": "same as .htm",
    },
    ".pptx": {"entry_point": None, "kind": "presentation", "supported": False, "reason": "no public entry point"},
}


def carrier_support(path: Path) -> dict[str, Any]:
    """Report whether the current public path can observe this carrier."""

    suffix = _suffix(Path(path))
    info = SUPPORTED_CARRIERS.get(
        suffix,
        {
            "entry_point": None,
            "kind": "unknown",
            "supported": False,
            "reason": f"unrecognized carrier {suffix!r}",
        },
    )
    return {"suffix": suffix, **info}


def probe_non_pdf_html(path: Path) -> dict[str, Any]:
    """Measure what the transcript path does with a non-transcript HTML document.

    Returns a truthful verdict instead of an exception: the existing extractor
    does not refuse a 10-K, it yields **zero units** and reports
    ``transcript_start_missing``. That distinction matters, because a
    zero-unit parse looks like a document with no content rather than an
    unsupported carrier.
    """

    module = _import_evidence()
    target = Path(path)
    data = target.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    try:
        from company_wiki.source_catalog.transcript_text_extract import (
            TranscriptMaterialError,
            extract_transcript_material,
        )
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ObserverUnavailable(f"cannot import the HTML extractor: {exc}") from exc

    report: dict[str, Any] = {
        "path": str(target),
        "suffix": _suffix(target),
        "sha256": sha,
        "extracted": False,
        "units": None,
        "page_count": None,
        "errors": [],
        "text_prefix": "",
    }
    try:
        material = extract_transcript_material(data, mime_type="text/html")
        material.verify(data)
    except TranscriptMaterialError as exc:
        report["refused"] = True
        report["errors"] = [f"transcript_material_refused: {exc}"]
        return report

    report["extracted"] = True
    text = material.text_utf8
    report["text_prefix"] = text[:200]
    report["text_chars"] = len(text)
    parsed = module.parse_transcript_text(
        text,
        source_id=f"urn:company-wiki:source:sha256:{sha}",
        source_sha256=sha,
        language="en",
    )
    report["units"] = len(parsed.units)
    report["page_count"] = parsed.page_count
    report["line_count"] = parsed.line_count
    report["errors"] = list(parsed.errors)
    report["usable"] = bool(parsed.units)
    return report
