# 进度

2026-10-15 ROOT 已创建独立稀疏工作树、复制施工卡/接口/真实观察。READY，未实施、未运行本卡测试；不继承主线工程通过结论。

2026-10-15 DU4-STATE 实施（本工作目录 `C:/Users/郑曾波/Projects/company-wiki-du4-state`，分支 `codex/du4-state-20261015`）：

- A：写 86 项语义反例/契约测试（真实 m41 三关系 + 32 原始例 + 16 扩展反例 + 4 holdout），
  先用空结果桩模块跑出**真正语义 RED**：`PYTHONPATH=src python -B -m pytest -q tests/unit/du4_operating_states`
  → exit 1，60 failed / 26 passed，核心失败 `test_real_first_answer_yields_three_independent_relations: assert 0 == 3`
  （模块可导入，非导入错误）。证据：`results/red-run.txt`。
- B：实现 `src/company_wiki/document_understanding/operating_states/`（text_view 保偏移匹配视图 /
  patterns 有界谓词模式 / relations 绑定与入口）。集中测试 → 86 passed，exit 0。证据：`results/final-run.txt`。
  输入不变、原文精确 refs（含 `\n`/繁体原字形）、零/部分预算 partial+计数、确定性、长句有界、
  role 无关、跨 parent 不串联、unknown 不落空串/假 complete 均有断言。
- C：`python -m ruff check <src><tests>` → 14 个 F541 已 `--fix`，0 remaining；
  `python -m mypy src/company_wiki/document_understanding/operating_states` → `Success: no issues found in 4 source files`。
  证据：`results/static-checks.txt`。交接：`handoff.md` / `handoff.json`。

实现期约定锁定（RED 后微调，RED 核心断言未变）：`assertion_refs`=子句证据跨度，绑定检查看组件 refs
（长句测试相应只扫组件 refs）；CN 主题/对象尾部助词裁剪与 EN `to` 后空格修复属于实现细节修复。

未做（归 ROOT）：原件重放、真实选择/完整 QA/0.8 回归、真实摘要、下游 RF 验收、版本 bump。
0 生产写入、0 供应商调用。提交后 STOP 等 ROOT 接收。

实现 commit：`dfb5180f feat(du4): implement bounded operating-relation detection (DU4-STATE)`（本行为交接补记）。

2026-10-15 独立审查（general-purpose 验收 agent，复跑命令与回执逐项核对）结论"有条件接收"：
20/22 满足，2 阻塞 + 4 建议。已全部处置：

- 阻塞 1（R15）：预算耗尽时丢弃已确定结果——`relations.py` 改为事件一确定即组装入库，
  `WorkBudgetExceeded` 后保留前缀；`test_partial_budget_keeps_determined_results` 改为
  逐档预算扫描的**非空洞前缀断言**（kept == full[:len(kept)] 且至少一档非空）。
- 阻塞 2（R21）：handoff.md/handoff.json 显式补"真实摘要主体/阶段独审（四行含义表）"ROOT 工作项。
- 建议 1：否定存在式风险套话误报（`公司不存在经营风险。`→原为 business_scope 正极性）——
  `_ABSENCE` 绑定"不存在/未曾/从未"，且抽象风险名词（风险/问题/挑战/不确定性…）不作经营对象，
  新增负控测试。建议 2（guard 子句内断言级粒度）记入 known_limits（无标点混排句的未来细化），
  当前 clause 级满足施工卡"同一单元有独立有效经营断言时仍保留它"。
- 建议 3/4/5/6：补认证失败否定断言、全枚举合法性契约断言、非字符串 context ValueError 断言
  （已实现分支补测）；handoff.json 静态检查条目已由 static-checks.txt 承载语义。

复跑：90 passed，exit 0；ruff 0 remaining；mypy Success（4 files）。证据：`results/final-run.txt`、
`results/static-checks.txt`。0 生产写入、0 供应商调用。STOP 等 ROOT 接收。
