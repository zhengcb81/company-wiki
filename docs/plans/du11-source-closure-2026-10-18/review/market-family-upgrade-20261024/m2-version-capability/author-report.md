# M2 normalization version capability — author handoff

## Result

Implemented the shared root-cause fix within the three owned files. Production compute-worker `create_runtime` now accepts a supported DOCX 1.2.0 pin and constructs the actual normalization port. Unknown versions are still refused at construction; MIME-specific identity still refuses DOCX 2.0, PPTX 1.2 and HTML 1.2. OCR requirements are unchanged.

## TDD and evidence

- RED: 6 failed / 11 passed (`red.xml`), including the actual factory constructor failure.
- First GREEN: 17 / 17 (`first-green.xml`).
- Final owned + adjacent factory/OCR composition: 58 / 58 (`green.xml`).
- Broader diagnostic attempt: 64 passed / 2 failed (`related-attempt.xml`); these failures are retained and reported below, not renamed as green.
- Ruff check, Ruff formatting (3 files), mypy (2 source files) and `git diff --check` passed.

## Shared design

`document_normalization.units.supported_parser_versions(format_name=None)` is the owner capability query. Its immutable registry is also used by `require_parser_version`. Initial document pins use the union because MIME is not available yet; `identity()` applies the format-specific constraint when MIME is known. The historical base-version fallback for non-specialized format names is preserved. No second list of supported versions remains in `NarrativeNormalization`.

## What the new tests actually prove

Generated original DOCX bytes are parsed by the actual parser at historical 1.0, 1.1 and current 1.2 versions. The production worker factory consumes serialized runtime options, then the captured real normalization port parses the source. Its current anonymous-speaker continuation remains unknown-role source evidence. A second actual factory construction receives the same frozen options; JSON-roundtripped EvidenceSpans replay against original bytes, stable unit IDs are retained, empty selection replay works, and altered source bytes are refused. No model client or budgeted model caller can be constructed in this test.

This is runtime factory/normalization recovery. It does not claim a crashed OS worker, DOCX catalog registration, complete batch job execution, formal summary or cache publication acceptance. The reusable run fixture has an isolated TXT catalog/run and the DOCX enters the real captured port directly.

## Broader diagnostics ROOT must retain

1. The tiny PPTX public CLI fixture failed before production work because a sandbox Temp marker was not writable.
2. The DOCX public-history integration failed in its old 1.0 producer model stage with one unknown synthetic-loopback reservation; the fixture deleted its catalog/logs on exit, so the exact caller/transport reason is unproved. Independently, this integration still hard-codes current parser == 1.1.0 and needs an owned contract update to 1.2.0. Neither test is claimed passed.

The public-history fixture is local synthetic HTTP only. No external provider, download, API credential or paid model was used.

## Freeze and cleanup

All source and receipt SHA-256 bindings are in `author-report.json`. The pre-format RED test byte hash was not captured; formatting after RED did not change test semantics. Four task-owned repository temp directories were removed after checked absolute-path containment; the two platform-created failure temp paths were absent on final check (`cleanup.json`). No originals, production configuration, gold, PWF, commits or Git index were changed.

## Files


- `src/company_wiki/document_normalization/units.py` — `a65813c07427c50c4a8d618e58bbf16d400519e7f8c4d190946815f94b9162c5`
- `src/company_wiki/source_catalog/narrative_normalization.py` — `97eca82a8472c167b7b1cd065eae154dca2e7019b77649ccc748e8fadfbb627a`
- `tests/unit/document_understanding_root/test_normalization_version_capability.py` — `596cb0736ab8367a153d462526f6cb33ec3b05973f1a206f0c14eb958f284860`
