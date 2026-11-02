# Tools R2 independent review — NEEDS ROOT FIX

**One P2 remains. This initial review does not sign acceptance.** Author report tools-repair-r2.json SHA `93a97ced46934a852d789bd720bb136e4748ef9c02750d82872e1f852fa7531c`; all 11 delivered file SHA matched at the end of the independent 7-case run before author repair was permitted.

`holdout_acceptance_observer.install.observed_generate`, line122: a write failure solely for optional `model-input.json` escapes as OSError before the real/native generate function, which is called zero times. The configured valid request and normal response are rejected by observation storage, and the observation-incomplete marker is absent for this failure. `observed_http` has the same unisolated body-path read/write family. Only the generate/write branch is executed RED here; the HTTP siblings are static same-owner evidence.

Author should isolate these diagnostic IO failures and report observation unknown without retrying or vetoing native work. A successfully read actual body mismatch, real post-once latch, durable paid pin and unknown-cost recovery must remain enforced. ROOT and author have been notified; reviewer has not modified their code.

Independent execution: **6 passed,1 failed /3.39s**. The passing probes use an actual owned child with2.4MB complete JSON/33000stderr bytes plus a failed optional observer; four false/unknown/malformed freeze/prior-use combinations retain all eligibility false/count0; and a real exit9 plus stderr-write error keeps native failure/bytes. No paid/network/source/model call.

Read-only caller review confirmed qualification propagation through attempt, sample row before error/resolve branches, standalone worker initialization, verify/bootstrap/run and bootstrap.json. Explicit scope does not claim quality/independence certification or loop stopping; generic overall=ok is not used as a clean counter in this tools tree. Content SHA+bytes remain distinct from metadata mtime. Real version/gold/source/paid/lifetime checks remain.

Full probe code, log, JUnit, exact11SHA and cleanup evidence: [tools-independent.json](tools-independent.json). Initial independent pre-run hashes were not separately persisted; the author-declared freeze and end-of-run 11/11 actual match are recorded honestly. The subsequent R3 delta review should save actual before/after snapshots.

Self-owned synthetic tmp/ti7 files were saved as report evidence then removed. No original/company/config/Git/index/main PWF modifications. No author22/fullUnit rerun or production acceptance claimed.
