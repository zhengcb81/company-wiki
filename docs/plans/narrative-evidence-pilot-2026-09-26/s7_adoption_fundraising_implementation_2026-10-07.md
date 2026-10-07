# S7 客户采用与募投表上下文：实施细则

## 基线、调查与所有权

MAIN 5f8a3ef；运行代码c1295b1，selector0.4.1/parser0.1.1，精确CI37552600440全绿75秒。RF实读6e6b817a及三owner日志dirty，沿IR收据的5个保护SHA只读；用户source_acquisition.yaml不暂存、不覆盖。原件不改、无下载/供应商/翻译，不跨写任何外仓。

上一IR节点实际发布属于进展。本节点按总计划补剩余两个业务联系，不重做N6/IR。正式基准为九文档27/33、761定位全绿、精选62953B；原86点/33分母及96/160不变。

只读新探针[s7_budget_layout_diagnosis_2026-10-07.json](harness_lanes/results/s7_budget_layout_diagnosis_2026-10-07.json)用默认年报与招股table34局部解析，33.485秒。它不是全表正式覆盖证明。年报operating_milestone选16个span，把客户生产线采用与基地投入使用混在同一类别；全球先进产线采用候选score13，被较高分多片段/其他页的投用状态挤掉。不能按公司/页码保留。

已实际渲染并目视招股page34：两行募投引导bbox结束y441.60，项目表顶部y475.58，间隔约34点，中间仅“单位：万元”。表头为募集资金运用方向、项目总投资、拟投入募集资金；设备扩产升级、研发中心建设升级为业务项目，流动资金/合计不属本绑定目标。法律说明在表后，解析序号却把表放到法律段后，必须用视觉/表结构，不能按数组相邻拼接。

## 一组实现与一个集中发布节点

### A. 客户采用分类（先TDD）

在现OperatingFact detector增加一般性customer_adoption_milestone：产品/设备/技术实际应用到客户或先进生产线、实现批量销售；计划采用/单纯基地投用/财务增速不获得此具体reason。沿原applied reason保留原字与情态，新reason用于语义分类，不额外堆分。预算独立customer_adoption类别，固定96/160、原有reserved与整组成本/页轮转保留，不创建品牌名单或强制保留特定golden。

责任反例包括已应用全球先进产线、客户量产/批量销售，基地投用、拟应用、收入占比；有限预算下客户采用不能全部输给基地状态，并验证输入逆序稳定。RED必须来自功能，不把缺参数当业务失败。

### B. 募投引导与表（先TDD）

新增纯CWP `narrative_project_context.py`，只读NarrativeUnit/pdf visual groups、已有candidate/group map，返回现GroupEnrichmentResult，复用既有结构，不建第二索引/任务库，不改parser或v2合同。

1. 正文引导必须同时含募投/募集资金和投资于/用于/投向以下项目；表头同时证明募集资金与项目/用途。通过列标题选择用途列，项目总投资/投入资金列不能作项目名。
2. 同source/parser/language、company_filing、同页、有效bbox，表在引导下方且水平重叠，垂直间隔最多72点。两者之间只允许单位/币种标题，正文或新标题是屏障；缺bbox、不相关列/页/来源不猜测。
3. 用途列只保留具体生产/设备/研发/产品/系统等建设/升级项目；补充流动资金、还贷、合计和纯金额行不入组。用原unit全文与原locator，不改写源字节；金额若附在真实业务项目行仅作为原行上下文，不独立变金融事实。
4. 引导的原visual group成员与所有具体项目行成一个原子组，≤8单位/1600字；超限不强拼。组ID绑定成员ID/source/parser，排序稳定。若成员已属旧组，只有该旧组的全部成员都在此联系内才可收敛；不截断/覆盖跨事件组。
5. 在既有visual/neighbor enrich之后、finalize之前接线；复用candidate，补concrete_fundraising_project/fundraising_table_context及capacity_projects，保留原reason与合理既有分数；缺失项目行可新增candidate。完整组预算一起取/舍，不能仅选笼统引导句。

责任测试覆盖split intro、抽取顺序法律段在表前但视觉在表后、两具体行与财务行、错误表头/用途列、同页另一列、法务/新标题夹在二者之间、跨来源/parser/语言/role/page、缺坐标、预算不足整组拒绝、8单位/1600字、组冲突不抢占、输入逆序与原locator/文本不变。实现先占位接口返回原输入，用用例见真实RED，再实现。

### C. 发布与证据

两项齐备后selector升0.4.2（parser仍0.1.1）。统一短责任包、相关Ruff及CI全部mypy；不在commit加入pytest，不新增日常长套件或人工签收。

真实默认年报/招股短探针先确认新点及原full点，再一次真实S01/S04/S09正式Worker/outbox→RF已提交消费者→search/exact→resume，独立短tmp、本地确定性配置、0供应商费用；确认引导与真实项目同selection group，纯财务/法律没有借组入选。复用现E2E框架与保护fixture，不写RF。

冻结旧final9与实际AUTO selector升级按版本影响检查；IR旧pin和parser升级节点已绿，不再重复无变化长包。集中全九一次：必需旧full无退步、全部locator回放、原golden不改，optional取舍逐项解释，不拿所有optional永久保留作硬门。S06同原件另页canonical产能及纯财务/provider的4个remaining继续公开。

保存≤2MiB报告和小JSON收据：基线/实际代码及运行模块SHA、各阶段新点/退步、RED/GREEN、真实/夹具边界、0供应商/下载、保护指纹、独立根恢复、正常commit/push与精确CI全步骤。只保留小产物，不保存PDF PNG/整份转换正文；原先absent的测试副本/DB/包装配置/脚本结束删除。总task_plan/findings/progress同步。整体目标最后另做需求逐项完成核查，不能只凭两个golden命中宣布完成。

## 当前状态

布局/预算调查及A/B实现已完成；初始8功能RED后28新责任项及既有共200项/1.65秒通过，完整CI范围Ruff/47源mypy绿。selector0.4.2/parser0.1.1，真实局部探针31.596秒年报五required、招股table34三required full；局部证据不冒充默认/全表。当前C正式入口和全九集中验收，保持运行源码冻结，不边跑大基准边改源码；未发布前状态不标complete。

C本地验收已通过：正式真实入口/冻结旧final9/selector升级11项122.26秒，九文档364.548秒29/33，761定位零失败、旧full零回退、精选63073B/+120B。当前默认pipeline另验S06 canonical page7原句full；四个正式剩余ID不改分母。重复4→6实读为招股34/353页引导句两片段，属于不同完整项目上下文，不拆事件组凑零重复。自身tmp六路径恢复absent、原件/用户配置/RF三owner保护不变。下一正常提交/推送与精确代码CI，再整体需求审计；小收据[s7_adoption_fundraising_main_acceptance_2026-10-07.json](harness_lanes/results/s7_adoption_fundraising_main_acceptance_2026-10-07.json)。
