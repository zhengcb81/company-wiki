# R5 最后集中接口独审 — 可工程发布，随后暂停

2026-11-01；审查者 `/root/rectification_review_a`。本轮只核已冻结的CWP/RF公开reading合同；没有扩大旧语义审查、原材料解析或付费。冻结CWP **5/5源码/测试SHA一致**，RF三文件实际字节身份见 [evidence](independent-wire-r5-evidence.json)。源/主PWF/Git/生产只读，仅本报告和小证据新增。

**结论：当前R5 wire节点通过，未发现本范围剩余实质P1/P2，可由ROOT正常提交、推送并按用户要求暂停。** 发布和精确CI仍由ROOT完成。本结论不代签C真实H1/新版摘要/持久缓存恢复/RF实际采用与经济验收；这些继续OPEN。

## 跨仓联调与合同结论

1. CWP真实`NarrativeSelectHandler`→严格`NarrativeSelectResult.from_dict/to_dict`正常/能力deferred两场景均通过，未mock selector或合同。complete为selected/True；deferred带健康typed段为partial/False。能力原因和bounded IDs通过真正输出wire，未出现unknown field或下一个diagnostic shape失败。
2. DU共享owner `reading-context-wire/1.1` / `du-production-reading/4`定义可选strict bool。无字段的旧材料保持原样，**不补True**。None/0/1/string/list/dict均拒，unknown属性仍拒。
3. RF便携consumer独立实现合同，不通过runtime import CWP私有代码耦合。新wire测试通过；另外对真实RF公开`validate_narrative_response`用有效schema1/2/3 fixture做正反对照：旧材料无新字段能解码，返回无伪默认；加入新字段后拒绝。schema4任意额外字段同样拒绝。
4. 三种source-readability diagnostic只接受精确字段、严格count/bool、dimension/phase、bounded canonical unit IDs、total/sample/limited关系；旧预算diagnostic shape保留。错误代码/字段/shape不能借新分支放宽。不存在新的人工许可或签收门。
5. 实际CWP handler golden的complete/deferred **reading_context + evidence_spans**直接交RF真实`_reading_context`解码，逐对象未变。其布尔值保持True/False，原producer selection selected/partial不互相替换。
6. RF fixture是15,153 B的精简投影，不是67,411 B整个SelectResult的字节复制。已核它声明的producer_golden_sha256正确，两个case的context/spans与完整CWP golden精确相等。没有伪造带模型summary的NarrativeBundle/read receipt，也不把此source合同联调称为完整RF流程。
7. CWP显式feature身份与实际recipe闭包成员测试通过，source修改会进入reading决策身份；未靠手工许可或只改字符串绕过校验。原件SourceExport v2不承载这项reading语义，不需跨层添加它。

## 独立验证

- CWP `tests/integration/test_source_processing_handler_wire.py`：**18P /8.59s**。
- RF `tests/test_source_readability_wire.py`：**32P /1.22s**。
- 额外内存探针6项：公开legacy1/2/3正反、schema4 unknown拒绝、真实CWP complete/deferred context/spans解码。读现有golden，无原文大解析。
- CWP golden SHA `0bec092a852adacdbacf93806ff3ebf540925cd48c67e35d2acdefccdf9781ae`；RF精简fixture SHA `d37d92fada4648d4636850c39267676548fd42b01aa39281c2dd55ba8466866c`，完整对照在[probe](independent-wire-r5-probe.json)。
- 作者RF109域/static结果由ROOT接收；本报告不冒称独立重跑该109域，也没有重复R3 41/88/100/H1/付费链。

## 观察代码错误与恢复

初次读取误用`Q01-rework-r5-integration-evidence.json`，实际为`Q01-rework-r5-evidence.json`，已按报告入口改正；RF/Projects根无AGENTS文件，未虚构附加规则。只读`git -C RF-worktree status`被环境拒绝，不影响已获准源码读取；没有改权限或绕过拒绝，发布由ROOT处理。

初次额外schema3探针未同步fixture的selected denominator，报invalid_selection_trace_selected；参照既有public_context同规则先建立合法baseline后再加字段，确认这是探针构造问题，未修改产品。初次要求整个RF golden字节等于CWP golden也不符合其公开精简接口，已核实际context/spans及producer SHA完全相同；未把压缩投影误报数据丢失。

两个独占短目录`tmp/wire-r5-cwp`、`tmp/wire-r5-rf`初始absent，长度均在现有pytest预算内；结束前核绝对目标在本repo/tmp，仅清理本轮目录，最终absent。没有原件/数据库/配置/缓存备份或恢复演练。

## 停点

原R4有界PASS和后来的H1 handler真实失败保留，R5在新增真正wire边界修复后才获本次工程PASS。ROOT可收取RF定点部署/正常发布证据、更新主PWF并暂停；C真实摘要、缓存恢复及RF经济责任不因这50个合同例变为完成。本review到此STOP，不另开任务或扩大测试。
