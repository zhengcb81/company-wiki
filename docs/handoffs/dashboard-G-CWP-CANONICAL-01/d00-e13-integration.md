# D00 E13 integration addendum — public canonical browse / exact CN issuer proof

As of: 2026-11-07. This is a current overlay for `G-CWP-CANONICAL-01`; its original 2026-10-30 handoff, frozen `company-wiki-canonical-document-browse/1` response, and `stockwiki.dashboard_issuer_proof/1` input contract remain preserved. This addendum authorizes and records only the narrow CWP-side extension below. It does not change the StockWiki envelope or schema.

## Authority and scope

The user-authorized B-01 implementation scope is recorded in the canonical Dashboard PWF at `.planning/unified-dashboard-2026-10-26/dispatch/B33-B01-IMPLEMENTATION.md`: the CWP author scope permits a CN strong issuer namespace consumer and exact original CN issuer identification; its integration rule requires the owner exact-version reader to verify the registered original bytes and strong issuer facts, without copying originals into Dashboard. This addendum is D00's E13 integration record for that existing authorization, not a new owner-wide reader policy.

The added route is limited to a `cwp_source_export_v2` binding naming an exact indexed source URN with an active, hash-bound verified source-facts assertion, whose exact `SourceRef` resolves to a registered PDF with `market=CN` and document kind `annual_report`, `semi_annual_report`, or `quarterly_report`. The verifier reads only that exact registered version through the existing `SourceVersionReader`; it does not search folders or choose a candidate by title, filename, ticker, or size.

The CN verifier (`cn-primary-uscc/1`) requires the native original PDF itself to establish the company legal name, its own stock-table security ID, and a checksum-valid 18-character USCC in the issuer's own registration passage. It also requires a cache-only exact active CNINFO security record that agrees on market/ticker and the issuer's own abbreviation. Missing, contradictory, ambiguous, encrypted, malformed, or out-of-budget sources remain named unknown/unavailable and do not produce items. Each source version is re-proved and its issuer/source/assertion/hash pin participates in the proof revision, so changed facts stale a prior snapshot.

Budgets and exclusions:

- Per original PDF: at most 16,000,000 bytes, 1,000 pages, and 8,000,000 extracted text characters. Total CN proof reads during one browse: at most 64,000,000 bytes.
- Native PDF text extraction only. No OCR, model, network, download, refresh, write, or mutation of the source catalog or original. Bytes are held in memory for this verifier and are not persisted or copied into Dashboard.
- The CNINFO security record must already exist in the local security-master cache; the route does not fetch it.
- Only the `cn.uscc` verifier is added. No conversion from unsupported namespaces, no general CN/HK issuer mapping, and no CIK/USCC equivalence.

## Current E13 evidence (acceptance is not yet final)

- Owner contract suite: `test_public_canonical_browser.py` + `test_cn_primary_issuer.py`: **64 passed** after current code changes.
- Shared public document browser and default steady source-reader regression: **21 passed**.
- Ruff: changed owner modules/tests clean. Mypy: four changed source modules clean.
- A real public CLI positive was independently observed using the fixed StockWiki proof CLI and the real 中微 ENT/LST: `binding=verified`, exact selected listing, `cn.uscc` / `cn-primary-uscc/1`, 4 exact PDF items. This was an adapter/CLI observation, not a claim that the Dashboard HTTP stream acceptance is complete.
- Dashboard D06 public-CLI → exact reopen → real loopback HTTP stream/range/cancellation acceptance and independent final review are **pending**. D00 will append their immutable evidence references and the final result here after they pass or record a named blocker if they do not.

## Historical statements superseded by this overlay

The original README §3/§5, protocol §4, and verification record describe the 2026-10-30 candidate before the owner authorized the B-01 CN original-proof route and before the real StockWiki proof CLI was available. Their claims that no real SW CLI existed, that CN documents could never enter `items`, and that no CN original was read are historical facts for that candidate only. The route above is the bounded current exception; the original SEC CIK route and all other unsupported-namespace refusals remain unchanged.
