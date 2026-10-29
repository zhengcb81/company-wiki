# W20-RF-ADOPTION 原包返工单 R1（2026-10-29）

> 本轮后续返工已交付并复验，部分问题已关闭；本文件为第一轮历史。请改用[第二轮当前入口](../w20-reception-r2-20261029/RETURN_RF.md)，不重复实施已关闭任务。

这不是新施工卡；在原工区、原分支续改，不重建工作树、不回退已完成进度。ROOT当前验收为CHANGES_REQUESTED，尚未并线。主线公司循环仍暂停。

- 工作目录：`C:/Users/郑曾波/Projects/revenue-forecast-w20-adoption`
- 分支：`codex/w20-rf-adoption-20261028`
- 本轮受审HEAD：`7716c7daefd540a143a282e621e1b53f9c1d9d07`
- 原执行计划：`docs/plans/w20-rf-adoption-2026-10-28/`，PLAN_ID不变。
- 必读：[ROOT独立报告](rf-review.md)、[机器报告](rf-review.json)、[可重放反例](rf-evidence/probe.py)、原卡construction_card.md。root-provenance.json记录交付状态。

## 修复范围

1. **RF-R1/P1：验证整条实际采用关系。** 目前source-B span可以借source-A哈希/claim误报used，显式不存在source_id也可通过。共同receipt resolution应验证来源/片段/claim/parameter等已知关系属于同一条链，复用既有ID/SourceRef/capture映射，不能仅检查键各自存在。对有提供但错配的信息输出可定位诊断；缺hash仍是宽松unknown，不新增权限或人工签收。补两份合法材料同时存在、错源/错hash/错定位/错claim/错param/跨run反例，并保留正例。
2. **RF-R2/P2：聚合全部真实采用路径。** 同一span用于2026和2027，当前只留首条。按canonical span聚合全部合法路径、路径去重、错误路径单独保留诊断；不能把同回执两个dependency叫两个receipt。覆盖多回执/同回执、年度/情景、多路径排列、合法和非法路径并存，不能重复算多源。
3. **RF-R3/P2：有界读取gzip。** 133B压缩输入在1024B上限下解压出100000B。读取阶段用受界流式解压，最多limit+1后命名失败；压缩/解压两个边界都遵守配置。损坏/截断、CLI exit2且不留半输出，不能靠提高限额。
4. 收尾时更新handoff中的task_plan/progress文档SHA，当前产品源码SHA均匹配；保留历史初审和终审，不覆盖旧报告冒充修复。

## 实施和复验

只改原卡allowlist共同owner与必要测试/文档。先将ROOT反例转成真实RED，再修根因，运行当前26项短包及新增反例、必要的真实deterministic CLI链。无需反复全仓或新付费模型、下载，不能修改别仓/全局技能/预算/发布门。真实公司实际采用仍由ROOT之后验收，不能用合成通过代签。

测试根独立、记录sentinel并恢复初态。完成后调用真正独立agent对本返工单+原卡全面复审，所有本范围问题修复、OPEN清空，保留旧初审与本轮审查/修复/复验；在原delivery更新handoff.md/json、实际实现与受测/受审commit及文件SHA、命令/时长/清理/局限。存在origin就正常commit/push本分支；不自行合主线或安装。然后STOP交ROOT接收，不需要中间人工签收。
