# 共享引擎＋多份文档阅读策略 — ROOT统一执行PWF

PLAN_ID: document-understanding-2026-10-13
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/company-wiki/docs/plans
Owner: ROOT
Current Phase: A — 生产选择与唯一材料，接口/TDD准备

## Goal

完成一个共享文档阅读引擎与多份市场/文档/业务策略，并接入正式资料处理、原语言摘要和缓存。与母PWF共用G2/G4/G5真实验证；不另建引擎、任务库、全篇MD副本、权限或人工签收链。原件保留，IO/身份/预算各由负责层执行。

此表是唯一当前执行状态；详细施工见 [completion_implementation.md](completion_implementation.md)。旧DU/DU2接收已关闭，旧卡和阶段文字只供历史/设计参考，不再等待交付或重发同卡。改前先读本表、findings、progress及所做节点细则。

## 已完成基础

- [complete] 20原件调查、设计与DU/1接口、原三包和独立接收整改。三仓本轮架构质量改造已发布。
- [complete] DU2三最新作者＋ROOT整合：一个运行catalog含24文档规格/14业务策略；层级/实际范围、原文闭包、字体/粗几何和有界布局实际消费。
- [complete] 联合1135 PASS，四PDF658原文span验真，真实10-Q六项PASS，独审共同根因关闭；原件/配置/测试环境保持。
- [complete] 源码deb7eb7d并master并推送，CI38476678472 success；正常pre-push4175 PASS/17 SKIP。收尾9e4faf2a已推送，ROOT整合树/临时材料已归档回收，作者bindings保持。

## 剩余阶段（仅三大节点）

### Phase A: 生产选择与唯一材料

**Status:** in_progress

统一ReadingPlan进入既有candidate/finalize/budget流程，业务价值/主题多样性/新信息和完整闭合边际成本共同决定选择。根治旧活跃题材/固定4–9个月优待，不能仅改排序或提高cap。共享上下文唯一材料＋组引用，复用生产eN/gN形式。先写行为RED，集中实现并跑A受影响测试。

责任范围：source_catalog的候选/预算/最终选择；document_understanding的选择桥/摘要组装。旧版本仅供必要回放，新默认在C达标后切换。

### Phase B: 正式摘要、generation与缓存恢复

**Status:** pending

同一次parser→DU→正式SelectResult→ModelRequest→NarrativeRef，只有最终实际采用提示进入模型。selection-decision指纹与final-sent-policy指纹分开；未选但参与决策的策略变化也失效，无关策略不全库重建。

采用base归属→正式select一次→final generation CAS→模型任务顺序，复用原AUTO/Store/outbox与计费。production factory/loopback、相关/无关变更0POST、取消/丢ACK/重启、旧ref回放和消费者在一次集中工程E2E节点验收，独立复核后正常发布。不新建canary或人工许可。

### Phase C: 真实质量、泛化、默认切换和清理

**Status:** pending

同原件同范围同预算旧/新比较，精确使用配置的MiMo/DeepSeek/MiniMax和原累计账$20/200万token；与母G2真实摘要、G4原三公司、G5新A/H/US三公司共用一个验证窗口。包含文档类型覆盖、关键业务gold、原文回开、数字/角色/阶段、空间/时间/并发观察。

细分栏/细表不足及缺样诚实记录；关键经营信息漏读不能用partial标签放行。达标后一次切正式默认、清理被替代运行逻辑和自有scratch，保留历史ref回放、原件及必要usage，正常并线/推送/精确CI与技能定点同步。

## Next Step

在既有A测试包先冻结并写“实际策略影响生产选中、未列题材可入选、共享闭包唯一成本、超限整体deferred”的反例；记录RED，再实现同一个预算planner的新策略。当前生产默认尚未切换，不能据DU2模块PASS标全升级完成。

## 完成标准与注意事项

- A/B/C全部有真实证据，正式默认启用且发布后才关闭共享阅读升级。母研究循环按原计划继续，不将模块PASS当经济研究PASS。
- 旧微软关键业务baseline4/8 FAIL保持；真实/合成/不可评分别报告，不降gold或删失败收据。
- 生产HTTP原已unique evidence rows；重复正文在DU中间package视图。接线复用既有传输，不能误修正确的HTTP机制。
- 原件与生产配置不写穿；测试独立tmp/sentinel/owned清单，成功/失败都恢复。Dayu/IQS和他人WIP不动。
- ROOT统一共有接口/状态/Git。作者卡全部已交付，不自动重派；未来分包需排他目录与冻结接口。
- 既有静态/快速hooks正常执行；只在A/B/C大节点做集中复核，不新增小节点门禁。

## 依据和历史

[已发布DU2验收](du2-reception/acceptance.md)、[发布收据](du2-reception/evidence/publication.json)、[旧DU验收](reception/acceptance.md)、[设计](design.md)、[接口](INTERFACES.md)、[旧细则](review/root_implementation.md)、[母跨市场PWF](../cross-market-rf-e2e-2026-10-08/task_plan.md)。原ROOT阶段表保留在Git 9e4faf2a；本表已合并其完成事实与全部剩余任务，历史不再作为当前指令。
