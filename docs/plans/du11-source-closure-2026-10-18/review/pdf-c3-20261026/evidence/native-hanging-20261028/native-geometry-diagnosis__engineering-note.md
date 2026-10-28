# Native hanging-indent root correction

The source-native DICT snapshot already contains marker/body origin, direction,
box and original character ordering. The default prose producer previously
coalesced font style and discarded these span measurements. The optional fine
capture producer retained boxes but also discarded origin/direction. Both now
carry bounded exact native spans through the existing observation adapter.

One pure geometry helper proves a marker-only prefix and a complete body row
with a shared measured baseline. The continuity owner retains source, role,
scope, page, column, style, original order and terminal barriers and applies
the existing flow tolerances to the measured body box. Canonical text, block
box, source/unit identity and locator are unchanged. A new bullet ends a
statement window while preserving physical adjacency for the existing
qualification mechanism. The helper is included in the existing decision
algorithm fingerprint, without another cache registry.

This proof intentionally abstains on absent/partial measurements, unsupported
direction, multi-row body spans and a short body under eight em. These are
conservative proof limits, not a judgement that the original material is
unimportant. No company, page, currency, business wording or document-specific
font is part of this rule. The original 2.1em/80%/1.15em tolerances remain.

The new neutral suite first produced 17 failures/16 passes on the old path.
Those console results were observed but no full RED log was saved. The first
real native probe (1.145 seconds) lacked default-producer spans and did not
close the gold; that console was also observed, not a preserved before-SHA
benchmark. Adding the existing default producer fixed the missing layer, not
the threshold. The preserved final production-context replay selected112
spans using5,174,255 work units in8.888seconds; the industry income/base/rate/
both-causes is a single source-bound support group. No SDK/model/download ran.

Full source-reading domain:2459 passed/1 new-fixture failure/11 skipped in69.43s.
The failed test changed source text but left font coverage offsets stale;
only that fixture was corrected. The final related114 tests pass in3.24s,
and the unchanged runtime domain is not repeated. Full mypy src393 passes,
targeted ruff passes. Independent review separately records its exact scope
and source hashes; counts overlap and must not be added as unique coverage.

The above is source-layer evidence only. Real prepared-task gold, generated
summary semantics, activation/cache recovery and RF forecast adoption remain
separate checkpoints. SDK startup cost has a read-only isolation design, not
an implemented or proven runtime fix. No raised budget or global package
metadata monkeypatch is proposed.
