# W08 legacy selector compatibility fix — independent review

Date: 2026-10-24 UTC  
Review type: read-only code and regression review

## Conclusion

No remaining compatibility blocker. Explicit selector versions 0.6.0/0.7.0/0.7.1 use the frozen legacy detector and join; current selector 0.8 keeps its pre-change group detector and expanded join; 0.9 continues through its separate reader path. Candidate scoring continues to use the version-appropriate candidate rules.

## Review evidence

- Review base: `2d92a00c32c7f6db30f4ebdb32104b43e73ed56b` plus the uncommitted `narrative_evidence.py` compatibility routing change.
- `src/company_wiki/source_catalog/narrative_evidence.py` SHA-256: `6375ad3ba6aa2e7aba66e9c7ffe33ea2e78ba01325cdfb79a83264f607dce840`.
- `tests/unit/test_n6_candidate_recall.py` SHA-256: `36671178332fd8a0bc9d2c14a46ae33f21029612dcb64c5ac6ac9fcb449d9a97`.
- Independent run: three pinned legacy fingerprints plus six facet-version boundary cases, 9 passed.
- Root runner test bundle after routing correction: 11 related files, 478 passed; Ruff passed; mypy passed for 372 source files.

## Finding and disposition

The preceding pre-push found that the legacy detector had been passed to current 0.8 group expansion, changing product-context selection and allowing unrelated adjacent-page products to be grouped. The change now routes only 0.6/0.7 through the frozen legacy detector; 0.8 retains the prior `detect_operating_fact` group behavior. The two reproduced tests pass after the correction.

No gold fingerprints or assertions were changed. The normal pre-push and remote CI remain required before publication.
