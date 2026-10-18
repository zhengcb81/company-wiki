# 正式摘要与付费恢复的共因改造 — ROOT实施细则

状态：ENGINEERING_IMPLEMENTED_AND_REVIEWED / REAL_C_PENDING。主计划仍为 document-understanding-2026-10-13；不是新审批链。优先于下一次真实供应商调用。两条RF/FF作者树继续独占，不改它们、Dayu、IQS或真实原件/config。ROOT独占CWP接线、最终独审、合主线与发布。

## 已证实的问题与取舍

最终源选材10/10不等于摘要保留10/10。MiMo实际64tasks→22clauses/19tasks，1264/8192输出tokens，不是截断；v4总20上限拒绝整份，移除该上限仍有合法ID串错产品参数、跨task否定、重复及关键业务遗漏。费用14819tokens/2681microUSD已入原母账，不重发、不修引用、不裁22成20冒称通过。完整证据/源SHA见du11_model_capacity_root_cause.md/json。

采用**源摘录优先的业务卡＋模型排序/有限disposition**。程序从现有完整source任务和support/context组装原语言卡，LLM不再自由改写canonical产品/数字/状态。容量足时保留全部已admitted且闭合安全卡；模型不能用稀疏遗漏删除它们，排序失败有诊断。缺项=unprocessed，缺context/字节不足=显式deferred，不能写成全部完成。原96证据仍可读。

新内部projection/请求/decoder采用独立版本（建议reading-model-input/5），旧v4二十条及旧付费失败语义不改。公共SourceExport v2、SummaryClaim现字段和上下游职责不改，不创建第二summary store，不将无界业务卡塞进metadata。新卡的正文必须是现有source-owned完整原文/闭合断言范围，不能让模型任意摘子串把“尚未量产”变成“量产”，也不能附一个正确quote就允许错误改写。混合现状/计划、第三方/提问、歧义表格或指代不明按原责任层保留unknown/diagnostic，不要求人工签收。

真实离线容量：该CN64完整support卡按现身份/引用序列化43913bytes，ID-only模型响应容量样例395bytes，最长原文892chars。仅说明容量可行，不证明所有卡语义闭合。**实际summary64KiB、selection1MiB、bundle1280KiB、模型response128KiB、HTTP262144bytes、最终artifact预留2MiB是不同上限，全部保持**。不能只按2MiB算摘要，或因有64tasks强拆4个付费请求。先单次有限ID-only执行计划，真正放不下时按实际配置有限defer；未来分片仍须现AUTO调度，不在本轮造第二任务引擎。

## 施工责任与顺序

### A：先固定行为测试（一个集中节点）

1. 保存不含密钥的小型真实失败回放索引，原v4响应及费用保持FAIL；合成未见公司/数字再覆盖同根问题，不能只修中微。
2. 计划控制：64+任务、顺序换位、泛化风险/财务噪声、同事件重复、未知role、长闭合组、有限预算。每个任务有admitted/deferred/unsupported/unprocessed等明确处置。生产决策不读取gold、公司名、页号或此次task编号。
3. 事实控制：合法ID但错产品/数字/单位、别task否定、问句变陈述、计划变已实现、验证变量产、歧义列归属、缺主语。新模型不能写事实正文；程序只取已存在完整原文和真实引用，不能自动修错误ID/补主语/猜币种/填缺字段。
4. 兼容控制：v4仍旧行为；新协议单独标识。public claims/reader兼容且受64KiB与bundle限约束。不另加消费者人工receipt或门禁。

### B：源卡/模型边界与生产接线

- 既有summary_tasks继续唯一source inventory，扩一个有限source-card/执行视图；新模块负责确定性组装、实际canonical bytes预算、完整closure、处置与去重，不重解析语义、不复制整份PDF/MD。
- 新narrative_model_extractive（命名可按现结构）只向实际模型暴露原来源任务及有限排序/disposition schema，拒绝把free-form模型正文写canonical。模型身份/语言/数据源由程序确定。rank/disposition不等于事实认证。
- runtime有限dispatch接新版本；旧scoped/legacy入口语义保留。现summarize/generation链使用同一BudgetedCaller，实际model metadata如实保存。**无模型/0POST不能伪造completed+model metadata**：模型前可有临时计划和原证据；实际模型已返回但排序坏时可保留程序安全卡与真实response身份/needs_review诊断，不冒称生成式改写已验证。
- 查清现生产默认factory/请求入口，集中接线只在新请求采用新模式；已有run/显式v4不改写。必须测试真实默认路径，不能仅测试手工传新flag。模型名称、endpoint、purpose、8192、价格和累计预算沿实际配置。

### C：已付费完整响应耐久化与恢复

严格复用现LocalNarrativeObjectStore和同一个AUTO reservation/attempt/lease/generation/outbox。给现reservation增加有界typed response pin/receipt，不能把raw伪装visible narrative_bundle，也不能另建responsecache/任务库/账本。

顺序：预留原预算→HTTP完整body在限额内读完→原对象设施durable字节→原AUTO绑定请求/响应SHA及身份→外层envelope解码/usage settle→摘要解码→现artifact outbox→activation。outer body SHA与final content SHA分开。raw request headers/密钥不得入对象/提示/报告/提交。最终具体方法/字段在du11_paid_response_durability_design.md/json列出的现owner接口上实现。

同run恢复先查已有request/body/model/source/taskbinding一致的response pin，验真实字节后0POST重新解码；未知/截断/缺失/变更的原响应不能假恢复。费用原attempt只结算一次；旧worker可留下原付费证据，当前lease/generation才可发布结果，不能覆新结果。外部已计费但本地durable前崩溃不可凭空恢复，保留unknown＋禁止盲重发。旧v4只存prefix/hash的历史失败照旧不能冒称可恢复；改协议/输入不冒用旧reply。

### D：一次集中离线集成与独审

按现真实接口设计故障测试：完整返回前/后、envelope前、summary decode前、activation前、lease丢失、字节/请求/taskbinding/source篡改；核0新增POST/原usage一次/未知hold不删/成功peer不重做/对象空间计入限额。沿用现恢复套件，新增必要行为不重跑所有历史大矩阵。真实收费暂缓到此节点绿且独立agent审查全部问题修复、最终源码SHA对齐；无逐小步人审。

### E：配置供应商真实C与发布

在最终提交HEAD，沿唯一phase_c_runner扩新协议（不新造runner/计费器），只读挂载同三原件、同一usage.jsonl、MiMo→DeepSeek→MiniMax串行。先验实际默认接线和输入支持，再验canonical source cards的本地蕴含/完整主体单位状态、所有任务处置/关键业务覆盖。排序是模型辅助，不冒称自由改写质量。再核paid response decode恢复与activation恢复0POST、公共read、同/跨run同AUTO缓存、当前FF/RF只读消费，原件/config/gold/sentinel不改和owned test目录恢复。

旧测试集是开发回归，不叫盲holdout；完成后再按母计划的新公司/新文档验证。正常commit/push和精确CI结果入PWF；未达步骤记OPEN/NOT_REACHED，不靠修改gold、提高上限或隐藏失败让C变绿。

## 接收/并行边界

ROOT统筹新mode/source-card/production/runner；可把raw-response durability实现和专属测试交内部独立线，写入文件白名单后开始。两线不共享修改同文件，最终ROOT集中装配/独审。外包RF/FF源码与计划目录不写。独立review发现真正缺陷修复，但不扩无穷词形审查或人工许可链。三个大的验收节点为A行为RED、B/C工程集成、E真实C；每个小函数不签收。
