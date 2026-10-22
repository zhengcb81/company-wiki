# Baseline contract analysis: five existing failures

Status: analysis and authorized narrow remediation completed on product96ca254d; ROOT non-author and cross-layer acceptance pending. This is not comprehensive acceptance of the entire cross-repository feature.

Baseline 1b39032c evidence/baseline-contract.log/xml:22 collected,17P/5F10.29s. Candidate evidence/related.log/xml:49 collected,44P/5F17.96s. Exactly the same nodes fail. No test should be weakened: an unrelated obsolete document must not veto a missing requested filing; a matching cached declaration must still be checked against its real original.

| Failures | Actual root cause | Required behavior |
|---|---|---|
| Wrong2022annual /2026Q1 with unsupported unrelated date | Narrow initial owner already returns not_relevant before dates; discovery broadens request and repeats proof with match_scope=False, so unrelated date completion escapes FiscalMetadataError | Exclude genuinely proven unrelated source before ancillary date processing, no fake publication, no new assertion |
| Cached wrongCIK/year after_discovery | verify_version already calls existing source_scope_qualification and refuses primary_issuer_conflict /primary_scope_conflict. The private fast path does not convert this native error into its structured result | Same owner validation once, named structured blocked result; do not add another verifier |
| Broken meta.json beside actual2022 original | Initial narrow actual proof excludes old year before _sec_cache; broad discovery reopens it and now reads its malformed sidecar, returning blocked local_metadata_unreadable | Irrelevant sidecar must not veto2026 missing request; same malformed sidecar on actual2026 must still block |

Correction to the first quick hypothesis: the after_discovery branch does NOT wrongly return ready for conflicting originals. source_reader.py filing_reuse automatically qualifies the actual body and throws; the defect is inconsistent failure representation outside the guarded writer loop.

Minimal solution: retain an in-memory per-call set only when restore_document_facts returns not_relevant from existing verified original proof; discovery skips those exact document IDs. Discovery proof uses the actual request instead of a broader request; latest already has its actual open period scope. Catch native qualification failure at the fast path and catch semantic owner failures in discovery without suppressing unknown/current target gaps. No filename/declaration/query label may populate the set. No permanent negative cache, permission, source ledger, second hash or new identity check.

Keep old22 assertions; add fresh discovered unrelated versus target/unknown and same-call reread checks. Then run original22 +ROOT9 budget +boundaries/latest/discovery limits and full-src mypy. No provider/download/API/key access.


## Implemented result

Product96ca254d60fe416598e47d108b5f561d2dc48179. Existing22 test assertions unchanged. Owner SourceReadError is converted into the same named result at after_discovery; source_reader remains the sole actual-byte qualifier. A call-local not_relevant_documents set is filled only after restore_document_facts returns not_relevant from verified original proof. Both discovery and recursive main candidate loops consume the set. Unknown scope, guessed names, declared cache years and query labels never populate it. Discovery uses the actual request before dates/cache, and preserves unknown/current semantic failures as structured blocked. Latest open scope and new revisions remain covered by its original5 tests.

TDD: original22 +new6 boundary tests RED10F/18P10.38s (old5 +new5 genuine failures; unknown negative already passed). First correction55P/2F15.03s proved recursion still reread negative originals; the2 call-count assertions were retained and implementation fixed. Final same-source focused57P/14.46s: original22 +new6 +ROOT9 budget +9 existing boundaries +5 latest +6 discovery limits. A subsequent actual2026/import-declared2022 positive was added: the now7-case boundary module7P/2.79s. These overlap and are two commands, not one58-test run. Full-src mypy366 files0errors; Ruff and normal commit hooks pass.

Exact source/test SHA: baseline-contract-evidence/final-source.json. The budget source remains ROOT's byte-exact11d2dd529216d17d982c673b490754b8b199123ae43302047527282c9f8c4550. No provider/API/model/download/key operation. No original modified. Source is frozen; only docs/cleanup follow.

ROOT budget evidence qualification: original evidence/red.xml is valid7-case RED. retention-baseline.xml contains one genuine previous-history-loss RED and one old-version missing-_progress KeyError, which is an interface/setup mismatch and not a second independent business RED. Child default encoding caused a final print UnicodeDecodeError; retention-baseline-restoration.json confirms both sources restored byte-for-byte in finally. retention-copy-invalid.* accidentally reran old7 after a failed relative-path copy: setup-invalid, never counted as9. retention-valid.xml is the valid9P/4.17s run.
