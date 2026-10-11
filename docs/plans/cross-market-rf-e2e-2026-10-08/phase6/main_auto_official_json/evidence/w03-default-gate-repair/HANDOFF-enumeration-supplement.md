# W03 default repair — enumeration grammar supplement / frozen source

This supplements the original `HANDOFF.md`; original handoff, original RED, 122-case node logs/receipts and their historical SHA index remain byte-for-byte unchanged. The original 122 PASS applies to its original source snapshot; this supplement does not falsely reissue a full-node result under the new snapshot. ROOT owns independent final acceptance and normal publication.

## Independent blocker and genuine TDD

Read the independent `w03-default-independent-review/REVIEW.md`, `minimal-probe.json` and `receipt.json`. They precisely established that `公司产品包括各类设备及配套服务等。` was incorrectly selected as `business_structure`; concrete industrial-controller/electric-actuator disclosure remained correctly selected.

Added five cases in the original owned unit test file, without altering any prior test or assertion. Three generic list negatives actually failed before implementation, while two concrete-component positives passed. Native preserved `enumeration-red.log`: **3 FAIL / 2 PASS / 1.62 s**.

Common lexical cause: category matching applied fullmatch directly to an unprocessed list component, so ordinary trailing `等` made the generic category appear specific. Another common list connector, `以及`, was split at `及`, leaving a fake lexical `以` attached to a generic category. Both are list grammar, not source business identity.

## Narrow systematic repair

Only `narrative_business_policy.py` changed again. `_COMPONENT_SEPARATOR` consumes `以及` before its shorter alternatives. `_COMPONENT_ENUMERATION_SUFFIX` recognizes trailing enumeration particles `等`/`等等` with an optional ordinary category suffix (`类型`, `种类`, `类别`, `产品`, `服务`, `设备`, `业务`, `方案`). The component classifier uses those normalized temporary lexical tokens to distinguish generic categories from actual components.

Source unit/raw text, EvidenceSpan text/hash and original locator are never normalized or rewritten. The suffix rule is end-anchored: the actual product term `等离子刻蚀设备` keeps its internal `等`, and concrete controller/actuator/etching-equipment names remain selected even when followed by enumeration grammar. No company, issuer, ticker, file or provider exception was added. Generic or empty tokens cannot become a component merely because of list grammar.

No new edit to grouping, pure version dispatch, runtime, parser, ledger, model, installation, configuration, original material or any W08 file. Default/explicit 0.7 semantics remain under the same not-yet-formally-published version; explicit 0.6 still never calls this helper. The five original failed assertions remain unchanged.

## Concentrated result, restoration and SHA

One targeted run combines the five new lexical cases, fourteen original repair cases and six original five-failure node cases: **25 PASS / 0.63 s pytest / 3.1432608 s outer**. Native log `enumeration-green.log` SHA `3411c22c9c6e945f0f9dfc21de158e9e62124e93a44b1add6f16bc5af6803f91`. Ruff: all three owned source/test files clean. Exact commands/native output and same-source before/after are in `enumeration-node-receipt.json`.

No 122/public3/whole-suite/prepush rerun. No download, model server or paid supplier call. The owned `cwp-w03-list-*` directory, pytest artifacts and all temporary files are removed. The 13 narrowly protected sources/tests/TXT/config files from independent review differ only in the owned policy and appended test; grouping/shared runtime/W04/true TXT/config/public node stay byte-identical. This avoids claiming ownership over the concurrent W08 implementation. `enumeration-final-receipt.json` records exact current SHA values and historical evidence stability.

Source and all writes are now frozen for ROOT final review. This resolves the demonstrated list-grammar defect, not an assertion that a bounded heuristic has exhaustive business-language understanding.
