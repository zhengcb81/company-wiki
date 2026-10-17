# DU9-CWP-GEOMETRY-POLICY：唯一catalog的几何阅读策略

工作目录：`C:/Users/郑曾波/Projects/company-wiki-du9-geometry-policy`。基线为已提交CWP `bf160c8e3fd8b9620f6bbc891ba448fd5647e388`，不追ROOT WIP。PLAN_ID=du9-geometry-policy-2026-10-16。

## 真实问题与目标

现有完整section_rules只有阅读role/priority/path/questions，没有明确几何请求语义；行政profile也是priority1，不能把阅读优先级直接等同fine扫描。金禾可转债原生书签第八章“本次募集资金运用”物理223，现family aliases有“募集资金运用”而heading_path根漏掉该变体。名创业务回顾及展望已有path。ROOT只读调查已经记录，但此卡仍须从实际catalog和测试确认。

在**原reading_catalog**中设计/补齐typed geometry_intent，经原registry解析、profile因果摘要和一个薄公开编译器输出INTERFACES的du-geometry-policy/1。同一共享引擎/同一catalog；不得另建provider配置、模板引擎、关键词词典或技能分支。

## 排他白名单

- src/company_wiki/document_understanding/profiles/{reading_catalog.json,registry.py}。
- 新增 profiles/geometry_policy.py（必要导出可改该目录__init__.py，仅导出本接口）。
- 新 tests/unit/du9_geometry_policy/ 及同名专用fixture目录。
- 自己 docs/plans/du9-geometry-policy-2026-10-16/。

其他profiles模块只读；schema/验证器若确需另文件，先向ROOT提交最小方案，不自行扩大。禁止改geometry_intent/调度器、strategy_binding、structure、source_catalog、automation、旧gold、CI和hooks。

## 实施细则

1. A列出实际全部family/form和各section，按经营/募投/混合附注/风险/行政/unknown确定几何**请求意图**，不是业务真相。覆盖A/H/US年半季、IPO/再融资/可转债、IR/业绩附件/电话会/行政。不强行对TXT开启几何。
2. 向实际sections增加typed字段，缺省unknown。保留完整heading_path/Part/Item上下文；补正实际可转债变体，不使用flatten fallback抹掉冲突。未知文档不能hard reject；financial_notes中的客户/RPO/销量仍可按实际表候选申请。
3. registry原逻辑唯一消费；增加geometry_policy.compile_geometry_policy，编译不重新route/match、不读取文件或clock。版本/实际几何内容改动进入既有profile/component摘要。原get_profile/legacy序列化若需要保持旧wire，采用兼容投影，不让缺省字段污染历史请求。
4. malformed enum/path/重复rule_key显式可诊断；预算/上限不在此模块执行，不加“已签收/已授权”字段。正常策略修改不要求用户逐条批准。

## A/B/C测试及独审

A先保存缺少几何能力、行政priority1、真实alias/path缺口的行为RED和独立期望。B集中原profiles/strategy相关快测及新矩阵；C用现route→resolve_reading_profile→compile真实入口，覆盖不同市场同名章节、risk标题含募投、附注经营表、行政含经营附件、unknown/缺字段/冲突。改实际相关几何策略必须改变摘要；无关family不得导致本source库存变化；不降低旧gold。

不调用真实供应商；不把配置矩阵通过写成真实PDF解析/摘要通过。最后严格执行INTERFACES的独立agent全面审查→全部修复→复核PASS，提交报告/源码SHA，再交接STOP。ROOT负责与独立PLANNER和来源生产port联调。
