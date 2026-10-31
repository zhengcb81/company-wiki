"""Patch comparison.md for the executed X1 arms (2026-10-31)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
p = REPO / "delivery" / "w23-xiaomi-ocr" / "comparison.md"
t = p.read_text(encoding="utf-8")


def rep(old, new):
    global t
    assert t.count(old) == 1, ("anchor count != 1", old[:70])
    t = t.replace(old, new)


rep(
    "**Verdict up front: PARTIAL, by resource bounds — not by engine quality.** The\n"
    "comparison ran the production RapidOCR arm (R0) and the born-digital control\n"
    "(N0) over the full frozen 14-page sample. The Xiaomi arm (X1) could not be executed: UNSUPPORTED on this host under the card memory bound, measured stage by stage (§2)",
    "**Verdict up front: PARTIAL.** The comparison executed the production RapidOCR\n"
    "arm (R0), the born-digital control (N0) and the Xiaomi arm over the frozen\n"
    "14-page sample — Xiaomi via a declared variant (X1F: exact fp32 upcast of the\n"
    "frozen checkpoint, read-only file mapping) after the upstream-exact load path\n"
    "proved impossible under the card memory bound on this host (§2). X1F completed\n"
    "13/14 pages with EOS inside the card budget; the 14th is not_run (30-minute\n"
    "budget exhausted), and the upstream-exact bf16 arm timed out once with partial\n"
    "text. X2 (two-stage) remains not_run.",
)

rep(
    "| X1 | HF `xiaomi-research/Xiaomi-OCR-0@bbd8cf8d…` (Qwen3.5-0.8B VLM; `model.safetensors` 1,746,937,856 B, SHA-256 `d4551e9f…b5d5348` = HF LFS blob), transformers 5.18.0 native `qwen3_5`, upstream prompt/non-thinking/greedy, upstream 2048-bound resize | pilot page unsupported at weight loading under the card bound; other 13 pages not_run (pilot-first rule) |",
    "| X1F | same frozen checkpoint (SHA above), widened losslessly bf16→fp32 (`model.fp32.safetensors`, SHA-256 `ddd3b661…9dcc71f`), read-only file mapping, upstream prompt/non-thinking/greedy/2048-bound/postprocess, manual greedy decode with explicit cache | **13/14 pages ok (all EOS)**; 1 not_run (budget) |\n"
    "| X1-bf16 | upstream-exact dtype arm (same everything, bf16) | 1 attempt: timeout at the 600 s upstream request deadline with 242 correct partial tokens |",
)

start = t.index("## 2. X1 not runnable")
end = t.index("## 3. R0 baseline results")
t = t[:start] + """## 2. X1 execution on this host: what failed, why, and what ran

**What ran (final state):** X1F — the frozen checkpoint widened losslessly to
fp32 (bf16 is truncated fp32, so the numbers are identical; no quantization),
mapped read-only into the process, upstream prompt/template/decoding/postprocess,
manual greedy decode with an explicit cache. Card-compliant pilot on the lightest
page: ok in 69 s with EOS, job peak 2.582 GiB under cap 3.895 GiB. Full batch:
13/14 pages ok, every ok page finished with EOS, 1801.6 s of request time under
the 1800 s card budget, job peak 2.812 GiB under cap 3.864 GiB. The upstream-exact
bf16 arm got one attempt and timed out at the upstream 600 s request deadline
with 242 correct partial tokens (peak 2.321 GiB, within bounds).

**What failed first, and the measured root causes** (each fixed in the tool, no
card bound was ever raised; full history in `x1_feasibility_measured.json` v3):

1. `from_pretrained` copy-loading needs ~3.1 GiB of private commit for weights +
   stack; every measured card cap (1.14–2.34 GiB) refused it (OS error 1455).
2. `torch.from_file(shared=False)` maps copy-on-write, which Windows charges in
   full against commit — an invisible 1.63–3.26 GiB surcharge that masqueraded as
   model memory. Fixed with a true read-only section (`mmap` ACCESS_READ +
   `torch.frombuffer`): commit-free, verified tensor-byte-identical to
   `safe_open` copies.
3. Prefill computed logits for all ~3000 positions: one ~2.85 GiB tensor.
   Eliminated with `logits_to_keep=1` (exactly what generate() does).
4. `generate()` ran without an effective cache for this hybrid linear-attention
   architecture — every decode step recomputed the prefix (~15× slower).
   Replaced by a manual greedy loop passing `past_key_values` explicitly (same
   greedy math; measured 1.4 s/step vs 15–22 s).
5. This CPU (Alder Lake, no AMX/AVX512-BF16) runs torch's large bf16 GEMM at
   **0.5 GFLOPS** vs **330 GFLOPS** fp32 (measured on 2048³). The bf16 arm
   therefore cannot prefill a page within any card deadline — its honest result
   is the recorded timeout. The exact fp32 upcast computes at full speed with
   identical numbers; this dtype/loading variant is declared in the arm identity
   and never equated with the official GPU leaderboard.

**Consequence for reading the numbers:** X1F results below are the frozen model's
numbers on this CPU through a declared load/compute variant — real measured
quality, not a leaderboard reproduction; X2 (PP-DocLayoutV3 two-stage) remains
not_run for its own dependency reason.

""" + t[end:]

rep(
    "## 3. R0 baseline results (production current state)",
    "## 3. Results (R0 baseline vs executed X1F)",
)

rep(
    "Aggregate over gold-verified pages (macro = mean per-page, micro = pooled\nchars; strict CER keeps real char differences; narrow CER is the declared\nNFC+whitespace normalization):",
    "Aggregate over gold-verified pages (macro = mean per-page, micro = pooled\nchars; strict CER keeps real char differences; narrow CER is the declared\nNFC+whitespace normalization; X1F scored on all 9 eval pages and 4/5 holdout\npages, the 5th being not_run):",
)

old_table_tail = "| holdout (5) | 5 | 0.1694 | 0.1732 | 0.1290 | 0.1917 (n=1) | 0.9367 (gold 74/79) | 0.9737 |"
new_table_tail = old_table_tail + """

X1F (mapped-f32) on the same frozen pages:

| split | pages | macro CER strict | micro CER strict | macro CER narrow | English WER | number recall (exact tokens) | number digit-present | precision |
|-------|-------|------------------|------------------|------------------|-------------|------------------------------|----------------------|-----------|
| eval (8+1 degraded) | 9 | **0.0860** | **0.0734** | **0.0376** | **0.1025** (n=1) | 0.7266 | 0.8870 | 0.8532 |
| holdout (4 run + 1 not_run) | 4 | **0.1158** | 0.0899 | 0.0400 | — | 0.2459 | 0.8131 | 0.5000 |

X1F vs R0, eval: character errors roughly halve (0.086 vs 0.160 strict; 0.038 vs
0.125 narrow) and the English page WER drops from 0.300 to 0.102. Two structural
differences drive the exact-token number gap: X1F's OTSL-to-text path
concatenates table cells ("乘用车4,281,0843,033,66241.12%…"), which exact tokens
undercount (digit-present recall 0.887 recovers it — the digits are all there),
and holdout page byd p022 is almost entirely one such table (token recall 0.085,
digit-present 0.90+). Where R0 structurally fails, X1F succeeds: every checkbox
state is read correctly ("☑适用 □不适用", "☑特定对象调研"; R0 lost all of them),
the negation line and the English opening line R0 dropped are complete, and the
superscript footnote is handled right (392.0, where R0 reads 392.01). Where X1F
loses: the stylized "2024 年度報告" year art on the meituan cover (its single
fact miss), and one holdout page not attempted at all (budget). The degraded
(synthetic 0.55×/1.3°) page scores identically to its clean twin (CER 0.051
both) — markedly more robust to low-resolution tilt than a classical pipeline
needs to be. Human fact scoring (`fact_scores_x1.json`): eval 76/76 facts and
10/10 conditions; holdout 31/32 facts and 8/8 conditions; zero fabrication, zero
repetition loops. X1F cost: 57–235 s per page (median ~130 s) at 1 batch, single
model process, plus ~12 s cold load — vs R0's ~16 s/page."""

assert t.count(old_table_tail) == 1
t = t.replace(old_table_tail, new_table_tail)

rep(
    "- **可进一步接入 (Xiaomi)**: cannot be assessed on this host — no CPU-feasible\n  path exists under the card bounds on this host. The measured requirement is\n  about 6.5 GB of available RAM at run start (card cap of about 3.2 GiB), or a\n  host with a GPU. The replayable runner is\n  `python -m tools.ocr_comparison.run_x1 --pages pilot:byd_ar_2024_p021 --tag <tag>`;\n  it refuses to silently change any identity axis.",
    "- **可进一步接入 (Xiaomi)**: now a measured answer, with two caveats. On\n"
    "  TEXT quality X1F halves R0's character error (0.086 vs 0.160 strict) and\n"
    "  reads checkbox states, negations and the superscript footnote that R0\n"
    "  structurally misses; on dense numeric tables the OTSL-to-text path\n"
    "  concatenates cells (digits present, tokens scrambled) and its exact-token\n"
    "  number recall trails R0 (0.73 vs 0.92 eval; digit-present 0.89 closes most\n"
    "  of the gap). Cost on this CPU: 57–235 s/page vs R0's ~16 s, via a declared\n"
    "  load/compute variant (exact fp32 upcast, read-only mapping, manual greedy\n"
    "  decode) — NOT the upstream bf16 runtime, which cannot prefill a page here\n"
    "  (bf16 large-GEMM 0.5 GFLOPS on this AMX-less CPU; recorded timeout), and\n"
    "  never the GPU leaderboard. Integration decisions stay with ROOT; the\n"
    "  reading-layer adapter sketch below remains design-only.",
)

rep(
    "- `x1_pilot_real_receipt.json`, `x1_pilot_stage_receipt.json`, `x1_pilot_cap_now_receipt.json` — the three X1 attempts;\n  `x1_feasibility_measured.json` — the consolidated measured record; `probe_x1_commit_steps.py` — per-step commit probe.\n  Superseded: `pilot_x1.json` (preflight-based record, retracted in §2).",
    "- X1 execution: `x1_pilot_f32_final_receipt.json` (card-compliant pilot, ok),\n  `x1_full_f32_receipt.json` (13/14 batch), `x1_pilot_bf16_receipt.json`\n  (upstream-arm timeout with partial text), `fact_scores_x1.json` (human fact\n  scoring), `x1_feasibility_measured.json` v3 (full root-cause history).\n  Copy-load failure history: `x1_pilot_real/stage/cap_now/after_chrome_receipt.json`;\n  probes `probe_x1_commit_steps.py`, `probe_mmap_under_job.py`.\n  Superseded: `pilot_x1.json` (preflight-based record, retracted in §2).",
)

p.write_text(t, encoding="utf-8")
print("comparison.md patched for executed X1")
