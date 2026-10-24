# W08 跨页结构接续建议（只读）

结论：现有设计方向成立。下一节点应修“物理相邻证据与列表作用域没有在结构阶段接通”，不应放宽未完句规则或在选片后补业务父标题。此报告没有运行探针/测试/实文档，没有修改源码、作者工区或母PWF。

## 当前可用入口和责任

给定 `NEXT_IMPLEMENTATION.md` 在工区和母仓所指路径均不存在，是过期指针；ROOT已确认无需等待。实际设计入口为：

`C:/Users/郑曾波/Projects/company-wiki-r1-local-observation/docs/plans/r1-final3-source-semantics-20261022/resume/cross-page-ancestry-design/design.md`，同目录 `design.json` / `probes.json`。

已先用该工区 CodeGraph 查 context/node/callers，随后只读已定位源码。真实依赖为 `pipeline.understand_units → structure.build_structure → _build_structure → sections.build_sections → _native_numbered_list_scopes`；晚期 `narrative_reading._prose_reading_packages → build_native_continuity` 又消费已完成的sections。必须保持这个单向顺序。

确认的共因：列表成员硬要求同一page；已识别页眉页脚在作用域恢复之后才跳过；现page_edge把物理观察与未完句/independent_start/最终scope混在一起；结构薄ObservationUnit没有足够native字体/坐标/原始block依据；Roman子项尚未进入同一上下文语法。

## 最小一致接口

1. **在现native owner里抽出纯物理观察与邻接判定**，可继续放 `narrative_continuity.py`，目前它不导入structure。输入借用已观测unit、原始provenance、coverage、已证明furniture、同一WorkBudget；输出仅原始左右ID/页/序号、frame/font/lane和被跳过furniture ID。无section/profile、独立开句callback、业务名或重建文本。这样sections可单向使用它，不反向调用晚期continuity。
2. `_Analysis.native`/page_edge作为原句子客户端，继续叠加heading排除、最终scope相同、未完句和independent_start否决；**完整左句的旧negative必须仍无sentence window**。新列表客户端以“已开启的编号引言＋缩进子项”证明逻辑关系，不能靠删句号/伪造scope调用旧page_edge。
3. pipeline在layout观察齐备后、build_structure前，一次性预扣并借用原始provenance索引；通过可选只读call-local context传给build_structure/build_sections。旧直接调用无context仍只有原same-page能力，缺依据不能变正例；不要扩SourceExport/du-input持久schema，不建第二缓存/任务库。
4. sections保留自己的section_id/parent_id。先跳过**已证明**furniture再决定是否关闭native列表；换source/真实heading/sibling/未知中间正文立即止步。每个跨页边必须为相邻物理页，且全scope仍受原2页/24units上界；不能每条边重置为一个无限滚动窗口。Roman `i./ii.` 只在已证明的本地列表上下文识别，不全局提升为heading。
5. **接线必须覆盖原始依赖出口**：basis字符串本身不足以传递边界证据。把所需引言/祖先/边界原始ID接到既有required-context/source-original闭包；逐目标处理，不能把整段/整个项目包所有列表正文变成atomic。proof引用可以是调用局部依据，不可另存一套权威父子映射或冒用continuation关系为新的事实语义。

家具的物理跳过证明与事实语义必须分开：保留其proof引用并计真实检查工作；不要把页眉页脚当业务正文/事实支撑。若本实现确实需要某个原始witness才能声明父子关系，其原始依赖成本必须进入联合envelope；不能因为它不可选就忽略成本。这个传输口须由下面公共测试冻结，不能只证明sections字典变好。

## 8个已有探针怎么变成TDD

| 探针 | 下一步 |
|---|---|
| same-page引言＋2完整bullet＋sibling | 保留现正控，父亲和sibling均不能串支 |
| adjacent-page第2完整bullet | 先公共structure＋select/model-view RED，要求自己的原parent/intro到达context |
| 同上＋已证明footer/header | 同一RED，家具不关闭scope，也不成为业务事实 |
| 下一页Roman子项 | 同一RED；另加**same-page Roman**隔离语法根因，不能靠跨页用例混淆两种缺陷 |
| 原未完句跨页、page-local paragraph/block重置 | 旧正控原断言不改 |
| 上项＋已证明2家具/global ordinal gap | 旧正控原断言不改 |
| 完整左句→完整右句 | 旧sentence负控原断言不改，列表正例也不能产生句子合并 |
| column=None | 负控保持无证明及现诊断；None==None不是可信跨页lane |

新公共RED不得注入最终sections/parent map、patch _understand或假pipeline。复用 `test_reading_native_continuity.py` 的native source fixture/真实_understand链，最终调用 `select_reading_evidence` 并核citation_views：support仍为实际子项、parent/intro仅context、原ID/locator/text不变、sibling不进来。现 `test_reading_named_segment_scope.py` 中注入sections的用例是下游回归控制，**不能**拿它证明本次结构发现已修。

## 三个施工阶段、一个审查节点

**A：冻结RED与抽共用物理层。** 先上述3跨页RED＋same-page Roman；提取共同观察，不改原句子语义。保持 `test_reading_native_continuity.py`、`test_native_prose_continuity.py` 原断言。加小矩阵：source/role不一致、frame/font/rotation不符、未知/离散column、coverage缺失/页deferred、序号断裂、未证明家具、2页→越界。

**B：早期结构接线＋最终公共依赖。** 索引只建一次且预扣WorkBudget；列表own-parent闭合再生成reading_plan/packages。保持same-page/unsplit、unindented/inline/non-colon/table/DOM/TOC、真实sibling关闭、missing/cycle/foreign-parent旧控制。页面邻近和业务词相似均不能代替语法/原始物理边。

**C：一次集中验收。** 在公共citation路径核联合originals恰8/超9、blocks恰4/超5、chars恰2048/超2049；每例隔离唯一超限，不让block先挡掉char；carrier按original_members计费。96spans/48k及16M不升，0/紧WorkBudget先拒绝分配/展开并给实际阶段诊断。复用shared_work_budget、structure_shared_work_budget、reading_budget_scale、native_carriers及既有scope_controls。一个独立当前字节审查后，才在ROOT已计划的年报回放中记录小范围边界projection，不另读原件。

真实D&M载体已有5originals，加2 broad祖先和Chemistry已达8；额外引言/witness可能确实超限。不能承诺跨页结构修好就一定能完整入选，更不能拆句绕限。无充分依据时保持祖先unknown；若字段必须有该父上下文才可引用，则延期该citation并保留诊断。独立完整事实可保留为unknown scope，不能假装祖先完整。

本报告源码SHA及8探针角色详见同名JSON。当前narrative_reading已与原design历史SHA不同，这是ROOT后续step3进展；本文未以旧探针冒签新源码运行结果。
