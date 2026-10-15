# 引用的事实支撑、上下文与阶段恢复

更新：2026-10-15；ROOT负责实施和整合。属于原A/B/C节点，不增加材料授权或小节点审查。

## 已证实的原因

- 新协议集中367例为366PASS/1FAIL：完整问答同时含投资者提问和管理层回答，原角色校验把所有上下文当成事实支撑，管理层陈述和投资者问题都无法正确表达。
- `QaDraft`已有answer anchors和question required-context，生产接线将区分丢失；不改成uncertain、不只挑另一个纯管理层片段来掩盖。
- 真实5a旧manifest仍有prompt2.0/schema3，但factory的全局whole-file软件哈希校验阻断。不写旧哈希假装新实现未改变；需要按实际剩余任务判断所需能力。
- 真实HK已有1次initial parse/select，96条正文/角色/flags及全部旧组逐项一致；后续复用真实选择，唯一正常独立verify为96/96。原件/配置/Temp保持。诊断Rect序列化失败及修复收据均保留；不是旧付费job完整恢复。

## 1. 冻结接口

### 1.1 来源阅读上下文

旧`du-production-reading/1`原字段和字节保持。新增有限`du-production-reading/2`，顶层不变，每个group在原四字段上增加：

```text
citation_views: [
  {support_evidence_ids: [canonical span IDs],
   context_evidence_ids: [canonical span IDs]}
]
```

每个view的support非空、唯一，context唯一，二者不交叠，二者并集恰为同一group原evidence_ids；均来自已经选中的同一原件。每组至多两个不同view，不增加另一份原文或任务库。

QA由原生`QaDraft.answer_ids/question_ids`经现dependency package传递两个view：答案支撑、问题上下文；以及问题支撑、答案上下文。不得按角色或文本重新猜问答关系。其他组保持原完整成员作support，不误用仅供排序的anchor来缩小事实范围。未知关联不制造QA view。

### 1.2 模型与canonical claim

新`reading-model-input/3`仍只输出flat claims和`citation_unit_ids`。编译器将每个真实view编译为一个单元；别名同时绑定完整成员和support/context分区。模型输入unit列为`id,evidence_ids,support_evidence_ids`；原文仍只存在唯一evidence表。

程序统一还原：`evidence_ids`为实际事实支撑，新增可选`context_evidence_ids`为理解所需的完整上下文。空context不序列化，历史claim和None/v1/v2请求/HTTP字节不变。旧context/1不能假造新的事实分区；其单元继续全成员作support。

合并多个单元时按实际原件顺序去重；显式support在另一单元中也是context时保留support义务，不静默降为context。不沿重叠组递归扩张。

角色和输出语言检查只使用support；context仍校验来源、唯一性、范围及质量，并和其他selected spans一起正常重放。提问中的数字不能只因同组有管理层文字就变成管理层披露。机械引用校验仍不等于语义蕴含。

### 1.3 消费者

盘点到RF的`scripts/company_wiki_narrative_contracts.py`严格只收context/1及旧claim字段，必须定点增加context/2与可选context引用支持。保留原文/Ref/hash/角色责任，不访问底层存储路径。FF/StockWiki未发现字面context/1专属分支，仍在跨仓联调核对。

## 2. 文件及顺序

1. 先写`tests/unit/test_narrative_citation_attribution_contract.py`和模型/原生QA正反例，实际保存RED；不先改已有失败断言。
2. `document_understanding/orchestration.py`只保留QA现有的两组原生support IDs；`source_catalog/narrative_reading.py`将其映射为已选canonical IDs，产出context/2。按现pipeline常量/决策inventory更新真实因果，不建第二registry。
3. `source_catalog/narrative_evidence.py`的SummaryClaim及共用校验、`automation/narrative_contracts.py`负责新可选context字段/有限版本分派；旧序列化未变化要有字节断言。
4. `automation/narrative_model_citations.py`负责唯一单元分区；`narrative_model.py`只消费这个编译结果，拒绝模型自行回填support/context IDs。语言观察沿现support字段即可，不另造检测器。
5. shared provider fixtures按实际schema/单元support选择返回内容，不能绕过问题或把事实一律改uncertain。正式新代测试升级为context/2，历史测试仍显式保旧格式。
6. RF只更新上述消费合同与专属测试，必要技能副本定点同步；不碰assurance/output或其他WIP。
7. 恢复另按下节职责TDD接线。完成后统一冻结源码、集中单元/静态/正式生产与跨仓E2E、正常commit/push和精确CI；不每个helper单独签收。

## 3. 恢复的责任范围

| 剩余动作 | 实际所需校验 |
|---|---|
| 读取已发布bundle或ACK canonical outbox | 已存字节/Ref/目标/原generation及正常发布或重放责任；不要求无调用的LLM renderer |
| verify已有canonical summary | 真正使用的来源解析和locator、typed claim/context、bundle版本；不检查未调用的prompt/provider |
| decode已付费raw final | 保留终文/attempt/usage，执行真正可用的decoder/validator；不自动重新POST或伪写旧哈希 |
| pending summarize | 仅该item真正冻结的renderer/schema/model/decoder/validator；不让已完成兄弟item的旧哈希阻断 |

先用独立旧5a源码生成真实activation_pending，再用新代码同DB恢复，实际观察是否经过factory；不得凭纯端口proof假定所有outbox均失败。旧源码只读导出到唯一短Temp，原件使用合成小文档，无生产数据备份/恢复演练，最后删除测试代码和目录。日常CI不依赖旧Git对象是否存在；用小冻结manifest与阶段职责矩阵固化。

## 4. 大节点检查点

- 公司回答、投资者问题、否定前提、短答均有各自support/context，不丢否定和限定；未知/跨原件/重复/缺失/重叠反例拒绝。
- 英文回答+中文提问不能许可中文翻译回答；真双语各自原语言、短句弃权保持。
- 分区调换alias不同；多单元重叠不丢显式support义务；context质量差仍needs_review。
- 至少一条真实原生QA selection→request→decode→verify→publication，并走RF消费；全程loopback、0供应商，Temp/原件/config/sentinel恢复。
- None/v1/v2冻结HTTP字节、旧canonical不增加空字段；真旧源码paid outbox及same/cross复用0新增POST、费用与attempt保持。
- 表格期间绑定是独立未完成项：HK已证原件存在2024右列，native大merged-cell含旧列而选择漏掉后续右列行。保留该失败，不拿引用/语言通过当错年已修。
