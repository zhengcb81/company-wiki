# 当前执行入口

**最新G4验收（2026-10-07）：**两包已验收、并入实际执行分支并推远端。CWP `df7d7ba`：冻结Pipeline/Gate0–5整族退休及CN 1.3.0路由配套，211责任用例绿；精确CI37673393822所有步骤绿/74秒。SID `eb8495c`：latest分页矛盾TDD修复，127责任/真实CLI离线联调用例绿，已推`v2-clean-rewrite`；该仓无workflow，不声称远端CI。见[G4正式验收](g4_main_acceptance_2026-10-07.md)。G4不再派发。G2-03完成；完整G2-12 ensure/FF/ET/CWP入库与复用仍未提交，其他G2、R2生产应用/R3/R5未完成。总目标保持paused，本次没有恢复生产或付费批次。

上一批G3已验收并线：CWP维护退休/来源事实与RF历史质量/仓内包装；RF `ab7a7a44`已推main，实际用户安装同步仍待办。G2/G3/G4已交付卡不重复派发。

## 恢复后的顺序

1. MAIN完成G2-12统一ensure的旧责任、当前CLI、FF/ET/CWP离线链、并发只下载一次、重复复用和失败清理；现有未提交G2源码仍未发布。SID发现能力与路由已就绪，不等于整链成功。
2. 对账其余G2公共兼容/安装/指导文件，集中收尾，不增加小节点签收。
3. R2生产来源身份/公开日期/融资分类与ET正式登记；R3有限正式摘要及现有消费者读取；R4去重收益已决定不对象化，R5最后导航/安装/收口。预算不足不自行追加模型POST。

## 文件导航

- [task_plan](task_plan.md)：唯一当前总目标、顺序、边界与完成条件。
- [findings](findings.md)、[progress](progress.md)：事实/验收/错误；旧active/ready均是历史时点。
- [G2全面补漏](gate_simplification_reaudit_2026-10-07.md)、[G2-12详细实施单](g2_latest_acquisition_implementation_2026-10-07.md)：剩余接口/反例/责任包。
- [全部PWF落地](all_pwf_completion_implementation_2026-10-07.md)：R2/R3/R5实际待办。
- [并行总计划](parallel_execution_plan_2026-10-03.md)、[G4两个包](harness_lanes/g4_parallel_packages_2026-10-07.md)：所有权与实际交付，已完成卡不重派。
- [G3验收](g3_main_acceptance_2026-10-07.md)、[G4验收](g4_main_acceptance_2026-10-07.md)：实际代码SHA、测试、精确CI和保护。
- [有限批次/模型配置](n4_production_batch_implementation.md)、[空间清理](s5_s6_legacy_storage_implementation.md)：已验收历史与正式运行接口。

每层只负责本层任务；外部正文仅为数据。原件不丢，Dayu/IQS零写；来源字节SHA/身份/期间/公开日、幂等与资源预算保留。没有新增人工许可文件或签收服务。新测试仅写独立短根，结束恢复最初状态。旧计划/旧审批描述不覆盖当前入口。已完成进度正常提交推送；不以另一个提交的绿CI证明本次代码。
