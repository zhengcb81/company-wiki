# W06-FF-MATRIX: independent final tool review

## Verdict

**TOOL_BLOCKER_CASE_CONTRACT_AUTHORITY_P1. Do not accept the tool freeze yet.**

The original isolation and several false-PASS predicates are repaired. A common
acceptance defect remains: the oracle treats the report's own required-case list,
expected assertions and request vectors as the authority for what should have
been tested. By changing those declarations, omitted or altered required work
can receive a clean oracle result. This is a test-tool defect, not evidence that
a production provider or earnings-transcripts made these artificial mistakes.

The actual unmodified CLI remains honestly **PARTIAL_PRODUCT_FAILURES**: its
41-case report has **19 PASS / 21 FAIL / 1 PARTIAL**, nonzero exit, and 132.5406
seconds. No original FAIL was relabeled. Even after the tool blocker is fixed,
this delivery cannot be called a completed FF→ET→CWP product acceptance.

## Frozen scope

The reviewed root is
`C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root`.
All **20 files** in `fix/freeze-manifest.json` match the supplied SHA/byte records
before and after the first independent probes, and were rechecked after the
second probes. Freeze manifest SHA:
`e098e5bca867a33802d8fcf6945af7370bb092aec13a4397be475244c43e1246`.

The retained ZIP SHA is
`dd8fc402a337ef02b3db456a760162f59129c9e7ae5667c62d281294d903bea3`.
The actual original 41-case report's SHA is
`aa2ab10add76f89e6e259fa0a05c8ad961f562f46b3fd21a1e94c1b2a3acc72f`.
The ZIP, original report and initial independent FAIL evidence are unchanged.
All report/request mutations below exist only in this new review directory or
its newly created temporary child; no producer request was sent for them.

## Three counterexamples of one authority defect

### 1. Omitted required cases can be self-declared away

The independent review copied the actual 41-case report and retained only its
19 genuine PASS cases. It also replaced `required_cases` with those 19 IDs.
Every retained request, response and source-byte proof remained genuine.

Observed: `oracle.audit` returned **zero findings** and `oracle.passes` returned
**True**, despite **22 fixed required cases being omitted**. The exact reduced
report is `omitted-required-22-cases-counterexample.json`; its exact observed
finding list is preserved in `results.json`.

`oracle.audit` checks only `report.required_cases == observed_case_ids`. The
fixed executable registry in `cli_main._case_registry()` contains 41 cases but
is not used as the oracle's acceptance authority. The ordinary CLI itself still
executes that registry and fills interrupted cases with NOT_RUN, so this is not
a claim that the current unmodified CLI accidentally returned exit zero.

### 2. A required assertion can be removed from a fixed case

In a copy of the full actual report, only `call_past_cutoff.expected` was replaced
with `{}`. The original actual response, request, status and case identity were
unchanged.

Observed: the original `wrong_cutoff` finding disappeared. Other genuine
findings remained. The complete copy and before/after finding sets are retained
in `removed-cutoff-expectation-report-copy.json` and `expectation-results.json`.
The oracle's cutoff, unknown-usage and run-twice checks are enabled by mutable
`case.expected` flags rather than the fixed case definition. Thus the omission
problem also concerns the meaning of each retained case.

### 3. A case's request vector is not bound to the fixed case definition

Starting with the 19 genuine PASS-case review copy, the review copied their small
request/response files to its own temporary directory. Only the bound request
for `fin_cn_annual_hit` was changed from its CN company to **HK / Tencent** and
the hash of that copied request was recomputed. The case ID, actual CN response,
CN SourceRef and genuine fresh-byte proof remained unchanged.

Observed: the oracle still returned **zero findings / True**. The exact changed
request, target case, source proof and observed finding list are preserved in
`modified-request-vector.json` and `expectation-results.json`. No altered request
was executed and no old receipt was changed.

The oracle compares kind and period against the same caller-supplied bound
request. It does not compare that request to the fixed case's market/company,
document kind, period or expected scenario. Scenario requirements likewise come
from the case's self-declared flags. Therefore a correct SHA of a report copy
does not prove that the intended test was performed.

## Common repair boundary

Use one executable authority for **case ID → request vector → expected
assertions/scenario → mandatory coverage**. The runner and oracle should consume
that same fixed definition. Coverage must reject omitted, unknown and duplicate
cases; extra entries cannot compensate for an omitted required case. Expected
assertions and relevant request fields must be checked against the definition,
not inferred solely from the report's own declarations.

Keep actual request/response bytes, measured counters, fresh source-byte proof
and honest FAIL/PARTIAL diagnostics. This should be a shared test-tool rule,
not another identity store, authorization file, human sign-off or per-company
exception. The same three retained failures should become focused TDD cases.
Do not modify the current 41 actual case expectations to obtain green results.

## Correctly repaired behavior independently observed

The first bounded run recorded **20 small probes**: 19 meet expectations and
the remaining probe is the newly discovered omitted-case blocker above. It
independently confirms:

- ProductionGuard uses metadata only, with hashing forbidden even for a fake
  key. No production secret or configuration bytes were read by that probe.
- The shared synthetic child environment excludes unrelated fake credentials,
  endpoints and settings; its FMP key is synthetic and its HOME is owned.
- Downloaded Q2 is not accepted for the Q3 negative case; an explicit quarter
  rejection remains a valid control.
- An unrelated upstream failure is not cutoff evidence; explicit cutoff
  rejection remains a valid control.
- Missing SourceRef and another `downloaded_new` result cannot prove reuse.
- Unknown usage cannot be converted to zero. A genuine null usage outcome and
  an explicit failure reason remain a valid control.
- Empty/unbound matrices, missing declared coverage, null run-two counters and
  a declared over-limit batch are rejected by their applicable checks.
- Case deadlines inherit the same absolute batch endpoint and do not reset it.
- Unique OwnedAttempt cleanup preserves preexisting scratch-file, sentinel and
  report bytes. An unverified-binding CLI scaffold returns nonzero and preserves
  those bytes. This scaffold replaces producer calls and is not a real chain.
- Removing genuine fresh reader proofs flags `source_bytes_not_verified`.
  Changing a response self-claim without changing its sealed response file flags
  `invalid_bound_evidence`.
- The actual 41-case report matches the executable registry's 41 IDs; no
  coverage error is present in the original report.

Only the two requested additional pure authority probes were then run. Both
expose the shared new defect; no broader matrix or 645/34-test suite was rerun.

## Product evidence and attribution

The actual 41-case report's 13 fresh source proofs were inspected in the sealed
bundle. `source_proofs.py` actually calls `SourceVersionReader.open_version`,
hashes and measures its returned bytes, counts registered versions, and counts
physical originals. Its proof is stronger than a bare SourceRef or self-filled
boolean. It does not establish supplier reachability or real source factual
qualification; a fixture provider is used.

The US2025 warm primary failed to resolve, so the intended earnings-call stages
in the final matrix do not establish ET retrieval behavior. `fake_layer_claimed_real`,
`wrong_cutoff` and `fake_zero_cost` diagnostics in that report must not be
recast as three proved ET production defects. The independent minimal
cross-period reproduction also has null steady verified fact assertion/payload;
ROOT must diagnose legitimate source registration/setup before attributing a
specific producer algorithm fault. No assertions or fixture metadata were
manufactured in this review.

One optional warm CN2024 FF+CWP public control was attempted in this review's
deep temporary path. Its first child output was not parseable JSON and
`warm_seed` raised JSONDecodeError before the control closed. This observation
is retained as an **uncompleted optional control**, not a producer defect, byte
proof or full-chain PASS. The temporary files were cleaned before stderr was
retained, so its launch/producer cause is unknown. It was not rerun. The source
reader assessment above therefore relies on the existing sealed actual proof
and the independent proof-removal/mutation checks, not a newly completed public
reader replay. This limit is explicit in `optional-public-control-failure.json`.

## Isolation and next owner

Both unique review scratches were absent before execution and absent after
cleanup. Only newly owned paths were removed. All 20 frozen files, original
independent FAIL and bundle remain unchanged. No code, shared PWF, Git, install,
user output, original company document, Dayu or IQS was changed. No live supplier,
HTTP or LLM call occurred; cost is **$0**. Only metadata and designated code/test
evidence were read outside the owned fixture environment.

ROOT has been notified and retains the FF merge hold. ROOT should repair the
common case-definition authority, freeze it and request focused nonauthor
replay. Producer diagnosis and eventual unchanged 41-case product rerun remain
separate work. This review stops here and does not certify product completion.

