# Findings

- Actual HK baseline: official identity HK/09896, immutable manifest HK/9896. Resolver strips zeros but candidate projection returns9896; strict FF comparison fails despite same security.
- Current resolver's generic lstrip-zero rule must be replaced by a market-qualified strict owner; security_identity._ticker_key is discovery alias matching and intentionally remains separate.
- Canonical public candidate is a projection, not mutation of observed source metadata. Existing source verifier, dates and SHA stay owners.
- Mother CodeGraph structural context confirms SourceResolver._identity_matches and SourceReader.describe_candidate are the two relevant seams. WT index need not be initialized.
- Meaningful RED7 failures cover generic lstrip-zero false positives and real unpadded candidate; no test depends on a new missing import. GREEN42 includes existing source identity and steady-reader contracts.
- Actual unchanged FF HEAD f1a939e consumes the synthetic official-format HK snapshot, performs identify+query (2calls), downloads0, and reuses SourceRef for both source9896/query09896 and source09896/query9896. Actual binary reader returns unchanged SHA/body/observed manifest; a same-size raw tamper returns2 with zero bytes. Socket guards record any attempted network; none occurred.
- Additional current verified fact388→candidate00388 preserves describe_version388, and old9896 cannot be reused. Unknown/future publication stay nonhistorical. Root/company/period/date/SHA responsibilities remain in existing owners.
- Canonical source-code matching is distinct from fuzzy security-master discovery. Market-free ticker alias discovery was not broadened or rewritten.
