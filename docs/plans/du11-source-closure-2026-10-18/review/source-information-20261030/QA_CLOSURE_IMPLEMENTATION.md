# Q1–Q3：问答的闭合来源范围（下一实施节点）

基线：`69c9b178`，精确CI40984342776 success。本文件是实施细则，不是实现验收。总loop active；未知制造参数继续unresolved/可读，不因此授qualified。ROOT负责下列源码；W21的runtime/worker/environment三个owner完全不进入本范围。

## 已复现及完成标准

公共选择链已冻结3RED/1PASS，见q-scope-baseline：财务与感谢在两种顺序下均借同答复的业务事实入选；两个自足业务回答合成一个support。后置否定目前随整个答复被保护，这个正控必须保留。独立只读探针还穿透到实际summary task，证实夹带会进入source card，不只是展示问题。

完成要求：同一问答保留父关系，闭合业务断言各有自身support与必要context；常规财务结果/致谢不得借别段业务资格获得独立摘要任务，也不得作为无必要成员反复付prompt成本。问句保持context，原文及原ID/locator可展开。未知范围诚实partial/deferred，不裁小后变complete。不以提高额度、加入公司词典或删除负例验收。

## 接线顺序与责任

1. 在`narrative_reading._candidates`中，现有`SourceOperatingSession`建立之后、任何按package index登记reference/deferred/extra_context之前，调用一次QA闭包服务。此时原packages与budget_packages一起同序重建，非QA逐项原样，不能一份拆另一份未拆。QA没有carrier不等于免除原范围/成员核对。
2. 闭包服务只消费已经观察的原始成员、canonical QA/来源顺序及同一WorkBudget；不读PDF、不选backend、不下载、不调用LLM、不建第二store。成员上限、截断、缺成员/错来源/错记录都沿用实际状态，不把排序相邻当邻接证明。
3. 先固定`support original IDs + meaning-dependent context original IDs + completeness`再做来源assessment。每个新scope使用独立immutable analysis owner，复用现有group/maps/_original_refs；不覆盖原unit owner。纯问题/model context不能捐actor或谓词。相同support但含义context不同不能共用prepared事实缓存；禁止先fact再改该owner的contexts。
4. 复用`reference_closure`与现有限制/模态/对象匹配。现有`build_antecedent_windows`没有QA record边界，PDF表格fragment也可能没有paragraph_index，不能仅把qa_exchange加到_REFERENCE_KINDS。应提供受当前QA范围证明的有界answer predecessors，明确哪里是已读边界、哪里是未检查/截断。
5. `local_qualification_dependencies`的`source_body_adjacency`是物理证明，不能用“同QA”伪造。将其中限制对象/模态的语义matcher抽到同session私有方法，旧physical入口保留原验证；新QA序列只能在自身来源/记录/顺序得到证明后调用该matcher。不全局放宽physical检查。
6. 由闭合结果同时生成package的members/anchors/required、citation支持视图和实际prompt材料。必要问题、主体指代、基期/单位、因果两端及后置限制保留；不做`[[uid], ...]`无条件拆分。一个QA父关系可以包含多个闭合范围，纯展示用完整原文不等于每张卡都发全部原文。
7. 旧unit/source/raw ID及relation wire不改变；新行为必须进入现有decision inventory/recipe依赖，不能误命中旧summary cache。继续同一预算/lease/outbox恢复机制，不新增审批、许可或canary。

## 必须先写的测试包

| 输入/变体 | 应验证的不变量 |
|---|---|
| JSON和物理PDF同义业务＋财务＋致谢，交换顺序 | 业务保留，财务/致谢无捐赠；package/citation/source-card成员一致 |
| 同QA两个自足业务，中间财务 | 两个可独立支持范围，问题context仍在；成本不再包含全部答复 |
| 已交付，后片尚未认证/不代表批量收入 | 不出现遗漏限制的较小positive支持范围 |
| 该系列/上述产品、跨片主体 | 明确前件才闭合；歧义、缺前件及另一记录不借用 |
| 收入下降，下一片“这一变化主要由于需求减少” | 因果两端/基期保留，单纯会计结果不能变驱动 |
| 完整业务后独立财务，与未结束半句后财务样片 | 前者可分，后者不能凭终止符臆造自足断言 |
| 问句有业务关键词但答复只有财务/套话 | 不授support；问题不当管理层事实 |
| 不同原件/QA记录/角色/不连续fragment | 不借支持、归属或限定，不伪造物理adjacency |
| 同support不同meaning context与缓存重复读取 | 事实隔离，重复读取零新增语义扫描，不因改contexts复用旧缓存 |
| 中途预算耗尽、窗口/成员上限、partial QA | 已确认保留，剩余deferred/partial，不虚报complete或释放旧未知费用 |

测试既要看候选，又要经实际summary task/source card检查support/context和发送成本；仅span数或原文包含不算通过。先运行最小ROOT短包，稳定后一次受影响领域＋独立终审，不增加逐小步骤签收。真实复验使用已有保存parsed；只有确定物理来源不足才与runtime单一owner协调重读，不能再次盲跑整批。

## 验收及后续

ROOT关闭独审发现的共同根因，最终源码SHA＋领域测试＋真实保存parsed差分一起留证。正式原语言摘要、费用预留前的实际task内容检查、激活/重启/跨run缓存、FF复用和RF模型实际采用分别留真实证据；本节点不能替它们签通过。九目审核中止、US RPO、W21接收及未曝光holdout/公司八步循环继续在母计划中保留。
