# R6 来源语义 R4 — 未知目标、范围声明与事实证明分轴

**FROZEN_READY_ROOT_INDEPENDENT_REVIEW**。基线`a6841e9`独审有P2，未签PASS；旧R3报告/独审/失败证据保留。本线代码在隔离`tmp/architecture-r2`冻结，未改Git/index、主工区src、主PWF、原件、配置、模型资源或生产库。ROOT负责独审、完整候选CI与并线，本报告不代替C验收。

## 根因与修复

前轮把POS识别出的未知NP默认为specific，再把`roles.operating`当payload：营销词替换后，raw payload=None也会变fact eligible/relevant。额外旁路是closed catalogue只因有两个未知NP就升级True；`business_scope`标签也有这种来源。financial exemption集合、描述范围和独立payload被混为一个bool。

本轮删除`_argument_relevance`的default-specific和promotional词补丁。有效原话、source scope和fact view分别保留；未知generic function/goal无原owner正向argument proof就是unresolved且relevant=False，raw None不改False，原话仍完整可检索。不添加公司、行业、新营销词或token额度。

- 原argument owner的正向语义供goal直接NP复用，POS仅负责matrix/NP/relative绑定；受益者背景不能捐proof。原quantified operating goal仍由原metric角色observer保留unresolved原话，不制造当前数量。
- `SourceAssertionRoles.source_scope`是内部资料范围/用途声明；`SourceClauseContext.fact_candidate`独立约束fact投影。typed offering+closed catalogue/经营流程范围、customer-facing范围、有限use/provision/scheduling关系可保source描述，**不强设independent_payload、不造milestone、不自动财务豁免**。若仅该scope，material band为description；comes-in-several-editions仍是description。
- qualitative coverage在既有composition/function owner绑定offering主体、局部谓词及通用process/workflow/operation/工序/流程/作业、经营或市场范围。原“生产服务覆盖下游工序”及跨语言变形保留；财务覆盖、纯指南、跨句借范围和未知愿景反控保留。不是给一句工序或某行业开例外。
- catalogue member身份/数目不再升级strong payload。已知offering class可保source_scope；未知成员列表仍unknown。并列成员、顺序、完整原文不改。
- `_ReadingRelationObservation`明确`payload_reasons / scope_reasons / unknown_reasons`，callback、payload投影和source scope复用同一规范clause缓存。qualitative plan/reporting basis不是strong payload；metric实际观察到的planned measure与纯plan label分开；仅名单推断的business_scope标签不自证相关。`operating_mechanism`只由真实positive payload追加，不能由operating语法角色推出。
- compat `source_narrative_relevance`已有roles时不能再用legacy eligible/reason覆盖其未知态；有独立payload、source_scope或原数字角色才相关。没有新增人工许可/身份/签收。
- 原cover-X-with-Y application标记复用、asset头治理NP末尾、因果source描述绑定仍须matrix。catalogue copula遇到被动/状态predicate不再当名词列表，其EN有限head匹配在同clause memo复用。语言歧义goal不能免费获relevance；缺资源/超界仍原deferred/partial。

## 已授权纠正的测试假设

ROOT明确确认：本线R2/R3自增的部分正例仅由POS产生，原support期待过强。neonatal wards、rare diseases、surgical services以及未知经营目标，改测unresolved/irrelevant、完整原文、顺序不影响未知态和no fact；不把unknown改False。portable compressors新例原先要求positive也是错误假设，现保留None和原话。orchard planting/coastal transport未知列表不能因两个NP相互证明。

这些案例没有删除：两条goal和一条未知列表从宽泛positive参数集移到明确unknown测试，数量保留；原CI20及真实native60的oracle未改。已绑定function、quantity、coverage、causal、billing、raw customer/source scope等正例保留。R2的use-location例因新增显式source_scope可作为description展示，但仍None/no fact。精确before/after函数与文本在JSON和独立erratum文档，不能将旧版PASS回写成新规范通过。

## 真实验证与失败历史

- 最小真实8例：**4F/4P，23.36s**；新增语义21：**12F/9P，12.49s**，之后逐步闭环。
- 首次旧域收口仍**10F/340P，27.29s**，揭示source_scope须进入compat角色及actual use/provision/scheduling/basis的责任遗漏；保留该失败记录。随后定点恢复先112P/1F，最后有限计划原限定描述闭环。
- 当前领域组：**290P/0F/0E，8.65s**，含新预算precharge/false memo/生产入口同账户/partial不缓存角色、已修正假设、cause与admission反控。
- 当前旧失败恢复、原20相关完整目标、真实native60、未知actual action、R4公开selector、R5真实handler wire、runtime：**280P/0F/0E，26.25s**。未改旧oracle，未重跑433/262/全仓。
- 最后发现compat passage有显式account却没传给prepared scope，单项**1F，7.48s**；仅补透传一行后，argument完整**37P，7.00s**。这行仅影响未提供prepared scope的compat路径，生产prepared路径行为不变；不以这37例冒称重跑全部前组。
- closed-list事前真实probe已留rawTrue/factTrue/supportTrue；其三条正式断言是在修复后补入，执行为3P。artifact名`r6-r4-list-red.xml`误含red，JSON明确它是regression-green，**不冒称做过断言RED**。
- Ruff、8源mypy、diff check绿。完整命令对应目标、JUnit与log字节SHA、各阶段失败ID见JSON/工区tmp。

## 预算与部署身份

原19n基础预留、16M总界、112槽、4096 chars/1024 tokens均不变。新增scope观察按**实际Σtargetchars×8+1**在工作前预扣，真假结果均缓存，重叠目标也计实际长度；directed provision按实际subject/target字符预扣两次扫描；goal NP callback同样预扣8n，POS仍32n+1。生产Session.fact和直接assessment两入口都传同一个WorkBudget，compat passage的显式账户也不丢失；budget=None仅保纯兼容调用。资源耗尽沿原unassessed/deferred传播，未返回的半份roles不缓存成完整。

这些logical work系数不是CPU指令等价，真实H1成本/召回/耗时仍要在原16M/112验；不能根据单元秒数保证无退化。实际PDF/非PDF reading_recipe闭包均包含8个相关owner，SHA见JSON；grammar4、passage10，资源字节与版本未改，无运行时下载或收费API。

## 明确能力边界与下一步

目前POS不能判断所有陌生目标的经济语义。真正业务目标但原owner尚未认识的，也会保原文而不自动进入positive业务选材；这项能力缺口不能用default-specific或行业词补丁掩盖。普通未知actual action可读原话，也不因此成为typed issuer/event/number事实。下一步仅ROOT独审→完整候选CI→真实H1/摘要、缓存恢复、RF采用C节点；T3仍暂停。不宣称整个PWF完成。

## 冻结身份

| 隔离工区相对路径 | SHA-256 |
|---|---|
| `src/company_wiki/document_understanding/statement_grammar/__init__.py` | `23369e92e6f1f9d330a09fcdb3ff7d470ce4c1176c4cc7e7a984022141dfb9e8` |
| `src/company_wiki/document_understanding/statement_grammar/predicate_arguments.py` | `207e0250cbe2aa7269dc2f021444577e38264791008b2ae8a15d0f76fcea2251` |
| `src/company_wiki/document_understanding/operating_states/assertion_roles.py` | `bf0bec525b83ff70444b0126ba3807b7d7f1781145d712309f5caab78b589fda` |
| `src/company_wiki/source_catalog/narrative_source_context.py` | `2b223273b56e1e6e55ff7e96bd8f6d57f4bc064c205d6e231606df9c83068038` |
| `src/company_wiki/source_catalog/narrative_source_passage.py` | `83c86a62e721e9ddc53b66cf16cbb9b3677fc35dc7e9df7b6b8f07d2a2e7ab4c` |
| `src/company_wiki/source_catalog/narrative_business_policy.py` | `a63e1a1ad5902e0c5e2ebef23898c88d3c332ced37f28ad05b3416d8560df808` |
| `src/company_wiki/source_catalog/narrative_support_use.py` | `d9632c14e7dda839ddbad0c98997ca4014b031aa4c25c17f78a191f2b11a3b35` |
| `src/company_wiki/source_catalog/narrative_operating_relations.py` | `865a6eaa12a880c54b85b134de5e92f1b0ab9e9c2215381e4f67bcdd1c33e230` |
| `tests/unit/du11_production/test_source_preparation_axes.py` | `71a5a16dc77f165bf655eaf6bdcc696d965edd62eadd9d6ae7b26b02784a07bc` |
| `tests/unit/du11_production/test_source_semantic_axes.py` | `594cc8347e090ab888980ebd87fd1d87b6b6dd971672d5ef9b3f24ad1d27c1be` |
| `tests/unit/du11_production/test_source_argument_semantics.py` | `e09a3f0189790bb3b54af2e84c722a489e4c928dc14c43a9c098fb22bd6d541e` |

报告及JSON由ROOT接收后STOP；未执行Git提交/推送，未影响其他作者工具/docs路径。
