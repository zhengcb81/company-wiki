# Findings

Approved diagnosis: semantic scope/reporting membership changes are absent from operating facts; PDF-only grouping loses replayable OCR fragments. Image pixels must never use PDF point body thresholds. The page7 first body line was not recognized in the prior OCR; no transcription is inserted. Full source coverage remains false.

## Boundaries
OCR adjacency binds source, page, media SHA, shape, role, language, parser and OCR config fingerprint. At most eight members within the existing business character window; index gaps, low confidence, cross-column/media/page and sentence/heading barriers stop joining. Source text, boxes and locators remain separate evidence spans.

## Implementation
- n6_scope_changes: specific business membership, from/to migration, future segment reporting, reporting definition changes, rename and otherwise-unchanged reasons. Source wording is retained; no derived growth assertion. Pure headings/numbers/static definitions/accounting negatives remain empty. New scope signals do not inherit the legacy numeric financial-table exemption.
- narrative_visual_units + narrative_ocr_groups: actual coordinate_space=image_pixels; identity includes source/page/media/shape/role/language/parser/config fingerprint/dimensions/slide ID. Adjacent line index only; aligned horizontal overlap + bounded vertical gap; sentence/heading/new bullet barriers; max8 members and existing business1200 character budget. OCR flags are preserved; unreliable units cannot become standalone candidates.
- completion and neighbors reuse those identity/geometry rules; neighbor expansion is capped at8/1200 and carrier-aware keys prevent shape/media collisions. Classification joins English with spaces; original units are never rewritten. PDF point groups and their body bounds remain separate.
- selector0.4.2 ->0.5.0 is included in existing generation manifest. Old dead jobs are not edited or resumed.

## Live limitation
Actual page7 initial and selected replay executed before receipt serialization failure. Exact selected/native counts and selected spans are unknown because the child receipt was never written. Only executed assertion/control-flow evidence is available. No replacement counts are inferred or synthetic spans used as native evidence. MAIN final single whole-deck node must validate actual bundle/count/replay.
