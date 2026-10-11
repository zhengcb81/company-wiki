# W06 cutoff result — FF author handoff

**AUTHOR_COMPLETE_PENDING_ROOT_ACCEPTANCE; FROZEN STOP.**

Base: `88997b85ce5be20dc3d563b5c040706590df6dbb`. Independent worktree: `C:\Users\郑曾波\Projects\_harness_worktrees\w06\ff-contract-matrix-root`.

## Root cause and repair
ET correctly excluded a legal requested-period transcript published after the information cutoff but omitted a reason. FF then flattened every non-fetched result into provider_unavailable. ROOT parent owns ET typed date diagnostics; this delivery preserves ordinary not_found and the two additive error codes call_after_as_of / publication_after_as_of. Ordinary/legacy/unknown codes mean exact_transcript_missing. Unknown child strings do not pass through. No cutoff is guessed from zero candidates.

Transport imports only one shared finite vocabulary from the existing test contract module. It does not call that module's validator or introduce another production identity/byte check. Companion and public v2 envelope already preserve status/reason/usage and remain unchanged. No extra provider, import, raw original, grant JSON or canary.

## Delivery / TDD
- Exactly two products plus three responsibility tests; see product-freeze.json.
- Behavioral RED: 23 FAIL / 8 PASS / 77 deselected, pytest1.09s; no import/setup failure used as RED.
- Same test bytes GREEN: 31 PASS / 77 deselected, pytest0.54s. Author did not duplicate the full responsibility node.
- Ruff and git diff --check green; 354 protected files and all original test prefixes unchanged. Unique owned scratch restored; zero real keys/supplier/network/LLM requests.
- Product freeze SHA: `0574664a9634d6ea11a9fa93949c8ea8469a60d013671e97c2015e8e093fa03c`.

## ROOT next action
Once ET producer delivery is ready, run a single concentrated responsibility node in each repository using isolated environment and one short owned scratch:

```powershell
python -B -m pytest -p no:cacheprovider --basetemp <unique-owned-short-scratch> -q tests/test_transcript_launch_contract.py tests/test_transcript_companion_transport.py tests/test_et_s0b_contract.py tests/test_transcript_response_budget.py tests/test_transcript_companion.py
```

Then run the original unchanged 41-case matrix. Product integration is not COMPLETE based on this focused GREEN. ROOT owns acceptance, commit/merge/push/install. Author remains STOP.

Canonical evidence: `C:\Users\郑曾波\Projects\company-wiki\.planning\w06-cross-period-acquisition\cutoff-implementation\ff`. Original frozen tool/test matrix and previous failing receipts remain untouched.
