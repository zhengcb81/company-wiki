"""The seven frozen checks of `identity-audit-receipt/1` (card section 5.4).

``audit`` compares what a request claims about exact source versions with what
the read side actually returns.  It is strictly read-only: the only side
effects are reading the config bytes to bind them into the receipt.  A check
that cannot reach a verdict is ``not_applicable``/``not_evaluated``/``null``
-- never silently converted into a pass.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.security_code import (
    canonical_security_code,
    security_codes_equivalent,
)
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef

from .export import IDENTITY_FIELDS, PERIOD_FIELDS, read_source, string_or_none
from .receipt import (
    CHECK_AVAILABILITY_UNKNOWN,
    CHECK_FAIL,
    CHECK_NOT_APPLICABLE,
    CHECK_NOT_EVALUATED,
    CHECK_PASS,
    DEPENDENCY_UNAVAILABLE,
    INVALID_ARGUMENT,
    LIMIT_EXCEEDED,
    LIMITATIONS,
    MAX_EVIDENCE_SPANS,
    MAX_RECEIPT_BYTES,
    MAX_SOURCE_REFS,
    P3_BYTES_MISMATCH,
    P3_IDENTITY_CONFLICT,
    P3_PERIOD_CONFLICT,
    P3_RECEIPT_SCHEMA,
    P3_REF_MISMATCH,
    P3_REQUEST_SCHEMA,
    P3_SPAN_UNGROUNDED,
    P3_UNIT_MISMATCH,
    RECEIPT_TOO_LARGE,
    TOP_BLOCKED,
    TOP_FAIL,
    TOP_OK,
    TOP_PARTIAL,
    TOP_UNAVAILABLE,
    canonical_json,
    is_sha256,
    sha256_hex,
    utc_now,
)

__all__ = [
    "MAX_EVIDENCE_SPANS",
    "MAX_RECEIPT_BYTES",
    "MAX_SOURCE_REFS",
    "audit",
]

COUNT_FIELDS = (
    "checked",
    "passed",
    "failed",
    "not_applicable",
    "not_evaluated",
)

_CHECK_ORDER = (
    "ref",
    "bytes",
    "identity",
    "period",
    "availability",
    "spans",
    "unit",
)

_REQUEST_KEYS = frozenset({"schema_version", "source_refs", "evidence_spans", "expect"})
_REF_FIELDS = frozenset(
    {
        "document_id",
        "source_id",
        "content_sha256",
        "byte_size",
        "mime_type",
        "schema_version",
    }
)
_SPAN_KEYS = frozenset(
    {
        "schema_version",
        "span_id",
        "source_id",
        "locator",
        "coordinates",
        "raw_text",
        "structured_value",
        "parser_name",
        "parser_version",
        "output_sha256",
        "parse_status",
        "quality_flags",
    }
)
_COORDINATE_OFFSETS = (
    "page_number",
    "paragraph_index",
    "table_index",
    "row_index",
    "column_index",
)

_REFERENCE_SCHEMA_VERSION = "2.0"

# Card section 5.4(7): the closed unit-token set, verbatim.  No conversion and
# no inference happens past this lexer.
_UNIT_PATTERNS = (
    re.compile(r"单位[:：]\s*(人民币)?(百万元|千万元|万元|千元|亿元|元)"),
    re.compile(r"(人民币|RMB|CNY|USD|HKD|million|billion|thousand)"),
    re.compile(r"[%％]"),
)
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


# ---------------------------------------------------------------------------
# receipt shell helpers
# ---------------------------------------------------------------------------


def _zero_counts() -> dict[str, int]:
    return {name: 0 for name in COUNT_FIELDS}


def _shell(
    status: str,
    generated_at: str,
    inputs: dict[str, Any],
    reason: str | None = None,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": P3_RECEIPT_SCHEMA,
        "status": status,
        "generated_at": generated_at,
        "inputs": inputs,
        "counts": _zero_counts(),
        "limitations": list(LIMITATIONS),
        "sources": [],
    }
    if reason is not None:
        receipt["reason"] = reason
    return receipt


def _entry(
    status: str,
    *,
    detail: dict[str, Any] | None = None,
    error_code: str | None = None,
    reason: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "status": status,
        "detail": detail if detail is not None else {},
    }
    if error_code is not None:
        entry["error_code"] = error_code
    if reason is not None:
        entry["reason"] = reason
    entry.update(extra)
    return entry


def _not_evaluated(reason: str) -> dict[str, Any]:
    return _entry(CHECK_NOT_EVALUATED, reason=reason)


def _input_binding(config_path: Any) -> dict[str, Any]:
    """Bind the config file bytes into the receipt (read-only)."""
    try:
        data = Path(config_path).read_bytes()
    except OSError:
        return {}
    return {"sha256": sha256_hex(data), "bytes": len(data)}


# ---------------------------------------------------------------------------
# request validation (blocked receipts, never exceptions)
# ---------------------------------------------------------------------------


def _validate_request(request: Any) -> str | None:
    """Return a blocking reason for a malformed request, else ``None``."""
    if not isinstance(request, dict):
        return INVALID_ARGUMENT
    unknown = sorted(set(request) - _REQUEST_KEYS)
    if unknown:
        return INVALID_ARGUMENT
    if request.get("schema_version") != P3_REQUEST_SCHEMA:
        return INVALID_ARGUMENT
    refs = request.get("source_refs")
    if not isinstance(refs, list) or not refs:
        return INVALID_ARGUMENT
    if len(refs) > MAX_SOURCE_REFS:
        return LIMIT_EXCEEDED
    spans = request.get("evidence_spans")
    if not isinstance(spans, list):
        return INVALID_ARGUMENT
    if len(spans) > MAX_EVIDENCE_SPANS:
        return LIMIT_EXCEEDED
    expect = request.get("expect")
    if expect is not None and not isinstance(expect, dict):
        return INVALID_ARGUMENT
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != _REF_FIELDS:
            return INVALID_ARGUMENT
        if ref["schema_version"] != _REFERENCE_SCHEMA_VERSION:
            return INVALID_ARGUMENT
        if not _valid_ref_text(ref["document_id"]) or not _valid_ref_text(
            ref["source_id"]
        ):
            return INVALID_ARGUMENT
        if not is_sha256(ref["content_sha256"]):
            return INVALID_ARGUMENT
        if isinstance(ref["byte_size"], bool) or not isinstance(ref["byte_size"], int):
            return INVALID_ARGUMENT
        if ref["byte_size"] <= 0 or not _valid_ref_text(ref["mime_type"]):
            return INVALID_ARGUMENT
    if expect is not None:
        allowed = set(IDENTITY_FIELDS) | set(PERIOD_FIELDS)
        if set(expect) - allowed:
            return INVALID_ARGUMENT
    for span in spans:
        problem = _validate_span(span)
        if problem is not None:
            return problem
    return None


def _valid_ref_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_span(span: Any) -> str | None:
    if not isinstance(span, dict) or set(span) != _SPAN_KEYS:
        return INVALID_ARGUMENT
    if not _valid_ref_text(span["source_id"]):
        return INVALID_ARGUMENT
    coordinates = span["coordinates"]
    if not isinstance(coordinates, dict):
        return INVALID_ARGUMENT
    for name in _COORDINATE_OFFSETS + ("char_start", "char_end"):
        value = coordinates.get(name)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return INVALID_ARGUMENT
    if span["raw_text"] is not None and not isinstance(span["raw_text"], str):
        return INVALID_ARGUMENT
    return None


# ---------------------------------------------------------------------------
# per-check implementations
# ---------------------------------------------------------------------------


def _ref_check(read: Any, requested: SourceRef) -> dict[str, Any]:
    catalog_ref = read.catalog_ref
    if catalog_ref is None:
        refusal = read.refusal
        detail = refusal.as_dict() if refusal is not None else {}
        return _entry(
            CHECK_FAIL, detail={"refusal": detail}, error_code=P3_REF_MISMATCH
        )
    diffs: dict[str, Any] = {}
    if requested.byte_size != catalog_ref.byte_size:
        diffs["byte_size"] = requested.byte_size
        diffs["observed_byte_size"] = catalog_ref.byte_size
    if requested.mime_type != catalog_ref.mime_type:
        diffs["mime_type"] = requested.mime_type
        diffs["observed_mime_type"] = catalog_ref.mime_type
    if requested.content_sha256 != catalog_ref.content_sha256:
        diffs["content_sha256"] = requested.content_sha256
        diffs["observed_content_sha256"] = catalog_ref.content_sha256
    if diffs:
        return _entry(CHECK_FAIL, detail=diffs, error_code=P3_REF_MISMATCH)
    return _entry(
        CHECK_PASS,
        detail={
            "byte_size": catalog_ref.byte_size,
            "mime_type": catalog_ref.mime_type,
            "content_sha256": catalog_ref.content_sha256,
        },
    )


def _bytes_check(read: Any, requested: SourceRef) -> dict[str, Any]:
    if read.data is not None:
        return _entry(
            CHECK_PASS,
            detail={"sha256": sha256_hex(read.data), "bytes": len(read.data)},
        )
    refusal = read.refusal
    detail: dict[str, Any] = {"requested_sha256": requested.content_sha256}
    if refusal is not None:
        detail["refusal"] = refusal.as_dict()
    return _entry(CHECK_FAIL, detail=detail, error_code=P3_BYTES_MISMATCH)


def _identity_check(
    manifest: dict[str, Any] | None, expect: dict[str, Any]
) -> dict[str, Any]:
    if manifest is None:
        return _not_evaluated("source_read_refused")
    observed = {field: string_or_none(manifest.get(field)) for field in IDENTITY_FIELDS}
    expected = {field: expect[field] for field in IDENTITY_FIELDS if field in expect}
    market = observed["market"]
    security_id = observed["security_id"]
    canonical = (
        canonical_security_code(security_id, market) if security_id is not None else None
    )
    detail: dict[str, Any] = {"canonical_security_id": canonical}

    def _fail() -> dict[str, Any]:
        return _entry(
            CHECK_FAIL,
            detail=detail,
            error_code=P3_IDENTITY_CONFLICT,
            observed=observed,
            expected=expected,
        )

    for field, claimed in expected.items():
        if field == "security_id" and claimed is not None and security_id is not None:
            equivalent = security_codes_equivalent(
                str(claimed),
                str(security_id),
                left_market=expected.get("market", market),
                right_market=market,
            )
            if not equivalent:
                return _fail()
            continue
        if claimed != observed[field]:
            return _fail()
    # The manifest must be self-consistent: a numeric code whose width does not
    # match its own declared market is an identity conflict, and a market's
    # canonical width is never borrowed from another market.
    if canonical is not None and security_id is not None and canonical != security_id:
        detail["width_rule"] = "canonical_code_differs_from_observed"
        return _fail()
    if market is None and security_id is None:
        return _entry(
            CHECK_NOT_APPLICABLE,
            detail=detail,
            reason="manifest_has_no_security_identity",
            observed=observed,
        )
    return _entry(CHECK_PASS, detail=detail, observed=observed, expected=expected)


def _is_iso_date(value: Any) -> bool:
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _period_check(
    manifest: dict[str, Any] | None,
    expect: dict[str, Any],
    availability: dict[str, Any] | None,
) -> dict[str, Any]:
    if manifest is None:
        return _not_evaluated("source_read_refused")
    observed: dict[str, Any] = {field: manifest.get(field) for field in PERIOD_FIELDS}
    observed["date_provenance"] = (
        "capture_evidence_present" if availability is not None else "unverified"
    )
    observed["unknown_source"] = "nullable_manifest"
    expected = {field: expect[field] for field in PERIOD_FIELDS if field in expect}
    for field in ("period_end", "published_date"):
        value = observed[field]
        if value is not None and not _is_iso_date(value):
            return _entry(
                CHECK_FAIL,
                detail={"non_iso_field": field, "observed": value},
                error_code=P3_PERIOD_CONFLICT,
                observed=observed,
                expected=expected,
            )
    for field, claimed in expected.items():
        if claimed != observed[field]:
            return _entry(
                CHECK_FAIL,
                detail={"conflict_field": field},
                error_code=P3_PERIOD_CONFLICT,
                observed=observed,
                expected=expected,
            )
    if all(observed[field] is None for field in PERIOD_FIELDS) and not expected:
        return _entry(
            CHECK_NOT_APPLICABLE,
            detail={},
            reason="manifest_has_no_period_fields",
            observed=observed,
        )
    return _entry(CHECK_PASS, detail={}, observed=observed, expected=expected)


def _availability_check(availability: dict[str, Any] | None) -> dict[str, Any]:
    if availability is None:
        return _entry(
            CHECK_AVAILABILITY_UNKNOWN,
            detail={"evidence": None, "reason": "no_verified_capture_evidence"},
        )
    return _entry(CHECK_PASS, detail={"evidence": availability})


def _span_groundable(span: dict[str, Any], mime_type: str, data: bytes | None) -> bool:
    coordinates = span["coordinates"]
    if mime_type != "text/plain" or not data:
        return False
    if span["structured_value"] is not None:
        return False
    return all(coordinates.get(name) is None for name in _COORDINATE_OFFSETS)


def _audit_one_span(
    span: dict[str, Any],
    *,
    mime_type: str,
    data: bytes | None,
    text: str | None,
) -> dict[str, Any]:
    if not _span_groundable(span, mime_type, data):
        return _entry(CHECK_NOT_APPLICABLE, detail={}, reason="not_groundable_shape")
    raw_text = span["raw_text"]
    if not isinstance(raw_text, str) or not raw_text:
        return _entry(CHECK_NOT_APPLICABLE, detail={}, reason="not_groundable_shape")
    if text is None:
        return _not_evaluated("text_not_decodable_utf8")
    char_start = span["coordinates"]["char_start"]
    char_end = span["coordinates"]["char_end"]
    detail = {"char_start": char_start, "char_end": char_end}
    if raw_text != text[char_start:char_end]:
        return _entry(CHECK_FAIL, detail=detail, error_code=P3_SPAN_UNGROUNDED)
    return _entry(CHECK_PASS, detail=detail)


def _unit_tokens(raw_text: str) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    seen: set[tuple[int, int, str]] = set()
    for pattern in _UNIT_PATTERNS:
        for match in pattern.finditer(raw_text):
            key = (match.start(), match.end(), match.group(0))
            if key in seen:
                continue
            seen.add(key)
            tokens.append(
                {
                    "text": match.group(0),
                    "char_start": match.start(),
                    "char_end": match.end(),
                }
            )
    tokens.sort(key=lambda token: (token["char_start"], token["char_end"]))
    return tokens


def _unit_check(
    owned: list[dict[str, Any]],
    *,
    mime_type: str,
    data: bytes | None,
    text: str | None,
) -> dict[str, Any]:
    groundable = [
        span
        for span in owned
        if _span_groundable(span, mime_type, data)
        and isinstance(span["raw_text"], str)
        and span["raw_text"]
    ]
    if not groundable:
        return _entry(
            CHECK_NOT_APPLICABLE,
            detail={},
            reason="no_groundable_span",
            tokens=[],
        )
    if text is None:
        return _not_evaluated("text_not_decodable_utf8")
    tokens: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    for span in groundable:
        offset = span["coordinates"]["char_start"]
        for token in _unit_tokens(span["raw_text"]):
            absolute_start = offset + token["char_start"]
            absolute_end = offset + token["char_end"]
            tokens.append(
                {
                    "text": token["text"],
                    "char_start": absolute_start,
                    "char_end": absolute_end,
                }
            )
            if text[absolute_start:absolute_end] != token["text"]:
                mismatches.append(
                    {
                        "char_start": absolute_start,
                        "char_end": absolute_end,
                        "claimed": token["text"],
                        "observed": text[absolute_start:absolute_end],
                    }
                )
    if mismatches:
        return _entry(
            CHECK_FAIL,
            detail={"mismatches": mismatches},
            error_code=P3_UNIT_MISMATCH,
            tokens=tokens,
        )
    if not tokens:
        return _entry(
            CHECK_NOT_APPLICABLE,
            detail={},
            reason="no_unit_token_in_span",
            tokens=[],
        )
    return _entry(CHECK_PASS, detail={}, tokens=tokens)


# ---------------------------------------------------------------------------
# per-source aggregation
# ---------------------------------------------------------------------------


def _audit_source(
    catalog: SourceCatalog,
    ref_payload: dict[str, Any],
    spans: list[dict[str, Any]],
    orphan_spans: list[dict[str, Any]],
    expect: dict[str, Any],
) -> tuple[dict[str, Any] | None, bool]:
    """Audit one source; returns (source fragment, catalog_unavailable)."""
    requested = SourceRef(
        document_id=ref_payload["document_id"],
        source_id=ref_payload["source_id"],
        content_sha256=ref_payload["content_sha256"],
        byte_size=ref_payload["byte_size"],
        mime_type=ref_payload["mime_type"],
    )
    read = read_source(catalog, requested)
    if read.refusal is not None and read.refusal.reason == "catalog_unavailable":
        # The catalog itself is unreadable: refuse at the top level instead of
        # dressing a dependency failure up as a per-source ref mismatch.
        return None, True

    checks: dict[str, Any] = {}
    ref_entry = _ref_check(read, requested)
    checks["ref"] = ref_entry
    downstream_reason = (
        "ref_check_failed" if ref_entry["status"] == CHECK_FAIL else None
    )

    if downstream_reason is not None:
        checks["bytes"] = _not_evaluated(downstream_reason)
    else:
        checks["bytes"] = _bytes_check(read, requested)
    bytes_failed = checks["bytes"]["status"] == CHECK_FAIL

    facts_reason = downstream_reason or (
        "source_read_refused" if read.manifest is None or bytes_failed else None
    )
    if facts_reason is not None:
        checks["identity"] = _not_evaluated(facts_reason)
        checks["period"] = _not_evaluated(facts_reason)
    else:
        checks["identity"] = _identity_check(read.manifest, expect)
        checks["period"] = _period_check(read.manifest, expect, read.availability)

    if downstream_reason is not None:
        checks["availability"] = _not_evaluated(downstream_reason)
    else:
        checks["availability"] = _availability_check(read.availability)

    text: str | None = None
    if read.data is not None:
        try:
            text = read.data.decode("utf-8")
        except UnicodeDecodeError:
            text = None

    owned: list[dict[str, Any]] = []
    span_entries: list[dict[str, Any]] = []
    for span in spans:
        if span["source_id"] != requested.source_id:
            continue
        owned.append(span)
        if downstream_reason is not None:
            span_entries.append(_not_evaluated(downstream_reason))
        elif read.data is None:
            span_entries.append(_not_evaluated("source_read_refused"))
        else:
            span_entries.append(
                _audit_one_span(
                    span, mime_type=requested.mime_type, data=read.data, text=text
                )
            )
    # Spans naming a source outside this request stay visible as unevaluated.
    for span in orphan_spans:
        span_entries.append(_not_evaluated("unknown_source_id"))
    checks["spans"] = span_entries
    if downstream_reason is not None:
        checks["unit"] = _not_evaluated(downstream_reason)
    else:
        checks["unit"] = _unit_check(
            owned,
            mime_type=requested.mime_type,
            data=read.data,
            text=text,
        )

    first_failure = None
    for name in _CHECK_ORDER:
        entry = checks[name]
        entries = entry if isinstance(entry, list) else [entry]
        for item in entries:
            if item["status"] == CHECK_FAIL:
                first_failure = item.get("error_code")
                break
        if first_failure is not None:
            break
    if first_failure is not None:
        checks["error_code"] = first_failure

    source = {
        "document_id": requested.document_id,
        "source_id": requested.source_id,
        "status": CHECK_FAIL if first_failure is not None else CHECK_PASS,
        "checks": checks,
    }
    return source, False


# ---------------------------------------------------------------------------
# entrypoint
# ---------------------------------------------------------------------------


def audit(*, config_path: Any, request: Any) -> dict[str, Any]:
    """Run the seven checks and return the ``identity-audit-receipt/1`` dict.

    Validation failures never raise: they come back as ``blocked`` receipts
    with a published ``reason``.
    """
    generated_at = utc_now()
    binding = _input_binding(config_path)
    inputs = {str(config_path): binding} if binding else {}
    blocking = _validate_request(request)
    if blocking is not None:
        return _shell(TOP_BLOCKED, generated_at, inputs, blocking)

    try:
        config = load_catalog_config(config_path)
        catalog = SourceCatalog(config)
    except (OSError, TypeError, ValueError):
        return _shell(TOP_UNAVAILABLE, generated_at, inputs, DEPENDENCY_UNAVAILABLE)

    requested_ids = {ref["source_id"] for ref in request["source_refs"]}
    orphan_spans = [
        span for span in request["evidence_spans"] if span["source_id"] not in requested_ids
    ]
    sources: list[dict[str, Any]] = []
    try:
        for ref_payload in request["source_refs"]:
            source, unavailable = _audit_source(
                catalog,
                ref_payload,
                request["evidence_spans"],
                orphan_spans,
                request.get("expect") or {},
            )
            if unavailable or source is None:
                return _shell(
                    TOP_UNAVAILABLE, generated_at, inputs, DEPENDENCY_UNAVAILABLE
                )
            sources.append(source)
    finally:
        catalog.close()

    counts = _zero_counts()
    any_failed = False
    any_not_evaluated = False
    for source in sources:
        checks = source["checks"]
        for name in _CHECK_ORDER:
            entry = checks[name]
            entries = entry if isinstance(entry, list) else [entry]
            counts["checked"] += len(entries)
            for item in entries:
                if item["status"] == CHECK_PASS:
                    counts["passed"] += 1
                elif item["status"] == CHECK_FAIL:
                    counts["failed"] += 1
                    any_failed = True
                elif item["status"] == CHECK_NOT_APPLICABLE:
                    counts["not_applicable"] += 1
                elif item["status"] == CHECK_NOT_EVALUATED:
                    counts["not_evaluated"] += 1
                    any_not_evaluated = True
    if any_failed:
        status = TOP_FAIL
    elif any_not_evaluated:
        status = TOP_PARTIAL
    else:
        status = TOP_OK
    receipt = _shell(status, generated_at, inputs)
    receipt["sources"] = sources
    receipt["counts"] = counts
    if len(canonical_json(receipt).encode("utf-8")) > MAX_RECEIPT_BYTES:
        return _shell(TOP_BLOCKED, generated_at, inputs, RECEIPT_TOO_LARGE)
    return receipt
