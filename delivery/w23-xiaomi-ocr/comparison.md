# W23 OCR Comparison Report (cwp-ocr-comparison/1)

PLAN_ID=w23-xiaomi-ocr-2026-10-30 · worktree `company-wiki-w23-xiaomi-ocr` · branch `codex/w23-xiaomi-ocr-20261030`

**Verdict up front: PARTIAL, by resource bounds — not by engine quality.** The
comparison ran the production RapidOCR arm (R0) and the born-digital control
(N0) over the full frozen 14-page sample. The Xiaomi arm (X1) is UNSUPPORTED
on this host under the card's frozen memory bound, and the two-stage arm (X2)
is NOT_RUN for the same dependency reason. No accuracy claim about Xiaomi-OCR-0
is made anywhere in this report.

## 1. What was compared

| arm | identity | result |
|-----|----------|--------|
| R0 | production `LocalOCRConfig` (RapidOCR 3.8.1 / ORT 1.26.0, PP-OCRv4 mobile det/rec + ppocr v2 cls, 2/1 threads), executed through the production `IsolatedOCRAdapter` boundary incl. bounded region recovery; three model SHAs verified against `config/local_ocr.json` | 14/14 pages ok |
| X1 | HF `xiaomi-research/Xiaomi-OCR-0@bbd8cf8d…` (Qwen3.5-0.8B VLM; `model.safetensors` 1,746,937,856 B, SHA-256 `d4551e9f…b5d5348` = HF LFS blob), transformers 5.18.0 native `qwen3_5`, upstream prompt/non-thinking/greedy, upstream 2048-bound resize | 14/14 pages **unsupported** |
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

## 2. X1/X2 not runnable — the measured reason (root cause)

Card bound per pilot page: peak commit ≤ min(8 GiB, **available-RAM ÷ 2**),
measured at each run start. Host: 15.77 GB total RAM, ~1.8–2.3 GB available
across the attempts (desktop applications hold the rest; no W22 task was
running), giving recorded caps of 0.995 GiB (pilot), 0.84 GiB and 1.155 GiB
(subsequent runs) — all recorded in each artifact's run manifest and in the
X1 records' `cap_bytes`.

The minimum possible load peak of the X1 checkpoint is **2 × weight bytes =
3,493,875,712 B ≈ 3.25 GiB** even in checkpoint-native bf16 (mmap'd
safetensors + in-RAM weight copy, before torch runtime or activations). Every
measured cap (0.84–1.16 GiB) is far below that, so no load strategy complies;
the preflight refuses with this arithmetic (`cap_bytes`/`weight_bytes/`
`minimum_peak_bytes` are recorded in every X1 record:
`memory_cap_below_minimum_load_peak`) instead of thrashing the host. Re-running the same replayable tool on a host with more free RAM is
the intended path; nothing in the tool was tuned to "fit".

Consequently: no CER/WER/number metric exists for X1/X2 (all `null` with
per-page reasons — never `0`), no latency/VRAM claims, and the card's
"do not extrapolate lighter/faster from 0.8B" rule is respected.

## 3. R0 baseline results (production current state)

Aggregate over gold-verified pages (macro = mean per-page, micro = pooled
chars; strict CER keeps real char differences; narrow CER is the declared
NFC+whitespace normalization):

| split | pages | macro CER strict | micro CER strict | macro CER narrow | English WER | number recall | number precision |
|-------|-------|------------------|------------------|------------------|-------------|---------------|------------------|
| eval (8+1 degraded) | 9 | 0.1599 | 0.1737 | 0.1250 | 0.300 (n=1) | 0.9219 (gold 118/128) | 0.9833 |
| holdout (5) | 5 | 0.1694 | 0.1732 | 0.1290 | 0.1917 (n=1) | 0.9367 (gold 74/79) | 0.9737 |

English WER covers exactly one page per split (the US-listed earnings-call
document); with a single-page denominator it is indicative, not a
population estimate. Per-page `wer`/`wer_ops` are in comparison.json.

Number identity uses the declared narrow canon: OCR thousands-group spacing
("4, 281, 084") is one token; `392.0¹ → 392.01` stays a wrong number.

Latency: per-page engine seconds in `raw_r0.json` (median 15.6 s, cold max 20.2 s in
the final run; the 62.7 s pilot cold-start included first-launch ONNX session
setup); single concurrency, no deadline violations (limits untouched:
production pixel/deadline bounds as configured). Region diagnostics:
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
- **可进一步接入 (Xiaomi)**: cannot be assessed on this host — no CPU-feasible
  path exists under the card bounds. If ROOT wants the X1 answer, re-run
  `tools/ocr_comparison.run_comparison --arms X1` on a host with ≥4 GB free
  RAM (bf16) or a GPU; the tool, manifest, gold and cache keys are ready for
  that replay and will refuse to silently change any identity axis.
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
- `pilot_r0.json` / `pilot_x1.json` — pilot receipts; `memwatch_r0_receipt.json` — R0 peak-memory instrumented run.
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
