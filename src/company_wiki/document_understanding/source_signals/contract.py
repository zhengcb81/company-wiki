"""du4-source-signal-observation/1 input contract and text-reference resolution.

Pure and deterministic: no configuration, filesystem, network or clock access,
no input mutation, no source locator allocation.  Structural malformation
(wrong schema, duplicate carrier unit ids, impossible reference indices)
raises ``ValueError``.  Recoverable evidence problems — a reference the source
text cannot back, a hidden DEI carrier, a value split across owners — are
per-item diagnostics that leave the rest of the document usable.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA_IN = "du4-source-signal-observation/1"
SCHEMA_OUT = "du4-source-signals/1"

KIND_DEI = "visible_inline_xbrl_document_type"
KIND_OWN_FORM = "visible_own_form_label"
KIND_TURN = "native_speaker_turn"

CARRIER_KINDS = frozenset({KIND_DEI, KIND_OWN_FORM, KIND_TURN})
FORM_CARRIER_KINDS = (KIND_DEI, KIND_OWN_FORM)

# attributes carries only these natively observed facts.  Anything else —
# notably a declarative provider ``form_type`` — is ignored with a diagnostic
# and can never manufacture an observed record.
NATIVE_ATTRIBUTE_KEYS = frozenset(
    {"concept", "visibility", "speaker", "turn_id", "turn_role"}
)

UNIT_REQUIRED_KEYS = ("text", "parent_id", "role", "kind", "locator")
REF_REQUIRED_KEYS = ("unit_id", "char_start", "char_end")

# Limited lexical vocabulary of printed SEC form literals.  This is a
# known/unknown check for diagnostics only; it is deliberately not a document
# family or route classification.
_FORM_LITERAL_RE = re.compile(
    r"^[A-Z]{0,2}\d{0,3}-[A-Z0-9]{1,3}(?:/[A-Z0-9]{1,3})?$"
)
_FORM_PREFIX_RE = re.compile(r"^\s*FORM\b[\s:：]*", re.IGNORECASE)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_unit_shape(unit_id: str, unit: Any) -> None:
    require(isinstance(unit, Mapping), f"units[{unit_id!r}] must be a mapping")
    for key in UNIT_REQUIRED_KEYS:
        require(key in unit, f"units[{unit_id!r}] missing required field {key!r}")
    require(isinstance(unit["text"], str), f"units[{unit_id!r}].text must be a string")
    for key in ("parent_id", "role", "kind"):
        require(
            bool(isinstance(unit[key], str) and unit[key]),
            f"units[{unit_id!r}].{key} must be a non-empty string",
        )
    require(
        isinstance(unit["locator"], str),
        f"units[{unit_id!r}].locator must be a string",
    )


def validate_ref_shape(ref: Any, *, where: str) -> tuple[str, int, int]:
    require(isinstance(ref, Mapping), f"{where} must be a mapping TextRef")
    for key in REF_REQUIRED_KEYS:
        require(key in ref, f"{where} missing required field {key!r}")
    unit_id = ref["unit_id"]
    require(
        bool(isinstance(unit_id, str) and unit_id),
        f"{where}.unit_id must be a non-empty string",
    )
    start = ref["char_start"]
    end = ref["char_end"]
    for name, value in (("char_start", start), ("char_end", end)):
        require(
            isinstance(value, int) and not isinstance(value, bool),
            f"{where}.{name} must be an int",
        )
    require(start >= 0, f"{where}.char_start must be >= 0")
    require(end >= start, f"{where}.char_end must be >= char_start")
    return unit_id, start, end


def normalize_form_value(raw: str) -> str:
    """Limited normalization of a printed form literal.

    Strips a leading ``FORM`` label, collapses whitespace and upper-cases.
    The raw writing is always preserved separately by the caller.
    """
    text = _FORM_PREFIX_RE.sub("", raw.strip())
    text = re.sub(r"\s+", " ", text).strip()
    return text.upper()


def is_known_form_literal(normalized: str) -> bool:
    return bool(_FORM_LITERAL_RE.match(normalized))


def declared_literal(normalized: str) -> str | None:
    """Extract a form-literal token from declarative metadata, if any."""
    for token in re.split(r"[\s,;|/]+", normalized):
        if token and is_known_form_literal(token):
            return token
    return None


def ref_text(unit_text: str, start: int, end: int) -> str:
    return unit_text[start:end]
