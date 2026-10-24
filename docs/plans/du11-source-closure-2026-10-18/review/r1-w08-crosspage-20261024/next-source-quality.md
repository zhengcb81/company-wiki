# 下一阶段：真实来源质量，而非扩大切片额度

唯一母入口为CURRENT_STATUS；沿用既有W08–W12责任，不建第二PWF总队列或任务库。

## 已证事实与验收口径

本次V2单次回放249页/5647units，1512候选、96spans/8518字符、同16M账用8630449；字符额度未满、工作未耗尽，aggregate budget_full不能证明每一项遗漏都因96限额。独立内容3pass/9partial/2missing。原14 gold不改，selected/citation/model真正采用与按SourceRef实读的fallback分开记录；不强求财务报表全文切片。V3有限工程绿不签全14、收费摘要或RF公司通过。

## 实施顺序（两大节点）

### 节点一：同一引擎内修上下文与选材

1. 从annual14/review.json固定真实反例：跨页Chemistry→D&M/TIDES、容量值与建设日期分离、集团新客户分母、收入指引及行业/贸易/监管前提；同时保留A01完整四业务分类及Others、A02持续/终止经营与重述口径、A14竞争风险；另保留研发引流与客户地域/比较期脚注/结算和集中度事实。用原ID/locator及真实几何/文字构造有界回归；可用中性名称验证同构，不在实现内写公司名、特定数字或页码。
2. 在现有selection/reading_context diagnostics保留已计算的逐项信息，补足有界逐目标trace；decision_inventory仍只负责family/facet策略与缓存依赖，不扩成原文内容库。逐项链为：候选形成→事实归类→语义/结构依赖→offer→admit/withhold→citation/model。记录原ID和具体原因，不保存整份PDF/MD、全部中间副本或第二状态库。缺证标unknown，不用aggregate budget_full猜根因。
3. 层级只由结构owner依据源本身编号/缩进/版面确定；DOM/原生结构/电话会沿用各自已有关系，不把PDF几何设为所有来源的前置条件；真实业务父级和局部定义/分母不能只在全局另一个task可见。时间、限制、指引条件复用既有事件/模态/经营关系owner，使完整含义进入相应task；跨主体、不同事件、独立新段落反控必须保留。
4. 无表头/单位/对象的裸财务数字不得仅因含数字成为可直接陈述的factual task。明确非业务财务表优先走按需原文/API；收入确认、RPO排程等对业务机制有用的描述仍可检索/作为具体预测的精确来源。不能把“可获取”写成“已读取/已采用”，也不能改14 gold掩盖缺口。
5. 根据实际trace改定额选择/原生carrier或既有batch安排；检查A09容量重复占位、A11集团新客户20%回退，原3pass不得因增加召回而丢失。先保留96/48000/16M与8/4/2048，按完整语义材料选取，不拆文规避限额、不简单抬上限。若真实任务无法容纳，使用现有有界batch/Worker及同一AUTO预算/lease/outbox恢复，不重建队列或重付unknown调用。
6. 先写正确反例再实现，开发只跑所属单元；本节点完成后一次完整相关自然包（明确包含du11_source_closure、du11_reference_readiness两整包及既有77/20/24、semantic_value、scope、多target相关范围）＋独立大节点正反例＋一次真实新版本选材，复用同一结果逐14检查。至少含既有CN跨页与US/电话会等已有异构材料，不因缺几何而伪造版面。不逐小步签收、不重复完整原件解析作演练。

### 节点二：正式采用与RF闭环

按实际模型配置、现10M tokens/USD20累计账及unknown执行正式原语言摘要；核source→selected→model→summary的实际采用、未被支持的数值不得输出。做同run/crossrun cache和付费后激活前恢复的必要新版本验收，原已证生命周期不重复收费凑记录。采用已发布W09研究桥和W10逐文档projection，形成真实12材料prepared/read/use矩阵，再跑W12原公司RF全流程及四路独审。只有该公司实际大问题修完，才依计划药明合联→Snowflake；不以本节点工程PASS重签旧final3 FAIL。

## 测试与清理

测试使用独立短Temp及已有只读SourceRef，恢复自己新增的文件/缓存，保留原件、旧sealed/history和所有费用。只保留有界必要收据；不生成全量PDF/MD备份，不清作者工区/Dayu/IQS，不创建权限JSON、canary或人工许可链。已证外部IR业务链接缺口仍OPEN，后续由既有获取工具处理，不强加收费provider。

## 下一节点先验证的既有投影接口（只读定位，尚未复现为生产缺陷）

实际链为narrative_reading → narrative_finalize → automation/narrative_select → summary_tasks → narrative_model_scoped。现有BudgetDiagnostic已带item_id/item_ids/locator/bundle_key/reason，finalize聚合时丢失具体关联；reading的withheld已有known_unit_ids/status，导出时压缩，_admitted=False直接continue，_context又把缺selected依赖统记SELECTION_BUDGET。优先保留这些已计算结果的有界投影，不重复语义分析或另起内容/状态库。

合同风险待公有端口反例验证：finalize已产生phase/dimension等diagnostics，而narrative_contracts._reading_context当前只接受code/count。先测NarrativeSelectResult.from_dict/to_dict及真实模型请求编译，未实际执行前不宣称已复现/已修复。沿用当前采样/字节上限和count/limited，未观察阶段写unknown；不把全量plan中的可见性当request-sent。

三组中性TDD纳入现有节点一：①两锚共享父级且一项有真实限制，足额/紧额输出各自完整采用或准确拒绝，邻近无关风险不强绑；②非业务裸数、缺前提指引、完整业务事实同场，语义拒绝/闭包延期/预算未选必须分开；③公有合同往返后编译两task只发送一个，明确selected/model-visible/request-sent/response-used及task本地context，不能借另一task全局可见补证。以上是同一大节点测试，不新增逐小节点审批。
