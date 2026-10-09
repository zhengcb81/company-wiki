# MAIN OCR selector handoff

**Engineering: PASS (155 concentrated tests). Product: pending MAIN final real whole-deck node.**

- Branch: `codex/main-ocr-selection-20261009`
- Base: `ea76998cc152317f653f101441de69bcb8aeb4fa`
- Exact runtime/test Git SHA: `a1ac491ecfd7da4aadd664215f3c3ce52179d6c1`
- Original parser branch retained at `238e053e3003045113efc9cc7afb1390657cb9a6`.
- This handoff/evidence is added in a later documentation-only commit; runtime SHA and file hashes are bound in `handoff.json`.

## Changes

1. Generic operating facts now retain specific business/product/segment/operating-metric membership, from/to migration, future reporting definitions, rename and otherwise-unchanged wording. Reasons distinguish scope/reporting changes; no revenue/growth is computed or asserted. New scope facts do not gain the legacy numeric financial-table exemption. Static headings, bare financial figures, definitions and accounting negatives stay empty.
2. Format-neutral OCR groups use actual `coordinate_space=image_pixels`, retaining every original unit, locator, text hash and box. They bind source/page/media/shape/role/language/parser/config/dimensions, require consecutive line indices and aligned overlapping geometry, and stop at sentence/heading/bullet/gap/unreliable boundaries. Max8 members and existing1200-character business window. Completion and neighbors share those safeguards. PDF point groups/body thresholds remain separate.
3. Selector `0.4.2 → 0.5.0`; the existing generation manifest carries the version. A concentrated test proves its generation hash changes. Old dead jobs/requests/origin are not changed or resumed.

## Actual test results

- Original responsibility RED: **24 failed / 17 passed**, 41 cases, 2.35s (`red.txt`).
- Final responsibility file:43 cases; two added actual-port/neighbor compatibility checks are explicitly synthetic.
- Final six focused files: **155 passed**, 0 failed, 1.86s (`focused-green.txt`).
- Ruff check with `--no-cache`:PASS (`lint.txt`).

```powershell
$env:PYTHONPATH=(Join-Path (Get-Location) 'src')
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m pytest tests/unit/test_main_ocr_selection.py tests/unit/test_n6_candidate_recall.py tests/unit/test_n6_candidate_main_boundaries.py tests/unit/test_narrative_english_business_recall.py tests/unit/test_narrative_english_operations.py tests/unit/test_narrative_selection_architecture.py -q -p no:cacheprovider
```

No installs, supplier requests, full22-page OCR, main merges or parent plan/config writes. No complete suite/repeated small review node was added. Pure helper serialization is tested inside the existing synthetic port test.

## Real authorized page7 sample — failure retained

Actual command: `python -B docs/implementation/main-ocr-selection/sample_page7.py --main-project C:/Users/郑曾波/Projects/company-wiki`. It ran once against only the archived display-page7 media, within **21.959662700013723s /60s**. The child reached and passed selection/selected-replay assertions, then receipt construction failed on nonexistent `selected.omitted_count`. Full native receipt/counts/spans were **not persisted**. This is **not live PASS**. See immutable `page7_real_receipt.json`, `LIVE_FAILURE.md`, and `page7_sample_closure.json`.

The helper now uses actual `omitted_candidate_count`; only synthetic evidence validated that writer. No extra real OCR was run after consuming the1initial+1selected-replay authorization. Native count/spans remain null; no synthetic or reconstructed replacement is offered.

Supplier/model calls, tokens, cost and unknown-provider usage:0 (local CPU sample invokes no model/provider/AUTO; this is not a fabricated native AUTO ledger). Original archived deck SHA/size/mtime/attributes and production config/MAIN PWF/MAIN script/old AUTO DB before-after identities are exact. Original bytes were opened read-only; the owned copy was readonly, restored and removed only after terminality, with absolute TEMP containment, owner marker, exact three files and no reparse entries. Old failed origin remains for recovery.

## MAIN integration

Integrate the scoped branch/runtime commit normally. MAIN's final single real whole-deck node must prove actual bundle/count/public exact replay. New selector identity creates a fresh generation; do not rewrite or resume old frozen failed work to claim repair. This engineering result does not establish financial meaning, metric comparability, or a product acceptance.
