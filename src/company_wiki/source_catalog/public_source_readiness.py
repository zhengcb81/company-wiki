"""Pathless public readiness diagnostics for an exact SourceRef.

Dashboard-facing capability on top of the SAME exact reader protocol used by
``source_reader.py`` (no second lookup): the caller supplies a complete
6-field SourceRef plus an explicit mode, and receives a versioned, pathless
response that says what the catalog metadata knows and — only for
``verify_existing_bytes`` — what a bounded local byte verification proved.

Hard boundaries enforced here:

* The request JSON must be a complete 6-field SourceRef.  Physical paths,
  roots, SQL, or commands are never accepted and never echoed.
* ``metadata_only`` is catalog metadata only (source_status + capture
  fields).  It can NEVER claim byte verification, even when the file exists.
* ``verify_existing_bytes`` streams the local bytes through the exact
  reader's same-SHA verification with a caller-visible deadline and byte
  ceiling.  ``byte_verified`` is true only after the reader verified size,
  identity and SHA-256 of the actually read bytes.
* Every refusal is a named state (``partial`` / ``blocked`` /
  ``unavailable``) with stable reason codes.  No internal root, relative
  path, exception text or policy detail is ever emitted.
* This module is read-only: it never fetches, OCRs, parses, summarizes or
  scans, and never writes the catalog or the source roots.
"""

from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import asdict
from typing import Mapping
from urllib.parse import urlsplit

from .reader import CatalogReaderUnavailable
from .read_budget import ReadBudget as _ReadBudget
from .source_reader import (
    SOURCE_REF_SCHEMA_VERSION,
    SourceReadError,
    SourceRef,
    SourceVersionReader,
    VerifiedVersionReceipt,
)


READINESS_SCHEMA_VERSION = "source-readiness/1"
ASSESS_MODES = ("metadata_only", "verify_existing_bytes")

DEFAULT_VERIFY_DEADLINE_SECONDS = 30.0
DEFAULT_MAX_VERIFY_BYTES = 256 * 1024 * 1024
_MAX_VERIFY_BYTES_CEILING = 2 * 1024 * 1024 * 1024
_MAX_TEXT_LENGTH = 4096

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MIME_TYPE = re.compile(
    r"[a-zA-Z0-9][a-zA-Z0-9!#$&^_.+-]{0,126}/"
    r"[a-zA-Z0-9][a-zA-Z0-9!#$&^_.+-]{0,126}\Z"
)
_REASON_CODE = re.compile(r"[a-z0-9_]{1,64}\Z")
_REF_ID = re.compile(r"[^\\\x00-\x1f\x7f]{1,512}\Z")
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
# Free-text metadata fields that may be projected to a dashboard consumer,
# each individually length-bounded and path-screened.  Anything not listed
# here — root ids, relative paths, storage internals — never leaves the module.
_READINESS_METADATA_FIELDS = (
    "title",
    "document_kind",
    "published_date",
    "source_url",
    "https_url",
    "retrieved_at",
    "collector_name",
    "collector_version",
    "canonical_entity_id",
    "display_name",
    "market",
    "security_id",
    "fiscal_year",
    "fiscal_period",
    "period_end",
    "form_type",
    "provider",
    "provider_document_id",
    "language",
    "capture_ready",
    "capture_provenance",
    "prompt_injection_status",
    "snapshot_sha256",
    "byte_size",
    "mime_type",
)
# Candidate ``scheme://…`` spans a network-URI mask COULD cover.  Whether a
# candidate is actually masked is decided structurally (see
# ``_mask_network_urls``), not by this regex alone: a multi-char scheme alone
# does NOT qualify.  A single-letter scheme is never a candidate (it is a
# Windows drive wearing a scheme shape, ``C://Users/…``), and ``file://`` is
# excluded (it IS a physical location).  The raw backslash-locator check below
# runs FIRST, so a bare drive/UNC locator embedded in a URL query
# (``https://h/?u=C:\\secret\\file``) is still caught before any masking.
_SCHEME_URL_CANDIDATE = re.compile(r"(?i)\b(?!file:)[a-z][a-z0-9+.-]+://\S*")

# Unambiguous file locators built from BACKSLASH or the ``file`` scheme.  A
# backslash is NEVER valid URL syntax, so these are checked on the RAW string
# and therefore survive even when embedded inside a URL query — a scheme prefix
# can never launder a bare Windows/UNC/file locator.  Rules:
#   * ``file:/`` … file URIs (always physical);
#   * a standalone drive letter + BACKSLASH (``C:\\``); the ``(?<![A-Za-z])``
#     lookbehind keeps the trailing ``s:\\`` of nothing-in-URL from matching
#     (URLs contain no backslash) and stops ``…s:\\`` glue;
#   * a UNC share (``\\\\server\\share``, two leading backslashes);
#   * a relative-escape segment ``..\\``.
_BACKSLASH_LOCATOR = re.compile(
    r"(?i)"
    r"file:/"
    r"|(?<![A-Za-z])[A-Za-z]:\\"
    r"|\\\\[^\s\"']+"
    r"|\.\.\\"
)

# Forward-slash path tokens + drive-letter paths, checked on the URL-MASKED
# string so a qualified https/ftp path/query/fragment colon, a port or an
# in-URL ``///`` is preserved while a single-letter drive (``C://Users``), a
# drive-relative token (``C:1secret``), a POSIX absolute path or a forward UNC
# is still caught.  Rules:
#   * a STANDALONE drive letter + slash (``C:/`` or ``C:\\``); the
#     ``(?<![A-Za-z])`` lookbehind keeps the trailing ``s:/`` of ``https://``
#     from being read as a drive letter;
#   * a drive-RELATIVE token (``C:1secret``) — a lone drive letter + colon +
#     a non-space/non-slash char, i.e. Windows drive-relative syntax;
#   * a forward UNC (``//server/share``; ``//`` NOT preceded by ``:``);
#   * a POSIX path TOKEN at a DELIMITER boundary: a ``/`` NOT glued to a
#     preceding path-continuation char (letter / digit / ``.`` / ``_`` / ``-``)
#     and followed by one or more non-empty segments.  This is token+context
#     recognition, not a whitelist: start-of-string, whitespace, quotes,
#     brackets ``[…]``, braces, assignment ``=``, colon-label ``:``, comma,
#     semicolon and other punctuation all count as the delimiter.  A ``/``
#     glued inside a URL path (``…/Archives/…``), a mime type
#     (``application/pdf``) or an ``A/B/C`` / ``12/25`` prose fragment is
#     exempt because its preceding char is a path-continuation char;
#   * a relative-escape segment ``../``.
_MASKED_PATH_SIGNAL = re.compile(
    r"(?i)"
    r"(?<![A-Za-z])[A-Za-z]:[\\/]"
    r"|(?<![A-Za-z])[A-Za-z]:[^\s\\/]"
    r"|(?<![:A-Za-z0-9])//[^/\s]"
    r"|(?<![A-Za-z0-9._-])(/[^/\s]+)+"
    r"|\.\./"
)


def _mask_network_urls(value: str) -> str:
    """Mask only QUALIFIED network URIs; leave un-qualified ones for the rules.

    A candidate ``scheme://…`` is masked (its legitimate path/query/fragment
    colons, ports and slashes become invisible to the token rules) ONLY when
    structured parsing proves it carries a real network authority: a multi-char
    scheme AND a non-empty ``netloc`` with a host and a valid optional port.  A
    ``scheme://`` with an EMPTY authority — ``https:///etc/…`` (netloc ``''``,
    hostname ``None``), ``https://?path=/opt/…``, ``https://#path=/opt/…`` —
    is not a network URL, it is a physical locator wearing a scheme prefix, so
    it is left in place for the POSIX/backslash rules to catch.  Parsing is
    structural only (``urllib.parse.urlsplit``): no DNS, no network, no
    URL-decoding; a parse that yields no host is treated as un-qualified, and
    a parse that raises is also left un-masked (never silently trusted).
    """

    def _qualify(match: "re.Match[str]") -> str:
        candidate = match.group(0)
        try:
            parts = urlsplit(candidate)
            host = parts.hostname  # may raise on a malformed netloc
            # urlsplit accepts a hostname even when its port is illegal.
            # Validate the optional port before granting the URI exemption;
            # otherwise zz://C:secret.txt launders a drive-relative locator.
            _ = parts.port
        except ValueError:
            return candidate  # unparsable → not qualified → do not mask
        if parts.scheme and len(parts.scheme) >= 2 and parts.netloc and host:
            return " "  # qualified network URI → mask its legitimate syntax
        return candidate  # no/illegal authority → keep for the locator rules

    return _SCHEME_URL_CANDIDATE.sub(_qualify, value)


def _contains_physical_path(value: str) -> bool:
    """True when the text carries a filesystem/location signal.

    The single source of truth for both ref-ID admission and metadata
    projection (D00-CWP-READINESS-002/-003/-004).  Backslash/file locators are
    checked on the raw string first (they are never URL syntax, so a scheme
    prefix cannot launder them); QUALIFIED network URIs (multi-char scheme +
    a real authority/host) are then masked so their legitimate ``/``-paths,
    ``:`` colons, ports and fragments never trip the token rules, while
    empty-authority ``scheme:///path`` locators, single-letter drives
    (``C://``), drive-relative tokens, POSIX paths and forward UNC are still
    caught.
    """
    if _BACKSLASH_LOCATOR.search(value):
        return True
    return _MASKED_PATH_SIGNAL.search(_mask_network_urls(value)) is not None


_STATUS_MAP = {
    "not_found": "partial",
    "not_indexed": "partial",
    "ambiguous": "partial",
    "blocked": "blocked",
    "unavailable": "unavailable",
}


class PublicSourceRefError(ValueError):
    """The request JSON is not a complete, well-formed 6-field SourceRef."""

    def __init__(self, reason_code: str):
        self.reason_code = reason_code
        super().__init__(reason_code)


class _VerifyDeadlineExceeded(RuntimeError):
    """Internal: the caller-supplied verify deadline elapsed."""


def parse_public_source_ref(payload: object) -> SourceRef:
    """Strictly accept ONLY a complete 6-field SourceRef JSON object.

    Duplicate JSON keys are rejected by the caller's loader; here every field
    is type- and shape-checked so no path, non-finite number or oversized
    value can enter the read chain.  The optional-but-required schema_version
    must be the exact reader schema the ref claims.
    """
    if not isinstance(payload, Mapping):
        raise PublicSourceRefError("invalid_source_ref")
    if set(payload.keys()) != _REF_FIELDS:
        raise PublicSourceRefError("invalid_source_ref")
    if payload["schema_version"] != SOURCE_REF_SCHEMA_VERSION:
        raise PublicSourceRefError("invalid_source_ref")
    document_id = payload["document_id"]
    source_id = payload["source_id"]
    if not isinstance(document_id, str) or not isinstance(source_id, str):
        raise PublicSourceRefError("invalid_source_ref")
    if not document_id or not source_id:
        raise PublicSourceRefError("invalid_source_ref")
    if not _REF_ID.fullmatch(document_id) or not _REF_ID.fullmatch(source_id):
        raise PublicSourceRefError("invalid_source_ref")
    for candidate in (document_id, source_id):
        # Opaque IDs only: refuse any physical-location signal before the
        # catalog is touched (D00-CWP-READINESS-002).  A drive/UNC/file-URI/
        # POSIX/relative-escape document_id is a request error, never echoed.
        if _contains_physical_path(candidate):
            raise PublicSourceRefError("invalid_source_ref")
    content_sha256 = payload["content_sha256"]
    if not isinstance(content_sha256, str) or not _SHA256.fullmatch(content_sha256):
        raise PublicSourceRefError("invalid_source_ref")
    byte_size = payload["byte_size"]
    if isinstance(byte_size, bool) or not isinstance(byte_size, int):
        raise PublicSourceRefError("invalid_source_ref")
    if not 0 <= byte_size <= 2**40:
        raise PublicSourceRefError("invalid_source_ref")
    mime_type = payload["mime_type"]
    if not isinstance(mime_type, str) or not _MIME_TYPE.fullmatch(mime_type):
        raise PublicSourceRefError("invalid_source_ref")
    return SourceRef(
        document_id=document_id,
        source_id=source_id,
        content_sha256=content_sha256,
        byte_size=byte_size,
        mime_type=mime_type,
    )


def _empty_response(source_ref: Mapping[str, object] | None) -> dict[str, object]:
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "status": "unavailable",
        "checked_mode": None,
        "source_ref": dict(source_ref) if source_ref is not None else None,
        "byte_verified": False,
        "reason_codes": [],
        "verification_receipt": None,
        "metadata": None,
    }


def _reason_code(value: str | None) -> str:
    if value is not None and _REASON_CODE.fullmatch(value):
        return value
    return "read_refused"


def _readiness_response(
    *,
    source_ref: SourceRef,
    checked_mode: str,
    status: str,
    reason_codes: tuple[str, ...] = (),
    metadata: dict[str, object] | None = None,
    byte_verified: bool = False,
    verification_receipt: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "status": status,
        "checked_mode": checked_mode,
        "source_ref": asdict(source_ref),
        "byte_verified": byte_verified,
        "reason_codes": list(reason_codes),
        "verification_receipt": verification_receipt,
        "metadata": metadata,
    }


def _screened_text(value: str) -> str | None:
    """Drop any text that smells like a physical location or escape."""
    if _contains_physical_path(value):
        return None
    return value[:_MAX_TEXT_LENGTH]


def _screened_value(value: object) -> object | None:
    """Recursively project a metadata value, path-screening every string.

    ``str`` → length-capped + physical-path-screened (``None`` drops the
    value when a location signal is present); ``int``/``bool``/``None``
    pass through; ``list``/``dict`` recurse (so a nested capture blob cannot
    smuggle a path past the top-level allowlist); every other type (float,
    non-finite, object) is dropped — the projection never invents structure.
    """
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, str):
        return _screened_text(value)
    if isinstance(value, (list, tuple)):
        projected_items = [_screened_value(item) for item in value]
        return [item for item in projected_items if item is not None]
    if isinstance(value, dict):
        projected_map: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            screened_key = _screened_text(key)
            screened_item = _screened_value(item)
            if screened_key is None or screened_item is None:
                continue
            projected_map[screened_key] = screened_item
        return projected_map
    return None


def _project_metadata(raw: object) -> dict[str, object]:
    """Project an allowlisted, path-screened metadata view or nothing.

    This projection carries catalog facts only.  By construction it cannot
    assert file existence, readability or SHA correctness — those facts exist
    only in a ``verify_existing_bytes`` result.
    """
    if not isinstance(raw, dict):
        return {}
    projected: dict[str, object] = {}
    for field in _READINESS_METADATA_FIELDS:
        if field not in raw:
            continue
        value = _screened_value(raw[field])
        if value is not None:
            projected[field] = value
    return projected


def _verification_receipt(receipt: VerifiedVersionReceipt) -> dict[str, object]:
    """Flatten the exact reader's receipt to its pathless identity fields."""
    data = asdict(receipt)
    projected: dict[str, object] = {}
    for field in (
        "document_id",
        "source_id",
        "content_sha256",
        "byte_size",
        "read_at",
        "policy_sha256",
        "source_read_policy_sha256",
    ):
        value = data.get(field)
        if isinstance(value, str):
            projected[field] = _screened_text(value)
        elif isinstance(value, int) and not isinstance(value, bool):
            projected[field] = int(value)
    return projected


class _ReadinessVerifyBudget(_ReadBudget):
    """Exact-reader read budget plus a monotonic deadline check.

    The deadline rides the reader's own per-chunk ``check`` hook, so a hung
    or huge local read still terminates inside the exact read rules instead
    of bypassing them.
    """

    def __init__(self, *, max_bytes: int, deadline_monotonic: float | None):
        super().__init__(max_bytes=max_bytes)
        self._deadline_monotonic = deadline_monotonic

    def check(self) -> None:
        if self._deadline_monotonic is not None and (
            time.monotonic() > self._deadline_monotonic
        ):
            raise _VerifyDeadlineExceeded()


class PublicSourceReadiness:
    """One diagnostic surface over the shared exact reader protocol."""

    def __init__(self, reader: SourceVersionReader):
        if not isinstance(reader, SourceVersionReader):
            raise TypeError("reader must be SourceVersionReader")
        self._reader = reader

    def assess(
        self,
        source_ref: object,
        *,
        mode: str,
        byte_deadline_seconds: float | None = None,
        max_verify_bytes: int | None = None,
    ) -> dict[str, object]:
        """Return the versioned pathless readiness response for one ref.

        ``mode`` must be an explicit ``metadata_only`` or
        ``verify_existing_bytes``.  Limits apply to verify mode; ``None``
        selects the module defaults.  Every failure path returns a named
        refusal — this method never raises for catalog or request state.
        """
        if mode not in ASSESS_MODES:
            return _empty_response(None)
        try:
            ref = parse_public_source_ref(source_ref)
        except PublicSourceRefError as exc:
            response = _empty_response(None)
            response["reason_codes"] = [exc.reason_code]
            return response
        if byte_deadline_seconds is None:
            deadline = time.monotonic() + DEFAULT_VERIFY_DEADLINE_SECONDS
        elif (
            isinstance(byte_deadline_seconds, bool)
            or not isinstance(byte_deadline_seconds, (int, float))
            or byte_deadline_seconds < 0
            or byte_deadline_seconds != byte_deadline_seconds
            or byte_deadline_seconds in (float("inf"), float("-inf"))
        ):
            response = _readiness_response(
                source_ref=ref, checked_mode=mode, status="blocked",
                reason_codes=("invalid_verify_limits",),
            )
            return response
        else:
            deadline = time.monotonic() + float(byte_deadline_seconds)
        if max_verify_bytes is None:
            verify_cap = DEFAULT_MAX_VERIFY_BYTES
        elif (
            isinstance(max_verify_bytes, bool)
            or not isinstance(max_verify_bytes, int)
            or not 0 < max_verify_bytes <= _MAX_VERIFY_BYTES_CEILING
        ):
            return _readiness_response(
                source_ref=ref, checked_mode=mode, status="blocked",
                reason_codes=("invalid_verify_limits",),
            )
        else:
            verify_cap = int(max_verify_bytes)
        try:
            if mode == "metadata_only":
                return self._assess_metadata(ref)
            return self._assess_verify(
                ref, deadline_monotonic=deadline, max_verify_bytes=verify_cap
            )
        except _VerifyDeadlineExceeded:
            return _readiness_response(
                source_ref=ref, checked_mode=mode, status="unavailable",
                reason_codes=("verify_deadline_exceeded",),
            )
        except SourceReadError as exc:
            return _readiness_response(
                source_ref=ref, checked_mode=mode,
                status=_STATUS_MAP[exc.status],
                reason_codes=(_reason_code(exc.reason),),
            )
        except (CatalogReaderUnavailable, sqlite3.Error):
            return _readiness_response(
                source_ref=ref, checked_mode=mode, status="unavailable",
                reason_codes=("catalog_unavailable",),
            )

    def _assess_metadata(self, ref: SourceRef) -> dict[str, object]:
        """Catalog metadata only: honest about NOT having looked at bytes."""
        try:
            candidate = self._reader.describe_candidate(ref)
        except SourceReadError as exc:
            return _readiness_response(
                source_ref=ref,
                checked_mode="metadata_only",
                status=_STATUS_MAP[exc.status],
                reason_codes=(_reason_code(exc.reason),),
            )
        return _readiness_response(
            source_ref=ref,
            checked_mode="metadata_only",
            status="ready",
            metadata=_project_metadata(candidate),
        )

    def _assess_verify(
        self,
        ref: SourceRef,
        *,
        deadline_monotonic: float,
        max_verify_bytes: int,
    ) -> dict[str, object]:
        """Bounded local byte verification through the exact reader.

        The ref's own declared size is checked against the caller's ceiling
        BEFORE any byte is touched; the reader then re-checks the real file
        size, identity and SHA under the same budget.
        """
        if ref.byte_size > max_verify_bytes:
            return _readiness_response(
                source_ref=ref, checked_mode="verify_existing_bytes",
                status="blocked", reason_codes=("verify_limit_exceeded",),
            )
        budget = _ReadinessVerifyBudget(
            max_bytes=max_verify_bytes, deadline_monotonic=deadline_monotonic,
        )
        try:
            receipt = self._reader.verify_version(ref, purpose="source_export", budget=budget)
        except SourceReadError as exc:
            return _readiness_response(
                source_ref=ref,
                checked_mode="verify_existing_bytes",
                status=_STATUS_MAP[exc.status],
                reason_codes=(_reason_code(exc.reason),),
            )
        return _readiness_response(
            source_ref=ref,
            checked_mode="verify_existing_bytes",
            status="ready",
            byte_verified=True,
            verification_receipt=_verification_receipt(receipt),
        )


__all__ = [
    "ASSESS_MODES",
    "DEFAULT_MAX_VERIFY_BYTES",
    "DEFAULT_VERIFY_DEADLINE_SECONDS",
    "READINESS_SCHEMA_VERSION",
    "PublicSourceReadiness",
    "PublicSourceRefError",
    "parse_public_source_ref",
]
