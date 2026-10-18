# DU11 正式 C 内容审查（CN / US，2026-10-18）

- 审查对象：两次真实供应商 C run
  - CN：live-cn-h1-b2v3i-20261018（MiMo mimo-v2.6-flash）
  - US：live-us-10k-b2v3-20261018（MiniMax MiniMax-M3）
- 实际收据目录：.planning/shared-reading-production/du11/live-cn-h1-b2v3i-20261018 与 live-us-10k-b2v3-20261018
- 说明：请求给出的 docs/plans/du11-source-closure-2026-10-18/live-... 路径在本次工作区不存在；上述 .planning 路径是实际 receipt/overall/materials 所在处，本报告按实际收据审查。
- 审查方式：只读；打开 overall/receipt/rf-narrative、claims 引用的 evidence_spans、gold 与 metadata；未改源码/测试/配置，未做 git 操作，未重新调用供应商。
- 原件/身份：CN source_sha256 182e2062fed950cd32310099cdf47f392c791440ce251f5e3bab7137dbc932fe；US source_sha256 99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe。
- 工程 receipt：两次 status=PASS、1 POST、activation_recovery PASS、cross_run_zero_POST=true；但 quality_status=needs_review、selection_status=partial，因此 receipt PASS 不是内容通过。

## 结论

- **CN：CONTENT_FAIL**。10 个 required business facts 命中 8 个，缺 f-gan-power-stage 与 f-inp-development-started（均 critical，且对应 evidence span 已被选中）；另有三条 P1 级 claim 质量问题（该新产品未闭合、t3-1 截断、t4-1 从句中段开始）。数字与引用大体准确；无投资结论。
- **US：CONTENT_FAIL**。8 个 required business facts 只命中 2 个（f-m365-consumer-vs-commercial-metric、f-azure-growth-inside-combined-line），f-azure-inside-intelligent-cloud 只算部分；缺 5 个 critical（Azure consumption-based、three segments、August 2024 segment change、RPO 375/368、RPO 40%/next 12 months）。8 条 claim 本身都是逐字引用且数字正确，但内容覆盖严重不足。
- 两次都没有投资评级、目标价、估值或买卖建议；语言分别保持中文/英文；数字未发现单位或换算错误。

## 1. Required facts 覆盖表

### CN（10 required；critical 7）

| fact id | importance | 命中 | claim | 说明 |
|---|---|---|---|---|
| f-five-year-target-is-plan | critical | 命中 | t13-1 | 未来五年 60%/70% 计划保留 |
| f-current-coverage-30 | critical | 命中 | t13-1 | 五十多种设备/超 30% 当前覆盖保留 |
| f-cmp-acquisition-completed | critical | 命中 | t12-1 | 报告期内完成众硅公司控股权收购、CMP |
| f-microled-sample-verification | critical | 命中 | t30-1 | Preciomo Udx / 2023 年底 / 重复订单 |
| f-gan-power-stage | critical | **缺失** | 无 | 选中 evidence 有 PRISMO PD5 2022 推出/交付验证/重复订单；summary 无 |
| f-sic-8inch-stage | critical | 命中 | t34-1 | 新型 8 寸碳化硅外延设备/生产验证/重复订单 |
| f-inp-development-started | critical | **缺失** | 无 | 选中 evidence 有 2026H1 启动 InP 专用 MOCVD 开发/下半年计划；summary 无 |
| f-advanced-packaging-primo-matrix | normal | 命中 | t38-1 | Primo Matrix 即将发往国内头部客户产线验证 |
| f-tsv-300e-serving | normal | 命中 | t38-1 | Primo TSV 300E 持续服务/重复订单 |
| f-third-gen-tsv-rd | normal | 命中 | t38-1 | 第三代 TSV 刻蚀机研发/客户订单/即将验证 |

CN 命中 8/10；critical 命中 5/7。缺失两项都是 critical，且对应 evidence 已在 96 个选中 span 中，属于 summary 漏写而不是不可读。

### US（8 required；全部 critical）

| fact id | 命中 | claim | 说明 |
|---|---|---|---|
| f-azure-is-consumption-based | **缺失** | 无 | 选中 evidence paragraph:233 有 infrastructure/platform consumption-based；summary 无 |
| f-azure-inside-intelligent-cloud | **部分/缺失** | t5-1 | t5-1 有 Server products/cloud、Azure and other cloud services，但没有 Intelligent Cloud 段归属 |
| f-three-segments | **缺失** | 无 | 选中 evidence paragraph:192 有三个分部原文；summary 无 |
| f-segment-change-in-august-2024 | **缺失** | 无 | 选中 evidence paragraph:193/732；summary 无 |
| f-m365-consumer-vs-commercial-metric | 命中 | t6-1 / t7-1 | Consumer 11%/11%、Commercial 14%/15% 分开保留 |
| f-azure-growth-inside-combined-line | 命中 | t8-1 | Server 23% / Azure and other 34%，未误写成 Azure 23% |
| f-rpo-scope-and-amount | **缺失** | 无 | 选中 evidence paragraph:3845 有 375B/368B/June 30 2025；summary 无 |
| f-rpo-recognition-is-forward | **缺失** | 无 | 选中 evidence 同段有约 40%/next 12 months；summary 无 |

US 命中 2/8，partial 1/8；所有 required 都有选中 evidence，主要问题是 summary claim 选择/覆盖不足，不是不可读。

## 2. Claim 逐条引用核对

### CN（20 claims）

| claim | 引用 locator | 判断 |
|---|---|---|
| t1-1 研发投入合计 | page30/table0/row1-6 + page28 header/单位 | 数字与合计行一致；但 6 个 span 均带 table_structure_ambiguous，表格结构未证明，列映射靠 header 阅读；P2 |
| t2-1 该新产品 Micro-LED | page18/paragraph:9；context page17/paragraph:26 标题 | 句子逐字支持，但“该新产品”没有产品名；context 只有标题，标题不能提名，P1 |
| t3-1 外延片 MOCVD | page11/paragraph:4 | 原文在 “MOCVD 设” 处被段落/页截断；claim 末尾加 “（原文截断）”，不是源文本，句子不完整；P1 |
| t4-1 到多个先进逻辑客户端 | page17/paragraph:4 | 原文/claim 都以 “到多个…” 开头，缺主语/前句；P1 |
| t5-1 大额商誉/中微众硅 | page177/paragraph:9 | 逐字支持；与 t8-1 的“众硅公司”命名不一致，P2 命名一致性 |
| t6-1 SEMI 2026 1659 亿美元 | page10/paragraph:14/chars:341-436 | 支持 |
| t7-1 中微公司主营业务 | page10/paragraph:21/chars:504-626 | 支持 |
| t8-1 收购众硅公司/CMP | page13/paragraph:4/chars:88-219 | 支持 |
| t9-1 30%/未来五年 60%/70% | page13/paragraph:18/chars:495-605 | 支持；当前 actual 与未来 plan 区分保留 |
| t10-1 研发投入 20.41 亿/36.86% | page15/paragraph:7/chars:137-294 | 支持 |
| t11-1 CCP 产品/UD-RIE | page15/paragraph:23/chars:553-755 | 支持；原文“高深刻比”为源文本 typo，claim 照抄，P3 |
| t12-1 Primo XD-RIE Alpha/Beta | page15/paragraph:35/chars:919-970 | 支持 |
| t13-1 ICP 50 多客户 | page16/paragraph:2/chars:38-175 | 支持 |
| t14-1 Primo Nanova LUX-Cryo/Angnova | page16/paragraph:5/chars:176-347 | 支持 |
| t15-1 Preciomo Udx/2023 底 | page18/paragraph:6/chars:152-250 | 支持 |
| t16-1 8 寸碳化硅外延设备 | page18/paragraph:21/chars:574-687 | 支持 |
| t17-1 TSV 300E/Matrix/第三代 | page18/paragraph:35/chars:945-1115 | 支持 |
| t18-1 南昌 14 万平方米/2023-07 | page19/paragraph:38/chars:991-1032 | 支持 |
| t19-1 中段/超高深宽比量产/60:1 | page25/paragraph:21/chars:453-625 | 支持 |
| t20-1 研发投入不足风险 | page33/paragraph:16/chars:433-523 | 支持；uncertain 模态合理 |

CN 引用本身大多逐字成立；P1 集中在 t2-1、t3-1、t4-1；P2 集中在 t1-1 表格、t5-1/t8-1 命名。

### US（8 claims）

| claim | 引用 locator | 判断 |
|---|---|---|
| t3-1 server products | paragraph:235 | 逐字支持 |
| t4-1 devices/Surface | paragraph:277 | 逐字支持 |
| t5-1 M365 Commercial 14%/15% | paragraph:699 | 逐字支持 |
| t6-1 M365 Consumer 11%/11% | paragraph:701 | 逐字支持 |
| t7-1 Server 23%/Azure 34% | paragraph:707 | 逐字支持；没有把 Azure 说成 23% |
| t8-1 fourth-quarter seasonality | paragraph:729 | 逐字支持 |
| t13-1 search/news $1.6B/13%/20% | paragraph:945 | 逐字支持 |
| t14-1 cash from operations $17.6B/$136.2B | paragraph:1081 | 逐字支持；仅写 fiscal year 2025，未写 June 30, 2025（P3 period 明确性） |

US 8 条 claim 的引用没有“引用存在但不支持”的句子；问题是 required facts 覆盖不足（见上表）。

## 3. 具体 P1 清单

### CN

- **CN-P1-1 缺 f-gan-power-stage**：source page18/paragraph:14 已有 “2022 年推出 PRISMO PD5 … 已交付客户进行生产验证，并取得重复订单”，summary 没有任何 PRISMO PD5/GaN 功率器件 claim。
- **CN-P1-2 缺 f-inp-development-started**：source page18/paragraph:29 已有 “于报告期内启动磷化铟（InP）材料体系专用 MOCVD 设备的开发 … 下半年将 … 尽早付运样机”，summary 没有 InP 开发/下半年计划 claim。
- **CN-P1-3 t2-1 “该新产品”未闭合**：claim 只有 “公司正进一步推进该新产品在 Micro-LED 市场的应用拓展与推广”，未给产品名；唯一 context 是标题 “（4）MOCVD 设备”，标题不能作为产品声明。B2 的指代闭合没有在这条 claim 体现。
- **CN-P1-4 t3-1 截断且带编辑标记**：claim 原文 “外延片生产的 MOCVD 设备早已 … 并在全球氮化镓基 LED MOCVD 设（原文截断）”；source span 在 “MOCVD 设” 处结束，“（原文截断）”不是源文本，句子不完整。
- **CN-P1-5 t4-1 从句中段开始**：claim 以 “到多个先进逻辑客户端进行验证” 开头，缺主语/前句；source span 同样从 “到多个…” 开始，作为独立 claim 不自洽。

### US

- **US-P1-1 缺 f-azure-is-consumption-based**：selected paragraph:233 有 “Azure revenue is mainly affected by infrastructure-as-a-service and platform-as-a-service consumption-based services”，summary 无此点。
- **US-P1-2 缺/部分 f-azure-inside-intelligent-cloud**：t5-1 有 Server products/cloud 与 Azure and other cloud services，但没有 Intelligent Cloud 段归属；required fact 要求三者同时保留。
- **US-P1-3 缺 f-three-segments**：selected paragraph:192 明确 “three segments: Productivity and Business Processes, Intelligent Cloud, and More Personal Computing”，summary 无。
- **US-P1-4 缺 f-segment-change-in-august-2024**：selected paragraph:193/732 有 2024 年 8 月分部重组及 M365 Commercial 并入 Productivity and Business Processes，summary 无。
- **US-P1-5 缺 f-rpo-scope-and-amount**：selected paragraph:3845 有 RPO $375B、commercial portion $368B、June 30, 2025，summary 无。
- **US-P1-6 缺 f-rpo-recognition-is-forward**：同段有 “expect to recognize approximately 40% … over the next 12 months”，summary 无；这是前瞻计划，不能省略。

## 4. P2 / P3

- **CN-P2-1 t1-1 表格结构**：t1-1 引用 page30/table0/row1-6，六个 span 都带 table_structure_ambiguous；合计数值 43.46/6.11/29.91 与 row6 对齐，但列结构/单位靠 context header 阅读，建议保留 needs_review，不应作为无保留的已证明表格事实。
- **CN-P2-2 t5-1/t8-1 命名不一致**：t5-1 用 “中微众硅”，t8-1 用 “众硅公司”；两处 source 各自逐字支持，但同一收购标的两套称谓会混淆主体，建议统一或加一句“即众硅公司/中微众硅”。
- **CN-P3-1 t11-1 源文本 typo**：source 是 “高深刻比”，claim 照抄；不是模型单位/数量错误，但建议在内容审查中标记源文本 typo，避免误读为“高深宽比”。
- **US-P3-1 t14-1 period 明确性**：claim 只写 fiscal year 2025，没有写 June 30, 2025；source 精确，period 语义可由 10-K 推断，但不满足最严格的 period 自我说明。
- **US-P3-2 summary 选择偏差**：8 条 claim 主要是 server/device/M365/季节/搜索/现金流；required 的 segment、RPO、Azure consumption 等未进入 claim，说明 claim 选择优先级没有覆盖 required facts；不是引用错误，而是覆盖策略问题。

## 5. 数字、单位、期间、语言与投资结论

- **CN 数字/单位**：t1-1 43.46/6.11/29.91 亿元；t6-1 1659 亿美元/23.2%；t9-1 50 多/30%/60%/70%；t10-1 20.41 亿元/5.50 亿元/36.86%/30.51%；t15-1 2023 年底；t16-1 8 寸；t18-1 14 万平方米/2023 年 7 月；t19-1 60 比 1。均与原文一致，未发现换算/单位改写。
- **US 数字/单位**：14%/15%、11%/11%、23%/34%、$1.6B/13%/20%、$17.6B/$136.2B；均与原文一致；没有把 Azure 34% 写成 23%，没有把 RPO 375B 写成 7265 亿。
- **期间/模态**：CN t9-1 保留 “未来五年将”（plan）；t20-1 用 uncertain；t2-1 planned；t6-1 forecast；US t14-1 fiscal year 2025；未见把 plan 写成 actual 的明显错误。
- **语言**：CN draft language=zh，claims 中文/产品英文名；US language=en；summary.translate=false；未发现整句翻译或中英混杂（产品名/缩写除外）。
- **投资结论**：CN/US 均无评级、目标价、估值、买卖建议；CN t9-1 “成为全球领先的高端设备平台型公司” 是公司愿景，不是投资结论。

## 6. 实际打开的原文 span / gold

CN 关键 span（locator + 原文）：
- page18/paragraph:14 — “于2022 年推出了用于氮化镓功率器件生产应用的MOCVD 设备PRISMO PD5，目前已交付客户进行生产验证，并取得了重复订单。”（f-gan 缺失证据）
- page18/paragraph:29 — “于报告期内启动磷化铟（InP）材料体系专用MOCVD 设备的开发，实验室已取得良好进展。下半年将结合客户反馈意见，加快产品开发，尽早付运样机至客户端开展生产验证。”（f-inp 缺失证据）
- page18/paragraph:9 — “同时，公司正进一步推进该新产品在Micro-LED 市场的应用拓展与推广。”（t2-1；前文未选）
- page11/paragraph:4 — “外延片生产的MOCVD 设备早已在客户生产线上投入量产，并在全球氮化镓基LED MOCVD 设”（t3-1 截断）
- page17/paragraph:4 — “到多个先进逻辑客户端进行验证，已顺利通过客户现场验证。”（t4-1 片段）
- page30/table0/row6 + page28 header — “合计 | / | 43.46 | 6.11 | 29.91 …”；header “预计总投资规模/本期投入金额/累计投入金额”，unit “单位：亿元”（t1-1）
- page177/paragraph:9 — “中微众硅为国内少数…CMP…”，page13/paragraph:4 — “完成对众硅公司控股权的收购…”（t5-1/t8-1 命名）
- 其余 CN claim 引用见第 2 节表。

US 关键 span：
- paragraph:233 — “Azure revenue is mainly affected by infrastructure-as-a-service and platform-as-a-service consumption-based services.”（f-azure-consumption 缺失）
- paragraph:192 — “We operate our business … using three segments: Productivity and Business Processes, Intelligent Cloud, and More Personal Computing.”（f-three-segments 缺失）
- paragraph:193 / 732 — “In August 2024, we announced changes to the composition of our segments … bringing the commercial components of Microsoft 365 together in the Productivity and Business Processes segment.”（f-segment-change 缺失）
- paragraph:3845 — “Revenue allocated to remaining performance obligations … was $ 375 billion as of June 30, 2025, of which $ 368 billion is related to the commercial portion … We expect to recognize approximately 40 % … over the next 12 months.”（f-rpo 两项缺失）
- paragraph:699/701/707 — M365 Commercial 14%/15%、Consumer 11%/11%、Server 23%/Azure 34%，分别对应 t5-1/t6-1/t7-1。
- paragraph:235/277/729/945/1081 — t3-1/t4-1/t8-1/t13-1/t14-1，逐字支持。

Gold：tools/document_understanding_benchmark/gold/cn-h1.json 与 us-10k.json；required business fact ids 与 critical ids 取 .planning/shared-reading-production/du11/metadata-registered-source-facts-20261017.json 的 sample 元数据。

## 7. 无法验证 / 边界

1. 未重新解析原始 PDF/HTML 完整内容；判断基于收据中的 96 个 evidence span 与 gold/meta；CN 表格结构、页边界未用版面图像复核。
2. 未重新调用 MiMo/MiniMax，无法判断模型是否还能在这些 prompt 下生成更多 claims；本报告只审已成稿的 summary。
3. 请求给出的 docs/plans/.../live-... 路径不存在；本报告使用实际 .planning/... 收据；若另有一份同名 docs/plans 收据，本报告未覆盖。
4. 未独立重算 CN/US 原始文件 SHA；使用 receipt 的 source_sha256 与 gold 的 source_sha256 对齐。
5. 未审查正式 C 的工程恢复/缓存/FF-RF 消费；这是内容审查。
6. 未判断 claim 生成上限是否参与 US 只有 8 条；从数据看 US 8<20，但未审 prompt/schema 上限实现。
7. 未验证 CN 593 / US 305 deferred 的 underlying selection 细节；required facts 的 evidence 已被选中，主要问题是 summary 漏写，不是不可读。

## 8. 结论摘要

- CN：required 8/10，critical 5/7；P1×5。内容可用性不足以 CONTENT_PASS；建议补 GAN/InP 两条 claim、闭合 t2-1 产品名、修复 t3-1/t4-1 截断或删除，再复审 t1-1 表格与 t5/t8 命名。
- US：required 2/8（partial 1），critical 2/8；P1×6。8 条 claim 引用都成立，但摘要没有覆盖分部、RPO、Azure consumption/Intelligent Cloud 等 required 关键事实；内容覆盖严重不足，不能 CONTENT_PASS。
- 二者均未发现投资结论/评级/目标价/估值；语言与数字未发现明显错误。

## 附录：审查输入

- CN receipt/overall：.planning/shared-reading-production/du11/live-cn-h1-b2v3i-20261018/receipt.json、overall.json、rf-narrative.stdout.json。
- US receipt/overall：.planning/shared-reading-production/du11/live-us-10k-b2v3-20261018/receipt.json、overall.json、rf-narrative.stdout.json。
- CN claims：20；US claims：8；evidence spans：96/96。
- CN model：mimo-v2.6-flash；US model：MiniMax-M3；prompt_version reading-source-scoped/4.0.1。
- Receipt：CN 15,394 tokens / $0.002783；US 18,093 tokens / $0.007782；1 POST；activation_recovery PASS；cross_run_zero_POST=true。
- 本报告只读生成；未修改源码/测试/配置/gold，未执行 git 写操作，未调用供应商。
