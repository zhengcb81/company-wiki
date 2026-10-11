# W07 三条独立施工线

三包工作目录已经准备，均可现在同时开工。每包的独立卡包括已有上下文、明确写集、固定API/输入、A/B/C大节点测试和交接格式；自己的 `.planning/<id>/START_HERE.md` 是本地副本。

## 当前接收进度（2026-10-11）

W07-AUDIT-ANALYST已接收、修复共用引用/作用域/actual诊断并并入Audit main：实现e7c92577，收尾2c494913；90PASS＋4子案例、原13真实CLI绿。两份技能各28文件一致，已连接第四reviewer并完成安装后实际入口验证。无remote，只有本地主线。详细见[ROOT接收PWF](../../../../../.planning/w07-audit-analyst-reception/task_plan.md)。RF-MODEL工具已正常并线发布8dc26710/CI38168556914成功；组合覆盖PARTIAL，见[ROOT剩余覆盖计划](ROOT-rf-remaining-coverage.md)。FF仍未ROOT接收；不要把准备状态当作实时开工状态。

| 包 | 工作内容 | 独立施工卡 | 工作目录 |
|---|---|---|---|
| W07-FF-PERF（优先） | 原41场景不减，修准备/进程/proof共同超时 | [卡](cards/W07-FF-PERF.md) | C:/Users/郑曾波/Projects/_harness_worktrees/w07/ff-matrix-efficiency |
| W07-RF-MODEL | 8类原生模型组合反例矩阵 | [卡](cards/W07-RF-MODEL.md) | C:/Users/郑曾波/Projects/_harness_worktrees/w07/rf-model-quality |
| W07-AUDIT-ANALYST | 买方模型8类风险的只读诊断 | [卡](cards/W07-AUDIT-ANALYST.md) | C:/Users/郑曾波/Projects/_harness_worktrees/w07/audit-analyst-quality |

## 接口与调度
不等彼此：Audit直接消费ROOT固定native JSON，不依赖RF新工具；FF直接消费ET/CWP固定code-only，不依赖ROOT浮动工区。三包不同仓/不同目录；共享安装和main只由ROOT写。输入记录是可复現工程证据，不增加许可/签收门。只在A/B/C三大节点测试。

ROOT同步推进W04原生召回并线→G2真实摘要/RF消费；FF包完成后ROOT接收固定41全链并发布FF/ET；RF/Audit包接收后辅助G4原三公司和G5新三/指定八公司独审，不能替代真实公司执行。W04/G2/G4/G5仍开放。

母计划入口：[ROOT接收状态](../w06_parallel_verification_2026-10-11/ROOT-reception-status.md)。接口格式：[交接契约](handoff_contract.md)。分发清单与commit/输入固定信息：[dispatch.json](dispatch.json)。

```
                     ROOT（母计划 / 主线 / 安装）
                     │ W04 → G2 → G4 → G5
        ┌────────────┼────────────────┐
        ↓            ↓                ↓
   FF固定41提速   RF组合测试      Audit风险诊断
        └────────────┴────────────────┘
                     ↓
                ROOT接收与集成
```
