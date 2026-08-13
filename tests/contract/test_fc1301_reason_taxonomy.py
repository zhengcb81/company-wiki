"""FC-1301: versioned reason-taxonomy audit gate.

Every reason literal emitted in production source must be registered in
``observability.REASONS`` (additive registry; codes are never removed,
only deprecated).  An unregistered literal is a taxonomy drift — this
audit fails closed so a new reason code forces a deliberate registry edit
with a description.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"
sys.path.insert(0, str(SRC.parent))

from company_wiki.source_catalog.observability import (  # noqa: E402
    REASONS,
    REASON_TAXONOMY_VERSION,
)

# Same patterns the FC-1301 implementation used to build the registry:
# keyword reason="x" / "reason": "x" / _reject(..., "x").
_LITERAL_PATTERNS = (
    re.compile(r'reason["\s:=]+["\']([a-z][a-z_]+)["\']'),
    re.compile(r'_reject\([^,]+,\s*["\']([a-z][a-z_]+)["\']'),
)


def _emitted_codes() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for pattern in _LITERAL_PATTERNS:
            for match in pattern.finditer(text):
                code = match.group(1)
                out.setdefault(code, []).append(f"{path.name}:{text[:match.start()].count(chr(10)) + 1}")
    return out


def test_taxonomy_version_current() -> None:
    assert REASON_TAXONOMY_VERSION == "1.1", (
        "taxonomy version must be bumped when codes are added"
    )


def test_every_emitted_reason_is_registered() -> None:
    emitted = _emitted_codes()
    missing = sorted(c for c in emitted if c not in REASONS)
    assert not missing, (
        f"unregistered reason codes in production source: {missing} — "
        f"register them in observability.REASONS (additive; never remove)"
    )


def test_registry_values_are_documented() -> None:
    for code, description in sorted(REASONS.items()):
        assert isinstance(description, str) and description.strip(), (
            f"reason {code!r} lacks a description"
        )
