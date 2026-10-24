# Publication delta independent review

1. Source changes pass458 cases including the whole du11_source_quality suite and8 additional neutral guards. Restoring number-word periods retains actual same-contract conversion; unrelated actor/obligation controls remain negative. Source-owned operating_description_unknown becomes valuable without any new actual-state assertion.
2. Recovery fixture changed only max_seconds request allowance30→90; all25 assertion ASTs are identical to HEAD, modelHTTP5s and CLI45s unchanged.
3. Sandboxed run458P/2F: isolated10.52s reproduction shows zero requests reaching loopback, matching existing PWF Windows10013 diagnosis. Archived sandbox-* and isolated-lifecycle.*.
4. Same frozen bytes outside sandbox459P/1F: v4 realPOST/recovery succeeds; v3 first paid fixturePOST succeeds but CLI recovery returns BATCH_REQUEST_CHANGED. This is not the90-second allowance or network.
5. Shared cause proven by pure roundtrip: dataclasses.replace(max_seconds=90) has int90 in to_dict; from_dict normalizes to float90.0; canonical hashes differ. max_seconds90.0 roundtrips exactly. Appropriate fix is request owner canonical numeric semantics, preserving existing normalized historical float bytes and meaningful changed-budget refusal. Evidence seconds-type-roundtrip-diagnosis.json. No assertions should be removed.

Current status CHANGES_REQUIRED pending request-owner canonicalization and fresh exact-byte runtime recovery verification. Original410 evidence untouched.

## Closure

Request-owner float serialization fixed the numeric representation drift. Final non-sandbox canonical/request/real-loopback tests30P20.77s. Source458P preserved on identical source-owner byte hashes. Final374-filetree6215a49d...stable; all25 lifecycle assertions retained. final-report.md/json nowPASS within declared scope.
