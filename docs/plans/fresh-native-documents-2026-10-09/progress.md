# W05 progress

2026-10-09: accepted exclusive worktree; read frozen IMPLEMENTATION W05 and RC08/RC27 matrix proofs. Initial source discovery via CodeGraph then Git for absent indexed files. No source implementation/test yet.

TDD first run: 14FAIL/4PASS0.79s; raw originals not touched. DOCX implementation run11PASS/1FAIL0.41s exposed new test interface mistake: EvidenceCoordinates already forbids paragraph+table combination. Corrected design/test to cell_paragraph_index in versioned source_locator/metadata with existing table coordinate schema intact. This is a new contract design correction, not relaxation of an existing assertion.

First true original read exposed non-person Trace Id promotion (firstbodyline2), despite18 synthetics GREEN. AddedRED1FAIL6PASS to cover page title + trace ID + navbar. Tightening only structural person/role labels; no issuer names/allowlist. First grouped run aborted6collectionERROR due old normalization tests importing bare conftest colliding with contract conftest; retain log and run existing packages in separate pytest processes without modifying unrelated test framework/CI.

Normalization-only95PASS8.80s. Shared pipeline first48FAIL/176PASS48.63s traced mostly to my mechanical import/return edit returning3 tuple values instead of2; fixed implementation. Two old transcript-version assertions updated to explicit new transcript version (PDF0.1.1 remains), and old0.1.1 replay will be asserted separately. No old evidence/metadata/byte requirements weakened.


Final real-original observation caught one more loss: closing `Thank you.` followed by operator direction was mistaken for a bare speaker label and truncated at line411. Added generic closing-courtesy RED1FAIL9PASS, fixed valid-person proof in speaker_fields, and whole original now reads lines90–414. Final record keeps the earlier defective observation separately.

Native inline Q/A and vanish=false RED2FAIL21PASS fixed without weakening role or locator rules. Reply-label RED1FAIL17PASS fixed `答复` as management. Source ordinal / unsupported table wrapper RED2FAIL18PASS fixed original ordinal reservation and explicit named coverage diagnostics. Final normalization103PASS9.83s.

Actual official-import CLI → configured finite batch → isolated subprocess Workers → loopback model → public reference/read/replay → idempotent rerun → original-byte check → test-directory baseline restore:1PASS10.34s initially, included in grouped243PASS72.50s. Initial failures were synthetic fixture QA first-span choice (analyst question cannot be company claim), missing OS USERPROFILE in isolated env, and missing strict Config search/root fields. Tests now retain real strict configuration and role assertions. No model caller/config/summary implementation changed.

All external/paid calls0. Raw original SHA+mtime unchanged; no mFresh/sealed/input mutation. New normalized text and DOCX ZIP material stay in memory; only selected existing narrative artifact format is persisted by the ordinary Worker in its temporary test catalog. TemporaryDirectory cleanup includes failed assertions and successful restore baseline; no package extraction directories.

Latest native unit/CLI E2E4PASS11.89s, focused ruff clean, existing evidence/language mypy2files clean, diff-check clean, cwW05 TEMP remaining0. Normal commit next with repository hooks; MAIN owns exact commit acceptance/install/M3.
