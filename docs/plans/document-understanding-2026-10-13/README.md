# 共享文档阅读项目入口

**唯一当前入口：** [当前状态与接手指南](../du11-source-closure-2026-10-18/CURRENT_STATUS.md)。当前代码实施暂停；已完成事项、剩余任务和唯一下一步均以该页为准。

本目录保留整体设计与历史阶段。B2来源闭合、真实C普通恢复/cache/FF-RF链及类型质量节点已有交付；已接收的DU/DU2/P1–P4等卡不重新派发。后续主线为独立新公司holdout与RF审查循环，尚未启动。

[总计划](task_plan.md) / [过程](progress.md) / [发现](findings.md) / [专项类型交接](../du11-source-closure-2026-10-18/HANDOFF-2026-10-21.md)。

## 历史设计与派工入口

下面保存发生时的设计与派工记录，其中“当前可分包”“生产尚未切换”等不是新的调度指令。

<details>
<summary>展开历史README</summary>

# 共享文档阅读升级 — ROOT总入口

**当前：共享模块与DU2三包已验收/并master/推远端；生产新选择、正式摘要与真实质量收尾已统一纳入本PWF。**

执行入口：[task_plan.md](task_plan.md)。施工细则：[completion_implementation.md](completion_implementation.md)。恢复顺序：task_plan→findings→progress→当前节点细则。三大节点A选择/唯一材料→B正式链/缓存恢复→C真实质量/默认切换，ROOT统一负责接线和并线。

- 一个共享引擎，唯一运行catalog含24文档规格、14业务策略。格式前端提供真实原文/坐标，文档策略指定阅读重点，既有预算/模型/Worker负责执行。
- 原件、SourceRef与历史locator保持；无全库MD重建或新许可链。未读/opaque/预算到限与无业务内容分开。
- 已交付卡不再派工。原作者树/local bindings只读保留；代码所有权与新接线在当前细则中明确。
- 新链尚未成为生产默认；微软旧关键业务4/8 FAIL、四样本细列/细cells缺口保留，后续必须按业务质量验证。

## 证据与设计

[DU2验收](du2-reception/acceptance.md) / [精确发布](du2-reception/evidence/publication.json)：源码deb7eb7d、CI38476678472 success，1135联合PASS、四PDF658原文span验真、真实10-Q六项PASS。

[设计](design.md)、[DU/1接口](INTERFACES.md)、[深化接口](review/INTERFACES.md)、[调查发现](findings.md)、[20样本清单](sample_manifest.json)、[旧DU验收](reception/acceptance.md)。implementation/review和原cards保留设计/历史；当前调度只看task_plan，避免按旧“正在施工”文字重开任务。

[母跨市场PWF](../cross-market-rf-e2e-2026-10-08/task_plan.md)、[母叙述资料PWF](../narrative-evidence-pilot-2026-09-26/task_plan.md)。真实G2/G4/G5共享一次窗口，不重复测试或签收。

## 当前可分包工作

[DU3：三张独立施工卡与工作目录](parallel/du3-2026-10-14/README.md)，QUALITY/DEPENDENCIES/GEOMETRY排他模块可同时启动；ROOT继续Phase A生产选择/最终材料，不改它们的在制目录。

</details>
