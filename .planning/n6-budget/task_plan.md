# N6-BUDGET: 唯一施工入口

本线目标/写集/接口/测试/交接只取 docs/implementation/handoffs/N6-BUDGET/INPUT_CARD.md。基线58b74d07dd4f8b589c134ef9060a689864a8c089（工作树头9495459为MAIN放入的卡与PWF），PLAN_ID=n6-budget。MAIN拥有共享入口与总PWF。

| 阶段 | 状态 |
|---|---|
| 接口与TDD反例 | done 2026-10-06：读 narrative_finalize/narrative_budget/narrative_document/narrative_candidates/narrative_routing/narrative_neighbors 与只读旧测试；离线回放S01-S08真实候选，见 findings.md |
| 本线实现 | planned：n6_budget_dedup（整组包含式保守去重 + 角色分组）与 narrative_budget（保留reserved/按页轮转，加入类别软配额） |
| 一次集中测试/真实边界/交接 | planned：三条新测试先RED，实现后GREEN；再跑 test_narrative_evidence.py 与预算/去重相关旧短测试；ruff；HANDOFF |

启动先核HEAD/status，输入PWF/card是MAIN创建的新文档，可随本线提交；不执行旧N5/根总计划。无原件/配置/owner写入、0付费模型，临时根恢复原状。tmp/ 下的回放脚本与抓取数据仅本线开发用，不入库。
