# 预算制度简化实施单

用户2026-10-23明确要求按已讨论建议实施。协调员ROOT负责；本单纳入DU11主线，不建立第二费用账或新的人工许可。W09/W11外包写集、封存scope/metadata/usage和原件不改。

## 目标与唯一责任层

- 当前任务累计外部模型额度改为10,000,000 tokens / USD20；历史已计量、unknown hold和FX hold全部沿用，不清零。
- 单公司150k tokens / USD1改软分配，只显示偏差；一个请求须满足真实模型部署/上下文及输出上限，并在累计余额内。禁止继续以公司软目标阻断。
- 本地文档工作量由一个可配置工厂创建，parse/select/嵌套phase共用同一账户；默认16M暂保留，支持显式配置更大值，不以扩大额度掩盖算法根因。错误必须报告dimension、phase、used、requested、limit，不能泛称layout。
- 选材96片段/48k字符和费用分开诊断。按信息量分批属于W08步骤5/正式摘要接线；本节点不把提高token额度宣称为已解决内容遗漏，不扩大依赖闭包8units/4blocks/2048chars。
- 新有效policy/scope通过当前入口采用；旧预检、失败、来源seal和历史metadata保持原字节。外包冻结输入里的旧2M仍是历史基线，最终ROOT整合用新的有效policy，不重写作者工区。

## 实施顺序

1. 只读查实际mother账、执行入口、审计技能scope及公司硬拒绝，先冻结中性RED。所有测试用独占tmp，无外网/真实付费调用。
2. 在CWP单一resource policy/现有预算owner接线累计限额、公司软目标与本地工作配置。保留生产AUTO原生reservation、unknown/并发计量；不再添加账本、签收或材料授权JSON。
3. 更新真实当前任务有效配置和恢复入口；累计账重算证明charged/unknown完全不变、只限额改变。不得修改封存文件。
4. 集中单测/真实loopback集成检查：子目标超限但母余额足够可执行；全局token/USD不足仍拒绝；unknown预留仍占额度；重试/恢复不重复POST；显式工作配置经parse/select保持同一实例；本地耗尽与选材容量诊断不同。
5. 独立agent查完整性/质量，全部修复后提交推送、更新CURRENT_STATUS/目标文档/外包整合说明；定点同步确有变更的审计技能副本。无新付费调用。

## 当前状态

PASS_COMMITTED_PUSHED_INSTALLED：CWP源码ab95027b已正常推送，完整7165P/24既有skip、另146smokeP；Audit源码564f77a及收尾af255d4已提交，两份39/39技能安装已核。Audit无remote，不声称远端发布。精确CWP CI40034980056已completed/success，状态收据见review/budget-regime-20261023/engineering-closeout.json。累计限额和工量接入单一config/resource_budget.yaml。现母账仍1,561,352tokens/631,959microUSD、新余额8,438,648tokens/19,368,041microUSD，旧7+新4unknown保留。当前有效scope以review/budget-regime-20261023/effective-scope-observation.json所指新文件为准，原scope未改。

独审先确认两个真实缺陷：有选中片段时计算耗尽漏报、计算额度变更后未完整读取结果仍可命中cache。ROOT已修为实际document_work诊断，未观察requested记null；资源中断的因果inventory保留partial，实际工作额度进入来源cache身份，费用/公司软目标不进入来源语义。普通tests/unit/du11_production/test_document_work_policy.py固化真实内存PDF反控，不依赖固定耗尽数字。最终独审99P及实际摘要/同run恢复47P，ROOT本机loopback恢复12P、常规2个真实PDF回归P；测试有重叠，不相加冒充单次总量。Audit low另有18项独审，完整662项660P/2skip；未重置账、未重复付费测试。

W08业务14目标、指引/跨页、96片段分批及正式真实新摘要仍OPEN。预算工程通过不代签这些内容质量；外包W09已正式交付待ROOT内容验收，W11仍独占。

## 验收与交接

只有上述实际执行行为和对账通过，才称预算制度生效。报告必须区分累计费用、token、公司软目标、请求技术限制、本地工作量和选材容量；附实际配置来源、before/after合计、测试版本及清理收据。旧2M用户授权文档保留，新的明确指令优先。native goal正文暂保留旧字样不代表旧额度仍约束当前任务；唯一CURRENT_STATUS及新有效policy记录最新授权。

下一步回ROOT主线：W09内容修复及并线、W08合当前预算配置后继续指引/跨页/选材。当前预算恢复scope为CURRENT_STATUS.json.budget_regime.current_effective_scope所指文件；旧scope和外包冻结输入不重写。
