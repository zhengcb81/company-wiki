# Historical artifact fixtures

These modules construct small old-format catalogs for reader, source-binding,
failure-recovery and storage-retirement tests. They are not installed by
setuptools, have no CLI, and must not be imported by `src`, `scripts` or `tools`.
Always pass a catalog created inside the test's temporary directory. Never use
these helpers to process company documents or restore a production writer.

The raw format parser remains in `company_wiki.source_catalog.normalizer`.
The fixture normalizer calls that same parser; there is no second parser copy.
Generator names and artifact bytes remain historical compatibility data.

New tests should seed only the old rows/files necessary for their assertion.
Do not add old summarization features here. Existing whole-document producer
assertions can be removed when their reader fixture is replaced with a smaller
seed; the source/hash/locator and deletion invariants must remain covered.
