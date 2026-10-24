# 冻结9例：源证明与模型材料的预算责任（只读）

**结论：建议分层，保留原9期待和原8/4/2048语义材料上限，不新增“页眉页脚也占模型材料block”的门槛。** 未跑测试或产品；这不是跨页最终独审。

## 数学正确，度量必须分开

`cross_page_furniture`实际原ID联合如下（完整ID见json）：

|责任|原page/block|units|raw字符|
|---|---|---:|---:|
|模型语义：root|p1/b0|1|6|
|模型语义：parent＋intro|p1/b1|2|22|
|模型可读：前页body|p1/b2|1|15|
|模型语义：target|p2/b1|1|14|
|物理证明：footer|p1/b3|1|21|
|物理证明：header|p2/b0|1|21|

所有实际来源合计 **7units／6blocks／99 raw字符**；其中需要理解事实的材料是 **5units／4blocks／57 raw字符**，另外两条是正证running-furniture的物理证明。native换行若实际进入某层仍计入该层，不能折价；它不是本例瓶颈。

我此前“6源block所以必须延期”的消息混淆了两种度量，现明确撤回其强制延期结论。不能漏算物理证据的实际工作，但也不应把未进入模型的几何元数据又收费成模型材料，凭此新增门禁。

## 依据原代码职责，而非按测试绿红定义合同

只读回看`1712ed10`：`within_reference_envelope`统计body、既有context和reference declaration，展开carrier以免语义材料低估；没有把全部观察/几何证明都作为材料。旧native sentence路径遇到已正证家具时先`state.charge()`，记录其ID/page/ordinal/paragraph，再continue，不把家具放进business run。

当前新增`NativeSourceDependencies`的docstring写“source-only也占同一材料envelope”，属于本轮新加的更强策略，不能拿它证明旧合同本来如此。我早期设计文字也把“所有证明联合计费”写得过宽，容易导致这个额外门槛；应按层修清职责，而不是修改9例来配合新门槛。

`unfinished_furniture`同理：root＋left＋right是3个语义blocks；加两家具虽有5个物理源blocks，并不自动违反4个模型材料blocks。原未完句正控不应仅因物理见证更多而被延期。

## 推荐责任边界

- **语义材料层**：target、祖先、intro、可读left-body、reference declaration、限制、脚注、deictic事实闭包联合原始8units/4blocks/2048chars，carrier必须展开；真实超限仍诚实延期。
- **物理证明层**：同一16M工作账预扣/实扣；保留真实source refs、定位、序号、frame/font/lane、coverage及被跳过家具ID。来源观察和几何证明受真实client窗口保护，不成为业务文本/模型支持或另一任务库。
- 只有**正证的running furniture**可physical-only；脚注、条件、限制、业务正文不能换个字段名逃出材料成本。缺/异源/未证家具应使这条祖先边不成立并诊断，不能借标题或把缺证当更小有效闭包。
- 24的措辞须准确：现列表client明确`members+skipped<=24`、最多2页，当前`NativeSourceContext.page_neighbour`也限制gap<=24；旧sentence跳家具另按逐unit工作和seen上限，不可仅凭结构常量就宣称所有旧句子物理路径已统一24。这里没有实验验收，也不建议为本例再造一个硬上限。

因此无需伪造原bbox/block或硬凑另一个4block家具夹具：当前fixture的**模型材料本来就是4blocks**。后续独审应分别验物理正证、真实工作量、语义上下文和模型材料上限。原source-only身份必须留痕，绝不是免费丢弃；也不能重名为footnote后省料。

只新增本md/json，原9测试、RED/旧freeze、源码、索引、母PWF均未改；新ROOT predicate节点是合法后续改动，不按旧freeze误报。早先note脚本只因Windows路径key分隔符在写入前退出，没有发布失败版或动到产品。
