# P3 Public Catalog Ports and Long-Path Fix

Date: 2026-11-10 UTC

## Scope

This is one local implementation node under the open P3 architecture work. It does not complete project-wide modularity or the remaining summary/cache/RF audit loop.

- Move catalog-owned source-location ranking out of SourceVersionReader's direct private SourceCatalog._annotate_locations calls.
- Move public document browse SQL and catalog metadata-field paths out of PublicDocumentBrowser and into SourceCatalog.
- Preserve the pathless browse wire DTO. Keep the path-bearing RankedSourceLocation confined to the CWP internal reader port.
- Make Windows lock-file operations work when configured/temporary roots exceed legacy MAX_PATH, including the real catalog operation lock lifecycle.
- Preserve the browse API's prior regex-shaped date projection behavior.

## TDD and root causes

- Three new AST boundary tests initially failed on private catalog annotation, direct browser SQL, and missing catalog owner ports. The source owners now provide ranked-location and typed pathless browse/version identity ports.
- A real pytest temp path reached exactly 260 characters at the acquisition lock file. The containing directory existed, but ordinary Windows os.open returned FileNotFoundError. The common file-mutex owner now exposes win32_filesystem_path, using UTF-16 units and supporting drive and UNC paths. The same adapter is used for CatalogOperationLock path operations and acquisition lock-directory creation.
- The first catalog-owned date projection rejected regex-shaped but calendar-invalid historical values. A RED compatibility test captured the old wire behavior; projection was restored to its previous YYYY-MM-DD shape check.
- The old Windows CIM test depended on the host's WMI service being available. It failed in this sandbox because the optional lookup returned no time. It now deterministically tests command construction and timestamp parsing with a mocked subprocess; production behavior still treats unavailable CIM as unavailable identity evidence.
- The verified FilingReuseObservation.admitted_copy retained the fields consumed by the resolver (source_id, candidate_rank, manifest_json, location, and verified digest). Independent review confirmed the current resolver call also provides its verified_ref.

## Verification

Final targeted command:

python -m pytest tests/unit/test_file_mutex.py tests/contract/test_source_catalog_operation_lock.py tests/contract/test_layer_public_boundaries.py tests/contract/test_public_document_browser.py tests/contract/test_source_reader_public_port_boundaries.py tests/contract/test_source_acquisition_verified_reuse.py tests/contract/test_source_catalog_canonical_writer.py -q

Result: 130 passed.

- Ruff on all changed Python files: passed.
- mypy on source_catalog, _file_mutex.py, and file_mutex.py: 235 source files, no issues.
- Independent read-only review: PASS; no blocking issue. Reviewer did not run tests. It confirmed pathless browse output, current resolver field use, long-path operation-lock lifecycle coverage, UTF-16 threshold handling, and UNC conversion.

## Remaining P3 work

SourceVersionReader still imports private budget, byte-verification, and metadata helpers from resolver.py and policy.py. Public streaming and parser ports remain unfinished. The historical stream/canonical branch candidate is not current mainline code; replay its claimed gaps against current main before adopting it.
