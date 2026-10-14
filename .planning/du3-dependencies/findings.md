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

Deriving a decision domain from the **entire** installed reading catalog produces **78
scopes** (the distinct regime/family/purpose tuples declared by all 24 families, over 38
family + facet components), which exceeds the frozen default of `max_scopes=64`. Such a
freeze is `partial` with `SCOPES_LIMIT_REACHED`. This is the concrete, measured reason the
dependency unit must be the **source-local** decision domain: a whole-catalog hash would be
both too strict (every unrelated edit invalidates everything) and, here, unusable. A
source-local domain built from the same real catalog identities freezes `complete` at
2 scopes / 28 components / 9 candidates.

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
