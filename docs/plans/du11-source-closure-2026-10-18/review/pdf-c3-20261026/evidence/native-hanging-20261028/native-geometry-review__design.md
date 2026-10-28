# Native hanging-indent body anchor — independent design review

2026-10-28. Read-only design review for ROOT; this is not implementation acceptance. No PDF/SDK/model execution or tests were run. Inputs: saved `native-geometry-diagnosis/page13-native.json`, the last section of `SUMMARY_QUALITY_PLAN.md`, source-native layout capture/binding, observation adapter, continuity edge owner, and ROOT's in-progress `hanging_indent_geometry.py`.

## Recommendation

Proceed with a source-measured auxiliary body anchor. The observed failure is geometric: a marker changes the block's left edge without changing its text body's lane. Keep canonical raw text, bbox, unit IDs, source SHA and locators unchanged. A geometry proof may supply a body bbox to the existing same-page physical-flow test; it must not bypass membership, source/page/order/role/column/font/scope/sentence barriers or increase their existing tolerances.

The saved page proves the mechanism without a company rule. Source SHA is `4f589193fae39fb53cb7d2121d93925b382bb052cfecbdc24e8e8271ea41bd36`. Block 7 marker starts x=99.194595; its body starts x=121.874596; block 8 begins x=121.874573. Marker/body separation is 22.68 points at 9pt font, while the true body-lane delta is about 0.000023 points. Native marker and body occupy different native **line indices** but have identical origin.y=276.125977. CJK and Latin span bbox tops differ despite sharing that baseline. Thus neither matching native line index nor bbox.top is a valid baseline substitute.

## Proof contract and responsibility

1. The native capture owner preserves bounded measured `origin`, line direction and, if used, writing mode with exact source span ranges. The existing projector/adapter explicitly carries these fields. The consumer does not reopen a PDF, infer a baseline from a bbox, or reconstruct a second paragraph inventory.
2. Only an isolated marker plus whitespace may precede the first body character. The prefix and body belong to the exact same canonical raw unit, source, page and coordinate frame. Character ordering/ranges must be exact; only whitespace gaps may be skipped. The marker may be a separate native line object when measured same-baseline evidence proves its placement.
3. The marker/body spans have finite measured coordinates, known supported horizontal direction, positive boxes and a bounded font-relative baseline difference. The marker lies left of and outside the body; body spans run in source order without conflicting overlap. A partial/clipped span cannot donate its full native bbox as a precise body start. Missing, conflicting, transformed or guessed coordinates abstain.
4. The resulting proof references the existing members and original ranges/geometry, records a version, and supplies an auxiliary body bbox. It does not rewrite a source unit or its locator. Downstream factual support still cites all original members, including the bullet, numerical head, comparison and explanatory tail.
5. Continuity alone owns acceptance of the adjacent-unit edge. Keep existing 2.1em horizontal tolerance, 80% overlap, 1.15em gap, terminal boundary and other barriers. Start with the existing same-page edge; do not accidentally extend the new proof into cross-page logic or the terminal-tail branch.
6. Charge work before traversal using the existing shared budget; use the existing bounded native span stream. Missing measurement or budget exhaustion produces an honest unavailable/deferred result, without a fallback semantic join or extra extraction pass. Ensure new geometry/layout/continuity versions participate in recovery/cache fingerprints; existing old artifacts remain readable and are not relabelled as newly verified.

## Recall and precision traps

- The actual source has mixed CJK/Latin fonts on one baseline, and a marker-only native line followed by a body native line. Preserve those positives without weakening the existing dominant body font/style guard. A marker's display font is not the paragraph's body font.
- The canonical newline between marker/body is real source text and must remain. NFC/trimmed subunit offsets must stay exactly aligned; do not derive coordinates by counting normalized characters against original spans without the existing alignment proof.
- A body continuation can begin with a currency unit, percentage, date, negation or qualification. Do not require business keywords or positive financial interpretation to prove physical flow. Conversely physical flow does not promote unresolved financial numbers to generated facts.
- A fresh right-hand bullet must remain a new item even when it shares the body lane. Test both large and small marker indent: the current in-progress guard is inside the large-x-delta fallback, so ordinary wrapped-line handling still deserves an independent next-item control. A complete left statement, heading, new section, table row, new column or source/page break must retain its barrier.
- Marker-only recognition should not reinterpret a dash-led table row, negative number or numbered list label as a bullet merely because the text starts with punctuation. The geometry proof is necessary but is not a financial/semantic exemption.
- Current helper proves **all supplied spans lie on one body row** and requires body width >=8em. These are conservative implementation limits, not general PDF truths. Document them and test abstention explicitly. Short legitimate bullets and multi-row units should not be silently classified as poor content; if later coverage requires them, extend through a measured first-row/remaining-body proof rather than lowering the guard blindly.
- Avoid min-x over an entire multi-line paragraph: later lines, subitems or another lane can change it. A first-row anchor needs exact row membership and cannot manufacture a paragraph group across independent source blocks.
- Explicitly unsupported RTL/vertical/rotated cases should abstain. If rotation is normalized upstream, prove origins/directions/bboxes were transformed into the same coordinate frame together.
- Origin within bbox and exact containment are good defensive checks, but real native metrics may have harmless negative bearings or floating-point edge drift. Do not fix any resulting rejection by widening flow tolerances. First establish a general source-metric invariant and test bounded numerical handling separately.

## Neutral test package for the major node

Use pure measured-layout fixtures, not company/page strings. Keep immutable input snapshots and assert IDs, raw text, canonical boxes and locator bytes remain unchanged.

| Group | Positive / negative evidence |
|---|---|
| Baseline | Same measured origin with different native line indices and differing CJK/Latin bbox tops passes; same bbox top with different measured baselines rejects. |
| Typographic diversity | Chinese simplified/traditional and English body; multiple font sizes; bullet font different from dominant body; multiple body spans. Do not require font-family equality beyond current owner policy. |
| Alignment | Exact whitespace/newline prefix passes; mismatched offsets, real text in prefix, missing origin/direction/frame, partial first body span, overlapping/unsorted ranges and nonfinite values reject. |
| Physical barriers | Same-lane next-line tail passes; competing column, displaced baseline, nonadjacent ordinal/block, different source/page, heading/table/scope/font barrier and terminal left statement reject unchanged. |
| Item boundary | New right bullet at both large and small indent stays separate; dash/negative/numbered-label alternatives do not gain a new unsupported path. |
| Known narrowness | Short body, multi-row left unit and unsupported direction explicitly abstain; no hidden parser/model fallback. Resource exhaustion is bounded and diagnostic. |
| Layer integration | Capture → projection → adapter preserves measured fields and exact binding; pure geometry consumes only those fields; continuity produces proof with original member IDs; consumer sees complete support closure. |

For the real major-node check, replay the already saved native fixture through pure binding/projection where possible, then ROOT's separately authorized real source path. Require the formerly split income/comparison/cause material to be fully recoverable with exact original references (source gold 3/3), while a nearby unrelated item remains excluded. That is source recall evidence; it is not by itself proof of summary quality, cache recovery, or RF adoption. Those remain subsequent PWF checkpoints and should not trigger another large PDF batch here.

## Review conclusion

The planned abstraction is correct: native measurement belongs to the source/layout layer; the shared continuity owner verifies physical neighbours; document/business policies consume already proven source members. The important safeguards are measured baseline preservation across the full interface, exact character membership, no canonical geometry mutation, and separate controls for a new bullet versus a wrapped continuation. A focused neutral package plus the one saved real failure is sufficient for this node; no extra permission or per-example signoff is needed.
