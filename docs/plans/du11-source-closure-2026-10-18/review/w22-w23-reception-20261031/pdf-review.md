# W22-PDF-DEPLOY ROOT independent reception — 2026-10-31

Author HEAD: `dc423843e0404b8730825b0893d8540ccb084b3f`; base `662f821e749bc221c8c308986e54e00465834332`.
ROOT integration starting HEAD: `d8b61d8a1a6a4b22fb1b1fb42cbf9d49a6b2b948` at `C:/Users/郑曾波/Projects/_w22r`.

## Verdict

The author's real ASCII deployment is supported by current read-only evidence. The deployment tool at author HEAD has reproducible safety/completeness defects and should not be accepted unchanged. ROOT authorized fixes in the separate integration checkout; those fixes and eight independent regression cases are now GREEN (88 lightweight tests), uncommitted for ROOT's final review. No SDK was imported, no model was run, and no existing deployment/source byte was modified by this reception agent.

## Findings and integration disposition

1. **P1 — destination junctions escape the owned tree.** Author `deployment.py:345-357` classifies an empty directory junction as EMPTY; `:400-429` follows existing parent aliases while creating links. Actual NTFS junction counterexamples proved (a) a fresh target junction writes the entire fake deployment into the referent, and (b) a package-parent junction in a genuinely owned INCOMPLETE tree writes a package file outside the target. `write_receipt:315-330`, used by verify as well, also writes its temp/marker through a target alias. Fix: preflight existing destination components with lstat, reject symlinks/reparse points before mutation, and enforce the same check in the receipt writer. Source links remain allowed. Tests use only owned temporary fixtures and remove junction names in finally.
2. **P2 — a blocked plan can be deployed as COMPLETE.** `__main__.py:24-40` saves the plan even when blocking_errors is nonempty and returns 1. `deployment.py:263-280` never rejects these errors. A missing RECORD source is omitted from env_rows, and a subsequent deploy returns COMPLETE for the incomplete closure. Fix: load_plan rejects blocking errors before creating the target.
3. **P2 — zero-write reuse omits interpreter and venv isolation.** `deployment.py:508-529` only checks planned links/config. Removing `env/Scripts/python.exe`, or changing `pyvenv.cfg` to system-site=true, still returns REUSED. Fix: reuse requires the interpreter and a parsed include-system-site-packages=false; missing scaffold goes through existing owned recovery, modified isolation fails closed without overwriting the config.
4. **P2 — output config lacks target containment.** `deployment.py:263-280` checks row targets but not output_config.path; `:475-481` writes to that field. A re-digested edited plan writes a new config outside target and returns COMPLETE. This counterexample needs an edited plan, unlike finding 2 which uses normal build_plan output. Fix: require an absolute target and the exact owned CONFIG_NAME/path.
5. **P2 — old-tool plans silently acquire current-tool attestation.** load_plan accepts a re-digested plan declaring another implementation SHA, while receipt_stub emits the current implementation SHA. Fix: reject a plan whose tool identity differs from this implementation, requiring a new plan. This preserves the tool/plan binding rather than pretending old receipts were produced by the ROOT fix.

All eight new regression tests failed against the corresponding pre-fix behavior. Initial six RED: 6 failed in 1.03s; tool-binding RED: 1 failed in 4.44s; receipt-writer RED: 1 failed in 0.49s. Final command covers all W22 author/reviewer/reception cases plus test_pdf_runtime_environment.py, test_pdf_paragraph_runtime.py, test_pdf_paragraph_alignment.py: **88 passed in 4.38s**. Ruff passed; mypy passed (two files). Final stdout is in integration-green-tests.txt. No heavy E2E was rerun.

## What the existing real evidence proves

- Recomputed the local plan's canonical digest: `498b75554fdab844991c0945d8b781f1ffe31418a89dfba9b4c1a37b7734c482`, equal to deployed receipt. Plan has 0 blockers, 104 distributions, 36,121 env rows plus 6 artifact rows.
- Independently checked **all 36,127 rows** for target existence, samefile(source,target), and planned size: zero failures. Independently rehashed 12 deterministic env samples and all 6 artifact source files (including model.safetensors): all match the plan. This is full link/size coverage plus sampled source hash coverage, not a claim that all 1.4 GB of sources were independently rehashed.
- Traversed actual final tree: zero symlink/junction/reparse points. Real target/env/artifacts are directories. Standard pyvenv.cfg uses C:/Miniconda, Python 3.13.9, include-system-site-packages=false.
- Actual source/output configs differ only in python and artifacts. Source config SHA `bcc427114955f6d045c5848b1885b24f1ec1666d1397bfb60ba4f404a225ff2a`; output config SHA `bd88ad431822b5af0361e9b8fed1e991947a79036b42207126fca61181d6bd22`.
- Deployed receipt and plan tool SHA match author deployment.py `be7dcf3407afd0bc76d8f173954e96ab8722fdfcb909750a67c9875e7c19eab5`. All 14 handoff code_files raw/LF SHAs independently match current author bytes; full list is code-file-sha256.json.
- Actual final deployment logical shared bytes recompute to 1,405,313,714. Prior receipts' scaffold 516,976B is consistent with ordinary venv files; physical allocation remains unmeasured.
- Read complete synthetic E2E and alignment diagnostic implementations/receipts. Real proposals come from actual SDK item provenance; normal native parser creates reading_layout; no fabricated positive geometry or threshold change was found. The final E2E receipt reports enhanced / accepted2 / rejected0 / completed[1,2] / stream_complete, worker 15.9895s and peak 3,329,736,704B, source text preserved, negative mismatch rejected. The separate diagnostic records actual SDK text/bboxes matching the native blocks. Reception did not independently run this SDK execution.
- The real-entry negative test uses wholesale mismatching text, whereas the unit negative test supplies a one-character change with valid geometry. Handoff prose conflates these; rejection evidence exists at both levels, but they are different controls. Synthetic evidence_span_count=0 and replay_verified=0 do not prove real-document recall; ROOT C2 remains outside this card.

## Final commit/review binding and limitations

`2562d3b4..dc423843` has no tool implementation change. The only code-scope additions are the explicit unwritable-receipt regression and an explanatory review-test docstring. The former was run with the current suite; the unchanged production implementation remains the version reviewed at 2562d3b4. Older tested/reviewed_commit fields therefore do not independently invalidate the delivery.

The environment R2 report covers the previous 302bf87d/1cba5f2e tree; the code R3 appendix covers final be7dcf34/498b7555 binding. Those scopes must remain distinct. This reception's independent audit closes final-tree link/hash/config evidence without attributing it to the old environment report. handoff.md still labels old hashes/plan/times as final while handoff.json has the current values; use JSON/current receipt or correct the prose.

ROOT fixes change tool identity. The existing real deployment, its plan, and existing E2E remain evidence for author be7dcf34; they are not retroactively bound to the new ROOT implementation. The new guard intentionally requires a new plan before a future deploy. No real environment rebuild, constructor, or SDK E2E was attempted here; ROOT owns that next acceptance step as appropriate.

Cleanup: owned integration `.p-tmp` was verified to stay under the exact integration root and contain no remaining reparse entries, then removed; restored absent. All temporary junctions were removed by the tests. Author/deployed trees stayed read-only. Author worktree still contains `__pycache__/pdf-paragraph`: **4,199 files / 87,017,586 logical bytes**, with tmp root present. This persistent warm cache is omitted from handoff cleanup and should be explicitly retained/accounted or retired by the owner; reception did not delete it. Old receipts/config/source bytes were not edited.

## Final ROOT edit byte binding

- `C:\Users\郑曾波\Projects\_w22r\tools\pdf_runtime_deployment\deployment.py`: raw `7e818ba766b36e8c7fc612826e728f7aa04cf3aa8b7798f04147264f9d7236e6`, LF `7e818ba766b36e8c7fc612826e728f7aa04cf3aa8b7798f04147264f9d7236e6`.
- `C:\Users\郑曾波\Projects\_w22r\tools\pdf_runtime_deployment\README.md`: raw `a0bbddcfb3add139d274fe2a15b7b08f4fcc136cebc359a2eedb83387ef301b2`, LF `a0bbddcfb3add139d274fe2a15b7b08f4fcc136cebc359a2eedb83387ef301b2`.
- `C:\Users\郑曾波\Projects\_w22r\tests\unit\test_w22_pdf_reception.py`: raw `1e09a5ec71b84381feddecdfe583706006d1dda09217e79498c72bf5d341f84a`, LF `1e09a5ec71b84381feddecdfe583706006d1dda09217e79498c72bf5d341f84a`.

No commit was created. Product edits are limited to tools/pdf_runtime_deployment/deployment.py, its README, and tests/unit/test_w22_pdf_reception.py. Root report artifacts: code-file-sha256.json, final-deployment-readonly-audit.json, readonly_audit.py, integration-fix-sha256.json, integration-green-tests.txt, and this report.

## Final scaffold-byte closure after independent OCR cross-review

OCR cross-review found that checking only existence and isolation could still accept a corrupted interpreter or changed pyvenv home. ROOT explicitly authorized the small root fix. COMPLETE and INCOMPLETE receipts now save SHA-256 for env/Scripts/python.exe and env/pyvenv.cfg. Existing files must match recorded bytes before reuse/recovery; changed scaffold fails without altering the existing marker. Missing files can recover only to the recorded bytes. Legacy COMPLETE receipts without scaffold binding explicitly require verification or a new owned target; no old real deployment or receipt is rewritten to invent that proof.

Two tampered-scaffold cases and an unbound-legacy-receipt case were independently RED (3 failed/0.70s), then GREEN. W22 mechanism scope after the final change: **48 passed/4.06s**, ruff clean, mypy clean (two files), log integration-scaffold-tests.txt. This final step does not claim the earlier 88-case command ran after the scaffold change; existing environment/runtime/alignment source behavior was unchanged. New independent cross-review belongs to OCR agent and ROOT.

The earlier final ROOT byte table above records the pre-scaffold stage. Superseding final byte binding:
- `C:\Users\郑曾波\Projects\_w22r\tools\pdf_runtime_deployment\deployment.py` raw `9487ca8179f422ad562287ed8346156da4572aa31eb7ec176aa5f333ccf8a1b9` / LF `9487ca8179f422ad562287ed8346156da4572aa31eb7ec176aa5f333ccf8a1b9`.
- `C:\Users\郑曾波\Projects\_w22r\tools\pdf_runtime_deployment\README.md` raw `fa64851b2df759c075efd5dc770ca66911038bd3d631192deaf2d2a73a3bc22f` / LF `fa64851b2df759c075efd5dc770ca66911038bd3d631192deaf2d2a73a3bc22f`.
- `C:\Users\郑曾波\Projects\_w22r\tests\unit\test_w22_pdf_reception.py` raw `0206e380715c78b32afb3cb4657c764c53a1e64969e742c26a33e01622e7f0b8` / LF `0206e380715c78b32afb3cb4657c764c53a1e64969e742c26a33e01622e7f0b8`.
