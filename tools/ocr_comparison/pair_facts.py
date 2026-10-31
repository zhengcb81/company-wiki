"""Assist manual fact scoring: for each eval page, print gold facts next to
the arm's output so a human can mark hit/miss/wrong-subject/condition-loss.
The judgment itself is recorded by hand into fact_scores.json — the tool only
pairs the texts, never auto-approves facts.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLAN = REPO / "docs" / "plans" / "w23-xiaomi-ocr-2026-10-30"
DELIVERY = REPO / "delivery" / "w23-xiaomi-ocr"

arm = sys.argv[1] if len(sys.argv) > 1 else "R0"
raw = json.loads((DELIVERY / f"raw_{arm.lower()}.json").read_text(encoding="utf-8"))["records"]
manifest = json.loads((PLAN / "sample_manifest.json").read_text(encoding="utf-8"))
gold = json.loads((PLAN / "gold.json").read_text(encoding="utf-8"))

by_page = {r["page_id"]: r for r in raw}
english = {k for k, v in manifest["documents"].items() if v["language"] == "en"}
for page in manifest["pages"]:
    if page["role"] != "eval":
        continue
    pid = page["page_id"]
    rec = by_page.get(pid, {})
    print(f"===== {pid} [{page['doc']}] status={rec.get('status')}")
    out_text = rec.get("text", "")
    for i, fact in enumerate(gold["pages"][pid].get("facts", [])):
        print(f"  F{i}: {fact}")
    for i, cond in enumerate(gold["pages"][pid].get("conditions", [])):
        print(f"  C{i}: {cond}")
    print("  --- output excerpt (first 600 chars) ---")
    print("  " + out_text[:600].replace("\n", "\n  "))
    print()
