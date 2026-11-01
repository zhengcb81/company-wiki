"""Declared, reproducible fact/condition/number matching for the R1 arms.

Rule (fixed before the run, applied identically to every arm):

- A fact/condition counts as PRESENT when
  (a) every numeric token it contains appears in the arm text with the same
      unit token (comma/space-insensitive value; printed currency/unit must
      match), and
  (b) at least 60% of its CJK bigrams and lower-cased Latin word tokens appear
      in the arm text after the declared markup/normalization strip.
- A number counts as PRESENT when its (value, unit) pair appears.
- Pages that failed or produced no text contribute 0 hits but stay in the
  denominator (full-sample coverage is reported separately from completed-page
  scores).  This is a surface-form check only: it cannot prove semantic
  relations, which is why sampled relation checks are reported separately in
  comparison.md and why gold itself is an independent visual transcription.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.ocr_comparison.metrics import extract_numbers, markup_strip, narrow_normalize  # noqa: E402

_CJK = re.compile(r"[\u4e00-\u9fff]")
_LATIN = re.compile(r"[A-Za-z][A-Za-z\-]+")


def anchors(text: str) -> tuple[set[str], set[tuple[str, str]]]:
    """(character bigram set, numeric (value,unit) set) for one phrase."""
    normalized = narrow_normalize(markup_strip(text))
    cjk_chars = [c for c in normalized if _CJK.match(c)]
    bigrams = {a + b for a, b in zip(cjk_chars, cjk_chars[1:])}
    latin = {w.lower() for w in _LATIN.findall(normalized)}
    nums = {(n["value"].replace(",", ""), n["unit"]) for n in extract_numbers(text)}
    return bigrams | latin, nums


def phrase_present(phrase: str, arm_text: str) -> bool:
    phrase_bigrams, phrase_nums = anchors(phrase)
    if not phrase_bigrams and not phrase_nums:
        return False
    arm_bigrams, arm_nums = anchors(arm_text)
    if phrase_nums and not phrase_nums <= arm_nums:
        return False
    if phrase_bigrams:
        hit = len(phrase_bigrams & arm_bigrams)
        if hit / len(phrase_bigrams) < 0.60:
            return False
    return True


def number_present(number: str, arm_text: str) -> bool:
    want = {(n["value"].replace(",", ""), n["unit"]) for n in extract_numbers(number)}
    have = {(n["value"].replace(",", ""), n["unit"]) for n in extract_numbers(arm_text)}
    return bool(want) and want <= have


def score_page(gold_page: dict, arm_text: str, *, produced: bool) -> dict:
    if not produced:
        return {
            "produced": False,
            "facts_hit": 0, "facts_total": len(gold_page.get("facts", [])),
            "conditions_hit": 0, "conditions_total": len(gold_page.get("conditions", [])),
            "numbers_hit": 0, "numbers_total": len(gold_page.get("numbers", [])),
        }
    text = markup_strip(arm_text)
    facts = gold_page.get("facts", [])
    conds = gold_page.get("conditions", [])
    nums = gold_page.get("numbers", [])
    return {
        "produced": True,
        "facts_hit": sum(1 for f in facts if phrase_present(f, text)),
        "facts_total": len(facts),
        "conditions_hit": sum(1 for c in conds if phrase_present(c, text)),
        "conditions_total": len(conds),
        "numbers_hit": sum(1 for n in nums if number_present(n, text)),
        "numbers_total": len(nums),
    }


def sum_pages(per_page: list[dict]) -> dict:
    keys = ("facts_hit", "facts_total", "conditions_hit", "conditions_total",
            "numbers_hit", "numbers_total")
    totals = {k: sum(int(p[k]) for p in per_page) for k in keys}
    totals["pages_produced"] = sum(1 for p in per_page if p["produced"])
    totals["pages_total"] = len(per_page)
    return totals
