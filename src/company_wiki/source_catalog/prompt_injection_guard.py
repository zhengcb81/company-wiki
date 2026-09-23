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

Policy surface (TTL-30D-POLICY, owner-ratified OWNER_DECISIONS.md §十九
option A + OPEN-6 ruling C6) — GUARD-MERGE ruling §1-1 (REJECT form):

- ``POLICY_RECEIPT_TTL_CAP_SECONDS`` — the policy CAP on the caller's
  ``ttl_seconds``: callers may only TIGHTEN (``ttl_seconds`` > cap raises
  ``PromptInjectionGuardError`` instead of being clamped), and a caller
  ``now`` earlier than the receipt's ``reviewed_at`` is a clock anomaly
  that fails closed as ``tampered`` — a rewound clock can never resurrect
  an expired receipt (``now`` may only make freshness stricter).
- The cap is part of the policy surface covered by ``policy_hash``:
  changing its value is a POLICY CHANGE, and receipts issued under the
  old policy must be invalidated on read exactly as when ``policy_hash``
  moves (OPEN-4 4c: policy content change ⇒ old receipts die).

FIX-W06-GAPS C7 (oracle.md) — GUARD-MERGE ruling §1-2: same-word
ambiguity between the cache-invalidation state ``cache_state="ignored"``
and the review conclusion ``detected_and_ignored`` is disambiguated with
an EXPLICIT ``state_domain`` tag on every state-carrying record
(``cache`` | ``review``).  The rename route (``ignored`` ->
``policy_changed``) is BLOCKED by frozen vocabulary (I-06-B oracle.md:87
pins ``cache_state="ignored"``).  The domain tag is fail-closed: missing
or illegal => refused / strictest, never defaulted into either semantics.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from .prompt_injection import (
    PROMPT_INJECTION_REVIEW_KEY,
    PROMPT_INJECTION_REVIEW_SCHEMA_VERSION,
    PROMPT_INJECTION_REVIEW_STATUSES,
    STATE_DOMAIN_CACHE,
    STATE_DOMAIN_REVIEW,
    STATE_DOMAINS,
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

# Policy CAP on receipt-freshness TTL — owner §十九 option A: 30 days
# (86400*30 = 2592000s), mechanism per OPEN-6 ruling C6: the TTL ceiling is
# fixed by the policy surface bound to policy_hash; caller-supplied
# now/ttl_seconds may only TIGHTEN, never widen.  A wider TTL is REJECTED
# (fail-closed), not clamped.  This constant is part of the policy_hash-
# covered contract: changing it is a POLICY CHANGE and invalidates receipts
# issued under the old policy (OPEN-4 4c — full re-review), exactly as if
# policy_hash itself had moved.
POLICY_RECEIPT_TTL_CAP_SECONDS = 86400 * 30


class PromptInjectionGuardError(ValueError):
    """Raised when a scan/evaluation input is invalid (fail closed)."""


def require_state_domain(value: Any, expected: str) -> None:
    """C7 fail-closed domain gate.

    A state token is only interpretable inside its own domain: a missing or
    illegal tag is refused, and a record of one domain can never be read as
    the other (``state_domain 'cache' record cannot be read as 'review'``).
    """
    if value not in STATE_DOMAINS:
        raise PromptInjectionGuardError(
            f"state_domain {value!r} is missing or illegal — fail closed "
            f"(ambiguity is never defaulted)")
    if value != expected:
        raise PromptInjectionGuardError(
            f"state_domain {value!r} record cannot be read as {expected!r}")


@dataclass(frozen=True)
class ScanResult:
    """Deterministic scanner verdict over one text."""

    status: str  # not_detected | detected_and_ignored
    matches: tuple[str, ...] = ()
    ruleset_hash: str = RULESET_HASH


@dataclass(frozen=True)
class ReviewEvaluation:
    """Cache evaluation of a stored review receipt (state_domain="cache")."""

    status: str  # not_detected | detected_and_ignored | not_reviewed
    cache_state: str  # hit | ignored | expired | tampered | absent
    state_domain: str  # C7: REQUIRED explicit domain tag (cache)
    reason: str = ""

    def __post_init__(self) -> None:
        # C7 fail-closed: missing (TypeError at construction) or illegal or
        # cross-domain tags are refused — ambiguity must never pass.
        if self.state_domain not in STATE_DOMAINS:
            raise PromptInjectionGuardError(
                f"state_domain {self.state_domain!r} is missing or illegal — "
                f"fail closed (ambiguity is never defaulted)")
        if self.state_domain != STATE_DOMAIN_CACHE:
            raise PromptInjectionGuardError(
                f"ReviewEvaluation state_domain must be 'cache', "
                f"got {self.state_domain!r}")
        # GUARD-MERGE §1-4 union-of-strictness (I-06-A side): an evaluation
        # carrying a value outside the cache vocabulary is refused too — the
        # tag and the tagged state must both be legal, never defaulted.
        if self.cache_state not in CACHE_STATES:
            raise PromptInjectionGuardError(
                f"cache_state {self.cache_state!r} is not a legal cache-domain "
                f"state — fail closed (ambiguity is never defaulted)")


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
        # C7 fail-closed: no valid domain tag => ambiguous => never trusted.
        if receipt.get("state_domain") != STATE_DOMAIN_REVIEW:
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
            state_domain=STATE_DOMAIN_CACHE,
            reason="source bytes changed since review",
        )
    if receipt.get("policy_hash") != policy_hash:
        return ReviewEvaluation(
            status="not_reviewed", cache_state="ignored",
            state_domain=STATE_DOMAIN_CACHE,
            reason="policy ruleset changed since review",
        )
    return None


def _freshness(receipt: dict[str, Any], now: str, ttl_seconds: float) -> ReviewEvaluation | None:
    """expired (older than TTL) or tampered (unparseable timestamps, or a
    ``now`` earlier than ``reviewed_at`` — clock anomaly, never fresh).

    ``ttl_seconds`` reaching this function is already policy-bounded:
    ``evaluate_review`` rejects anything above
    ``POLICY_RECEIPT_TTL_CAP_SECONDS`` before the receipt is read, so the
    only reachable path here is ``ttl_seconds <= cap`` (callers may only
    tighten further).
    """
    reviewed_at = _iso_seconds(str(receipt.get("reviewed_at") or ""))
    now_seconds = _iso_seconds(now)
    if reviewed_at is None or now_seconds is None:
        return ReviewEvaluation(
            status="not_reviewed", cache_state="tampered",
            state_domain=STATE_DOMAIN_CACHE,
            reason="receipt reviewed_at is not ISO-8601 UTC",
        )
    if now_seconds < reviewed_at:
        # OPEN-6 C6: the caller's `now` may only TIGHTEN freshness.  A `now`
        # before reviewed_at makes the age negative (never > ttl_seconds),
        # which would let a rewound clock resurrect an expired receipt —
        # fail closed as a clock anomaly instead of reporting fresh.
        return ReviewEvaluation(
            status="not_reviewed", cache_state="tampered",
            state_domain=STATE_DOMAIN_CACHE,
            reason="receipt reviewed_at is after now "
                   "(clock anomaly; now may only tighten freshness)",
        )
    if now_seconds - reviewed_at > ttl_seconds:
        return ReviewEvaluation(
            status="not_reviewed", cache_state="expired",
            state_domain=STATE_DOMAIN_CACHE,
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

    ``ttl_seconds`` is bounded by the policy CAP
    (``POLICY_RECEIPT_TTL_CAP_SECONDS``, 2592000s = 30 days): callers may
    only tighten; a wider TTL raises ``PromptInjectionGuardError`` (OPEN-6
    ruling C6 / owner §十九 option A).  Validation order (TTL card, frozen):
    source_sha256 -> policy_hash -> ttl<0 -> over-cap REJECT -> isfinite,
    all before the receipt is read.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise PromptInjectionGuardError("source_sha256 must be a lowercase SHA-256")
    if not re.fullmatch(r"[0-9a-f]{64}", policy_hash):
        raise PromptInjectionGuardError("policy_hash must be a lowercase SHA-256")
    if ttl_seconds < 0:
        raise PromptInjectionGuardError("ttl_seconds must be >= 0")
    if ttl_seconds > POLICY_RECEIPT_TTL_CAP_SECONDS:
        raise PromptInjectionGuardError(
            "ttl_seconds exceeds policy cap of 2592000s")
    if not math.isfinite(ttl_seconds):
        raise PromptInjectionGuardError("ttl_seconds must be a finite number")
    receipt = _receipt_from_store(store, document_id)
    if receipt is None:
        return ReviewEvaluation(
            status="not_reviewed", cache_state="absent",
            state_domain=STATE_DOMAIN_CACHE)
    mismatch = _binding_mismatch(receipt, source_sha256, policy_hash)
    if mismatch is not None:
        return mismatch
    stale = _freshness(receipt, now, ttl_seconds)
    if stale is not None:
        return stale
    return ReviewEvaluation(
        status=str(receipt["status"]), cache_state="hit",
        state_domain=STATE_DOMAIN_CACHE,
        reason="receipt fresh and bound",
    )


__all__ = [
    "CACHE_STATES",
    "POLICY_RECEIPT_TTL_CAP_SECONDS",
    "PROMPT_INJECTION_GUARD_SCHEMA",
    "PROMPT_INJECTION_GUARD_SCHEMA_VERSION",
    "RULESET_HASH",
    "STATE_DOMAINS",
    "PromptInjectionGuardError",
    "ReviewEvaluation",
    "ScanResult",
    "evaluate_review",
    "require_state_domain",
    "scan_text",
]
