# R7 final core — independent r2 NEEDS_FIXES

Original r1 FAIL report remains unchanged. All16 final SHA were checked. This round ran only4cases: original last/only-location cancellation and deadline nowPASS, known-proof/discovery-budget partial positivePASS, one new default-resolver account controlFAIL (3P1F/1.18s).

## P2: default resolver budget lacks the new check method

`SourceResolver.resolve` defaults to the existing `resolver._ReadBudget` and forwards that account to stored_availability_evidence for sources without published_date. The terminal fix now calls budget.check unconditionally before lookup, but that actual base type has no check method. Even an ordinary missing stored proof raises AttributeError instead of returningNone. This is a real consumer/owner contract mismatch, not a rejected fake source or permission request.

The independent reproduction uses the actual _ReadBudget with30bytes already consumed, the actual public stored owner, and a missing assertion. Existing LocalReadBudget terminal checks are correct; unify the existing base/rich budget check contract without replacing/resetting the parent account or dropping cancellation/deadline. No new budget system, threshold or skip flag.

Exact source/test manifest, caller lines,4case source/log/JUnit are in JSON. No full group, original, model, paid call or source/Git/PWF write. Owned scratch will be restored to absent after preserving this evidence. Root should provide final manifest after the one shared-contract repair for a small independent delta recheck.

Cleanup: 7files/11271.0bytes removed after predelete parent/nonreparsechecks; ownedroot restored absent.
