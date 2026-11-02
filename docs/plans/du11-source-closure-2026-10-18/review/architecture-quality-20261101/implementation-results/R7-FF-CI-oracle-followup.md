# FF focused CI stale hook oracle

Status: FIXED_OBSOLETE_TEST_ORACLE_PENDING_EXACT_REMOTE_CI.

Failed run: 41444682305, FF `b35262233c572fef7b4ba85cd24dcab144880b8c`. The public annotation exposed only exit1, so this report does not claim to reconstruct every remote failure.

The installation-surface test still required `--skip-install-sync` after daily push deliberately moved to `--push-checks`. This is a stale policy assertion, not a product regression or a reason to restore full CI to every push. Only that existing test was migrated: assert the fast mode and reject full-CI/full-test/install arguments. No test was removed, runtime changed, budget raised, CI table narrowed or skip added.

The CI compatibility manifest pins CWP `0ccdc6896ee58063ff827e9ceab16043c7550e0c`. Its src only was exported from Git to an owned temporary directory (366 files, 5,288,426 bytes), with `FILING_FETCH_V2_WIKI_SRC` and `PYTHONPATH` pointing there. Raw materials, databases and production configuration were not copied or changed.

Actual reproduction: 1 failed / 0.16 s at the retired hook argument. After the test migration, the complete seven-case installation-surface file plus four relevant pin/inventory/daily/failure-isolation controls passed: 11 passed / 1.07 s. Single-file Ruff passed. All logs and both JUnit files are preserved in the evidence directory.

The original 40-file CI inventory is byte/AST unchanged. Per ROOT's explicit bounded-diagnosis instruction, the full 933-case focused suite was not repeated after a deterministic static failure was reproduced. Only the next normal remote CI can establish whether there were additional failures.

Every FF scripts/*.py byte and the four RF uncommitted assurance artifacts matched their before hashes. No commit, push, credentials, external API, original-document parse or global installation was performed.

Cleanup is recorded in the companion JSON after native removal of the owned temporary pin/test tree. Next action belongs to ROOT: accept this narrow delta, commit/push normally, inspect the exact resulting CI and use minimum-node diagnosis for any residual failure.
