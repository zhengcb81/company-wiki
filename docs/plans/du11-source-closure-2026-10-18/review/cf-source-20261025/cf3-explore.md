# CF3：共享理解与候选工作量独立调查（2026-10-25）

唯一计划：`du11-source-closure-2026-10-18`。状态：调查完成，未实施产品代码，不代表真实IPO验收通过。

## 1. 结论与真实边界

真实中微招股书429页、14,025 units的冻结结果仍是：parse420,052；understand_units11,473,800；candidates4,091,862；单16M账户最终15,999,740并耗尽、0span。未再次跑原样真实失败，未提高或拆分预算。这里的比例是逻辑工作量，不能当CPU或耗时占比。

已证明三类共享关系算法会在本可排除的负例上产生二次工作量。ROOT可先在同一owner按TDD修复这些明确冗余，再决定是否需要更深的增量流水线重构。不能宣称三项synthetic节省就已解释真实IPO的全部5.43M reserve。

## 2. 准确调用路径与现有复用

`select_reading_evidence → _understand → pipeline.understand_units → build_observation / apply_layout_hints / NativeSourceContext / build_structure / bind_reading_plan / dependency packages → _candidates → _prose_reading_packages → SourceOperatingSession.reference / local_qualification_dependencies / local_operating_context_dependencies → priority-ordered fact/admission loop → finalize_selection`。

结构builder的`WorkPlan.stage`9阶段合计44次线性unit/text-block pass和10次N×bit_length(N)排序预留。用N14,025与64字符块B14,266重构：`44×(14025+14266)+10×14025×14=3,208,304`，与真实账本逐单位一致。这不是“可以删掉3.2M计费”的证据；必须先减少实际pass/排序后再相应计费。

`SourceOperatingSession`已有按owner的relations/facts/financial缓存；底层`OperatingRelationSession`已有unit、normalized text、offset/name view、(unit,context tuple)结果、(target,predecessor tuple,complete)引用缓存。中性实测同一fact首次6,299work，重复fact和financial均0；不能再加一层同义缓存冒充修复。不同target共享同一predecessor仍各付98，说明原始声明观察可在同session进一步复用，但目标归属/歧义与边界仍须逐目标判断。

## 3. 三个可复现中性负例

| 输入规模N | 单列N页（全0关系） | 同DOM父级单语（全0关系） | 同页两列长度N与N+1且同语（全0关系） |
|---:|---:|---:|---:|
|64|4,096|2,016|4,163|
|128|16,384|8,128|16,515|
|256|65,536|32,640|65,795|
|512|262,144|130,816|262,659|

- `structure/relations.py::language_lane_relations`：每一页又扫描整份`by_page_lane`键；单列页根本无跨列可比对象仍精确N²。一次建立page→lanes索引后只访问本页。
- `_pair_lanes(allow_self=True)`：同DOM父级预留n(n−1)/2组合，再发现所有语言相同。先按已观察语言家族排除不可能配对；不得把语言不同直接当成配对正证。
- `_pair_by_nearest`：不等长两列先预留L×R，即使语言都相同且缺几何。先排除确定不可能的家族，再保留原有最近邻、24阈值、kind、原次序tie与confidence语义。

精确计费点、调用次数和二级reserve caller已经在中性JSON中记录。中性完整PDF64/128/256/512 units的理解work为23,083/47,108/96,440/197,672，完整选择355,546/712,065/1,426,381/2,857,581；本例近线性，但新owner每个可能谓词clause仍会跑32个事件语法，之后20个业务识别逻辑pass。此处0span无内容gold，不做召回率结论。

## 4. 真实reserve5,429,520的证据上限

只读验证`profile_ipo.py`SHA与冻结收据相等；该脚本只保存直接charge frame的filename/function/line，并跳过最多4层charge转发。它没有保留`reserve`的上一级caller或每次调用参数。旧`cn-ipo.json`也不含parsed units/structure。

因此无法从旧报告逆推5,429,520中有多少来自哪一关系函数。不能伪造二级分摊，更不能为补账原样重跑14k失败。本次取样用中性小输入记录reserve的直接调用者；真实分摊只能在共享owner有实质改动后的验收回放中同时记录（root账本唯一计数、固定深度，拒绝请求另记，不重复累计嵌套阶段）。

## 5. 已完成合法工作如何处理：已有正例，不能重做成新功能

23-unit中性HTML有独立业务段，后接20条行政内容：16M基线消耗66,121，选2span；20k/30k/50k上限耗尽仍保留相同2span、status=partial，未知尾部逐包withheld。10k时尚未完成合法包，0span、needs_review。这证明后期候选保全已存在。

IPO失败更早：全源reference、qualification和local-context扫描在首张priority候选形成前执行，耗尽于`local_operating_context_dependencies`。先减上述真实冗余；若仍不够，再将处理按“来源已证明的独立闭合依赖范围”分段，而非任意按页截断。一个包只有主体、引用、修饰、否定/计划限制及原始unit envelope全部完成才可提交。未知同scope后缀可能改变限制时必须withhold；不同已证明scope的合法结果可partial保留。不得耗尽后继续扫描，不发明第二budget/store/state machine。

## 6. ROOT最小实施建议与中性RED

1. 先修三项结构负例：固定关系输出与排序，对N倍增负例约束近线性；用混合语言、缺失语言、相同距离tie、跨source/page、真实geometry对照，保证精确原关系不变。
2. 后续如需优化32语法扫描，应从现有谓词grammar派生保守家族dispatch，缓存immutable normalized lexical observation；无法证明必要条件时退回全语法，不能靠company/market字符串或“未匹配”伪造absence。20业务pass现已受owner缓存包围，需先证明内部重复观察再重构。
3. 若引入声明观察复用，只以同一原始unit身份缓存解析观察；仍逐目标判断窗口complete、family compatibility、多个候选歧义、最近原声明和原字节offset。相同文本不同source不合并。
4. 固化“独立早段+晚尾耗尽保留partial”正例及“同scope限制尾未读拒绝裸计划”负例。结构中断已有closed-stage state；不得把它当整源complete，也不应直接丢弃已验证独立包。
5. 有意义的owner改动与中性门通过后，才对冻结IPO原件做新attempt，parse+select仍同16M/112cap。无正式内容gold保持NOT_GRADED。计费改善、实际task语义、正式摘要与缓存恢复分别验收。

## 7. 执行边界与错误留证

本agent无产品源码/测试/config修改，无production catalog打开、无原件读取/副本、无下载/网络/API、无跨仓写。仅写分配的scratch与本报告。未创建临时目录，所有持久文件均为命名证据。探针没有全局hook；root Budget子类计量而已。

最初synthetic parser_version误写cf3-1，EvidenceSpan正确拒绝；原失败JSON保留，修为1.0.0后重跑，所有工作量结果不变。一次Windows rg路径通配符错误与一次过宽历史JSON搜索已留notes；后改具体路径/filename-only查询，无重复原件处理。

完整机器接口、SHA、计量、局限见同名JSON；scratch证据在`.planning/cf-source-20261025/cf3-explore/`，未复制产品源码或原件。
