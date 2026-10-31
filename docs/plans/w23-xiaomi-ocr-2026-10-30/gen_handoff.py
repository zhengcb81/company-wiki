"""Generate delivery/w23-xiaomi-ocr/handoff.json (harness-handoff/1)."""
import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CARD = "W23-XIAOMI-OCR"


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.strip()


def file_sha(path, *, lf_normalized):
    data = Path(path).read_bytes()
    if lf_normalized:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


CODE_FILES = [
    "tools/ocr_comparison/__init__.py",
    "tools/ocr_comparison/backends/base.py",
    "tools/ocr_comparison/backends/native_n0.py",
    "tools/ocr_comparison/backends/rapidocr_r0.py",
    "tools/ocr_comparison/backends/xiaomi_x1.py",
    "tools/ocr_comparison/cache.py",
    "tools/ocr_comparison/compare.py",
    "tools/ocr_comparison/manifest.py",
    "tools/ocr_comparison/metrics.py",
    "tools/ocr_comparison/pair_facts.py",
    "tools/ocr_comparison/render_pages.py",
    "tools/ocr_comparison/run_comparison.py",
    "tools/ocr_comparison/runner.py",
]
TEST_FILES = [
    "tests/unit/test_w23_ocr_comparison_metrics.py",
    "tests/integration/test_w23_ocr_comparison_entry.py",
]

code_shas = {
    rel: {
        "raw_sha256": file_sha(REPO / rel, lf_normalized=False),
        "lf_sha256": file_sha(REPO / rel, lf_normalized=True),
    }
    for rel in CODE_FILES + TEST_FILES
}

requirements = [
    {"req": "A1 baseline identity & model bytes", "status": "implemented/tested",
     "evidence": "three ONNX SHAs verified vs config/local_ocr.json (unchanged since de7ffe48); progress.md A entry"},
    {"req": "A2 resource detection", "status": "implemented/tested",
     "evidence": "i3-1220P/15.77GB/no GPU; per-run caps recorded in run manifests"},
    {"req": "A3 frozen upstream commit+HF revision", "status": "implemented/tested",
     "evidence": "b1a9bb4c… / bbd8cf8d…; model.safetensors 1,746,937,856B sha d4551e9f…b5d5348 = HF LFS blob"},
    {"req": "A4 one-page pilot within bounds", "status": "partial",
     "evidence": "R0 pilot ok (62.7s); X1 pilot unsupported: measured card cap (0.995GiB) < minimum load peak 3,493,875,712B; arithmetic recorded in every X1 record; no bound raised, no repeated timeouts"},
    {"req": "A5 frozen blind sample", "status": "implemented/tested",
     "evidence": "sample_manifest.json frozen pre-engine-output (commit 0d24c943); 7 docs/14 pages, exact SHAs; reviewer re-hashed all 14 PNGs + 7 PDFs"},
    {"req": "A6 human gold frozen + holdout", "status": "implemented/tested",
     "evidence": "gold.json frozen pre-engine-output; 5 holdout pages; native text only a correction base; meituan pages fully manual"},
    {"req": "B TDD comparator", "status": "implemented/tested",
     "evidence": "41/41 tests (32 unit + 9 integration); card-required locks: CER/WER ops, timeout/empty/truncated never pass, dedup numbers, cache-key axes, cache-hit latency, partial-failure batch, output cap, temp-dir cleanup, fault-injection retry, repetition guard, runner field passthrough"},
    {"req": "B R0 real production path", "status": "implemented/tested",
     "evidence": "IsolatedOCRAdapter + recover_regions ladder + production config; reviewer verified fairness"},
    {"req": "B X1 whole-page arm", "status": "partial",
     "evidence": "backend implemented (upstream prompt/non-thinking/greedy/2048-bound, dtype=checkpoint bf16); NOT executed on this host - memory bound (unsupported, honest arithmetic)"},
    {"req": "B X2 two-stage arm", "status": "partial",
     "evidence": "declared NOT_RUN with resource reason; never merged into X1"},
    {"req": "B N0 born-digital control", "status": "implemented/tested",
     "evidence": "12 ok + 1 empty (image cover) + 1 unsupported (degraded variant shares one native page)"},
    {"req": "C paired macro/micro eval", "status": "implemented/tested",
     "evidence": "eval macro strict 0.1599/micro 0.1737/narrow 0.1250, EN WER 0.300 (n=1 page/split), numRecall 0.9219/numPrec 0.9833; holdout 0.1694/0.1732 (WER 0.1917); reviewer recomputed to <1e-6"},
    {"req": "C reporting completeness (self-audit delta, post-review)", "status": "implemented/tested",
     "evidence": "per-page source/page/image_SHA joined into comparison.json + raw files (page_identity_provenance noted); raw_r0.json restored after the one-page instrumented pilot clobbered it (delta D2), engine fields byte-identical to c62ba969, provenance recorded; raw filenames now per-invocation unique (raw_output_path + test); R0 engine peak memory re-measured with a fresh-interpreter method (memwatch_r0_receipt.json schema /2: 0.671GB WS / 0.988GB commit, supersedes mislabeled /1); two-column and seal coverage gaps declared; three-run policy documented (R0 texts byte-identical, no output selection)"},
    {"req": "C fact/number/condition human scoring", "status": "implemented/tested",
     "evidence": "fact_scores.json fully accounted: facts 83/15/3, conditions 12 hit/6 miss, per-judgment evidence"},
    {"req": "C fabrication/repetition negative controls", "status": "implemented/tested",
     "evidence": "0 fabrication, 0 loops, blank-region negative control (meituan cover) clean"},
    {"req": "C cleanup & assets", "status": "implemented/tested",
     "evidence": "temp dirs recovered; page PNGs deleted post-review; ROOT untouched; single 1.7GB model snapshot as declared asset"},
    {"req": "C independent review", "status": "implemented/tested",
     "evidence": "general-purpose agent, first review NEEDS_FIXES (5 OPEN), fixes commit c62ba969, closing re-review READY_FOR_ROOT, 0 OPEN (review_independent.md)"},
    {"req": "output interfaces cwp-ocr-comparison/1 + harness-handoff/1", "status": "implemented/tested",
     "evidence": "comparison.json + this handoff.json"},
]

handoff = {
    "schema_version": "harness-handoff/1",
    "card_id": CARD,
    "plan_id": "w23-xiaomi-ocr-2026-10-30",
    "workdir": str(REPO),
    "branch": "codex/w23-xiaomi-ocr-20261030",
    "base_commit": "de7ffe48aee3f9decfb4be6dfc2f561dcd3aa29d",
    "implementation_commits": [
        "0d24c943 docs: freeze W23 OCR comparison sample and gold before any engine output",
        "8469df7c feat: add W23 OCR comparison tool with frozen metrics contracts",
        "fde39dfe feat: run W23 comparison with R0 baseline, N0 control and recorded X1/X2 resource bounds",
        "c62ba969 fix: address independent review findings - runner field passthrough, gold char-level corrections, fact accounting",
    ],
    "final_tested_commit": "c2e5dcf8",
    "final_reviewed_commit": "ca3bbbcb (delta re-review by the same independent agent, see review_independent.md)",
    "code_file_sha256": code_shas,
    "requirements": requirements,
    "overall_status": "PARTIAL",
    "status_reason": (
        "R0/N0 comparison complete and independently verified; X1 is unsupported on this host "
        "under the card's frozen memory bound (cap 0.84-1.155 GiB measured < minimum load peak "
        "3,493,875,712 B in checkpoint-native bf16) and X2 is not_run (paddlex stack outside "
        "resource bounds). No Xiaomi accuracy metric exists anywhere in the delivery; re-running "
        "tools.ocr_comparison.run_comparison on a host with more free RAM is the replayable path."
    ),
    "commands_and_results": [
        {"cmd": "python -m pytest tests/unit/test_w23_ocr_comparison_metrics.py tests/integration/test_w23_ocr_comparison_entry.py -q",
         "result": "41 passed (32 unit + 9 integration)", "time": "final run ~44s", "path": "delivery/w23-xiaomi-ocr/test_receipt.txt"},
        {"cmd": "python -m tools.ocr_comparison.run_comparison --arms R0,N0,X1,X2 --out delivery/w23-xiaomi-ocr/comparison.json",
         "result": "R0 14/14 ok; N0 12ok+1 empty+1 unsupported; X1 14 unsupported; X2 14 not_run",
         "time": "~604s", "path": "delivery/w23-xiaomi-ocr/comparison.json"},
        {"cmd": "python -m tools.ocr_comparison.run_comparison --arms X1 --pages pilot:byd_ar_2024_p021 --out delivery/w23-xiaomi-ocr/pilot_x1.json",
         "result": "unsupported memory_cap_below_minimum_load_peak", "path": "delivery/w23-xiaomi-ocr/pilot_x1.json"},
    ],
    "review": {
        "first_pass": {
            "verdict": "NEEDS_FIXES",
            "open_items": 5,
            "report": "delivery/w23-xiaomi-ocr/review_independent.md",
        },
        "fixes_commit": "c62ba969",
        "closing_pass": {"verdict": "READY_FOR_ROOT", "open_items": 0},
        "independence_note": "reviewer did not use author claims; re-hashed inputs, recomputed metrics, re-ran tests",
    },
    "cleanup_and_assets": {
        "deleted": ["render_probe thumbnails", "gold_candidates", "r0_outputs", "run temp dirs", ".w23_cache/frozen_pages (post-review)"],
        "retained_assets": [{
            "path": "company-wiki-w23-xiaomi-ocr/.w23_cache/hub (HF snapshot xiaomi-research/Xiaomi-OCR-0@bbd8cf8d…)",
            "bytes": 1773858913,
            "note": "single allowed copy; not committed; reusable for the X1 replay",
        }],
        "production_isolation": "diff de7ffe48..HEAD additions-only under docs/plans/w23-xiaomi-ocr-2026-10-30/, tools/ocr_comparison/, tests/**/test_w23_ocr_comparison_*, delivery/w23-xiaomi-ocr/; config/local_ocr.json empty diff; ROOT untouched",
    },
    "recommendation": (
        "现有不动 for the production OCR stack; track the R0 defect classes (checkbox states, "
        "isolated line drops, o-for-0 in numbers) as reading-layer concerns; Xiaomi adoption "
        "CANNOT be assessed on this host - replay X1 on a host with >=3.3GiB free RAM (bf16) or "
        "a GPU before any integration decision; reading-layer adapter shape sketched in "
        "comparison.md §4 is design-only and NOT implemented."
    ),
    "limitations": [
        "no real scanned pages in the catalog; one declared synthetic_degradation page",
        "no two-column (双栏) page in the frozen catalog slice (Q&A and cross-paragraph qualifier groups covered); no seal/stamp page",
        "X1/X2 never executed: no accuracy/latency claims about Xiaomi-OCR-0",
        "English WER has a single-page denominator per split (one EN document)",
        "R0 peak memory measured once in-process (memwatch_r0_receipt.json), excluding the isolated-child boundary overhead",
        "US 10-K filings are text/html in this catalog; EN pages covered by an earnings-call PDF",
        "gold post-review char-level corrections documented in gold.json post_review_corrections",
    ],
    "pushed_to_remote": None,
}
out = REPO / "delivery" / "w23-xiaomi-ocr" / "handoff.json"
out.write_text(json.dumps(handoff, ensure_ascii=False, indent=1), encoding="utf-8")
print("WROTE", out)
