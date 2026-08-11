# FC-802 Independent Review — reviewer-fc802-independent

**Verdict: REJECTED** (2026-08-11, schema 2.0, evidence in `12_reviewer_receipt.json`)

Reviewed in the clean worktree `C:\Users\郑曾波\Projects\.fcap-review\fc-802\company-wiki` (HEAD `e581edc`, base wiki `d09243f` == result wiki; receipt commit on top touches only `11_implementer_receipt.json`). filing-fetch main checkout (`abde149`) read-only; mutation replays ran in a temporary filing-fetch worktree, reverted byte-identical, worktree removed.

## 1. Receipt + triplets — PASS

- Revenue `aa12d9e7` == revenue-forecast HEAD == base == result.
- Filing base `85731b2` / result `abde149` both exist (`git cat-file -e`); `abde149` == filing-fetch HEAD.
- Wiki base `d09243f` == result (unchanged); `git merge-base --is-ancestor d09243f HEAD` -> ANCESTRY-OK.
- `plan_sha256` 158fc1e1... recomputed MATCH — frozen `task_plan.md` at revenue commit 2d64186 (campaign baseline constant, same as FC-801/604/704/705; FC-802 Phase 8 content confirmed in that frozen plan).
- `command_registry_sha256` 215b8077... recomputed MATCH — `compatibility/command_registry.json` at revenue HEAD.

## 2. Diff scope — PASS (with F3)

`git diff --stat 85731b20 abde149` = the 3 allowlisted files (fetch_filing.py +139, filing_contracts.py +41, test_fc802_gap_orchestration.py +301) + `IMPLEMENTATION_PLAN_FC802.md` (process artifact outside the receipt lists — FC-801 F3 precedent; content faithfully matches the plan). Zero unrelated changes.

## 3. Code read — thin orchestration properties verified

- **Structured-gap path**: `action = "ensure" if (allow_download or is_latest) else "resolve"`; `status == "gap"` returns `{status: gap, gap_plan, resolution}` — never `not_found`. Nothing is fetched (mock-verified fetch=0, no `--allow-download` on the command).
- **Thin binding** (`_close_gap_and_return_handle`): `request_id`/`gap_plan_hash` from the ensure payload's plan (`acquisition.gap_plan`), `policy_hash` from the resolution envelope, provider/accessions/caps/expiry from the caller authorization. No provider/root/identity re-derivation. close-gap CLI (`cli.py:1067+`) reads the identical binding keys. Fail-closed: missing envelope -> `policy_hash` None -> `str(None)="None"` -> step-1 policy check rejects.
- **`_handle_from_resolution` single-sourcing**: exactly-one match, `capture_ready` provenance, `validate_handle` containment, FC-704 envelope forwarding (explicit param from close-gap output, `resolution_envelope` fallback) + `validate_resolution_envelope`.
- **Authorization validation** (filing_contracts.py): optional block; non-dict / missing fields / bad shapes -> `request_error`, never silently ignored.
- **Temp binding file**: `NamedTemporaryFile(delete=False)` -> dump -> close -> pass path -> unlink in `finally`.

## 4. Fresh runs — PASS

- `pytest tests/test_fc802_gap_orchestration.py -q` -> **107 passed, 1 skipped, 27 subtests** (module import pulls in the parent suite; `Fc802GapTests` alone = 5 passed).
- `pytest tests/test_fetch_filing.py -q` -> **102 passed, 1 skipped, 27 subtests** (regression green).
- `ruff check` on the 4 files -> **All checks passed**.

## 5. Mutation replay — M1 and M2 KILLED (implementer's claims independently confirmed)

- **M1** (structured-gap branch disabled): `test_gap_structured_without_download` AND `test_allow_download_without_authorization_stays_gap` -> **2 FAILED**. Reverted.
- **M2** (policy_hash bound from request authorization instead of envelope): `test_authorized_close_gap_returns_handle` -> **1 FAILED** (assertion pins `policy_hash == envelope b*64`). Reverted byte-identical; worktree clean; suite green after revert.

## 6. Validator gate — PASS

`python tools/receipt_validator.py --receipt .../11_implementer_receipt.json` from revenue-forecast -> `OK: 1 receipt(s) valid`, exit 0.

## 7. FINDING — F1 (BLOCKING): the ensure CLI rejects `--mode`; latest_as_of orchestration cannot run

**Live proof** (company-wiki CLI at the review worktree, no side effects — strict argparse fails before any config/catalog access):

```
$ python -m company_wiki.source_catalog.cli ensure --entity "Test Inc." --document-kind annual_report --as-of-date 2026-07-18 --mode latest_as_of
company-wiki-source-catalog: error: unrecognized arguments: --mode latest_as_of
```

Control: the same invocation with `resolve` is accepted and executes.

Root cause chain:
1. `fetch_filing._command_arguments` (fetch_filing.py:173-175) unconditionally appends `--mode <mode>` when the request carries one.
2. FC-802's new action line (fetch_filing.py:638-640) routes **every** `latest_as_of` request through `ensure`.
3. The ensure subparser (`cli.py:417-461`) defines no `--mode` (only `resolve` at line 415 and `close-gap` at line 485 do); `main` uses strict `_parser().parse_args` (cli.py:671) -> exit 2 -> `_run_company_wiki_json_retry` raises `FilingFetchError`.

Consequences:
- The structured-gap result (FC802-1/2 — the core of the FC) is **unreachable against the real CLI**. The 5 new tests mock `subprocess.run` and therefore pass while the production boundary fails — exactly the divergence this protocol exists to catch.
- Even a tolerant parser would silently drop the mode: the ensure handler reads `getattr(args, "mode", None)` -> None. Mode is load-bearing in the coordinator — `acquisition.py:313,339` and `resolver.py:827,853` branch on `request.mode == "latest_as_of"` to produce the metadata-only gap plan (and to consult the provider even on local reuse). Dropping the flag in filing-fetch is **not** a valid fix; the ensure parser must gain `--mode` (a company-wiki change, mirroring resolve/close-gap) — which FC-802's sealed scope (wiki unchanged) cannot contain.
- Note: base 85731b20 had the same latent forwarding for the `allow_download`+`mode` combination, but FC-802's action line makes it the primary path of the feature.

## 8. Secondary findings

- **F2 (minor)**: receipt records "6 passed" for the focused command; the file has 5 `Fc802GapTests` methods and the actual command yields 107 passed (parent suite pulled in by import). Scenario count 6 vs test count 5 — FC802-4 is covered by the pre-existing suite only.
- **F3 (informational)**: `IMPLEMENTATION_PLAN_FC802.md` ships outside the receipt lists — accepted FC-801/FC-704/FC-705 precedent; content faithful.
- **F4 (informational)**: `fetch_filing main()` wraps every result as `{status: "capture_ready", handle: ...}` with no gap special-case; a structured gap would surface with top-level `capture_ready` while `handle.status == "gap"`. Downstream consumer contract is for the follow-up.

## 9. Rollback / remediation

Revert `abde149`, or extend FC-802 with the company-wiki `--mode` parser fix and re-seal with a wiki triplet change. The sealed triplet as-is cannot deliver the feature.
