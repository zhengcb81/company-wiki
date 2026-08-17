"""ZR-302: prompt-injection scanner/reviewer receipt lifecycle (guard).

Builds on the FC-905 receipt store (``prompt_injection.py``) with the
missing lifecycle:

- ``scan_text`` — a deterministic injection scanner over a versioned,
  hash-bound ruleset (unknown ruleset hash fails closed).
- ``evaluate_review`` — cache evaluation of a stored receipt against the
  current source bytes and policy ruleset:
    * hit      — receipt valid, source_sha256 + policy_hash match, fresh;
    * ignored  — policy_hash changed (ruleset moved on): not_reviewed,
      never green from a stale ruleset;
    * expired  — reviewed_at older than the TTL: not_reviewed;
    * tampered — source_sha256 mismatch (bytes changed) or malformed
      receipt: not_reviewed (fail closed);
    * absent   — no receipt: not_reviewed.
  ``not_reviewed`` is never faked green: every non-hit path returns
  not_reviewed with an explicit cache_state.

This module is shadow-only on the evaluation side (reads via the
CatalogStore-compatible ``store.fetchone``); receipt generation still goes
through the existing write path in ``prompt_injection``.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .prompt_injection import (
    PROMPT_INJECTION_REVIEW_KEY,
    PROMPT_INJECTION_REVIEW_SCHEMA_VERSION,
    PROMPT_INJECTION_REVIEW_STATUSES,
)

PROMPT_INJECTION_GUARD_SCHEMA_VERSION = "1.0"
PROMPT_INJECTION_GUARD_SCHEMA = "prompt-injection-guard-1.0"

# Versioned scanner ruleset: (pattern_id, regex).  The ruleset hash is the
# SHA-256 of the canonical JSON serialization — a changed ruleset changes
# the hash and forces re-review (ignored), never a stale green.
_RULESET_PATTERNS: tuple[tuple[str, str], ...] = (
    ("ignore_previous_instructions", r"ignore\s+(all\s+)?(previous|prior)\s+instructions"),
    ("system_prompt_override", r"you\s+are\s+now\s+(an?\s+)?(the\s+)?(system|admin|root)"),
    ("prompt_leak_request", r"(reveal|print|show|output)\s+(your\s+)?(system\s+)?prompt"),
    ("instruction_injection", r"disregard\s+(all\s+)?(previous|prior)\s+instructions"),
    ("exfiltration", r"send\s+(the\s+)?(contents?|data|file)\s+to\s+https?://"),
)
_RULESET_BLOCKLIST: dict[str, str] = dict(_RULESET_PATTERNS)

RULESET_HASH = hashlib.sha256(
    json.dumps(
        [list(item) for item in _RULESET_PATTERNS], ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
).hexdigest()

CACHE_STATES = frozenset({"hit", "ignored", "expired", "tampered", "absent"})


class PromptInjectionGuardError(ValueError):
    """Raised when a scan/evaluation input is invalid (fail closed)."""


@dataclass(frozen=True)
class ScanResult:
    """Deterministic scanner verdict over one text."""

    status: str  # not_detected | detected_and_ignored
    matches: tuple[str, ...] = ()
    ruleset_hash: str = RULESET_HASH


@dataclass(frozen=True)
class ReviewEvaluation:
    """Cache evaluation of a stored review receipt."""

    status: str  # not_detected | detected_and_ignored | not_reviewed
    cache_state: str  # hit | ignored | expired | tampered | absent
    reason: str = ""


def scan_text(text: str, ruleset_hash: str = RULESET_HASH) -> ScanResult:
    """Scan *text* against the ruleset; unknown ruleset fails closed.

    A match is reported as ``detected_and_ignored`` (the review receipt
    records that injection was found and deliberately ignored, mirroring
    the FC-905 status vocabulary); no match is ``not_detected``.
    """
    if not isinstance(text, str):
        raise PromptInjectionGuardError("text must be a string")
    if not isinstance(ruleset_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", ruleset_hash):
        raise PromptInjectionGuardError("ruleset_hash must be a lowercase SHA-256")
    if ruleset_hash != RULESET_HASH:
        raise PromptInjectionGuardError(
            f"unknown ruleset hash {ruleset_hash!r} (fail closed)")
    lowered = text.lower()
    matches: list[str] = []
    for pattern_id, pattern in _RULESET_PATTERNS:
        if re.search(pattern, lowered):
            matches.append(pattern_id)
    if matches:
        return ScanResult(status="detected_and_ignored", matches=tuple(matches))
    return ScanResult(status="not_detected")


def _receipt_from_store(store: Any, document_id: str) -> dict[str, Any] | None:
    """The stored receipt dict, or None when absent/malformed (fail closed)."""
    row = store.fetchone(
        "SELECT metadata_json FROM documents WHERE document_id=?",
        (document_id,),
    )
    if row is None:
        return None
    try:
        metadata = json.loads(str(row[0] or "{}"))
        if not isinstance(metadata, dict):
            return None
        receipt = metadata.get(PROMPT_INJECTION_REVIEW_KEY)
        if not isinstance(receipt, dict):
            return None
        if receipt.get("schema_version") != PROMPT_INJECTION_REVIEW_SCHEMA_VERSION:
            return None
        if receipt.get("status") not in PROMPT_INJECTION_REVIEW_STATUSES:
            return None
        return receipt
    except json.JSONDecodeError:
        return None


def _iso_seconds(value: str) -> float | None:
    """Parse an ISO-8601 UTC timestamp (Z suffix) into epoch seconds."""
    try:
        from datetime import datetime

        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp()
    except ValueError:
        return None


def _binding_mismatch(receipt: dict[str, Any], source_sha256: str, policy_hash: str) -> ReviewEvaluation | None:
    """tampered (source bytes changed) or ignored (ruleset changed)."""
    if receipt.get("source_sha256") != source_sha256:
        return ReviewEvaluation(
            status="not_reviewed", cache_state="tampered",
            reason="source bytes changed since review",
        )
    if receipt.get("policy_hash") != policy_hash:
        return ReviewEvaluation(
            status="not_reviewed", cache_state="ignored",
            reason="policy ruleset changed since review",
        )
    return None


def _freshness(receipt: dict[str, Any], now: str, ttl_seconds: float) -> ReviewEvaluation | None:
    """expired (older than TTL) or tampered (unparseable timestamps)."""
    reviewed_at = _iso_seconds(str(receipt.get("reviewed_at") or ""))
    now_seconds = _iso_seconds(now)
    if reviewed_at is None or now_seconds is None:
        return ReviewEvaluation(
            status="not_reviewed", cache_state="tampered",
            reason="receipt reviewed_at is not ISO-8601 UTC",
        )
    if now_seconds - reviewed_at > ttl_seconds:
        return ReviewEvaluation(
            status="not_reviewed", cache_state="expired",
            reason=f"review older than {ttl_seconds:g}s TTL",
        )
    return None


def evaluate_review(
    store: Any,
    document_id: str,
    *,
    source_sha256: str,
    policy_hash: str,
    now: str,
    ttl_seconds: float,
) -> ReviewEvaluation:
    """Evaluate the stored receipt against the current source/policy.

    ``store`` must expose ``fetchone(sql, params)`` (CatalogStore- or
    reader-compatible).  Every non-hit path returns ``not_reviewed`` with
    an explicit cache_state — never a faked green.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise PromptInjectionGuardError("source_sha256 must be a lowercase SHA-256")
    if not re.fullmatch(r"[0-9a-f]{64}", policy_hash):
        raise PromptInjectionGuardError("policy_hash must be a lowercase SHA-256")
    if ttl_seconds < 0:
        raise PromptInjectionGuardError("ttl_seconds must be >= 0")
    receipt = _receipt_from_store(store, document_id)
    if receipt is None:
        return ReviewEvaluation(status="not_reviewed", cache_state="absent")
    mismatch = _binding_mismatch(receipt, source_sha256, policy_hash)
    if mismatch is not None:
        return mismatch
    stale = _freshness(receipt, now, ttl_seconds)
    if stale is not None:
        return stale
    return ReviewEvaluation(
        status=str(receipt["status"]), cache_state="hit",
        reason="receipt fresh and bound",
    )


__all__ = [
    "CACHE_STATES",
    "PROMPT_INJECTION_GUARD_SCHEMA",
    "PROMPT_INJECTION_GUARD_SCHEMA_VERSION",
    "RULESET_HASH",
    "PromptInjectionGuardError",
    "ReviewEvaluation",
    "ScanResult",
    "evaluate_review",
    "scan_text",
]
