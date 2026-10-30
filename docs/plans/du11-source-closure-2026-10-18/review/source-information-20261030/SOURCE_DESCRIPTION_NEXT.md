# QA闭包后的真实召回修复：共享描述与流程断言

状态：独立只读设计已接收，READY_NEXT；不得把方案当实现。先结束并发布当前QA闭包工程，再改同owner；不在QA独审冻结期间动产品文件。总体goal继续active。

## 已确认的证据与根因

真实保存的IR parsed可重放，未重读PDF/SDK或调用供应商。修正确支持范围后，独立财务/致谢退出，但以下自足内容尚未被孤立owner识别，不能拿任务或字节变少当质量通过：

- 已售产品构成/已开发300种化合物；不能把研发数量当全部已销售或量产。
- 子公司产品→客户类型→客户的下游类型；不能把“生产/制造企业”这种客户类别当生产事件。
- 收到上市审核问询、申请中止、资料更新后拟申请恢复；不是停产、监管拒绝或已经恢复审核。
- 管理层对经营影响的否认；保留报道/第三方/管理层归属，不冒充独立核实。

独立中性改名对照已确认：“公司主要产品为…”和具名主体同样缺构成语法；“公司提供…”却可识别。上市流程有无“财务数据”都financial=False/purpose unknown，因此不再改财务veto碰运气。详见本目录roster-design/README.md及actual-roster-observations.json。

## 施工顺序

1. 把独立设计的10组正反对照先落到正式单元/公共选材与task测试，冻结来源主体、阶段、模态及原文。
2. 在现有assertion_roles的描述/局部proof owner内补copular/composition与客户链，不加公司名/产品名词库；未知实体类型不等于内容无价值，也不能变发行人归属。修“器件制造企业”名词修饰假阳性，保护真正的制造/提供谓词。
3. 同prepared owner补有明确过程对象的regulatory/source-event族；申请/受理/批准/中止/条件恢复严格区分，仍用原文source+locator。复用SourceAssertionRoles/ReadingBusinessAssessment/use/relevance/value，不新建skill/provider/selector/store。
4. 用保存parsed复验所有现有业务检查点与真实SourceCard，核产品清单、研发数量、审核条件不失真；再相关域和独立大节点审查。不扩大成逐小步骤审批，不重跑超时整批。
5. 来源召回与真实task内容通过后，再按母计划正式摘要、激活/重启/跨run缓存、FF复用和RF实际采用；继续US RPO、W21接收及holdout/八步循环。不能以本节点代码或模拟链通过代签这些责任。

ROOT拥有上述共享描述/来源语义；W21三个runtime owner、原件、配置与外来工区保持隔离。
