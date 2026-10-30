# pdf_runtime_deployment

Reproducible deployment of the existing offline PDF paragraph-enhancement
runtime to a **real ASCII resource tree**. The pinned docling-parse 6.2.0 C++
layer cannot open its bundled resources from a non-ASCII deployment path on an
ACP=936 Windows host (W21 evidence: canonical Chinese-path env fails at
`PAGE_1 ChildFailed/native_fallback`; a temporary ASCII alias of the same env
completed conversion as a diagnostic). This tool builds the supported,
non-alias remedy.

## What it does

1. `plan` — runs the existing `pdf-runtime-closure/2` resolver inside the
   **source** interpreter (metadata-only probe: no SDK import, no writes),
   enumerates every selected distribution's RECORD entries, hashes each file,
   and freezes an integrity-digested plan. Diagnostics (RECORD provenance
   deviations, active `.pth` hooks) are recorded, never upgraded into gates.
   Blocking errors (missing/escaping record sources, conflicting duplicate
   claims) stop the plan.
2. `deploy` — creates a plain venv (`--without-pip --copies`,
   `include-system-site-packages = false`) at an **ASCII** target on the same
   NTFS volume, hardlinks every planned file (re-hashing each source just
   before linking; `samefile` proof per link; zero SDK/model byte copies),
   hardlinks the model artifacts tree, and emits a
   `pdf-paragraph-runtime/2` config identical to the source profile except the
   ASCII `python`/`artifacts` paths. Targets are classified
   `ABSENT/EMPTY/OWNED_COMPLETE/OWNED_INCOMPLETE/FOREIGN`: complete owned
   deployments are reused with **zero writes**, incomplete owned deployments
   are recovered row-by-row, anything else conflicts and is never modified.
3. `verify` — fresh-process light checks: the deployed interpreter re-resolves
   the closure (digest must match the receipt), proves isolation (no pip, no
   user/base site, all distributions under the deployed site-packages, ASCII
   prefix, zero SDK imports), and the production
   `configured_paragraph_runtime()` loads the emitted config. A tree snapshot
   proves the recheck wrote nothing.
4. `constructor-probe` — explicit opt-in no-document SDK constructor (30 s
   deadline) through the deployed interpreter.
5. Real-entry E2E lives in
   `tests/integration/test_w22_pdf_deployment_entry.py` (opt-in via
   `W22_PDF_DEPLOYMENT_E2E=1` + `W22_PDF_DEPLOYMENT_CONFIG=<config>`), driving
   the production `PdfReading` -> worker -> offline SDK -> existing alignment
   path on a synthetic two-page PDF.

## Usage

```powershell
# Must run under the base interpreter that owns the source env's venv module.
python -m tools.pdf_runtime_deployment plan `
  --source-config <existing runtime config json> `
  --target C:/ascii-owned-target --plan-out plan.local.json
python -m tools.pdf_runtime_deployment deploy --plan plan.local.json
python -m tools.pdf_runtime_deployment verify --config C:/ascii-owned-target/paragraph-runtime.config.json
```

The emitted config stays a `pdf-paragraph-runtime/2` config: consumers select
it with `COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG`; no upper layer learns Python or
SDK paths. Nothing here changes ROOT production profiles, global environment
state, or any source byte; hardlinked sources must never be edited or
re-privileged in place.
