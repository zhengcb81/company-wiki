# P3-IDENTITY-AUDIT — Independent Review Report (Round 2, FINAL)

**VERDICT: APPROVE**

- reviewer: **independent-agent (non-author, non-ROOT)**
- round 1: 2026-10-18 (REJECT, bound to `99a67f06`; findings F1–F7 + notes F8–F11)
- round 2 (this report): 2026-10-18 (re-review of the fixes)
- implementation commit (bound): `99a67f06` (`99a67f06d082964cc8ad974e31611d582f095213`)
- fixes commit (bound): `20a43fab` (`20a43fab696a3dccb9e0886633f3daadae012b92`)
- `git rev-parse HEAD` at review start **and** end: `20a43fab696a3dccb9e0886633f3daadae012b92` — **unchanged during the review**; HEAD == fixes commit.
- baseline: `4045787f`, branch: `codex/p3-identity-audit-20261018`
- working tree: **clean** (`git status --porcelain` empty) before this report write; after this write the tree contains exactly one modified tracked file — this report. HEAD did not move.
- All probe fixtures were built under `%TEMP%\p3-review-r2*\` (`probe.py`, `probe2.py` in `%TEMP%\p3-review-r2\`); no production `config/source_catalog.yaml`, no production `catalog.sqlite3`, no `output/` was opened or written.

All round-1 BLOCKER/MAJOR findings (F1–F3) are genuinely fixed and independently reproduced against the final tree; all MINOR fixes (F4–F7) are verified. Notes F8–F11 remain disclosed/acknowledged (F11 resolved by a clean `static-2.log`). One new MINOR hardening nuance (NEW-M1) and two cosmetic notes (NEW-M2, NEW-N3) are listed below; none blocks. The full acceptance battery passes (50/50 tests twice, ruff 0, mypy 0, scope clean, read-only proven byte-level, receipt shape exactly frozen).

## 1. Per-finding verification (round-1 findings vs final tree)

| # | Severity (R1) | Status | How the reviewer verified (own commands/probes at `20a43fab`) |
|---|---|---|---|
| F1 | BLOCKER | **FIXED** | `core.py:235-247::_validate_span` now calls the frozen `EvidenceSpan.from_dict`; `EvidenceSpanError` subclasses `ValueError` (`src/company_wiki/source_contract/evidence_span.py:32`) and is mapped to `blocked`/`invalid_argument`. Live CLI probes on a fresh `%TEMP%` fixture: (a) span with **all-null coordinates** → exit **3**, `status=blocked`, `reason=invalid_argument`, **exactly one** canonical LF line on stdout, non-empty, **no traceback**; (b) span with a **corrupted span_id** (valid URN shape, wrong binding) → same refusal. `from_dict` also rejects missing/unknown span fields, wrong `schema_version`, bad `parse_status`/`quality_flags`, unpaired/negative offsets and `output_sha256` mismatches (`evidence_span.py:212-242, 305-366, 408-428`). |
| F2 | MAJOR | **FIXED** | The illegal shape is refused at validation with `sources == []` — no span verdict exists, so `pass` is impossible (probe F1a). `text[None:None]` is unreachable: `_span_groundable` (`core.py:430-436`) requires all five structural coordinates null, and `from_dict` guarantees paired non-null int offsets (`char_end > char_start >= 0`) for every accepted span. Probe: wire-valid span with `page_number=1` (null char offsets) → `not_applicable(reason=not_groundable_shape)`, never pass. |
| F3 | MAJOR | **FIXED** | `core.py:456-460` explicit bounds check before slicing. Live probe: span `char_end=10^9` → exit **2**, span `fail` + `p3_span_ungrounded` + `detail.bounds_violation.text_length=31` (not a slice-clamped pass). Regression test `test_a_span_beyond_eof_is_ungrounded_not_clamped` asserts all three. |
| F4 | MINOR | **FIXED** | `core.py:285-303::_bytes_check` recomputes sha256 **and** length on the pass path and compares against the request; mismatch → `p3_bytes_mismatch` with `requested_sha256`/`requested_bytes` in detail. Verified by code read; clean-run probe shows pass detail `sha256=62a4d15f…, bytes=51` equal to the requested digest/size; the one-byte-flip probe exercises the fail path (exit 2, `checks.error_code == p3_bytes_mismatch`). |
| F5 | MINOR | **FIXED** | `receipt.py:71` LIMITATIONS now discloses that a `source_availability_unknown` entry is counted under `checked` only. Probe arithmetic: `checked=6`, verdict buckets sum `5`, gap `== 1 ==` the number of `source_availability_unknown` entries; disclosure line present in every receipt (clean and fail runs). |
| F6 | MINOR | **FIXED** | `core.py:380-418`: **every** period `detail` now carries `date_provenance` — pass (`{date_provenance}`), non-ISO fail, expect-conflict fail (`core.py:404`), and not_applicable. Probes: clean run `detail={date_provenance:"unverified"}`; non-ISO fixture (`period_end="2026/06/30"`) fail detail carries it; direct `_period_check(all-null, {}, None)` not_applicable detail carries it. The `observed.date_provenance` copy is retained (compatibility) and the strengthened assertion `checks["period"]["detail"]["date_provenance"]` is in the suite. |
| F7 | MINOR | **FIXED** (as scoped in R1) | `cli.py:169-171, 211-213::_refused_out_path` rejects a `..` component or an existing symlink target before any byte moves. Live probe: `--out <root>/sub/../escape.json` → exit **3**, `blocked`/`invalid_argument`, neither path written. Symlink-target branch verified by code inspection only — creating a file symlink is privileged in this environment (probe hit `WinError 1314`), see “NOT evaluated”. Residual nuance about junctioned **parent** directories is NEW-M1 below. |
| F8 | NOTE | **ACKNOWLEDGED** | Check entries remain a documented superset of the card §5.3 sample (`detail` everywhere, `tokens`, `observed`/`expected`, checks-level `error_code`); the receipt **shell** is exactly the frozen 7 keys (probe, §3 item 5). Extension openly documented in `test_2_receipt_shell.py:28-40`; status vocabulary untouched. |
| F9 | NOTE | **ACKNOWLEDGED** | Extra reason `no_groundable_span` (`core.py:501-505`) alongside the card-named reasons; reasons are not a frozen vocabulary (INTERFACES §2/§3 freeze statuses/error codes only) and every `not_applicable`/`not_evaluated` carries one (probes). |
| F10 | NOTE | **ACKNOWLEDGED** | `p3_availability_fabricated` defined (`receipt.py:56`) and exported (`:129`) with no call site — consistent with card §5.4(4) (a non-null date without evidence is honest-unverified; fabrication surfaces as expect-conflict) and INTERFACES §3 “只增不改”. Reviewer grep: exactly those 2 references. |
| F11 | NOTE | **RESOLVED** | `static-2.log` is a clean re-capture (ruff “All checks passed!”, mypy “no issues found in 6 source files”, manual CLI demo `exit=0 status=ok` with byte-level read-only proof); no traceback. `static-1.log` retained as historical evidence only. |

## 2. Acceptance battery (all commands run by the reviewer in the worktree)

| # | Command | Exit | Result |
|---|---|---|---|
| 0 | `python -B -c "import company_wiki; print(list(company_wiki.__path__))"` (PYTHONPATH=`src`) | 0 | resolves to **this worktree**'s `src\company_wiki` |
| 1a | `$env:PYTHONPATH=(Join-Path (Get-Location) 'src'); python -B -m pytest tests/unit/test_identity_audit -q -p no:cacheprovider` | 0 | **50 passed, 0 skipped, 0 failed** (21.12s) |
| 1b | same command, second run (stability) | 0 | **50 passed** again (25.43s) — stable |
| 1c | New-case quality read | — | The 4 round-2 cases are meaningful, not placeholder: core-level blocked-with-no-sources; CLI exit-3 single-line-JSON; bounds-violation triple assertion; `--out` traversal with “nothing written” assertions. `git diff 99a67f06..20a43fab -- tests/…` = **81 insertions, 0 deletions** (additions/strengthening only, no case removed or weakened) |
| 2a | `python -m ruff check tools/identity_audit tests/unit/test_identity_audit` | 0 | All checks passed! |
| 2b | `python -m mypy tools/identity_audit/{core,cli,receipt,export,__main__,__init__}.py` | 0 | Success: no issues found in 6 source files |
| 3a | `git diff --stat 4045787f..HEAD` | 0 | 25 files, 3452 insertions; **every path inside** `tools/identity_audit/**`, `tests/unit/test_identity_audit/**`, `docs/plans/parallel-packages-2026-10-18/P3-IDENTITY-AUDIT/**`; `src/**` appears **0** times; **0 paths outside the write set** |
| 3b | `git status --porcelain` | 0 | empty (clean) before this report write; HEAD `20a43fab` unchanged start→end |
| 4a | Fresh `%TEMP%` fixture, unmodified CLI run + whole-tree snapshot (sha256+size+mtime_ns) | 0 | `status=ok`, one canonical line; **whole fixture tree byte-identical** (incl. mtime_ns) |
| 4b | One-byte flip of the raw original (same length) → CLI → restore | 2 | `bytes.status=fail`, `p3_bytes_mismatch` (both entry- and checks-level), top `fail`; after restore raw file **byte-identical**; **catalog/ subtree (4 files) identical** incl. mtime_ns; only the reviewer's own restore touched `lake/Acme/annual.txt` (mtime only) |
| 5 | Receipt-shape re-check (clean + blocked receipts) | — | shell keys exactly `{schema_version,status,generated_at,inputs,counts,limitations,sources}` (+`reason` on blocked, card-mandated); counts keys exactly the frozen five; statuses only from the vocabulary (`source_availability_unknown` on `availability` only); every `not_applicable`/`not_evaluated` carries `reason`; stdout = single line, **LF-only, no CR, ASCII, canonical** (`ensure_ascii, sort_keys, compact separators`) |
| 6a | `git diff 99a67f06..20a43fab -- tests/unit/test_identity_audit/` | 0 | only `test_1_checks.py` +81/−0: 4 new regression cases + 1 strengthened `detail.date_provenance` assertion; **no removed assertions, no deleted/skipped cases**; grep for `skip`/`xfail`/`--ignore`/`-k` in the lane suite: none |
| 7 | Reviewer probes (`%TEMP%\p3-review-r2\probe.py`, `probe2.py`) | 0 | F1a/F1b blocked exit 3; F2 no unknown→pass; F3 bounds violation; F5 counts arithmetic; F6 all detail paths; F7a traversal refused; byte-flip as in 4b — see §1 |

## 3. NEW findings from this round

- **NEW-M1 — MINOR (non-blocking): reparse-point *parent* directories are traversed by `--out`.** Evidence: reviewer probe — an unprivileged directory **junction** parent (`%TEMP%\p3-review-r2-*\junction-out` → `real-out`) accepted `--out junction-out\receipt.json` with exit **0** and wrote through the junction. `cli.py:171` checks `".." in parts or out_path.is_symlink()`, which covers the final target only; `Path.is_symlink()` is False for junctions (mount-point reparse points). Card §8 lists “拒绝重解析点”. Impact is limited: the write still lands exactly at the caller-supplied path, `..` escape and symlink targets are refused, and refusing *all* parent reparse points would break common TEMP/OneDrive-style layouts. Suggested fix: either document the rule (“only the final `--out` target is checked for reparse status; parent junctions are treated as ordinary directories”) in the README/handoff, or extend `_refused_out_path` with an ancestor `is_junction()` scan (`pathlib`, Python ≥3.12). Decision belongs to author/ROOT; does not block APPROVE.
- **NEW-M2 — MINOR (cosmetic, docs):** `tools/identity_audit/README.md` was not synced with round-2 behavior: the `--out` bullet (README.md:21-22) mentions only directory refusal although `..` traversal and symlink targets are now refused, and “Known limitations” (README.md:96-103) does not carry the F5 counts disclosure that every receipt now prints. The receipt itself discloses both correctly, so this is documentation drift only.
- **NEW-N3 — note (cosmetic):** `_period_check` computes and assigns `observed["date_provenance"]` twice in a row (`core.py:381-383` then `:385-388`) — harmless redundancy introduced by the F6 fix.

## 4. What this review did NOT evaluate

- The production catalog (`config/source_catalog.yaml`, production `catalog.sqlite3`) and `output/` — never opened, per boundary; all probes ran on synthetic fixtures under `%TEMP%`.
- Live refusal of a **symlink** `--out` target: file-symlink creation is privileged here (`WinError 1314`); that branch was verified by code inspection (`cli.py:171`) only, not by a live probe.
- PDF/DOCX span grounding (out of card scope; only exact UTF-8 `text/plain` spans exercised).
- The other three lanes (P1/P2/P4), cross-lane integration, or any card other than P3.
- Behavior under SQLite-level I/O failures beyond the `catalog_unavailable` → `unavailable` mapping covered by code and tests.
- `pyproject.toml` packaging (frozen by the card); entry-point registration.
- Exact-ceiling boundary behavior (500 refs / 5000 spans / 16 MiB at the precise limit) beyond the >limit blocked tests; no performance measurement.
- Whether the RED log was produced before the implementation commit at the VCS level (content-judged only, as in round 1).
- The policy question behind NEW-M1 (whether ROOT wants a strict “no reparse points anywhere in the `--out` chain” rule) — flagged for author/ROOT decision.

## 5. Binding statement

This report is bound to commit `20a43fab696a3dccb9e0886633f3daadae012b92` (HEAD at review start and end, identical to the fixes commit; implementation `99a67f06`; baseline `4045787f`). HEAD did not move and the working tree was clean throughout the review; the reviewer wrote exactly one file in the worktree — this report — and modified nothing else. All temporary artifacts live under `%TEMP%\p3-review-r2*`. Verdict: **APPROVE** — no open BLOCKER or MAJOR; NEW-M1/NEW-M2/N3 are minor and non-blocking.
