# 剩余单元反证：只读共因盘点（等待 ROOT 单次全域完成）

状态：INVENTORY_RECONCILED_SOURCE_TDD_DISPATCHED。基线908ef3cb / CI40729898744；ROOT paragraph3 WIP继续冻结、不入SOURCE manifest。ROOT单次全域9476 collected在600s、retained_plan_fixture_bytes第4/12、89%超时，初次收据明确INCOMPLETE和27条failure reports；原wrapper清理Git只读对象失败，ROOT已核无子进程并精确清理、补receipt。随后仅补未执行尾部50文件1021P/129.18s、retained12P/15.53s、正常child插件harness3P/55.85s，均complete且scratch清理。未重复全域；初次不完整性质不改写成单次全域PASS。除3个harness假反证关闭外，24个待关闭报告归为marker1、语言import5、partial17、v3recovery1，尾部无新缺陷。本文现在定稿并按ROOT显式dispatch仅实施共享heads SOURCE根修；其余四旧fixture文件由ROOT并行修，不改producer/consumer协议。

## 当前已知两组

### partial-source：首批注解9项，当前增量已见17项，同一完整 device 动作被漏

原fixture BUSINESS=`Company launched a new device and received repeat orders from overseas customers.`。多个partial/replay/forgery测试先需要真实可选span；完整业务句漏选后，下游partial和篡改检测一起失去测试起点。

当前17个报告包含5个正路径/coverage断言和12个依赖 `package.evidence_spans[0]` 构造篡改样本的负控起点；不能把构造阶段的缺span当成12个产品防篡改失效。后续修共享head后仍须原样跑这些负控，确认拒绝的是篡改材料而非因为没有真实起始span。

静态证据：shared assertion_roles 头部枚举已通过 product_head_spans 消费 canonical product heads；但 actor→provision/action→target 分支只检查局部 `_DESCRIPTION_OBJECT` / `_RESOURCE_OBJECT` / `_STATE_HEAD`。`device`是共享 PRODUCT_SUFFIX/product-reference 已有头，却不在该局部_DESCRIPTION_OBJECT枚举，因而同一个对象在主语位置和动词后的宾语位置判法不同。不能只往局部词表补device；后续修应统一消费已有头的实际局部 span / typed object证明，避免为每个产品头追加副本。

同时核 source predicate binder 的 PRODUCT_LAUNCH_EN actor-contract：目前以 ISSUER_WORD/RELATED_PARTY/THIRD_PARTY 为真正事件主体约束；不能因为描述正例恢复就扩大issuer归属或制造完成stage。完整未知阶段描述可保留，原句source主体和原始text必须保持。此处是静态候选根因，待允许实施后的中性RED验证，不把推断写成已实测。

建议后续TDD（当前未跑）：canonical shared product-head的若干中性不同对象位于动词后，完整 Company/The company/We + launched/provided动作必须可读；同一 heads 作裸NP仍不可独立；断句/另一actor/另一个predicate后才出现head，不得借给前句动作。优先重用当前一次预备的head span索引，不能在每predicate重新扫描整句、放大前缀复杂度或提高预算。原partial9节点完整断言不改；合适时保留整个partial source文件的positive/forgery/unread/replay控制，不绕过实际选择。

共享头不等于任意金融修饰名词都可经营准入：保留原 `_description_payload` 的治理/会计对象关系约束和 clause-local source purpose，复验既有内部会计/控制系统、金融资产/期权模型、规则/审计对象负控，以及对客软件/设备/平台正控。不得用typed head存在替代完整主体—谓语—实际宾语关系，也不能仅借source section恢复eligible。`_DESCRIPTION_OBJECT`中云/工作负载等补充描述头与canonical product-family头应合到一次局部观察的入口供两个消费位置使用，不再维护两份产品家族枚举。

**同文件另有旧模型协议夹具，须分层处理。** `_registered_dag` 显式设置 `reading_model_projection=lambda _:None`，CountingModel读取旧 `data['source'] / data['evidence']`。这与当前/4生产producer和已独审“/4不能调用legacy codec”的合同不一致。typed-head修好selection后若DAG在model-port仍拒绝，属于下一层旧测试协议，不得修改producer/consumer合同或给partial放行legacy。ROOT可将此fixture迁为当前合法scoped model端口，保持BUSINESS、partial coverage/unread、原件reopen/replay次数、所有forged/零model负控断言不变。SOURCE作者不扩展写消费者。该迁移与本节真实device召回根因分别记账，不能用迁移fixture掩盖未修selection。

**第27个当前报告是同类历史producer/codec候选。** `test_narrative_scoped_runtime_recovery::test_real_paid_v3_typed_stage_recovers_with_zero_new_posts_after_validator_upgrade` 在first.status处报告failed/MODEL_RESPONSE_INVALID。源码仍使用当前selector0.9，却通过generation_manifest monkeypatch强制reading-model-input/3。需由ROOT查明其是否把当前/4 producer与历史codec混配；历史恢复正控应先真实形成合法旧producer/协议绑定，不能为了制造历史账单把当前/4换tag或放宽runtime拒绝规则。保留原已完成后0新POST/数据库与原件不变/validator升级恢复断言；修复/迁移先取得定向RED与明确绑定，不宣称静态观察已证实全部因果，也不归成source新业务词缺失。

### value-coverage marker 的1项：旧fixture需语义完整迁移

原test_marker_filter_does_not_remove_words_with_digits_or_roman_prefixes含3句。第一句`IV therapy services for hospitals`只有NP+for修饰，不是完整断言；当前阻止它独立summary与已验收NP边界一致。该测试真正意图是IV字母前缀不被误当纯Roman marker，而非让标题短语自行变事实。

只将这一正例迁为保留开头IV、但带有限谓语的`IV therapy services are provided to hospitals.`（或同一完整谓语等价句）。保留其原_admitted断言；另外两句`Our 2026 product portfolio includes recycling systems.`和`一体化生产服务覆盖多个下游客户工序。`完全不改。现有noun-only negatives与裸NP拒绝继续作为反控；不放宽producer proof、marker、section intent或NP grammar来迁就旧fixture。此迁移应由ROOT统一拥有，当前未改测试。

### 当前增量 daily_push_policy 的3项：盘点 harness 插件继承，不改 gate

本次 ROOT 全域盘点父进程禁用插件自动加载，并显式通过 `-p` 加载 timeout；子pytest继承 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，却未继承父argv的插件加载，故拒绝hook既有 `--timeout=180`。当前失败正文明确是 unrecognized arguments，而非真实gate放行/阻断语义变化。

这是与 SOURCE 真召回缺口、marker旧语义夹具分开的第三类。保持这次单全域跑完，不重启或改gate/删timeout迁就观察工具。盘点结束后，ROOT用正常CI插件环境定点复验原3项（显式使child加载插件，或撤销禁autoload；仍隔离测试temp/资源），先取得该类真假失败的确证。后续记录环境反证和复验范围，不将它们记为本次SOURCE产品修复。

同一类别下新增语言5项：目前完整正文全部在 `from tests.document_normalization.test_docx import ...` 处报 `ModuleNotFoundError: No module named 'tests.document_normalization'`，产品语言采样、DOCX normalize、batch语义均尚未执行。不能把它们归为五个业务/公司召回问题；待ROOT正常CI可移植import-path环境定点核这个测试命名空间，再决定是harness还是旧测试import夹具。保原语言、部分DOCX、无效包和normalization-owner断言，不改生产语言检测来迎合导入错误。

## 已定施工与收据边界

SOURCE仅修改 assertion_roles.py 与 owned test_source_support_use.py：先中性RED，准备一次共享typed-head span索引，描述主语和action宾语消费同一索引；宾语须在同一原clause、实际predicate后局部范围内，保既有financial/audit/NP/actor及unknown-stage规则，不添产品词表副本/公司/阶段/预算。若需其他SOURCE13 owner先明示ROOT。必要短包包括新head泛化、既有描述/用途/金融/审计/NP及缓存计量、实际partial节点（ROOT迁移fixture后合验），不重跑已完整全域或尾部。Ruff/mypy与清理后冻结handoff-remaining.md/json，ROOT统一独审/一次五gold全views/发布。

证据：all-unit-counterproof/receipt.json（明确INCOMPLETE）、unit-counterproof-tail/receipt.json、unit-counterproof-retained/receipt.json、unit-counterproof-harness/receipt.json；原失败正文failures.jsonl保留，原SOURCE CI13F与中性12F历史也不覆写。新测试中性验证不等于新实际供应商摘要通过；readonly盘点阶段未运行任何额外测试/原件/SDK/模型，之后仅按上述明确dispatch做SOURCE TDD。

## SOURCE实施结果（2026-10-28冻结）

ROOT明确dispatch后，中性RED13项=7F6P；六canonical对象族和原BUSINESS缺口均真实重现，负控先绿。仅在assertion_roles的原clause准备中合并shared product_head_spans、原描述/state头，resources以object-only加入一个位置索引；head-first消费与predicate后100字范围的bisect查找共用此索引。没有给局部词表追加device，也没有扩大Company的issuer归属、stage、阈值或模型合同。

必要SOURCE四短包412P/7.86s；独立动作族45P/5.76s（含主体/否定/未来/研究vs发布控制），合计457unique。最后仅资源迭代变量重命名以关闭mypy局部Match类型推断，之后精确HEAD/线性14P/4.34s；Ruff/mypy1src/scoped diff-check通过。原partial/recovery/语言/marker四ROOT文件和paragraph3 WIP本作者未写也未纳入SOURCE清单。详见source-support-use/handoff-remaining.md/json；ROOT接着统一迁移fixture合验、独审和一次五gold/fullviews实际回归。
