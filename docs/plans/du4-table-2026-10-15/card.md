# DU4-TABLE：表格数字的列、期间、单位与范围绑定

状态 READY，2026-10-15。这是新实施任务，不是已完成 DU3 几何包的重复验收。

## 开工入口与独占范围

- 工作目录：`C:/Users/郑曾波/Projects/company-wiki-du4-table`。
- 分支：`codex/du4-table-20261015`；固定基线 `8206e78d4087531b1d7ed57c45a73c942cc702e3`。
- PWF：`docs/plans/du4-table-2026-10-15/`；先读其中 task_plan.md、INTERFACES.md、references/implementation-brief.md。
- **只写** `src/company_wiki/document_understanding/table_measurements/**`、`tests/unit/du4_table_measurements/**`、本 PWF。新包的 `__init__.py` 导出公共函数；不修改父目录 `__init__.py`。
- 所有既有源码/测试/总计划/配置只读。尤其不改 PDF extractor、layout_hints、structure/tables、narrative_reading、selector、model、SourceExport、RF。原参考设计里建议的既有文件接线由 ROOT 做；**本卡所有权取代其旧分工**。

## 实际问题和真实夹具

港股实际模型输入把 2023/2024 标题与只有一组数值的行同时送出，模型将 2023 数值归到 2024。三列期间、两值的行也存在，不能靠右对齐补列。2023 六个月和十二个月不能按年份去重。

新的零付费原件重放已证实原件含 2024 数据：某些原生左侧大合并格含旧年标签/数值，真正新年值在后续右列行，现选择只截取了较早几行。因此既有列值绑定缺失，也有选择闭包不含正确新列的问题；本包负责前者并交付后者需要保留的依赖引用，ROOT 修选择。

本 PWF `fixtures/hk-table-observation.json.gz` 是真实保存的原生观察副本，保留 strings 去重表、actual_replay_units、tables、rich_layout、目标别名等。`fixtures/manifest.json` 给出文件 SHA 和来源。它有 228 cells/64 rows，且截断；旧 initial_structure_pipeline 未留存。**不是完整原始 PDF，也不是已经证明逐值列归属的金标**。

先理解字符串引用和坐标；原包不修改。自己的测试适配器可将真实 packet 投影到公共接口，并明确哪些是原生事实、哪些是 synthetic。不能凭历史 eN/gN 别名造期间答案，不能从审查推算合计来补原值。

## 要实现什么

按 INTERFACES.md 的 `bind_operating_table` 实现一个共享纯组件：

1. 一次索引原生槽与表头引用；保留空位、未提取位、合并未知。可使用既有明确 native_slot 或 fine_geometry 的归属，不重建第二个几何引擎。
2. 把逐值字符引用绑定到原生列、真实表头路径、完整期间；区分 as-of/duration/fiscal year，保留原始期间标签及未披露字段。
3. 单位按单元格/行/表的真实作用域；同表 GMV、交易量、每单金额、百分比、门店数、合作伙伴数不混用。范围保留地区/品牌/门店或全渠道/存量或新增的原始引用。
4. `bound/ambiguous/unavailable` 按值输出；局部未知不连坐其他可用行。依赖 refs 必须涵盖决定解释的表头、单位、脚注，供 ROOT 后续选择闭包使用。
5. 线性索引后按有界候选匹配；避免 cell×全文、行×所有列的无界笛卡尔扫描。全部工作复用传入预算，耗尽明确 partial。

不改原文，不算缺失值，不换币种/单位，不写投资结论。不用公司名/产品名/文件路径特判，不调 LLM，不提高 96/48000 或路由探测上限来隐藏缺口。

## A：先写真实语义反例与 RED

在新测试目录建立独立 expected 字段，至少覆盖：

- 2023/2024 两列；标题两列但值只有一列，不能自动归最新年。
- 六个月 2023、十二个月 2023、2024 三列只有两值，保空位；同年不同 duration 不合并。
- 真实 HK 合并大格/后续右列样例：没有逐值原生定位时明确 ambiguous；有定位的右列能正确绑定。不得硬编码正确 2024 数字。
- 多级表头/单位/脚注、跨行标签、重复中英标签，不靠字符长度/语言自动合列。
- 百分比区间、金额 million、每交易金额、件数同时出现；负号/括号/破折号不能误零。
- row_span/column_span unknown，None/真实空串/merged_unknown；粗整表 bbox 不能复制为细格。
- 相同 table index 不同 page/parent，不跨表拼接；缺页/截断是诊断。
- refs 越界、冲突槽、未知 schema、输入不变、预算 0/小预算/大数据有界、相同输入稳定。

新模块初始 import 失败可以记录，但实现 API 骨架后要保存至少一次真正列/期间语义失败再完成实现。不得改测试 expected 去迁就错误输出。

## B：组件集中验证

实现后运行一次本包集中测试、Ruff；对本包做 mypy（沿仓库当前设置）。同一真实 packet 的适配器+绑定器走通，报告 bound/ambiguous/unavailable 的真实计数和引用，不能用“没有崩溃”作正确性证明。补独立合成多表/重复年 holdout；不是只测 HK 一张表。保存预算使用和耗时观察，不设脆弱的毫秒门槛。

## C：交付与 ROOT 接线

按公共 handoff 格式提交自己的分支；报告未绑定原因、接口实例、真实/合成边界，STOP。

ROOT 后续负责：同次 native parse 采集格槽 → adapter/structure 调本组件 → 将解释必需 refs 加入现有选择依赖 → canonical context/模型投影带同一绑定 → 真实 HK 与另一公司/格式 holdout → cache/旧 Ref 恢复及摘要数字审查。作者不替 ROOT 写这些接线，不宣称生产已改善。
