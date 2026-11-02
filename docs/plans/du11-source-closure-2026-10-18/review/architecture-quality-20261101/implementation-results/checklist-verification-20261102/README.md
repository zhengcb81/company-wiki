# 整改清单逐项复核（2026-11-02）

唯一详细入口：[checklist.md](checklist.md)/[机器对照表](checklist.json)。主执行状态仍为[CURRENT_STATUS](../../../../CURRENT_STATUS.md)。

原41项全部对应（40工程完成、Q11边界保留），工具T01逐个核8入口；本次3新增漏项已直接TDD修复，独审通过，本次新源码精确CI成功。2可选优化和真实公司验收仍单列。未新建施工包/许可或重复全量测试。

- [原Q01–Q14独立核对](q-items-independent.md)：每项源码/测试/独审/发布，16MiB初始反例是补修前历史。
- [工具逐入口独立核对](tooling-independent.md)：T01八入口、T02、SWEEP四项、两可选及保留边界。
- [跨仓独立核对](crossrepo-independent.md)：RF五项、SW八项、FF/invest/安装与保留理由；150/150所检安装文件一致。
- [ROOT核心/集成对照](core-and-integration.json)：G1–G5、F1–F3及实际父预算等增量。
- [首批两项补漏TDD与受影响测试](residual-repair.json)；[独立增量审查](residual-repair-independent.md)。
- [冻结元数据补漏](residual-binding-repair.json)；[独立增量审查](residual-binding-independent.md)。

报告均限定具体版本和范围。旧作者pending/旧FAIL不删改，当前表明确谁已覆盖；StockWiki仅本地主线未配置remote，不冒远端已验。原件/生产config/DB、R4及其他owner WIP保持，0收费/下载。
