"""Consolidate the executed X1 arms into the delivery (2026-10-31).

Sub-arms:
  X1 (upstream-exact bf16, mapped bf16 file) — one dense-page attempt,
  timeout at the 600 s upstream request deadline with 242 partial tokens.
  X1F (declared exact fp32 upcast, mapped fp32 file) — card-compliant batch,
  13/14 pages ok (one not_run after the 30-minute total budget).

Both ran in a child process under a Windows Job Object at the card memory cap.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.ocr_comparison.backends.xiaomi_x1 import (  # noqa: E402
    MODEL_REVISION, UPSTREAM_COMMIT, XiaomiX1,
)
from tools.ocr_comparison.compare import evaluate_split  # noqa: E402
from tools.ocr_comparison.job_limit import GIB  # noqa: E402

D = REPO / "delivery" / "w23-xiaomi-ocr"
PLAN = REPO / "docs" / "plans" / "w23-xiaomi-ocr-2026-10-30"
MODEL_DIR = (REPO / ".w23_cache" / "hub" / "models--xiaomi-research--Xiaomi-OCR-0"
             / "snapshots" / MODEL_REVISION)

manifest = json.loads((PLAN / "sample_manifest.json").read_text(encoding="utf-8"))
gold = json.loads((PLAN / "gold.json").read_text(encoding="utf-8"))
identity_of = {}
for p in manifest["pages"]:
    doc = manifest["documents"][p["doc"]]
    identity_of[p["page_id"]] = {
        "source_id": doc["source_id"], "document_id": doc["document_id"],
        "content_sha256": doc["content_sha256"], "pdf_page_index": p["pdf_page_index"],
        "page_image_sha256": p["png_sha256"], "market": doc["market"],
        "language": doc["language"], "genre": doc["genre"],
    }

f32_run = json.loads((D / "x1_full_f32_receipt.json").read_text(encoding="utf-8"))
bf16_run = json.loads((D / "x1_pilot_bf16_receipt.json").read_text(encoding="utf-8"))
pilot_run = json.loads((D / "x1_pilot_f32_final_receipt.json").read_text(encoding="utf-8"))

records_f32 = {r["page_id"]: r for r in f32_run["records"]}
bf16_record = bf16_run["records"][0]
pilot_record = pilot_run["records"][0]

# raw_x1.json: one record per page. X1F is the executed arm; the bf16 page
# (byd p021) additionally carries the upstream-exact attempt; the rest of the
# bf16 arm was not attempted (its one attempt timed out; card: no repeated
# timeouts).
records = []
for page in manifest["pages"]:
    pid = page["page_id"]
    rec = dict(records_f32.get(pid) or {"page_id": pid, "status": "not_run",
               "error": "total_inference_budget_exhausted"})
    rec["page_identity"] = identity_of[pid]
    rec["arm"] = "X1F"
    if pid == bf16_record["page_id"]:
        rec["upstream_bf16_attempt"] = {
            k: bf16_record.get(k) for k in (
                "status", "finish_reason", "generated_tokens", "request_seconds",
                "engine_seconds", "text_sha256")}
        rec["upstream_bf16_attempt"]["text_head_160"] = bf16_record.get("text", "")[:160]
    records.append(rec)
raw = {
    "records": records,
    "summary": {
        "pages_total": 14,
        "pages_ok": sum(1 for r in records if r["status"] == "ok"),
        "batch_status": "partial",
        "note": "X1F (mapped-f32) executed 13/14; 14th not_run after the 30-min budget; "
                "upstream-exact bf16 arm attempted once on byd_ar_2024_p021 -> timeout with partial text",
    },
    "receipts": {
        "x1f_batch": "x1_full_f32_receipt.json",
        "x1f_pilot": "x1_pilot_f32_final_receipt.json",
        "bf16_attempt": "x1_pilot_bf16_receipt.json",
    },
}
(D / "raw_x1.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")

identity_f32 = XiaomiX1(model_dir=str(MODEL_DIR), deadline_seconds=600.0,
                        max_new_tokens=16384, weights_mode="mapped-f32").identity_manifest
identity_bf16 = XiaomiX1(model_dir=str(MODEL_DIR), deadline_seconds=600.0,
                         max_new_tokens=16384, weights_mode="mapped").identity_manifest

evaluation = {"arm": "X1F"}
for split in ("eval", "holdout"):
    part = evaluate_split(gold, records, manifest, arm="X1F")[split]
    for entry in part["per_page"]:
        entry["page_identity"] = identity_of[entry["page_id"]]
    evaluation[split] = part
bf16_eval = evaluate_split(gold, [dict(bf16_record, page_id=bf16_record["page_id"])],
                           manifest, arm="X1-bf16")["eval"]

comp_path = D / "comparison.json"
comp = json.loads(comp_path.read_text(encoding="utf-8"))
comp["arms"]["X1"] = {
    "identity": identity_f32,
    "upstream_bf16_identity": identity_bf16,
    "summary": {
        "pages_total": 14, "pages_ok": 13, "batch_status": "partial",
        "sub_arms": {
            "X1F": ("declared variant: exact fp32 upcast of the frozen bf16 checkpoint, "
                    "read-only file mapping, CPU; 13/14 ok, all ok pages finished with EOS"),
            "X1-bf16": ("upstream-exact dtype arm; one attempt on byd_ar_2024_p021 -> "
                        "timeout at the 600 s upstream request deadline with 242 partial tokens; "
                        "not re-attempted (card: no repeated timeouts)"),
        },
        "pilot": "x1_pilot_f32_final_receipt.json (cover page ok in 69 s, EOS, peak 2.58 GiB under cap)",
        "budget": {"total_inference_seconds": 1800, "spent_request_seconds": 1801.6},
        "memory": {"cap_gib": f32_run["receipt"]["memory"]["cap_gib"],
                   "job_peak_gib": f32_run["receipt"]["memory"]["job_peak_process_gib"],
                   "enforcement": "Windows Job Object ProcessMemoryLimit at min(8 GiB, avail RAM/2)"},
    },
    "evaluation": evaluation,
    "upstream_bf16_attempt_evaluation": bf16_eval,
    "raw_output_file": "raw_x1.json",
    "feasibility_record": "x1_feasibility_measured.json",
}
comp_path.write_text(json.dumps(comp, ensure_ascii=False, indent=1), encoding="utf-8")

for split in ("eval", "holdout"):
    agg = evaluation[split]["aggregate"]
    dig = [p["numbers_digit_present"]["recall"] for p in evaluation[split]["per_page"]
           if p.get("numbers_digit_present", {}).get("recall") is not None]
    print(f"X1F {split}: macro {agg['macro_cer_strict']:.4f} micro {agg['micro_cer_strict']:.4f} "
          f"narrow {agg['macro_cer_narrow']:.4f} WER {agg['macro_wer']} "
          f"numTokR {agg['number_recall']:.4f} digitR {sum(dig)/len(dig):.4f} "
          f"counts {agg['page_status_counts']}")
b = bf16_eval["per_page"][0]
print("bf16 page:", b["page_id"], b["page_status"],
      "CER", round(b["cer_strict"], 3) if "cer_strict" in b else None,
      "hyp_chars", b.get("hyp_chars"))
print("raw_x1.json + comparison.json updated")
