# Parser-version CI fixture addendum

**PASS, 0 OPEN for these three fixture corrections.** Reviewed final source diff at HEAD `1e4e9eb51804cd1857ad73245880320efa6171d8` and the root's 4-module final log: **113 passed in 4.15 seconds**. No redundant independent rerun was performed, as requested.

1. English TXT recall tests deliberately retain the old line layout, paragraph 1 and exact locators. Explicit legacy TXT 0.1.1 is the correct owner pin; using the current PDF constant was a fixture coupling. The legacy 0.1.0 replay comparison remains, and synthetic PDF units still use the current PDF constant.
2. Verify-handler fixture metadata now uses actual parsed-unit parser name/version, preserving current transcript 0.4.0 and current PDF 0.1.2 independently. These deterministic fixture inputs have units, including skipped-policy PDF; no production acceptance rule or parser version support changed.
3. The old raw-manifest test checks a legacy wire shape constructed now, not a persisted/frozen producer recipe. Its raw JSON-mime, filing-class fixture has no explicit parser recipe and takes the current fallback 0.1.2. The new comment explains this distinction; canonical object equality and all other fields remain exact. No false TXT 0.1.2 support was added.

Adding the three concrete failing representative nodes to the existing CI regression inventory is within the migration's impact closure. Select nodes that actually traverse these three causes, preserve original parameterized coverage and use the existing mechanism; a new full-module/full-repository gate is unnecessary. This recommendation does not certify the not-yet-reviewed inventory diff.

- `tests/unit/test_narrative_english_business_recall.py` — raw `338cd02c72b3ba4084b6221bb34a6bb7e4915e6ea8787836fe164016c4eb8443`; LF `338cd02c72b3ba4084b6221bb34a6bb7e4915e6ea8787836fe164016c4eb8443`.
- `tests/unit/test_narrative_verify_handler.py` — raw `5955ee5b49e0c8ef3f47b4efa5427b768845a912c47e574e9b4cc7e309d6a3e4`; LF `5955ee5b49e0c8ef3f47b4efa5427b768845a912c47e574e9b4cc7e309d6a3e4`.
- `tests/unit/test_official_json_projection_generation.py` — raw `63d39a1be7c3b455fdf6ad802b90706d85a481f72e2ce312ec5c3fe8fb54cbb8`; LF `232c802b895996731399747bebed1cf3a1d9b71d16973df56fcff20ed3f10c70`.

This is fixture engineering proof, not final remote-CI/full-suite green, summary adoption or RF acceptance. The consumer-mode experiment remains explicitly SUPERSEDED and withdrawn; its original evidence is preserved. No product edits, original PDF reads, FF/RF invocations, SDK/model calls or downloads were performed by this reviewer.
