# P3-IDENTITY-AUDIT — Independent Review Report

- reviewer: **independent-agent (non-author, non-ROOT)**
- date: 2026-10-18
- implementation commit (bound): `99a67f06` (`99a67f06d082964cc8ad974e31611d582f095213`)
- `git rev-parse HEAD` at review time: `99a67f06d082964cc8ad974e31611d582f095213` — **unchanged**, i.e. HEAD == implementation commit; report bound to `99a67f06`.
- baseline: `4045787f`, branch: `codex/p3-identity-audit-20261018`
- working tree before report write: **clean** (`git status --porcelain` empty). After this report is written the tree contains exactly one untracked file — this report (`docs/plans/parallel-packages-2026-10-18/P3-IDENTITY-AUDIT/review/independent.md`); no tracked file and no path outside the card write set is touched. All probe fixtures were built under `%TEMP%\p3-independent-review\` and the probe script under `%TEMP%\p3_review_probe.py`; nothing under `output/`, no production `config/source_catalog.yaml`, no production `catalog.sqlite3` was opened or written.

## VERDICT: REJECT

1 BLOCKER + 2 MAJOR. All three are in the span-validation/grounding path and empirically reproduced by the reviewer against a fresh synthetic fixture. Minor/NOTE findings are listed below and do not block by themselves.

## 1. Verification matrix (all commands run by the reviewer in the worktree)

| # | Check | Command (abbreviated) | Exit | Result |
|---|---|---|---|---|
| 1a | Full lane suite | `$env:PYTHONPATH=<worktree>/src; python -B -m pytest tests/unit/test_identity_audit -q -p no:cacheprovider` | 0 | **46 passed, 0 skipped, 0 failed** (matches author's `green-1.log`) |
| 1b | No scope-narrowing | grep of lane tests for `skip`/`-k`/`--ignore`/`xfail` | — | none found; only `except` is `harness.py:39` (RED-phase `ImportError`→named `AssertionError` wrapper, disclosed, re-raises — not swallowing) |
| 1c | RED genuineness | read `red-1-pre-implementation.log` | — | genuine pre-implementation log: 44 failed / 2 passed; **34 explicit `AssertionError: … is not implemented yet`** wrapping `ModuleNotFoundError: No module named 'tools.identity_audit'`; the 2 passes are the fixture-contract tests that need no lane module. Assertion messages, not bare ImportErrors. |
| 2a | ruff | `python -m ruff check tools/identity_audit tests/unit/test_identity_audit` | 0 | All checks passed |
| 2b | mypy | `python -m mypy tools/identity_audit/{core,cli,receipt,export,__main__,__init__}.py` | 0 | no issues in 6 source files |
| 3a | Scope diff | `git diff --stat 4045787f..HEAD` / `--name-only` | 0 | 22 files, all inside `tools/identity_audit/**`, `tests/unit/test_identity_audit/**`, `docs/plans/parallel-packages-2026-10-18/P3-IDENTITY-AUDIT/**`. **Zero paths outside the write set**; no `src/**`, no `pyproject.toml`, no `.githooks/**`, no other card's dir, no ROOT-exclusive path. |
| 3b | Tree state | `git status --porcelain` | 0 | empty (clean) |
| 4 | One-byte flip read-only probe (reviewer's own fixture under `%TEMP%`, mirroring `fixtures/sidecar_catalog.py` and importing it via `sys.path`) | flip byte 0 of the raw original (same length), run CLI, restore | see left | (a) `bytes` = **fail** + `p3_bytes_mismatch` (detail.refusal `content_sha256_mismatch`); (b) top `status="fail"`, **exit 2**; (c) after restore, raw bytes identical and `catalog/` subtree sha256+size+**mtime_ns** identical; whole tree unchanged except the reviewer's own restore of the raw file; (d) unmodified re-run: **exit 0**. Clean run with no `--out` leaves the whole fixture tree byte-identical (sha+size+mtime_ns). |
| 5a | No `--out` → no out file | clean run, full-tree snapshot diff | 0 | no file created anywhere in the fixture tree |
| 5b | `--out` = directory | `--out <fixture-root dir>` | 3 | `blocked` / `invalid_argument` |
| 5c | missing `--request` | `--config <cfg>` only | 3 | `blocked` / `invalid_argument`; `b"usage"` absent from stdout |
| 5d | stdout canonical single line | byte-level stdout capture via file redirect | 0 | exactly one line, **LF only (no CRLF)**, equals `json.dumps(parsed, ensure_ascii=True, sort_keys=True, separators=(",",":")) + "\n"` |
| 5e | `--pretty` equivalence | `--pretty --out pretty.json` | 0 | file content JSON-equal to stdout |
| 5f | duplicate JSON keys | raw request with two `source_refs` keys | 3 | `blocked` / `invalid_json` |
| 6 | Receipt shape adversarial | reviewer probe on receipts produced above | — | shell keys exactly `{schema_version,status,generated_at,inputs,counts,limitations,sources}`; `counts` keys exactly the frozen 5; bucket-wise reconciliation with per-source check entries holds (see F5 for the additive gap); per-check statuses only from `{pass,fail,not_applicable,not_evaluated}` (+`source_availability_unknown` on `availability` only); every `not_applicable`/`not_evaluated` carries a `reason`; blocked receipts add only the card-mandated `reason` field |
| 7 | unknown→pass hunt (code read + probes) | `core.py` review + adversarial probes | — | availability-missing → `source_availability_unknown` (never pass) ✓; `expect` explicit-null vs non-null → `p3_identity_conflict` ✓; ref-fail poisoning: downstream checks become `not_evaluated`, never pass ✓; `not_applicable` cannot mask an expectation conflict (expect loop runs before the `not_applicable` branch in both identity and period) ✓; **but span grounding has two real unknown→pass paths — F2/F3 below** |
| 8 | Honest limitations | receipt `LIMITATIONS`, README, findings.md | — | §5.4(5) key-name discrepancy (`schema_version`/`source_url`/`captured_at` vs real `source-availability-evidence/1` keys `available_by`/`basis`/`evidence_ref`/`locator`/`source_sha256`) is **disclosed, not hidden**: it is in every receipt's `limitations` (receipt.py:69), README "Known limitations", and findings.md §2. |

## 2. Findings

### F1 — BLOCKER: contract-illegal spans are not rejected; one shape crashes the CLI (no receipt, exit 1)
- Evidence: `tools/identity_audit/core.py:250-266` (`_validate_span` hand-rolls validation and allows `char_start=null, char_end=null` with all coordinates null), `core.py:509` (`absolute_start = offset + token["char_start"]` → `TypeError` when offset is `None`). Card §5.2 mandates: “`evidence_spans` 用 `EvidenceSpan.from_dict` 解析；非法即 `invalid_request`”. `EvidenceCoordinates` (`src/company_wiki/source_contract/evidence_span.py:232-236`) rejects all-null coordinates ("coordinates must contain at least one location") — so this request must be `blocked`/`invalid_request` exit 3.
- Reproduced (reviewer probe, `%TEMP%` fixture): request span with all-null coordinates and `raw_text` containing a unit token → CLI exits **1**, stdout **empty**, traceback `TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'` at `core.py:509`. Violates card §5.1 (“成功/失败都向 stdout 打一行 JSON”; exit codes only 0/2/3).
- Suggested fix: parse each request span with `EvidenceSpan.from_dict` and map `EvidenceSpanError`/`ValueError` to a `blocked` receipt (`invalid_request`/`invalid_argument`, exit 3), exactly as the card specifies; keep `_validate_span` only as an early cheap filter, not a replacement.

### F2 — MAJOR: unknown→pass — a span with null offsets is recorded as `pass`
- Evidence: `tools/identity_audit/core.py:430-458`. `_span_groundable` never checks `char_start`/`char_end`; with both `null`, `text[None:None]` is the whole text, so `raw_text == text[None:None]` yields `pass` with `detail={"char_start": null, "char_end": null}`.
- Reproduced: same illegal all-null-coordinate span on a unit-token-free body → **exit 0, top `ok`, span entry `pass`** with null offsets. This is precisely the card §10 “未知→通过” focus: an ungroundable/unknown interval is certified as verified.
- Suggested fix: after F1's `from_dict` validation this input becomes blocked; additionally, as defense-in-depth, treat `char_start is None or char_end is None` inside the grounding branch as `not_applicable`/`not_evaluated` with a reason, never `pass`.

### F3 — MAJOR: silently clamped span offsets — `char_end` beyond EOF passes
- Evidence: `tools/identity_audit/core.py:456-458` (`raw_text != text[char_start:char_end]` relies on Python slice clamping; no bound check `char_end <= len(text)`).
- Reproduced: span claiming `char_start=0, char_end=1000000000` with `raw_text` = full text → **exit 0, span `pass`, `detail.char_end=1000000000`**. The claimed interval does not exist in the document; the receipt certifies it as grounded and echoes the absurd offset. Card §10 names “span offsets silently clamped” as a review focus.
- Suggested fix: require `0 <= char_start < char_end <= len(decoded_text)` before comparison; otherwise `fail` + `p3_span_ungrounded` (or `not_applicable` with an explicit reason) — never a clamped `pass`.

### F4 — MINOR: `bytes` pass branch never compares against the request
- Evidence: `tools/identity_audit/core.py:304-309` — on the pass path only the recomputed sha256/len are reported; the comparison demanded literally by card §5.4(2) (“重算 sha256，与 `content_sha256` 相等且 `len(bytes)==byte_size`”) is delegated to the read side's internal verification (`src/company_wiki/source_catalog/source_reader.py:749-753`, `_read_verified_bytes(expected_sha256=ref.content_sha256, expected_byte_size=ref.byte_size)`), which the reviewer verified is called with the **requested** ref (`tools/identity_audit/export.py:109`). Transitively safe today, but not self-contained: any future change to the reader's verification semantics would silently turn this check into "echo whatever the reader returns".
- Suggested fix: in `_bytes_check`, explicitly compare `sha256_hex(read.data) == requested.content_sha256 and len(read.data) == requested.byte_size` before `pass`.

### F5 — MINOR: `counts` are not additively closed when availability is `source_availability_unknown`
- Evidence: `tools/identity_audit/core.py:703-722` — every entry is counted into `checked`, but a `source_availability_unknown` entry falls through all four status buckets. Reviewer's clean-run receipt: `checked=6, passed=4, failed=0, not_applicable=1, not_evaluated=0` → buckets sum to 5, not 6. The card froze the 5-key counts shape with no bucket for this status, so bucket-wise reconciliation holds (verified) but consumers reading `checked − (passed+failed+na+ne)` will see a phantom "1 unchecked".
- Suggested fix: pick and document one convention (e.g. count `source_availability_unknown` under `not_evaluated`, or state in the README/receipt limitations that `checked` intentionally exceeds the bucket sum by the number of availability-unknown entries); flag for ROOT if a counts-key change is preferred.

### F6 — MINOR: `date_provenance` placement deviates from the frozen shape
- Evidence: `tools/identity_audit/core.py:387-389` emits `period.observed.date_provenance`; card §5.4(4) says `detail.date_provenance="unverified"`. Semantics are disclosed either way, but the card's per-check shape is frozen.
- Suggested fix: move `date_provenance` into the check's `detail` (or get ROOT sign-off on the observed placement).

### F7 — MINOR: card §8 `--out` hardening only partially implemented
- Evidence: `tools/identity_audit/cli.py:107-129,141` — a directory target is refused (✓), but `..` traversal components and reparse points are not rejected, both of which card §8 explicitly lists (“拒绝目录、拒绝 `..` 逃逸、拒绝重解析点”).
- Suggested fix: resolve the path and reject if any component is `..`, the final target exists and is a reparse point, or the resolved parent escapes the caller-intended directory per a documented rule.

### F8 — NOTE: check-entry shape is a documented superset of the card §5.3 sample
- Evidence: `tools/identity_audit/core.py:160-177` — every check uniformly carries `detail` (and `unit` carries `tokens` even when `not_applicable`); the card's §5.3 sample shows no `detail` on identity/period/unit. The receipt **shell** itself is exactly the frozen 7 keys (probe A4). The extension is openly documented in `test_2_receipt_shell.py:28-40` and `progress.md` (RED→GREEN fix #1); status vocabulary untouched.
- Suggested fix: none required for correctness; ROOT may want a one-line note in handoff.json that check entries are a shape superset of the card sample.

### F9 — NOTE: additional `unit.not_applicable` reason string
- Evidence: `tools/identity_audit/core.py:495-501` — `reason="no_groundable_span"` in addition to the card-named `no_unit_token_in_span`. Reasons are not a frozen vocabulary (INTERFACES §2/§3 freeze statuses and error codes only); both uses carry the mandatory `reason`.
- Suggested fix: none; optionally align naming at ROOT review.

### F10 — NOTE: `p3_availability_fabricated` is defined but unreachable
- Evidence: `tools/identity_audit/receipt.py:56` defines it; no call site. This is consistent with card §5.4(4), which explicitly rules that a non-null `published_date` without availability evidence is honest-unverified (`pass` with provenance) and fabrication surfaces only as an `expect` conflict (`p3_period_conflict`). INTERFACES §3 allows unused codes (“只增不改”).
- Suggested fix: none; keep for future contract use or drop with ROOT's consent.

### F11 — NOTE: `static-1.log` retains an earlier failed demo traceback
- Evidence: `docs/plans/.../static-1.log` contains a UTF-16-mangled `ModuleNotFoundError: No module named 'fixtures'` traceback from a first demo attempt, preceding the successful run (`demo exit: 0`). Evidence hygiene only; the final demo result is valid.
- Suggested fix: none; optionally re-capture a clean log before handoff.

### Positive verifications worth recording
- Read-only is **proven, not claimed**: reviewer's own one-byte flip → `bytes.fail`/`p3_bytes_mismatch`, exit 2, catalog `catalog/` subtree byte- and mtime-identical after restore; clean runs leave the tree byte-identical (sha+size+mtime_ns), matching the design note in findings.md §4 (`mode=ro` + `PRAGMA query_only=ON`, `src/company_wiki/source_catalog/reader.py:175-198`).
- Exit-code ↔ `status` consistency verified across all probes: `ok`→0, `fail`→2, `blocked`→3; `unavailable`→3 covered by `test_2_receipt_shell.py::test_an_unreadable_catalog_is_unavailable_not_a_pass`.
- Identity width rule works as specified: observed CN `9896` → canonical `009896` ≠ observed → `p3_identity_conflict`; markets never borrowed (`security_codes_equivalent`, `security_code.py:28-35`).
- Unknowns stay `null`/`not_applicable` with reasons everywhere except F2/F3; no `""`/`0`/`[]` fabrications found.
- Ref-fail does not poison downstream into passes: all downstream checks become `not_evaluated("ref_check_failed")` and the source/top go `fail` (probe B).

## 3. What this review did NOT evaluate

- The production catalog (`config/source_catalog.yaml`, production `catalog.sqlite3`) — never opened, per boundary; all probes ran on synthetic fixtures under `%TEMP%`.
- PDF/DOCX span grounding (out of card scope; only exact UTF-8 `text/plain` spans were exercised).
- The other three lanes (P1/P2/P4), their dirs, or any cross-lane integration; no card other than P3 was imported or run.
- Behavior under SQLite-level I/O failures (locked DB, disk errors) beyond the `catalog_unavailable` mapping that the code and tests cover.
- `pyproject.toml` packaging (intentionally untouched by the card; `python -m tools.identity_audit` relies on namespace-package semantics from the repo root, which the reviewer did exercise — it works from the worktree root).
- Long-run resource ceilings at their exact limits (500 refs / 5000 spans / 16 MiB) beyond the >limit blocked test already in the suite; no timing/performance measurements.
- Whether the RED log was produced before the implementation commit at the VCS level (evidence is committed together with implementation; genuineness was judged from content: 34 explicit pre-implementation assertion failures naming the missing module).

## 4. Binding statement

This report is bound to commit `99a67f06d082964cc8ad974e31611d582f095213` (HEAD at review time, identical to the implementation commit). The reviewer wrote exactly one file in the worktree — this report — and modified nothing else; all temporary artifacts live under `%TEMP%`. F1 must be fixed (and F2/F3 addressed) by the author, after which a re-review against the final SHA is required per card §10.
