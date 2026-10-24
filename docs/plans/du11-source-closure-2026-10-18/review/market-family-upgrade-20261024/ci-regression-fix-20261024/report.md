# 2026-10-24 精确 CI 回归根修与定向验收

## 结果

在主线 `master` 修复精确远端 CI `40109033205` 发现的五个失败；根修提交为 `c22a952f`（`fix: restore narrative and cross-page reading regressions`）。本机定向验收：相关 unit 322 passed、integration 4 passed、Ruff passed、`git diff --check` passed。没有运行 8k 全量 suite。M4 两份真实季报此前已用最终连续性逻辑完成离线回放，见同目录 `../m4-sparse-quarterly/report.md`；原件 SHA 前后一致、零下载/零模型调用。新提交对应远端 CI 尚待推送后核对。

## 发现与根因

精确失败运行：[GitHub Actions 40109033205](https://github.com/zhengcb81/company-wiki/actions/runs/40109033205)，失败检查 `120916666195`，代码 HEAD `e3e7d2fb0c5163878680b4405cd263c120eeed23`。五个失败测试为：

1. `test_narrative_english_business_recall::test_governance_safe_harbor_and_financial_growth_do_not_become_business_candidates`（financial growth 参数）。
2. `test_fresh_selection_semantics::test_operating_subject_and_cause_cannot_be_borrowed_from_training_or_another_sentence`（English 参数）。
3. `test_fresh_selection_semantics::test_metric_words_in_training_or_a_finished_previous_sentence_are_not_operating_growth`。
4. `du11_source_closure.test_cross_page_reference_plan::test_only_actual_running_furniture_can_be_skipped_at_the_page_boundary[False]`。
5. `du11_reference_readiness.test_native_page_local_positions::test_unproved_page_counter_cannot_erase_an_unfinished_preceding_body`。

根因分成两类。业务筛选把通用 `operating_metric_change` 当成财务事实豁免，导致年收入/净利润增长进入经营动态；治理培训句里的反舞弊、合规内容又能被宽泛经营活动识别为客户/业务事件。连续性处理在未证明页码连续时，把已闭合前缀和真正未闭合的尾部一起延期；页边界重复判断还可能让相同 unit 重复出现在延后结果中。CI 报告同时缺少有效 JUnit，是测试步骤提前失败的报告后果，不是第五个产品根因。

## 根修

- `narrative_business_policy.py` 仅由具体业务关系建立财务事实豁免；通用方向词和裸财务变化不能豁免 finance-only 过滤。
- `narrative_business_groups.py` 的读取候选在财务-only 时清除 reading-only 贡献，同时保持 legacy fact 路径不变。
- `narrative_source_purpose.py` 增加句内、限长的治理/反舞弊/合规培训用途分类，避免培训文字借用同句治理对象变成经营动态。
- `narrative_continuity.py` 的 `finish()` 只返回未闭合后缀给页边界决策；真正跨页不确定时只延后该后缀与当前片段。页边界处的非终止 singleton 保持待判；闭合前缀不会被重新延后。deferred ID 用增量集合去重，避免连续运行中重复构造集合。

## 验收证据

- 失败类及相邻连续性/目的分类回归：8 个定向 unit 文件，`266 passed in 14.68s`。
- 经营候选规则：`tests/unit/test_narrative_business_recall.py`，`56 passed in 13.02s`。
- 生产读取集成：`tests/integration/test_narrative_business_recall.py`，`4 passed in 5.78s`。
- Ruff 对四个变更源码文件通过；空白检查通过。
- M4真实季报此前按最终修复回放：中微2026Q1保留关键业务进展，珀莱雅2026Q1保留现金流原因并排除法定补助模板；中微仍为 `partial`。对应原件 SHA 分别 `ab7bb0076b2a3fb42ebca7b54d1b167a790221e394613ce544e275b249eb3268` 和 `873df9697b20c8c8882f9f16f60bdf755bc6b1b27022f2cd491ebc94c012a49e`，没有下载、模型请求或原件改写。

这是一组定向工程回归与样本复验，不代表跨市场所有文种的业务质量验收，也不取代正式摘要、缓存恢复、RF 消费和年度/holdout 循环。推送后只检查新 HEAD 对应 CI；M5 的 US IPO provider 启动前预算失败诊断仍是后续唯一工程节点。
