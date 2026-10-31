"""Rewrite the X1 delivery records from the measured X1 receipts (no engine output
is invented; R0/N0 records are untouched).  Inputs: the three X1 pilot receipts
and the frozen sample manifest and gold."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.ocr_comparison.backends.xiaomi_x1 import XiaomiX1  # noqa: E402
from tools.ocr_comparison.compare import evaluate_split  # noqa: E402
from tools.ocr_comparison.job_limit import GIB, card_memory_cap_bytes, host_memory_snapshot  # noqa: E402

D = REPO / "delivery" / "w23-xiaomi-ocr"
PLAN = REPO / "docs" / "plans" / "w23-xiaomi-ocr-2026-10-30"
MODEL_DIR = REPO / ".w23_cache" / "hub" / "models--xiaomi-research--Xiaomi-OCR-0" / "snapshots" / "bbd8cf8d21f256b3644b44cb860f3a7cecb93c30"

manifest = json.loads((PLAN / "sample_manifest.json").read_text(encoding="utf-8"))
gold = json.loads((PLAN / "gold.json").read_text(encoding="utf-8"))
identity_of = {}
for p in manifest["pages"]:
    doc = manifest["documents"][p["doc"]]
    identity_of[p["page_id"]] = {
        "source_id": doc["source_id"],
        "document_id": doc["document_id"],
        "content_sha256": doc["content_sha256"],
        "pdf_page_index": p["pdf_page_index"],
        "page_image_sha256": p["png_sha256"],
        "market": doc["market"],
        "language": doc["language"],
        "genre": doc["genre"],
    }


def receipt(name):
    return json.loads((D / name).read_text(encoding="utf-8"))


ATTEMPT_FILES = [
    ("attempt_1_pilot_real", "x1_pilot_real_receipt.json"),
    ("attempt_2_pilot_stage", "x1_pilot_stage_receipt.json"),
    ("attempt_3_pilot_cap_now", "x1_pilot_cap_now_receipt.json"),
]

attempts = []
for tag, name in ATTEMPT_FILES:
    payload = receipt(name)
    r = payload["receipt"]
    attempts.append({
        "tag": tag,
        "receipt": name,
        "host_avail_gib_at_start": round(r["host_before"]["avail_phys_bytes"] / GIB, 3),
        "card_cap_gib": r["memory"]["cap_gib"],
        "job_peak_gib": r["memory"]["job_peak_process_gib"],
        "child_return_code": r["child"]["return_code"],
        "child_wall_seconds": r["child"]["wall_seconds"],
        "events": r["child"]["events"],
        "page_record": payload["records"][0],
        "stderr_tail": r["child"]["stderr_tail"][-500:],
    })

now = host_memory_snapshot()
feasibility = {
    "schema_version": "cwp-ocr-x1-feasibility/2",
    "verdict": "UNSUPPORTED on this host under the card memory bound (measured stage by stage; no X1 page completed)",
    "supersedes": "pilot_x1.json (preflight-based record, memory_cap_below_minimum_load_peak); its 2 x weight-bytes premise was never measured",
    "card_rule": "peak commit <= min(8 GiB, available physical RAM / 2) measured at each run start; enforced by a Windows Job Object ProcessMemoryLimit",
    "attempts": attempts,
    "probe": {
        "script": "docs/plans/w23-xiaomi-ocr-2026-10-30/probe_x1_commit_steps.py (run under a 2 GiB job limit)",
        "steps": [
            {"step": "import torch", "status": "ok", "commit_delta_bytes": 544673792},
            {"step": "import transformers qwen3_5 modeling module", "status": "ok", "commit_delta_bytes": 594939904},
            {"step": "import transformers qwen3_vl processing module", "status": "ok", "commit_delta_bytes": 393216},
            {"step": "Qwen3VLProcessor.from_pretrained", "status": "ok", "commit_delta_bytes": 180338688},
            {"step": "safetensors access to model.safetensors (largest tensor)", "status": "error",
             "error": "OSError: os error 1455 (ERROR_COMMITMENT_LIMIT) under the 2 GiB job limit"},
        ],
    },
    "measured_facts": [
        "attempt 3 (cap 1.717 GiB): processor loaded (commit 1.43 GB at processor_loaded), then the weight load failed with OSError 1455 at model_load_start",
        "attempt 2 (cap 1.139 GiB): MemoryError while loading the processor (last stage processor_load_start)",
        "attempt 1 (cap 1.311 GiB): Rust allocation failure of 17,301,520 B within 15 s; not instrumented, so the stage is unknown",
        "fixed cost before any weight is read: about 1.33 GB committed (probe steps 1 to 4)",
        "R0 ONNX engine without torch: peak commit 0.988 GB on a representative page (memwatch_r0_receipt.json, schema /2)",
    ],
    "not_measured": [
        "end-to-end peak commit with the checkpoint weights resident (no attempt got past model_load_start)",
        "per-page latency of Xiaomi-OCR-0 on this CPU (no page completed)",
    ],
    "projection_labelled": {
        "what": "fixed cost 1.33 GB (measured) plus checkpoint weights 1,746,937,856 B (file size); not a measured end-to-end peak",
        "estimated_load_commit_gib": round((1330000000 + 1746937856) / GIB, 2),
        "implied_card_cap_gib_before_activations": "about 2.9 GiB; with generation activations roughly 3.2 GiB",
        "implied_available_ram_gb_at_run_start": "about 6.5 GB",
    },
    "host_avail_gib_now": round(now["avail_phys_bytes"] / GIB, 3),
    "card_cap_gib_now": round(card_memory_cap_bytes(now["avail_phys_bytes"]) / GIB, 3),
    "options_for_the_user": [
        "free about 3 to 4 GB of physical RAM on this host (close desktop applications) and re-run the card-compliant pilot; the peak must then be measured",
        "run on a host with about 6.5 GB or more of available RAM at run start, or with a GPU, where the card rule is not binding",
        "change runtime (for example an ONNX export of the VLM): a new, declared arm with its own identity, not the upstream checkpoint, and a larger engineering step",
        "keep X1 UNSUPPORTED with this evidence",
    ],
}
(D / "x1_feasibility_measured.json").write_text(json.dumps(feasibility, ensure_ascii=False, indent=1), encoding="utf-8")

pilot_record = receipt("x1_pilot_cap_now_receipt.json")["records"][0]
records = []
for page in manifest["pages"]:
    pid = page["page_id"]
    if pid == "byd_ar_2024_p021":
        rec = {**pilot_record,
               "status": "unsupported",
               "failure_stage": "model_load_start",
               "failure_reason": "commit limit (os error 1455) while loading the weights under card cap 1.717 GiB",
               "receipt": "x1_pilot_cap_now_receipt.json"}
    else:
        rec = {"page_id": pid, "status": "not_run",
               "error": "pilot_unsupported_under_card_bound: page not attempted; no memory bound raised"}
    rec["page_identity"] = identity_of[pid]
    records.append(rec)
raw = {
    "records": records,
    "summary": {"pages_total": 14, "pages_ok": 0, "batch_status": "unsupported"},
    "receipt": "x1_pilot_cap_now_receipt.json",
    "note": "supersedes the preflight-based raw_x1.json; see x1_feasibility_measured.json",
}
(D / "raw_x1.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")

comp_path = D / "comparison.json"
comp = json.loads(comp_path.read_text(encoding="utf-8"))
identity = XiaomiX1(model_dir=str(MODEL_DIR), deadline_seconds=180.0,
                    max_new_tokens=4096, dtype="bfloat16").identity_manifest
evaluation = {"arm": "X1"}
for split in ("eval", "holdout"):
    part = evaluate_split(gold, records, manifest, arm="X1")[split]
    for entry in part["per_page"]:
        entry["page_identity"] = identity_of[entry["page_id"]]
    evaluation[split] = part
comp["arms"]["X1"] = {
    "identity": identity,
    "summary": {"pages_total": 14, "pages_ok": 0, "batch_status": "unsupported",
                "pilot_attempts": 3, "pilot_receipts": [name for _, name in ATTEMPT_FILES]},
    "evaluation": evaluation,
    "raw_output_file": "raw_x1.json",
    "feasibility_record": "x1_feasibility_measured.json",
}
comp_path.write_text(json.dumps(comp, ensure_ascii=False, indent=1), encoding="utf-8")

agg = comp["arms"]["X1"]["evaluation"]["eval"]["aggregate"]
print("feasibility v2 written; host avail GiB now", feasibility["host_avail_gib_now"],
      "cap", feasibility["card_cap_gib_now"])
print("X1 eval pages_scored", agg["pages_scored"], "status counts", agg["page_status_counts"])
