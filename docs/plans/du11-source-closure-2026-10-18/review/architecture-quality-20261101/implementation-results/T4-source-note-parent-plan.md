# T4：独立备注的真实父链边界（R7之后）

这是既有来源正确性责任，不是新门禁或新外包；本轮仅补实施细则，未恢复该源码施工。前置为R7最后遗漏工程收口/精确CI。证据为C-source-v4-independent.md/json，不能把12/12召回、局部intro正确签成父链正确。

## 已证故障与唯一责任层

真实半年报v4完整388583B记录、112spans/101unique native成员、12/12required exact originals均成立。但group-25/view-0、group-28/view-0、group-65/view-0的context_evidence_ids仍含旧p34¶3“（4）减持股份的信息披露”，span `5c9eca078287e9d60d43988fecc63f132e24c0b6f2b52363519485640bf035bf`。原页34–36证实独立备注6–11是新承诺主体，局部note_scope已隔离，树仍继承旧嵌套标题。

根因落在document_understanding/structure/sections.py的note_parent_stack=list(stack)及source_note_scope边界；不得让summary/selector/RF再补一份公司名/备注号过滤。不得提高额度/名额、重新归类整页、按公司的特殊词删除标题。

## 测试先行与实现约束

|反例族|应保留的行为|
|---|---|
|首次被识别的新独立note前存在旧嵌套标题，前一note未被识别|新note不继承前一承诺的局部子标题；仍保真正共享的章/节父标题|
|连续同级note、换页、断行标题、别的编号和主体|新peer scope关闭旧局部层级，无公司/编号硬编码|
|当前note内部新子标题或条件分句|在下一个真实peer boundary前保正确嵌套，条件/否定/actor限定不丢|
|财务解释性备注真正隶属表/上级小节|不得把所有note一律提升到root，不因本样本盲目flatten|
|未标记普通正文、页眉脚、无法证明的几何|不猜新的独立主体或层级；缺geometry不普遍拒，歧义明确标示|
|有限proof/work/deadline耗尽|完成前缀保留partial，不把未知边界改成已证独立；不以partial整文禁读|

先用上述去公司化正反例冻结期望，作者确认正确RED后才改来源树owner。若现有source_scope和heading kind不足以表达边界，仅扩同层结构事实/版本，不把主题/经营推断放进结构层。跨scope的context来自结构真实成员，不以某个string白名单修整输出。

## 两个大节点

1. 工程：只跑新增边界与受影响结构/closure邻域一次，失败定点修；冻结最终源码SHA，独立agent审实际父链、合法嵌套、partial/资源反控。旧T3/R7成功历史不重签新版本。
2. 真实C-source：冻结代码后仅单H1，原90s/16M/112保持，不重整批或付费。正向核当前intro/actor和真正父标题；三个已选组无旧(4)污染；原12成员仍exact来源可回放。Pair5的p35¶16–18三终止条件可在同一native carrier，不以direct map空冒缺失。其余未选单位仍明确unselected，不能把7/17支持代表全覆盖；不强制101或111作为固定计数门。

原件PDF SHA/size、生产DB/config/runtime前后核对；只引用原件不复制，隔离临时资料恢复初始。失败保完整记录，observer故障不翻转业务/重发付费。两节点通过后正常提交推送更新PWF，再进入C-preparation新真实摘要/paid恢复/同artifact RF采用。没有逐小节点人工许可。


## SEM-QUAL-01 — 同一来源正确性节点追加（真实摘要前，P2）

本轮合同测试带出真实缺口，不能归作新夹具错误：原文“公司计划在项目建成后为工厂提供产能保障。”与“该安排仍须客户完成验收后方可投产。”两段都引用，改写“公司已为工厂提供产能保障。”/modality actual，legacy与当前v7均可能draft/needs_review=false、prose/atomic诊断为空。精确source/span/locator/decoder结果已冻结在gate-rejection-followup-20261102/cwp-contract-followup.json。原失败必须保留；已支持“项目建成后将…”的正反控不能代替这个反例通过。作者别名T4-R4-CONDITION-SCOPE-LOSS与本节SEM-QUAL-01为同一反例，映射既有T4/R4限定/归属共因，不另建目标或重复计缺陷。

### 责任与根因调查

- 沿现有来源限定/上下文/claim decoder owner定位：限定是否未提取、被错误绑定，或只是引用完整原文就被误认为claim保留了限定。不要先假定只少了一个regex，也不要写公司/产品关键词或新增手工批准。
- 计划、前置验收、依赖事件与既成事实分开绑定到证据范围；核原文主体、时间与条件作用域，覆盖跨段支持上下文。不能因引用p1/p2齐全就认定改写被支持。
- 原文与有效span继续可读；对剥掉条件/升级actual的派生claim按现有partial/diagnostic owner处置，不能假verified，也不要求人工review receipt。无法判定保unknown/needs_review，不凭有限词表自称完整语义证明。

### TDD与实施细则

1. 先冻结这个真实公开反例，并加去行业化的中英文变体：计划/验收/获批/时间前置、跨段条件、否定；真正无条件actual与原文明示条件已满足的正控也要有。不要只换成已支持句式。先证明原实现对当前反例确实漏报。
2. 源owner统一产生/消费限定绑定；legacy与当前source-owned/scoped路径薄复用同一规则，避免只补一个decoder。绑定和选择发生变化须进入现有recipe/input/cache身份，不另建状态库/许可链。
3. 单元验原子限定与作用域；集成走normalize/select/model-input/decode，确认条件确实进入实际模型输入；API/worker验无错误accepted claim以及有效材料不因可选诊断被拒。当前legacy/v7原反例均需闭合。
4. 旧付费响应/费用/pin不改；新判定下可重解码已存材料以检错，不能靠重POST或增额度掩盖。失效/partial与已知/未知费用依旧归原owner。
5. 与T4父链修复合并一个大节点独审：检查泛化正反例、原始source/locator、实际模型输入、原H1的12重点/成员/父链与限定召回。只跑必要受影响域及单H1原90s/16M/112，不重复超时全量。此节点完成后才做新版真实摘要、恢复与同artifact实际RF采用。

整个公司loop/买方分析仍需后续真实验收；技术门禁清理与已有147/149合同证据不能把这个语义缺口签成已解决。
