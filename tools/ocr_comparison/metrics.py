"""Frozen metrics for the W23 OCR comparison.

Pure functions only: no model, no network, no filesystem.  All normalization
is the *declared narrow* form (NFC + whitespace removal); script conversion or
synonym replacement is refused because silent folding would inflate scores.

strict CER keeps every real character difference (e.g. 雲 vs 云 counts as a
substitution); the narrow-normalized CER is reported alongside it, never
instead of it.  English WER lowercases tokens and strips edge punctuation
(declared).  Numbers are compared as deduplicated multisets so repeated lines
add no recall and fabricated numbers hit precision.
"""

from __future__ import annotations

import re
import unicodedata

_NUMBER_RE = re.compile(
    # OCR thousands-group artifact: whitespace may follow a group comma or the
    # decimal point ("4, 281, 084", "41. 12%"), but bare digit-space-digit
    # stays separate tokens.
    r"[+-]?\d+(?:[ \t]*,[ \t]*\d+)*(?:[ \t]*\.[ \t]*\d+)?(?:%)?"
)
# Longer suffixes first so 百萬元 wins over 百萬.
_UNIT_SUFFIXES = (
    "billion", "million", "trillion",
    "百萬美元", "百万美元", "百萬元", "百万元", "億元", "亿元",
    "万件", "万支", "万片", "億", "亿", "萬", "万",
)
_SIGN_RE = re.compile(r"^[+-]")


def narrow_normalize(text: str, *, fold_synonyms: bool = False) -> str:
    """Declared narrow normalization: NFC + whitespace removal, nothing else."""
    if fold_synonyms:
        raise ValueError("synonym folding is not allowed in declared normalization")
    if not isinstance(text, str):
        raise TypeError("text must be str")
    composed = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", "", composed)


def _edit_ops(ref, hyp) -> tuple[int, dict[str, int]]:
    """Levenshtein distance with operation attribution over any sequence.

    Elements may be characters (CER) or tokens (WER); insertions counted in hyp.
    """
    rows = len(ref) + 1
    cols = len(hyp) + 1
    dist = [[0] * cols for _ in range(rows)]
    ins = [[0] * cols for _ in range(rows)]
    dele = [[0] * cols for _ in range(rows)]
    sub = [[0] * cols for _ in range(rows)]
    for i in range(1, rows):
        dist[i][0] = i
        dele[i][0] = i
    for j in range(1, cols):
        dist[0][j] = j
        ins[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            if ref[i - 1] == hyp[j - 1]:
                dist[i][j] = dist[i - 1][j - 1]
                ins[i][j] = ins[i - 1][j - 1]
                dele[i][j] = dele[i - 1][j - 1]
                sub[i][j] = sub[i - 1][j - 1]
                continue
            candidates = (
                (dist[i - 1][j] + 1, ins[i - 1][j], dele[i - 1][j] + 1, sub[i - 1][j]),
                (dist[i][j - 1] + 1, ins[i][j - 1] + 1, dele[i][j - 1], sub[i][j - 1]),
                (dist[i - 1][j - 1] + 1, ins[i - 1][j - 1], dele[i - 1][j - 1], sub[i - 1][j - 1] + 1),
            )
            best = min(candidates, key=lambda c: c[0])
            dist[i][j], ins[i][j], dele[i][j], sub[i][j] = best
    return dist[-1][-1], {
        "insertions": ins[-1][-1],
        "deletions": dele[-1][-1],
        "substitutions": sub[-1][-1],
    }


def cer_strict_ops(ref: str, hyp: str) -> tuple[int, dict[str, int]]:
    """Strict CER edit distance and op counts over NFC-composed text."""
    return _edit_ops(unicodedata.normalize("NFC", ref), unicodedata.normalize("NFC", hyp))


def cer_strict(ref: str, hyp: str) -> int:
    return cer_strict_ops(ref, hyp)[0]


def char_error_rate(ref: str, hyp: str) -> float:
    distance, _ = cer_strict_ops(ref, hyp)
    denominator = len(unicodedata.normalize("NFC", ref))
    if denominator == 0:
        return 0.0 if not hyp else float("inf")
    return distance / denominator


_TOKEN_STRIP = '.,;:!?"\'()[]{}<>«»、。；：！？（）“”‘’'


def wer(ref: str, hyp: str) -> tuple[int, dict[str, int], int]:
    """English word error rate; declared token rule: lowercase, strip edge punctuation."""
    ref_tokens = [_strip_edge(t.lower()) for t in ref.split()]
    hyp_tokens = [_strip_edge(t.lower()) for t in hyp.split()]
    ref_tokens = [t for t in ref_tokens if t]
    hyp_tokens = [t for t in hyp_tokens if t]
    if not ref_tokens and not hyp_tokens:
        return 0, {"insertions": 0, "deletions": 0, "substitutions": 0}, 0
    distance, ops = _edit_ops(ref_tokens, hyp_tokens)
    return distance, ops, len(ref_tokens)


def _strip_edge(token: str) -> str:
    return token.strip(_TOKEN_STRIP)


def extract_numbers(text: str) -> list[dict]:
    """Extract numeric tokens with sign/percent and the immediately following unit word.

    Deduplication happens in number_prf; extraction keeps first occurrences.
    """
    if not isinstance(text, str):
        raise TypeError("text must be str")
    found: list[dict] = []
    seen: set[str] = set()
    for match in _NUMBER_RE.finditer(text):
        raw = match.group(0)
        end = match.end()
        unit = ""
        for suffix in _UNIT_SUFFIXES:
            if text[end:end + len(suffix)] == suffix or (
                end < len(text) and text[end] == " "
                and text[end + 1:end + 1 + len(suffix)] == suffix
            ):
                unit = suffix
                break
        value = raw[:-1] if raw.endswith("%") else raw
        unit = "%" if raw.endswith("%") else unit
        key = raw
        if key in seen:
            continue
        seen.add(key)
        found.append({"text": raw, "value": value, "unit": unit})
    return found


def _canon_number(token: dict) -> tuple[str, str]:
    # Declared narrow canon: drop group separators and OCR-introduced internal
    # whitespace from the value ("4, 281, 084" == "4,281,084"); percent sign
    # and unit stay part of the identity.
    text = re.sub(r"[, \t]", "", token["value"])
    return text, token["unit"]


def number_prf(gold_numbers: list[dict], hyp_numbers: list[dict]) -> dict:
    """Precision/recall over deduplicated (value, unit) multisets."""
    gold = {_canon_number(n) for n in gold_numbers}
    hyp = {_canon_number(n) for n in hyp_numbers}
    hits = gold & hyp
    return {
        "gold_total": len(gold),
        "hyp_total": len(hyp),
        "recall_hits": len(hits),
        "precision_hits": len(hits),
        "recall": len(hits) / len(gold) if gold else None,
        "precision": len(hits) / len(hyp) if hyp else None,
    }


_PASS_STATUSES = frozenset({"ok"})


def counts_as_pass(status: str) -> bool:
    """Only a completed successful run passes; timeout/truncated/empty/error
    /not_run/unsupported never count as a pass."""
    return status in _PASS_STATUSES
