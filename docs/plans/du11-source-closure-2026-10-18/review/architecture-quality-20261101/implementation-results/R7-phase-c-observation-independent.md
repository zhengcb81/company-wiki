# R7 PhaseC2 observation boundary — independent PASS

Reviewed the author-frozen2files and verified SHA before and after the review. The exact source/test manifest,9new independent cases, full test source/log/JUnit and call edges are recorded in sibling JSON. No source was modified.

Nine new pure synthetic cases passed in2.00s. A >300KB multi-member gzip with a multibyte character crossing the65536 read boundary is fully counted and hashed; exact duplicate observations are harmless and unrelated events cannot override identity. Late CRC corruption, final incomplete UTF8, prefix-only native SHA, one bad duplicate event and absence of a matching event all remain explicit errors.

At the real observer seam, success/failure preserves native receipt and usage object identity and values; `_cli` is guarded and never called. Optional failures expose only a safe reason/type, mark model observation INCOMPLETE and do not invent a saved capture. Successful observation is OBSERVED.

Actual caller inspection confirms the observer is followed by public read, native generation identity, same-run/cross-run zeroPOST and consumer checks. Final aggregation explicitly emits OBSERVATION_INCOMPLETE when any optional observation is incomplete; it cannot become acceptance PASS. Genuine later source/accounting/cleanup failures still become FAIL. The observer contains no owner retry or POST route.

No P1/P2 issue found. No48s native/full-cache run was repeated: the author's native integration evidence was read and is bound to the same unchanged2SHA. This review's new dynamic evidence is the9pure capture/state cases; the final aggregate/caller conclusion is static plus that seam, not a falsely claimed second full native run. No original, external model, key, source/config/CI/Git write, own INV review or unfrozen availability review.

Owned `tmp/r7pc-review` was initially absent. Cleanup receipt is appended after exact parent/nonreparse validation and removal; all reproducible evidence is preserved in JSON first. STOP pending ROOT's final core manifest.

Final measured cleanup: 16 files / 11770.0 bytes; exact parent/nonreparse verified before deletion, restored absent.
