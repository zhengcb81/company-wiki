# W05-RF-FLOW: independent price-correlation final acceptance

## Verdict

**PASS_WITH_SCOPE. The retained point-stock and price-cancellation P1s are
repaired at the common type owner and all four native boundaries.** No new
blocking defect was found in the bounded independent review. ROOT can proceed
with ordinary publication and integration; this report is not a claim that
real-company facts or economic forecasts have been independently certified.

## Exact freeze and evidence preservation

The accepted engineering freeze is the **30 files / 818,229 bytes** in
`fix/price-correlation/root-product-inventory.json`. Every hash and size matches
before and after this review. In particular, the actual common owner
`scripts/contracts/period_flow.py` has SHA-256
`0c1a47b1f0bca1e729039bac432a273f5122703df2b7a136ac923fa2140800ff`.

The product root remains
`C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root`, declared base
`1b616622763ece6549676f2a74f596e6c65244af`, pending original delivery
`f1a782a478d255b9b4b8f531e7a3961134e257ba`. Earlier inventories and reports remain
historical. This review did not commit, merge, install or push product code.

All eleven files frozen in the preceding `independent-typed-final/manifest.json`
remain byte-identical, including the six exact wrongly accepted input/output
artifacts. The original point-stock failure file is also unchanged. The new
results live only in this new directory and do not overwrite any FAIL evidence.

## Independent execution

**31 bounded synthetic cases pass their expectations**, comprising eight exact
earlier cases, three exact retained price P1 inputs, seven new independent
variants, ten earlier independent formula controls, and three native-model
positive controls. The run records 74 validation/forecast/reader boundary
outcomes for the first 28 cases and eight additional exact old-output reader
outcomes. Execution after imports took **1.199 seconds**.

For the original three price inputs and original point-stock input, all **16
actual boundary calls** now reject with a financial `typed flow` error:

1. `validate_document`;
2. `run_forecast`;
3. `validate_published_forecast`;
4. `validate_forecast_output`.

The three price outputs are the exact original artifacts that formerly passed,
not fabricated substitutes or expected-output snapshots. The point-stock output
is separately forged and rehashed around the exact retained input, so its reader
checks exercise the mathematical contract rather than only hash rejection.
No publication-environment error is counted as a correct business rejection.

Additional independent negative variants reject:

- Same original price retained through a distinct derived alias.
- The equivalent expression `(p + 2*p) / (3*p)` multiplied by a monetary stock.
- An outer coefficient multiplying stock × cancelled price ratio.
- Nested monetary stocks, scalar/rate-only annual aliases, stock-plus-flow,
  true flow cancelled back into stock, stock-derived ARPU, and zero-weight
  supporting anchors from the preceding independent review.

Positive controls remain usable:

- A cancelled price ratio with a coefficient scales **real annual income**.
- Quantity-stock × annual ARPU, income-derived ARPU, and real flow/stock
  turnover yield their expected annual contributions.
- Different existing price dimensions support their legitimate distinct roles
  in the same formula: user-stock × annual unit ARPU plus annual occupied-area
  flow × transaction price.
- An explicitly dated full-year quantity flow × transaction price produces
  recognized income without inventing or changing its interval.
- Income-derived unit ARPU can coexist with a different unit transaction price
  in the same formula; consistent origin is retained rather than all prices
  being rejected.
- Native subscription, asset-management fee and bank-yield models retain their
  ordinary stock roles. Their consolidated numbers exactly match their baseline
  results; validation, forecast and both strong readers pass.

One minimal independent native CLI replay also passes with network calls denied
and a minimal child environment. Its JSON and Markdown are full-byte identical
to the frozen CNY synthetic case, and both strong readers accept the result.
The existing 390-test suite and earlier 3.9 compatibility suite were not rerun.

## Common-root review and practical limits

The implementation uses affine period expressions with shared symbols, retains
them through recursive aliases and actual AST references, and imposes equations
for addition and intermediate annual revenue. Division cancels shared symbols
before interpretation. A complete expression must admit one consistent
assignment; it no longer chooses each occurrence's price meaning independently.
The independent alias and algebraically equivalent probes confirm behavior
beyond a literal `x/x` special case.

Only the three existing price dimensions can introduce ambiguous symbols, so
the interpretation search is at most **eight assignments** regardless of the
number of raw prices or aliases. This bounds interpretation enumeration, not
arbitrary total DAG size, recursion depth or peak memory. No extra solver,
identity registry, authorization, review receipt or test gate was introduced.

Like raw temporal prices of one dimension share a role within a formula DAG.
A generic expression requiring both raw annual ARPU and transaction price of
that same dimension must use actual income-derived ARPU or the existing native
business roles, as the documented contract states. The positive mixed-role
probe verifies the supported flow-derived construction. Free-text rationale
alone cannot distinguish those roles. This is an explicit mathematical scope
limit, not a new human approval requirement.

Period algebra proves mathematical amount/stock consistency. It does not prove
that a raw annual price is a truthful ARPU, that quantity assumptions are
well-founded, that group/segment perimeters are economically disjoint, or that
an actual source supports a forecast. Synthetic source claims remain fixtures;
real source qualification and buy-side analysis remain separate audit work.

## Isolation

The owned `_owned_scratch` was absent before execution and absent after cleanup.
Only that newly created child directory was removed. All product files and old
failure files were checked before/after. No canonical WIP, installed skill,
original document, production configuration or product file was written.
Provider, LLM and network calls: **0**. Cost: **$0**.

`results.json` contains every observed outcome and before/after SHA record;
`probes.py` contains the independent reproducer; `native-cli.log` retains actual
CLI output; `manifest.json` freezes this review's evidence. ROOT remains
responsible for ordinary hooks, selective installation, main integration and
remote publication against this accepted freeze.

