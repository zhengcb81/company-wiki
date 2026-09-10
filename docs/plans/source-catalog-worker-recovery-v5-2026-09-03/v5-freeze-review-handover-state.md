# V5-3 handover — independent review of frozen state & verification fidelity

Axis: **frozen-state & verification fidelity** (independent re-derivation; no author claims trusted).
Reviewer role: independent reviewer, did not author any reviewed artifact.
Repo: `C:\Users\郑曾波\Projects\company-wiki`, HEAD `1a992cd`, branch worktree as-is (one uncommitted author edit to `v5-freeze-record.md` §8 + one untracked sibling review file created concurrently at 2026-09-10 20:39:22).
Plan dir: `docs/plans/source-catalog-worker-recovery-v5-2026-09-03`.
Measurements taken 2026-09-10 20:2x–20:40 local (UTC+1). Python 3.13.9 (Anaconda), Windows/pwsh. All temp artifacts under `%TEMP%\v5review\`. **No file in the repo was created, modified or deleted by this review** other than this report.

## Verdict

**`accepted_with_findings`**

No P0/P1. The frozen artifact, the manifest bindings, the isolation guard, the worktree↔HEAD↔freeze-commit identity of all 52 bound paths, and the new §8 SQL-OBS-3 structural-block claim all reproduce independently and exactly. The findings are documentation-fidelity defects (2×P2, 3×P3) that do not invalidate the freeze; one P3 (HDS-P3-1) is *unfixable inside generation v5* because it lives in manifest-bound bytes.

## Verification results (task-by-task)

| Task | Result |
|---|---|
| 1. triple re-run vs README §2 | default `PASS: 7720 checks` exit 0 (172 B) ✓; `--verify-manifest` `PASS: 9188 checks` exit 0 ✓; `--self-test` `17 cases / 32 mutations + 4 default-mode checks + 3 guard checks; failures=none` exit 0 ✓ — **except the literal JSON rendering** of the default line (HDS-P2-1) |
| 2. frozen artifact | 172 bytes, **0 CR**, sha256 `5e60611c…ad83`, and **byte-identical** (`filecmp.cmp(..., shallow=False) is True`, `a == b` True) to a fresh default-mode stdout captured to `%TEMP%` ✓ |
| 3. isolation guard | `python <checker>` (no `-I`) → **exit 1**, stdout **0 bytes**, stderr `FAIL: run with an isolated interpreter - \`python -I <checker>\`.` — **no PASS line** ✓ |
| 4. manifest binds the frozen set | 51/51 recomputed sha256+size match; manifest self-excluded; manifest+51 = 52 paths all tracked, `git hash-object` == `git ls-tree -r HEAD` blob for 52/52; `evidence`, `evidence_tools`, `capture_manifest`, `supersedes`, `investigation_source`, `boundary_record` all match their files ✓ |
| 5. §8 SQL-OBS-3 row | claimed block is **REAL** — both routes empirically blocked; the row's `~90s / zero repo writes / all under %TEMP%` claims hold (measured 73.6 s and 72.4 s; 0 repo writes incl. `.git`). Two wording precision notes (HDS-P3-2, HDS-P3-3) |
| 6. drift | **No frozen byte has changed**: all 52 bound paths are blob-identical between HEAD and the freeze-products commit `4f4dea1`, and **0 commits** touched any frozen path since `4f4dea1`. All §1 hash claims re-verified correct (including the one not covered by the manifest). Drift found only in *prose* claims (HDS-P2-2, HDS-P2-3, HDS-P3-1) |

Extra independent checks passed: retired-copy inventory recomputes to `38 / da927ee2…c81b` (N9 payload); both evidence tools `--check` exit 0; all six referenced commits (`454f632`, `917b8d8`, `9418e72`, `89c0862`, `436ecd3`, `4f4dea1`) exist and are ancestors of HEAD; `PINNED_HISTORY_SHA256` (6 files) is exercised by the passing default run; default mode still reproduces the frozen bytes at 20:40:29 **after** a concurrent sibling file appeared in the plan directory (so an untracked active doc does not disturb the artifact).

## Findings

| ID | Severity | Finding | Evidence (command + observed output) | Required fix |
|---|---|---|---|---|
| HDS-P2-1 | P2 | README §2 (and `v5-freeze-record.md` §2/B2/§5, `v5-freeze-boundary.md` §freeze-time) quote the expected default-mode PASS line with **non-literal JSON**: no space after the colons. The real and frozen stdout renders `json.dumps(..., sort_keys=True)`, i.e. `": "` separated. A verifier doing a literal string compare of README §2's quoted expectation against stdout/`plan_freeze_check.v5.txt` gets a mismatch; only the byte/sha256 claim in the same bullet holds. | `python -I …/tools/v5_plan_consistency_check.py` → `'PASS: 7720 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}\nREAD_ONLY: no production database, registry, process, source, config, or network access\n'` vs README line 36 ``PASS: 7720 checks; {"fixed_nodes":115,"schemas":29,"tests":315,"vectors":18}`` | Rewrite the README §2 (and record §2/§3, boundary §freeze-time) quotation to the literal bytes, or explicitly mark it as a normalized rendering and point at `plan_freeze_check.v5.txt` + sha256 as the anchor. Docs only — no frozen byte changes. |
| HDS-P2-2 | P2 | Freeze-head identifiers are inconsistent across the audited set: `v5-freeze-record.md` §2/B6 states 冻结时点 HEAD `9418e72` (that is the **V5-2.2** commit `plan(v5): V5-2.2 close the 2 new P1 findings…`), contradicting the same record's line 4 (`89c0862d…`) and the manifest's `plan_freeze_git_head` (`89c0862d9a8b0fc9cc1edb0e243aa6aa39845b40`). README §2 additionally uses the shorthand “冻结 `4f4dea1`”, which is the commit where the *products were committed*, not the declared freeze head — the distinction is nowhere stated. | `git log -1 --format='%h %ci %s' 89c0862` → `89c0862 2026-09-09 22:27:46 +0100 plan(v5): V5-2.3 close 3 P1s…`; `… 9418e72` → `9418e72 … plan(v5): V5-2.2 close the 2 new P1 findings…`; manifest `plan_freeze_git_head = 89c0862d…`; blob compare shows all 52 bound paths are byte-identical at `4f4dea1` and 2 of them (checker, manifest) differ at `89c0862` | Correct B6 to `89c0862d` and add one line distinguishing “freeze-time HEAD (`plan_freeze_git_head`, 89c0862)” from “commit that first contains the frozen products (4f4dea1)”. Record is declared non-anchor and correctable in-generation. |
| HDS-P2-3 | P2 | `v5-freeze-record.md` §2 (“后冻结复验… + 2 守卫检查”) and §3 (“另有 4 项默认模式检查与 2 项守卫检查”) still state **2** guard checks, contradicting the actual self-test output (3), the same record's line 15 (“+ 3 守卫检查”) and §3 table (GUARD / GUARD-I / GUARD-M = 3 rows), and README §2. Stale from V5-2.3; GUARD-M was added in V5-2.4 (D17). | `python -I … --self-test` last line → `SELF-TEST: 17 cases / 32 mutations + 4 default-mode checks + 3 guard checks; failures=none`; three `SELF-TEST GUARD…PASS` lines | Update both occurrences to 3 in `v5-freeze-record.md` (non-anchor record). |
| HDS-P3-1 | P3 | `v5-freeze-boundary.md` — whose bytes **are** manifest-bound (`boundary_record.sha256 = 5e939d46…`) — contains stale frozen-time values a verifier may misread as current: “`--self-test` 17 例 / **27** 个变异” (today: 32 + 4 + 3), freeze-time HEAD `436ecd3…` (that is the V5-1 commit; the manifest binds `89c0862d`), and “`git ls-files` = 74” (94 tracked files today). | `python -I … --self-test` → `17 cases / 32 mutations + 4 default-mode checks + 3 guard checks`; `git ls-files -- docs/plans/<plan>` → 94 lines; manifest `plan_freeze_git_head = 89c0862d…`; sha256 of `v5-freeze-boundary.md` = `5e939d46…` = manifest binding | No v5 fix possible (correcting the file breaks its manifest binding → new generation). Add it to the v6 redesign list; in the record, mark the boundary record as a frozen historical snapshot and point readers at README §2 for current expected counts. |
| HDS-P3-2 | P3 | The §8 SQL-OBS-3 row's block is **real but slightly broader than the code supports**. (a) Real and reproduced: mutating the checker's bytes fires `N5` and nothing else new; adding any *file* under `tools/` fires `V5-TOOLS-EXACT`. (b) Precision: `tools/__pycache__` is explicitly exempt from `V5-TOOLS-EXACT` (documented in-code), so “任何新文件” is not literally exact; and the self-test temp tree comes from `tempfile.TemporaryDirectory()`, which honours `TEMP`/`TMP`, so the wall-clock symptom can be reduced **without touching any frozen byte** (e.g. pointing `TEMP` at a RAM disk). The row's sentence is scoped to the named code optimization (“复制一次 + 逐例回滚”), so it is not false — only its “在 generation v5 内不可行” should not be read as “wall clock cannot be improved in v5”. | Differential experiment in `%TEMP%` (identical trees, real checker vs +1 appended comment line): control codes `['N10','N8','V5-ATTRS-UNSET']` → treatment codes `['N5','N10','N8','V5-ATTRS-UNSET']`, new = `['N5']`, fail line `- N5: hash/size mismatch: tools/v5_plan_consistency_check.py`. Planted `tools/zz_extra.py` → rc=1 with `V5-TOOLS-EXACT`; planted `tools/zz_extra.pyc` → rc=1 with `V5-TOOLS-EXACT`. `TOOLS_EXPECTED` = exactly 4 names (`v5_equivalence_check.py`, `v5_freeze_manifest_build.py`, `v5_plan_consistency_check.py`, `v5_version_reference_scan.py`); enumeration skips `__pycache__` (`tools/v5_plan_consistency_check.py:299-303`) | Optional wording fix only: say “code changes to the frozen checker are blocked; environmental tuning (TEMP location) remains available”, and narrow “任何新文件” to “任何非 `__pycache__` 文件”. |
| HDS-P3-3 | P3 | Measurement-series transcription drift in the source the new row cites: `v5-freeze-review-sql-performance-closure3.md` line 20 records mutation growth as “27→31→**34**”, while the frozen checker's AST at `89c0862` (V5-2.3) and at `4f4dea1`/HEAD both contain exactly **32** mutations (the record says 27/31/32). The new §8 row cites only the wall-clock series (11→50→55→89 s) and makes no mutation-count claim, so the row itself is accurate. | `ast` count of `N_CASES`/`V5_CHECK_CASES` from `git show <commit>:tools/v5_plan_consistency_check.py` → `89c0862 cases=17 mutations=32 v5_check_cases=4`; `4f4dea1 … 32`; `HEAD … 32` | None required (historical review file). If touched, correct 34 → 32. |

## Explicit answers to the two adjudication questions

**Is the §8 claim that optimizing `--self-test` inside generation v5 is structurally blocked real?** — **Yes, for the two routes the row names, and I reproduced both from the code and behaviourally.**
(a) `plan_manifest.v5.json` binds `tools/v5_plan_consistency_check.py` (`sha256 b5b2da6c…ea38`, `size_bytes 58055`) as a normative entry; `verify_manifest()` recomputes every declared entry's sha256/size from disk and raises `N5` on mismatch (`v5_plan_consistency_check.py:405-411`). Differential experiment: appending one comment line to a copy of the checker produced exactly one new failing code, `N5: hash/size mismatch: tools/v5_plan_consistency_check.py`. The manifest is additionally declared immutable (`immutability_policy`), so re-binding a changed checker means a new `plan_manifest.vN.json` + re-review — i.e. a new generation.
(b) `V5-TOOLS-EXACT` requires the recursive file enumeration of `tools/` (excluding `__pycache__`) to equal the fixed 4-tuple `TOOLS_EXPECTED` (`:78-79`, `:299-303`). Planted `tools/zz_extra.py` and `tools/zz_extra.pyc` each made the default mode exit 1 with `V5-TOOLS-EXACT`; the checker's own self-test covers the same two mutations.
There is no third frozen-bytes-free *code* route: the self-test loop, the mutation table and the temp-copy strategy all live inside the frozen checker, and adding a helper anywhere under `tools/` is caught by (b).

**Is the row's wording accurate (including ~90 s, one-shot, zero repo writes, all under `%TEMP%`)?** — **Yes on all four, with the two precision notes in HDS-P3-2/HDS-P3-3.**
* One-shot: `main()` dispatches `--self-test` separately; default and `--verify-manifest` never run it (measured 2.1 s / 4.6 s vs 73.6 s).
* ~90 s: measured **73.563 s** (run 1) and **72.366 s** (run 2, concurrent load) on this machine; same order, so the “~90s” figure is a fair cost statement (the internal series 11→50→55→89 s is machine-dependent).
* Zero repo writes: a full pre/post walk of every file under the repo (**57 878** files excluding `.git`, run 1; **62 367 → 62 368** including `.git`, run 2) reported `created=[] deleted=[] changed=[]` for run 1 and, for run 2, `deleted_count=0`, `changed_count=0`, **`git_dir_changed_count=0`** (the single “created” entry in run 2 is a concurrent sibling agent's review document `v5-freeze-review-handover-docs.md`, mtime 2026-09-10 20:39:22, not produced by the checker). Code audit of every write primitive (`write_text`, `write_bytes`, `mkdir`, `copytree`, `rmtree`, `mklink`, `git init`) shows all targets are derived from `ctx.root` / `ctx.baseline` of the temporary copy or from `tempfile.TemporaryDirectory()` (`:996-1148`); no write target is built from the real repo path in `--self-test`.
* All under `%TEMP%`: the self-test tree is `tempfile.TemporaryDirectory()` (no explicit `dir=`), which resolves to `%TEMP%`; all observed writes and the `mklink /J` / `git init` side effects occur inside that tree. (Limit of this measurement, stated honestly: I proved zero writes to the repo and that the temp root is the `tempfile` default; I did not audit the whole filesystem for writes outside repo+`%TEMP%`.)

## Appendix — raw measurements

Environment: `python --version` → `Python 3.13.9`; `TEMP=C:\Users\郑曾波\AppData\Local\Temp`; repo HEAD `1a992cdf9576c49e047c7d6d184d6617514570bd`; `git status --porcelain` at start → ` M docs/plans/source-catalog-worker-recovery-v5-2026-09-03/v5-freeze-record.md`.

### A1. Triple run (`%TEMP%\v5review\run_modes.py`, subprocess with byte capture)

```
default            exit=0 sec=2.096  bytes=172 cr=0 sha256=5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83
  'PASS: 7720 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}\nREAD_ONLY: no production database, registry, process, source, config, or network access\n'
--verify-manifest  exit=0 sec=4.584  bytes=172 cr=0 sha256=6ab6255c5cc35311dcb6600eebeff9248c742c8c9544cdda3346a5cda5d3a384
  'PASS: 9188 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}\nREAD_ONLY: …\n'
--self-test        exit=0 sec=73.563 bytes=3799 cr=0
  last line: 'SELF-TEST: 17 cases / 32 mutations + 4 default-mode checks + 3 guard checks; failures=none'
  32 × 'SELF-TEST N*.* PASS: rejected (full+isolated)', 4 × 'SELF-TEST V5-*.* PASS: default-mode check rejects the mutation',
  3 × 'SELF-TEST GUARD[-I|-M] PASS'
second --self-test run: exit=0 sec=72.366, same last line
```
README §2 expectations: `7720` ✓, `9188` ✓, `17 cases / 32 mutations + 4 default-mode checks + 3 guard checks; failures=none` ✓ (byte-exact); the quoted default-mode JSON differs only by `": "` spacing → HDS-P2-1.

### A2. Frozen artifact identity

```
python -I -c "… filecmp.cmp(frozen, fresh, shallow=False) …"
frozen size 172 cr 0 lf 2 sha 5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83
fresh  size 172 cr 0 lf 2 sha 5e60611c82e42924705c3eaeec066ecfe48a620e4370ac55fe924c8fc4e2ad83
filecmp identical: True ; bytes equal: True
frozen repr: b'PASS: 7720 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}\nREAD_ONLY: no production database, registry, process, source, config, or network access\n'
```

### A3. Isolation guard

```
guard_no_I  exit=1 sec=0.081 stdout=0 bytes  stderr='FAIL: run with an isolated interpreter - `python -I <checker>`.\r\nWithout -I, sys.path[0] (script dir or cwd under -m) can shadow the stdlib.\r\n'
```
No PASS line on stdout or stderr. Guard source: `v5_plan_consistency_check.py:28-40` (requires `sys.flags.isolated`, checked before any stdlib import beyond builtin `sys`).

### A4. Manifest bindings (`%TEMP%\v5review\verify_bindings.py`)

```
MANIFEST sha256=f9735eb8e3128f8920c5bdd1a45d434428afa48d4c334fc7b7731a4e1bc252d3 size=14125
normative_files entries=51 normative_file_count=51 composition={'imported':48,'v5_own_governing':3,'total':51,'self_excluded':1}
A_PER_ENTRY_MISMATCHES=0
B_SELF_EXCLUDED=True  B_self_exclusion_field=plan_manifest.v5.json  B_DUPLICATE_PATHS=False
C_TARGETS=52 C_NOT_IN_HEAD=0 C_BLOB_DIFF=0            (git ls-tree -r HEAD vs git hash-object)
C_git_status_plan_dir=' M …/v5-freeze-record.md\n'
D_capture_manifest ok=True da7d116e8c692d63/34238
D_evidence[v5-version-reference-inventory.json] ok=True 72db3a1ac13c0e94/29973
D_evidence[v5-baseline-equivalence.json] ok=True 79ac6ca49ad7a708/2970
D_evidence_tools[0] tools/v5_version_reference_scan.py ok=True ab46623873e4c529/10057
D_evidence_tools[1] tools/v5_equivalence_check.py ok=True c29e19ad1d9392fc/3035
D_supersedes[0] baseline/history/plan_manifest.v4.json ok=True c34b849475f1efeb
D_supersedes[1] baseline/history/plan_manifest.v3.json ok=True 9ee84acdbe65a294
D_investigation_source baseline/investigation/worker-investigation-2026-08-20.md ok=True 8e6166ba063bc281
D_boundary_record v5-freeze-boundary.md ok=True 5e939d4646d23350
D_manifest_blob_match=True (worktree blob c338f2be… == HEAD blob)
E_imported=48 governing=3 total=51 ; E_equivalence_recount={'v4_exact':21,'crlf_only':17,'unproven_new_baseline':10,'v5_own':3}
```

### A5. Freeze-record §1 hash claims (independent recomputation)

| §1 claim | recomputed | ok |
|---|---|---|
| `plan_manifest.v5.json` `f9735eb8…/14125` | `f9735eb8…/14125` | ✓ |
| `plan_freeze_check.v5.txt` `5e60611c…/172` | `5e60611c…/172` | ✓ |
| `plan_manifest.schema.v5.json` `d7218d36…/7327` | matches manifest entry (A4 mismatch=0) | ✓ |
| `tools/v5_plan_consistency_check.py` `b5b2da6c…/58055` | matches manifest entry | ✓ |
| `.gitattributes` (manifest first entry) `88182b26…/172` | matches manifest entry; content `* -text -eol -filter -working-tree-encoding` | ✓ |
| `tools/v5_freeze_manifest_build.py` `5ece62bc…/6586` | `5ece62bc9c4a07fbed8c5f254efea983c7790b196f5fefb20ad77e18390ad459/6586` | ✓ |
| `v5-version-reference-inventory.json` `72db3a1a…/29973` | ✓ (A4) | ✓ |
| `v5-baseline-equivalence.json` `79ac6ca4…/2970` | ✓ (A4) | ✓ |
| `import_manifest.v5.json` (manifest `capture_manifest`) | `da7d116e…/34238` | ✓ |
| `v5-freeze-boundary.md` `5e939d46…/7262` | ✓ (A4) | ✓ |

**No stale hash claim in §1.** (The stale claims found are non-hash prose: HDS-P2-2, HDS-P2-3, HDS-P3-1.)

### A6. Drift / provenance (`%TEMP%\v5review\drift.py`, `final_state.py`)

```
FREEZE_COMMIT 89c0862 (V5-2.3 freeze head): present=52 missing=0 blob_diff_vs_HEAD=2
   DIFFERS: tools/v5_plan_consistency_check.py, plan_manifest.v5.json     (products finalised one commit later)
FREEZE_COMMIT 4f4dea1 (V5-2.4 products committed): present=52 missing=0 blob_diff_vs_HEAD=0
COMMITS_TOUCHING_FROZEN_PATHS_SINCE_4f4dea1=0
PLAN_DIR_DIFF_4f4dea1..HEAD: README.md | findings.md | progress.md | task_plan.md | v5-freeze-review-sql-performance-closure3.md | v5-freeze-review-test-dag-closure4.md  (active docs only)
S6_tracked_files_in_plan_dir=94        (boundary record's "74" is a freeze-time value)
S6 commits 454f632/917b8d8/9418e72/89c0862/436ecd3/4f4dea1: all type=commit, ancestor_of_HEAD=True
S5_retired_dir declared=38/da927ee294978a2578d459e285bbd00f7e7abea87ae6e42a0294a588f9a8c81b measured=38/(same)
S4 v5_version_reference_scan.py --check exit=0 'CHECK OK: inventory .json and .md reproduce byte-for-byte'
S4 v5_equivalence_check.py --check exit=0 'CHECK OK: v5-baseline-equivalence.json reproduces byte-for-byte'
FINAL_AT=2026-09-10T20:40:29  FINAL_manifest_sha=f9735eb8…  entries=51 mismatches=0
FINAL_blob_targets=52 not_in_HEAD=0 worktree_ne_HEAD=0
FINAL_default_rc=0 stdout==frozen:True stdout_sha=5e60611c…ad83
FINAL_git_status_plan_dir=' M …/v5-freeze-record.md\n?? …/v5-freeze-review-handover-docs.md\n'
```

### A7. §8 row probes

```
AST count of the frozen checker: 89c0862 cases=17 mutations=32 v5_check_cases=4 ; 4f4dea1 … 32 ; HEAD … 32
Differential (N5): control rc=1 codes=['N10','N8','V5-ATTRS-UNSET'] ; treat (+1 comment line) rc=1 codes=['N5','N10','N8','V5-ATTRS-UNSET']
                   new codes = ['N5'] ; fail line '- N5: hash/size mismatch: tools/v5_plan_consistency_check.py'
                   (N10/N8/V5-ATTRS-UNSET fire in BOTH arms — artefact of the experiment's non-git temp tree, hence the differential)
tools/ enumeration: plant tools/zz_extra.py rc=1 V5-TOOLS-EXACT fired=True ; plant tools/zz_extra.pyc rc=1 V5-TOOLS-EXACT fired=True
TOOLS_EXPECTED (checker :78-79) = exactly 4 names; :299-303 enumerates tools/**/* skipping __pycache__
self-test writes: run1 (repo minus .git, 57 878 files) created=[] deleted=[] changed=[]
                  run2 (incl. .git, 62 367→62 368) deleted=0 changed=0 git_dir_changed=0; the 1 new file is a concurrent sibling's v5-freeze-review-handover-docs.md (mtime 20:39:22)
```

### A8. Reviewer-environment caveats (declared)

1. The plan directory had **concurrent writers** during this review: the author's uncommitted §8 edit (mtime 20:29:01) and a sibling reviewer's new untracked `v5-freeze-review-handover-docs.md` (20:39:22). Neither is in the frozen set or the evidence scope, and the frozen bytes still reproduced at 20:40:29.
2. Wall-clock figures are machine- and load-dependent; run 2 overlapped other work.
3. `--self-test` was the only long operation; all other measurements are single-shot and were re-confirmed in the final state pass (A6).
