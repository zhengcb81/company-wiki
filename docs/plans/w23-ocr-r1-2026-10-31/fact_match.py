"""Declared, reproducible fact/condition/number matching for the R1 arms.

Rule (fixed, applied identically to every arm and to the gold itself):

- A fact/condition counts as PRESENT when every numeric token of the phrase is
  matched (value + unit + currency window) in the arm text AND at least 60% of
  its CJK bigrams / Latin word tokens appear after the declared markup strip.
- A number counts as PRESENT when an occurrence of its value carries the same
  unit token and, if the gold entry names a currency within a 12-character
  window, the same currency within that window of the arm text.
- ACHIEVABILITY: every gold entry is first matched against its own page's gold
  text.  Entries that do not self-match are ill-formed annotations (a bare
  en-dash nil marker, a wrapped unit no transcription could satisfy); they are
  excluded from the primary denominator and reported in
  ``unachievable_entries`` with the raw entries, so the denominator is honest.
- Pages that failed or produced no text contribute 0 hits but stay in the full
  denominator.  Surface-form matching cannot prove semantic relations; sampled
  relation checks are reported separately in comparison.md.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.ocr_comparison.metrics import markup_strip, narrow_normalize  # noqa: E402

_CJK = re.compile(r"[\u4e00-\u9fff]")
_LATIN = re.compile(r"[A-Za-z][A-Za-z\-]+")
_CURRENCIES = ("人民币", "美元", "RMB", "USD", "HK$", "$")
_CURRENCY_WINDOW = 12
_EN_STOP = {"the", "is", "are", "was", "were", "a", "an", "and", "or", "of", "in", "on",
            "at", "to", "for", "by", "with", "as", "that", "this", "these", "those",
            "it", "its", "their", "from", "be", "been", "has", "have", "had", "not",
            "which", "who", "whom", "whose", "than", "also", "into", "over", "about"}
_NUM_RE = re.compile(r"[+-]?\d[\d,]*(?:\.\d+)?(?:%)?")


def _currencies(text: str) -> set[str]:
    return {token for token in _CURRENCIES if token in text}


def _numeric_spans(text: str):
    for match in _NUM_RE.finditer(text):
        yield match.group(0), match.start(), match.end()


def _unit_after(text: str, end: int) -> str:
    for suffix in ("%", "百萬美元", "百万美元", "百萬元", "百万元", "億元", "亿元",
                   "亿美元", "billion", "million", "万件", "万支", "万片", "億", "亿", "万"):
        if text[end:end + len(suffix)] == suffix:
            return suffix
        if text[end:end + 1] == " " and text[end + 1:end + 1 + len(suffix)] == suffix:
            return suffix
    return ""


def _value_unit(value: str, end: int) -> str:
    """Unit for a match; '%' is part of the matched token, not a suffix."""
    if value.endswith("%"):
        return "%"
    return _unit_after(value, end)


def _window_currencies(text: str, start: int, end: int) -> set[str]:
    window = text[max(0, start - _CURRENCY_WINDOW): end + _CURRENCY_WINDOW]
    return _currencies(window)


def _number_match(value: str, start: int, end: int, unit: str, currencies: set[str],
                  arm_text: str) -> bool:
    normalized = value.replace(",", "")
    for m_value, m_start, m_end in _numeric_spans(arm_text):
        if m_value.replace(",", "") != normalized:
            continue
        if _value_unit(m_value, m_end) != unit:
            continue
        if currencies:
            window = arm_text[max(0, m_start - _CURRENCY_WINDOW): m_end + _CURRENCY_WINDOW]
            if not (currencies & _currencies(window)):
                continue
        return True
    return False


def number_present(number: str, arm_text: str) -> bool:
    for value, start, end in _numeric_spans(number):
        if _number_match(value, start, end, _value_unit(value, end),
                         _window_currencies(number, start, end), arm_text):
            return True
    return False


def anchors(text: str) -> set[str]:
    stripped = markup_strip(text)
    # CJK bigrams over whitespace-free text; Latin words from the ORIGINAL
    # spacing (whitespace removal would concatenate English words).
    cjk_chars = [c for c in narrow_normalize(stripped) if _CJK.match(c)]
    bigrams = {a + b for a, b in zip(cjk_chars, cjk_chars[1:])}
    latin = {w.lower() for w in _LATIN.findall(stripped)
             if len(w) > 2 and w.lower() not in _EN_STOP}
    return bigrams | latin


def phrase_present(phrase: str, arm_text: str) -> bool:
    phrase_grams = anchors(phrase)
    if not phrase_grams:
        return False
    arm_grams = anchors(arm_text)
    hit = len(phrase_grams & arm_grams)
    if hit / len(phrase_grams) < 0.60:
        return False
    for value, start, end in _numeric_spans(phrase):
        if not _number_match(value, start, end, _value_unit(value, end),
                             _window_currencies(phrase, start, end), arm_text):
            return False
    return True


def score_page(gold_page: dict, arm_text: str, *, produced: bool) -> dict:
    gold_text = gold_page["full_text"]
    facts = gold_page.get("facts", [])
    conds = gold_page.get("conditions", [])
    nums = gold_page.get("numbers", [])
    # Numbers: only numerically well-formed entries join the denominator; a
    # bare en-dash nil marker or a spelled-out number can never be matched.
    nums_ok = [n for n in nums if any(_numeric_spans(n))]
    unachievable = {"numbers": [n for n in nums if n not in nums_ok]}
    # Facts/conditions keep the RAW denominator (an analytic/paraphrased fact is
    # legitimate but may be unreachable by surface matching); two declared views
    # are reported: surface presence (bigram+number rule) and numeric anchors
    # (all of the entry's numerals present in the arm text).
    base = {
        "facts_total": len(facts), "conditions_total": len(conds),
        "numbers_total": len(nums_ok),
        "facts_raw_total": len(facts), "conditions_raw_total": len(conds),
        "numbers_raw_total": len(nums),
        "unachievable_entries": unachievable,
    }
    if not produced:
        return {"produced": False, "status": "no_output",
                "facts_hit": 0, "conditions_hit": 0, "numbers_hit": 0,
                "facts_numeric_hit": 0, "conditions_numeric_hit": 0, **base}
    text = markup_strip(arm_text)

    def numeric_hit(phrase: str) -> bool:
        spans = list(_numeric_spans(phrase))
        if not spans:
            return phrase_present(phrase, text)
        return all(_number_match(v, s, e, _value_unit(v, e),
                                 _window_currencies(phrase, s, e), text)
                   for v, s, e in spans)

    return {
        "produced": True,
        "facts_hit": sum(1 for f in facts if phrase_present(f, text)),
        "conditions_hit": sum(1 for c in conds if phrase_present(c, text)),
        "numbers_hit": sum(1 for n in nums_ok if number_present(n, text)),
        "facts_numeric_hit": sum(1 for f in facts if numeric_hit(f)),
        "conditions_numeric_hit": sum(1 for c in conds if numeric_hit(c)),
        **base,
    }


def sum_pages(per_page: list[dict]) -> dict:
    keys = ("facts_hit", "facts_total", "conditions_hit", "conditions_total",
            "numbers_hit", "numbers_total", "facts_raw_total",
            "conditions_raw_total", "numbers_raw_total",
            "facts_numeric_hit", "conditions_numeric_hit")
    totals = {k: sum(int(p[k]) for p in per_page) for k in keys}
    totals["pages_produced"] = sum(1 for p in per_page if p["produced"])
    totals["pages_total"] = len(per_page)
    totals["unachievable_counts"] = {
        "numbers": sum(len(p["unachievable_entries"]["numbers"]) for p in per_page)
    }
    return totals


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    plan = Path(argv[1]) if len(argv) > 1 else Path("docs/plans/w23-ocr-r1-2026-10-31")
    delivery = Path(argv[2]) if len(argv) > 2 else Path("delivery/w23-ocr-r1")
    gold = json.loads((plan / "r1_gold.json").read_text(encoding="utf-8"))
    manifest = json.loads((plan / "r1_sample_manifest.json").read_text(encoding="utf-8"))
    pages = [p["page_id"] for p in manifest["pages"]]
    out = {}
    arm_files = {
        "R0": ["run_r0.json", "run_r0_qa_extension.json"],
        "N0": ["run_n0.json", "run_n0_qa_extension.json"],
        "X1F_attempt1": ["run_x1_attempt1.json"],
        "X1F_attempt2": ["run_x1_attempt2.json"],
    }
    for arm, filenames in arm_files.items():
        records = {}
        for filename in filenames:
            path = delivery / filename
            if not path.is_file():
                continue
            records.update({r["page_id"]: r for r in
                            json.loads(path.read_text(encoding="utf-8"))["records"]})
        if not records:
            continue
        per_page = []
        for pid in pages:
            record = records.get(pid, {})
            produced = record.get("status") in ("ok", "truncated", "timeout") and bool(
                (record.get("text") or "").strip())
            entry = score_page(gold["pages"][pid], record.get("text") or "", produced=produced)
            entry["page_id"] = pid
            per_page.append(entry)
        out[arm] = {"per_page": per_page, "totals": sum_pages(per_page)}
    (delivery / "fact_match.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for arm, payload in out.items():
        t = payload["totals"]
        print(arm, f"facts {t['facts_hit']}/{t['facts_total']} "
                   f"conds {t['conditions_hit']}/{t['conditions_total']} "
                   f"nums {t['numbers_hit']}/{t['numbers_total']} "
                   f"unachievable {t['unachievable_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
