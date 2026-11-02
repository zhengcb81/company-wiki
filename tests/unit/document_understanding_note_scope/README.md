# T3 phase A — source-note scope, tests first

This directory was absent before this task and belongs only to its T3 tests.
All observations are synthetic. No originals, source databases, downloads or
models are used. No production implementation is supplied here.

The tests use existing `build_observation`, `understand_units`, structure/layout
and `NativeSourceContext.page_neighbour` interfaces. Positive HTML headings come
from the actual HTML normalizer; note fixtures inject no `heading_level` hints.
The no-bbox positive case obtains `pdf-paragraph-membership/1` from the actual
`align_paragraphs` producer, then withholds optional geometry while preserving
all original IDs/text/locators and that producer's member proof.

`inherited_heading_ids` inspects the actual structural parent chain. It does
not claim that downstream reading_context/citation views or model fragments
were exercised. Those checks, real H1 and cache/RF adoption remain OPEN.

Run only this directory with a new explicit owned short basetemp and disable
pytest's cache provider. Record real RED and existing positive controls; do not
xfail the missing behavior, fake heading hints, delete assertions, or stage this
test-only state as a supposedly green product release. ROOT will stage this
path explicitly together with the later production repair. No other R4 source
author's commit includes this directory automatically.
