# OCR runtime composition handoff

Ready for MAIN integration. Branch `codex/main-ocr-runtime-composition-20261009`; worktree `C:/Users/郑曾波/.codex/worktrees/audit-provider-cause/company-wiki`.

- Canonical base `824ab778e2187b5ae5967ab05f6fb22731ade912`.
- Parser dependency `238e053e3003045113efc9cc7afb1390657cb9a6` (feature `a9534e5f`), normal merge `bdebb894690400476f667d6185b63f8021b42b9d`.
- Implementation `d11db2a2020ea329a4fd7dc75033e666c5799d14`. Final delivery is the normal documentation commit containing this handoff; exact hash is reported to MAIN after commit.
- Exact 15 owned implementation/test paths and SHA-256 values are in `handoff.json`. Parser files, main/shared PWF, production configuration, installed packages, raw originals, Dayu and other repositories were not edited. No push.

## Runtime interface

| Seam | Actual contract |
| --- | --- |
| Source composition | `NarrativeNormalization.from_project(root, enabled=...)` reads at most 64 KiB of `config/local_ocr.json` once; missing config gives pure parsing. Non-PPTX work disables that load. |
| Frozen child | `from_snapshot(snapshot, deadline=..., parser_versions=...)`; internal factory options `normalization_config`, `normalization_deadline`, `normalization_parsers`. Each process owns its lazy adapter. Factory never rereads deployment config. |
| Causal identity | `identity(mime, parser_version=...)` dispatches HTML 1.0 / pure PPTX 1.1 / OCR PPTX 2.0. Actual `parser_components` overrides manifest parser tuple. OCR config paths remain only internal snapshot data; causal identity is pathless. Frozen config/manifest mismatch refuses `BATCH_FROZEN_BINDING_INVALID`. |
| Public read | Reader composes current OCR config only for recorded PPTX 2.0, validates actual local model SHA/runtime through the adapter and replays all selected spans once. One inference per selected unique media. Pure 1.0 internal slide IDs and 1.1 display ordinals ignore current OCR. Selected OCR fingerprint must also match generation metadata. |
| Language | Native source text first, then at most three actual unique image samples; no company/market guess or second whole-deck OCR. Selected units keep the actual source language, including English. |
| Coverage/reuse | `partial` plus completed summary and reliable selected spans may reuse after exact public replay. Whole-source coverage remains false with explicit opaque/recall/layout diagnostics. Empty skip still needs coverage complete, zero spans, summary_not_needed. No reliable span fails PARSER_INCOMPLETE. |
| Historical binding | Legal scoped builder without manifests produces /2; complete manifested batch produces /3. Declared malformed /3 never falls back. /1,/2,/3 preserve frozen job/model/pricing/usage identity while observing current facts. |

## Accepted evidence

| Proof | Result | Receipt |
| --- | --- | --- |
| Concentrated select/verify/factory/batch/generation/publicread + known CI compatibility | 215 PASS, pytest 32.47 s | `GREEN-responsibility-final.json/.txt` |
| Snapshot/manifest and selected fingerprint causal faults, three-version frozen resume | Initial 3 RED/1 PASS; final 76 PASS, 11.42 s | `RED-causal-binding`, `GREEN-causal-and-frozen-resume` |
| Real configured finite public CLI, HTML/PDF/TXT different-run reuse | 3 PASS, 29.31 s; each source 1 loopback POST total, reused run 0 reservations/fees, publicread verified | `GREEN-configured-carriers.json/.txt` |
| Scoped lint and normal code commit | ruff --no-cache passed; normal ruff/mypy/host hooks passed | `RUFF-owned-final.json/.txt`, code commit |

Tests use self-owned tiny PNG/PPTX/model byte fixtures and an isolated adapter, with the actual parser/replay implementation. Tiny model SHA verification is real; offline adapter does not initialize ONNX or claim installed-engine validation. Loopback POSTs are engineering proof only. Supplier/paid model calls: 0. No new real 22-page run.

All runner receipts record protected config hashes equal before/after and own short TEMP absent after finally cleanup. Earlier failed caller and implementation receipts remain present and explicitly unaccepted in `handoff.json`, including GREEN-named files with nonzero exit. This task used no budget overlay.

## MAIN follow-through

Normal merge this delivery branch, then MAIN's one actual major node with the published verified OCR configuration and adequate remaining outer deadline (card uses 600 seconds). Outer worker deadline, existing AUTO/budget/outbox/storage responsibilities are retained. Actual local engine correctness and real deck/model completion are not claimed by this offline package.

RF source_preparation has a hard min30-second publicread timeout. Selected media replay on the actual deck may exceed that cap; MAIN owns the downstream remaining-deadline fix. No RF files were edited here.
