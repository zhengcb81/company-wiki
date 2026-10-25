# annual14 当前来源与模型输入独立复审

本次结论：**源/输入10 PASS、4 PARTIAL、0 MISSING；模型响应语义全部NOT_REVIEWED；当前RF采用全部OPEN。** 原冻结8/6/0报告与14项目标未修改，未减分母。

绑定：当前HEAD `245f2d7ae443bc4abd2b72e28a5b1107835795d3`，生产节点 `2942355c`；原件SHA `7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2`。当前112条span/64个task；独立重编译实际scoped payload SHA `068f565928250d5eb52669942776423d25e82899841f6ea60936ea3de66797c1`，与冻结model-view一致。全部112条原文按原PDF DICT block/member offset核验，190次block/member检查零差异；原金标32条引句逐页核真。

完整SHA、逐目标full_quote/locator/task角色、原金标引句、64任务实际视图及检查结果见 [report.json](report.json)。

## 逐项结果

| 目标 | 源/输入 | 当前实际输入与剩余项 |
|---|---|---|
| ST-A01 | PARTIAL | 四业务taxonomy在t23；Chemistry全分子/制剂范围已在t55完整可见；R任务t29有Chemistry父级。 t30(D&M)与t31(TIDES)没有Chemistry父级；本地成员集不能证明二者属于Chemistry。不能把TIDES与Chemistry再相加，也不能将剩余额自动命名纯R。 |
| ST-A02 | PARTIAL | t24明确持续经营434.2亿元；t37明确总收入4,545,616.58万元及15.84%，t41也有收入15.84%；t64明确终止业务名称/范围。 精确元值的合计、持续与终止收入、21.40%和可比期重述未在当前scoped输入完整绑定；t64数字缺表头/币种单位，不能按裸列猜收入。 |
| ST-A03 | PASS | t24完整呈现四地区持续经营客户收入及同比；t39明确客户母公司所在地、对比期间已调整。 无源输入缺项。t39混有裸财务表行且保留table_structure_ambiguous；本次只将完整文字定义计为可见，不将裸数字命名，也不证明模型正确采用此定义。 |
| ST-A04 | PASS | t24明确期末持续经营580.0亿元/+28.8%；t61本身明确持续经营RPO5,800,478.75万元与预计2026确认4,220,706.46万元。 无源输入缺项；不得当作本年收入或新增订单流量。 |
| ST-A05 | PARTIAL | Chemistry364.7亿元、D&M199.2亿元/+11.4%、TIDES113.7亿元/+96.0%各自在t11/t30/t31清楚具名。 t30/t31局部输入缺上级Chemistry，跨页(1)业务父级尚未闭合；不能自行将差额归为纯R。 |
| ST-A06 | PASS | t30保留小分子D&M主体、年度新增839、年末3452及83/91/377/2901阶段存量、全年增加22。 无源输入缺项；839新增流量与3452期末存量不能混同。 |
| ST-A07 | PASS | t29同任务保留Chemistry父项、R交付超42万新化合物与R到D转化310分子。 无源输入缺项；两指标不是同一分母或收入。 |
| ST-A08 | PASS | t31具名TIDES订单+20.2%；t12具备TIDES父项，清楚列客户数+25%和服务分子数量+45%。 无源输入缺项；45%不能变成收入增速。Chemistry总父级缺口统一记A01/A05。 |
| ST-A09 | PASS | t25明确2025年底小分子API反应釜>4000kL；t26/t27在12页、t32/t33在14页将2025-09泰兴多肽建设完成与>100000L容量互为support/context，14页版本带TIDES父项。 无源输入缺项。这里证明同段陈述和时点可见，不添加未经披露的因果/额外产能量；物理体积不能直接成为收入。 |
| ST-A10 | PASS | t13具名Testing收入40.4亿元/+4.7%；t14具Testing父项及药物安全评价+4.6%；t34具Testing父项及新分子收入超30%；t40明确Testing毛利率降6.32个百分点和价格随订单转化体现。 无源输入缺项；各子事实主体和单位清楚。 |
| ST-A11 | PASS | t15具名Biology26.8亿元/+5.2%；t35带Biology父项、集团超20%新客；t19带Biology父项、新分子收入超30%。 无源输入缺项；新客比例与业务收入比例分母不同。 |
| ST-A12 | PASS | t4/t36均在同一成员集呈现2026总收入513–530亿元、持续经营+18–22%及订单/行业/贸易监管前提和不确定性。 无源输入缺项；属于年报披露时点前瞻指引，不代表现已实现或后续更新。 |
| ST-A13 | PARTIAL | t56/t57具通用控制权及时段/时点条件；t58预收先为负债后转收入；t18明确部分Chemistry/其他业务在时点确认；t16/17判断规则可见。 持续经营时段/时点精确总额未选；公司具体Testing/Biology按时段确认段(184页paragraph8/chars269-473)已admitted但budget_full，缺两项增量（本地heading+body），不能用通用会计准则补具体归属。 |
| ST-A14 | PASS | t42前五客户48.11%；t47研发预算/外包需求；t48监管；t49/t50竞争；t52建设/监管延误；t53美元结算与人民币升值对收入折算风险。 无源输入缺项；风险均按条件陈述，不能说已发生。 |

## 优先根因与责任

**1. 跨页父级仍丢失（A01/A05）。** 第13页Chemistry `(1)`父项能进入同页R的t29；第14页D&M的t30及TIDES的t31只有局部破折号父项和经营章节标题，没有Chemistry父级。第119页完整Chemistry范围已进入t55，但不能用另一任务替代本地所有权。建议在原生层级/上下文owner，用匿名“编号业务父项→跨页破折号→罗马数字”例先写根因测试，并包含相邻同级业务负例。

**2. 公司具体收入确认机制被预算挤掉（A13）。** trace精确指向 `9f5b9e7f...`，loc `page:184/paragraph:8/chars:269-473`；purpose=operating、priority=2、score=3、value_band=meaningful_fact，topics含core_business/business_revenue_recognition。它已admitted/candidate，最终是 `budget_full: used111/requested2/limit112, closure_size3`，不是源文缺失或未识别。required中4832...为已选第83页财报标题；e787...为未选第184页paragraph7“1、在某一时段内履行的履约义务”。两者按生产identity字段独立重算吻合。新增2条是local heading(14字)+body(204字)，并非两个新依赖。

当前已选t56/t57通用控制权/时段时点条件、t16/t17判断和t18部分Chemistry时点；这些不能替代Testing/Biology具体按时段确认的公司事实。建议在共享选材预算分配/闭包成本owner比较通用规则与公司具体机制的效用，保持上限和质量规则。没有证据要求再增加全文/批次数。

**3. 精确财务数据走实际完整来源（A02/A13）。** 原件第7/13/183/184页含单位、期间、精确值与重述；第235页终止经营表完整。当前t64是缺表头的文字块，保留table_structure_ambiguous完全必要。A02原金标精确元值、21.40%与重述，A13精确时段/时点总额依然逐项未满足；可通过完整表/已配置API按需取得，但本次不能代签它们已进入新RF。

ROOT另有来源路线调查收据 `docs/plans/du11-source-closure-2026-10-18/review/st-a02-table-source-20261025/source-route-receipt.json`（SHA `f2fab288e592843c291047825b7a2c722fb79cae597e8a62d58f6e040a1ef48a`），状态OBSERVED_OLD_RF_ONLY_CURRENT_ATTEMPT_STILL_OPEN。该收据核实既有SourceVersionReader/表格路线及旧RF引用，不代表新金融API调用或当前attempt采用。

## 已修复范围及保留限制

- A03定义现已实际进入t39；t24金额/同比与t39明确文字定义均可见。t39混有裸财务列，质量标记仍在，本次不将那些数字命名，响应语义仍待审。
- A09日期与容量目前已互为support/context：12页t26/t27和14页t32/t33；14页版本还带TIDES父项。本次仅确认原文同段陈述可见，不添加新因果或物理容量到收入的换算。
- 全部旧通过项在本次源/输入审查保持通过；4项partial为A01/A02/A05/A13。A01全文范围子缺口已补回，但父级仍缺，因此整项不升PASS。
- 没有模型响应、正式摘要质量或当前RF公式采用验收；这些全部保持NOT_REVIEWED/OPEN。没有运行全量测试，没有外网、模型、下载、原件复制或生产写入。

## 复核绑定

- selection SHA `6fb97953c61ed7eb76c47e0c10d852ff1a5201926991862f2a43d08166c2fe3a`
- model-view SHA `de2057a4df8d5186f79e6d77547495e7788a5b200e76e0439fab8664d38dd34e`
- trace SHA `638710d062e1f46811865f6638172a5b325fae780054da1710fc40aa7ae8e39a`
- 原冻结内容报告 SHA `4b68ac829e0c53e2416cac5558fb3f3ed48d6fdb5ec0c02421f6a2d74b673926`
- 原14目标金标 SHA `92aafc341326845cac2aada578b67d6211f99244163f90345269686fedf0b258`
- 全部374份生产py源码digest `46ced6fe18c8d7b47aa2525ccb9350daa31289a4059f7e4ddc14549d0b12f0a0`，与来源replay收据一致；20份selection显式源码SHA亦全一致。
