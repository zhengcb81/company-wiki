# DU11 F3 market-qualified source identity projection

PLAN_ID=du11-identity-projection-2026-10-18; PWF_PLAN_ROOT=docs/plans.
Base: a8eef273. Branch codex/du11-identity-projection. ROOT owns integration/push.

## Goal and boundaries

One CWP pure owner canonicalizes strict, market-qualified security codes. Resolver identity equivalence and public candidate identity projection share it. Immutable manifest and verified source facts remain observed bytes/values; no request-driven rewriting, new RPC/store/approval. FF unchanged and readonly. No source narrative, automation, config, schema, CI, hooks, production DB, original or author-worktree edits.

Allowed: source_catalog/security_code.py (new), resolver.py, source_reader.py identity scopes; tests/unit/du11_identity_projection/**; tests/integration/test_du11_identity_projection.py; this plan directory. Any necessary extra runtime file requires ROOT overlap notification first.

## Phases

1. A meaningful RED: HK both directions, CN width, distinct codes/markets, US class punctuation, unknown namespace and observed manifest preservation. Status COMPLETE: 7 meaningful FAIL / 19 PASS, red.log/xml.
2. B implement one pure owner and two call sites; concentrated existing identity/query regressions. Status COMPLETE: 42 PASS/6.76s (green.log/xml), including 16 existing owner tests.
3. C isolated actual FF→CWP identify/query/reuse/open, zero download/provider/model; negative company/market/period/date/hash controls; Temp/sentinel cleanup. Status COMPLETE: 31 PASS/13.43s (integration.log/xml), 29 own unit + 2 real external FF CLI integration cases.
4. Independent different-agent review at frozen SHAs, fix all findings, normal owned-only commit, handoff. Status COMPLETE: independent reviewer PASS,37PASS13.20s; normal implementation commit310252bd, no defects found.

## Next Step

ROOT receives implementation310252bd and this final handoff documentation commit for merge; real HK consumer-only replay remains ROOT responsibility.

## Acceptance

No broad lstrip-zero comparison without market. HK canonical five digits; CN exact supported width, US class symbols preserved; unknown namespaces do not acquire aliases. Public candidates canonical; describe-version/source facts unchanged. Existing source SHA/period/as-of/root qualification retained. Synthetic test state only. No paid calls or network; no broad suite reruns. Author cannot self-sign independent acceptance.

## Errors

Initial test draft expected query_local to expose a public candidates dictionary; source inspection confirmed typed SourceQueryResult.matches. Corrected only the test lookup before GREEN. RED itself failed earlier at the actual canonical-code assertion, not this unreachable fixture error.

Ruff initially flagged pytest's imported fixture/function parameter F811; retained the actual fixture injection and documented the single test-signature suppression, not a runtime or broad lint exclusion. No test behavior changed.
