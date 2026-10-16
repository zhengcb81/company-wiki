# Independent review verdict (verbatim, C node, 2026-10-15)

Reviewer: fresh subagent, blind to the freeze process, given only the two gold
files and their originals (du5-cn-proya-q1 + its Q1 PDF; du5-cn-gbits-call +
its docx transcript). Instructions: adversarial source-faithfulness check of
every anchor, modality/role label, importance, must_preserve and
must_not_assert, plus target coverage. This file preserves the reviewer's
final report exactly as returned; the applied changes are in
`gold_corrections.json.content_corrections` (receipts/review-corrections-applied.txt).

Reviewer counts as reported: SAMPLE A anchors 22 (its text says "21/21" once —
the packaged gold carries 22 anchors across 10 facts); SAMPLE B anchors 20
across 12 facts (its text says "21/21" — packaged count is 20). Anchor
RESOLVED status was unanimous in both samples; the count wording in the
reviewer's prose is the only discrepancy and is corrected in handoff records.

---

## SAMPLE A — du5-cn-proya-q1 (12p PDF, all text read)

- report-period-unaudited-identity — RESOLVED (p1 title, p8 利润表 header, p12 board date all verbatim; note quote1 also matches every page's running header after whitespace normalization, so it's non-discriminating but correctly placed) | semantic PASS — Q1=1—3月 window and 2026-04-20 filing date correct; all three negative controls genuinely wrong (3/31 is balance-sheet date, not release).
- statements-unaudited-no-new-standards — RESOLVED (p1 □是√否, p5 审计意见 □适用√不适用, p6 编制 block incl. halfwidth "币种:人民币") | PASS — all must_preserve load-bearing; "新会计准则调整年初报表" negative control genuinely wrong (p12: □适用√不适用).
- q1-revenue-yoy-decline — RESOLVED (p1 and p8) | UNCERTAIN — figures/sign/period all correct, but 2 of 3 negative controls are flawed: "为年初至报告期末累计" is TRUE for a Q1 report (1/1–3/31 ≡ 本报告期), and "23.05亿元" is a faithful rounding of 2,305,344,625.43 (23.0534亿), not an error. Only "2026年3月单月" and "+2.29%" are genuinely wrong.
- attributable-net-profit-q1 — RESOLVED (p1, p10) | PASS — 383,647,847.96 (合并净利) vs 366,686,734.14 (归母, minus 少数股东损益 16,961,113.82 p10) confirms the attribution trap; negatives genuinely wrong.
- deducted-net-profit-and-nonrecurring-total — RESOLVED (p2 both) | PASS — 25,529,496.96 (p3 合计) = 366,686,734.14 − 341,157,237.18 exactly; "9.97个百分点" and "期末余额" negatives genuinely wrong.
- operating-cash-flow-collapse — RESOLVED (p2; quote2 also on p2, claimed p11 valid) | PASS — positive 106.97M vs prior-year 675.49M; all three negatives genuinely wrong.
- cash-flow-drop-driver — RESOLVED (p3 both) | PASS — only narrative in filing, cause direction (收款↓/推广费↑) consistent with 销售费用 1,076.5M→1,171.9M (p9); negatives genuinely wrong.
- eps-basic-diluted-unit — RESOLVED (p2 both) | UNCERTAIN — basic=diluted 0.93/0.99, 元/股, −6.06 all correct; but negative "为年化或年初至报告期末累计口径" again contains a true disjunct (YTD ≡ Q1 window here); only "年化" and "+6.06%" are wrong.
- total-assets-point-in-time — RESOLVED (p2 both) | PASS — textbook stock-vs-flow fact; comparison is 2025-12-31 (上年度末), +5.00%; all negatives genuinely wrong.
- share-capital-and-buyback-holdings — RESOLVED (p8, p5) | UNCERTAIN — numbers right (10-share delta; 3,757,848 股 = 0.95%), but negative "股本395,976,008为金额（元）而非股数/注册资本元" is confusing and arguably TRUE: the balance sheet literally states 实收资本（或股本）in 单位：元. Also the reason's "equity-incentive effect" is an inference not stated in the filing.

Coverage A: Strong on the declared 期间/单位 trap (本报告期 vs 本报告期末/上年度末; 元 vs 元/股 vs 个百分点) and the attribution/flow-stock corruptions. Gaps: (1) 加权平均净资产收益率 5.78 vs 6.97 "减少1.19 个百分点" — the flagship pp-vs-% item sits only in fact 8's reason text, not as its own fact; (2) 归母所有者权益 6,406,175,986.81 (+4.32%, stock block partner of 总资产); (3) 投资收益 65,170,571.32 has a blank prior-year comparative (blank-cell trap); (4) 现金及现金等价物净增加额 −316,584,460.79 and 货币资金 5.06B→4.75B corroborate the cash-flow fact. Shareholder-table omissions acceptable.

## SAMPLE B — du5-cn-gbits-call (ASR transcript, full text read)

- yy-flow-decline-premise — RESOLVED (both) | PASS — both quotes are 说话人1 (analyst) 00:00 turn; question + premise attribution correct; all three "公司确认/披露" negatives genuinely wrong (company answered only about buydown cost).
- steam-activity-premise — RESOLVED (both) | PASS — "steam时代上面的监测…从绝对值可能不太准确" is analyst's third-party estimate; company replied "我们还没有具体去拆开来看"; "不没有" ASR kept; negatives genuinely wrong.
- lei-ting-profit-analyst-inference — RESOLVED (both) | PASS — analyst's back-solve from 少数股东 (雷霆 only semi-annual); company attributed Q4 jump to bonus-accrual reversal ("四季度没提反而还冲回了"), so "经营改善" negative is genuinely wrong.
- yy-roi-decline-actual — RESOLVED (both) | PASS — "买了"≈"减了" reading well supported by following sentences ("买量这块比较大幅度的减少了"; "尽量的去减少对买量的一个依赖"); "增加了买量支出" negative genuinely wrong under that reading.
- buydown-cut-and-stock-operation-plan — RESOLVED (both) | PASS — 希望/会/尽量 = forward plan, plus "会配合一些短期的买量" refutes "已停止买量"; negatives genuinely wrong.
- buydown-no-return-negation — RESOLVED | PASS — "买量会不会再走到原来的水平了" read as ASR-dropped 不 (不会再到), contextually correct ("但整体来看的话"); modality negation defensible.
- yy-stabilize-target-uncertain — RESOLVED (both) | PASS on substance, but label change: modality "conditional" → "plan" (it's a hedged plan 希望…但目前也不太好判断, not an if-then conditional). Negatives genuinely wrong.
- outpost-update-plan-uncommitted — RESOLVED (both) | PASS — "计划还没有…可能还会有所变化" explicit; "确定推出大更新" negative genuinely wrong (确定 + 大更新 both overstated).
- outpost-buyout-revenue-recognition — RESOLVED (both) | PASS — buyout: 当即确认收入 + 退货率-related liability; contrasted with 消耗型道具递延 (spans 说话人1's "它不像" interjection — handled); all negatives genuinely wrong.
- outpost-stage-problems-resolved — RESOLVED | PASS — 大部分/少数 gradation preserved; "全部修复/完全恢复/彻底解决" genuinely wrong.
- strategy-category-unchanged-negation — RESOLVED | PASS — mgmt answered only on 品类 ("没有一个很大的变化"), scoped correctly; negatives genuinely wrong.
- yy-user-base-scale — RESOLVED | PASS — "2000多用户" unit-dropped ASR; forbidding promotion to "2000万"/precise MAU and the absurd "2000人" both genuinely wrong vs document text.

Coverage B: Role/trap matrix (analyst premise ≠ company fact, plan ≠ achieved, negation retention, ASR noise) is well distributed. Gaps: (1) 问道 Q1 trend — mgmt actual "整个季度环比来看的话是比四季度会好好一些，但是同比去年一季度还是下滑的" (dual QoQ-up/YoY-down trap, the call's only top-line business actual) is missing; (2) mgmt's own explanation of the 雷霆 Q4 jump (奖金计提冲回) exists only as a must_not_assert; (3) 亿万光年: "纯粹的代理，就没有其他的利益关系" (negation) + "签了全球…先发国内" / "半年。没有明确的时间。" (plan/uncommitted); (4) disclosure-refusal pattern ("具体的销量…不太方便分享", "具体比例可能没办法分享") and 航海王 "从业绩方面可能不是会有太大的贡献".

## Overall verdict (reviewer's words)

No fact rejected outright; Sample B is clean (21/21 anchors resolved, semantics faithful). Sample A has four defective negative controls to fix — all in must_not_assert: (a) q1-revenue item "…为年初至报告期末累计或2026年3月单月收入" — split it; the 年初至报告期末 disjunct is true for Q1, keep only the 单月/上半年 corruption; (b) q1-revenue item "23.05亿元" — a correct rounding, not an error; reword to demand exact 元 (e.g. forbid "23亿元"/"2,305,344,625.4"); (c) eps item "为年化或年初至报告期末累计口径" — same half-true disjunct; (d) share-capital item "为金额（元）而非股数/注册资本元" — ambiguous and arguably source-true; reword to forbid "增发/回购导致股本大变" style errors instead. Label changes: yy-stabilize-target-uncertain modality conditional → plan (hedged). Optional: give ROE "减少1.19 个百分点" its own fact in Sample A. Also note report-period quote1 anchors to every page (running header) — harmless but weak as a locator.

---

## Disposition (author side, recorded)

- Applied as v2 content correction (gold_corrections.json.content_corrections):
  proya q1-revenue-yoy-decline / eps-basic-diluted-unit /
  share-capital-and-buyback-holdings must_not_assert rewrites; gbits
  yy-stabilize-target-uncertain modality conditional→plan. Old values
  replayable (old_value entries + manifest *_at_freeze).
- NOT applied (post-freeze, would expand the frozen target set): the suggested
  ROE fact and the Sample B coverage additions. Recorded as future candidates.
