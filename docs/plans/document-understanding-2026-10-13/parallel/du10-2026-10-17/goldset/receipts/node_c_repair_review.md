# DU10-CWP-SUMMARY-GOLDSET Repair Review

- Reviewer: automated agent (same reviewer as initial audit)
- Date: 2026-10-17
- HEAD: 45d7f3635e1c4be9e6625e4c362c855a5d5df285
- Scope: verify 5 identified issues (I1-I4, O1) have been fixed correctly

## Pre-flight

| Check | Result |
|-------|--------|
| HEAD matches expected 45d7f363 | PASS |
| pytest (58 tests, excl. verify_anchors) | PASS (58 passed, 0.42s) |
| verify_anchors.py (11/11 cases) | PASS (11 bound, 0 unbound) |
| git status (no stray modifications) | PASS (only receipt files untracked) |

## Fix Verification

### I1 (BABA) must_preserve[2] scope fix -- PASS

**Issue**: global-annual-active-consumers fact's must_preserve[2] previously misstated scope (claimed "蚂蚁金服去重合并口径").

**Fix**: Now reads: "全球口径=中国消费业务7.30亿+国际1.30亿之和（不含蚂蚁金服；蚂蚁金服并入的是9.60亿中国用户口径）"

**Source verification** (companies/阿里巴巴/raw/prospectus/阿里巴巴招股说明书2019.pdf p19):
- 全球年度活跃消费者(3) = 8.60亿
- 中国消费业务年度活跃消费者(2)(3) = 7.30亿
- 国际年度活跃消费者(3)(4) = 1.30亿
- 注(1): 阿里巴巴数字经济体中国用户(1) = 中国消费业务(2) + 螞蟻金服 = 9.60亿
- 注(2): 中国消费业务 = 中国零售市场、本地生活服务及优酷（不含蚂蚁金服）

The fix correctly distinguishes 8.60亿 (excl. Ant) from 9.60亿 (incl. Ant). The boundary[1] guard also updated accordingly.

### I2 (AMEC) allowed_summary[2] XD/YD RIE separation -- PASS

**Issue**: allowed_summary[2] previously conflated XD RIE and YDRIE timelines ("一年左右" mixed into XD RIE).

**Fix**: Now reads: "XD RIE处于在研阶段、将很快完成开发进入市场，YDRIE处于在研阶段、预计一年左右进入市场。"

**Source verification** (companies/中微公司/raw/investor_relations/【芯片】中微公司交流纪要20220416.pdf p3):
- XD RIE: "公司已经开发了XD的RIE...很快就完成开发进入市场"
- YDRIE: "公司正在紧锣密鼓地开发，现在叫YDRIE...一年左右即将进入市场"

The two products now have distinct timelines in the summary matching the source.

### I3 (MINISO) speaker title correction -- PASS

**Issue**: summary_proposition previously labeled speaker as "董事长".

**Fix**: Now reads "叶国富（招股书称创始人兼首席执行官）" in summary_guidance.must_preserve[0].

**Source verification** (名创优品/December Quarter and Full Year of 2024 Transcript.pdf p1):
- "参加今天会议的有我们的创始人兼首席执行官叶国富先生"

Title confirmed as "创始人兼首席执行官" (Founder and CEO), not "董事长".

### I4 (VRSK) boundary annotation source-grounding -- PASS

**Issue**: boundary[0] parenthetical about Underwriting+Claims=$782.6m had no text support.

**Fix**: boundary[0] now reads: "84%不得写成总收入占比（84%为insurance revenues子口径，非total revenues；disaggregation中total revenues=Underwriting+Claims=$782.6m）"

**Source verification** (vrsk20260331_10q.htm disaggregation table):
- Underwriting: $552.1M
- Claims: $230.5M
- Total revenues: $782.6M
- $552.1 + $230.5 = $782.6M confirmed

The annotation is now directly grounded in the disaggregation table.

### O1 (DFC) reason internal-tension observation -- PASS

**Issue**: q3-submarine-hv-cable-revenue reason field lacked observation that single-quarter total revenue (~30.66B) < category revenue (35.49B).

**Fix**: reason now includes: "原件内部张力：p1单季总收入约30.66亿（3,065,970,750.30元）低于p3类别口径35.49亿，说明35.49亿是含了其他收入的口径；标注忠实引用原件措辞，不自行改写期间。"

**Source verification** (companies/东方电缆/raw/financial_reports/东方电缆：东方电缆2025年第三季度报告.pdf):
- p1: 营业收入 3,065,970,750.30 元 (Q3 single quarter) = approx 30.66亿
- p3: "海底电缆与高压电缆实现营业收入35.49亿元" (category revenue)

The tension is real (35.49 > 30.66) and the reason field correctly flags it and explains the scope difference.

## Verdict Summary

| Issue | Fix | Verdict |
|-------|-----|---------|
| I1 (BABA must_preserve scope) | Corrected to exclude Ant Group | PASS |
| I2 (AMEC XD/YD RIE timeline) | Separated into distinct timelines | PASS |
| I3 (MINISO speaker title) | Corrected to Founder and CEO | PASS |
| I4 (VRSK boundary grounding) | Grounded in disaggregation table | PASS |
| O1 (DFC reason tension) | Added internal tension observation | PASS |

## Overall Conclusion

**PASS** -- All 5 identified issues have been correctly fixed. Each fix is verified against source documents with direct text extraction. No new issues found. The goldset is ready for use.
