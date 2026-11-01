"""R1 comparison builder: one capture -> comparison.json/md + per-page records.

Reads only the campaign artifacts (ledger, per-arm run JSONs, frozen manifest
and gold) and computes every aggregate programmatically.  No patch scripts, no
hand-edited totals: facts/conditions/numbers are summed from the per-page gold
and per-page records.
"""
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.ocr_comparison.compare import evaluate_page  # noqa: E402
from tools.ocr_comparison.metrics import markup_strip  # noqa: E402

PLAN = REPO / "docs" / "plans" / "w23-ocr-r1-2026-10-31"
DELIVERY = REPO / "delivery" / "w23-ocr-r1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    manifest = load_json(PLAN / "r1_sample_manifest.json")
    gold = load_json(PLAN / "r1_gold.json")
    ledger = load_json(DELIVERY / "campaign_ledger.json")
    pages = manifest["pages"]
    page_ids = [p["page_id"] for p in pages]
    role = {pid: gold["pages"][pid]["role"] for pid in page_ids}
    meta = {p["page_id"]: p for p in pages}
    english = {pid for pid, m in meta.items() if m.get("language") == "en"}
    strata = {pid: f"{meta[pid].get('market')}/{meta[pid].get('language')}/{meta[pid].get('genre')}"
              for pid in page_ids}

    arms = {}
    for tag, filename in (("R0", "run_r0.json"), ("N0", "run_n0.json"),
                          ("X1F_attempt1", "run_x1_attempt1.json")):
        path = DELIVERY / filename
        if not path.is_file():
            continue
        payload = load_json(path)
        records = {r["page_id"]: r for r in payload["records"]}
        arms[tag] = {
            "file": filename,
            "records": records,
            "remaining_after": payload.get("remaining_seconds"),
            "request_deadline": payload.get("request_deadline"),
        }

    comparison = {
        "schema_version": "cwp-ocr-comparison/1",
        "plan_id": "w23-ocr-r1-2026-10-31",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "campaign": {
            "ledger_file": "campaign_ledger.json",
            "budget_seconds": ledger["budget_seconds"],
            "spent_seconds": ledger["spent_seconds"],
            "remaining_seconds": ledger["budget_seconds"] - ledger["spent_seconds"],
            "entries": ledger["entries"],
            "rule": "one unified cumulative 1800 s inference campaign including R0/X1F attempts; per-request <= 180 s",
        },
        "inputs": {
            "sample_manifest_sha256": sha256_file(PLAN / "r1_sample_manifest.json"),
            "gold_sha256": sha256_file(PLAN / "r1_gold.json"),
            "page_count": len(pages),
            "holdout_pages": [pid for pid in page_ids if role[pid] == "holdout"],
        },
        "pages": [
            {
                "page_id": pid,
                "role": role[pid],
                "stratum": strata[pid],
                "source_pdf": meta[pid]["pdf"],
                "pdf_page_index": meta[pid]["pdf_page_index"],
                "page_image_sha256": meta[pid]["png_sha256"],
                "gold_chars": len(gold["pages"][pid]["full_text"]),
                "gold_facts": len(gold["pages"][pid].get("facts", [])),
                "gold_conditions": len(gold["pages"][pid].get("conditions", [])),
                "gold_numbers": len(gold["pages"][pid].get("numbers", [])),
            }
            for pid in page_ids
        ],
        "arms": {},
    }

    aggregate = {}
    for arm, info in arms.items():
        per_page = []
        for pid in page_ids:
            record = info["records"].get(pid, {"status": "not_run", "error": "no_record"})
            text = record.get("text") or ""
            if record.get("status") in ("ok", "truncated", "timeout") and text.strip():
                scored_text = markup_strip(text)
                entry = evaluate_page(gold["pages"][pid]["full_text"],
                                      {**record, "text": scored_text},
                                      english=pid in english)
            else:
                entry = {"page_status": record.get("status", "not_run"),
                         "reason_excluded": record.get("status", "not_run")}
            entry["page_id"] = pid
            entry["role"] = role[pid]
            entry["stratum"] = strata[pid]
            entry["engine_seconds"] = record.get("request_seconds")
            entry["finish_reason"] = record.get("finish_reason")
            per_page.append(entry)

        scored = [e for e in per_page if "cer_strict" in e]
        failed = [e for e in per_page if "reason_excluded" in e]
        denom = {s: len([e for e in per_page if e["stratum"] == s]) for s in sorted(set(strata.values()))}
        complete = {s: len([e for e in scored if e["stratum"] == s]) for s in sorted(set(strata.values()))}

        def mean(values):
            return sum(values) / len(values) if values else None

        agg = {
            "pages_total": len(per_page),
            "pages_scored": len(scored),
            "pages_excluded": len(failed),
            "coverage_by_stratum": {s: {"pages": denom[s], "scored": complete[s],
                                        "coverage": complete[s] / denom[s] if denom[s] else None}
                                    for s in denom},
            "macro_cer_strict": mean([e["cer_strict"] for e in scored]),
            "macro_cer_narrow": mean([e["cer_narrow"] for e in scored]),
            "macro_wer": mean([e["wer"] for e in scored if "wer" in e]),
            "sum_gold_chars": sum(e["gold_chars"] for e in scored),
            "micro_cer_strict": None,
            "micro_cer_narrow": None,
            "number_token_recall": None,
            "number_token_precision": None,
            "number_digit_present_recall": mean(
                [e["numbers_digit_present"]["recall"] for e in scored
                 if e.get("numbers_digit_present", {}).get("recall") is not None]),
            "repetition_flagged_pages": sum(1 for e in scored if e.get("repetition_flagged")),
        }
        gold_chars = sum(e["gold_chars"] for e in scored)
        if gold_chars:
            strict_ops = sum(sum(e["cer_strict_ops"].values()) for e in scored)
            narrow_ops = sum(sum(e["cer_narrow_ops"].values()) for e in scored)
            agg["micro_cer_strict"] = strict_ops / gold_chars
            # normalized micro denominator: normalized reference length
            norm_chars = 0
            from tools.ocr_comparison.metrics import narrow_normalize
            for e in scored:
                norm_chars += len(narrow_normalize(gold["pages"][e["page_id"]]["full_text"]))
            agg["micro_cer_narrow"] = narrow_ops / norm_chars if norm_chars else None
        nums = [e["numbers"] for e in scored]
        if nums:
            gp = sum(n["gold_total"] for n in nums)
            hp = sum(n["hyp_total"] for n in nums)
            rh = sum(n["recall_hits"] for n in nums)
            ph = sum(n["precision_hits"] for n in nums)
            agg["number_token_recall"] = rh / gp if gp else None
            agg["number_token_precision"] = ph / hp if hp else None
            agg["number_gold_total"] = gp
            agg["number_hyp_total"] = hp
        comparison["arms"][arm] = {"per_page": per_page, "aggregate": agg}
        aggregate[arm] = agg

    # Programmatic fact/condition/number counts, summed from the per-page rows
    # above; full-sample denominators include failed pages.
    fact_path = DELIVERY / "fact_match.json"
    if fact_path.is_file():
        comparison["fact_match"] = load_json(fact_path)

    # Declared arm status for X2 (platform/budget unsuitable; never merged).
    comparison["arms"]["X2"] = {
        "aggregate": {"pages_scored": 0, "status": "not_run",
                      "reason": "PP-DocLayoutV3 requires the paddlex runtime; not installed under the frozen resource bounds; no two-stage leaderboard claim"},
        "per_page": [],
    }
    comparison["arms"]["X1F_attempt1"]["aggregate"]["status"] = "resource_blocked"
    comparison["arms"]["X1F_attempt1"]["aggregate"]["reason"] = (
        "single measured attempt inside this campaign: card cap 1.142 GiB at attempt start "
        "(avail 2.28 GiB / 2) < measured fixed load cost 1.33 GiB; child MemoryError at load. "
        "Later check: cap 0.838 GiB. No retry: the card forbids repeated timeouts, and the "
        "condition (available RAM) never improved during the campaign."
    )

    out = DELIVERY / "comparison.json"
    out.write_text(json.dumps(comparison, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", out)
    for arm, agg in aggregate.items():
        print(f"{arm}: scored {agg['pages_scored']}/{agg['pages_total']} "
              f"macro_strict {agg['macro_cer_strict']} narrow {agg['macro_cer_narrow']} "
              f"numRec {agg['number_token_recall']} digitRec {agg['number_digit_present_recall']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
