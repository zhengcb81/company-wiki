# DU2-FACETS：业务关注点、经营机制和必要上下文

状态 READY；可独立开工，与FAMILIES、LAYOUT和ROOT没有写入重叠。

仓库：company-wiki。
工作目录：C:/Users/郑曾波/Projects/_harness_worktrees/document-reading-review-20261013/facets
分支：codex/du2-facets-20261013
PLAN_ID=du2-facets；PWF_PLAN_ROOT=<本worktree>/.planning。

## 任务

先读AGENTS、[复审](../report.md)、[业务矩阵](../strategy_matrix.md)、[公共接口](../INTERFACES.md)及原sample_manifest。本包解决“业务里什么最有用、证据必须带哪些限定”，产出各类文档共用的数据策略；不做投资模型，不代替revenue-forecast，不抽全套财务报表，不调用LLM做答案生产。

独占 docs/plans/document-understanding-2026-10-13/review/deliverables/facets/**（含自身tests），.planning/du2-facets/**。不改FAMILIES的文档分类与章节别名，不改任何src、旧DU模块、benchmark、shared PWF/CI/config/安装或其他仓。

## 实施步骤

1. 写自身PWF、base/status。先对“第二曲线阶段”和“产能项目”各写规格与反例，RED查必要槽位/显式候选字段/支持组等结构不变量。缺否定、错项目、未来当实际的语义输入/期望交ROOT，记NOT_RUN_ROOT_INTEGRATION；C节点核实原文含义。不能自建推理器或声称本包已执行生产语义测试。
2. 覆盖八个共用面：主业与商业机制、行业与竞争、新产品/新业务、海外、新客户订单与履约、产能/募投、经营指标、业务风险/明确否认。为每个面写保存对象、证据形态、必须随带条件、常见误解和未披露/未读/未答行为。
3. 增加四类可组合经营模式：软件订阅/消费，零售店网，制造认证/利用率，生物医药/CDMO研发或商业化。只写通用机制，不能出现“某公司固定产品名单”；药物试验阶段、订单/里程碑/版税与收入分开，无原文依据就unknown。
4. 用已有真实片段锚定风险：恒锋分期先后和建设期；金禾原有/新增产能与资金缺口；万润问句前提、管理层否定、股东vs上市公司；名创门店模式/总数/地域/期后；微软消费/订阅与电话会角色。需要补本地不同公司/行业时只读现有池；没有就交缺样清单，不编“专家常识”作公司事实。
5. 每条断言写条件式required_context：例如只有输出数量才要求单位/分母，描述定性进度不强制补数字；stage/subject/role/否定决定原意时不可丢。强事实、推测、指导目标、计划、假设风险分开，不将管理层展望升级成确定收入。
6. 正反配对case保持同一原文，改变主体/时间/单位/范围/语态或删条件，写expected_failure和理由；同时给低信息/无业务/无回答的合法退出例。包括纯财务数字“不要求选，但选了不可错”，防止基准反向逼引擎膨胀。
7. 测试数据格式/引用/必须条件以及机制组合不互相覆盖，人工对照原文的C记录单列；不能实现独立自然语言推理器或第二summary generator。ROOT消费required_context及focus，统一实现闭包、选择、校验。

交付 README、index.json、records/、cases/、tests/、coverage_matrix.md、acquisition_requests.json，以及本包handoff。共享case接口见第4节；FAMILIES提供用途，FACETS提供业务语义，两包都可在对方为空时自足交付。

## A/B/C 与验证

- A：两份语义规格、关键错误反例与合法空值规则。
- B：八个关注面/四类机制的集中数据和反例测试；必要槽位均说明条件，不要求未披露事实。
- C：真实原文核对，至少覆盖不同市场与经营模式；其余明确缺样，恢复目录与一次交接。

命令：python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/review/deliverables/facets/tests -q

不加全仓CI，不跑完整研究和付费模型。用实际数据支持目标，不以regex碰到关键字声称事实蕴含。每source引文合计≤8KiB，本包持久数据建议≤512KiB，0原件复制；使用自有tmp/哨兵并finally恢复，核对已读原SHA/mtime。正常提交本分支并交handoff停止，不并主线或安装。
