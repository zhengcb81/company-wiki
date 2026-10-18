# Indented terminal tail helper — frozen pending independent review

Only two new engineering files: `document_understanding/indented_tail_geometry.py` and own `tests/unit/du11_source_tail_geometry/test_indented_tail_geometry.py`. No continuity/reading/business policy/foreign worktree edits, no git stage/commit/push, no API/PDF/original/config work.

## Pure contract and bounds

`indented_terminal_tail_proof(left_bbox,right_bbox,font_size,left_text,right_text)->dict|None` takes measured boxes/font and existing source text. It requires valid nonnegative finite boxes, non-bool positive fontsize, all finite derived ratios, body width≥8em, real1–2.2em indent, tail width≤3em AND≤quarter-body, right edge≤left body right edge, forward gap0–1em, both bbox heights0.5–1.5em. Left is not terminated and ends in real CJK; right has1–3nonnumeric real CJK followed by a real terminator with permitted closing quotes, total≤4codepoints. Left text is bounded2048characters. It observes source strings without changes/rewrites and has no file/model/parser/business logic.

The returned proof records actual bbox, negative or positive overlap, font-relative measurements and version`indented-terminal-tail/1`. Actual risk example negativeoverlap−0.11015 is explicit: this is a new narrowly qualified shape, not an assertion that old positive-overlap conditions passed.

## Mandatory caller responsibility

Caller must FIRST prove same original/page/scope/frame/font, actual consecutive ordinal/paragraph and existing column/table/heading/role barriers. Those are not function inputs; the function cannot verify/certify them. It returns no sourceID, column, semantic subject or complete assertion claim. ROOT must connect inside those guards and bind actual helper source/version into current causal cache identity. Lack of proof means unknown/defer, never text repair.

## Test and receipt

70PASS/1.10s focused unit matrix; initial missing-module RED and later5behavior RED retained. Actual __file__ points to this isolated ROOT worktree. No shared historical suite or real C rerun. New module/test hashes and bounded logs in handoff.json. Independent review is deliberately unclaimed; ROOT assigns another agent, fixes confirmed issues and performs integration/real C separately.
