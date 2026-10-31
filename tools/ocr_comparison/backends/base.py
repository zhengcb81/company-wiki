"""Backend-neutral output handling: status classification, caps, repetition.

VLM outputs and native extraction share these helpers so no arm can quietly
turn a timeout/truncation into a pass, invent bbox or confidence, or hide a
generation loop.
"""

from __future__ import annotations

import hashlib
import re


def classify_raw_output(text: str, *, finish_reason: str | None) -> str:
    """Status for one raw generation output.

    ``finish_reason == "length"`` (or any non-stop reason) is truncated even
    when the text looks fine; blank text is empty_response.
    """
    if text is None or not text.strip():
        return "empty_response"
    if finish_reason is not None and finish_reason != "stop":
        return "truncated"
    return "ok"


def enforce_output_cap(text: str, *, cap: int) -> tuple[str, str]:
    """Hard output cap in characters; crossing it marks the run truncated."""
    if len(text) <= cap:
        return text, "ok"
    return text[:cap], "truncated"


_REPEAT_LINE_RE = re.compile(r"^(.{1,256})\n(?:\1\n){3,}", re.MULTILINE)


def detect_repetition(text: str, *, min_repeats: int = 8) -> dict:
    """Detect degenerate repetition: long single-char runs or repeated lines.

    A suspicious flag never changes the text; it is reported alongside.
    """
    suspicious = False
    reasons: list[str] = []
    runs = re.finditer(r"([^\s\n])\1{%d,}" % (min_repeats * 2), text)
    for _ in runs:
        suspicious = True
        reasons.append("long_single_character_run")
        break
    stripped = text.strip()
    for unit_len in range(1, 17):
        if len(stripped) >= unit_len * min_repeats and stripped == stripped[:unit_len] * (len(stripped) // unit_len):
            suspicious = True
            reasons.append(f"cyclic_unit_x{len(stripped) // unit_len}: {stripped[:unit_len]!r}")
            break
    line_counts: dict[str, int] = {}
    for line in text.splitlines():
        key = line.strip()
        if len(key) < 4:
            continue
        line_counts[key] = line_counts.get(key, 0) + 1
    for line, count in line_counts.items():
        if count >= min_repeats:
            suspicious = True
            reasons.append(f"repeated_line_x{count}: {line[:40]!r}")
            break
    match = _REPEAT_LINE_RE.search(text)
    if match:
        suspicious = True
        reasons.append("repeated_block")
    return {"suspicious": suspicious, "reasons": reasons}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def serialize_lines(lines: list[dict]) -> list[dict]:
    """Serialize line-level records with honest locator fields.

    Backends without word/line boxes keep ``bbox: null`` and
    ``confidence: null``; ``locator_quality`` states what the box actually is
    (``word_box``, ``region_crop`` or ``none``).  Never fabricate geometry.
    """
    out = []
    for line in lines:
        record = {
            "text": line["text"],
            "bbox": line.get("bbox"),
            "confidence": line.get("confidence"),
            "locator_quality": line.get("locator_quality", "none" if line.get("bbox") is None else "region_crop"),
        }
        out.append(record)
    return out
