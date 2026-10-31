# W23-XIAOMI-OCR Independent Review (2026-10-30)

Reviewer: independent review agent (not the author). Scope: full task card
`docs/plans/w23-xiaomi-ocr-2026-10-30/TASK_CARD.md`, branch
`codex/w23-xiaomi-ocr-20261030`, HEAD `fde39dfe`, baseline `de7ffe48`.
Every claim below was re-verified from artifacts, not from the author's notes.
Commands were run with `PYTHONUTF8=1 C:/Miniconda/python.exe` inside the lane
worktree only; no file under review was modified.

## Findings

### 1. Freeze discipline — [OK]

- `git log -- docs/plans/w23-xiaomi-ocr-2026-10-30/{sample_manifest,gold}.json`
  shows exactly one touching commit: `0d24c943` (2026-10-30 20:29:22 +0000),
  before the tool commit `8469df7c` (22:48:27) and the delivery commit
  `fde39dfe` (00:06:08). `git diff 0d24c943 HEAD -- <both files>` is empty
  (blob-identical).
- The freeze commit contains no engine code and no engine output; the delivery
  directory does not exist until `fde39dfe`.
- `freeze_sample.py` imports only hashlib/json/sqlite3/pypdfium2/PIL;
  `build_gold.py` imports only json/pathlib. No OCR engine participates in
  sample or gold construction, so no engine output could have influenced them.
- Manifest contents verified: 7 documents / 14 pages = 8 eval + 5 holdout +
  1 `eval_degraded` (counts block agrees); the degraded page carries
  `degradation.note = "synthetic_degradation,不代表真实扫描覆盖"`. Every
  document has `content_sha256`/`byte_size`/`source_id`; every page has
  `png_sha256`/`png_px`/`png_bytes`.
- Re-hashed all 14 frozen PNGs under `.w23_cache/frozen_pages/`: all match
  `png_sha256` and `png_bytes` (14/14 OK).
- Re-hashed all 7 source PDFs at their storage roots
  (`company_raw` → `C:/Users/郑曾波/Projects/company-wiki/companies/<path>`,
  `dayu_portfolio` → `C:/Users/郑曾波/Projects/dayu-agent/workspace/portfolio/<path>`
  per `render_pages._resolve_physical`): all match `content_sha256` (7/7 OK).
- Hash note: sha256 of the *worktree* gold/manifest files (773692dd…/6c0076d3…,
  as recorded in `comparison.json.run_manifest.inputs`) differs from the git
  blob hashes (b2935740…/a91aa77d…) purely because of CRLF checkout; parsed
  JSON contents are identical, and the run consumed exactly the worktree bytes
  it hashed. No content drift.

### 2. Gold visual spot-check (4 pages across markets) — [OK]

Pages opened as images and compared against `gold.json full_text`:

- `hrjp_cb_prospectus_p006` (CN zh-CN): header, all body paragraphs, condition
  sentences (如果…将…×2), and numbers 2021 / 6,300万片 / 50万件 / 140万支 /
  第2号 all present and faithful; page ends mid-sentence as on the image.
- `ksy_q1_2026_p002` (HK zh): all 25+ numeric tokens verified on the image
  (2,703.7 / 392.0¹ / 37.2% / 351.4 / 7.2% / 27.6% / 11.4個百分點 / 30億 /
  1,970.0 / 2,761.4 / 2.1% / 1,996.3 / 289.4 / 1,353.5 / 47.5% / 1,902.4 /
  4.9% / 707.4 / 102.6 / 616.5 / 14.7% / 859.0 / 17.6% / 90% / 6.8980 / 1.00 /
  3896/KC), footnote text complete, superscript footnote marker correctly
  excluded from `392.0` and documented in `gold.superscript_note`; page
  number 3 at reading-order end.
- `bili_call_4q22_en_p001` (US en): all sentences and numbers (93 million,
  29%, 28%, 26%, 96 minutes, 51%, RMB 21.9 billion, 6.1 billion, 6%, 20%, 18%,
  28%, 30%, 21%, 21%, 26%, 2024) match the image.
- `byd_ar_2024_p022` (table-heavy holdout): both tables transcribed row-major
  with every cell value matching the image (7 vehicle rows + 合计; products
  table with 525,989,680,000.00 / 7,340,435,000.00), checkbox row states in
  `conditions` match the image exactly (☑适用/□不适用, □适用/☑不适用 ×2,
  ☑适用/□不适用).

No number in gold is absent from the image; no visible body text is missing
from gold. Negative controls are real: N0 scores meituan_p011 native layer at
CER 0.7389 vs gold and meituan_p000 as empty_response — confirming the meituan
gold pages could not have been copied from a text layer and must be manual
transcriptions, exactly as `provenance` claims.

Gold blemishes found (see finding 5).

### 3. Metric reproduction — [OK]

- `python -m pytest tests/unit/test_w23_ocr_comparison_metrics.py
  tests/integration/test_w23_ocr_comparison_entry.py -q -p no:cacheprovider`
  → **38 passed** (29 unit + 9 integration), 58s, no network, no model load
  (`test_no_heavy_imports_at_unit_level`, `test_ci_domain_stays_light` pass).
- Independent recompute from `raw_r0.json` + `gold.json` with my own
  Levenshtein and my own number canonicalization (not the repo's aggregation):

  | split | pages | macro CER strict | micro CER strict | numRecall | gold nums |
  |---|---|---|---|---|---|
  | eval | 9 | 0.163579 | 0.176934 | 0.921875 | 128 |
  | holdout | 5 | 0.170505 | 0.174240 | 0.936709 | 79 |

  Matches `comparison.json arms.R0.evaluation` aggregates to <1e-6 on every
  value (threshold was 0.005). `gold` total = 16,387 chars, matching the
  progress note. All 14 raw R0 `text_sha256` re-hashes match their texts; all
  14 statuses `ok`; engine seconds 14.6–51.0s, far under the 180s deadline.
- Determinism evidence: pilot R0 CER on byd_p021 (0.115811…) is identical to
  the full-run value for the same page.

### 4. X1/X2 resource-bound honesty — [OK] (narrative gap in finding 6)

- `raw_x1.json`: 14/14 records `status="unsupported"`,
  `error="memory_cap_below_minimum_load_peak"`, no `text` key anywhere, no CER
  anywhere; `pages_ok=0`, `batch_status="failed"`. `raw_x2.json`: 14/14
  `not_run`. `comparison.json` X1/X2 evaluation aggregates are all `null` with
  per-page `reason_excluded` — never zeros, never fabricated.
- `pilot_x1.json` equally honest (0 ok, failed, all nulls).
- Preflight code (`tools/ocr_comparison/backends/xiaomi_x1.py:145-172`):
  `minimum_peak = weight_bytes × 2`; unsupported when `minimum_peak >
  memory_cap_bytes`, returning cap/weight/minimum-peak arithmetic. It runs
  first inside `run_page` (line 178) and cannot be bypassed from the CLI:
  `run_comparison.py` always computes `memory_cap_gb = min(8, max(0.5,
  avail/2))` and passes it; the only bypass is constructing the class directly
  with `memory_cap_bytes=None`, which the runner never does. A missing
  `model.safetensors` raises `FileNotFoundError` → runner records `error`
  (fail-closed, not silent).
- Arithmetic verified against the actual snapshot:
  `model.safetensors` = **1,746,937,856 B**, sha256
  `d4551e9f6127ac9e35cff7b4f7a72a90410e03e6c8676a36f0e2b7eaeb5d5348` (matches
  comparison.md), snapshot dir is the frozen revision
  `bbd8cf8d21f256b3644b44cb860f3a7cecb93c30`. 2× = 3,493,875,712 B ≈ 3.49 GB
  decimal ≈ 3.25 GiB. Recorded caps: pilot 0.995 GiB, final run 0.84 GiB —
  both far below the minimum load peak, so `unsupported` is correct under
  every recorded measurement.
- Watchdog and deadline handling are honest by construction: commit sampled
  every 0.5s; cap violation reported as `error` even when generation cannot be
  interrupted; `finish_reason=length` → `truncated`; wall-deadline
  StoppingCriteria + post-check → `timeout` with raw output retained.

### 5. Gold blemishes (minor, disclosed here) — [OPEN]

1. **Invisible control characters**: `bili_call_4q22_en_p001` full_text
   contains `under\x02performing` (offset 1989) and `bili_call_4q22_en_p003`
   contains `e\x02commerce` (offset 1959) — U+0002 artifacts of the PDF text
   layer where the image shows a hyphen. Not mentioned in `corrections`.
   Cost: ≤2 chars per page against every glyph-based engine; N0 inherits the
   same chars (slight pro-N0 bias). No numeric effect.
2. **Checkbox glyph inconsistency**: `byd_ar_2024_p022` full_text uses PUA
   `\uf052` for the checked box while its own `corrections` note claims "☑"
   was restored and `byd_ar_2024_p021` uses real U+2611 in full_text.
   Conditions fields are correct everywhere; only the glyph codepoint in
   p022 full_text is inconsistent.
3. **Correction-note wording**: for byd_p021/amec/hrjp pages the note says the
   page-footer number was "moved to reading-order end", but in full_text it
   sits right after the page header (ksy/ir/bili pages do have it at the
   end). Content-fidelity neutral; wording only.

Any fix that edits `full_text` changes `gold_sha256` and strictly requires
re-freeze + re-evaluation (cheap: raw outputs are small and the R0 rerun is
~8 min); alternatively the blemishes can be documented in `gold.json` notes
without touching `full_text`, with `comparison.md` disclosing them.

### 6. Resource-bound narrative vs artifacts — [OPEN]

`comparison.md` §2 and `progress.md` state "1.84 GB available → card cap
0.92 GB" and claim the preflight arithmetic is "入档 pilot_x1.json". The
delivered artifacts record **cap 0.995 GiB (pilot)** and **0.84 GiB (final
run)**, and neither `pilot_x1.json` nor `raw_x1.json` contains the
`cap_bytes`/`weight_bytes`/`minimum_peak_bytes` fields — the runner drops them
(finding 7). The conclusion (≈0.9 GiB cap ≪ 3.25–3.49 GB minimum load peak)
is unaffected and the unsupported verdict is correct under every recorded
measurement, but the specific cited numbers have no artifact backing. Fix:
record preflight fields end-to-end (finding 7) or correct the prose to cite
the recorded caps, and remove the "入档 pilot_x1.json" claim.

### 7. Runner drops backend diagnostic keys (code defect) — [OPEN]

`tools/ocr_comparison/runner.py:41` copies only
`("text", "text_sha256", "raw_output_sha256", "error", "lines")` from backend
results into records. Consequences, verified by reading code and by inspecting
the delivered records (raw_r0.json record keys:
`engine_seconds, inference_runs, lines, page_id, retries, status, text,
text_sha256, wall_seconds`):

- X1's `repetition` flag never reaches `evaluate_page`, so
  `repetition_flagged_pages` is structurally always 0 regardless of actual
  loops. `detect_repetition` exists and is tested, but its output cannot flow
  through the real pipeline (the integration test bypasses `run_pages`, which
  is why its repetition assertion passes).
- R0's `recovery_attempts` and `dropped_regions`, computed by the backend
  (`rapidocr_r0.py:86-90`), are absent from `raw_r0.json` and from
  `comparison.json`, although the card's output contract requires cache/
  recovery counts ("缓存/恢复次数").
- X1 preflight arithmetic (`cap_bytes`, `weight_bytes`, `minimum_peak_bytes`,
  `arithmetic`) is dropped — root cause of finding 6.
- On a warm-cache rerun, `cache_hit=true` set by `cache.ResultCache.get` would
  be dropped from the delivered record (the contract test
  `test_cache_hit_keeps_original_latency_not_zero` locks the cache module
  only, not the pipeline; `engine_seconds` survival does hold through the
  runner).

No numeric result in this delivery is corrupted by this (X1 never generated;
R0 emits no repetition field; all 14 R0 pages genuinely ok; cache was cold
in-run — `run.cache_entries=28` = 14 R0 + 14 X1 keys, zero hits). But the
pipeline cannot honestly report these contract fields until the allowlist is
extended (or records pass through unknown keys). Fix + a pipeline-level test
locking that a flagged repetition reaches `comparison.json`.

### 8. Baseline fairness — [OK]

- `git diff de7ffe48 -- config/local_ocr.json` is empty (production config
  untouched); the full baseline diff contains no modified or deleted files at
  all (see finding 11).
- `rapidocr_r0.py` builds `LocalOCRConfig` from `config/local_ocr.json`
  (identity manifest carries engine 3.8.1 / ORT 1.26.0, det/cls/rec SHAs
  d2a7720d…/e47acedf…/48fc40f2…, text_score 0.5, max_side 3000, 2/1 threads),
  executes inside the production `IsolatedOCRAdapter` boundary
  (`IsolatedOCRAdapter(config, deadline=deadline)` — matches the production
  keyword-only signature) and runs the production `recover_regions(ocr=…,
  image_bytes=…, result=…, limits=…, budget=RecoveryBudget(),
  accept_threshold=config.text_score)` ladder with production defaults
  (4 regions/image, 2 attempts/region, 8/image) — the full production path,
  not a weakened no-recovery variant.
- OCRLimits deadline semantics preserved: R0 passes
  `time.monotonic() + 180` (absolute monotonic, includes isolated-child
  startup), matching `OCRLimits.check_deadline` and the production contract
  ("one absolute deadline includes native startup"). A deadline hit raises
  `NormalizationLimitError` → runner records `error` → excluded, never a pass.

### 9. Cache/runner contracts — [OK]

Locked by tests I ran (all passing) and by code reading:

- Key axes: backend identity (model revision/precision/prompt/preprocess
  variations each change the key), page image sha, prompt sha, params
  (`test_cache_key_separates_backend_identity_axes`,
  `test_page_mismatch_rejected`). R0 uses prompt `"n/a"` honestly (no prompt).
- Cache hit keeps original `engine_seconds` and flags `cache_hit=true`
  (`test_cache_hit_keeps_original_latency_not_zero`); the flag's loss further
  down the runner is finding 7.
- Partial batch reports `partial`, never `ok` (`test_partial_failure_not_batch_pass`).
- timeout/truncated/empty/error/not_run/unsupported never count as pass —
  7-status parametrized test over `counts_as_pass`.
- Retry accounting: fault-injected retry records the extra inference without
  duplicating pages (`test_fault_injected_retry_records_inference_not_duplicate_page`).
- Output cap flags truncation; empty detection; page/render mismatch raises
  in `render_pages` (sha checked against the frozen manifest).

### 10. Card interface conformance — [OK] (summary totals wrong: finding 12)

- `comparison.json` uses `schema_version="cwp-ocr-comparison/1"`, carries
  `sample_manifest_sha256`/`gold_sha256` (matching the consumed worktree
  files), per-arm `backend_identity`, per-page status/error, and NOT_RUN/
  UNSUPPORTED as null + reason (`reason_excluded` in evaluation per_page;
  X1 pages `unsupported`; X2 pages `not_run` with the paddlex/resource
  reason). X1 identity: revision `bbd8cf8d…`, `checkpoint-native-bfloat16-cpu`,
  prompt sha `fd7abd1c…` which I re-derived from the committed
  `PROMPT_DOCUMENT` constant (verbatim upstream prompt) — match. The chat
  template in the frozen upstream snapshot defaults to an empty
  `<think></think>` block when `enable_thinking` is undefined, so the
  "no_think" identity claim is consistent.
- No bbox/confidence fabrication: R0 records carry real word boxes with
  confidences; X1 declares `bbox:null/confidence:null/locator_quality:"none"`
  (`serialize_lines`), locked by `test_null_locator_fields_stay_null`.
- `comparison.md` states **PARTIAL** up front, attributes it to resource
  bounds, and makes no Xiaomi accuracy claim anywhere (checked the full
  document).
- `fact_scores.json` per-judgment notes cite output evidence (e.g. the
  392.01 superscript merge, `- q d o o` fragments, 7o%/5o% o-for-0 errors);
  `pair_facts.py` only pairs texts, never auto-approves.
- `handoff.md/json` correctly absent (they follow this review).

### 11. Production isolation — [OK]

- `git diff de7ffe48..HEAD --diff-filter=M` and `--diff-filter=D` are empty;
  all 64 changed files are additions confined to
  `docs/plans/w23-xiaomi-ocr-2026-10-30/`, `tools/ocr_comparison/`,
  `tests/unit/test_w23_ocr_comparison_metrics.py`,
  `tests/integration/test_w23_ocr_comparison_entry.py`,
  `delivery/w23-xiaomi-ocr/`. No production src/config/deps changes;
  `git diff 0d24c943 HEAD -- config/ pyproject.toml requirements*.txt` empty.
- No literal company names, usernames, or host paths in
  `tools/ocr_comparison/**` or the two test files (grep for
  比亚迪/中微/美团/金山云/万润/华锐/哔哩哔哩/bilibili/byd/meituan/郑曾波/C:\Users :
  the only hit is the sample page id `byd_ar_2024_p021` in the usage
  docstring of `run_comparison.py` and README — runtime identity comes from
  the manifest; docstring-only, cosmetic).
- ROOT worktree `C:/Users/郑曾波/Projects/company-wiki` git status shows only
  other lanes' in-flight files (du11 source-closure src/tests/.planning/.cwp* );
  nothing under the W23-allowed paths, no `.w23_cache` in ROOT.
- Lane worktree status: `M docs/plans/w23-xiaomi-ocr-2026-10-30/progress.md`
  (author's C-phase notes, lane-owned) and `?? .w23_cache/` (declared
  experiment cache, untracked, not gitignored — must not be added at push).

### 12. fact_scores summary totals misstated — [OPEN]

`comparison.md` §3 and `progress.md` claim "eval 36 fact-hits / 4 partial /
1 miss; holdout 35 hit / 3 partial / 2 miss". Summing the delivered
`fact_scores.json` gives **eval 47 hit / 9 partial / 1 miss** and **holdout
35 / 4 / 2**. Additionally, 3 gold facts are unaccounted in the scores:
ksy_q1_2026_p002 (7 scored of 8 gold facts), bili_call_4q22_en_p001 (9/10),
bili_call_4q22_en_p003 (9/10). The per-page judgments themselves cite
evidence and are credible; the headline totals are stale or mis-summed.
Also, `fact_scores.method` cites evidence "under .w23_cache/r0_outputs",
which has been deleted — the evidence survives in `raw_r0.json` texts, but
the citation should point there. Fix: regenerate the totals from
`fact_scores.json`, score or explicitly mark the 3 unaccounted facts, and
update the evidence path.

### 13. comparison.md artifact reference mismatch — [OPEN]

§5 states comparison.json contains a "merged N0 re-run provenance note"; no
such note exists in `comparison.json` (the only "merged" occurrence is inside
the X2 reason string). The final N0 arm is a same-run arm (raw_n0.json written
by the final run at 00:04) and matches the earlier standalone
`comparison_n0.json` (23:30, 12 ok / partial) — the data is consistent, the
described provenance note is simply absent. Fix: add the note or correct §5.

### 14. Cleanup and asset honesty — [OK]

- `.w23_cache/` contains exactly `hub/` (1.7 GB, single model snapshot at the
  frozen revision, untracked — the one allowed asset) and `frozen_pages/`
  (13 MB, declared retained until this review completes, then to be deleted).
- No `w23-ocr-run-*` temp directories in %TEMP%; `render_probe/`,
  `gold_candidates/`, `r0_outputs/` deleted as claimed; run dirs are created
  via `tempfile.mkdtemp` and removed in a `finally` block.
- No lane processes/ports: the runner is synchronous and closes the isolated
  adapter per page.
- Budget: new download 1.77 GB ≤ 6 GiB; persistent 1.7 GB ≤ 8 GiB.

### 15. Counterexample checks (reviewer's own) — [OK]

- Truncated X1 output: `finish_reason="length"` → `truncated` → excluded from
  denominators with `reason_excluded`; output cap crossing → `truncated`;
  blank → `empty_response`. All locked by passing tests.
- Duplicated line: number PRF dedupes (`test_number_recall_duplicates_add_nothing`);
  `detect_repetition` flags repeated lines/cycles — but see finding 7 for the
  pipeline-level drop.
- Page swap: cache key includes the page image sha; `render_pages` raises on
  any sha mismatch vs the frozen manifest, so a swapped page aborts the run.
- R0 empty result on a visible-text page would score CER 1.0 as a scored page
  rather than being excluded — defensible semantics for a real OCR failure
  (crash/timeout paths do raise and are excluded); noted, no action required.
- Missing model file: preflight `stat()` raises → `error` record (fail-closed).
- Forcing a run by raising the cap would be visible: `process_memory_cap_gb`
  is recorded in the run manifest and the cap computation is deterministic
  from the measured snapshot.

## Verdict

**NEEDS_FIXES** — the quantitative core (freeze discipline, gold fidelity,
R0/N0 metrics, resource-bound honesty, baseline fairness, production
isolation, cleanup) independently verified clean, but the following OPEN
items must be fixed and re-reviewed before READY_FOR_ROOT:

1. Finding 7 — runner key allowlist drops `repetition`, `recovery_attempts`,
   `dropped_regions`, preflight arithmetic, `cache_hit`; card-required
   cache/recovery counts cannot reach `comparison.json`. Code fix + pipeline
   test.
2. Finding 6 — record the real cap/preflight arithmetic in artifacts or
   correct the 1.84 GB → 0.92 GB narrative and the "入档 pilot_x1.json" claim.
3. Finding 12 — regenerate fact-score totals (eval 47/9/1, holdout 35/4/2),
   score or mark the 3 unaccounted facts, update the evidence path to
   `raw_r0.json`.
4. Finding 13 — add the claimed N0 provenance note to comparison.json or fix
   comparison.md §5.
5. Finding 5 — document (or fix + re-freeze + re-evaluate) the gold blemishes:
   U+0002 control chars in both bili pages, PUA \uf052 vs ☑ in byd_p022, and
   the "reading-order end" wording for byd/amec/hrjp footer numbers.

— Independent reviewer, 2026-10-30.

---

## Closing re-review (2026-10-31, commit `c62ba969`)

All five OPEN items re-verified against the final code and artifacts; none
remain open.

1. **Runner passthrough — RESOLVED.** `runner.py` now passes every backend
   result key through (only `page_id`/`status`/`engine_seconds` are
   runner-owned). New pipeline test
   `test_runner_preserves_accounting_fields_end_to_end` locks it; 39/39 tests
   pass (30 unit + 9 integration). Delivered records confirm:
   `raw_r0.json` carries `dropped_regions` (8 total) and `recovery_attempts`
   (3 total) per page; every `raw_x1.json` record now carries
   `cap_bytes=1,240,171,806 / weight_bytes=1,746,937,856 /
   minimum_peak_bytes=3,493,875,712` plus the arithmetic string.
2. **Resource narrative — RESOLVED.** comparison.md §2 cites the recorded
   per-run caps (0.995 GiB pilot / 0.84 / 1.155 GiB — verified in the run
   manifests) and the 2 × weight-bytes minimum peak
   (3,493,875,712 B ≈ 3.25 GiB, now correctly GiB-labeled); the "0.92 GB /
   入档 pilot_x1.json" wording is gone.
3. **fact_scores accounting — RESOLVED.** Programmatic check: every gold
   fact/condition is in exactly one bucket on every page (eval 59/59 facts,
   holdout 42/42; conditions 10/10 and 8/8). Totals: facts 83 hit / 15
   partial / 3 miss (eval 48/10/1, holdout 35/5/2); conditions 12 hit /
   6 miss (eval 8/2, holdout 4/4) — match comparison.md and progress.md.
   Evidence path now cites `delivery/w23-xiaomi-ocr/raw_r0.json`; the
   ir_p000 condition entry is now honestly 0/0/0 (gold has no conditions
   there).
4. **§5 provenance — RESOLVED.** comparison.md now states the final
   invocation ran all four arms in-process and explains
   `comparison_n0.json` as the earlier import-bug workaround.
5. **Gold corrections — RESOLVED.** `gold.json` gained a dated
   `post_review_corrections` block; verified programmatically: U+0002 count
   2→0, PUA U+F052 2→0, U+2611 ×4 in byd_p022, six footer numbers
   repositioned to reading-order end (fix script committed for audit).
   `sample_manifest.json` is untouched since the freeze
   (`git diff 0d24c943 HEAD` on it is empty). Ordering is proven by the
   re-run's recorded `gold_sha256` matching the corrected file (run
   00:49:53Z, commit 00:51:49Z). R0 texts are byte-identical between the
   pre- and post-fix runs (verified), so the "engines not re-run" note is
   accurate; the re-run regenerated raw records with the new accounting.

**Independent recompute against the corrected gold** (my own Levenshtein and
number canon, from the re-run `raw_r0.json`): eval macro strict 0.1599 /
micro 0.1737 / narrow macro 0.1250, numRecall 0.9219 / numPrecision 0.9833
(128 gold numbers); holdout macro 0.1694 / micro 0.1732 — all match
`comparison.json` to <1e-6. Final-run latency claim verified (median 15.6 s,
max 20.2 s). Diff `de7ffe48..HEAD` remains additions-only in the allowed
areas; no temp dirs, `.w23_cache` unchanged (hub 1.7 GB + 14 frozen pages);
`handoff.md/json` correctly still absent.

Non-blocking observations for the handoff step:
- progress.md keeps the superseded C-phase entry as history; the dated
  2026-10-31 entry documents the corrections — ROOT should read final
  numbers from comparison.md/comparison.json.
- The final run's manifest records `branch_commit=fde39dfe` (pre-commit HEAD)
  with a dirty worktree, but every `code_file_sha256` matches the `c62ba969`
  files — handoff should record `c62ba969` as the final tested/reviewed
  commit.
- Per the card, `.w23_cache/frozen_pages/` (13 MB) can now be deleted after
  this closing review; keep the hub snapshot.

## Final verdict: **READY_FOR_ROOT** — no remaining [OPEN] items.

---

# Delta Re-Review (2026-10-31) — self-audit commits `ca3bbbcb` / `d45f23e2`

Independent delta reviewer (not the author). Scope: only the five self-audit
fixes added after the closing re-review above. Every claim below was
re-verified first-hand with `PYTHONUTF8=1 C:/Miniconda/python.exe` inside the
lane worktree; no file under review was modified except this appended section.
Where a claim depends on the delivered `raw_r0.json`, note that HEAD's copy
differs from the delivered final-run copy — see D2 — and the final-run copy
(`c62ba969`, texts verified byte-identical to `fde39dfe`) was used.

### D1. English WER reporting — [OK]

- comparison.md §3 aggregate table now carries the English WER column:
  eval `0.300 (n=1)`, holdout `0.1917 (n=1)`, with the explicit caveat
  "English WER covers exactly one page per split … with a single-page
  denominator it is indicative, not a population estimate", and points at the
  per-page values. Per-page `wer`/`wer_ops` exist in
  `comparison.json arms.R0.evaluation` on exactly the two EN pages
  (`bili_call_4q22_en_p001` wer 0.3, ops i26/d77/s17; `bili_call_4q22_en_p003`
  wer 0.19170984…, ops i15/d51/s8; all other pages `None`, never 0).
- Own recompute with `tools.ocr_comparison.metrics.wer` (token-level,
  lowercase, edge-punctuation strip) against `gold.json` `full_text` and the
  delivered R0 texts: p001 120/400 = **0.300**, p003 74/386 =
  **0.191709844…**, operation counts identical to `comparison.json`.

### D2. Per-page identity and raw_r0.json integrity — [OPEN]

- Verified: `page_identity` (source_id / document_id / content_sha256 /
  pdf_page_index / page_image_sha256 / market / language / genre) matches
  `docs/plans/w23-xiaomi-ocr-2026-10-30/sample_manifest.json` exactly for all
  14 pages in `comparison.json` (all four arms, both splits) and in
  `raw_n0/raw_x1/raw_x2.json` (sampled byd_ar_2024_p021,
  bili_call_4q22_en_p003, meituan_ar_2024_p011, then swept all pages: 0
  mismatches). Engine fields of raw_n0/x1/x2 are unchanged vs `c62ba969`
  (additions-only identity join).
- **OPEN:** the delivered 14-page `raw_r0.json` no longer exists at HEAD.
  `run_comparison.py` writes `raw_{arm}.json` derived from `--out`'s
  directory, so the self-audit session's single-page verification re-run
  (byd_ar_2024_p021 only) overwrote it. HEAD's `raw_r0.json` holds 1 record
  from an invocation *later* than the one `comparison.json` records
  (00:49:53Z): engine_seconds 21.74 vs the final run's 19.88, **no
  `page_identity`** (0/1) and no `page_identity_provenance` — contradicting
  the "raw_*.json records now carry page_identity" claim. `comparison.json`
  `arms.R0.raw_output_file`, comparison.md §3/§5 and handoff.json still cite
  `raw_r0.json` as per-page evidence, and §3's latency claim (median 15.6 s /
  cold max 20.2 s) is no longer verifiable from the delivery (I re-verified
  it against `c62ba969`: median 15.6 / max 20.2 — true at delivery time). The
  surviving page's text/lines/dimensions are identical to the final run
  (text sha `20f87913…`).
- Fix (either): restore the `c62ba969` `raw_r0.json` and re-apply the
  identity join, or re-run the full R0 arm once into the delivery dir (texts
  are deterministic — four independent executions verified byte-identical,
  D4) and re-enrich.

### D3. R0 peak-memory receipt — [OPEN]

- `memwatch_r0_receipt.json` (0.183 GB working set / 0.512 GB commit,
  byd_ar_2024_p021) claims "LocalOCRAdapter engine in-process … excludes
  child-process boundary overhead"; comparison.md §5 repeats it as "R0
  peak-memory instrumented run". The committed reproduction script
  (`docs/plans/w23-xiaomi-ocr-2026-10-30/memwatch_r0.py`) instead calls
  `RapidOCRR0.run_page` → production `IsolatedOCRAdapter` → a real native
  child (`subprocess.Popen` + `_worker_main`); the script's
  `K32GetProcessMemoryInfo(GetCurrentProcess())` measures the **parent only**.
- Empirical replication (in-memory, no artifacts written): parent peaks after
  imports 0.049/0.037 GB (matches the receipt's "before"), after the pdfium
  render of the 14 pages **0.183/0.512 GB**, and after the engine call
  **unchanged** — exactly the receipt's numbers. The 0.512 GB commit is the
  pypdfium2 rendering footprint (pypdfium2 import alone ≈ 376 MB commit); the
  OCR engine's memory (in the child) was never measured. "Excludes
  child-process boundary overhead" in fact excludes the entire engine — the
  same three ONNX sessions the receipt's own note says the child holds. The
  number is trivially plausible (well under the card caps and the 15.77 GB
  host RAM) but is not "R0 peak memory with the engine loaded in-process".
- Fix (either): re-measure by constructing `LocalOCRAdapter` directly
  in-process, or relabel the receipt honestly as parent-side
  render/adapter-boundary overhead only, not an engine-peak measurement.

### D4. Coverage-gap declaration and three-run byte-identity — [OK]

- comparison.md §1 declares the missing two-column (双栏) group ("the two-
  column group is not [covered]") and that "no seal/stamp (印章) pages exist
  among the frozen documents", explicitly not filled post-freeze;
  handoff.json `limitations` carries both, plus the single-page WER
  denominator and the once-only memory measurement caveat (its label is D3's
  problem; the disclosure itself is present). The three-run policy note lives
  in handoff.json's reporting-completeness evidence ("R0 texts byte-identical,
  no output selection"); comparison.md itself discloses the N0 re-run but has
  no three-run sentence — acceptable, the claim is in the handoff.
- Claim verified by hashing, not trust: run1 (`fde39dfe`) vs run2
  (`c62ba969`) — all 14 R0 texts byte-identical; run3 (the ca3bbbcb
  single-page re-run, current `raw_r0.json`) — byd_ar_2024_p021 identical
  (sha16 `20f87913338caf8b`); the pilot's `arms.R0.evaluation` `hyp_sha256`
  equals the final run's for the same page; and this review's own in-process
  execution reproduced the identical text (a fourth independent
  confirmation). "No output selection" holds for texts; note the delivered
  `raw_r0.json` is run3's file (D2).

### D5. Temp-cleanup test lock — [OK]

- `tools/ocr_comparison/run_comparison.py` defines `owned_tmp_dir` (context
  manager, `shutil.rmtree(..., ignore_errors=True)` on exit) and `main()`
  executes the entire run inside it. New unit test
  `test_owned_tmp_dir_always_cleans_up` covers both the normal-exit and the
  injected-exception path.
- Re-ran `python -m pytest tests/unit/test_w23_ocr_comparison_metrics.py
  tests/integration/test_w23_ocr_comparison_entry.py -q -p no:cacheprovider`
  → **40 passed** (31 unit + 9 integration) in 43.0 s;
  `delivery/w23-xiaomi-ocr/test_receipt.txt` records 40 passed.

### D6. Consistency — [OK]

- `handoff.json` `final_tested_commit` = `ca3bbbcb`, the commit carrying all
  five self-audit fixes; `d45f23e2` is docs-only (handoff backfill,
  `gen_handoff.py`, removal of the three probe `.ps1` leftovers).
  `final_reviewed_commit` references this delta re-review.
- `code_file_sha256` spot-check 3/3 (`tools/ocr_comparison/run_comparison.py`,
  `tools/ocr_comparison/metrics.py`, `tests/unit/test_w23_ocr_comparison_metrics.py`):
  both raw and CRLF→LF sha256 match the current file contents.
- `git diff --numstat de7ffe48..HEAD`: additions-only (0 deletions on every
  file; no net deleted files — the ca3bbbcb probe `.ps1` additions were
  removed again in `d45f23e2`), all paths inside `delivery/w23-xiaomi-ocr/`,
  `docs/plans/w23-xiaomi-ocr-2026-10-30/`, `tests/*/test_w23_ocr_comparison_*`,
  `tools/ocr_comparison/`; `config/local_ocr.json` and all root/production
  files untouched. Only untracked path: `.w23_cache/` (the declared 1.77 GB
  HF snapshot asset, not committed — as documented).

## Delta verdict: **NEEDS_FIXES** — OPEN: D2 (delivered 14-page `raw_r0.json`
destroyed and replaced by the later 1-page re-run; identity join and final-run
timings lost from the delivery), D3 (memwatch receipt mislabeled: measured
number is the parent-side pdfium render footprint; the engine ran in the
isolated child and its peak was never measured). D1, D4, D5, D6 verified
[OK]. Both fixes are artifact-integrity repairs; no metric result, engine
quality conclusion, or X1/X2 unsupported verdict is affected by them.

---

# Delta Re-Review Round 2 (2026-10-31) — fix commits `c2e5dcf8` / `d8a7991f`

Same independent delta reviewer. Scope: only the two OPEN items from the
round-1 delta review. Everything below re-verified first-hand with
`PYTHONUTF8=1 C:/Miniconda/python.exe`; no file under review was modified
except this appended section.

### D2 (re-check) — clobbered raw_r0.json restored + root cause fixed — [OK]

- `delivery/w23-xiaomi-ocr/raw_r0.json` at HEAD: 14 records again;
  `page_identity` present on 14/14 and **value-identical to
  `sample_manifest.json`** (full sweep, 0 mismatches); engine fields
  (text/lines/engine_seconds/width/height/dropped_regions/recovery_attempts/
  text_sha256) **byte-identical to `c62ba969`** record-by-record
  (identity excluded). `page_identity_provenance` documents the full file
  history honestly: final four-arm run (c62ba969) → identity join →
  accidental one-page overwrite (ca3bbbcb era) → restored from c62ba969 by
  git show and re-joined (delta review OPEN D2).
- `comparison.json` untouched by the fix commits; `arms.R0.raw_output_file`
  = `raw_r0.json` again resolves to the full 14-page evidence file.
- Root cause fixed: `run_comparison.py` now derives per-arm raw filenames via
  `raw_output_path(out_dir, arm)` — UTC stamp + pid + a strictly monotonic
  per-process counter — so two invocations sharing an out dir can no longer
  clobber each other. Locked by new unit test
  `test_raw_output_names_never_collide_across_invocations`.
- Suite re-run: `pytest tests/unit/test_w23_ocr_comparison_metrics.py
  tests/integration/test_w23_ocr_comparison_entry.py -q -p no:cacheprovider`
  → **41 passed** (32 unit + 9 integration) in 45.6 s;
  `test_receipt.txt` updated to 41 passed.

### D3 (re-check) — genuine engine-peak measurement — [OK]

- `memwatch_r0_receipt.json` is now schema `cwp-ocr-memwatch-receipt/2` with
  staged numbers (baseline_import / after_import / after_engine_load / final),
  an explicit `excludes` field (isolated-child boundary overhead; the render
  happened in the parent) and a `supersedes` note naming the mislabeled /1
  and this review's D3 finding. Arithmetic verified:
  720,424,960 B = 0.671 GB WS, 1,060,950,016 B = 0.988 GB commit,
  delta over import 0.95 GB.
- Method is sound this time: the driver renders the page with pdfium in the
  parent, then `memwatch_r0_engine_child.py` runs in a **fresh interpreter**
  that imports only the engine path and runs `LocalOCRAdapter`
  (`load_production_config(config/local_ocr.json)`) — exactly the engine the
  isolated child executes. after_import commit is only ~40 MB, so no pdfium
  pollution; the child's process-lifetime peaks are the engine's.
- **Independent re-measurement by this reviewer** (same driver/child flow,
  own run): final WS 720,433,152 B = **0.671 GB** (receipt: 720,424,960 =
  0.671), commit 1,061,470,208 B = **0.989 GB** (receipt: 1,060,950,016 =
  0.988), delta 0.951 GB, status ok, line_count 49 (= receipt). The number
  reproduces to ~0.1% and is ~2x the previous render-only figure — the engine
  is genuinely inside the measurement now.
- handoff.md and handoff.json now cite 0.671/0.988 GB with the
  fresh-interpreter label. Note (accuracy of the author's claim, not of the
  artifact): **comparison.md §5 was not updated** — it still carries the
  one-line artifact entry "`memwatch_r0_receipt.json` — R0 peak-memory
  instrumented run" without the new values or caveat. That label is no longer
  false (the receipt it names is the honest /2), so nothing dishonest remains
  in comparison.md, but the claim "comparison.md §5 now cites these values"
  did not hold. Non-blocking; the receipt of record and the handoff are
  honest and mutually consistent.
- Stale-wording nit: handoff.json `limitations` still says "R0 peak memory
  measured once in-process … excluding the isolated-child boundary overhead"
  (/1-era wording; omits the render exclusion and the fresh-interpreter
  method). The authoritative receipt is honest; no action required.

### Consistency — [OK]

- `handoff.json` `final_tested_commit` = `c2e5dcf8` (d8a7991f backfilled the
  PENDING_FINAL placeholder; d8a7991f is docs-only: handoff.json +
  gen_handoff.py). `code_file_sha256` updated for both changed code files —
  spot-check 3/3 (`run_comparison.py`, unit test file, `metrics.py`) match
  raw and CRLF→LF hashes.
- All changes in both fix commits are inside the allowed areas
  (delivery/w23-xiaomi-ocr/, docs/plans/w23-xiaomi-ocr-2026-10-30/,
  tools/ocr_comparison/, tests); comparison.json untouched; no production
  file touched. `final_reviewed_commit` still names ca3bbbcb only (round 1);
  this section documents the round-2 review of c2e5dcf8/d8a7991f.

## Delta round-2 verdict: **READY_FOR_ROOT** — no remaining [OPEN] items.
Both round-1 OPEN items are fixed and independently verified (D2 restored +
clobber-proof; D3 genuinely measured and reproduced to ~0.1%); noted nits
(comparison.md §5 one-liner not refreshed, stale limitations wording) are
non-blocking documentation polish.

# Delta Re-Review: X1 execution (2026-10-31)

Scope: commits `845972fc..7980261b` only — the first real execution of the
Xiaomi X1 arm (previously declared unsupported). Everything below was verified
by the reviewer directly (hashing both weight files, parsing safetensors
headers, tensor-level equality, recomputing aggregates from `raw_x1.json`
against `gold.json`, re-running the test suites); author claims were not taken
on trust. Environment: `PYTHONUTF8=1`, `C:/Miniconda/python.exe`,
`sys.path.insert(0,'.')` from the worktree root.

### X1. Exact-upcast honesty (fp32 widening is lossless) — [OK]

- Both files exist under `.w23_cache/hub/models--xiaomi-research--Xiaomi-OCR-0/
  snapshots/bbd8cf8d21f256b3644b44cb860f3a7cecb93c30/` at exactly the claimed
  sizes: `model.safetensors` 1,746,937,856 B, `model.fp32.safetensors`
  3,493,815,312 B.
- Reviewer-recomputed SHA-256: bf16
  `d4551e9f6127ac9e35cff7b4f7a72a90410e03e6c8676a36f0e2b7eaeb5d5348` (matches
  the recorded frozen-checkpoint hash); fp32
  `ddd3b66173fe4dad520a10d23b3ce287bac84691b28e7cd6c261d15c09dcc71f` (matches
  `x1_feasibility_measured.json` v3, `handoff.json` `cleanup_and_assets`, and
  comparison.md).
- Headers parsed with `tools.ocr_comparison.mmap_loader.parse_safetensors_header`:
  both files carry the identical 488-key set; bf16 file is all-BF16, fp32 file
  all-F32; every shape identical; every fp32 byte span is exactly 2x the bf16
  span; fp32 data offsets are non-overlapping and end exactly at the file size.
- Tensor equality via the module's own read-only mapped storages: 9 keys
  spanning small (32-B `linear_attn.A_log`, `dt_bias`), visual
  (`blocks.0.attn.proj.bias`, `qkv.bias`, 18.9-MB `merger.linear_fc1.weight`),
  mid language (`layers.20.linear_attn.in_proj_b.weight`), mtp (`mtp.fc.weight`
  4.2 MB, `mtp.pre_fc_norm_hidden.weight`), and the largest tensor
  `model.language_model.embed_tokens.weight` (508,559,360 bf16 bytes): all nine
  `torch.equal(bf16.to(torch.float32), fp32)` — TRUE. The widening is exactly
  the conversion `make_fp32_copy.py` performs. Losslessness confirmed.

### X2. Card-bound compliance of the three executed runs — [OK]

- Cap arithmetic recomputed from each receipt's own `host_before`: pilot f32
  avail 8,365,486,080 -> cap 4,182,743,040 B (3.895 GiB) exact; full f32 avail
  8,298,373,120 -> cap 4,149,186,560 B (3.864 GiB) exact; bf16 attempt avail
  8,064,327,680 -> cap 4,032,163,840 B (3.755 GiB) exact. All equal
  min(8 GiB, avail/2); rule lives in `job_limit.card_memory_cap_bytes`.
- Job peaks 2.582 / 2.812 / 2.321 GiB — all under their caps.
- Single concurrency: one `subprocess.Popen` per run (`run_x1.py`), receipts
  each show exactly one `child_ready` and one `child_done`, `return_code` 0,
  `backstop_hit` false; pages run sequentially inside the child.
- Pilot: `deadline_seconds_per_request` 180 s in receipt config; the ok page
  took 68.9995 s. Full batch: per-request deadline 600 s, max observed 234.4 s.
- 14th page honestly not_run: receipt record is `{status: not_run, error:
  total_inference_budget_exhausted}` with no text/raw_output fields;
  `raw_x1.json` and the comparison holdout entry (`reason_excluded: not_run`,
  no metrics) never zero-fill it.
- Budget accounting (see X7 for the wording nit): sum of the 13 ok pages'
  `request_seconds` = 1801.5966 s; the child's `child_done` event independently
  records 1801.5966 s. Enforcement is dispatch-time (`spent >= budget` ->
  not_run), so the last in-flight page completed after the nominal 1800 s.

### X3. No silent bound changes; Job Object enforcement real — [OK]

- `git diff ca3bbbcb..HEAD -- config/ src/ requirements.txt pyproject.toml`
  is EMPTY. Every path changed in the range lives under `tools/ocr_comparison/`,
  `tests/`, `delivery/w23-xiaomi-ocr/`, or `docs/plans/w23-xiaomi-ocr-2026-10-30/`.
- `run_x1.py` assigns the child to a Windows Job Object with
  `JOB_OBJECT_LIMIT_PROCESS_MEMORY` (`job_limit.JobMemoryLimit`), limit =
  `min(8 GiB, avail/2)` at run start; the peak is read back from the OS.
- `tests/unit/test_w23_ocr_comparison_metrics.py::test_job_memory_limit_is_enforced_on_child_commit`
  exists (spawns a child that tries to commit 300 MiB under a 120 MiB job limit
  and asserts the OS refuses). Reviewer re-ran the suites:
  `47 passed` (unit + integration), matching `test_receipt.txt`.

### X4. Metric honesty (aggregate recomputed from raw records) — [OK]

Recomputed with `tools.ocr_comparison.compare.evaluate_split` over the 13
`arm=X1F, status=ok` records of `raw_x1.json` against the frozen `gold.json`;
matches `comparison.json arms.X1.evaluation.eval.aggregate` to the last digit:
macro_cer_strict 0.08603821432538125, micro 0.07341772151898734,
macro_cer_narrow 0.03761177921599788, macro_wer 0.1025, number_recall
0.7265625; digit-present recall mean 0.886988936988937 (9 eval pages). The
holdout aggregate (4 scored pages) also matches exactly (0.1158 / 0.0899 /
0.0400). All 13 ok records carry `finish_reason: "stop"` (EOS) — no partial
output presented as complete. The bf16 attempt is scored separately under
`upstream_bf16_attempt_evaluation` (timeout, CER 0.6761) and is NOT merged:
byd_ar_2024_p021 inside X1F scores 0.0617 from the X1F output.

### X5. Fact-score spot checks — [OK]

- (a) byd_ar_2024_p021: raw text contains the exact line `☑适用 □不适用` — the
  checkbox condition is genuinely read correctly.
- (b) ksy_q1_2026_p002: text contains `392.0` and does NOT contain `392.01`
  (the superscript footnote `¹` stays a footnote; no digit merge).
- (c) meituan_ar_2024_p000: the 49-token output contains none of
  `年度報告` / `年度报告` / `2024` — the year-art miss is honestly recorded, not
  silently repaired.

### X6. Freeze integrity untouched — [OK]

- `git diff 0d24c943 HEAD -- docs/plans/w23-xiaomi-ocr-2026-10-30/sample_manifest.json`
  is empty.
- `git diff c62ba969 HEAD -- docs/plans/w23-xiaomi-ocr-2026-10-30/gold.json`
  is empty (only the already-reviewed post_review_corrections state remains).

### X7. Batch budget wording overstates the arithmetic — [OPEN]

The measured batch total is 1801.5966 s of request time (reviewer-summed from
the ok pages; the receipt's `total_request_seconds` agrees). Enforcement is
honest — the budget is checked before each dispatch, the last in-flight page
was allowed to complete, no page started after exhaustion, and the 14th page is
not_run — and the machine records disclose the number
(`comparison.json` `summary.budget = {1800, spent 1801.6}`). But four prose
statements present it as within budget: progress.md `请求时间 1801.6 s ≤ 1800 s
卡预算` (literally false), comparison.md §2 and handoff.md `1801.6 s of request
time under the 1800 s card budget`, and handoff.json `status_reason` `inside
the 30-minute card budget`. Fix: reword to state the +1.6 s (+0.09%) in-flight
completion explicitly. Documentation-only; no re-run needed.

### X8. Handoff pinning incomplete for the new enforcement code — [OPEN]

`handoff.json` `code_file_sha256` (15 entries) omits the five files added by
the execution commit — `run_x1.py`, `x1_child.py`, `job_limit.py`,
`mmap_loader.py`, `make_fp32_copy.py` — because `gen_handoff.py`'s `CODE_FILES`
list was not extended. The handoff's own pinning mechanism therefore does not
cover exactly the code that implements and enforces the card bound
(`xiaomi_x1.py` and both test files are hashed and match disk, verified).
Related nit: the X1F identity string says "sha256 of that file recorded by the
loader", but neither the loader's `weights_load_info` in the receipts nor
`raw_x1.json`/`comparison.json` machine manifests carries the fp32 sha (it is
recorded — and reviewer-verified correct — in x1_feasibility_measured.json v3,
handoff.json, comparison.md). Extend CODE_FILES (and ideally have the loader
record the sha or fix the sentence), regenerate the handoff.

### X9. handoff.md header stale after the X1 commits — [OPEN]

handoff.md line 4 still says "final tested & reviewed commit: c62ba969" and
"What ROOT receives" still counts "41 tests (32 unit + 9 integration)", while
handoff.json records `final_tested_commit`/`final_reviewed_commit` = a2288b4c
and `test_receipt.txt` shows 47 passed. The results paragraph was updated but
the header was not; handoff.md is internally inconsistent until refreshed.

### X10. Declared-variant labeling; no hidden success claims — [OK]

comparison.md §2 declares X1F as a load/compute variant (exact fp32 upcast,
read-only mapping, manual greedy decode with explicit cache — the loop with
`use_cache=True`/`past_key_values`/`logits_to_keep=1` exists in
`backends/xiaomi_x1.py`), lists the five measured root causes, and explicitly
states it is NOT the upstream bf16 runtime and never a GPU-leaderboard
reproduction (also handoff.json `status_reason`, feasibility v3). The bf16
timeout (600 s deadline, 242 partial tokens, peak 2.321 GiB) is disclosed in
every artifact including progress.md; no text anywhere claims the upstream bf16
runtime executed successfully. The fp32 asset is declared in
`cleanup_and_assets` with sha and the 5.27 GB ≤ 8 GB total.

## Delta re-review verdict: **NEEDS_FIXES**

All substantive execution claims verified true by direct measurement: the
fp32 widening is bit-exact (hashes + 9-tensor `torch.equal` incl. the 508-MB
embedding), the three runs obeyed `min(8 GiB, avail/2)` Job-Object caps with
honest not_run/timeout records, aggregates reproduce to the last digit from
raw records, freezes are untouched, and the variant/timeout labeling is
truthful. The three OPEN items (X7 budget wording `1801.6 ≤ 1800` is false as
written; X8 handoff `code_file_sha256` missing the five new enforcement files;
X9 stale handoff.md header) are documentation/provenance fixes only — no
re-execution required.

# X1 delta re-verification of fix commit `1071b743` (2026-10-31)

Reviewer re-checked only the three fix claims against the worktree at HEAD =
`1071b743` (worktree clean except untracked `.w23_cache/`; worktree handoff.md
byte-identical to the committed version). Drift check first: `git diff
a2288b4c..1071b743` touches exactly `delivery/w23-xiaomi-ocr/{comparison.md,
handoff.md, handoff.json, review_independent.md}` and `docs/plans/
w23-xiaomi-ocr-2026-10-30/{gen_handoff.py, progress.md}`; the review_independent.md
change is additions-only (this reviewer's X1 section committed verbatim, verdict
line intact). No other drift.

### X7 (budget arithmetic wording) — fixed in all five named spots — [OK]

Every flagged statement now reads "1801.6 s of request time against the 1800 s
card budget" with the +0.09% in-flight overshoot disclosed, and the
"enforcement fires at dispatch / last in-flight page allowed to finish"
mechanism stated: comparison.md §2, handoff.md results paragraph, handoff.json
`status_reason`, handoff.json B-X1 `evidence` (via gen_handoff.py), and
progress.md (`对 1800 s 卡预算超出 0.09%…如实披露`). Verified by reading each
file at HEAD. Residual note: two same-class spots the original finding did not
list still carry the old framing — comparison.md §1 summary line 10 ("13/14
pages with EOS **inside the card budget**", now contradicting §2 two paragraphs
below) and x1_feasibility_measured.json v3 ("1801.6 s of request time **under
the 1800 s budget** + backstop", backstop-qualified and therefore arguably a
statement about the enforcement envelope). The claim "no ≤/under-budget claim
remains" does not hold for these two; one-line edits each.

### X8 (code file list + identity wording) — half fixed — [OPEN]

- List part VERIFIED: `gen_handoff.py` `CODE_FILES` extended by exactly the
  five files; `handoff.json` `code_file_sha256` now has 20 entries and the
  reviewer re-hashed all 20 against disk — 20/20 match, including
  `run_x1.py`, `x1_child.py`, `job_limit.py`, `mmap_loader.py`,
  `make_fp32_copy.py`.
- Wording part NOT DONE: the string "sha256 of that file recorded by the
  loader" still exists in `tools/ocr_comparison/backends/xiaomi_x1.py` (the
  identity builder — every future run regenerates it), in the delivered
  `comparison.json` (line 1190), and in all five x1 f32 receipt JSONs. No file
  containing the phrase was touched by the fix commit (`handoff.json` never
  carried it). The claim that the loose wording "was removed" is false.

### X9 (handoff.md header) — NOT done — [OPEN]

handoff.md at HEAD still reads "final tested & reviewed commit: **c62ba969**
(implementation 0d24c943 → 8469df7c → fde39dfe → c62ba969)" (line 4) and "41
tests (32 unit + 9 integration)" (line 9); no torch-import caveat exists
anywhere. The fix commit's handoff.md diff touches only the results paragraph
(budget wording). The claim that the header "now" names a2288b4c with 47 tests
(38 unit + 9 integration) is false. For reference the correct values are:
final tested commit a2288b4c (fixes are docs-only through 1071b743), 38 unit +
9 integration = 47 passed (reviewer-run and `test_receipt.txt` agree); handoff.json
line 133's "41/41" is a round-1 historical record and acceptable as history, but
handoff.md line 9 is a present-tense claim about the deliverable and is wrong.

## Re-verification verdict: **NEEDS_FIXES**

X7 is genuinely fixed (residual two spots noted above, same one-line class).
X8's list part is genuinely fixed and fully hash-verified, but its wording part
and all of X9 were not implemented despite being reported as done. Remaining
work is exactly: (1) edit comparison.md line 10 and x1_feasibility_measured.json
v3 to the "against (+0.09%)" phrasing, (2) actually remove the loader-sha
wording from `backends/xiaomi_x1.py` and regenerate comparison.json or annotate
the recorded manifests, (3) update handoff.md lines 4 and 9 (and optionally
handoff.json review evidence) to a2288b4c / 47 tests with the torch caveat. No
re-execution of any run is required.
