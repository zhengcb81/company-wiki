# F3 implementation handoff — independent review PASS

Branch codex/du11-identity-projection, base a8eef273, managed isolated WT. Different independent reviewer PASS;37tests passed13.20s with frozen bytes unchanged and independent cleanup. No mandatory fixes found. Author commits normally; no push/main merge by author.

## Changes

- New pure security_code owner: HK ASCII1..5 digits →5width; CN ASCII1..6→6width; US ASCII ticker case normalization retains dot/dash class distinctions. Unknown market/namespace/malformed values stay literal. Cross-market identities do not compare equal; absent market cannot be borrowed from request.
- Resolver strict matching shares this owner instead of globally lstrip-zero/casefold. Missing auxiliary identity/period/SHA/as-of ownership unchanged.
- describe_candidate projects canonical source security code; describe_version, current source facts, sidecar/immutable metadata, raw bytes and SourceRef remain observed values. No request field overwrites source facts, new RPC, store or approval.
- Runtime touched only security_code.py, resolver.py and source_reader.py. FF unchanged at f1a939e. No FF/RF author-worktree files touched.

## TDD and actual integration evidence

1. RED7FAIL/19PASS4.95s: real over-width/market-free leading-zero and case aliases plus actual unpadded candidate. No missing-symbol-only RED.
2. GREEN42PASS6.76s:26own+10existing identity-resolver+6existing steady reader.
3. Real external FF CLI suite31PASS13.43s:29own+2 actual subprocess chains. Synthetic official-format master; observed9896/query09896 and observed09896/query9896 both identify→query with2calls/0download. No service/response/identity mock. Socket guard asserts no attempted network. Actual binary reader verifies unchanged bytes/SHA and observed manifest. Same-size synthetic tamper is refused with0bytes; original restored.
4. Final own unit35PASS4.63s adds CN/US/class/unknown projection controls. Ruff5files and git diff --check pass.

All logs/XML stay in this owned plan directory. source-freeze.json binds actual working bytes and normalizedLF hashes (resolver normal Git CRLF checkout). source_reader has historical -text mixed endings; retained original ending bytes and emitted only new lines LF, avoiding full-file churn.

## Cleanup and risks

Fixtures close catalog, remove each owned synthetic lake/config/snapshot/DB/bootstrap in finally, verify sentinel bytes and remove newly created sentinel. Synthetic tamper restored before deletion. No production config/DB, original PDF, key, API/provider/model or external author write. Detailed cleanup claims and error history are in handoff.json/progress.md, not a claim that unrelated pytest historical folders were deleted.

One unreachable draft test mistakenly expected query_local's public CLI candidates dictionary; corrected to typed SourceQueryResult.matches after source inspection. Initial Ruff fixture F811 was fixed by one documented pytest fixture-signature suppression. Exploratory absent filename reads had no effect. Mixed-line-ending check was corrected without changing semantic code.

Independent acceptance: review/independent-review.md/json and XML/log. Still OPEN: owned normal commit and ROOT real HK consumer revalidation without new model POST. Source-business quality F1/F2 and actual model rank F4 remain ROOT work, not closed by identity fix. Discovery security-master aliases are intentionally separate from strict source matching.

Normal hooks passed; implementation commit `310252bd5eb09ff21943ce8053a9ebc6464ccbfc`. Independent reviewed working bytes remain exact; committed blob SHAs (Git newline filters where applicable) recorded in handoff.json. No branch push or mother mutation. ROOT owns merge and real HK consumer-only replay.
