# DU10 goldset ROOT independent review

- Author HEAD: `faf5e58019314fd0b5dce0f6d00b44587a81ff28`
- Result: NEEDS_FIX (semantic gold and promised SourceRef replay incomplete).
- Once-only structural suite: 58 PASS; all 11 raw anchor cases PASS; 118 anchor/integrity checks.
- Originals unchanged: True; author files unchanged: True; sentinel unchanged: True; owned temp removed: True.
- Detailed bound SHA and source snapshots are in sibling JSON.

## Findings

### GS-R1 P1 du10gs-us-10q-vrsk
Gold incorrectly treats insurance revenues as a strict subset of total revenues, forbids a potentially correct total-revenue subscription share, and labels the scope difference a known trap.

Evidence: Original explicitly says one operating segment and one reportable segment, Insurance. Insurance Underwriting $552.1m + Claims $230.5m = Total revenues $782.6m. MD&A category table repeats Total Insurance $782.6m.

Root cause: Required literal scope preservation was elevated into an unproven strict subset assumption; the independent review did not reconcile business-segment note and revenue tables.

Fix: Preserve wording insurance revenue and approximately, but remove strict-subset assertion and blanket prohibition; add evidence for one Insurance segment and insurance total. Replace trap with category-vs-total or subscription-share-vs-amount distinction.

### GS-R2 P1 du10gs-hk-ipo-baba
Corrected fact conflicts with uncorrected summary_guidance.boundary claiming 8.60亿 includes Ant Chinese users.

Evidence: PDF p19: global active consumers 8.60亿 = China consumer business 7.30亿 + international 1.30亿; China digital economy users 9.60亿 combines China consumer business and Ant, note (1).

Root cause: Repair changed one fact branch while leaving duplicated boundary prose contradictory.

Fix: Align every proposition/guidance/fact branch to original 8.60 vs 9.60 definitions; keep periods, international dedup and 2019 FY cloud values.

### GS-R3 P1 du10gs-cn-q3-dfc
Allowed summary presents internally contradictory 35.49亿元 category revenue as a confident Q3 actual and reason invents an explanation that it includes other revenue.

Evidence: PDF p1: company Q3 total 3,065,970,750.30 yuan (~30.66亿); p2 explicitly defines 本报告期 as three-month Q3; p3 says 本报告期海底电缆与高压电缆 35.49亿. Original itself inconsistent; no explanation in source.

Root cause: Literal quote replay was treated as economic truth, and a numeric reconciliation failure was explained through unsupported inference.

Fix: Represent this as source inconsistency: attribute p3 figure as original statement with conflict to p1, mark period/scope unresolved, prohibit confident standalone Q3 category assertion and invented explanation. Do not silently rewrite to YTD or “correct” original. This is useful real holdout evidence.

### GS-R4 P2 du10gs-call-miniso-q4-2024
Repair report claims title repaired, but proposition still labels speaker 董事长; guidance says 招股书称创始人兼首席执行官 although source is this call.

Evidence: PDF p1 operator introduces 创始人兼首席执行官叶国富; p3 heading 叶董讲稿. “董事长” inference may be externally true but not the direct title from this self-contained source.

Root cause: Partial textual fix and incorrect document attribution; reviewer did not re-read all final fields.

Fix: Use source explicit 创始人兼首席执行官 or neutral 叶国富; say 本电话会开场而非招股书. Add p1 role anchor if required role remains enforced.

### GS-R5 P2 du10gs-cn-ir-amec-minutes
21.81% must_preserve omits that CAGR concerns plasma etching equipment, attaching it to general semiconductor-equipment market-size fact. Proposition still groups XD RIE and YDRIE as both expected about one year although allowed_summary was fixed.

Evidence: PDF p2: 等离子体刻蚀设备 ... 2019-2022年平均年增长率21.81%（2022年是预测数据）. PDF p3: XD RIE 很快完成开发进入市场; YDRIE 一年左右进入市场.

Root cause: Adjacent industry and product facts conflated; repair edited allowed_summary but did not propagate semantic distinction throughout schema.

Fix: Bind 21.81% explicitly to plasma etching or move into separate factual unit with same anchor; distinguish XD RIE soon vs YDRIE about a year in every summary/guidance field.

### GS-R6 P2 du10gs-cn-annual-catl-capacity
Allowed summary and guidance redefine 772GWh as period-end capacity; original says 报告期内产能772GWh and only 321GWh is explicitly period-end construction capacity.

Evidence: PDF p24 exact: 报告期内公司锂电池产能772GWh，期末在建产能321GWh.

Root cause: Period and stock interpretation added beyond exact text.

Fix: Retain 报告期内772GWh vs 期末在建321GWh; do not assert period-end for both without separate source support. Preserve construction-not-operating distinction.

### GS-R7 P1 all
No actual CWP read-only SourceRef/SourceExport replay exists in submitted verifier or reviewer receipts. Local binding is raw path plus substring marker, SHA, fitz/BeautifulSoup.

Evidence: tests/_support.py resolve_binding os.path.abspath + contains /companies/ etc, page_text uses fitz.open(path)/Path.read_bytes; verify_anchors only calls these. No configured root resolver, CWP SourceRef read, or evidence open; case source_id never participates in resolution.

Root cause: SourceRef-shaped metadata and raw-file anchor integrity were conflated with integration-contract validation.

Fix: Add a bounded ROOT-owned or goldset-only existing CWP read-interface replay for each SourceRef and locator. Confirm configured-root/current source identity + SHA and required read operation. Keep raw verifier as separate anchor integrity evidence, not SourceRef contract PASS. Unregistered roots must use existing scan/open policy and remain honest, do not add production permission gates.

### GS-R8 P2 du10gs-us-10q-vrsk
All HTML anchors are document-level whitespace contains matches, so no precise section/paragraph/DOM locator is provided for machine/analyst replay.

Evidence: See verifier source inspection and JSON.

Root cause: Minimum anchor-present condition substituted for card precise locator requirement.

Fix: Use existing locator vocabulary to record MD&A insurance subscriptions, revenue disaggregation, segment note, non-GAAP definition section/paragraph anchors; verify bounded location, keeping document-level match as fallback diagnosis only.

## Coverage and retained passes

11 cases from 10 originals across CN/HK/US and eight types. CATL same source is explicitly two distinct propositions. MINISO call is PDF prepared remarks; no TXT or Q&A coverage. Missing new TXT/HK quarterly noted honestly.

Reviewed key original pages: CATL17/24; Sugon8/9; Huarui105/293; Milkyway344; AMEC1/2/3; DFC1/2/3; BABA19/21; MINISO interim14/23; MINISO call1/2/3/4; VRSK segment note/revenue disaggregation/MD&A/non-GAAP. No other independent wrong numeric magnitude identified in these pages.

Root may repair retained cases and add focused semantic controls plus bounded existing read-interface replay. No need to rerun broad repository suites for these data-only corrections. Historical author PASS receipts must be retained as historical and superseded by corrected final review.
