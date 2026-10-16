## ROOT接收收尾 — 2026-10-16

CWP已正常并线推送，252真实材料测试与12Git往返通过，精确CI 38834945691 SUCCESS。ROOT金标纠正显式v3，保留原旧值/锚点/重要性/分母；作者v2 handoff为历史。

**Next Step：** ROOT用同一金标验生产候选；原native12/37是待修质量，不自称生产完成。详[总接收](../document-understanding-2026-10-13/review/du5_reception.md)。

---

# 进度

2026-10-15 ROOT已创建独立稀疏工作树及启动文档，尚未开始实现/测试。源码来自明确committed base；主目录WIP/密钥/原件未复制。

## A（完成，2026-10-15）

- 读 README/EVIDENCE_CONTRACT/schema/records/gold/coverage/contamination/observer/
  checkers 与现测试；实查矩阵见 findings.md §1（五轴机读形态在 coverage_matrix）。
- 选定 9 份真实原件（7 公司，A/H/US，9 形态）；prior use 全量检索后冻结。
- 两个真实 RED 先行留证：`receipts/RED-coverage-axes.txt`（3 failed，coverage 五轴
  塌缩）、`receipts/RED-gold-anchors.txt`（2 failed，错页行+du5 未建）。
- 9 个独立子代理逐字读原件回报（reader_reports/ 留存），gold 冻结于
  `2026-10-15T23:54:38+01:00`（freeze-gold.txt；全部锚点冻结前验证通过）。

## B（完成，2026-10-15）

- coverage_matrix 五轴扩充（SAMPLE_AXES/sample_axis_report/axis_counts）；
  hk_quarterly、sec_8k_6k_exhibit 依新原件转 real，us_s1_f1/amended_filing 保持
  missing；旧行不实注释修正。
- contamination 增 9 个 du5 条目 + `company_prior_use` 词汇；holdout.json 增
  du5 区块并更新 carrier gap（8-K/exhibit 已实测填补，REQ-3 生产验收仍 open）。
- `gold_corrections.json`（锚点更正提案+不可验证记录）、`du5_manifest.json`、
  test_du5_gold.py（旧 20 文件字节锁+新集校验+真实 gold 正控）、
  test_gold_anchor_integrity.py、test_du5_coverage_axes.py。
- 行换行：.gitattributes 钉 benchmark JSON `text eol=lf`（沿 tests/golden 先例），
  实测 add→blob→fresh-checkout 一致（git-blob-roundtrip.txt）。
- 集中回归：offline 236 passed/9 skipped（基线 217 全数保持）；
  real_data 245 passed；ruff 0 errors（receipts/B-*）。

## C（完成，2026-10-15）

- 真实 CLI native 回放 ×2（复跑一致）：9/9 可读、新集 critical 12/37=0.324
  （8 FAIL/1 PARTIAL，生产质量缺口如实保留）；raw/config/sentinel 恢复证据齐全，
  model/paid/network=0（receipts/native-run*/native/summary.json）。
- 独立 reviewer 对照原件复核 2 组新来源目标（proya 22 锚点/10 事实、gbits 20 锚点/
  12 事实，全部 RESOLVED；判定原文见 receipts/independent-review-verdict.md）；
  发现 proya 3 条事实的 4 条 must_not_assert 含真命题/半真析取 + gbits 1 条 modality
  误标 → 按“改错金标需单独更正记录和版本”以版本 2 记录应用
  （gold_corrections.content_corrections，旧值可回放）。
  reviewer 建议的增补事实因已过冻结点未采纳，记录为后续候选。
- 旧/新分开报告、handoff.md/json、正常 commit；STOP 等 ROOT 接收。
