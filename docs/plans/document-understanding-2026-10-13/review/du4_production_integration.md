# DU4三组件接入唯一共享引擎：ROOT实施顺序

2026-10-15。三包组件接收后执行本文件；当前是**实施细则，尚未接线完成**。作者目录保持交付快照，ROOT只改本仓既有生产组合层。旧只读审查文档的SOURCE/Git STOP说明当时审查范围，不是对当前已授权ROOT施工的新审批要求。

## 1. 实际调用链和预算所有权

当前`pipeline.understand_units`依次组合build_observation→apply_layout_hints→route_document→structure→bind_layout_context→strategy/packages。实际源码的两个预算创建点为`layout_hints.contract.parse_observation`与`layout_bridge.bind_layout_context`；router当前没有WorkBudget参数。不能把handoff写到的“现有route预算端口”当成已存在实现。

把调用方WorkBudget所有权提升到唯一组合owner，给已有layout解析/bridge及三个组件增加薄传递端口；standalone旧入口不传时在原owner创建一次，组合调用显式传同一实例。组件不创建或续预算，现AUTO/API费用账不变。固定probe单位/字符cap与计算工作上限各司其职，不把200 probes、96 selected spans和WorkBudget混为同一上限。先做廉价且真实的source carrier观察，再消费已有有界layout增强；耗尽给partial/deferred，原文仍可读，不发明人工许可。

TDD：同一个实际对象贯穿所调用组件；budget0不转换正文/拷贝长尾；部分耗尽不抹去已确定事实，也不把未读部分当业务不存在。测试真正访问数及持久结果，不只比较work_used。layout standalone兼容和原预算失败用例保留。

### 1.1 已核源码中的共同效率缺口，接线前优先解决

只传一个新参数还不够。只读已发现：apply_layout_hints先deepcopy整observation并全量组页；layout parse在budget创建后仍全量验证/排序/复制hints/frame，derive的耗尽捕获在parse之后；bind_layout_context先deepcopy、耗尽路径再扫全semantics；profiles先全建UnitRef tuple再200/64k采样。structure的limits还要求max_work_units>0，所以不能把统一0机械塞进各自limits并宣称诚实partial。

下一A节点必须先固化这些实际工作反例，再选最小共同owner方案：source/adapter一次准备已观察的基础单位与索引，内部只读共享已有text/metadata及原生ID；各分析层只为自己的少量增强字段建立overlay或结果对象，禁止反复复制全document。不要要求每个配置策略再完整解析、校验或签收同一身份。现有外部Mapping入口可在所属owner做一次兼容准备，内部组合调用复用准备结果；不得新增第二canonical source/schema registry或共享可变状态。

测试分别衡量不可避免的单次基础输入/输出物化与可选分析：同一原文只parse一次；同一单位的基础准备次数有限且不随组件数倍增；零增强预算不启动转换/正则/全量deepcopy，仍可引用已存在原文；永久/部分预算覆盖正常路径和异常诊断路径，不在except里无界扫描。不能为了满足一个计数器隐藏必要工作，不能拿扩大预算解决多次复制。旧standalone正值limits规则保持，由组合owner显式处理零工作而非加新拒绝门。

完整独立Observation的物化需要基础O(N)工作，不能同时承诺零预算、不访问长尾和返回所有unit/deferred IDs。A节点须先检查真实调用者：新增强耗尽返回薄partial并保留上游原parser材料，未读部分不得冒充已校验；如旧调用者仍必须接收全量投影，则明确记录基础O(N)与增强预算两部分，不能宣称整链硬限。route与profile resolver复用同一只读parsed视图，不能每个策略重新全建UnitRef；完整父子范围不能用孤立标记替代。只读调查的13源指纹与事实位置保存在ROOT工作记录 `du4-production-design/budget-owner.json`，调查未执行测试，不是已完成实现。

## 2. FORM：原生事实先被观察，再进入原cap路由

1. 在html_parser当前可见DOM owner/emit路径提取真实visible dei:DocumentType或own FORM label，记录其所在原unit精确字符范围和原生属性。隐藏/脚本/排除节点、文件名/provider声明不能伪造observed事实。不二次parse、不get_text拼整篇。
2. 用一条能随DocumentStructure存活的transient unit metadata路径传递carrier；adapter一次映射给已接收source_signals。不要只加在NormalizedDocument.metadata然后在language_structure处丢失。原text/locator/unit ID保持；transient reading字段不泄漏进旧EvidenceSpan/旧模型wire。
3. collector输出经当前profiles allocator在200units/64000chars内预留真实carrier，再填原cover/heading/body；不事后追加。UnitRef保留原parent/role/turn提示，call predicate依真实说话正文/归属判断，普通财务单元格的冒号不算电话会。原生表格内真正发言保持正控。
4. parent/child附件分别过滤自己的carrier和turn；理由必须引用真正载体，不用封面/目录ID顶替。不能引入第二router或单独下载路径。

验收：现存VRSK观察中的FORM 10-Q不再漏掉、Revenues:不再成为电话会；真实电话会与8-K父子样本保持；跨parent/hidden/声明冲突/降cap控制。至少一次实际HTML原文→单次native parse→adapter→router→正式selection的端到端。留真实观测与合成范围，组件fixture不冒充全文回放。

## 3. STATE：唯一经营谓词消费已绑定关系

在source/structure拥有原unit与同parent上下文处计算一次relations，向reading-only经营事实准入薄投影；不在每个相邻字符串片段重复跑组件。不改来源角色，也不另查实体库。question/shadow仍由原角色层负责；关系是来源描述，不是投资结论。

移除0.9 reading-only的裸OBJECT×ACTIVITY共现旁路；旧0.8 detect_business_fact与冻结请求重放保持。沿既有版本资产/selection generation记录新策略依赖。否定/尚未/暂停/合作意向可保留业务信息，但不能加business_progress；股东联系不变成发行人合同。无法闭合的限定语/主体/对象保持unknown，不能把schema合法当语义PASS。

TDD：m41三条实际关系与原文偏移；中文/英文/繁体同构、主句与供应商定语、计划/条件/假设、取得类aux；完整QA依赖不能被裁掉。再跑原三/新三真实source-only覆盖集，区分准入修复与测试oracle错误；若新构造仍缺普通业务披露能力，保留缺口整改，不按公司名补规则。

## 4. TABLE：原生槽、解释关系与选择依赖

在同一次原生解析/已有真实fine geometry观察中保留row/column/span/presence及逐值TextRef，adapter构造du4-table-observation/1后消费binder；不按最新年、文字顺序或右对齐制造列。无逐值定位的合并格仍unknown。复用已有TableDraft/reading context的单一owner投影，不能让binder成为无人调用的副本。

把解释所必需的真实表头/期间/单位/范围/限定refs加入现有dependency closure，再用当前selector预算整体选择；不要在模型后从别处补出处。unit→EvidenceSpan转换由来源层一次完成，消费者不访问CWP物理目录；若公共reading context需新字段/版本，同步唯一严格编解码与RF消费者契约、旧省略字段金样。

TDD：真实HK保留包只作开发回归，另选一家公司/格式做真实holdout；同数不同列/期间、万元/亿元/币种、复合单位、不可用表头、外parent、稀疏列、合并格、负数/破折号原样。计数34bound/7ambiguous是保留观察而非全文召回。selection确实携带解释依赖并进入正式摘要输入；不能只在临时对象上附新字段。

## 5. v4正式摘要、恢复和真实质量

遵循[source-scoped实施细则](source_scoped_summary_implementation.md)：legacy narrative_model.py真实字节保留；有限runtime入口选择旧None/v1/v2/v3与显式v4。新请求仍兼容HTTP的base request类型和with_output_budget配置端口，不另造HTTP/caller/费用库。源任务覆盖和有证据的指代关系来自共享引擎，模型只产text/basis_parts/modality。

先冻结旧v3实际请求/HTTP/identity与paid旧阶段0POST反例，再实现v4全局20条、局部basis/QA事实与context隔离、程序ID/角色、实际依赖hash和恢复。默认0.8、new0.9默认v3先保持；source因果配置更新后新generation与旧已付费结果分开处理，不伪造历史decoder可执行性、不重复付费。

正式离线E2E必须走真实worker→model caller(loopback)→decode/verify/outbox→公共读→RF消费，不手搓输出文件。其后按现配置MiMo/DeepSeek/MiniMax、累计2M tokens/$20运行有界真实摘要，逐claim核主体/产品/阶段/数字/期间/单位/原语言和重要方向覆盖，原6错引与PD5/Matrix遗漏保留旧FAIL后比较新结果。合法引用不等于蕴含。

## 6. 仅原大节点验收

A：源级真实反例/合成控制与旧兼容RED。B：统一生产接线、集中单元/集成/离线真实CLI及旧付费恢复。C：原文单parse、配置/Temp恢复、三配置供应商真实质量和独立审查，正常提交/推送/精确CI。费用、原件SHA、as-of等在所属层检查，不新增人工签收。HKIPO B0/B1/B2/C及母G2/G4/G5、原三→新三研究审计仍按母PWF开放；本文件不把组件发布算作全部计划完成。
