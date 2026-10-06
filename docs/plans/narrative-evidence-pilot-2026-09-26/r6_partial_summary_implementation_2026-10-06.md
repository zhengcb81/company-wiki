# R6：局部坏模型片段不阻断可用摘要

## 原要求与发现

已采纳的激进方案R6要求局部解析/引用失败只丢该片段并显式显示不完整，模型无害额外字段不阻断整份来源。完成审计发现当前`decode_model_draft`遇一条未知引用直接抛异常，公共draft解析器遇额外字段也整体拒绝；此前S4真实run10成功没有覆盖这项容错要求。重新打开S4的此具体缺口，保留已有真实业务效果证据。

MAIN独占此修复，RF当前main6e6b817a与owner两日志只读，复用它的已提交consumer；N5外线仅benchmarks/tools，不改它们的写集。Dayu/IQS零写。0外部模型、0下载、0付费，不改变Config、输出token/温度/端点/超时。

## 设计与接口

1. 私有模型边界先做有限投影：只取当前draft/claim合同字段，丢未消费的额外字段，原响应仍受128KiB/严格UTF8 JSON/重复键限制。未知字段的名称/值不写诊断、日志或工件。公开reader和canonical合同继续拒绝额外字段，不让所有接口一起变宽。
2. 全局条件不能修补：draft缺失/非对象、claims非数组、source ID/SHA/语言错、全局状态无效、显式translate非false、JSON坏/重复键/尺寸超限仍具名失败。不按文件名纠正来源，不猜语言，不补造字段。
3. 逐claim恢复：alias仅解析到本次选中canonical ID；一个claim中任何引用不明则丢整claim，不能仅移除坏ID而保留可能失去依据的文字。字段/空文本/角色/情态/质量标记不合约同样只丢该claim；不改写正文、引用、角色或情态。重复claim ID全部丢，避免歧义；至少一条通过原canonical校验才有可用摘要。
4. 将来源身份与单claim验证拆成可复用纯函数，原`validate_summary_draft`调用它们；模型adapter使用同一解析/验证函数，不复制角色或引用算法。分析师问题必须保持question情态，不能由CWP产出而等RF拒绝。
5. 局部丢弃时复用当前公开合同的`draft.status=needs_review`与bundle `quality_status=needs_review`表示**摘要不完整的质量诊断**，剩余claim保留自己的标记。现行RF只接受verified/needs_review/skipped三个quality值，不能自造partial enum或额外wire字段；需要人审的许可已经退出，这个标记不会阻断读/搜索/导出。不冒称精选证据coverage变少，选中span/locator保持原样；说明明确这是partial-summary的兼容映射，非人工签收。
6. 无可用claim继续失败，保留原错误类别与静态rule标签；单一坏身份/语言/角色不能变绿。费用结算仍先于解码，坏JSON/坏claim/partial都照已发生usage记账，不新增第二账本或重试模型。私有prompt/响应策略版本升级1.5.1使请求hash不静默复用旧处理；公开历史bundle仍可读。

写集：`automation/narrative_model.py`、`narrative_summarize.py`、`source_catalog/narrative_evidence.py`与专属新Unit/Integration；确有必要才改现有受影响测试，不改golden、公开wire、源库/生产配置、跨仓代码。正常源码注释去掉已退出的“G1人工review才能可用”描述，不扩展投资语义。

## TDD与一个集中验收节点

1. 先RED：一好一未知引用、一claim好/坏混合引用、错角色、错情态、坏shape/空文本/坏质量标记、重复ID，保留好claim且公开needs_review；全部坏仍失败。extra字段在root/draft/claim层忽略且不会持久化其原文。
2. 防放松反例：wrong source/hash/language/status、translate=true、无claims、非数组、重复JSON key/超限、无证据、路径泄漏；公开canonical解析器仍拒绝extra；旧正常草稿与25条长草稿照读，选择/span与request原语言保持。
3. 实现私有恢复，责任Unit集中一次；已有诊断测试中的“额外字段必须失败”与新已批准要求矛盾，改为额外字段不持久化的成功断言，身份/语言/角色失败断言保留。不得把RED标准改成当前实现输出。
4. 一次真实CLI+loopback HTTP E2E：正式configured entry/Worker/DAG/outbox生成局部可用工件→公开reference/read/search/exact→全部locator回放→RF已提交consumer读取；再跑同run确认零重复调用，输出unknown字段不在工件中。使用隔离真实TXT字节与fixture来源元数据，不能称真实供应商新摘要。外部POST/费用0。
5. 测试根原先不存在，finally核原件/生产/配置/RF owner指纹并清理本次目录。复用未受影响节点A/B、已绿真实run10，不全仓重跑长E2E，不新增日常CI矩阵或人工门。责任lint/mypy、正常commit/push、对应代码CI通过后写小收据与PWF。

## 完成定义

合格片段能在其余片段有错时经原严格合同被发布与消费；不完整质量可见且不要求人工许可；全局身份/语言/字节和全部剩余引用仍真实；坏片段与无害extra不进入最终产物；无可用片段失败。Unit/正式离线E2E/RF消费/清理/精确代码CI共同证明本修复，不把真实run10或绿色旧测试替代局部容错验收。

## 当前阶段

**Status: complete** — 代码eae2dd4557491e6621ddbe73f972f01a841a8f00已推master；[精确CI37521679387](harness_lanes/results/r6_partial_summary_ci_2026-10-06.json)attempt1全绿/59秒。

- TDD初轮30项：17 RED/13 GREEN；另三项NaN/Infinity严格JSON反例先RED再修。最终7个责任文件184 passed/2.04秒，相关Ruff与两模块mypy绿。
- 正式离线CLI E2E 1 passed/16.62秒：真实66324 B电话会字节、loopback模型响应一好一坏引用，正式Worker/outbox→public reference/read/search/exact→RF已提交六模块读取，46个locator全部回放；只保留好claim且needs_review可读，同run恢复零重复POST。没有真实供应商请求/费用。
- 两次E2E初红是夹具config位于root而非config/，两个CLI默认project-root推导不一致；仅把测试config移入标准config目录后绿，不削弱reader或改RF。mypy两处schema类型推断红已补明确dict类型。文件名猜测读不到、一次沙箱RF Git ownership错误已改实际目录/正常用户上下文，未改生产设置。
- 原件、三个生产配置/库文件、RF两owner日志指纹保持；七个明确测试根经绝对路径/无reparse核查恢复absent。未知扩展不落盘，全局身份/语言/显式翻译与全坏claim仍拒绝。
- 收据：[R6集中节点](harness_lanes/results/r6_partial_summary_node_2026-10-06.json)。此前run10真实业务证据保持，不能把本离线响应称为新付费模型验收。
