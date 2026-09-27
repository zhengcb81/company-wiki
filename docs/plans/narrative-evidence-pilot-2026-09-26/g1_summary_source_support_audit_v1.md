# G1 人工摘要来源支持审查 v1

> 范围：仅核对 13 条人工草稿是否被所引来源支持、是否保留说话人/时间/计划状态。逐页对照样本原件和对应 locator。`supported` 表示来源确实这样记载，不表示独立证明了公司陈述为真。此记录由本次实施者完成，**不是独立审稿签字**；所有草稿仍为 `needs_review`，不可作为生产摘要。
>
> 机器校验收据：[g1_summary_validation_v8.json](g1_summary_validation_v8.json)，使用主样本 [g1_pilot_metrics_v16.json](g1_pilot_metrics_v16.json)。引用/角色校验为 13/13 通过；语义校验器明确未执行。

| 草稿 | 来源 locator | 来源支持结论 | 保留边界 / 待办 |
|---|---|---|---|
| C01-summary | P01，p.40 ¶8 | **supported**：原文明确说 EPI 设备进入客户端量产验证阶段。 | 保留“验证中、不等于量产已完成”，没有把验证状态写成商业量产。 |
| C02-summary | P02，p.21 ¶3–4 | **supported；已修正**：半年报原文先写五至十年、通过自主研发和产业合作，再在相邻拆分片段写“超过60%的设备市场”。新增拆分数字目标锚点后，两片均被选中。 | 这是未来目标，不是已达覆盖率或已实现市场份额；摘要沿用公司原句的市场范围。 |
| C03-summary | P03，p.3 ¶24–25 | **supported**：两段合起来列出四款 MOCVD 新产品、应用方向、客户端验证及部分批量订货。 | 保留“部分”范围；不推断四款都已批量销售。 |
| C04-summary | P04，p.114 ¶16 | **supported**：招股书时点称 MOCVD 设备在行业领先客户生产线上大规模投入量产。 | 仅作招股时历史披露，不外推为当前状态。 |
| C05-summary | P05，p.231 ¶27–28 | **supported**：可转债募集说明书将延伸锻件产业链、交付更高附加值零件列为项目目标和建设理由。 | 项目论证不证明已经建成、交付或形成产能。 |
| C06-certification-summary | P06，p.3 ¶13、¶38 | **supported**：注册稿写明航空数字化集成中心向下游装配延伸，需合格供应商与产品认证，并预计周期 4–9 个月。 | 只记录申报时预计周期；没有写成已经认证或已经完成。 |
| C06-rationale-summary | P06，p.101 ¶3–4 | **supported with caveat**：发行文件以“小核心、大协作”和主机厂中小锻件外协需求论证项目必要性。 | 这是公司发行文件中的行业背景/项目理由，不是独立需求验证，也不代表项目效益兑现。 |
| C07-summary | P07，p.6 表格第 16 问答 | **source-supported; locator needs review**：IR 原文称截至记录时中试线按计划推进，并预计六月底前建成、投入中试。 | locator 带 `locator_unstable`；人工草稿保留 2026-05-15 时点且明确不能证明后来按期完成。需稳定表格定位后方可提升。 |
| C08-summary | P07，p.6 表格第 15 问答 | **source-supported; locator needs review**：管理层答复称推广石化催化用沸石分子筛，且已有产品实现销售。 | locator 带 `locator_unstable`；合作意向书和已有销售分开表述，没有把意向书算作销售。 |
| C09-investor-question-summary | P08，p.2 表格第 3 问 | **source-supported; locator needs review**：这是投资者关于多类新兴业务占比和产能/认证的提问。 | “不足5%”只能标为提问中的前提，不能当作公司核实数据；locator 不稳定。 |
| C09-management-answer-summary | P08，p.2 表格第 3 答 | **source-supported; locator needs review**：管理层限定为已披露的两个 OLED 业务主体，称其 2024 年收入比例超过25%，并提示以公司公告为准。 | 分母和业务范围窄于问题所列的 OLED、光刻胶等多类新兴业务；不能把回答写成对所有新业务“低于5%”的直接更正。保留问答关系和不同角色；locator 不稳定。 |
| C10-summary | T01，¶263 chars 91–205 | **supported**：英文原句说 demand exceeds available supply，并称为 relatively extreme moment。 | 保留英文，不改成中文；只陈述管理层在电话会中的表述。 |
| C11-summary | T02，¶207 chars 331–455 | **supported with inference caveat**：原文说现在预测还太早，届时再看数据。 | “回答没有证明 superiority”是谨慎的范围说明而非原文直接结论，须由独立审稿人结合前后测试讨论确认；保留英文。 |

## 总结

- 13 条草稿均能在指定原件中找到对应语义；其中 C02 的量化目标在 v15 选择包中原本缺少拆行的数字片段，已补选择规则、锚点和预算回归测试，并在 v16 中通过。
- P07/P08 的 IR 表格定位均标 `locator_unstable`。这几条的原文支持不等于定位合同通过；必须保留 `needs_review`，稳定 locator 后再谈生产使用。
- 不使用当前草稿计算预测、公司质量、投资结论或后续事件是否兑现。P09（IR 管理办法）与 P10（业绩说明会通知）没有发现值得生成业务动态摘要的内容，试点分类为跳过。
- 本次 source-support audit 只是实施者的逐条核源。G1 的独立审查、真实生产存储差量、扫描/目录接入及任何 Worker 调度均尚未完成；须先过 G0 跨项目契约门。
