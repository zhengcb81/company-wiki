# Independent budget-policy TDD: frozen RED

This report freezes tests before ROOT implements the new public budget policy. Only `tests/unit/test_resource_budget_policy.py` was added. No existing test, production source, live ledger/configuration, raw document, provider or Git state was changed.

## Actual run

-63 tests collected,56 failed,7 passed,0 fixture/collection errors;3.53 seconds.
-Production resource_budget.py SHA before/after: `17ef6e5a3ffa87d0527d03e86ec4b325273fb38f275b57600db2dcff406dab1e`.
-Frozen test SHA: `1f7856b22c3e928155d7591148f985f731b7de6cae94af9e6e07a6cde73d25f6`.
-Source remains old: no loader, no factory policy/phase/override arguments, no phase-aware structured exhaustion. Missing API is a genuine product RED, not a fixture bug.
-Exact command, JUnit counts and actual relocated cleanup are in red_receipt.json; full stdout in red.txt, JUnit in red.xml. Requested and effective temp dirs are absent.

## Contract covered

1. Public loader accepts Path/string, returns a frozen dataclass, and does not rewrite its selected temporary YAML.
2. Explicit path wins over environment; selected environment path is independent of cwd; missing/malformed selected environment file cannot silently fall back.
3. Each of5 numeric dimensions accepts0, rejects negative/bool/float/string/null. Wrong schema, missing required number and unsupported hard company enforcement are explicit errors.
4. Company allocation is a soft target: it may exceed the cumulative allowance. LLM token/USD targets remain separate from local document work and do not charge/reset it.
5. New factory loads configured document work, accepts explicit0 or larger-than16M requests, honors phase, and rejects invalid explicit limit types.
6. Direct work limits/charge arguments are actual nonnegative integers, and invalid charges cannot mutate the account.
7. Exhaustion has dimension document_work, actual phase, exact used/requested/limit, without the old blanket layout message.
8. Child rejection is atomic; parent and sibling scopes share one spent account; child exhaustion does not consume unused parent allowance, while mother exhaustion retains the mother actual remaining state.
9. Parse/select pass the same identity and cannot reset what parse already spent.

All policy fixtures are tmp YAML;0 external calls and0 live billing-ledger reads. Schema/default repository-path wiring and real cross-repository mother-budget execution remain ROOT integration responsibilities. No extra manual approval or per-document gate is introduced.

The author will now wait for ROOT's implementation, then review current source and actual execution against these unchanged assertions.
