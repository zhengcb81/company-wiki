# Independent review 3 — W11-CWP-SOURCES (fresh review of `2e1dfd04`)

- Reviewer role: **independent re-reviewer** (not the author; no part in writing or fixing this code).
- Review window: 2026-10-23 23:14–23:25 Europe/London.
- Workspace: `C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery`.
- Interpreter: `C:/Users/郑曾波/Projects/company-wiki/.venv/Scripts/python.exe` (3.14.2, Windows), pytest 9.1.1.
- Constraints honoured: 0 network, 0 model calls, 0 downloads; production catalog/lake never opened or written; sealed evidence read-only; product, tests and author delivery artifacts not modified by this review. My scratch was `tmp/review3/` and was removed; the only files I added are `delivery/w11/review/independent-review-3.*` and `delivery/w11/review/evidence/review-3-*`.
- Freshness: I did **not** reuse the `a6d12a53` verdict. All product probes load the committed `2e1dfd04` blob via `git show 2e1dfd04:src/company_wiki/source_catalog/official_discovery.py` (22,173 B / SHA-256 `4eaeee5f…`), with `a6d12a53` loaded separately only for differential checks.

## Verdict

**CHANGES REQUIRED — one new High regression.**

Every item the parent asked me to check passes **except the "no new regressions" check**, which fails on R3-01: NR-01 navigation no longer becomes a candidate and cannot consume `max_items`; IR-12's newline and `半年报` are fixed; NR-02/03/04/05/07/08/10 are fixed; notices, limits, receipt integrity, schema, `no_documents_claimed`, pure parse/thin CLI, and no-production-writes are intact; the delivery narrative records NR-06 and the legal/nav heuristic as bounded limits.

However, the round-2 section-label rule introduced a **silent regression on document files whose anchor text is exactly a section label**: `Annual Report`, `Annual Reports`, `Press Release`, `News Release`, `Announcement`, `Report`, `Results`, `公告`, `业绩`, `报告`, `Financial Reports` pointing at a `.pdf` are now dropped with **0 candidates, no limitation, `coverage_status=checked_index_only`**. Base `a6d12a53` emitted them. CN announcement tables (`公告` × N PDFs), EN press-release tables (`Press Release`/`Announcement` PDFs), and dated list items reproduce it through the public CLI. This is the same class of silent material loss the lane exists to fix, so it must be corrected before handoff.

## Reviewed version and exact SHAs

| Item | Value |
|---|---|
| branch | `codex/r1-w11-source-recovery-20261023` |
| reviewed HEAD | `2e1dfd041fdfb9e14a0a1b911049b077df1e06d4` (`2e1dfd04`) |
| parents | `a6d12a53` (review 2), `ecc7d622` (review 1), lane base `0d7ada21` |
| worktree status | product/test files clean (CRLF checkout only); untracked `delivery/w11/handoff.md`, `delivery/w11/push-gate-round2.log`; reviewer files untracked |

| Path | Worktree B / SHA-256 | HEAD blob B / SHA-256 |
|---|---|---|
| `src/company_wiki/source_catalog/official_discovery.py` | 22,790 / `855e57dec9c0f6971fdb7f8d10216086d981e2f9fa9f46ec78bc0e8c1d1ad279` | 22,173 / `4eaeee5fb8317d11f610facd587218dd8db394840b0e38f72e4b7bb7b3c096cd` |
| `src/company_wiki/source_catalog/official_source_cli.py` | 13,362 / `bdd06d5728dc25ef9a7433e5d7c1c89534f3fa52b9dd6e15ce7867e40d9c6162` | 13,081 / `7fb9a8031e6d98fd9788518b9fb41904179f326fba57c2bbb08fb48d1dee1adf` |
| `tests/integration/test_official_discovery_offline.py` | 29,924 / `8e6a558d981216ee2bd438a053f03ba48d27f53342d9950104a5f370694d8368` | same (no CRLF) |
| `tests/integration/test_official_source_flow.py` | 56,854 / `f374c7d7ff39677c9b30c9f4ac9c8429740c7e8df1655fb95efc3bb453564b66` | 55,444 / `ff255559a09fbb00dfe6e2f233f2eebb779d2f0daf43fcb6d6de6c1aaaa7b142` |
| `delivery/w11/test_results.json` | 3,120 / `4a50f38251659315e77e536de7668d4f268676c1adf7fae917c295d73d9f3cdb` | 3,066 / `1368acec…` |
| `delivery/w11/test-results.xml` | 9,377 / `88b883e82ec041c3dddbc05b473c81e111e194b5a9105d36b3af7ece4e9b0446` | same |
| `delivery/w11/test-run-stdout.txt` | 1,125 / `00bfa74658684b13ad47ae00aa109bc3bb9440a418d657aab7ee856e1c099a67` | 1,110 / `4720c8c8…` |
| `delivery/w11/probes/red-probe-output.txt` | 2,931 / `54dd99e10d7f95492f7a25b25296d811456c513b52d98366cbe92f5195542ce1` | 2,837 / `2a5e5cf0…` |
| `delivery/w11/root_followup.md` | 2,997 / `5122c30fbe0ac3b5afac0d3e67a7bc179bd292f2b45194a6a29879f24ccc7116` | 2,971 / `86ac7417…` |
| `delivery/w11/handoff.md` (untracked) | 5,246 / `5cf07b1b57c882bb5dcd6882cdd5932a64e1b226f730270521dd1483f200653e` | not in `2e1dfd04` |
| `config/source_catalog.yaml` | `3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968` | unchanged |
| `config.yaml` | `15541ba44e9621456cab7c6956c4f33be3f33e9b20f7053f1dc4aa6f0371bd1e` | unchanged |

`test_results.json.input_source_shas` (855e57de, bdd06d57, f374c7d7, 8e6a558d) match the current worktree files; the reviewed product bytes are the HEAD blobs (`4eaeee5f`, `7fb9a803`), which differ from the worktree only by CRLF.

## Tests I ran (own commands)

All offline; `PYTHONPATH=<workspace>/src;<workspace>/tests` unless noted.

| # | Purpose / command | Result |
|---|---|---|
| T1 | In-session import proof for both modules | exit 0; both `__file__` under workspace `src` |
| T2 | `pytest tests/integration/test_official_discovery_offline.py -q -p no:cacheprovider` | **48 passed in 26.10 s**, exit 0 |
| T3 | `pytest tests/integration/test_official_source_flow.py -q -p no:cacheprovider` | **36 passed in 89.07 s**, exit 0 |
| T4 | Delivered selection (`-k 'discovery or official_index_http or cn_fundraising or TestMaterial or TestNonMaterial or TestTimeWindow or TestUrlAndDedup or TestPagePayload or TestLimits or TestPublicCli'`) | **55 passed, 29 deselected in 27.12 s**, exit 0; JUnit 55 cases, 0 failures/errors; delivered 55/0/0, 10.35 s |
| T5 | 75-case differential probe from committed bytes (`git show 2e1dfd04:…`, old `a6d12a53` loaded separately) covering NR-01/02/03/04/05/07/08/10, IR-01 positives, notices, limits, dedup, malformed URLs, exact-label regression | exit 0; `review/evidence/review-3-probe-output.json`; all non-error cases have recomputed `receipt.event_sha256` and `no_documents_claimed=false` |
| T6 | CLI + scale: invalid page URL / malformed row / byte cap / normal via public subprocess; 1k/5k/10k material-anchor scaling; `hashlib.sha256` call counting | invalid URL → exit 2 JSON no traceback; malformed row → exit 2; byte cap → exactly one `byte_limit_reached`; 10k anchors **0.808 s vs a6d12a53 7.292 s**; 30-anchor page = **1 whole-page hash** (32 calls total) vs 30 (61 calls) at `a6d12a53`; `review/evidence/review-3-cli-scale.json` |
| T7 | CLI reproduction of exact section-label documents (CN `公告` table; EN `Press Release`/`Announcement` table) | exit 0, `candidates=[]`, `coverage=checked_index_only`, `limitations=[]`, `no_documents_claimed=false` — the R3-01 regression end to end; `review/evidence/review-3-cli-section-labels.json` |
| T8 | Delivery checks: all `delivery/w11/**/*.json` parse; JUnit/log SHAs match `test_results.json`; JUnit 55 cases no failures; 11/11 `INPUTS.json` W11 byte/SHA matches | all pass (red-probe JSON needs `utf-8-sig` because of a BOM — see R3-02) |
| T9 | `ruff check` on both product and both test files | `All checks passed!` |
| T10 | IR-12 checks on committed bytes | test file ends with `\n` (29,924 B); `半年报` absent from the material tokens |
| T11 | Product/state checks | `companies/`, `.source_catalog/`, `catalog/` absent; config hashes unchanged; product/test content diff clean apart from CRLF |

## Prior findings verification

| ID | Status | Evidence (my runs, committed 2e1dfd04 bytes) |
|---|---|---|
| **NR-01** (nav/section candidates + budget) | **PASS for the named defect** | `<nav>公告/业绩</nav>` → 0 candidates (old 2); header `Results`/`Annual Reports`, footer `Reports`, `News Releases` → 0 (old 4); `max_items=1` with nav `公告` before `2025年年度报告` → the report is emitted; default `max_items=30` with `Annual Reports` nav + 30 real PDFs → 30 PDFs, no nav; CN variant same. The new **R3-01** regression is a side effect of the section-label rule, not a failure of the NR-01 requirement itself. |
| **IR-12** (test newline, 半年报) | **PASS** | Committed test file ends with a newline; `半年报` removed from the strong tokens. |
| **NR-02** (single-material page-level time) | **PASS** | Single material under a page-level `<time datetime="2026-10-22">` → 1 candidate with `published_date=None`, `excluded=[]`; two-material page still dates `None`; item-scoped `<time>` → `2026-09-15`; sibling `<li>` does not borrow. |
| **NR-03** (legal/nav false partial) | **PASS** | Dated annual report + privacy PDF → 1 candidate, `limitations=[]`, `coverage=checked_index_only`; privacy-only/contact-only pages → 0 candidates, no limitations; sealed-derived 3 privacy/terms PDFs + external script → 0 candidates, `limitations=["dynamic_content_unresolved"]`, `partial`. |
| **NR-04** (legal over-veto) | **PASS** | `Annual Report 2025 - Legal Entity Changes` (`/ar.pdf`) → candidate; `Legal Information - Investor Day 2026` and `Accessibility - Annual Report Archive` → 0. |
| **NR-05** (title cap) | **PASS** | Prose container → candidate title length **116** (≤120); the no-space container falls back to `Download` rather than an unbounded title. Worst-case truncation is 120 content chars + ellipsis (≤121) and the author test allows 121; the requested ≤120 bound is met in practice. |
| **NR-06** (multi-link Download+View rows) | **PASS as bounded limit** | Still not fixed by design; `findings.md`, `root_followup.md` and `handoff.md` record it as a bounded limit rather than a fix. |
| **NR-07** (query-only self link) | **PASS** | `?page=2` and absolute `https://ir.example/ir?page=2` skipped; only `/real.pdf` remains (old 2). |
| **NR-08** (invalid page URL) | **PASS** | Library raises `ValueError("invalid_index_page_url")` for `not-a-url`, `https://`, `ftp://`, credentials; CLI → exit 2 JSON `official-source-failure/1`, no traceback. |
| **NR-09** (delivery hygiene) | **PARTIAL** | EOF/log-encoding/inventory band counts/tautological assertion fixed (logs now UTF-8; inventory now 84 + 5 = 89). Remaining: `handoff.json` absent, `handoff.md` untracked, 0 B `push-gate-round2.log` untracked, red-probe JSON has a UTF-8 BOM (strict `json.loads` fails without `utf-8-sig`), `prepared_at` still postdates the commit. See R3-02. |
| **NR-10** (bounded work) | **PASS** | `index_source_sha256` computed once per page (30-anchor page: 1 whole-page hash vs 30); pending cap reports `item_limit_reached`; 10k anchors **0.808 s** vs **7.292 s** at a6d12a53; 400-anchor page returns 30 candidates + `item_limit_reached`. |
| **Round-1 behaviours** | **PASS** | IR-01 positives still work (table `Download` → `2027 Interim Results`; aria-label; img alt; `FY2025 Annual Results`/`Interim Results 2026`/`Q1 2027 Financial Results`; CN `电话会纪要` → `investor_call_transcript`; `Corporate Deck`); notices still `index_notice` and never consume the budget; malformed href/fragment/empty-self/byte-limit behaviour unchanged. |

## New findings

### R3-01 — High — Exact section-label titles pointing at document files are silently dropped

**Evidence (committed `2e1dfd04` bytes vs `a6d12a53`):**

1. Every one of these `.pdf` links → **0 candidates, `limitations=[]`, `coverage=checked_index_only`** at `2e1dfd04`, while `a6d12a53` emitted 1 candidate each: `Annual Report`, `Annual Reports`, `Press Release`, `News Release`, `Announcement`, `Report`, `Results`, `公告`, `业绩`, `报告`, `Financial Reports`.
2. CN announcement table (2 rows, `2026-08-30` + `/upload/2026/a1.pdf` titled `公告`, `2026-08-29` + `a2.pdf` titled `公告`) → **0 candidates, no limitations, `checked_index_only`**; `a6d12a53` → 2 candidates. The same table through the public CLI → exit 0, `candidates=[]`, `coverage=checked_index_only`, `limitations=[]`, `no_documents_claimed=false`.
3. EN press-release table (`Press Release` PDF + `Announcement` PDF) → **0 candidates**; `a6d12a53` → 2; public CLI same clean empty result.
4. Dated list/article items (`<li><time …></time><a href="…pdf">公告</a></li>`, `<article><time …></time><a href="…pdf">Press Release</a></article>`) → 0; old 1.
5. Table row `<td>Annual Report</td><td><a href="/files/ar.pdf">Download</a></td>` → 0; old 1. Query variant `/files/doc.pdf?x=1` titled `Press Release` → 0; old 1.

**Cause:** `_is_material_link` checks `_is_section_label(folded)` before the document-path branch; `_SECTION_LABEL_TITLES` contains these exact labels, and the check ignores `_is_document_path(path)`. The code comment says section labels are "navigation to a listing, not a document", but a `.pdf` link is a document.

**Impact:** silent under-recovery of core material classes (press releases, announcements, annual reports, CN announcements), with a result that claims a clean `checked_index_only` index and no limitation — the exact failure mode the lane was created to eliminate. This is a regression relative to `a6d12a53`. Until it is fixed, the delivery narrative's claim that the fixed discovery "把真正的业务材料锚（deck/report/transcript/业绩说明会等）作为候选输出" is overbroad: exact `Press Release`/`Announcement`/`公告` document files are not output.

**Required fix:** apply the section-label exclusion only when the URL is not a document path (e.g. `if _is_section_label(folded) and not _is_document_path(path): return False`, or move the check after the document/strong-clue branches). Add tests for exact section labels with document suffixes, including a CN announcement table (`公告` PDFs) and an EN `Press Release`/`Announcement` table; re-run the matrix and re-review the new SHA.

### R3-02 — Low — Delivery packaging remains incomplete

- `delivery/w11/handoff.json` is absent; `delivery/w11/handoff.md` (5,246 B) is untracked and not part of `2e1dfd04`; `delivery/w11/push-gate-round2.log` is a 0-byte untracked file. The card requires `handoff.md` + `handoff.json` in the final handoff commit, so the final report-only commit must add them and remove the stray log.
- `delivery/w11/probes/red-probe-output.txt` is UTF-8 with a BOM; `json.loads(bytes)` fails unless decoded with `utf-8-sig`. The content itself is valid (D1/D2/D3 base/current reproduced).
- `evidence_inventory.json.prepared_at` (`2026-10-23T23:35:00+00:00`) still postdates the `2e1dfd04` commit (`22:12:35Z`); the band counts are now correct (84 audit + 5 holdout).
- These are packaging items, not product defects.

### R3-03 — Info — Bounded residuals confirmed and worth recording in the known-limits section

- Header/footer strong material titles without a document suffix are dropped by design (`<header><a href="/ar/latest">Annual Report 2025</a></header>` → 0; old 1); this is the structural-chrome rule.
- `/ir/` (trailing slash) is not recognized as the same document as `/ir`; it remains a candidate. Pre-existing, low.
- `pending_limit = max_items*10 + 30` can drop later documents behind >330 non-document materials on very large pages; `item_limit_reached`/`partial` is reported, so it is honest but worth recording.
- Title truncation is 120 content characters plus `…` (worst case 121); the prose fixture is 116.
- `Annual Report 2025 Legal Notice` becomes `index_notice` because of the `notice` token, despite being a document PDF; bounded notice heuristic.

## Positives verified (independent)

- **NR-01 genuinely fixed:** CN/EN nav/header/footer section links are no longer candidates; `max_items=1` keeps the real report; default `max_items=30` keeps all 30 real PDFs ahead of a section link; the candidate ordering (document suffix → other materials → notices) works.
- **IR-12 fixed:** final newline present; `半年报` removed.
- **NR-02/03/04/05/07/08/10 fixed:** single-material page-level time keeps `date_unknown`; legal/nav exclusion no longer produces false partial; legal-word document files survive; title recovered ≤116 in the prose fixture; `?page=2` self link skipped; invalid page URL refused with ValueError/CLI exit 2; page hash computed once and pending bounded (10k anchors 0.808 s vs 7.292 s; 1 vs 30 whole-page hashes).
- **No new regressions in notices/limits/schema/transaction mechanics:** event notices are `index_notice` and never consume the material budget; 31 materials → 30 + one `item_limit_reached`; 30 materials → no item limit; byte limit → one `byte_limit_reached` + `partial`; malformed href isolated with `invalid_anchor_url`; fragment-insensitive dedupe with distinct queries; empty/`#` skipped; unsupported MIME limitation does not stop later HTML; `no_documents_claimed=false` everywhere; candidate/result/receipt keys identical to `a6d12a53`; `receipt.event_sha256` recomputes in all non-error probe cases.
- **Delivery narrative records NR-06 and the legal/nav heuristic as bounded limits** in `root_followup.md` (committed) and `handoff.md` (untracked), and `findings.md` explicitly marks NR-06 as "未修，如实记为 bounded limit". No false "fully correct" claim for the multi-link row.
- **Tests/evidence are truthful:** 48 new + 36 existing = 84; delivered selection 55 passed / 29 deselected; JUnit 55 cases, 0 failures; log and JUnit SHAs match `test_results.json`; `input_source_shas` match the worktree; `ruff` passes; all delivery JSON parses (red-probe with `utf-8-sig`); 11/11 `INPUTS.json` W11 entries match; config hashes unchanged; `companies/`, `.source_catalog/`, `catalog/` absent.
- **RED evidence still reproducible:** `red-probe-output.txt` decodes (UTF-8 BOM) to the same D1/D2/D3 base/current story with base blob `7d8fb129…`.

## External limits / not verified

- The 486,789 B IR body remains unavailable; no replay claim. The derived sealed fixture is not an original replay.
- No live HTTP; real transport/redirects only via the existing MockTransport test.
- The nav/legal/section classifier remains a bounded heuristic; R3-01's CN/EN fixtures are synthetic but realistic, and the sealed page body cannot be inspected to confirm its exact anchor labels.
- I did not run the full-repo suite; the review covers the W11 product/tests plus the 75-case differential probe and CLI/scale checks.
- R3-03's pending-cap/header-CTA behaviour is measured on synthetic pages only.

## Required fixes before handoff

1. **R3-01 (High, blocking):** do not apply the exact section-label veto to document-suffix URLs; a `.pdf` titled `Press Release`/`Announcement`/`Annual Report`/`公告`/`业绩`/`报告`/`Results` must remain a candidate. Add the CN announcement-table and EN press-release-table regression tests (with `.pdf`) and re-run the 48/55/84 matrix; then submit the new SHA for a fresh review.
2. **R3-02 (Low, packaging):** add `delivery/w11/handoff.json`, commit `handoff.md`, remove the 0-byte `push-gate-round2.log`, write the red-probe JSON without a BOM (or decode with `utf-8-sig`), and correct `prepared_at` so it does not postdate the commit.
3. **R3-03 (Info):** add the header/footer strong-CTA behaviour, trailing-slash self link, pending cap, 120+ellipsis title cap and legal-notice disposition to the handoff "known limits"; they are bounded and do not block by themselves.

## Conclusion

`2e1dfd04` fixes NR-01, IR-12, NR-02/03/04/05/07/08/10 and keeps the notice, limit, receipt, schema, CLI, performance and no-production-write properties intact; the delivery narrative now records NR-06 and the heuristic limits. It is not approvable because the section-label rule silently drops document files titled with exact section labels (`Press Release`, `Announcement`, `Annual Report`, `公告`, `业绩`, `报告`, `Results`, …) while reporting a clean `checked_index_only` index. The fix is narrow (gate the section-label check on `_is_document_path`), but it is a functional under-recovery regression and must be corrected and re-reviewed.
