# Independent initial findings

Review scope: source material value and new disclosure coverage, baseline 89540df4.

1. New disclosure relations collect unrelated noun and predicate/number anywhere in a clause; stock can borrow employee/cash amount, geography can borrow payroll/customer address allocation, conversion can borrow supplier/equity/another contract. Common remedy: local assertion and object-bound relation, not keyword denials. Existing reading policy contract conversion fallback must use the same validated relation.
2. New geographic customer revenue grammar only recognizes Chinese income-from-regional-customer phrasing or headquarters/location definition. Ordinary English revenue-from-customers-in-market disclosure is omitted entirely. No country-name list is needed.
3. Explicit assumptions/stock targets can still receive stock coverage and high material value. Source topics do not assert issuer truth, so not automatically a state hallucination; keep original qualifiers and distinguish this from actual signed backlog in summaries.

No raw/source read, model/network/key access, author script, gate file or external repo mutation. Initial probes import actual mother src. Final PASS is not yet given; source-quality 14-item coverage remains unproven.

## Revision review

Original 21 independent tests all pass (revision.xml). ROOT reused predicate_scope, bound direct amounts, removed old duplicate noun-bag conversion logic, and added ordinary English customer-region revenue.

Remaining common grammar defect: stock-headed quantity/conversion relationships are represented only by a narrow direct/partitive string prefix. Same-head coordinated predicate (`and will be delivered`), quantity-first relative (`50% of which`), with-quantity (`with 50% expected`), and attributed amount (`obligations of $80 million are expected`) are omitted; partitive bodies still borrow another actor's unrelated delivery. Six concrete checks added alongside three preservation/negative controls, for 30 total independent cases.

Material value observation remains: generic English core-values/activities can inherit legacy business_structure and keep meaningful_fact. This is a material-value completeness concern, distinct from eligibility or actual-state truth. No assertion that all conditional stock wording is factual; topics are source uses, original qualifiers remain.

## Second revision: semantic pass, efficiency blocker

404 independent + related tests pass, with 374 source files and all changed-code SHA stable before/after (final-execution.json). However, independent bounded-work probe finds exponential backtracking in repeated `_CONVERSION_LINK` alternatives containing unbounded `_AMOUNT`: after excluding import startup, 12 repeated digits + invalid tail takes about 0.007s; 20 takes 2.145s; 28 is killed by parent after 4s. Evidence: regex-work-probe.json. This is a production bounded-work violation even though declared WorkBudget remains finite. A linear carrier tokenizer or genuinely atomic deterministic grammar is required; increasing timeout/work budget is not a remedy. An actual disclosure_relations subprocess regression has been added, excluding interpreter startup time and ensuring child cleanup.

## Final closure

Final410P/31.85s on final bytes2c85b131 (disclosures), tree788a7213/374files. All recorded internal findings resolved; see final-report.md/json. Previous13F/8P and linear-revision406P evidence remain separate historical diagnostics. No claim of annual14 or downstream company closure.
