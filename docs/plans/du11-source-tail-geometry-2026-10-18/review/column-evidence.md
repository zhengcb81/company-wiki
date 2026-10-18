# CN physical page 31: bounded native body-column evidence

Conclusion: **the original page provides a defensible local, single-body-lane witness for blocks 18–22; the existing `column=None` fields themselves provide no same-column proof.** This is a read-only source observation and design input, not acceptance of an implemented column/continuity rule. No runtime code, test, model, full-report parse or PDF copy was executed.

## Original and measurement scope

Original: `companies/中微公司/raw/financial_reports/semi_annual/2026-08-19_cninfo_1225482884_2026年半年度报告.pdf` in the mother repository. SHA-256 before/after the first page read: `182e2062fed950cd32310099cdf47f392c791440ce251f5e3bab7137dbc932fe` (unchanged). Two read-only `fitz.open` observations inspected **only physical page 31**, rect `(0,0,595.300,841.900)`, rotation 0. Second observation checked native block/drawing occupancy of the local band, not the full report. Existing investigation maps block 18 to `loc:v1/page:31/paragraph:21` and block 19 to paragraph 22.

## Measured facts

All coordinates below are original page points, rounded to 0.001. All relevant body blocks have horizontal native line direction `(1,0)` and regular `SimSun` size `10.45`; block 20 additionally has regular `TimesNewRomanPSMT` size `10.45` for its number/percent run.

| Native block | x0–x1 | y0–y1 | Role in this bounded observation |
|---|---|---|---|
| 15 | 89.880–530.755 | 530.710–541.160 | Previous risk paragraph's full-width continuation; prior section, so **not** a same-section closure anchor |
| 16 | 89.880–478.316 | 551.110–561.560 | Previous paragraph end, before heading 17 |
| 18 | 110.880–530.763 | 592.029–602.479 | First-line-indented risk body, ends `不利影` |
| 19 | 89.880–110.770 | 612.429–622.879 | Two-character short continuation `响。` |
| 20 | 110.880–521.165 | 631.417–645.128 | Next paragraph, same first-line indent, begins `公司为高新技术企业` |
| 21 | 89.880–530.755 | 653.350–663.800 | Next paragraph's full-width continuation; strongest local lane anchor |
| 22 | 89.880–257.765 | 673.750–684.200 | Next paragraph's short final line |

Native block 17 is the heading `3、政府支持与税收优惠政策变动的风险`; the next heading is block 23 `（二）行业风险`. Blocks 18–22 are consecutively ordered between those headings. The inspected vertical band `591.9–684.3` contains **only those five text blocks**, no image block and no native drawing. Thus there is no competing side-by-side text block, illustration or table ruling in this bounded band. This does not assert that the entire PDF has one column or no tables.

Limited original excerpts (each example below <120 characters):

- Target, blocks 18–19: `如果公司未来不能持续获得政府支持或政府支持显著降低，将会对公司经营业绩产生不利影响。`
- Next paragraph, blocks 20–22 (bounded excerpt): `公司为高新技术企业，报告期内公司享受高新技术企业15%所得税的优惠税率，如果国家上述税收优惠政策发生变化，或者公司未能持续获得高新技术企业资质认定，则可能面临因税收优惠减少或取消而降低盈利的风险。`

## What this proves, and what it does not

The same-section next paragraph witnesses a **body lane** with continuation left margin `89.880` and right extent `530.755`. Its first line begins `110.880`, the identical 21-point indent seen in block 18. The target's right extent differs from the anchor by only `0.008` points, and its short tail starts exactly at the anchor's continuation left margin. Target line-start advance is `20.400` points; the following paragraph's final two line starts also advance `20.400` points. Target inter-line vertical bbox gap is `9.950` points. Font, page, direction, block adjacency, section boundaries, lane-spanning lines and absence of a competing lane jointly support the local same-body-lane observation. This is stronger than merely observing two unknown column IDs or two nearby glyph boxes.

The target boxes themselves have **negative horizontal overlap**: `110.770 - 110.880 = -0.110` points. The witness is the surrounding full-width body flow, not positive target-box overlap. A rule requiring overlap must not be globally removed; a narrowly qualified first-line-indent/short-tail alternative would need to consume this explicit native lane evidence. Prior blocks 15/16 can corroborate page margins/font but cannot silently bypass the intervening heading or be labeled same-section context.

There is no tagged PDF column ID exposed by this observation, and current `column=None` remains **unknown as a stored explicit column identity**. No existing current-code column witness has been shown here. The measurable local lane could support a derived, source-owned witness if its owner verifies these conditions; assigning `column=0` globally, matching arbitrary short lines by containment, allowing another column/heading/table, or treating `None == None` as proof is unsupported. When full-width same-section anchors are unread, ambiguous or absent, the proposed exception must remain unknown/deferred.

No full-page layout reconstruction, semantic product inference, character fabrication or cross-page stitching follows from these measurements. ROOT retains implementation and TDD responsibility.
