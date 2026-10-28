# Native-range source quote oracle — frozen handoff

Status: ready for non-author review. Only the oracle and one tools-side neutral test changed; no production, observer, gold or PWF change.

## Cause and repair

Verified native-range actual line breaks were folded to spaces before quantity/CJK boundary observation; a complete selected original was falsely scored missing. The sibling fragment join already knew the same numeric/CJK edge.

Share the existing CJK boundary predicate between fragment and native-range observers. Observe actual single source line breaks before general whitespace folding; preserve intentional inline spaces, blank paragraph breaks, English and digit/decimal/comma token boundaries.

## Validation

- Neutral TDD: 13 failed / 32 passed before; 45 passed after.
- Related source-quote, numeric-fragment, claim-grounding, observer/admission and context/display matrix: 156 passed, 3.836 seconds. Ruff and mypy passed.
- Same saved v5 selection + exact sent HTTP envelope + unchanged gold: full selection and actually sent tasks both 2/3 → 3/3. Industry closure is witnessed by t33. Compiler material byte-equivalence assertions passed.
- Original source identity/page/role and partial factual citation controls remain strict; no SDK, PDF parsing, model, downloads or budget changes. .c3cir restored absent.

## Frozen files

- `tools/document_understanding_benchmark/closed_group_support.py` — raw SHA `67180cdee5e260b9e25430b4b9489f9806a33d216ed50f49ae6d52e272de85b9`, LF SHA `4f0b7127384339bebaba1d7150436d01ebfa08ecce4e4a70dbac2f042c336af9`
- `tools/document_understanding_benchmark/tests/test_native_range_quote_boundaries.py` — raw SHA `590835cf5a5b4c00a4ebf6ae08c12068fd46d7c670af60efe1b88b4fd8089bab`, LF SHA `590835cf5a5b4c00a4ebf6ae08c12068fd46d7c670af60efe1b88b4fd8089bab`

## Observer ownership

`phase_c_observer._sent_task_gold` and `gold_observation` both use this score_facts owner. Its file is unchanged; no secondary patch is needed. See handoff.json for its frozen SHA and input gold/gzip hashes.

## Evidence and limits

red.xml/log, green.xml/log, matrix.xml/log/json, actual-red.json and actual-green.json remain in this directory. Reproduction scripts use stdlib saved-data reads or focused pytest only. This is source-support observation, not free-text entailment, summary quality, cache recovery or proof that PDF ingress was validated here. Independent review and ROOT publication remain outstanding.
