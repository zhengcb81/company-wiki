# Independent review 4 — W11-CWP-SOURCES (fresh review of `6b538ca2`)

- Reviewer role: **independent re-reviewer** (not the author; no part in writing or fixing this code).
- Review window: 2026-10-23 23:26–23:40 Europe/London.
- Workspace: `C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery`.
- Interpreter: `C:/Users/郑曾波/Projects/company-wiki/.venv/Scripts/python.exe` (3.14.2, Windows), pytest 9.1.1.
- Constraints honoured: 0 network, 0 model calls, 0 downloads; production catalog/lake never opened or written; sealed evidence read-only; product, tests and author delivery artifacts not modified by this review. My scratch was `tmp/review4/` and was removed; the only files I added are `delivery/w11/review/independent-review-4.*` and `delivery/w11/review/evidence/review-4-*`.
- Freshness: all product probes load the committed `6b538ca2` blob via `git show 6b538ca2:src/company_wiki/source_catalog/official_discovery.py` (22,353 B / SHA-256 `6bba88a2…`); `2e1dfd04` was loaded separately only for differential checks.

## Verdict

**APPROVE — the product SHA is approved for handoff.**

R3-01 is genuinely fixed: all 11 exact section labels pointing at `.pdf` documents are candidates again, including table rows and dated `<li>`/`<article>` items; the same labels as listing links (no document suffix) and nav/header/footer section anchors remain non-candidates; the `max_items=1` and default-bound nav cases still pass. The previously passing set (NR-01/02/03/04/05/07/08/10, IR-12, notices/budget/limits, receipt/schema, `no_documents_claimed`, pure parse/thin CLI, no production writes, ruff) re-verifies on this SHA, and the packaging items (BOM-free probe output, gate log removal, test counts/log hashes) match.

No product change is required. The remaining items are **handoff-document completion only**: `delivery/w11/handoff.json` is still absent, and the handoff known-limits should add the extensionless-document-endpoint residual. These do not require another product review.

## Reviewed version and exact SHAs

| Item | Value |
|---|---|
| branch | `codex/r1-w11-source-recovery-20261023` |
| reviewed HEAD | `6b538ca2f18fb8d5805f2ff59a41404b6e8302cd` (`6b538ca2`) |
| parents | `2e1dfd04` (review 3), `a6d12a53` (review 2), `ecc7d622` (review 1), lane base `0d7ada21` |
| worktree status | product/test content clean (CRLF checkout only); only untracked `delivery/w11/handoff.md` plus reviewer files |

| Path | Worktree B / SHA-256 | HEAD blob B / SHA-256 |
|---|---|---|
| `src/company_wiki/source_catalog/official_discovery.py` | 22,972 / `7436057e7291d336f2084f3fec0b912b3b32c15ae6690a96b8ff3a0c4af2f6b5` | 22,353 / `6bba88a286f588caad6d3de6235eff3effe15204a07a91883d03ae1bc458493d` |
| `src/company_wiki/source_catalog/official_source_cli.py` | 13,362 / `bdd06d5728dc25ef9a7433e5d7c1c89534f3fa52b9dd6e15ce7867e40d9c6162` | 13,081 / `7fb9a8031e6d98fd9788518b9fb41904179f326fba57c2bbb08fb48d1dee1adf` |
| `tests/integration/test_official_discovery_offline.py` | 31,358 / `b1a0da0228b3b077c076ea1a4665728dd022fc33358248d16c53bc4d9dd16069` | same (no CRLF) |
| `tests/integration/test_official_source_flow.py` | 56,854 / `f374c7d7ff39677c9b30c9f4ac9c8429740c7e8df1655fb95efc3bb453564b66` | 55,444 / `ff255559a09fbb00dfe6e2f233f2eebb779d2f0daf43fcb6d6de6c1aaaa7b142` |
| `delivery/w11/test_results.json` | 3,120 / `bf7b96bed13bb6874a7a44616b442657f7d0a0557f18e3b9a3a4660bda74c41c` | 3,066 / `0bbfb0a5…` |
| `delivery/w11/test-results.xml` | 12,268 / `749f18b1d2d7c1062743d785e8c7212fa0eb26e9e89ff6b81d2be860557c5b54` | same |
| `delivery/w11/test-run-stdout.txt` | 1,122 / `973fdbb236d66be41651905d2fa728d3d12b080555f76a4b4de0e4988e351ebd` | 1,107 / `7d58fc67…` |
| `delivery/w11/probes/red-probe-output.txt` | 2,928 / `e4d1fd13b517ce019cd46717110c023080d34e7ba0552a7a2debfa9926ae4855` | 2,834 / `db9de964…` |
| `delivery/w11/root_followup.md` | 2,997 / `5122c30fbe0ac3b5afac0d3e67a7bc179bd292f2b45194a6a29879f24ccc7116` | 2,971 / `86ac7417…` |
| `delivery/w11/evidence_inventory.json` | 8,275 / `0dcdc565b1104aec710b7e9e31bd7abc2965b8026bfd16bfb2cb735a76e514dc` | 8,089 / `0eaa2e77…` |
| `delivery/w11/handoff.md` (untracked) | 5,765 / `e34cc459e7cfb3bf30bb2a6dc4f2d40c6222cb818fcb796cbefbf704f53bffec` | not in `6b538ca2` |
| `config/source_catalog.yaml` | `3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968` | unchanged |
| `config.yaml` | `15541ba44e9621456cab7c6956c4f33be3f33e9b20f7053f1dc4aa6f0371bd1e` | unchanged |

`test_results.json.input_source_shas` (7436057e, bdd06d57, f374c7d7, b1a0da02) match the current worktree files; the reviewed product bytes are the HEAD blobs (`6bba88a2`, `7fb9a803`), which differ from the worktree only by CRLF.

## Tests I ran (own commands)

| # | Purpose / command | Result |
|---|---|---|
| T1 | Collected counts per file | **62 new + 36 existing = 98** |
| T2 | `pytest tests/integration/test_official_discovery_offline.py tests/integration/test_official_source_flow.py -q -p no:cacheprovider` | **98 passed in 87.51 s**, exit 0 |
| T3 | Delivered selection (`-k 'discovery or official_index_http or cn_fundraising or TestMaterial or TestNonMaterial or TestTimeWindow or TestUrlAndDedup or TestPagePayload or TestLimits or TestPublicCli'`) | **69 passed, 29 deselected in 17.16 s**, exit 0; JUnit 69 cases, 0 failures/errors |
| T4 | 78-case differential probe from committed bytes (`git show 6b538ca2:…`; old `2e1dfd04` separately): R3-01 exact labels/listing/nav/table/dated, NR-01/02/03/04/05/07/08/10, IR-01 positives, notices, limits, dedup, malformed URLs | exit 0; `review/evidence/review-4-probe-output.json`; all non-error cases recomputed `receipt.event_sha256` and `no_documents_claimed=false`; 30 non-empty schema-key comparisons identical |
| T5 | CLI + scale: CN announcement table, EN press-release table, nav listing, invalid URL, malformed row, byte cap; 1k/10k scaling; `hashlib.sha256` counting | exact-label tables → 2 candidates each; nav listing → 0; invalid URL/malformed row → exit 2 JSON no traceback; byte cap → one `byte_limit_reached`; 10k anchors **0.314 s** vs `2e1dfd04` **0.332 s**; 30-anchor page **1 whole-page hash** (32 calls); `review/evidence/review-4-cli-scale.json` |
| T6 | Packaging/evidence: red-probe BOM check/parse; gate-log presence; `test_results.json` vs JUnit/log hashes; JUnit 69 cases; full-run 98; `handoff.json`; `prepared_at` | red output UTF-8 **BOM-free** and parses; `push-gate-round2.log` gone; log/JUnit SHAs match; 69 cases/0 failures; full 98 reproduced; `handoff.json` **absent**; `prepared_at` 23:40Z still postdates the 22:25Z commit |
| T7 | Delivery/product state: all delivery JSON, 11/11 `INPUTS.json`, config hashes, production roots, ruff, in-session `__file__` | all pass; config unchanged; `companies/`, `.source_catalog/`, `catalog/` absent; `ruff` clean; modules under workspace `src` |
| T8 | IR-12 committed bytes | test file ends with newline (31,358 B); `半年报` absent |
| T9 | RED evidence | `red-probe-output.txt` parses (BOM-free), base blob `7d8fb129…`, D1/D2/D3 base/current story intact |

## Prior findings verification

| ID | Status | Evidence (committed 6b538ca2 bytes) |
|---|---|---|
| **R3-01** (exact section labels + docs) | **PASS** | 11/11 `.pdf` exact labels → 1 candidate each (2e1dfd04 → 0): Annual Report, Annual Reports, Press Release, News Release, Announcement, Report, Results, Financial Reports, 公告, 业绩, 报告. Table rows (Annual Report/公告/Press Release) → 1; dated `<li>`/`<article>` for 公告 and Press Release → candidate with `2026-08-30`; same labels as listing links (no suffix) → 0; nav/header/footer section anchors → 0; `max_items=1` and default-bound nav tests pass; public CLI on CN/EN announcement tables → 2 candidates each. |
| **NR-01** (nav/budget) | **PASS** | `<nav>公告/业绩</nav>` and header/footer `Results`/`Annual Reports`/`Reports` → 0; `max_items=1` nav 公告 before `2025年年度报告` → report emitted; default `max_items=30` nav + 30 real PDFs → 30 PDFs, no nav (EN and CN). |
| **IR-12** | **PASS** | Committed test file ends with newline (31,358 B); `半年报` removed. |
| **NR-02** | **PASS** | Single material under page-level `<time datetime="2026-10-22">` → 1 candidate date None, `excluded=[]`; two-material page dates None; item-scoped `<time>` → `2026-09-15`; sibling `<li>` does not borrow. |
| **NR-03** | **PASS** | Dated annual report + privacy PDF → 1 candidate, `limitations=[]`, `checked_index_only`; privacy-only → 0 candidates no limitations; sealed-derived 3 privacy/terms PDFs + script → 0 candidates, `limitations=["dynamic_content_unresolved"]`. |
| **NR-04** | **PASS** | `Annual Report 2025 - Legal Entity Changes` (`/ar.pdf`) → candidate; `Legal Information - Investor Day 2026` and `Accessibility - Annual Report Archive` → 0. |
| **NR-05** | **PASS** | Prose container → title 116 chars (≤120); no-space container falls back to `Download`; worst-case 120 content + ellipsis (≤121) matching the author test. |
| **NR-06** | **PASS as bounded limit** | Still not fixed by design; recorded in `findings.md`, `root_followup.md` and `handoff.md` known-limits ("未修"). |
| **NR-07** | **PASS** | `?page=2` and absolute same-path query skipped; only `/real.pdf` remains. |
| **NR-08** | **PASS** | Invalid page URL (`not-a-url`, `https://`, `ftp://`, credentials) → `ValueError`; CLI → exit 2 JSON, no traceback. |
| **NR-10** | **PASS** | Page SHA once (32 calls, 1 whole-page hash); pending cap → `item_limit_reached`; 10k anchors 0.314 s vs 0.332 s at 2e1dfd04; 400-anchor page → 30 candidates + `item_limit_reached`. |
| **NR-09 / R3-02 packaging** | **PARTIAL (handoff-only)** | BOM-free red-probe, gate log gone, log/JUnit hashes match, selection 69 and full 98 verified. Still open: `handoff.json` absent; `prepared_at` 23:40Z postdates the 22:25Z commit; `test_results.json` records only the 69 selection (the 98 full run is verified but not a recorded run entry). |
| **Round-1 / round-2 behaviours** | **PASS** | IR-01 positives (table Download, aria-label, img alt, results variants, CN 电话会纪要, Corporate Deck); notices `index_notice` and never budget-consuming; malformed href `invalid_anchor_url`; fragment dedupe with distinct queries; empty/self skipped; byte limit one `byte_limit_reached`; unsupported MIME limitation; 31 materials → 30 + one item limit; 30 → no limit; `no_documents_claimed=false`; candidate keys identical; `receipt.event_sha256` recomputes. |

## New findings

### R4-01 — Low — Handoff-document completion remains (no product change required)

- `delivery/w11/handoff.json` is still absent; `handoff.md` (5,765 B) is untracked and belongs to the final report commit. Card §6 requires both `handoff.md` and `handoff.json`.
- The handoff known-limits list covers NR-06, the legal/nav heuristic, header/footer strong CTA without suffix, trailing-slash self links, pending caps, 120+ellipsis titles and `index_notice` disposition, **but not the extensionless-document-endpoint residual**: exact section labels pointing at a document URL without a recognized document suffix (e.g. `/download?id=42`, `/press-release/2026-q3`) are still treated as listing links and dropped. This is a direct consequence of the R3-01 fix and should be listed.
- `evidence_inventory.prepared_at` (`2026-10-23T23:40:00+00:00`) postdates the `6b538ca2` commit (`22:25:36Z`), so the earlier "timestamp updated" claim is still not accurate.
- `test_results.json` records the 69-pass selection; the 98 full-file run is verified by this review but is not a recorded run entry. Optionally add it.

**Required action:** handoff-document only — add `handoff.json`, commit `handoff.md`, add the extensionless-endpoint known limit, and correct `prepared_at`/record the full run. No product change or re-review needed.

### R4-02 — Info — Bounded behaviors to keep explicit in the handoff

- Nav/header/footer anchors **with a document suffix** remain candidates (document files), while no-suffix chrome/section links are non-candidates; e.g. `<nav><a href="/files/ar2025.pdf">Annual Report</a></nav>` → 1 candidate. This is the intended "document file" branch; clarify if the intent was "all chrome anchors non-candidates".
- Extensionless document endpoints with exact section labels remain non-candidates (see R4-01).
- Header/footer strong CTA without a suffix is dropped (already in handoff).
- `/ir/` trailing slash is not treated as the same document as `/ir` (already in handoff).
- `pending_limit = max_items*10 + 30` can drop later documents behind >330 non-document candidates; `item_limit_reached`/`partial` is reported (already in handoff).
- Title recovery is 120 content chars + ellipsis (already in handoff).
- `Annual Report 2025 Legal Notice` becomes `index_notice` due to the notice token (already in handoff).

## Positives verified (independent)

- **R3-01 is fixed cleanly and narrowly:** the section-label veto is now gated on `not _is_document_path(path)`; 11 exact labels, 3 table-row cases, 4 dated-item cases and the public CLI CN/EN tables all produce candidates again, while 11 listing links and nav/header/footer section anchors remain non-candidates. The new tests add 14 cases (62 new total).
- **No regression in the prior set:** NR-01/02/03/04/05/07/08/10, IR-12, IR-01 positives, notices/budget, limits, dedupe, malformed href, byte cap, receipt integrity, schema keys, `no_documents_claimed`, pure parse/thin CLI, and no production writes all re-verify on `6b538ca2`.
- **Performance/bounds preserved:** 10k anchors 0.314 s (2e1dfd04 0.332 s); page hash once; pending cap reports `item_limit_reached`; 400-anchor page bounded.
- **Tests/evidence are truthful:** 62 new + 36 existing = 98 full; delivered selection 69 passed / 29 deselected; JUnit 69/no failures; log and JUnit SHAs match `test_results.json`; `input_source_shas` match the worktree; red-probe output is BOM-free UTF-8 and parses; 11/11 `INPUTS.json` matches; config hashes unchanged; production roots absent; `ruff` clean.
- **Handoff narrative records the bounded limits** (NR-06 and legal/nav heuristic) and now references review 4; the only missing known-limit is the extensionless-endpoint residual in R4-01.
- **RED evidence intact:** base blob `7d8fb129…`, D1/D2/D3 base/current story unchanged.

## External limits / not verified

- The 486,789 B IR body remains unavailable; no replay claim. The derived sealed fixture is not an original replay.
- No live HTTP; real transport/redirects only via the existing MockTransport test.
- The nav/legal/section classifier remains a bounded heuristic; R3-01's EN/CN fixtures are synthetic, and the sealed page body cannot be inspected.
- I did not run the full-repo suite; the review covers the W11 product/tests plus the 78-case probe and CLI/scale checks.
- The extensionless-document-endpoint residual is measured synthetically; it is a known heuristic limit, not a regression on the `.pdf` cases.

## Required fixes before handoff

1. **R4-01 (handoff-document only, no product change):** add `delivery/w11/handoff.json`; commit `handoff.md`; add the extensionless-document-endpoint known limit (exact section labels on `/download?id=…`, `/press-release/2026-q3` remain non-candidates; nav/header/footer document-suffix anchors remain candidates while no-suffix chrome links do not); correct `prepared_at` and optionally record the full 98-file run in `test_results.json`.
2. **No product fix required.** The product SHA `6b538ca2` passes the review-1/2/3/4 product checks; no re-review of the product is needed for the handoff-document items.

## Conclusion

**APPROVE.** `6b538ca2` fixes R3-01 without regressing the previously passing set, keeps the notice/limit/receipt/schema/CLI/performance/no-production-write properties intact, and its test/evidence counts match. The only remaining work is handoff-document packaging and known-limits (add `handoff.json`, one known-limit line, optional metadata fixes), which does not change the product and does not require another product review.
