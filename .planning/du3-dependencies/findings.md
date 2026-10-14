# Findings — du3-dependencies

## 1. What the component is, and the one question it answers

`freeze_decision_dependencies` / `compare_decision_dependencies` answer exactly one
question: *is the source-local selection decision still the same decision?* The card's
premise is that hashing only the payload finally sent to the model cannot justify a
selection cache, because a component that **participated but lost** can win next time
after its priority or matching signals move. The manifest therefore freezes the decision,
not its outcome: scopes (parent + child), every inspected component including
unmatched/losing ones, the full candidate membership with eligibility, and the adopted
algorithm versions.

`same` is **not** a cache hit. ROOT still performs the original-text/locator read check and
owns the AUTO Store/CAS decision.

## 2. Error-handling split (derived from the card, applied consistently)

The card draws a line between two kinds of bad input and the implementation keeps it
exactly:

| input condition | `freeze` | `compare` |
|---|---|---|
| wrong type (not a mapping; wrong field type) | **raise** | **raise** |
| duplicate id, same id different content, repeated reference | **raise** | **raise** |
| dangling scope/component reference | **raise** | **raise** |
| digest not a full 64-char lowercase SHA-256 | **raise** | **raise** |
| `versions` key naming a runtime setting / secret handle | **raise** | **raise** |
| unknown or missing `schema_version` (legacy artefact) | `partial` + diagnostic | `unavailable` |
| `trace is None` (old path recorded no decision at all) | `partial` + `MISSING_TRACE` | `unavailable` |
| `inventory_complete` missing / false | `partial` + `INVENTORY_UNKNOWN` / `INVENTORY_INCOMPLETE` | `unavailable` |
| no candidate membership recorded | `partial` + `MISSING_CANDIDATES` | `unavailable` |
| work / byte / row budget reached | `partial` + `*_LIMIT_REACHED` | `unavailable` |
| everything complete and equal | `complete` | `same` |
| content / membership / scope / version moved | `complete` | `changed` |

Rationale: DU3/1 says real data errors are **rejected** ("相同ID不同内容冲突、错误类型、
悬空引用明确拒绝，不静默去重/截断后给same") while unknown or missing items **explicitly
return a diagnostic** ("未知/缺项显式返回诊断，不猜业务事实") and legacy/incomplete/budget
cases return `unavailable`/`partial`. Nothing in the right-hand column can degrade into
`same`.

One asymmetry is deliberate and is the difference between an *assertion* and a *record*:

* a **caller-supplied `du-decision-trace/1`** is an assertion that the wire contract holds,
  so a structural violation raises `DecisionTraceError`;
* a **stored `du-decision-dependencies/1` manifest** is a record that may come from another
  build or may have been touched since it was written, so anything that makes it unusable
  -- an unknown or missing field, a duplicate id, a dangling or repeated reference, a
  malformed digest, a wrong-typed row, or a `decision_digest` that no longer matches its
  own rows -- returns `unavailable` with a diagnostic naming the problem.

Both are equally incapable of producing `same`. The second path reports instead of raising
because a cache precheck that crashes on an old record is worse than one that honestly
says "cannot tell" and recomputes.

## 3. Design decisions worth ROOT's attention

1. **`inventory_complete` is the one optional field of a declared `du-decision-trace/1`.**
   It is the caller's attestation about *external* completeness, which this package cannot
   see. Its absence is itself the honest signal "not asserted", so it is reported rather
   than rejected. Everything else in the declared `/1` structure is a contract.

2. **A decision domain with zero candidate membership can never freeze `complete`.**
   Whatever the caller attests, such a domain recorded nothing reusable and nothing
   comparable. This is the detectable shape of a "winners only" trace, and blocking it is
   the strongest anti-laundering lever available inside the input.

3. **Uncertifiable external omission — documented, per the card.** If a caller asserts
   `inventory_complete: true` while genuinely leaving participants out, this package
   cannot detect it: the trace is the only evidence, and there is no catalog read to
   cross-check against. The card explicitly asks for this to be documented rather than
   papered over. ROOT's instrumentation is the place where completeness is actually
   established.

4. **The manifest key set is closed**, so there is no slot for a path, run id, clock value,
   cost, timeout or API-key/env name. The one caller-supplied map (`versions`) is screened
   by name against `NON_CONTENT_FIELD_NAMES`, so those cannot be smuggled in as an
   "algorithm version" either. No policy body, document text, DOM or unit list is
   representable — asserted in the B node against a real catalog policy phrase.

5. **Array order is not identity.** Rows are sorted by id and reference lists are compared
   as sets; a repeated reference inside one row is a caller error and is rejected rather
   than silently collapsed (that is the card's "不静默去重").

6. **Every loop is charged against `max_work_units`**, and the row/byte caps are separate.
   A tight but non-zero budget still stops and still reports; it never produces a
   half-walked `complete`.

## 4. Real finding from the C node (not synthetic)

Deriving a decision domain from the **entire** installed reading catalog produces **126
scopes** (the distinct regime/family/form/purpose tuples declared by all 24 families, over
38 family + facet components), which exceeds the frozen default of `max_scopes=64`. Such a
freeze is `partial` with `SCOPES_LIMIT_REACHED`. This is the concrete, measured reason the
dependency unit must be the **source-local** decision domain: a whole-catalog hash would be
both too strict (every unrelated edit invalidates everything) and, here, unusable. A
source-local domain built from the same real catalog identities freezes `complete` at
2 scopes / 28 components / 9 candidates.

The count is worth a note because it moved during review. The first version of the C-node
fixture derived scope ids from (regime, family, purpose) and dropped `form_type`; the real
catalog declares several forms under one such tuple (a '6-K' and an '8-K' event update, four
lifecycle-overlay revisions), so the ids collided and the de-duplication silently discarded
54 of the 132 applies rows -- which is where an earlier "78 scopes" figure came from. With
`form_type` in the id, 126 distinct scopes remain and the only collapse left is of genuinely
identical tuples.

## 5. Corrections made during TDD (kept, not deleted)

Three A-node assertions were corrected after the first green run because they read the
card more strictly than DU3/1 states:

* an unsupported or missing `schema_version` was asserted to *raise*; DU3/1 says unknown
  or missing items return an explicit diagnostic. It is now `partial` + `unavailable`.
* a `None` trace was asserted to *raise*; the card lists `缺trace` alongside
  legacy/incomplete/budget as an `unavailable`/`partial` case. It is now `partial`.
* `test_an_unknown_wire_field_is_rejected` and the strict row structure stayed as they
  were — a stray field inside a declared `/1` is a real data error and is rejected.

Two test-side bugs were also fixed (a fixture component id computed without a modulo;
a case that compared a legitimately valid empty manifest as if it were invalid). No
assertion about the component was weakened to make a test pass.

## 6. Scope and raw preservation

* `git status` shows only the four owned paths; `git diff --name-only <base>...HEAD` was
  empty before the first commit because nothing outside the owned paths was touched.
* The installed `reading_catalog.json` was read only; its SHA-256 is recorded in the C
  receipt and is identical before and after the replay.
* No company original, production config, database, model call, network call or
  installation action was used. No authorization, sign-off or canary file was created.
* The public surface is exactly the two frozen functions; an AST check proves the package
  imports no selector, registry, Store, source_catalog, automation, filesystem, clock or
  network facility.

## 7. Interface deviations

None against DU3/1's "决策依赖组件" section. One addition is purely defensive and does not
change any frozen field: `freeze`/`compare` reject a `versions` key that names a runtime
setting or secret handle, which is how the card's "不把API密钥/env名、路径、run ID、当前
时间、费用/timeout等非内容字段纳入manifest" is enforced on the only caller-supplied map.

## 8. Independent review (two agents) and what it changed

Two independent reviewers -- one checking the card and interface requirement by
requirement, one reading the code adversarially -- were run after the first commit. They
were not shown my own conclusions. Their verdict on the committed state was
**"not acceptable as-is; acceptable after one fix commit and a clean tree"**. Everything
they found that was real has been fixed and pinned with a counter-example:

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | `compare`'s manifest-vs-manifest path silently de-duplicated duplicate component ids, accepted dangling references, raised `AttributeError` on wrong-typed rows and never verified `decision_digest` — all able to yield `same` on a malformed record | MAJOR | fixed + counter-examples |
| 2 | `decode_trace` walked the whole input with **no** budget charged, so `max_work_units` did not bound decode and `max_input_bytes` never bounded the input at all | MAJOR | fixed + counter-examples |
| 3 | `NO_PARTICIPATING_COMPONENT` did not block `complete` | MINOR | fixed + counter-example |
| 4 | the package docstring overstated what shape diagnostics catch about a forged winners-only inventory | MINOR | rewritten to the exact limit |
| 5 | handoff line counts were wrong | MINOR | corrected to measured values |
| 6 | one handoff sentence mislabelled the regression scope | MINOR | corrected (496/17 for the five pre-existing packages) |
| 7 | the AST import deny-list omitted the two sibling DU3 packages | MINOR | added |
| 8 | the `contract.py` comment overstated what `max_input_bytes` accounting measures | MINOR | corrected to describe the accounting actually used |
| 9 | `max_input_bytes` was **bypassable**: accounting sampled a subset of each row (`form_type`, both digests and the reference lists went uncharged), so a 35 KB input froze `complete` under a 25 KB cap — a 1.95x undercount | MAJOR | fixed: bytes are charged on the real canonical encoding of every row |
| 10 | `_reference_list` de-duplicated with a list scan, O(n²) inside a nominally bounded call | MAJOR→minor | fixed: set-based, linear |
| 11 | `compare`'s index/sort/set-diff pre-passes ran uncharged before the first `budget.charge()` | MINOR | fixed: every row charged while indexing, diffs charged by size |
| 12 | `decision_digest` used `.get()` defaults, so missing arrays collided with empty ones, and it was row-order sensitive while `compare` is order-insensitive | MINOR | fixed: exact identity fields required (raises otherwise) and rows sorted before hashing |
| 13 | `compare` validated `limits` only on some routes, so a bad limits mapping raised on one path and returned `unavailable` on another | MINOR | fixed: validated before any verdict path |
| 14 | the AST import guard was defeatable by `from parent import forbidden_child` and by `__import__()` | MINOR | fixed: imported names and dynamic-import calls are checked, with synthetic-offender counter-tests |
| 15 | `decision_digest`'s coverage of `versions`/`scopes`/`candidates` was unproven — two mutants deleting those payload fields still passed all 111 tests | MAJOR (test gap) | fixed: one digest-sensitivity assertion per identity class + a candidate add/remove case |
| 16 | the manifest-vs-manifest `changed` route had no test at all; one cross-process test never crossed a process; one assertion was tautological; `walk_scalars` was dead | MINOR | fixed: manifest-vs-manifest mutation matrix added, tests corrected, dead code removed |
| 17 | C-node fixture: `scope_id_for` dropped `form_type`, colliding 20 real scope ids and silently discarding 54 of 132 applies rows; `winners` mixed family ids with profile ids | NIT | fixed: identity includes `form_type`, `winners` is profile ids, and the facet population is documented as deliberately unreferenced |

Two findings were **accepted without changing behaviour**, and the reason is recorded here
rather than hidden:

* *RED-first is evidenced by a receipt, not by separate commits*, because tests and
  implementation landed in one commit. `evidence/a_red.json` records the original
  `51 failed` run and the three post-RED assertion corrections, and the reviewer
  independently confirmed the suite fails without the package.
* *A fully-shaped forged winners-only trace that omits participants and still asserts
  `inventory_complete: true` is not detectable from inside the input.* That is exactly the
  card's "不可认证的外部漏报", which the card asks to be documented rather than papered over.
  What the component *can* and now does catch are the degenerate shapes -- no candidate
  membership at all, and inspected components no candidate ever references -- both of
  which are refused as `complete`. The remainder is ROOT's instrumentation to establish.

### Re-verification

Both reviewers were asked to re-check the fix commit against their own reproductions, and
both did so independently of my tests. The acceptance reviewer ran 12 fresh adversarial
probes and returned **ACCEPTABLE, defects 1-8 all genuinely closed**, with four residual
items: a dirty tree during the fix (since committed), one imprecise docstring sentence,
duplicated per-node timings that drift between runs, and an under-pinned scope count in the
C replay. All four are cleared -- the docstring states the record-vs-assertion split
exactly, `nodes.json` is declared the single timing source, the C replay pins the scope
count against the snapshot's own distinct applies tuples (the exact regression that
produced the old "78"), and the tree is committed and clean.

The adversarial reviewer re-ran every original reproduction and **all three digest
mutants** -- which now fail, where they previously passed 111/111 -- and confirmed D-A
through D-L closed with no regression and no migration break (a manifest produced by the
old code still verifies under the new compare). It also found four residuals, all of which
are now fixed and pinned:

| # | Residual | Status |
|---|---|---|
| R1 | the manifest **validation** pass (field checks, reference checks and the `decision_digest` re-derive) ran uncharged before the diff, and its reference check was quadratic — 2x300k-row compare with `max_work_units=1` cost 4.321 s on the fix commit, *worse* than the 0.274 s it was meant to improve | fixed: validation is charged to the same budget and the reference check is set-based. 300k-row compare now returns `unavailable` in 0.000 s; 20 000 references validate in 0.234 s |
| R2 | the per-row byte envelope was charged once per **reference**, so a 100 KB trace stopped fitting a 2 MiB cap — a ~20x shrink of the published budget for reference-heavy inputs | fixed: the envelope is charged once per row and the row's canonical encoding carries the references. A 135 KB / 12 000-reference trace freezes `complete` at 6.5% of the cap |
| R3 | `decision_digest` silently skipped non-mapping rows, so `components=['garbage', 42]` hashed the same as `components=[]` | fixed: `ValueError` |
| R4 | manifest scope rows were not type-checked beyond the id | fixed: `regime`/`family`/`purpose` are non-empty strings, `form_type` null-or-string, matching the trace side |

R1 and R2 are worth recording because they were **regressions introduced by my own first
fix** -- the reviewer's point that "charging more" is not the same as "charging correctly".
Both are now covered by counter-examples (`test_the_manifest_validation_pass_is_charged_too`,
`test_the_manifest_reference_check_is_linear`,
`test_a_reference_heavy_trace_still_fits_the_published_byte_budget`,
`test_decision_digest_refuses_rows_that_are_not_mappings`,
`test_a_manifest_scope_row_with_a_wrong_typed_field_is_unavailable`).

### Final pass

The adversarial reviewer's last verdict: **good to hand to ROOT** -- R1-R4 closed by
reproduction, no regression, no new defect, and cross-version compatible (a manifest built
by the previous commit verifies under the current compare, and losing participants are
still caught through an old record). All three digest/import mutants remain killed.

It left two observations, both conservative and inside the documented contract. Both are
now fixed rather than handed on:

* *Compare was a stricter gate than freeze.* Each row was byte-charged on three passes
  (validation, index, diff), so a domain that froze `complete` could still never compare
  `same` -- a 456 KB trace froze complete yet compare returned `unavailable`. Rows are now
  byte-measured **once**, in the validation pass; the index and diff passes charge work
  only. Freeze and compare now agree: a 260 KB domain freezes `complete` and compares
  `same`, and the boundary is where freeze itself stops.
* *Two wording paths.* A budget stop was described as "while diffing" even when it
  happened during validation, and a stop inside the digest recompute surfaced as
  `FROZEN_NOT_A_DECISION_MANIFEST`. Both now report the budget reason.

Pinned by `test_a_domain_that_freezes_complete_also_compares_same_at_the_same_limits`.

### Measured effect of the fixes

Every line below is a re-run of the reviewer's own reproduction, not a paraphrase.

| probe | before | after |
|---|---|---|
| 60 000 rows, `max_work_units=1` | 0.665 s of real work | 0.073 s, stops immediately |
| 40 000 rows / >2 MiB input, default limits | fully decoded, 1.76 s | 0.053 s, `BYTES_LIMIT_REACHED` |
| 35 KB input under a 25 KB `max_input_bytes` | `complete` (1.95x undercount) | `partial`, `BYTES_LIMIT_REACHED` |
| 9 000 references, zero budget | 0.45 s (quadratic scan) | 0.006 s (linear) |
| 60 000-row manifest vs itself, `max_work_units=1` | 0.25 s uncharged | 0.000 s, `unavailable` |
| `compare(frozen, frozen + {"junk": ...})` | `same` | `unavailable` |
| manifest with a duplicated component id | `same` | `unavailable` |
| manifest with contradictory rows + stale digest | `same` | `unavailable` |
| manifest with a dangling reference | `same` | `unavailable` |
| manifest row that is a string | `AttributeError` | `unavailable` |
| manifest with a stale `decision_digest` | accepted | `unavailable` |
| manifest row values `1` vs `True`, `[1]` vs `["1"]` | `same` | rejected |
| permuted manifest rows | `compare: same` but digests differ | `compare: same` and digests equal |
| `decision_digest({})` | silent empty default | `ValueError` |
| `compare(..., limits={"bogus": 1})` on a short-circuit route | `unavailable` | `ValueError` |
| `from company_wiki.document_understanding import profiles` in a package module | guard passed | guard fails |
| `__import__("os")` in a package module | guard passed | guard fails |
| components referenced by no candidate | `complete` | `partial` |
| digest mutants dropping `versions` / `scopes`+`candidates` from the payload | 111/111 still passed | pinned by per-class digest assertions |
| whole-catalog decision domain | 78 scopes (54 rows silently discarded) | 126 scopes, 38 components |
