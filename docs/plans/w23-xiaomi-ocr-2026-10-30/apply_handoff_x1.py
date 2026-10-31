"""Post-measurement update of handoff.json for the X1 correction (the earlier
preflight claim is retracted; X1 failures are measured by stage)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
path = REPO / "delivery" / "w23-xiaomi-ocr" / "handoff.json"
handoff = json.loads(path.read_text(encoding="utf-8"))

def set_requirement(prefix, status, evidence):
    for item in handoff["requirements"]:
        if item["req"].startswith(prefix):
            item["status"] = status
            item["evidence"] = evidence
            return
    raise KeyError(prefix)

set_requirement(
    "A4",
    "partial",
    "R0 pilot ok (62.7 s cold). X1 pilot: three card-compliant attempts under the Job Object limit "
    "(caps 1.14, 1.31 and 1.72 GiB). Stages reached: processor load, then the weight load, which failed "
    "with ERROR_COMMITMENT_LIMIT (x1_feasibility_measured.json). No bound raised; no repeated timeouts.",
)
set_requirement(
    "B X1",
    "partial",
    "backend implemented with the upstream prompt, greedy decoding, enable_thinking=False and the vendored "
    "upstream postprocess (byte-identical); executed in a child process under a Windows Job Object memory "
    "limit; no page completed on this host (failure measured at model_load_start).",
)
set_requirement(
    "C paired macro/micro eval",
    "implemented/tested",
    "R0 eval macro strict CER 0.1599 / micro 0.1737 / narrow 0.1250; English WER 0.300 (n=1 page per split); "
    "numRecall 0.9219 / numPrec 0.9833; holdout 0.1694 / 0.1732 (WER 0.1917). X1 has no metric: its only page "
    "is unsupported, the other 13 are not_run, and both are excluded with reasons.",
)

handoff["status_reason"] = (
    "R0/N0 comparison complete and independently verified. X1 was executed for real: three attempts in a "
    "child process under a Windows Job Object memory limit at the card rule (min(8 GiB, available/2)). Each "
    "failed at a measured stage: the processor load, then the weight load (OSError 1455, commit limit). The "
    "fixed cost before weights is about 1.33 GB (measured); the checkpoint weights are 1.63 GiB. A complete "
    "load needs roughly 6.5 GB of available RAM at run start under the card rule. X2 is not_run for its "
    "own resource reason. No Xiaomi accuracy metric exists in the delivery."
)

handoff["limitations"] = [
    "no real scanned pages in the catalog; one declared synthetic_degradation page",
    "no two-column (双栏) page in the frozen catalog slice (Q&A and cross-paragraph qualifier groups covered); no seal/stamp page",
    "X1 never completed a page on this host: measured failure at weight loading under the card cap; the 6.5 GB requirement is a projection from measured steps and the file size",
    "X2 never executed (paddlex stack outside the resource bounds)",
    "English WER has a single-page denominator per split (one EN document)",
    "R0 engine peak memory measured once in a fresh interpreter (memwatch_r0_receipt.json schema /2: 0.671 GB WS / 0.988 GB commit; excludes the isolated-child boundary overhead and the page render)",
    "US 10-K filings are text/html in this catalog; EN pages covered by an earnings-call PDF",
    "gold post-review char-level corrections documented in gold.json post_review_corrections",
]

handoff["recommendation"] = (
    "现有不动 for the production OCR stack; treat R0's defect classes (checkbox states, isolated line drops, "
    "o-for-0 in numbers) as reading-layer concerns. The Xiaomi question remains open on this host: it needs "
    "about 6.5 GB of available RAM at run start (close desktop applications) or a host with a GPU, and then "
    "the card-compliant pilot must be re-run and measured. A runtime change would be a new declared arm, not "
    "the upstream checkpoint."
)

handoff["commands_and_results"] = [
    cmd for cmd in handoff["commands_and_results"]
    if "run_comparison --arms X1" not in cmd.get("cmd", "")
    and "pilot_x1.json" not in cmd.get("path", "")
]
handoff["commands_and_results"] += [
    {"cmd": "python -m tools.ocr_comparison.run_x1 --pages pilot:byd_ar_2024_p021 --tag pilot_real",
     "result": "child rc 0xC0000409; Rust allocation failure 17,301,520 B; no record",
     "path": "delivery/w23-xiaomi-ocr/x1_pilot_real_receipt.json"},
    {"cmd": "python -m tools.ocr_comparison.run_x1 --pages pilot:byd_ar_2024_p021 --tag pilot_stage",
     "result": "MemoryError at processor_load_start (cap 1.139 GiB, job peak 1.126 GiB)",
     "path": "delivery/w23-xiaomi-ocr/x1_pilot_stage_receipt.json"},
    {"cmd": "python -m tools.ocr_comparison.run_x1 --pages pilot:byd_ar_2024_p021 --tag pilot_cap_now",
     "result": "processor loaded; OSError 1455 at model_load_start (cap 1.717 GiB, job peak 1.332 GiB)",
     "path": "delivery/w23-xiaomi-ocr/x1_pilot_cap_now_receipt.json"},
    {"cmd": "python docs/plans/w23-xiaomi-ocr-2026-10-30/probe_x1_commit_steps.py (under a 2 GiB job limit)",
     "result": "torch +519 MiB; transformers qwen3_5 modeling +567 MiB; processor +172 MiB; safetensors access failed 1455",
     "path": "delivery/w23-xiaomi-ocr/x1_feasibility_measured.json"},
]

path.write_text(json.dumps(handoff, ensure_ascii=False, indent=1), encoding="utf-8")
print("handoff.json updated for the X1 measured correction")
