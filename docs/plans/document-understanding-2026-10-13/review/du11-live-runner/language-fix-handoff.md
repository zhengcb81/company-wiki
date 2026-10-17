# ROOT C source preparation boundary correction

Status: implementation frozen, focused tests green; ROOT will independently review alongside the source-owner facts projection fix. No commit or push by this agent.

## Change

`phase_c_readonly_source.py` keeps source-owner `query_local` issuer/kind/period/as-of matching, unique SourceRef, requested SHA and actual `open_version`. Its former exact-manifest loop now returns `descriptor_diagnostics` instead of denying accepted sources. Actual owner manifest is preserved; descriptor date/URL/language never overwrite it. No new language normalizer, source facts registration, identity database or provider is added.

New tests use owned synthetic originals and sidecars, actual scan/register/query/open and formal `_current_sources`. Existing acquisition metadata language `en-US`, `en`, `null`, `zh-CN` correctly produces source-owner `en`/`zh`; differing descriptor URL/date are diagnostics. Wrong company, market, security ID, fiscal year, fiscal period, document kind and pre-publication as-of remain refused.

## Evidence

- `language-red-corrected.json`: 4/4 real behavioral RED before implementation, 13.88s.
- `language-final-test-receipt.json` + `language-final-junit.xml`: 11 PASS / 0 FAIL / 0 SKIP, 29.12s pytest; 34.82s process. Source SHA before/after equal. Temp root and pytest relocated root removed.
- `language-fix-handoff.json`: exact two-file freeze, baseline HEAD and mother ledger SHA. Ruff check PASS.
- The first RED fixture tried locale tags through new official imports, which intentionally accept worker language families only. It failed earlier at fixture creation for locale cases. Kept `language-red.json`; corrected the synthetic legacy sidecar before the behavioral RED. No real sidecar changed.

## Limits / next ROOT action

This is source preparation software verification, not paid summary quality acceptance. ROOT will combine independent review with its existing source-owner facts/entity projection correction and then rerun real three-source C preflight. HK fact registration is deliberately absent from the helper. Its actual Temp facts demonstration exposed `describe_version` / `query_local` inconsistency, reported separately in `.planning/shared-reading-production/du11/source-preflight-review.md/json`.

No external API/model/network call or key read. Original documents, real sidecars, production DB/config, frozen metadata, and mother ledger unchanged. Mother cumulative 599590 tokens / 385113 microUSD, historical unknown7 retained. No long loopback or large suite repeated.
