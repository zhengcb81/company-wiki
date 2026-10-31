"""Paired evaluation across arms: macro and micro CER/WER, number PRF,
fabrication and repetition flags.

Eval pages only for headline scores; holdout pages are scored separately and
never tune anything.  Failed pages (timeout/empty/truncated/error) are listed
with their status and excluded from char denominators — never counted as
zero-cost successes.
"""

from __future__ import annotations

from pathlib import Path

from .backends.base import sha256_text
from .metrics import (
    cer_strict_ops,
    char_error_rate,
    extract_numbers,
    narrow_normalize,
    number_prf,
    wer,
)


# Pages whose produced text is scored: complete output, plus output cut short by
# the length cap or the request deadline (the partial text is what the arm
# produced within its bound; it counts as a quality result, never as a pass).
PRODUCED_OUTPUT_STATUSES = frozenset({"ok", "truncated", "timeout"})


def evaluate_page(gold_text: str, record: dict, *, english: bool) -> dict:
    result: dict = {"page_status": record["status"]}
    text = record.get("text") or ""
    if record["status"] not in PRODUCED_OUTPUT_STATUSES or not text.strip():
        result["reason_excluded"] = record["status"]
        return result
    hyp = text
    result["hyp_sha256"] = sha256_text(hyp)
    strict_dist, ops = cer_strict_ops(gold_text, hyp)
    gold_len = len(gold_text)
    result["cer_strict"] = strict_dist / gold_len if gold_len else None
    result["cer_strict_ops"] = ops
    gold_n = narrow_normalize(gold_text)
    hyp_n = narrow_normalize(hyp)
    narrow_dist, narrow_ops = cer_strict_ops(gold_n, hyp_n)
    result["cer_narrow"] = narrow_dist / len(gold_n) if gold_n else None
    result["cer_narrow_ops"] = narrow_ops
    if english:
        w_dist, w_ops, w_ref = wer(gold_text, hyp)
        result["wer"] = w_dist / w_ref if w_ref else None
        result["wer_ops"] = w_ops
    result["numbers"] = number_prf(extract_numbers(gold_text), extract_numbers(hyp))
    # Supplementary, declared lenient view: VLM tables concatenate cells
    # ("4,281,0843,033,662"), so exact tokens undercount.  A gold number counts
    # as digit-present when its comma/space-stripped digit string occurs in the
    # hypothesis digit string.  Reported alongside, never instead of, the exact
    # token metric above.
    import re as _re

    def digits(s):
        return _re.sub(r"[^0-9]", "", s)
    gold_digits = digits(gold_text)
    hyp_digits = digits(hyp)
    gold_nums = {n["value"].replace(",", "") for n in extract_numbers(gold_text)}
    hit = sum(1 for v in gold_nums if digits(v) and digits(v) in hyp_digits)
    result["numbers_digit_present"] = {
        "gold_total": len(gold_nums),
        "hits": hit,
        "recall": hit / len(gold_nums) if gold_nums else None,
    }
    result["hyp_chars"] = len(hyp)
    result["gold_chars"] = gold_len
    result["repetition_flagged"] = bool(record.get("repetition", {}).get("suspicious"))
    return result


def aggregate(per_page: list[dict]) -> dict:
    """Macro (mean of per-page rates) and micro (pooled chars) aggregates."""
    scored = [p for p in per_page if "cer_strict" in p]
    failed = [p for p in per_page if "reason_excluded" in p]
    macro_cer_strict = (
        sum(p["cer_strict"] for p in scored) / len(scored) if scored else None
    )
    macro_cer_narrow = (
        sum(p["cer_narrow"] for p in scored) / len(scored) if scored else None
    )
    gold_total = sum(p["gold_chars"] for p in scored)
    strict_dist_total = sum(
        p["cer_strict_ops"]["insertions"]
        + p["cer_strict_ops"]["deletions"]
        + p["cer_strict_ops"]["substitutions"]
        for p in scored
    )
    narrow_dist_total = sum(
        p["cer_narrow_ops"]["insertions"]
        + p["cer_narrow_ops"]["deletions"]
        + p["cer_narrow_ops"]["substitutions"]
        for p in scored
    )
    wer_scores = [p["wer"] for p in scored if "wer" in p and p["wer"] is not None]
    numbers = [p["numbers"] for p in scored]
    recall_hits = sum(n["recall_hits"] for n in numbers)
    gold_nums = sum(n["gold_total"] for n in numbers)
    hyp_nums = sum(n["hyp_total"] for n in numbers)
    precision_hits = sum(n["precision_hits"] for n in numbers)
    status_counts: dict[str, int] = {}
    for p in per_page:
        status_counts[p["page_status"]] = status_counts.get(p["page_status"], 0) + 1
    return {
        "pages_scored": len(scored),
        "page_status_counts": status_counts,
        "pages_failed": [p["page_status"] for p in failed],
        "macro_cer_strict": macro_cer_strict,
        "macro_cer_narrow": macro_cer_narrow,
        "micro_cer_strict": strict_dist_total / gold_total if gold_total else None,
        "micro_cer_narrow": narrow_dist_total / gold_total if gold_total else None,
        "macro_wer": sum(wer_scores) / len(wer_scores) if wer_scores else None,
        "number_recall": recall_hits / gold_nums if gold_nums else None,
        "number_precision": precision_hits / hyp_nums if hyp_nums else None,
        "number_gold_total": gold_nums,
        "number_hyp_total": hyp_nums,
        "repetition_flagged_pages": sum(1 for p in scored if p.get("repetition_flagged")),
    }


def evaluate_split(gold: dict, records: list[dict], manifest: dict, *, arm: str) -> dict:
    """Evaluate eval pages and holdout pages separately for one arm."""
    english_docs = {
        doc_id for doc_id, spec in manifest["documents"].items()
        if spec["language"] == "en"
    }
    by_page = {r["page_id"]: r for r in records}
    out: dict = {"arm": arm}
    for split in ("eval", "holdout"):
        per_page = []
        for page in manifest["pages"]:
            role = "holdout" if page["role"] == "holdout" else "eval"
            if role != split:
                continue
            record = by_page.get(page["page_id"], {"page_id": page["page_id"], "status": "not_run"})
            gold_text = gold["pages"][page["page_id"]]["full_text"]
            english = page["doc"] in english_docs
            entry = evaluate_page(gold_text, record, english=english)
            entry["page_id"] = page["page_id"]
            per_page.append(entry)
        out[split] = {"per_page": per_page, "aggregate": aggregate(per_page)}
    return out
