# CI regression inventory addendum

**PASS, 0 OPEN.** Reviewed two final files and parser-version-gate-green.txt: **9 passed in 1.70 seconds** (6 existing gate meta cases plus 3 added regression nodes). No redundant test/full-suite rerun was performed, as requested. The earlier count RED is retained as history.

The existing CURRENT_CI_REGRESSION_CASES receives exactly three specific function nodes covering legacy TXT layout, actual transcript producer identity and raw-manifest current fallback. AST comparison confirms the old inventory remains in its original order, no whole-module entry is added, and the original FAST_CONTRACT_CASES tuple definition is unchanged. Its expansion grows from 31 to 34 entries. The meta test changes only that expected count and explanatory comment; original assertions remain.

Daily timeout stays 180 seconds, affected-target cap stays 32 and output caps remain unchanged. No affected-file selector, error handling, full-suite trigger or production parser behavior changes. This is a narrow addition of observed failure witnesses to the existing mechanism, not forced full-repository validation.

The current raw SHAs of the three files in ci-parser-fixture-addendum.json still match that seal. Together the two addenda cover all five proposed publication paths.

- `tools/pre_push_gate.py`: raw `6f43247b9667ef46128e263f21cc01b91ace8ded6f3aeac3b3ec15c60c0d2811`; LF `a6f00fbfeb2114e7b916a7c5e0719a46a8a92f9e5b80b6fa17879b22e8183a35`.
- `tests/unit/test_pre_push_gate.py`: raw `7f4bc852df776af304a956870add943d412d997ea1bde9e54be48899d0928eac`; LF `7f4bc852df776af304a956870add943d412d997ea1bde9e54be48899d0928eac`.

This review does not certify a remote CI/full-suite green result, actual normal-push duration, model summary adoption or RF acceptance. No original PDF read, download, SDK/model call or product-file edit was performed by this reviewer.
