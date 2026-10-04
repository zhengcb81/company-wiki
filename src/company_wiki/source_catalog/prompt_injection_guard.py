"""Small deterministic scanner used to write optional source diagnostics."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

PROMPT_INJECTION_GUARD_SCHEMA_VERSION = "1.0"
PROMPT_INJECTION_GUARD_SCHEMA = "prompt-injection-guard-1.0"

_RULESET_PATTERNS: tuple[tuple[str, str], ...] = (
    ("ignore_previous_instructions", r"ignore\s+(all\s+)?(previous|prior)\s+instructions"),
    ("system_prompt_override", r"you\s+are\s+now\s+(an?\s+)?(the\s+)?(system|admin|root)"),
    ("prompt_leak_request", r"(reveal|print|show|output)\s+(your\s+)?(system\s+)?prompt"),
    ("instruction_injection", r"disregard\s+(all\s+)?(previous|prior)\s+instructions"),
    ("exfiltration", r"send\s+(the\s+)?(contents?|data|file)\s+to\s+https?://"),
)
RULESET_HASH = hashlib.sha256(
    json.dumps(
        [list(item) for item in _RULESET_PATTERNS],
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
).hexdigest()


class PromptInjectionGuardError(ValueError):
    """Raised when scanner input is invalid."""


@dataclass(frozen=True)
class ScanResult:
    """Deterministic scanner result; it carries no approval semantics."""

    status: str
    matches: tuple[str, ...] = ()
    ruleset_hash: str = RULESET_HASH


def scan_text(text: str, ruleset_hash: str = RULESET_HASH) -> ScanResult:
    """Return a diagnostic classification for text without deciding access."""
    if not isinstance(text, str):
        raise PromptInjectionGuardError("text must be a string")
    if not isinstance(ruleset_hash, str) or not re.fullmatch(
        r"[0-9a-f]{64}", ruleset_hash
    ):
        raise PromptInjectionGuardError("ruleset_hash must be a lowercase SHA-256")
    if ruleset_hash != RULESET_HASH:
        raise PromptInjectionGuardError(f"unknown ruleset hash {ruleset_hash!r}")
    lowered = text.lower()
    matches = tuple(
        pattern_id
        for pattern_id, pattern in _RULESET_PATTERNS
        if re.search(pattern, lowered)
    )
    return ScanResult(
        status="detected_and_ignored" if matches else "not_detected",
        matches=matches,
    )


__all__ = [
    "PROMPT_INJECTION_GUARD_SCHEMA",
    "PROMPT_INJECTION_GUARD_SCHEMA_VERSION",
    "RULESET_HASH",
    "PromptInjectionGuardError",
    "ScanResult",
    "scan_text",
]
