# PDF runtime environment v2 handoff

Implemented only the assigned reading-layer sources and new regression tests. No model, interpreter, source, production config, downloader, AUTO/FF/RF consumer or historical runtime file was changed. No commit/push, PDF conversion, network/download or paid call was performed.

## Ownership and identity

- `narrative_pdf_environment.py` owns `pdf-runtime-closure/2`: configured Docling plus non-Python `runtime_versions` roots; selected `importlib.metadata.distribution(name)` metadata; active `Requires-Dist` transitive closure.
- PEP 508 requirements/specifiers/markers/extras use the existing optional deployment's `packaging` package. Extras propagate to a fixed point, including cycles and later activation of earlier nodes. Unused extras do not require installed metadata. Missing active metadata, invalid versions/specifiers and undeclared active extras fail explicitly.
- The resolver does not enumerate installed distributions, deduplicate a global inventory, import SDKs, inspect models or perform network operations. Standard Docling's declared `standard` extra and its `chunking` transitive extra are included because the selected Docling metadata explicitly requires them; other installed extras are not assumed active.
- Selected-distribution precedence is retained: a genuinely selected alternate distribution version changes the fingerprint; a shadow duplicate or unrelated installed package does not.
- The hash includes the algorithm version, explicit roots, interpreter/platform marker environment, selected versions, active extras and active dependency declarations. It is metadata/version binding, not wheel-byte attestation. Active direct URL dependencies fail explicitly because their byte identity cannot be proved from installed metadata alone.

## Version compatibility

- Frozen `pdf-paragraph-runtime/1` remains parsed as the legacy inventory algorithm; `--describe-environment` with no config retains the exact old inventory calculation. V1 cannot claim a v2 algorithm. Existing v1 response and recipe field shape remains unchanged; actual current worker/orchestration source hashes still distinguish changed source.
- New `pdf-paragraph-runtime/2` requires explicit `environment_algorithm: pdf-runtime-closure/2`. Its request/response schema is `/2`, and algorithm response binding is checked. Its recipe adds the algorithm identifier and fingerprint implementation source SHA alongside existing worker/orchestration/alignment, model/config, pinned versions, options and limits.
- The additive CLI is `C:/Miniconda/python.exe -B src/company_wiki/source_catalog/_paragraph_worker.py --describe-environment --runtime-config .planning/c3-20261026/pdf-env/runtime-4g-v2.json`.
- The old runtime JSON is untouched: SHA-256 `d84387132edda4dab3cc43d62a7cd9a93634914977b8da89b42ddb90f3c27a1a`.

## RED and GREEN

- `red.txt`: original implementation, 11 failures for absent v2 API, one pass and one unrelated TEMP fixture setup error. No assertion was removed. The fixture-only problem was removed by avoiding filesystem setup for the configuration parser test; its pure-memory rerun against the original loader is `red-config.txt`: 1 failure because the old schema rejects v2, 12 deselected.
- New final tests cover duplicate discovery/unrelated packages, actual transitive version and metadata changes, marker activation, extras fixed points/cycles, selected version precedence, missing/invalid metadata/specifiers/extras, schema/recipe compatibility and v2 request/response algorithm binding.
- `green.txt`: 37 passed in 3.79s across the new test file, existing paragraph runtime and existing PDF reading integration. The initial default sandbox TEMP was unwritable; final tests used this task's own `tmp` directory, which was removed after verification. No assertions were changed to accommodate the environment.
- `ruff.txt`: all checks passed. `mypy.txt`: no issues in three source files.

## Real lightweight worker reproduction

The existing Conda Python 3.13.9 was run with normal host approval in metadata-only describe mode. `PYTHONPATH=ROOT/src` and `PYTHONPATH=ROOT/src;ROOT/src` returned identical complete environment descriptions (receipts `environment-entry-src.json` and `environment-entry-duplicate-src.json`). No heavy SDK was imported or real candidate processed.

- Environment SHA-256: `c84a984ccb3a56dffbfd0d4538f14ce4a27de44dec4981527a2b0c4a545cdf44`.
- Declared closure: 104 distributions, excludes company-wiki; packaging 25.0 is present through actual declared Docling dependencies, so pyproject needs no addition for this optional path.
- Core unchanged: Docling 2.96.0, core 2.78.0, IBM models 3.13.2, torch 2.12.0, PyMuPDF 1.26.7, pypdfium2 4.30.0, Python 3.13.9.
- New task-local config: `.planning/c3-20261026/pdf-env/runtime-4g-v2.json`, SHA-256 `077654bd7eeb016d57667ec3560e602f4de480a74c2cbb236fc1100dda942fd6`. It differs from the frozen v1 JSON only in schema version, explicit algorithm and environment SHA. Model/config SHAs and all explicitly configured or default resource limits are retained (120 seconds, 3 pages, 4 GiB, 4 threads).

`handoff.json` includes final byte and normalized source SHA-256 values. ROOT owns independent review, the one bounded real content confirmation and all subsequent cache/RF/paid-summary validation. Those content outcomes are not claimed here.
