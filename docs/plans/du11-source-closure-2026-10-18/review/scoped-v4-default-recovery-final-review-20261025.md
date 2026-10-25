# Scoped v4 default and paid-response recovery — final independent review

## Verdict

**PASS — no P0–P2 findings.** This is a read-only source review. The reviewer did not run tests or make provider calls; validation evidence is recorded separately in `CURRENT_STATUS.json` and `progress.md`.

## Exact binding

- Reviewed HEAD: `023252eaf3c9f8a7672d42b5e944e967e5ec49b2`
- `git diff --binary HEAD` SHA-256: `06a7970f4e4bad875ae0f2dd6d72e476687e901dbe16490496d1662a62ff884d`
- Untracked fixture `tests/support/scoped_model_response.py` SHA-256: `ce1642e89fc08b127dc4deeb6303ce617db84351b5f4459736687ecef53a033f`
- Reviewer excluded the pre-existing `.githooks/pre-push` file-mode-only change from the technical verdict; it was not modified or staged as part of this change.

## Reviewed behavior

- Selector `0.9.0` defaults to `reading-model-input/4` task-scoped summaries; explicit v5 remains ranking compatibility.
- Both v4 and v5 preserve complete paid responses and support exact, no-second-POST recovery.
- Persistent-space preflight reserves response bytes plus the pin for omitted/v4 requests; explicit v5 additionally reserves `EXECUTION_MAX_BYTES`. The unit test checks the exact threshold and the one-byte-under rejection.
- Phase C defaults, holdout request/observer schema, live README example, and PWF state agree with the v4 default.
- Semantic summary quality, source coverage, and RF consumption remain open; deterministic protocol tests are not represented as content acceptance.

## Prior review findings

The earlier review found two P2 consistency issues: the live README example forced v5, and v4/omitted preflight reserved v5-only execution-report capacity. Both were corrected and reviewed in the exact binding above. No new P0–P2 findings remain.
