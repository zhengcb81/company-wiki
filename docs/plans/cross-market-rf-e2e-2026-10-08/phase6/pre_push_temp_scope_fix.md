# Pre-push scratch decoupling (2026-10-09)

## Actual root

The company-pool candidate push failed before pytest ran: tools/pre_push_gate.py always placed temporary state under PROJECT_ROOT/tmp, then rejected any path over60 characters. A valid managed worktree is deeper than a primary checkout. Its placement became a false test-failure/license requirement, although the repository conftest already owns Windows relocation. The gate further reparsed that diagnostic and required relocation=false and a matching path as an extra success condition. This couples tooling to checkout layout and can reject an otherwise successful relocated suite.

## TDD and change

Three behavior cases first RED3/3: deep checkout with real Python child exit0, real child exit7, and owned transport-timeout cleanup. The old gate returned1 without launching the child and created checkout/tmp. New tests record the actual allocated path, verify it is absent afterward, preserve original checkout sentinel, and check true returncodes/exception. GREEN3/3,0.44s, Ruff PASS.

Implementation removes the repository-local temp root, fixed60-character rejection and redundant decision-log permission parsing. Each gate invocation uses an owned system TemporaryDirectory, cleaned on success/failure/timeout. The real pytest returncode remains authoritative. Existing conftest Windows placement/cleanup logic is retained as runtime support; no test removed, no download/identity/budget/source condition changed, no skip hook or permission variable introduced.

## Milestone

MAIN runs the unchanged curated fast contract set on the original failing managed worktree and the real push hook before publication. Candidate source/narrative proofs remain separate; this is engineering context, not NVDA quality approval. Subsequent explicit milestone wrappers use short owned TemporaryDirectory so they restore their initial state. No production writes, original deletion, supplier calls or fees.
