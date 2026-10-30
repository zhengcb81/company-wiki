# QA闭包后的真实召回修复：共享描述与流程断言

状态：QA已发布；来源描述实现、受影响域和真实输入8检查点已通过，最终独审复核中，尚未发布。总体goal继续active。

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

## 2026-10-30 实施与退回根因闭合

独审R1复现：模板receipt/产品构成用途漏传、具名process/impact的QA边界漏传、英文逗号未知成员被预切、英文影响缺语法、process前缀重复扫描呈平方增长。正式补测先13失败/42通过，另实际未来套话任务1失败；已在同owner根修，不使用公司名/产品词库、提高额度或删断言换绿。规则/字母首位置只算一次；完整构成frame保护有界逗号成员，显式新actor仍结束；时间边界直接共用既有ACTION_TEMPORAL_FRAME，条件/模态和原文不改。

验证：3377通过/11既有skip/66.04秒；397源mypy及ruff通过。真实保存parsed复验15spans/8admitted，各自支持范围覆盖已售清单+300研发、子公司客户链、审核申请/条件恢复、报道前提下重大影响否认、需求因果、VC否认+股东联系希望、751吨未来产能，未来独立套话未进入支持。8检查点全通过但整文partial；未签全量质量/正式摘要/缓存/RF。原PDF SHA两次核对不变，0新下载/模型/SDK。

执行差错：一次PowerShell花括号路径在只读查询报ParserError，改用显式两路径；一次短测写错已知测试文件名导致0收集，纠正为真实文件后95P；这些错误日志保留，不当绿测试。最终受影响域已包含完整du11_production/selection/root/du4/sourcequality/sourceclosure及输出失败收尾。

下一步：独立复审必须绑定当前6源码/测试文件稳定raw与LF SHA；通过再发布、精确CI。后续主线真实摘要/缓存恢复/FF-RF采用、US RPO与W21生产接收、holdout及完整八步循环仍需实施。不得因本组件通过结束goal。


最终稳定版追加：独审又检出“产品介绍模板”标题只靠前有产品名词绕过用途、成本事件错误污染经营影响；5RED/57PASS后修为真实head→predicate→模板支配、经营影响由business/operations目标支配。正式62项，相关132P/3.64秒，最终受影响域3383P/11skip/64.89秒，397mypy/ruff；以前3377为修第二轮前历史观察。真实real-r3仍15spans/8卡/8检查点全true；归档重放selection gzip SHA f18b589eed76ea6286e1e6a39a1eed25ffae18c560f87ac5a6dceb1f92f3372d完全一致。隔离测试根及额外重放输出清理，复现紧凑包约195KB，不复制原PDF/SDK/数据库。最终独审尚待签署，不冒签发布。

最终独审：27项通过/1.75秒，6文件raw/LF SHA绑定，7类共因闭合/OPEN0；实际8卡局部内容初筛无语义冲突。见description-final/independent/review.json；仅工程与输入局部通过，正式摘要等仍OPEN。当前正常发布下一步。
