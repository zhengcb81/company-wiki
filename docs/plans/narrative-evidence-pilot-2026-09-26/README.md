# 当前执行入口

**最新G3验收（2026-10-07）：**三个包已接收并补齐MAIN接线，两个本地主线已并入。RF `ab7a7a44`已正常推远端main（107快测绿）；CWP接线代码`b2c9e66`，115责任用例最终绿、1921单元绿，正在正常发布。详情见[g3_main_acceptance](g3_main_acceptance_2026-10-07.md)。G3不再派发；G2-04旧维护退休已完成，R4依据现有注册重复上界决定不做对象化迁移（不是释放空间）。RF真实用户安装未同步；G2-12/其他G2、R2元数据生产应用、R3和R5仍未完成。目标服务保持paused，本次仅执行用户明确要求的G3验收，并未恢复总目标/付费/生产批次。


**此前卡发布记录：**本次按用户请求发布[G4两项独立大任务](harness_lanes/g4_parallel_packages_2026-10-07.md)，可现在分别给两个harness；[冻结Pipeline退休](harness_lanes/g4_cwp_frozen_pipeline_retirement.md)与[SID最新财报发现](harness_lanes/g4_sid_latest_discovery.md)各有独占工作树/写集/接口/测试/交接。G3三个工作树已建立、待交接，不重复派发；目标服务此刻实读paused，本次不恢复生产/付费。下方此前ready/active为历史时点，当前分工取此节及task_plan。

此前恢复运行时点目标服务active，本次G3验收保持paused。先G2，再生产落地；已完成的有界验收不等于整个计划完成。上一批G2三卡已验收并线，不重派；[新G3三卡](harness_lanes/g3_parallel_packages_2026-10-07.md)ready，可交不同harness同时开工，尚未启动。

八仓/14组补漏已写细；核心93ac5a5、G2-13/b202d07、01b/22dcc927已发布/精确CI绿；SW0b48919本地主线，RF1a2f9428与StockQA0f8fbfa远端主线均绿。MAIN当前G2-12统一获取流程尚未提交，继续旧责任/CLI/FF/并发联调；G3承担独立P1和只读调查，公共接线/生产/安装仍MAIN负责。

1. [task_plan.md](task_plan.md)：唯一当前目标、G2→R2→R3→R4→R5顺序、owner、完成条件、下一步。
2. [findings.md](findings.md)、[progress.md](progress.md)：当前事实、真实验收与错误记录。
3. [n4_production_batch_implementation.md](n4_production_batch_implementation.md)：scope/预算/model/CLI/恢复/空间的详细接口；原三个节点已验收历史，不重新执行。
4. [radical_simplification_proposal_2026-10-03.md](radical_simplification_proposal_2026-10-03.md)：已采纳的八束优化及迁移前置，实施状态以task_plan为准。
5. [最终空间收据](harness_lanes/results/gd_storage_final_cleanup_2026-10-03.md)和[46项历史审计](gate_permission_inventory_2026-10-03.md)：基线证据，不产生新的许可/签收。
6. [G2全面补漏实施单](gate_simplification_reaudit_2026-10-07.md)：当前P0，八仓审计、14组和scoped pin漏项、完整同步写集/接口和仅两个大测试节点；隐含整库检查/补种列P0。
7. [全部PWF落地细则](all_pwf_completion_implementation_2026-10-07.md)：G2完成后继续生产来源、正式运行、原文收益决策和最终收口。
8. [并行实施总计划](parallel_execution_plan_2026-10-03.md)与[当前G3三个施工包](harness_lanes/g3_parallel_packages_2026-10-07.md)：RF历史质量/包装、CWP维护后端、R2/R4只读事实独占目录/写集，可同时开工，详细单卡自包含。G2三卡已完成，Dayu/IQS不分派。

其余W/G/worker/review/space和并行卡保留技术背景与已经完成的证据，执行顺序、权限/审批和测试频率均由task_plan覆盖。已交付harness不重复派发；未交付独立线由root给出独占范围后接入当前接口。所有原始资料继续保留。

旧三份PWF入口完整历史保存在Git bff81af，未复制归档。无需在每次恢复时加载全部旧Phase。新进展及时正常提交推送；有限批次和大节点真实测试先于旧Worker退出/无引用派生删除。
