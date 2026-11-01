# R6 source semantics — 冻结待 ROOT 独审

状态：**FROZEN_READY_ROOT_INDEPENDENT_REVIEW**。仅在隔离工区 `tmp/architecture-r2` 施工；主工区 src、原件、配置、生产DB、模型资源和 Git 均未修改。此报告不代替整候选CI、真实H1或主线闭环验收。

## 真实 RED 与收口

- CI 41305132919 的63项失败是多个共因。本线重现指定8个语义文件：**16 failed /507 passed /60 errors，33.96s**。60 errors全是 sparse 工区缺同一已跟踪 golden gzip（预期SHA `e22a10df47b0890a2b62794f7134fc5670e00ceeff9707e3c4b9f9a51a9079f6`），ROOT补入后全部真实执行，未deselect或改旧期望。
- 新语义轴初始26例：**14 failed /12 passed，29.95s**。保留失败历史。自加的 equipment passive 新例最初误要求 support；既有 `source_payload_unresolved` 的强类型不完整合同应保持 unresolved，因此新例改为精确检查“unresolved且原话相关”，旧 monotonic 测试未改。
- 含真实 golden 的10文件中间轮：**3 failed /680 passed，26.58s**。三项为复杂中文名词补语和旧不确定性被错误提升；根修后65定点全绿。
- 进一步用纯客套反控获 **2 failed /9 passed，8.53s**；用介词宾语充当主语及同源重复扫描反控获 **4 failed /1 passed，9.57s**，均先RED再修。
- 当前冻结版：指定原10域 + grammar runtime + R4 deferred public selector + R5实际handler严格合同，共 **746 passed /0 failed /0 errors，111.94s**。其中原本60E的真实夹具全部保留、通过。
- Ruff（4源+新测）、mypy（4源）与 `git diff --check` 绿；diff check仅有其他owner文件的既有CRLF提示。此线没有改任何旧测试文件或期望；ROOT的runtime/消费者迁移另有owner。

## 根因与责任修复

1. **句法完整被误当作经营相关性。** 原通用fallback只要POS观察到完整句，便可把套话、目录元文本、非经营membership重新变成support。新增同owner纯策略 `narrative_source_context.py`，同一prepared clause只观察一次，区分 candidate/context/unresolved。`source_clause_context` 的 reporting/metadata/courtesy/objective 观察与 `statement_complement_context` 的经营相关性消费是同一职责，不做IO、不认公司身份、不产生经营事件。
2. **全句级历史bound标记过宽。** `existing_use=support` 不再单凭全局bound_payload给免费通行；保留局部 independent_payload 或已成立 substantive fact 的快速通道。事实仍由原关系/度量/事件owner负责；完整原话不改变fact、issuer、期间、stage或数值proof。
3. **上下文被逗号后缀重新放行。** arithmetic presentation等先在同prepared clause被确定，角色掩码保持源文长度与原refs；不能再把四舍五入注释的逗号后半句当陌生经营句。独立的新经营句保留原文，套话不得借它变成事实。
4. **中文句法把宾语内部的`的`错误理解为整个主句名词化，或把其内部名词当新主语。** copula/possession以及`于`补语谓词可取有内部`的`的名词补语；即时V+的仍不能伪装主句。歧义VP的尾部不得自己再造矩阵；编号/罗马枚举不提供主语；终结vn需要独立于介词宾语的显式主语。未添加任何公司/行业动词名单或专有名词分支。
5. **词义多用不应成为一词否决。** includes/comprises等只有membership关系并不证明经济相关；有prepared业务head/function的跨行业覆盖、用途和成员描述保留；`cover X with Y`按施用构式处理，不因cover字眼被当作成员枚举。
6. **完整语法不补强已有类型不确定性。** 旧typed `source_payload_unresolved`继续unresolved+relevant，不能被POS“补成事实”。未知行业的完整经营原话仍可support，但source fact和attribution不升级。

## 结果三轴与边界

- 明确context/abstract/reporting负例：不占摘要槽；原始SourceRecord、原语言文本和检索入口不变。
- 弱membership缺少经营head/function证据：`use=unresolved`、`relevant=False`，reason=`source_membership_relevance_unproved`；保留原话，不冒充纯财务、不制造事实。完全陌生且仅有单一成员枚举的语义可能保守，本层不声称有开放域经济常识模型。
- 可读具体原话但句法词义歧义：原 `unresolved + relevant=True` 保留（例如农户/蔬菜反例）；无类型事实升级。
- 缺POS资源或超4096/1024：原 `assessment_complete=False`、financial轴None、公开deferred/partial及unit/reason仍保留；不能伪装“没有业务”。正常纯财务完整可跳过。R4/R5真实selector/handler反控全绿。
- `_PAGE_NAME`是“页码 + 法定组织名称后缀 + 无句子终结”的来源格式，不是公司名单；不读用户公司池、不识别issuer。复用ISSUER_WORD只判纯客套的语法前缀，从不作为经营事实或身份通行门。生僻公司名、铁路/运输/诊疗/种植等正例不依赖该词。

## 计量、性能和身份

- 新owner进入实际 `business_algorithm_hashes(pdf_frontend=True)` 的AST闭包，未手工补全仓hash；映射包含 `company_wiki.source_catalog.narrative_source_context`，值 `a3774789bd4c5064df90d050e4be8afc72cabb2de438def29f7ba1b8689420fd`。
- SOURCE_PASSAGE从24到 `24 + SOURCE_CONTEXT_SCAN_PASSES(12)`，新增最多按 `12 × 新评估source字符数` 预留；总上限仍**16M /112**，POS仍**32n+1、4096字符/1024 tokens**。没提高任何总额度。12是source-role regex输入访问的保守上包络，涵盖有界算术/name/meta guard、objective/principle/abstract/courtesy和已缓存矩阵补语，非CPU指令等价物。长度32/64/128实际计量线性；含原abstract/accounting owner的3个合成探针分别观察5.0、7.0、7.1429次输入访问。
- source clause context保存在SourceStatementScope；objective_operator直接复用，精确同scope的OBJECTIVE.search只有1次；相同矩阵的补语结果局部memo。5类已知metadata在任何POS回退前完成，重复Session访问不再扫描或补收费。逗号切出的新视图分别观察，不能借全句的objective/角色。
- 较早741项耗时36.51s，最终746项111.94s；offline fresh child 7.656→22.149s、首EN冷初始化4.254→7.167s、首CN1.349→7.092s，其他旧case也变慢。**原因未确诊**，不能把宿主并发猜测当性能结论，也不能声称无退化；按ROOT要求不重复整组。最终真实H1的16M/112召回/耗时仍须实测，可能因诚实新成本更早partial。
- grammar=`statement-grammar/3`、passage=`source-passage/7`。资源实际identity=`15ecddf9259146c37fc879a30e431efff95b54261c76d109e4d0de0248dc7873`，其中包含schema版本；原模型JSON/字典的字节没有改动或下载。没有新增API费用或按公司常驻资源。

## 可复现入口与范围

宿主 `C:/Miniconda/python.exe -B -X utf8`；工区 `C:/Users/郑曾波/Projects/company-wiki/tmp/architecture-r2`；`PYTHONPATH=src;tests`、`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`。pytest参数 `-p pytest_asyncio.plugin -q -p no:cacheprovider --tb=short`。最终13文件清单在工区 `tmp/r6-semantics-frozen.log`，完整JUnit在同名xml；各次artifact SHA、失败case与源码身份见同名JSON。

本线源码/新测：

| 路径（相对隔离工区） | SHA-256 |
|---|---|
| `src/company_wiki/document_understanding/statement_grammar/__init__.py` | `a067fcd5ce43e73a3c58cae866d1f2c497d9af29aa1633632b56618dbfad974b` |
| `src/company_wiki/source_catalog/narrative_source_passage.py` | `9a1e3f40c943e3c2155854ac85a9e71d44ebefa6211fa55e697b12ab70d50ca0` |
| `src/company_wiki/source_catalog/narrative_business_policy.py` | `9e44f1cf238db06ab84e24ac410cd49beb7620210ea4043bdb1c22786f7c8f77` |
| `src/company_wiki/source_catalog/narrative_source_context.py` | `a3774789bd4c5064df90d050e4be8afc72cabb2de438def29f7ba1b8689420fd` |
| `tests/unit/du11_production/test_source_semantic_axes.py` | `5469915187eedccc5747475fd5976639516417f0adc360511c66176a2735281f` |

## 待ROOT

集中独审并确认以上源码身份；其他owner迁移/CI诊断合流后，精确候选CI通过再并线。恢复真实H1、新摘要、缓存恢复和RF实际采用之前，不把746项工程绿称作整个项目或真实端到端验收完成。本线现已冻结，STOP，不再扩展源码、跑付费/真实公司、改PWF主文件或执行Git。
