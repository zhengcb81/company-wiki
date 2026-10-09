# Findings

See MAIN read-only diagnosis handoff. Isolated US catalog contains FY2021–FY2025 annuals; current FY2026 absence is wrongly vetoed by old fiscal-date parser exceptions, then26 provider metadata directories exceeding raw-candidate cap16. Source head titles10-Q are real but cannot be appended through existing facts API; form_type also omitted. Primary publication proof remains missing for CN FY24 and HK H1/overview.

Source reader already allows nullable title; do not add a title permission. Real title enrichment should use observed source text, not request ticker/year. Only verified original scope can exclude a wrong-period candidate; stale provider/filename year is not exclusion proof.

Implementation facts: Windows alias spelling can point at the same real directory (Acme/ACME); discovery deduplicates actual resolved base directories, not company-specific tickers. Nullable title fact maps to source_title and updates SQL display only when non-null; explicit null still overrides capture fallback. form_type already has an assertion SQL column, now included in the existing source-fact vocabulary and actual DocumentType evidence. No database migration or second registry. The current writer and projection publish together; public SourceRef/manifest key/schema versions do not change. Separate finite groups/entries/candidates all consume one current time/byte budget.
