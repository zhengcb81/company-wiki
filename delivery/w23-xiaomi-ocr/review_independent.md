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
