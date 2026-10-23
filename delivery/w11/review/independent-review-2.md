# Independent review 2 — W11-CWP-SOURCES (re-review of `a6d12a53`)

- Reviewer role: **independent re-reviewer** (not the author; no part in writing or fixing this code).
- Review window: 2026-10-23 22:54–23:15 Europe/London.
- Workspace: `C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery` (independent sparse worktree).
- Interpreter: `C:/Users/郑曾波/Projects/company-wiki/.venv/Scripts/python.exe` (3.14.2, Windows), pytest 9.1.1.
- Constraints honoured: 0 network, 0 model calls, 0 downloads, production catalog/lake never opened or written, sealed evidence read-only, product and author tests not modified by this review; my scratch was under `tmp/review2*/` and was removed after the probes.
- Read before review: the W11 card, `delivery/w11/review/independent-review-1.md`/`.json`, both delivery test files, the delivery JSONs, `probes/red_probe.py` + output, and the sealed `faa5bf…` capture.
- **Concurrent-writer warning:** the worktree was clean when this review started. At ~23:08–23:10, while this report was being written, another process modified `src/company_wiki/source_catalog/official_discovery.py` (observed 21,748 B / SHA `bdfd5d14…` then 22,790 B / SHA `855e57de…`, mtime 23:08:49) and `tests/integration/test_official_discovery_offline.py` (26,655 B / `fd65dc…` → 29,884 B / SHA `dd555b43…`, mtime 23:09:30), and created untracked dirs (`cwpaW03-p122fzr2/`, `pytest-of-郑曾波/`, `tmp49oqmktc`, `tmp9st97nlj`). None of that is part of `a6d12a53` and none of it was written by this reviewer (my scratch was removed). HEAD remained `a6d12a53`. All review evidence is bound to the committed `a6d12a53` bytes; T16 re-runs the decisive cases directly from `git show a6d12a53:…` after the concurrent edit appeared. The in-progress test revision I sampled still ended without a final newline.

## Verdict

**CHANGES REQUIRED — not approved for handoff yet.**

Twelve of the thirteen prior findings are verified fixed on the final product SHA. IR-12 is only partially fixed (the offline test file still has no final newline).

The IR-01/IR-03 token broadening, however, introduced a **Medium false-positive/budget regression**: navigation-only links whose labels contain broad material tokens (`Annual Reports`, `Results`, `News Releases`, `公告`, `业绩`, `Reports`) are now emitted as `candidate` records, including from `<nav>`/`<header>`/`<footer>`. Under `max_items` they displace real documents. With `max_items=1`, a CN nav link `公告` before `2025年年度报告` reproduces the exact failure mode that IR-02 fixed for event notices (base emitted the report; current emits only the nav link plus `item_limit_reached`). With the default `max_items=30`, a nav link plus 30 real report PDFs emits only 29 reports because the nav link takes a slot. This is a regression relative to base `0d7ada21` and contradicts the lane's purpose (recover material leads, do not emit navigation as material).

Several bounded residuals remain (single-link page-level `<time>`, `unclassified_document_links` mislabel, legal-page over-veto, prose-as-title, multi-link rows, query-only self links, malformed page URL, deferred-truncation cost). They are Low/Info, but the delivery narrative currently overstates two of them as fully "fixed"/"correct".

## Reviewed version and exact SHAs

| Item | Value |
|---|---|
| branch | `codex/r1-w11-source-recovery-20261023` |
| reviewed HEAD | `a6d12a537bcacdf3d03d0045caa2ef2ddabafb87` (`a6d12a53`) |
| parent / lane base | `ecc7d622` (prior reviewed) / `0d7ada21` (lane base) |
| worktree status | clean at review start; concurrent uncommitted edits to `official_discovery.py` and `test_official_discovery_offline.py` appeared at ~23:08–23:10 (see warning above) and are excluded from this review; reviewer-owned files are only the review/evidence additions |
| working-tree product/test SHAs (independently recomputed; these match `test_results.json.input_source_shas`) | see below |

| Path | Bytes | SHA-256 (working tree, CRLF checkout) | SHA-256 (HEAD blob, LF) |
|---|---:|---|---|
| `src/company_wiki/source_catalog/official_discovery.py` | 18937 | `f2ad8e578b221993c7fba984d31f874c324e2b651ef3a1c22aaa7c85384695f5` | `a008e1cb5a9fc5140c1dd3b7470e107abc2611cc397d279e7a97b2ad46b2a079` |
| `src/company_wiki/source_catalog/official_source_cli.py` | 13362 | `bdd06d5728dc25ef9a7433e5d7c1c89534f3fa52b9dd6e15ce7867e40d9c6162` | `7fb9a8031e6d98fd9788518b9fb41904179f326fba57c2bbb08fb48d1dee1adf` |
| `tests/integration/test_official_discovery_offline.py` | 26655 | `fd65dc34c6c126ad549811b4ff7745c4e6375c7f72d8f3f5bfef9ddb8379aff1` | `fd65dc34…` (byte-identical) |
| `tests/integration/test_official_source_flow.py` | 56854 | `f374c7d7ff39677c9b30c9f4ac9c8429740c7e8df1655fb95efc3bb453564b66` | `ff255559a09fbb00dfe6e2f233f2eebb779d2f0daf43fcb6d6de6c1aaaa7b142` |
| `delivery/w11/evidence_inventory.json` | 7684 | `87833dbc8d496429d6057259e7834cf02137cc08b2799cafd01ec0c083e34fb7` | `228abf16…` (CRLF only) |
| `delivery/w11/test_results.json` | 3120 | `8cb423a1bba78623294d1511218e9729114c5dc40b5d7a0a07a5fb4fe695f242` | `ba4dd466…` (CRLF only) |
| `delivery/w11/test-results.xml` | 8051 | `c8d98ffdf66a1dcef78039dc1fd1147742c2a04fd352c336c32aecb580be8d6c` | `c8d98ffd…` (byte-identical) |
| `delivery/w11/test-run-stdout.txt` | 2222 | `c6d9d487cc7faa922b28e7bf8a919e9ea6e3e2fe0df4bce2a78c7a89ab8c768d` | `c6d9d487…` (byte-identical) |
| `delivery/w11/cleanup.json` | 4209 | `a2b041586b370d122e0cbadb5394aa9eaa50663b6e2a783963da6790b479f3e3` | `a2b04158…` |
| `delivery/w11/root_followup.md` | 2770 | `8bf94a3489ac5dbac7204aaebb8201570a040164ee9cb43069b816d33006b06f` | `1cab80bf…` (CRLF only) |
| `delivery/w11/probes/red_probe.py` | 4967 | `22506fac4dc7212e882a8441e1c8a2ebc6bbeebc80ac58bb3a1dd86dbcc3a741` | same |
| `delivery/w11/probes/red-probe-output.txt` | 5762 | `be0cc1616756b38fb1bbea9179c2ad2a6921331abe1d01e95d40cab7ca857088` | same |

The SHA-256 values bound by `delivery/w11/test_results.json` (`f2ad8e…`, `bdd06d…`, `f374c7…`, `fd65dc…`) match the files I reviewed byte-for-byte. Config hashes are the pre-lane values: `config/source_catalog.yaml` `3d159a4e…`, `config.yaml` `15541ba4…`.

**Binding to `a6d12a53` despite the concurrent edit.** The committed LF blob is 18,436 B / SHA-256 `a008e1cb…`; the initial CRLF checkout was 18,937 B / `f2ad8e…` (same content). My test runs and 61-case probe output were produced at 22:55–23:02, before the concurrent edit appeared; after discovering it I re-loaded the committed `git show a6d12a53:src/company_wiki/source_catalog/official_discovery.py` bytes and re-ran the decisive cases (T16), reproducing every finding below. The uncommitted worktree edit is therefore not part of the reviewed artifact and is not approved by this review.

**The concurrent new round also overwrote three delivery artifacts** at 23:10:58–23:11:03: `delivery/w11/test-results.xml` (9,377 B / `88b883e8…`), `delivery/w11/test-run-stdout.txt` (1,125 B / `00bfa746…`) and `delivery/w11/probes/red-probe-output.txt` (2,931 B / `54dd99e1…`). Those are not the `a6d12a53` files reviewed here. The reviewed versions are the HEAD blobs listed in the table (`c8d98ffd…`, `c6d9d487…`, `be0cc161…`) and remain recoverable with `git show a6d12a53:…`; HEAD is still `a6d12a53` at the time of writing.

## Tests I ran (own commands/exit/results)

All offline; `PYTHONPATH=<workspace>/src;<workspace>/tests` unless noted. `py` = the workspace interpreter above, `-X utf8 -B`.

| # | Purpose / command | Result |
|---|---|---|
| T1 | In-session import proof with the card's exact command (`Path(d.__file__).is_relative_to(cwd/src)` for both modules) | exit 0; both `__file__` under `<workspace>/src` |
| T2 | `pytest tests/integration/test_official_discovery_offline.py tests/integration/test_official_source_flow.py -q -p no:cacheprovider -p pathcheck_plugin --collect-only` (plugin asserts `__file__` inside `pytest_configure`) | 76 collected (40 + 36); both PATHCHECK lines under `<workspace>/src` |
| T3 | `pytest tests/integration/test_official_discovery_offline.py -q -p no:cacheprovider --basetemp=tmp/review2-pytest-a` | **40 passed in 6.65 s**, exit 0 |
| T4 | `pytest tests/integration/test_official_source_flow.py -q -p no:cacheprovider --basetemp=tmp/review2-pytest-b` | **36 passed in 35.69 s**, exit 0 |
| T5 | Exact delivered selection (`-k 'discovery or official_index_http or cn_fundraising or TestMaterial or TestNonMaterial or TestTimeWindow or TestUrlAndDedup or TestPagePayload or TestLimits or TestPublicCli'`) | **47 passed, 29 deselected in 11.58 s**, exit 0 (delivered: 47/0/0, 29 deselected, 11.66 s) |
| T6 | Differential probe harness: current workspace module vs base `0d7ada21` module extracted with `git show`; 61 reviewer-authored cases (material leads, notices, legal/nav, dates, URL/dedup, limits, nav/structural, sealed-derived) | exit 0; `review/evidence/review-2-probe-output.json`; every current result has `no_documents_claimed=false` and a recomputed `receipt.event_sha256` match |
| T7 | CLI probe: 15 cases through the real `--operation discover` subprocess (malformed rows/fields, byte cap over/exact, both inputs, non-list pages) | exit 0; `review/evidence/review-2-cli-probe-output.json` |
| T8 | Re-run `delivery/w11/probes/red_probe.py` with `TEMP` inside the workspace | exit 0; base blob SHA `7d8fb129…`; decoded delivered output and rerun are semantically identical (D1/D2/D3) |
| T9 | Independent full SHA-256 walk of both authorized sealed roots | audit: 2052 files / **166,731,220 B**; holdout: 65 files / **17,360,200 B**; exact-486789 hits 0; body-SHA hits 0; 400–600 KB band 84 + 5 = 89; capture dir 250/250/0/2839 B with the card's SHAs |
| T10 | `json.load` every `delivery/w11/**/*.json` | 6/6 OK (plus `independent-review-1.json` OK) |
| T11 | Verify all 11 `INPUTS.json` `W11-CWP-SOURCES` paths/sizes/SHA-256 | 11/11 match |
| T12 | `python -m ruff check` on the two product files and both test files | `All checks passed!` (exit 0) |
| T13 | EOF/BOM/trailing-whitespace check on changed text files | **offline test file: no final newline** (IR-12 residual); others clean, no BOM |
| T14 | Derived sealed fixture (exact 3 sealed titles/URLs + external script) through the public CLI pages branch, entity `药明康德`, 2026-01-01…2026-10-21, `max_bytes=1048576` | exit 0; `candidates=[]`, `coverage=partial`, `no_documents_claimed=false`, limitations `["dynamic_content_unresolved","unclassified_document_links"]`; base module yields exactly the 3 sealed privacy/terms candidates |
| T15 | Scale probe: current vs base on a synthetic page with 1k/5k/10k material anchors, `max_items=30` | 1k: 0.10 s vs 0.02 s; 5k: 0.99 s vs 0.09 s; 10k: 4.79 s vs 0.65 s (see NR-10) |
| T16 | Re-run the decisive cases from the committed `git show a6d12a53:…official_discovery.py` bytes (18,436 B / `a008e1cb…`), after the concurrent worktree edit appeared | exit 0; IR-01 table/CN/deck positives, IR-02 budget, IR-03 legal/material, IR-04 page/item time, IR-05 fragment/query, IR-08 empty/hash, NR-01 nav (CN + EN, max_items=1 and 30), NR-02 single-link page time, NR-04 legal hybrid, and the sealed-derived fixture all reproduce the report's results; `review/evidence/review-2-head-bytes-probes.json` |

## Prior findings verification

Status is against the final `a6d12a53` product SHA. "PASS" means the finding's named defect and required behaviour are fixed; residuals are listed as new findings rather than hidden.

| ID | Status | Evidence (my runs) |
|---|---|---|
| IR-01 | **PASS** | `<tr><td>2027 Interim Results</td><td><a href="/files/ir2027.pdf">Download</a></td>` → 1 candidate, title `2027 Interim Results`; `aria-label="Q3 2026 Corporate Deck"` icon → candidate; `<img alt="Board Deck 2026">` → candidate; `FY2025 Annual Results` / `Interim Results 2026` / `Q1 2027 Financial Results` → 3 candidates; `2026年第三季度电话会纪要` → candidate, kind `investor_call_transcript`; `Corporate Deck 2026` → candidate. A dropped document-suffix link (legal/nav-vetoed PDF) adds `unclassified_document_links` and coverage `partial` instead of a clean index (e.g. `Privacy Statement` PDF → 0 candidates + limitation; `Annual Report 2025` + privacy PDF → 1 candidate + limitation). |
| IR-02 | **PASS** | `Media Briefing` and `Press Briefing` (dated articles) → 0 candidates; `Upcoming Events` / `Upcoming Careers Fair` → 0; `max_items=1` with `Upcoming Investor Conference` before `Annual Report 2025` → only `/files/ar2025.pdf` emitted; a lone `Notice of Upcoming Investor Conference` → 1 `index_notice` with `is_business_original=false`; 3 materials + 2 notices with `max_items=2` → 2 materials, `item_limit_reached` once. |
| IR-03 | **PASS** | `Legal Information - Investor Day 2026` + `Accessibility - Annual Report Archive` → 0 candidates; `Annual Report 2025 - Contact Information` → candidate; `Investor Presentation - Privacy Update` → candidate. Residual over-veto and missing bounded-heuristic disclosure: NR-04. |
| IR-04 | **PASS** | Page-level `<time datetime="2026-10-22">` in a `.content` div with 2 materials → both candidates, `published_date=None`, `excluded=[]`; item-scoped `<article><time datetime="2026-09-15T10:30:00Z">` → `2026-09-15`; sibling `<li>`: first dated 2021 excluded `before_window`, second `None` (no borrow); `data-date="2026-09-01"` wins; `<tr>` with a second `View` link does not borrow a date. Residual single-link page-level case: NR-02. |
| IR-05 | **PASS** | `/doc.pdf`, `/doc.pdf?dl=1`, `/doc.pdf#p2`, `/doc.pdf#p3` → exactly 2 candidates (plain + query; fragments deduped); base yielded 4. Query semantics stay distinct as documented. |
| IR-06 | **PASS** | Public CLI: missing `capture_id`, missing `url`, missing `mime_type`, empty `capture_id`, non-dict page row, missing/blank `entity`, missing/typed `start_date` → exit 2 with a JSON `official-source-failure/1` on stderr and **no** `Traceback`/`KeyError`; a single HTML file larger than `max_bytes` → `limitations == ["byte_limit_reached"]` exactly once; a file exactly at the cap → candidate and no byte limitation. |
| IR-07 | **PASS** | `/ok.pdf` `Annual Report 2025` + `http://[` → keeps the valid candidate and adds `invalid_anchor_url`; base raises `ValueError: Invalid IPv6 URL`; malformed-only page → 0 candidates + `invalid_anchor_url`, coverage `partial`. |
| IR-08 | **PASS** | `href=""`, `href="#"`, and an absolute link to the index URL → only the real `/real.pdf` candidate; `#page2` fragment-only is skipped by the self check. Query-only variant remains: NR-07. |
| IR-09 | **PASS** | All delivery JSON parses (T10). Independent walk reproduces the inventory totals exactly: audit 2052 / 166,731,220 B, holdout 65 / 17,360,200 B; 0 files of 486789 B; 0 files with body SHA `f1e822a8…`; 84 + 5 = 89 files in the 400–600 KB band; `faa5bf…` capture has only the 250 B input/consume pair, 0 B stderr, 2839 B stdout with SHA `1c33f18b…`; `body_available=false` is honest. Delivery metadata nits: NR-09. |
| IR-10 | **PASS** | `red_probe.py` rebuilds the base module from git `0d7ada21` and reproduces D1/D2/D3; my rerun is semantically identical to the delivered (UTF-16) output. D1: base labels Earnings Release/Presentation `investor_call_transcript` → current `investor_relations`; D2: base 3 privacy/terms candidates → current 0; D3: base 4 generic-nav candidates → current 0. |
| IR-11 | **PASS** | Date tests renamed/split (`test_page_level_timestamp_is_not_a_material_date`, `test_item_scoped_datetime_is_truncated_to_a_date`); socket comment now accurate; the unused `SEALED_RESULT_SHA256`/`DERIVED_FIXTURE_NOTE` constants are gone (SHA is in the docstring). Minor comment/assertion nits: NR-09. |
| IR-12 | **FAIL (partial, cosmetic)** | `_TRANSCRIPT_TITLE_TOKENS` is simplified to `("transcript","电话会","纪要")`; `" Cookie"` is removed; the comment is corrected. **But `tests/integration/test_official_discovery_offline.py` still has no final newline** (last bytes are `...not in call.stderr` with no `\n`), exactly the item IR-12 asked for. Also `半年报` is now mechanically redundant under the added `年报` token. |
| IR-13 | **PASS** | `delivery/w11/push-gate-rerun.log` is gone; delivery files are present with normal tracked bits (`git ls-files -v` = `H`, not skip-worktree); worktree clean at review start/end; `cleanup.json` records the sparse restoration and stray removals. No production roots/catalog/config writes (`companies/`, `.source_catalog/`, `catalog/` absent; both config hashes match). Nits: NR-09. |

## New findings

### NR-01 — Medium — Navigation/section links are emitted as material candidates and can consume the item budget ahead of real documents

**Evidence (my probes, current vs base `0d7ada21`):**

1. `<nav><a href="/investors/announcement">公告</a><a href="/investors/results">业绩</a></nav>` → current 2 candidates (`investor_relations`, `date_unknown`, `metadata_only=true`), coverage `partial`; base 0 candidates. A CN issuer's IR navigation is exactly this.
2. `max_items=1`, `<nav><a href="/investors/announcement">公告</a></nav><a href="/files/2025-report.pdf">2025年年度报告</a>` → current emits only the nav link and `item_limit_reached`; the real annual report is **not** a candidate. Base emits the annual report (the same slot-competition failure IR-02 fixed for notices).
3. Default `max_items=30`, `<a href="/investors/reports">Annual Reports</a>` + 30 real report PDFs → current emits the nav link + 29 reports and `item_limit_reached`; base emits 30 real reports with no item limit.
4. `<header><a href="/investors/results">Results</a><a href="/investors/reports">Annual Reports</a></header>` → 2 candidates; `<footer><a href="/reports">Reports</a></footer>` → 1 candidate. `Results` and `News Releases` are new admissions vs base (base 0), introduced by the broad `results`/`report`/`news release` material tokens.
5. `item_limit_reached`/`publication_date_unknown` then make the page `partial` even when every real document is dated, because a nav candidate has no date.

**Why Medium:** deterministic false positive plus real document loss under the existing item bound, with realistic EN and CN section labels; it contradicts the lane's "recover real material, do not emit navigation as material" purpose and the notice-budget rule.

**Required fix:** do not treat navigation/section anchors as `candidate` material: skip/demote anchors inside `<nav>`/`<header>`/`<footer>` (or with a section URL path and no document suffix and a generic section label such as `Annual Reports`/`Results`/`Reports`/`News Releases`/`公告`/`业绩`) to the deferred `index_notice` bucket. At minimum, rank document-suffix links ahead of non-suffix material links inside `max_items`. Add EN + CN regression tests with a nav link *before* a real report at `max_items=1` and at the default bound.

### NR-02 — Low — Single-link page-level `<time>` is still adopted as a material date and can exclude the only material

**Evidence:** `<div class="content"><time datetime="2026-10-22">Last updated</time><a href="/ar.pdf">Annual Report 2025</a></div>` → current `candidates=[]`, `excluded=[{"ar.pdf","2026-10-22","after_as_of"}]`, `limitations=[]`, `coverage=checked_index_only`; base identical. The fix's `_item_container` falls back to a `div` that contains exactly one link, so a page-level "Last updated" around a single material is indistinguishable from an item date. The new test only covers a two-link div.

**Required fix:** drop the generic `div` fallback (use `article`/`li`/`tr` only), or accept a `div` time only when the div is demonstrably an item (e.g. a heading/label plus one link and no page-level class); or explicitly record this as a known bounded limitation and narrow the "page-level time no longer excludes materials" claim. Low because pre-existing, single-container only, and the exclusion is visible in `excluded`.

### NR-03 — Low — `unclassified_document_links` is emitted for deliberate legal/navigation vetoes, producing false `partial` coverage

**Evidence:** `Privacy Statement` PDF → `limitations=["unclassified_document_links"]`, `partial`; `Annual Report 2025` + privacy PDF → 1 candidate + the same limitation; the sealed-derived fixture (3 privacy/terms PDFs + external script) → `limitations=["dynamic_content_unresolved","unclassified_document_links"]`, `partial`. By construction, any document-suffix link whose title lacks a legal/page/nav token is admitted by the suffix path, so this limitation can only fire for links that were *deliberately* excluded as legal/nav. Nearly every real IR page with a privacy/terms PDF will therefore report `partial` for a reason that is not incomplete coverage.

**Required fix:** separate an intentional legal/nav exclusion (e.g. `excluded_legal_document_links`, or no limitation at all) from a genuinely unclassified document link; keep the "no silent clean index" property for the latter. Low: conservative, never silent loss, only an inflated/ambiguous coverage signal.

### NR-04 — Low — Legal page-section veto still over-vetoes titles with a strong material clue

**Evidence:** `Annual Report 2025 - Legal Entity Changes` (`/ar.pdf`) → 0 candidates + `unclassified_document_links`; base 1 candidate. `2026 Annual Report - Accessibility Statement` → 0. The `_LEGAL_PAGE_TITLE_TOKENS` veto runs before the material-clue path, so one secondary word (`legal`, `accessibility`, `imprint`) removes a clear document. IR-03's required fix explicitly said not to let a single secondary token veto a title with a strong material token, or at minimum to record the denylist as a bounded heuristic; the delivery narrative says "correctly excludes" without that caveat.

**Required fix:** use structural/section signals (URL segment, `nav`/`footer`) for page-section vetoes or let a strong material clue win when the URL is a document; record the residual as a bounded heuristic in the delivery if not fixed. Low.

### NR-05 — Low — Item-title recovery can promote a 300-character prose blob to the title

**Evidence:** `<article><h2>Welcome to our investor centre</h2><p>Read our latest annual report and proxy statement for details about the meeting, voting and the board of directors.</p><a href="/wp-content/uploads/abc123.pdf">Download</a></article>` → candidate title `Welcome to our investor centre Read our latest annual report and proxy statement` (container text truncated at 300 chars). The candidate was already admitted by suffix in base (title `Download`), so this is not a new admission, but the title (and the shared classifier's kind input) is distorted, and a longer prose block can exceed a sane title length.

**Required fix:** prefer a heading/cell label, or cap the recovered title (e.g. 120 chars) and require the block text to be item-like; add a regression test. Low.

### NR-06 — Low — Multi-link table rows without a document suffix still lose the document silently

**Evidence:** `<table><tr><td>2026 Annual Report</td><td><a href="/download?id=42">Download</a><a href="/viewer?id=42">View</a></td></tr></table>` → 0 candidates, 0 limitations, `checked_index_only`. `_item_container` returns `None` when the row has two anchors, so the row title is never recovered; the anchor label `Download` has no clue and `/download` has no document suffix. Base also returned 0 (pre-existing gap), but the result is a silent clean index for a row that clearly names an annual report, contrary to IR-01's "no silent clean index" principle.

**Required fix:** if all anchors in the item resolve to the same resource, allow the container title; or use the row text when the anchor label is a generic action word (`download`/`view`/`open`); or emit a limitation when such an action anchor is dropped. Low.

### NR-07 — Low — Query-only self/pagination links are not recognized as self-references

**Evidence:** `<a href="?page=2">Annual Report 2025 page two</a>` → candidate `https://ir.example/ir?page=2` (`date_unknown`); base 0. The self check compares the query-bearing dedupe key with the page key, so a same-path query link passes. Requires a material-ish title, so Low.

**Required fix:** treat a URL whose scheme/netloc/path equals the index document as self (regardless of query), or skip pagination query params; add a test. Low.

### NR-08 — Low — Malformed page URL yields a clean empty result instead of a refusal/limitation

**Evidence:** page `url="not-a-url"` (or `"https://"`) through the library/CLI page-row path → 0 candidates, no limitations, `checked_index_only`, exit 0; relative anchors are silently skipped because `urljoin` cannot produce an absolute URL. The CLI now validates page-row keys but not the URL shape. Base identical (pre-existing). Low (malformed request only).

**Required fix:** validate `page["url"]` as an absolute `http(s)` URL with a hostname in the CLI/library and refuse with exit 2, or emit `invalid_index_url`. Low.

### NR-09 — Info — Delivery/metadata hygiene nits

- `tests/integration/test_official_discovery_offline.py` still lacks a final newline (IR-12 residual).
- `delivery/w11/probes/red-probe-output.txt` and `delivery/w11/test-run-stdout.txt` (and the prior review evidence stdout files) are UTF-16LE with BOM; git records them as binary and normal text tools cannot read them without decoding. Their content is valid and matches the recorded SHAs, but UTF-8 would be more reviewable.
- `delivery/w11/evidence_inventory.json` attributes the combined 400–600 KB band count (89) to the audit scope; my walk gives 84 audit + 5 holdout. `prepared_at` (`2026-10-23T23:20:00+00:00`) postdates the HEAD commit (`21:53Z`).
- `delivery/w11/cleanup.json` lists a `delivery/w11/handoff` write, but no `handoff.md`/`handoff.json` exists yet.
- The test module docstring says "two privacy/terms titles" while the fixture mirrors three sealed titles (four anchors); `test_legal_navigation_pdfs_are_not_candidates` asserts `coverage_status in {"partial","checked_index_only"}`, which is tautologically true.
- Empty `cw-pytest-basetemp/` parent directory remains after conftest cleanup (environment artifact, not a product write).

### NR-10 — Low — Deferred item truncation removes `max_items` as a work bound; per-candidate whole-page SHA-256 makes large indexes O(items × page_bytes)

**Evidence:** with `max_items=30`, a synthetic page of `N` material anchors takes: `N=1000` 0.10 s (base 0.02 s), `N=5000` 0.99 s (base 0.09 s), `N=10000` 4.79 s (base 0.65 s) — the current parser classifies every anchor and computes `index_source_sha256 = sha256(original)` per pending record (profile: 10,001 sha256 calls / 0.62 s for 5000 anchors), while base stops after 30 candidates. A byte-capped 8 MiB page with many anchor rows can therefore spend minutes and hold a large `pending` list, even though only 30 items are returned. (Recorded here rather than in a separate row because it is a resource regression, not a correctness one.)

**Required fix:** cache the page hash once per page, and cap pending collection (e.g. stop after `max_items` + a bounded notice allowance, recording `item_limit_reached`). Low: official IR pages are normally small (the sealed one is 486,789 B), and the byte bound still limits the input.

## Positives verified (independent)

- **All 13 prior findings were genuinely addressed in substance except IR-12's newline.** The two observed classification defects are fixed and the regression suite covers them; my differential probes against `0d7ada21` reproduce the RED and the corrected behaviour.
- **The sealed-evidence story is honest.** `faa5bf…/stdout.txt` is 2839 B / `1c33f18b…`; all 11 `INPUTS.json` W11 entries match byte count and SHA-256; full independent SHA-256 walk of both roots gives 2052/166,731,220 and 65/17,360,200 with 0 exact-size and 0 body-SHA hits; the capture directory contains no body; `body_available=false` is correct. The derived sealed fixture is explicitly a derived minimal fixture, not a replay, and the public CLI returns `candidates=[]`, `coverage=partial`, `no_documents_claimed=false` on it (base returns the 3 privacy/terms candidates).
- **Notice budget semantics work.** Notices require notice + business-event clues, are emitted after materials, never displace a real document under `max_items`, and the total candidate count stays bounded; `item_limit_reached` is emitted once and only when something was actually deferred.
- **Limit/transaction mechanics are sound.** Malformed hrefs no longer abort the page; duplicates are fragment-insensitive while query variants stay distinct; empty/`#`/self anchors are skipped; byte-limit truncation stays `partial` with one `byte_limit_reached`; exact-cap does not emit a false limit; unsupported MIME is a limitation and later HTML still parses; `item_limit_reached`/`publication_date_unknown` keep `no_documents_claimed=false`.
- **Receipt integrity and schema stability.** `receipt.event_sha256` recomputes exactly in all 61 probe cases; candidate/result/receipt key sets are identical to `0d7ada21`; no company/domain/year branch appears in the diff; the parse stays pure and the CLI discover branch remains a thin validator/transport wrapper; input bounds (`max_items` 1..30, `max_bytes` >0..8 MiB, 1..6 CLI pages, 64 KiB request) are still enforced.
- **Test/evidence counts are truthful.** 40 new + 36 existing = 76 collected; the exact delivered selection gives 47 passed / 29 deselected; JUnit has 47 cases with no failures; `test-run-stdout.txt` and JUnit SHAs match `test_results.json`; `ruff` passes.
- **No production writes.** `companies/`, `.source_catalog/`, `catalog/` are absent; both config hashes match the pre-lane values; the worktree was clean at review start, and the only mid-review product change is the concurrent uncommitted edit described above (not reviewer-owned, excluded from this review); `push-gate-rerun.log` is gone and delivery files are tracked normally.
- **The RED probe is reproducible.** `red_probe.py` rebuilds the base package from git `0d7ada21` (blob SHA `7d8fb129…`) and my rerun matches the delivered output semantics exactly.

## External limits / not verified

- The real 486,789 B IR body remains unavailable; I did not re-fetch it, reconstruct it, or claim the original replay passed. The derived sealed fixture is not an original replay.
- No live HTTP was used; `fetch_official_indexes` real transport/redirect/budget behaviour was only exercised by the existing MockTransport test (which passed). Nothing here proves full-site/search coverage.
- The nav/legal/section classifier is a bounded heuristic; my EN/CN examples are synthetic and cannot prove what a specific real site emits. The sealed page body is unavailable, so its nav anchors cannot be inspected.
- I did not run the full-repo suite (per the card; ROOT owns that), and I did not re-verify every prior-review probe (I re-ran the ones needed for the 13 findings and added my own 61-case differential set).
- Performance (NR-10) is measured only on synthetic pages; the item-budget interaction is deterministic, but the wall-clock impact on a real large index was not measured live.
- **Concurrent uncommitted product/test edits:** while this report was being written, another process modified `src/company_wiki/source_catalog/official_discovery.py` (observed 21,748 B / `bdfd5d14…` then 22,790 B / `855e57de…`, mtime 23:08:49) and `tests/integration/test_official_discovery_offline.py` (29,884 B / `dd555b43…`, mtime 23:09:30), and created untracked dirs. I did not review, approve, run the author tests against, or write that version; it is outside `a6d12a53`. If it is the intended next fix it must be committed as a new SHA and re-reviewed. My findings remain bound to `a6d12a53` via T16.

## Required fixes before handoff

1. **NR-01 (Medium, blocking).** Do not emit navigation/section links as `candidate` material or let them consume `max_items` ahead of document links. Handle `<nav>`/`<header>`/`<footer>`/section URLs (EN + CN labels), and add the `max_items=1` and default-bound regression tests described above. Re-run the 40 + 7 matrix and return for re-review of the new SHA.
2. **IR-12 residual (Low, trivial).** Add the missing final newline to `tests/integration/test_official_discovery_offline.py`; while touching the token list, remove the now-redundant `半年报` member.
3. **Delivery narrative honesty (Low, required because the package is the handoff artifact).** `root_followup.md` line 10 ("修复后的 discovery 已能正确排除隐私/条款导航…") and the findings table's "已修" wording should be narrowed for the bounded heuristics: single-link page-level `<time>` (NR-02), legal page-section over-veto (NR-04), and the `unclassified_document_links` false-partial (NR-03). Either fix these or record them explicitly as known limitations for ROOT; do not present them as fully correct.
4. **Recommended, non-blocking:** NR-05 (cap recovered title), NR-06 (multi-link row recovery), NR-07 (query-only self), NR-08 (page URL validation), NR-09 (UTF-8 logs / inventory scope / handoff file), NR-10 (page-hash cache + pending cap). These do not by themselves block handoff, but NR-05/NR-06 are cheap and align with IR-01's "no silent loss" goal.

## Conclusion

The author fixed the two observed classification defects, addressed the High/Medium review-1 findings, retained honest RED evidence, and kept the sealed-evidence, schema, layering, budget and cleanup properties intact. The delivered test counts are truthful and reproducible.

I cannot approve handoff yet because the broadening that fixed IR-01 also re-admits navigation as material: a CN/EN section link can now be a `candidate` and, at the item bound, deterministically displaces a real document (NR-01, Medium). The remaining residuals (single-link page-level dates, legal over-veto, false-partial limitations, prose titles, multi-link rows, query-only self-links, malformed page URLs, deferred-truncation cost) are bounded and mostly pre-existing, but two of them are currently described as fixed in the handoff narrative. Fix NR-01, add the final newline, and record or fix the bounded residuals; then re-review the final product SHA.
