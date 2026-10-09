# MAIN local PPTX OCR implementation plan

## Objective and owned boundary

Implement versioned PPTX display-page evidence and explicit bounded local CPU OCR, preserving pure parsing and HTML identity. Provide selected-media exact multi-span replay and honest partial quality. Only document_normalization, its tests, and this package documentation are edited. MAIN owns all automation/catalog/request/profile/public-read integration. No production config, installed copy/model, raw original or other repository is written; no supplier POST/network/download.

## Phases

| Phase | Result | State |
|---|---|---|
| 1. Interface and responsibility RED | Actual 256/260 page error + unsupported OCR interface failed before implementation | complete |
| 2. Ordinals and frozen locators | Current 1.1.0/shape2, old 1.0.0/shape1 retained, HTML unchanged | complete |
| 3. Bounded local OCR and replay | OCR2.0.0/config SHA/CPU; unique media once; selected 10 spans/2 media=2 calls; final legacy/current-config and no-inference preflight verified | complete |
| 4. Real 22-page source and visual QA | Real public TEMP import/read;1067lines/145.549s;8spans/4media16.570s;one page18 numeric follow-up;0network;TEMP/raw/models restored; actual gaps retained | complete |
| 5. Normal scoped commit and interface handoff | Implementation committed normally; final HANDOFF/manifest bind the tested implementation head, delivered in a documentation follow-up commit | complete |

## Evidence and limits

- Initial RED2failed/0.70s. Existing+new concentrated suite81PASS/14.51s; final narrow compatibility/preflight regression4PASS/0.49s (15 deselected), not an extra whole-deck run.
- Full and numeric real checks are opt-in under hard subprocess deadlines; small CI uses deterministic adapters. No optional broad tests or additional real OCR are planned.
- Coverage_complete remains false. Critical first line on body page7 and subtitle on18 are absent; footer/spacing and column-order issues remain. Exact selected replay does not prove full recall or financial table semantics.
- Git hooksPath points at worktree .githooks; pre-commit and commit-msg hooks are absent. Commit will be normal; manual gates are recorded, no hook pass claimed.
