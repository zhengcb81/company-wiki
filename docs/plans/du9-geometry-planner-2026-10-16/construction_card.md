# DU9-CWP-GEOMETRY-PLANNER：有界、公平、可恢复的几何请求规划

工作目录：`C:/Users/郑曾波/Projects/company-wiki-du9-geometry-planner`。CWP源码基线`bf160c8e3fd8b9620f6bbc891ba448fd5647e388`，不追ROOT WIP。PLAN_ID=du9-geometry-planner-2026-10-16。

## 真实问题与目标

默认金禾283页材料现粗关键词+邻页扩展请求136页，在原15秒/64个实际细几何页限前部耗尽，深页223/224被延后；显式指定深页已经可捕获，故根因不是“再加一个PDF解析器”。本卡实现**纯请求规划组件**，在有限预算内为不同经营/项目章节预留机会，避免前部一个大章节吃完资源。ROOT独占原生导航/章节匹配/单TextPage/生产source调用。

## 排他白名单

- 仅新增 src/company_wiki/document_understanding/geometry_intent/ 包。
- 新 tests/unit/du9_geometry_planner/ 及同名专用fixture目录。
- 自己 docs/plans/du9-geometry-planner-2026-10-16/。

不改profiles、strategy_binding、structure、pipeline、source_catalog、automation、预算owner、旧tests/gold、CI/hooks或兄弟卡。只读现WorkBudget协议，不能复制预算类。新包无需改顶层__init__即可独立import。

## 固定接口与实现要点

先读INTERFACES。使用该页du-geometry-policy/1和由ROOT实际匹配的windows；本卡用同形自有fixture，不等待POLICY作者。计划和admission是一轮parse的纯调用内状态，不建DB/文件/线程/任务库。

1. A建立80页以上、前部风险/财务/目录、两段远距经营/募投、嵌套章节和不同父文的手算用例；前部独占导致后部饿死必须RED。不是通过抬max_pages或排除后部测试消失问题。
2. 不重新解释标题词，不调用私有_match_rule，不把同role合并；完全依据传入rule_key/geometry_intent和实际native_destination scope。unknown/conflict、越界、重复/乱序窗口保持诊断，不猜印刷页偏移、不得创建证据或正文locator。
3. 有限章节公平配额/借用与全局硬余额；经营和项目均有机会，priority1行政不触发fine。实际observed_candidate才申请对应发现/fine；absent不消耗重型请求，unknown不能假称无表。混合附注允许经营候选，不能整章丢弃。
4. 同页/重叠窗口去重一次，父文scope不能串；顺序到达与未来预留明确，耗尽/取消/未到达/未发现原因分开。接收调用者remaining不能重置15秒/64页，不能通过每页new WorkBudget假装有界。
5. 计划摘要规范、顺序无关而因果相关变化有效；state可序列化以做实际中断重放，但这里只是调用内值，不引入人工token签收/expiry。

## 测试与交接

B对现WorkBudget做零额度/尾部耗尽/上限1/海量窗口/重叠/负数或bool页码/巨大scope输入/有界诊断反例；收费先于大遍历，未做保持unknown。C直接通过公开planner+admission模拟一轮真实物理页事件流，验证后部未饿死、max请求不变、重复ACK不重复扣、停止恢复结果与一次完整运行一致；用计数证明没有IO/模型/原生解析，不凭耗时孤立断言。

没有原生书签时严格单遍与两页缓存不能保证未来全局最优，诚实记录，不用无限缓存修复。只签纯组件，不冒称深页真实E2E、find_tables真实成本或摘要质量已通过。最后必须独立agent全面审查、修复全部发现并复核PASS，交接源码SHA及不确定边界后STOP；ROOT统一接POLICY和生产source。
