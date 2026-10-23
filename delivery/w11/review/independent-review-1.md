# Independent review 1 — W11-CWP-SOURCES (offline discovery root-cause fix)

- Reviewer role: **independent reviewer** (not the author; no part in the implementation).
- Review time: 2026-10-23 22:33–22:52 Europe/London.
- Workspace: `C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery` (independent sparse worktree).
- Interpreter: `C:/Users/郑曾波/Projects/company-wiki/.venv/Scripts/python.exe` (3.14.2, Windows), pytest 9.1.1.
- Constraints honoured: 0 network, 0 external model calls, 0 downloads, production catalog/company lake never opened or written, sealed audit evidence read-only, author tests/product not modified by this review.
- Authority read before review: `W11-CWP-SOURCES.md`, `INTERFACES.md`, `INPUTS.json`, `handoff.template.json`; workspace PWF; delivery files; sealed `faa5bf…` capture.

## Verdict

**CHANGES REQUIRED — not approved for handoff as-is.**

The two *observed* defects named by the lane are genuinely fixed and I verified them independently against the pre-fix module: the sealed result's three privacy/terms candidates are now excluded, and "earnings release/presentation" no longer becomes `investor_call_transcript`. The new tests pass exactly as claimed (26 new; 36 total in the existing file; 33 in the delivered selection).

However the new **title-token whitelist introduces deterministic, silent false negatives on realistic IR-index markup** (High), admits event/navigation titles as material candidates (Medium), the date-ownership defect that the new test claims to cover is still present (Medium), and **`delivery/w11/evidence_inventory.json` is invalid JSON** (Medium). These are fixable, but the artifact must not be handed off claiming full/normal discovery coverage until they are fixed or explicitly recorded as external limits and re-reviewed.

## Reviewed version and exact SHAs

| Item | Value |
|---|---|
| branch | `codex/r1-w11-source-recovery-20261023` |
| reviewed HEAD | `ecc7d6223c46073896089d68046ffcfa180822e9` |
| parent / lane base | `0d7ada2138d41053598fcbfab5ac1e2bbd6684f5` / `a2f99db676846b7f475def253c541e12c49ae5fe` |
| worktree status at review start | only `?? delivery/w11/push-gate-rerun.log`; product/config tracked files unchanged |
| base product blob (for differential probes) | `0d7ada21:src/company_wiki/source_catalog/official_discovery.py`, 11,008 B, SHA-256 `7d8fb1292c6728adae9edf5a179242a3718b756e8659bbbb19154aff9f8ec2c3` |

Working-tree SHA-256 (the bytes the delivered `test_results.json` binds; independently recomputed):

| Path | Bytes | SHA-256 |
|---|---:|---|
| `src/company_wiki/source_catalog/official_discovery.py` | 12844 | `5073da1872d56577980b0c94ba43aca527a4e87bbdfd4fdca885f87d4ad5b17d` |
| `src/company_wiki/source_catalog/official_source_cli.py` | 12514 | `18746c6b0904e38e3b24b5a015d79ebf8b814bf0bab5f73a539154c2c94eae46` |
| `tests/integration/test_official_discovery_offline.py` | 20632 | `dae893398172c29ab497d197d245452ebf4e75f66ff59608619c2d19ab9c2996` |
| `tests/integration/test_official_source_flow.py` | 56854 | `f374c7d7ff39677c9b30c9f4ac9c8429740c7e8df1655fb95efc3bb453564b66` |
| `delivery/w11/evidence_inventory.json` | 7352 | `d39a214aede7b2a44c9ea36dce9c6bef6e8681d377d4d1c53b244cbc68f59fe7` |
| `delivery/w11/test_results.json` | 3162 | `e9d610de6d3cc492ef5de5d810f110b392eb77ebd1a776bd51b1e8c9eb19df53` |
| `delivery/w11/cleanup.json` | 2603 | `324fd327758f9dd40f7e53a39e56ea3f526fd5a6bef714c5aed56e270be6311d` |
| `delivery/w11/root_followup.md` | 2744 | `1cab80bfc64994f2188c4d72d6f7cc90d7f1bfd72bdf1f3ff0093ff45388df2c` |
| `delivery/w11/test-results.xml` | 5650 | `1d5c9c0c12ebd058a5ec4db00be7f3a635121b7a6a602315b3cbcb665b9b4962` |
| `delivery/w11/test-run-stdout.txt` | 2222 | `c641cbaee6b7776677faa0a8e5777578de2db87211be482f372f3a1acdd82e6e` |
| `config/source_catalog.yaml` (unchanged) | 866 | `3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968` |
| `config.yaml` (unchanged) | 3984 | `15541ba44e9621456cab7c6956c4f33be3f33e9b20f7053f1dc4aa6f0371bd1e` |

HEAD blob SHA-256 values (raw `git show`, LF) differ from the working-tree values only by CRLF checkout normalization; after normalizing line endings the content is byte-identical (`official_discovery.py` HEAD `7991558f…`, `official_source_cli.py` HEAD `3eaaa40a…`, `test_official_source_flow.py` HEAD `ff255559…`). The new offline test file is byte-identical at HEAD (`dae893…`).

Environment note: `delivery/w11` is outside the worktree's sparse-checkout cone (`core.sparseCheckout=true`; the tracked files carry the `S` skip-worktree bit). The tracked delivery files were present when I read/hashed them, then disappeared from the working tree mid-review while `git status` stayed "clean"; `git show HEAD:delivery/w11/*` still has the reviewed bytes. This was not caused by the author or by this review (I wrote only `tmp/review` and `delivery/w11/review`). It does mean `git status` alone cannot prove delivery-file presence — see IR-13.

## Tests I ran (own commands, not the author's narrative)

All offline; `PYTHONPATH=<workspace>/src;<workspace>/tests` unless noted.

| # | Purpose / command | Result |
|---|---|---|
| T1 | In-session import: `python -X utf8 -B -c "…assert Path(d.__file__).resolve().is_relative_to((Path.cwd()/'src').resolve())…"` with the two modules | exit 0; both `__file__` under `<workspace>/src` |
| T2 | In-session pytest import proof: `pytest tests/integration/test_official_discovery_offline.py -q -p no:cacheprovider -p pathcheck_plugin --collect-only` (plugin asserts `__file__` inside `pytest_configure`) | 26 collected; both modules under `<workspace>/src` |
| T3 | `pytest tests/integration/test_official_discovery_offline.py -q -p no:cacheprovider --basetemp=<workspace>/tmp/review-pytest-1` | **26 passed in 17.15 s**; conftest relocated/removed its basetemp (`review/evidence/offline-26-stdout.txt`) |
| T4 | `pytest tests/integration/test_official_source_flow.py -q -p no:cacheprovider` | **36 passed** (all cases in the existing file, not only the 7 discovery cases); first run 141.62 s, repeat 48.05 s (`review/evidence/existing-36-stdout.txt`) |
| T5 | Exact delivered selection: `pytest tests/integration/test_official_discovery_offline.py tests/integration/test_official_source_flow.py -q -k 'discovery or official_index_http or cn_fundraising or TestMaterial or TestNonMaterial or TestTimeWindow or TestUrlAndDedup or TestPagePayload or TestLimits or TestPublicCli' -p no:cacheprovider` | **33 passed, 29 deselected in 15.24 s** (matches delivered 33/0/0; delivered log says 11.48 s — count is what matters) |
| T6 | Adversarial probe harness (patched module + `0d7ada21` base module loaded from `git show`): `python -X utf8 -B tmp/review/w11_probe.py` | 45 probe results recorded; output in `review/evidence/probe-output.json` |
| T7 | Extra probes: `python -X utf8 -B tmp/review/extra_probe.py` | 14 probe results; `review/evidence/extra-probe-output.json` |
| T8 | Sealed-root body scan (independent, read-only): hash every file ≤60 MB in both authorized roots, exact-size 486789 search | audit run 2052 files / 166,731,220 B; holdout 65 files / 17,360,200 B; exact-size hits **0**; body-SHA hits **0**; 89 files in the 400–600 KB band (matches the inventory's count) |
| T9 | Verify all 11 `INPUTS.json` W11 entries | every byte count and SHA-256 matches |
| T10 | `ruff check` on the three changed source/test files | `All checks passed!` |
| T11 | Post-run product-state check | `companies/`, `.source_catalog/`, `catalog/` absent; `config/*` SHA-256 unchanged; no tracked product/test diff |

## Findings

Severity: High = functional under-recovery/regression from this commit; Medium = correctness or delivery defect that should be fixed before handoff; Low = real but bounded/pre-existing; Info = environment/handoff hygiene.

### IR-01 — High — Material-title whitelist silently drops legitimate material links (introduced)

**Evidence (all reproducible with the probe harness):**

1. `class-download-anchor-FN` — a very common IR table row where the title is in the row cell and the anchor text is "Download":
   ```html
   <table><tr><td>2026 Interim Report</td><td><a href="/ir2026.pdf">Download</a></td></tr></table>
   ```
   patched: `candidates=[]`, `coverage_status="checked_index_only"`, `limitations=[]`;
   base `0d7ada21`: 1 candidate (`https://ir.example/ir2026.pdf`).
2. `class-aria-label-icon-FN` — icon-only anchor: `<a href="/deck.pdf" aria-label="Investor Presentation"><img alt="Investor Presentation"></a>`: patched `[]`; base 1 candidate (empty title, PDF-suffix path).
3. `class-annual-results-FN` — `2025 Annual Results`, `Interim Results 2026`, `Q3 2026 Financial Results` (all `/…pdf`): patched `[]`; base 3 candidates. The list contains `results announcement` and `annual report` but not the equally common `annual results` / `interim results` / `financial results`.
4. `class-cn-phone-call-FN` — `2026年半年度电话会纪要`: patched `[]`; base 1 candidate. `"电话会"` is in `_TRANSCRIPT_TITLE_TOKENS` but not in `_MATERIAL_TITLE_TOKENS`, while English `"transcript"` is in both. The Chinese transcript class is therefore unreachable unless the title also contains 活动记录/业绩说明会/… .
5. `class-corporate-deck-FN` — `Corporate Deck 2026`: patched `[]`; base 1. The task card itself uses "deck" as a positive class; the list only has `presentation`.
6. `coverage-all-filtered-static` — page containing `2025 Annual Results` + `Board Deck` returns `coverage_status="checked_index_only"`, `limitations=[]`, `no_documents_claimed=false`. Nothing distinguishes "index has no material" from "the title whitelist rejected every anchor".

**Expected:** business-material leads remain candidates (or, at minimum, filtered anchors are counted/limited so the result cannot read as a clean covered index). Anchor text is not the only title source on IR pages; `aria-label`, `<img alt>`, and the nearest item container (`tr` / `li` / `article`) are part of the document lead.

**Actual:** deterministic silent loss for realistic index markup, with a coverage status that looks clean. This directly contradicts `root_followup.md` ("修复后的 discovery 已能正确排除隐私/条款导航并把真正的业务材料锚 … 作为候选输出") and the card's warning not to obtain negative-control green by rejecting all inputs.

**Required fix:** derive the lead from anchor text **plus** `aria-label`/`title`/`alt` and the nearest item-container text (or the URL basename token under a strict legal veto); never use bare suffix alone. If a link is rejected, expose an explicit limitation/count (e.g. `title_unmatched` or `ignored_anchors`) so `checked_index_only` is not claimed when many anchors were discarded. Add regression tests for the five inputs above. Re-run and re-review.

### IR-02 — Medium — `briefing`/`upcoming` are treated as material document clues (introduced)

**Evidence:**

1. `nonmaterial-briefing-FP`:
   ```html
   <article><time datetime="2026-05-01"></time><a href="/events/media-briefing">Media Briefing</a></article>
   <article><time datetime="2026-06-01"></time><a href="/events/press-briefing">Press Briefing</a></article>
   ```
   patched: 2 candidates with `disposition="candidate"`, `document_kind="investor_relations"` (a press/media event is not a document lead); base `0d7ada21`: 0 candidates.
2. `nonmaterial-upcoming-FP`: `Upcoming Events` and `Upcoming Careers Fair` become `index_notice` candidates; base 0.
3. `slot_probe` — the interaction that matters, with `max_items=1`:
   ```html
   <a href="/events">Upcoming Events</a><a href="/ar.pdf">Annual Report 2025</a>
   ```
   patched: only `Upcoming Events` is emitted, the real Annual Report is omitted, `limitations=["item_limit_reached", …]`; base: `Upcoming Events` is not a candidate, so the Annual Report is emitted.

**Expected:** non-material event/navigation titles do not qualify as material documents; at most they are `index_notice`, and they must not consume the material item budget ahead of real documents.

**Actual:** a dated media briefing is a full `candidate`; an "upcoming events" nav link can crowd out a real report under `max_items`.

**Required fix:** restrict `briefing` to `investor briefing` / `analyst briefing` (not media/press); either move `upcoming`/`event notice` out of the material gate into notice handling (only when a material clue is present) or exclude notices from the item budget. Add negative tests for media/press/careers/upcoming and a `max_items` interaction test.

### IR-03 — Low — Static legal/site denylist both leaks and over-vetoes (introduced in part)

**Evidence:**

1. `legal-hybrid-slip` — `Legal Information - Investor Day 2026` (href `/legal`) and `Accessibility - Annual Report Archive` (href `/access`) both become candidates. The list has `legal notice` but not `legal`; `accessibility` is absent entirely. A legal/utility page that also names a material-ish event slips through.
2. `material-contact-veto-FN` — `Annual Report 2025 - Contact Information` is vetoed (`contact`), although it names an annual report; base includes it.
3. `material-privacy-veto-FN` — `Investor Presentation - Privacy Update` is vetoed (`privacy`); base includes it.
4. `" Cookie"` (leading space) is subsumed by `"cookie"`; most other denylist entries are unreachable as written because the material-token gate already drops any title lacking a material token.

**Expected:** legal/navigation pages are never candidates; a genuine material title is not vetoed merely because a secondary word appears.

**Actual:** both directions remain possible; the denylist is a finite string list, not a section/context classifier.

**Required fix:** use structural/section signals (footer/nav/header/role, legal URL segments) in addition to word-boundary title tokens; do not let a single secondary token veto a title with a strong material token; add both-direction tests. At minimum record this as a bounded heuristic (not "correct") in the delivery narrative.

### IR-04 — Medium — Shared-container `<time>` misattributes publication dates; page-level "last updated" excludes all materials (pre-existing, overclaimed)

**Evidence:**

1. `date-page-level-timestamp`:
   ```html
   <div class="content"><time datetime="2026-10-22">Last updated</time>
     <a href="/ar.pdf">Annual Report 2025</a><a href="/ir.pdf">Interim Report 2026</a></div>
   ```
   patched (and base): **both** links land in `excluded` with `published_date="2026-10-22"`, `reason="after_as_of"`, zero candidates. A page-level "last updated" time is adopted as each material's publication date.
2. `date-shared-parent-misattribution` (two `<time>` in one `<div>`): both links get the first date `2021-08-15`, and the 2026 item is wrongly excluded as `before_window`.
3. `date-shared-list` (`<ul><li>` wrapper with a first `<time>`): same.
4. The new test `test_page_retrieval_marker_is_not_a_publication_date` does not test this: `discover_official_documents` has no fetch-time input at all; the test feeds `<time datetime="2026-10-21T19:39:09Z">` and asserts `published_date == "2026-10-21"`, i.e. it verifies ISO-timestamp truncation, not separation from retrieval time. Its comment ("A capture timestamp near the anchor must not be adopted…") is not exercised. The sealed fetch actually started `2026-10-22T19:39:09Z` (stdout `fetch_receipts`), not `2026-10-21`.

**Expected:** a material date must come from the material's own item (data-date or a `<time>` owned by that list item), never from a shared page/container timestamp; fetch/receipt time must never become `published_date`.

**Actual:** shared wrapper's first `<time>` is applied to every anchor beneath it, producing false exclusions/labels.

**Required fix:** scope the `<time>` lookup to the anchor's nearest item container (`li`/`tr`/`article`) and reject container-level/page-level times, or accept only `data-date` per anchor. Add a test with a page-level "Last updated" and a shared-container case. If this is deferred as out of the lane's write scope, remove the "通过" claim in findings A5 #9 and the misleading test name, and record it as a known limitation for ROOT. Pre-existing at `0d7ada21` (verified same behaviour), so it is not a regression from this commit.

### IR-05 — Low — `#fragment` variants duplicate the same resource (pre-existing; test enshrines it)

**Evidence:** `url-fragment-duplicate`:
```html
<a href="/ar.pdf#page=1">Annual Report 2025 one</a><a href="/ar.pdf#page=2">Annual Report 2025 two</a>
```
patched: 2 candidates with URLs differing only by `#page=…`; base: same. The new test `test_query_and_fragment_variants_stay_distinct` asserts 3 candidates for plain/query/fragment.

**Expected:** fragments are client-side selectors and are not sent to the server; the same PDF should not be reported as two independent candidates (query-string semantics may reasonably stay distinct). At minimum the dedup choice should be explicit and motivated.

**Actual:** duplicate candidates for one resource; downstream capture attempts would collide on content hash. **Required fix:** strip the fragment (and default port) before `seen`/candidate creation and add a test; or document the intentional fragment-distinct choice and its downstream cost. Pre-existing, low risk.

### IR-06 — Low — CLI: duplicate `byte_limit_reached`; malformed page rows crash with a traceback (pre-existing)

**Evidence:**

1. `cli-duplicate-byte-limitation` — a single HTML file larger than `max_bytes` (100) through the public CLI pages branch returns `limitations: ["byte_limit_reached","byte_limit_reached"]` (the library adds it, then the CLI appends it again in its `local_truncated` block). The delivered `test_cli_local_truncation_stays_partial` uses a file exactly equal to the cap and therefore misses this case.
2. `cli-missing-page-key` (remove `capture_id`), `cli-missing-entity` (remove `entity`), `cli-missing-mime` (remove `mime_type`) → exit code **1** with a Python `KeyError` traceback, not the documented `{"schema_version":"official-source-failure/1","status":"failed",…}` exit **2**. Other malformed inputs (`pages` not a list, 7 pages, `max_items=0`, both `urls`+`pages`) are refused cleanly.

**Expected:** `limitations` is a set-like unique list; malformed request shapes produce a clean JSON refusal. **Required fix:** de-duplicate before appending; validate required page-row keys and top-level fields and raise a caught `ValueError`. CLI is unchanged by this lane, so this is pre-existing; either fix here (allowed discover branch) or record as an external limit. Low because it requires a malformed request.

### IR-07 — Low — One malformed href aborts the whole discovery (pre-existing)

**Evidence:** `url-malformed-ipv6`:
```html
<a href="/ok.pdf">Annual Report 2025</a><a href="http://[">Annual Report malformed</a>
```
patched (and base) raises `ValueError: Invalid IPv6 URL` from `urljoin`/`urlsplit`; no partial result. Through the CLI this becomes a generic `official_source_ValueError` exit 2 and loses the valid candidate/no partial coverage.

**Expected:** skip the malformed anchor, keep the valid candidate, and record a limitation/count. **Required fix:** per-anchor `try/except ValueError` around URL resolution plus an explicit `invalid_url` limitation; test. Pre-existing; low frequency but a single bad link in a 486 KB page is plausible.

### IR-08 — Low — Empty / `#` href becomes a self-referential candidate (introduced)

**Evidence:** `url-self-link`:
```html
<a href="">Annual Report 2025</a><a href="#">Interim Report 2026</a>
```
patched: 2 candidates whose `source_url` is the index page itself (`https://ir.example/ir`, `https://ir.example/ir#`); base: 0 (no suffix/keyword). **Expected:** empty, `#`, and same-document anchors are not document leads. **Required fix:** skip zero-length/`#`-only refs and URLs resolving to the index document before candidate creation; add a test. Introduced by the material-title path.

### IR-09 — Medium — `delivery/w11/evidence_inventory.json` is invalid JSON; scan byte totals do not reproduce

**Evidence:**

1. Parsing the committed file (`git show HEAD:delivery/w11/evidence_inventory.json`) raises:
   `JSONDecodeError: Expecting ',' delimiter: line 146 column 29` because `"total_bytes": 167_018_437` and `"total_bytes": 17_449_142` use Python digit separators, which JSON does not allow. The file is a required machine-readable delivery artifact.
2. Independent read-only scan reproduces the substantive claim but not the totals: audit run 2052 files / **166,731,220 B** (inventory claims 167,018,437); holdout 65 files / **17,360,200 B** (inventory claims 17,449,142). File counts, 89 files in 400–600 KB, exact-486789 = 0, body-SHA hits = 0 all reproduce.
3. `body_available=false`, the "not a whole-disk absence claim" caveat, and the `must_not` instructions are honest and were independently corroborated (every file in both roots hashed; no file of size 486789; no file with SHA-256 `f1e822a8…`; the `faa5bf…` capture dir has only 250 B input×2, 0 B stderr, 2839 B stdout).

**Expected:** every delivery JSON parses; numeric evidence is reproducible from the recorded method. **Required fix:** plain JSON integers, corrected totals (or exact scan command/config so the totals can be regenerated), and a `json.load` check for all delivery JSON before handoff. This is a delivery blocker even though the absence conclusion is sound.

### IR-10 — Low — The required RED evidence was not retained

**Evidence:** card §4-A.4 requires, when a defect is actually observed, preserving the original RED stdout/JUnit and failing assertion; the delivery has no RED log. `test_results.json.red_phase` says `RED_not_observed_for_existing_suite` and lists D1–D3, while `findings.md` cites `probe_defects.py`/`probe12.py` outputs that were deleted (`cleanup.json`). I independently reproduced all three against the base module: earnings release/presentation → `investor_call_transcript`; privacy/terms PDFs → candidates; `Business`/`Investor`/`Conference`/`Contact Information` → candidates. So the claims are true, but the raw evidence required by the card is not in the package.

**Expected:** preserved RED/probe log (regenerable from `git show 0d7ada21:…`) or an explicit statement that probe outputs were not retained. **Required fix:** attach the base-code probe stdout (with the base blob SHA) or amend the delivery narrative; do not imply a pytest RED that did not exist.

### IR-11 — Low — Test names/comments overclaim what the tests verify; derivation constants unused

**Evidence:**

1. `test_page_retrieval_marker_is_not_a_publication_date` — vacuous for the named property (see IR-04); it asserts a `<time>` timestamp **is** used as the publication date.
2. `_offline_socket_guard` comment — "the CLI subprocess only needs a local socket pair for asyncio's loop": the pages branch never runs asyncio/sockets, and the in-process monkeypatch does not cover the subprocess at all; the guard is harmless but the comment is wrong.
3. `SEALED_RESULT_SHA256` and `DERIVED_FIXTURE_NOTE` are defined at module level but never used or asserted anywhere; the docstring's "bound to that result's SHA" claim is decorative.
4. The sealed timestamp used in the test (`2026-10-21T19:39:09Z`) differs by a day from the real `fetch_receipts.started_at` (`2026-10-22T19:39:09Z`), further indicating the fixture is not actually modelling the sealed receipt.

**Expected:** test names/comments state exactly what is verified; derivation binding is asserted. **Required fix:** rename/split the date test, fix the socket comment, assert `DERIVED_FIXTURE_NOTE`/the sealed SHA in a test (or delete the dead constants).

### IR-12 — Low — Redundant/dead tokens and an inaccurate comment

**Evidence:**

- `_TRANSCRIPT_TITLE_TOKENS = ("call transcript", "transcript", "电话会", "transcript of")`: `"call transcript"` and `"transcript of"` are substrings of `"transcript"` and add nothing.
- The comment says transcript identity "requires an explicit call/transcript clue", but there is no bare `"call"` token; e.g. `Q2 2026 Earnings Call` is not classified as a transcript (which may be the intended semantics, but the comment says otherwise).
- `_NON_MATERIAL_TITLE_TOKENS` contains `" Cookie"` (leading space), subsumed by `"cookie"`; most entries are unreachable because the material-token gate already drops those titles.
- `tests/integration/test_official_discovery_offline.py` has no final newline (cosmetic; ruff passes because W292 is not enabled).

**Required fix:** simplify the token tuples, correct the comment (or implement the stated call clue), remove `" Cookie"`, add the trailing newline. Low engineering-quality cleanup; does not change verdict by itself.

### IR-13 — Info — Handoff/environment hygiene (not all author-owned)

- Tracked `delivery/w11/*` files were removed from the working tree mid-review by an out-of-cone sparse operation (see the environment note); HEAD blobs are intact, but the parent must restore/verify them and must not run `git sparse-checkout reapply` while assembling the handoff or the review reports can vanish. `git status` cannot detect this because the files are skip-worktree.
- Untracked 0-byte `delivery/w11/push-gate-rerun.log` exists (created 22:32:51, after the lane commit) and is not in `cleanup.json`; remove or explain it before handoff.
- `cleanup.json`'s `only_lane_writes_in_tree` is a tracked-path list; `.mypy_cache`, `.ruff_cache`, `.benchmarks`, `.coverage`, `.ingested` have post-baseline mtimes (ignored tool caches), so it is not a full filesystem delta. No production/catalog/config writes were found: `companies/`, `.source_catalog/`, `catalog/` are absent; both config hashes match the pre-lane values; no tracked product diff.
- The test run leaves `pytest-of-郑曾波/` in the workspace whenever pytest uses its default basetemp (this write sandbox only permits writes inside the workspace; the observed effect is that pytest's default basetemp lands in cwd). The author deleted one per `cleanup.json`; my combined-selection run re-created one and I removed it. The delivered combined run itself logged `relocated: false, reason: no-explicit-basetemp`, so reviewers/CI must pass an explicit basetemp or clean this up. This is an environment behaviour, not a product write. I also removed `tmp/review` and an empty `cw-pytest-basetemp/20261023-213342-29888771` (aborted reviewer pytest invocation); reviewer evidence is retained under `delivery/w11/review/evidence/`.

## Positives verified (independent)

- **Sealed evidence is real and correctly described.** `faa5bf…/stdout.txt` = 2839 B / SHA-256 `1c33f18b…`; all 11 `INPUTS.json` W11 files match byte count and SHA-256. The result has exactly 3 candidates, all privacy/terms PDFs, `coverage_status=partial`, `dynamic_content_unresolved` + `publication_date_unknown`, `no_documents_claimed=false`, `response_bytes=486789`, body SHA `f1e822a8…` only in `fetch_receipts`.
- **The body is genuinely absent.** Full independent SHA-256 scan of both authorized roots (2052 + 65 files): 0 exact-size files, 0 body-SHA hits. The capture directory has no body. The delivery does **not** claim the body exists or that the original replay passed — that part is honest.
- **The observed classification defects are fixed.** Differential probes against the `0d7ada21` module:
  - `Q2 2026 Earnings Release` / `… Earnings Presentation`: base `investor_call_transcript` → patched `investor_relations`.
  - `Earnings Call Transcript`: `investor_call_transcript` (unchanged).
  - `Privacy Statement`, `Terms of Use`, `Legal Notice and Disclaimer`: base 3 candidates → patched 0.
  - `Business`, `Investor`, `Conference`, `Contact Information`: base 4 candidates → patched 0.
- **Sealed-derived minimal fixture (clearly `derived_minimal_fixture`, not a replay).** I reconstructed the exact three sealed titles (`隐私声明`, `使用条款`, `|  隐私声明`) and exact `officialsite-static.wuxiapptec.com` URLs from stdout into a 403-byte page (SHA-256 `37e86e59…`), entity `药明康德`, window 2026-01-01…2026-10-21, and ran the **public CLI pages branch**: `candidates=[]`, `no_documents_claimed=false`, exit 0. The same fixture through the base module yields exactly the 3 sealed candidates. A derived variant with an external `<script src>` returns `coverage_status=partial`, `limitations=["dynamic_content_unresolved"]`, `candidates=[]`, `no_documents_claimed=false` — consistent with the real page's known dynamic symptom, but still not an original replay (the 486789 B body remains absent; no claim of replay success).
- **Coverage/limit semantics are honest in the paths I tested.** item limit → `item_limit_reached` + partial + `no_documents_claimed=false`; exact-max does not emit a false item limitation; byte limit on the first/second page → `byte_limit_reached` + partial; first-page-over-cap → 0 candidates + limitation (not "no documents"); zero-page library calls → `checked_index_only` with empty event list (note: checked_index_only with zero indexes is arguably weak, but `no_documents_claimed=false`); unsupported MIME → limitation + later HTML still parsed; `index_fetch_incomplete` propagates when a fetch receipt is not `opened`; `fetch_receipts` present; `receipt.event_sha256` recomputes exactly and `event_ids` bind the consumed captures.
- **Payload honesty.** Inline JSON-LD (`script` without `src`) does not trigger `dynamic_content_unresolved`; an external script does (conservative, pre-existing) and material candidates are still emitted with the partial status. A static page containing the prose word "Loading" still triggers the heuristic — documented as an external limit, not silently removed.
- **CLI layering/hygiene.** CLI discover branch remains thin; local pages require absolute paths; `urls`+`pages` together is refused; 7 pages / `max_items=0` / non-list pages are clean exit-2 refusals; the two-neutral-issuer subprocess test passes; no production catalog/config is opened on the pages path.
- **No schema drift.** `official-discovery-result/1` keys are unchanged; the changes are internal token lists plus the transcript-kind override; no company/domain/year-specific branch appears in the diff; input bounds (`max_items` 1..30, `max_bytes` >0..8 MiB, 1..6 pages at the CLI, 64 KiB request) remain enforced; `ruff` passes.
- **Delivered test numbers are truthful.** Delivered combined run = 33 passed / 0 failed / 0 skipped / 29 deselected; JUnit has `tests="33"` with no failures; `test-run-stdout.txt` SHA-256 matches the recorded `log_sha256`; my independent runs reproduce 26 new, 36 existing, and 33 in the exact selection. The `test_results.json` `input_source_shas` match the working-tree files.

## External limits / not verified

- The 486,789 B original IR body is not available; I did not re-fetch it, reconstruct it, or claim the original discover replay passed. The derived fixture is explicitly not a replay.
- Coverage remains one-index-only (`checked_index_only`) or partial; nothing here proves full-site/search completeness, and no new source was acquired.
- I did not exercise real HTTP except the existing MockTransport/loopback test paths; no network was used. ET/CN-wire/fee issues named by the card are out of this lane and not assessed.
- `fetch_official_indexes` real transport, redirects and budget exhaustion were covered only by the existing MockTransport test (which passed); no live endpoint was contacted.

## Required fixes before handoff (priority order)

1. **IR-01 (High):** broaden material-lead extraction (container text / aria-label / alt / URL basename with legal veto) and make any rejected-anchor loss visible; add the five regression inputs; re-run.
2. **IR-02 (Medium):** restrict `briefing`; separate notice tokens from material tokens or exclude notices from the item budget; add negative tests (media/press/careers/upcoming) and the `max_items` interaction test.
3. **IR-09 (Medium):** make `evidence_inventory.json` valid JSON with corrected/reproducible byte totals; validate every delivery JSON parses.
4. **IR-04 (Medium):** scope `<time>` to the item, add a page-level timestamp test; or record it explicitly as a known limitation and remove the "通过"/test-name overclaim.
5. **IR-03 / IR-05 / IR-06 / IR-07 / IR-08 (Low):** fix or record as bounded external limits, with tests. At minimum do not mark them "correct" in A5/delivery.
6. **IR-10 / IR-11 / IR-12 (Low):** retain honest RED/probe evidence; correct test names/comments and unused constants; clean redundant tokens/EOF.
7. **IR-13 (Info, parent/ROOT):** restore/verify the delivery files from HEAD, remove the stray push-gate log, avoid sparse reapply during handoff, and keep the review evidence with the package.

After the fixes, the same final product SHA must be re-reviewed by an independent reviewer (this report is not a self-recheck). The sealed-result honesty and the two observed defects are already acceptable; the outstanding work is the generalization/coverage honesty and delivery-artifact correctness above.

## Conclusion

The lane correctly identified and fixed two real deterministic defects, kept the sealed-evidence story honest (body absent; no replay claim), preserved the pure-parse/thin-CLI layering, and produced truthful test counts. It does **not** yet meet the handoff bar: the replacement title whitelist under-recovers realistic material links (High), admits non-material event/navigation titles and lets them consume item budget (Medium), still misattributes shared-container dates while a new test claims otherwise (Medium), and a required delivery JSON is syntactically invalid (Medium). Verdict: **CHANGES REQUIRED**; re-run the full matrix and return for independent re-review of the final SHA.
