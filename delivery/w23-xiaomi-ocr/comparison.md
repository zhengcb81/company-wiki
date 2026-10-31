# W23 OCR Comparison Report (cwp-ocr-comparison/1)

PLAN_ID=w23-xiaomi-ocr-2026-10-30 · worktree `company-wiki-w23-xiaomi-ocr` · branch `codex/w23-xiaomi-ocr-20261030`

**Verdict up front: PARTIAL.** The comparison executed the production RapidOCR
arm (R0), the born-digital control (N0) and the Xiaomi arm over the frozen
14-page sample — Xiaomi via a declared variant (X1F: exact fp32 upcast of the
frozen checkpoint, read-only file mapping) after the upstream-exact load path
proved impossible under the card memory bound on this host (§2). X1F completed
13/14 pages with EOS inside the card budget; the 14th is not_run (30-minute
budget exhausted), and the upstream-exact bf16 arm timed out once with partial
text. X2 (two-stage) remains not_run.
on this host under the card's frozen memory bound, and the two-stage arm (X2)
is NOT_RUN for the same dependency reason. No accuracy claim about Xiaomi-OCR-0
is made anywhere in this report.

## 1. What was compared

| arm | identity | result |
|-----|----------|--------|
| R0 | production `LocalOCRConfig` (RapidOCR 3.8.1 / ORT 1.26.0, PP-OCRv4 mobile det/rec + ppocr v2 cls, 2/1 threads), executed through the production `IsolatedOCRAdapter` boundary incl. bounded region recovery; three model SHAs verified against `config/local_ocr.json` | 14/14 pages ok |
| X1F | same frozen checkpoint (SHA above), widened losslessly bf16→fp32 (`model.fp32.safetensors`, SHA-256 `ddd3b661…9dcc71f`), read-only file mapping, upstream prompt/non-thinking/greedy/2048-bound/postprocess, manual greedy decode with explicit cache | **13/14 pages ok (all EOS)**; 1 not_run (budget) |
| X1-bf16 | upstream-exact dtype arm (same everything, bf16) | 1 attempt: timeout at the 600 s upstream request deadline with 242 correct partial tokens |
| X2 | two-stage PP-DocLayoutV3 upstream pipeline | **not_run** (paddlex stack outside resource bounds; never merged into X1) |
| N0 | pypdfium2 text layer, born-digital control only | 12 ok + 1 empty (image cover) + 1 unsupported (degraded variant) |

Sample: 7 documents / 14 pages = 8 eval + 5 holdout + 1 declared
`synthetic_degradation` (KSX p2 same-page 0.55×/1.3° — no real scans exist in
the catalog; not counted as scan coverage). Known coverage gaps, listed per
the card's "样本不足列缺口" rule and NOT filled post-freeze: no two-column
(双栏) page in the catalog slice selected — the Q&A and cross-paragraph
qualifier groups are covered, the two-column group is not; and no seal/stamp
(印章) pages exist among the frozen documents. Markets CN zh-CN / HK zh / US en;
genres annual/semi-annual/quarterly reports, IR Q&A, convertible-bond
prospectus, EN earnings call. Sample manifest and gold were frozen **before any
engine output existed** (`gold.json.frozen_before_engine_outputs=true`); native
PDF text was only a correction base (meituan p11's native layer is scrambled
and both meituan pages are full manual transcriptions).

## 2. X1 execution on this host: what failed, why, and what ran

**What ran (final state):** X1F — the frozen checkpoint widened losslessly to
fp32 (bf16 is truncated fp32, so the numbers are identical; no quantization),
mapped read-only into the process, upstream prompt/template/decoding/postprocess,
manual greedy decode with an explicit cache. Card-compliant pilot on the lightest
page: ok in 69 s with EOS, job peak 2.582 GiB under cap 3.895 GiB. Full batch:
13/14 pages ok, every ok page finished with EOS, 1801.6 s of request time against
the 1800 s card budget (+0.09%: budget enforcement fires at dispatch, so the last
in-flight page was allowed to finish — disclosed), job peak 2.812 GiB under cap 3.864 GiB. The upstream-exact
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

## 3. Results (R0 baseline vs executed X1F)

Aggregate over gold-verified pages (macro = mean per-page, micro = pooled
chars; strict CER keeps real char differences; narrow CER is the declared
NFC+whitespace normalization; X1F scored on all 9 eval pages and 4/5 holdout
pages, the 5th being not_run):

| split | pages | macro CER strict | micro CER strict | macro CER narrow | English WER | number recall | number precision |
|-------|-------|------------------|------------------|------------------|-------------|---------------|------------------|
| eval (8+1 degraded) | 9 | 0.1599 | 0.1737 | 0.1250 | 0.300 (n=1) | 0.9219 (gold 118/128) | 0.9833 |
| holdout (5) | 5 | 0.1694 | 0.1732 | 0.1290 | 0.1917 (n=1) | 0.9367 (gold 74/79) | 0.9737 |

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
model process, plus ~12 s cold load — vs R0's ~16 s/page.

English WER covers exactly one page per split (the US-listed earnings-call
document); with a single-page denominator it is indicative, not a
population estimate. Per-page `wer`/`wer_ops` are in comparison.json.

Number identity uses the declared narrow canon: OCR thousands-group spacing
("4, 281, 084") is one token; `392.0¹ → 392.01` stays a wrong number.

Latency and footprint: per-page engine seconds in `raw_r0.json` (median 15.6 s, cold max 20.2 s in
the final run; the 62.7 s pilot cold-start included first-launch ONNX session
setup); single concurrency, no deadline violations (limits untouched:
production pixel/deadline bounds as configured). Peak engine memory, measured
once on a representative page in a fresh interpreter that loads only the R0
engine (`memwatch_r0_receipt.json`, schema /2): peak working set 0.671 GB,
peak commit 0.988 GB for the ONNX det/cls/rec sessions plus one transcribe —
the production isolated child performs the same work with the same model
bytes; the receipt excludes only the child-process boundary overhead and the
page render. Region diagnostics:
8 dropped low-score regions, 3 bounded recovery attempts across the sample,
0 repetition flags — all recorded per page in the raw JSON.

Human fact scoring (`fact_scores.json`, author-judged with per-judgment
evidence, fully accounted against gold): eval pages 48 fact-hits / 10 partial /
1 miss (59 facts) + 8 condition-hits / 2 condition-losses; holdout 35 hit /
5 partial / 2 miss (42 facts) + 4 condition-hits / 4 condition-losses; conditions lost concentrate in one recurring class.
No fabrication, no loops, no blank-region inventions on any of the 14 pages
(meituan image cover is the negative control — output contains only real
cover strings, and even reads the drone-box micro print gold had marked
"indeterminate", which is recall, not invention).

R0's recurring defect classes (the honest baseline picture):

1. **Checkbox glyph/state unreadable** — every ☑/□ state row (BYD 适用/不适用
   ×5, IR category box) loses the checked state. This is exactly the class the
   production low-confidence/recovery path already surfaces as diagnostics.
2. **Isolated line drops** with short garbage fragments on English pages
   (`- q d o o`, `- - t q p`), costing e.g. the 21.9B revenue clause and the
   non-GAAP loss sentence on the call script page.
3. **o-for-0-style char errors inside numbers** on EN pages (`7o%`, `5o%`).
4. **Table cell order scrambles** multi-column rows (values preserved, order
   interleaved) — the geometry reader fixes this downstream (`ocr_page_text`).
5. **Superscript merge**: `392.0¹` → `392.01` (inherited by any glyph-based
   engine; flagged as a wrong number by the comparator).

## 4. What this means (recommendation within card scope)

- **现有不动**: for the general pipeline nothing in this evidence supports
  changing the production OCR stack — R0 is functional, fast (sub-minute
  per page cold), and its failure classes are already observable as
  diagnostics/recovery records.
- **局部困难页补救** is the one evidence-backed gap worth tracking: checked
  checkbox states and the rare dropped-line classes above. These are reading-
  layer concerns and out of this card's scope to fix.
- **可进一步接入 (Xiaomi)**: now a measured answer, with two caveats. On
  TEXT quality X1F halves R0's character error (0.086 vs 0.160 strict) and
  reads checkbox states, negations and the superscript footnote that R0
  structurally misses; on dense numeric tables the OTSL-to-text path
  concatenates cells (digits present, tokens scrambled) and its exact-token
  number recall trails R0 (0.73 vs 0.92 eval; digit-present 0.89 closes most
  of the gap). Cost on this CPU: 57–235 s/page vs R0's ~16 s, via a declared
  load/compute variant (exact fp32 upcast, read-only mapping, manual greedy
  decode) — NOT the upstream bf16 runtime, which cannot prefill a page here
  (bf16 large-GEMM 0.5 GFLOPS on this AMX-less CPU; recorded timeout), and
  never the GPU leaderboard. Integration decisions stay with ROOT; the
  reading-layer adapter sketch below remains design-only.
- Minimum internal wiring for a future reading-layer adapter (design only,
  NOT implemented): a `transcribe(bytes, limits) -> ImageOCRResult`-shaped
  adapter returning empty `lines` plus a markdown payload would violate the
  current contract (lines are the only text channel); the honest shape is a
  new arm interface with `bbox=None`/`confidence=None` and a
  `locator_quality="none"` payload, aligned to this tool's serialization —
  plus tests that forbid fabricated boxes. This belongs to the shared reading
  layer, not to this card.

## 5. Artifacts

- `comparison.json` — machine report (`cwp-ocr-comparison/1`): run manifest,
  per-arm identity/summary/evaluation; the final invocation ran all four arms
  in-process (an earlier N0-only re-run `comparison_n0.json` exists because the
  first invocation's N0 arm hit an import bug, fixed before the final run).
- `raw_r0.json` / `raw_n0.json` / `raw_x1.json` / `raw_x2.json` — per-page
  records incl. statuses, timings, error strings.
- `fact_scores.json` — human fact/condition scoring with evidence.
- `pilot_r0.json` — R0 pilot receipt; `memwatch_r0_receipt.json` — R0 engine peak-memory run (schema /2).
- X1 execution: `x1_pilot_f32_final_receipt.json` (card-compliant pilot, ok),
  `x1_full_f32_receipt.json` (13/14 batch), `x1_pilot_bf16_receipt.json`
  (upstream-arm timeout with partial text), `fact_scores_x1.json` (human fact
  scoring), `x1_feasibility_measured.json` v3 (full root-cause history).
  Copy-load failure history: `x1_pilot_real/stage/cap_now/after_chrome_receipt.json`;
  probes `probe_x1_commit_steps.py`, `probe_mmap_under_job.py`.
  Superseded: `pilot_x1.json` (preflight-based record, retracted in §2).
- `test_receipt.txt` — 40/40 W23 tests (31 unit + 9 integration).
- Frozen inputs (committed): `docs/plans/w23-xiaomi-ocr-2026-10-30/
  {sample_manifest,gold}.json`; code under `tools/ocr_comparison/` (committed).

## 6. Cleanup & assets

- Page PNGs and rendered temp dirs: owned temp dirs, deleted on exit
  (`render_pages` runs inside `tempfile.mkdtemp`, removed in `finally`).
- Model snapshot: single copy at
  `company-wiki-w23-xiaomi-ocr/.w23_cache/hub/.../snapshots/bbd8cf8d…`
  (1.77 GB, not committed; explicit experiment asset per card).
- No production files touched; catalog opened read-only; no processes/ports
  left behind (runner is synchronous, child adapters closed per page).
