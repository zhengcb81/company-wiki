# Two-source real replay independent review

2026-10-25 — **PASS_TWO_SOURCE_COMPATIBILITY_RECEIPT**, 0 OPEN receipt findings. Frozen producer: `66dcb7250f807e65e6abac7ed39b8890a4f15117`.

Read-only verification, no tests, batch, model, download, or old profiler rerun. All seven final engineering review LF SHA values match Git blobs of the frozen producer. Gzip SHA/65,461 bytes and expanded SHA/270,191 bytes match the receipt; the archive contains complete two-source results, not only a summary.

| Source | Full worker wall time | Source observation | Model-view compile | Selected spans | Compiled tasks |
|---|---:|---:|---:|---:|---:|
| CN 2024 H1 PDF | 56.2 s | 32.692 s | 21.432 s | 112 | 55 |
| CN call DOCX | 6.6 s | 2.278 s | 2.148 s | 55 | 55 |

Both stay below the unchanged 120-second sample cap. Recorded actual observation and compile selectors are .9; historical .8 is only default metadata here. Import provenance points into the frozen clean producer. Observation plus compile time fits inside each measured worker wall time. Both keep coverage incomplete; no all-content-complete claim is made.

The two originals and three production configurations match recorded before/after SHA and the current on-disk bytes. The archived producer and attempt paths lie in the owned temporary root, which is independently confirmed absent. Worktree removal succeeded. Recorded temporary peak is 15,647,014 bytes; this historical peak is a producer observation, not independently reconstructed after deletion. Zero POST/download/original-copy claims agree with the serialization-only architecture and the request_sent=false artifacts; no external response or semantic summary was produced.

**Product limitations stay visible:** archived content oracle status is FAIL for both samples; formal semantic summary remains NOT_REVIEWED. This accepts the two targeted timeout/language compatibility repairs, not full business recall, PDF-C2 structure enhancement, cache/RF completion, or a new blind holdout. Existing baseline archives were not rewritten. CI receipt binds the correct commit but was still in_progress when last recorded; this review does not claim CI success.

Exact machine-verifiable bindings and oracle counts are in real-review.json. Normal PWF updates should preserve the distinction between tool compatibility success and remaining content failures.
