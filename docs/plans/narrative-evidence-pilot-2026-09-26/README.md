# 当前执行入口

2026-10-07本次按用户要求全面补漏门禁、更新实施计划并收口当前责任代码；目标服务实读paused，未自动恢复。恢复后先G2（含SW/StockQA日常门P0-B），再生产落地；已完成的有界验收不等于整个计划完成。

1. [task_plan.md](task_plan.md)：唯一当前目标、G2→R2→R3→R4→R5顺序、owner、完成条件、下一步。
2. [findings.md](findings.md)、[progress.md](progress.md)：当前事实、真实验收与错误记录。
3. [n4_production_batch_implementation.md](n4_production_batch_implementation.md)：scope/预算/model/CLI/恢复/空间的详细接口；原三个节点已验收历史，不重新执行。
4. [radical_simplification_proposal_2026-10-03.md](radical_simplification_proposal_2026-10-03.md)：已采纳的八束优化及迁移前置，实施状态以task_plan为准。
5. [最终空间收据](harness_lanes/results/gd_storage_final_cleanup_2026-10-03.md)和[46项历史审计](gate_permission_inventory_2026-10-03.md)：基线证据，不产生新的许可/签收。
6. [G2全面补漏实施单](gate_simplification_reaudit_2026-10-07.md)：当前P0，八仓审计、14组和scoped pin漏项、完整同步写集/接口和仅两个大测试节点；隐含整库检查/补种列P0。
7. [全部PWF落地细则](all_pwf_completion_implementation_2026-10-07.md)：G2完成后继续生产来源、正式运行、原文收益决策和最终收口。
8. [并行实施总计划](parallel_execution_plan_2026-10-03.md)：历史已交付线的所有权/接口；不重新发已完成卡，IQS不重复派线。

其余W/G/worker/review/space和并行卡保留技术背景与已经完成的证据，执行顺序、权限/审批和测试频率均由task_plan覆盖。已交付harness不重复派发；未交付独立线由root给出独占范围后接入当前接口。所有原始资料继续保留。

旧三份PWF入口完整历史保存在Git bff81af，未复制归档。无需在每次恢复时加载全部旧Phase。新进展及时正常提交推送；有限批次和大节点真实测试先于旧Worker退出/无引用派生删除。
