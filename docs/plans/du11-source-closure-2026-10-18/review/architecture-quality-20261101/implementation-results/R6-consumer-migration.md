# R6 旧接口与消费者迁移收口（作者短域PASS，待ROOT独审/整合CI）

2026-11-01。工区`C:/Users/郑曾波/Projects/company-wiki/tmp/architecture-r2`，分支`codex/architecture-rectification-r2-20261101`，起点`f298a383`。读取主PWF `CWP-failed-CI.md`后按实际41个RED归并责任。**本线只修改5个测试文件，产品源码0变更、代理0新增**，未修改主PWF/索引、commit、合并或部署。

## 重现、根因与处置

| 组 | 原失败 | 已确认责任与改法 | 保留的行为断言 |
|---|---:|---|---|
| narrative source usability | 30 | 公共旧trace函数仍由DU薄兼容提供，但测试在DU shim找私有`import_module`；将注入点移至真实`source_catalog.narrative_decision_inventory`，公共调用仍走原compat验证 | 真实不同parser的matcher、原文可用性源码变化失效、同代码移安装位置/CRLF不变、其他carrier matcher不影响、旧歧义trace拒缓存 |
| CF3 algorithm identity | 1 | 私有`_structure_algorithm_hashes`已归source组合owner，测试直接该owner，未为其恢复DU反向接口 | 新结构子模块影响身份、无关txt不影响、host目录变化不影响；另强化真实generation cache比较见下 |
| canonical import reference | 4 | writer已从高层SourceVersionReader退到精确identity投影，旧测试mock的高层reader不再调用；用仅有`exact_source_version`的窄reader替身，实际运行`query_source_reference` | exact查询恰1次；真实缺行/错SHA/非active行均拒，抛CanonicalImportError且cause.reason保持；不搜索metadata、不用capture许可 |
| native list ancestry | 4 | 语法谓词已归`operating_states.relations`，测试改从该owner取`independent_statement_start`，不在reading facade加alias | 原unfinished/带furniture需要句子闭包，terminal/unknown-column不凭列表邻接造连续；真实结构/选择/模型编译不变 |
| missing PDF projection | 2 | 测试patch DU shim并`raising=False`，注入的是未使用的新属性，无法模拟真实组件缺失；改patch真实source inventory owner，去掉phantom patch | 模块缺失/版本缺失均不能声称完整PDF，HTML保持相同 |

没有删/放宽旧行为断言、提高预算、扩数据字段或新增人工门禁。四个legacy公开值/trace合同仍沿实际薄兼容使用；私有模块局部变量/函数的位置不作为跨层API恢复。

CF3第一例增加真实端到端身份链：实际pipeline→`build_decision_trace`→`freeze_decision_dependencies`→真实`current_reading_decision_matches`，初始complete/same必须True；模拟关系算法源码变化后，原business digest必须变，真实generation cache比较必须False。不是只证明私有函数换了名字，也未冒称运行了真实Store/付费缓存恢复。

canonical四例不直接mock投影函数返回/抛错：返回窄端口真实row，让现有source/version/active验证自己决定；成功结果为原SourceRef，3个失败原因必须真实匹配。该替身没有高层metadata/reader API，倒退为高层循环会自然失败。

## 命令和结果

宿主`C:/Miniconda/python.exe -B -X utf8`，`PYTHONPATH=src;tests`。先跑下列原测试目标：

```text
pytest tests/unit/test_narrative_source_usability_dependencies.py
       tests/unit/test_cf3_algorithm_identity.py
       tests/unit/test_canonical_import_reference.py
       tests/unit/document_understanding_selection/test_reading_native_list_ancestry.py::test_existing_sentence_page_flow_is_not_replaced_by_list_continuation
       tests/unit/document_understanding_selection/test_reading_value_coverage.py::test_missing_pure_projection_component_cannot_claim_complete_pdf
       -q --disable-warnings --tb=short
```

- 原始RED：**41F/9P/2warnings，69.75s**；不是41个独立产品缺陷。
- 同50目标迁移及CF3强化后：**50P/2warnings，40.62s**。测试期间由语义作者暂时冻结其owner文件，防止合法算法变化让正在比较same的测试抖动；结束已通知其恢复。
- Ruff五改动测试PASS。产品源码0变更，不为此重跑全部mypy/full unit/模型/E2E。
- CodeGraph主索引仍反映旧canonical writer，用当前工区已知文件核对source_references实际实现；没有初始化第二索引。读文件工具一次输出被截断，之后只读取必要段落，不把截断当执行失败。

## 冻结与交接边界

`R6-consumer-migration.json`列出5个改动测试的完整SHA、目标和结果。只冻结本线文件，不冒称并行语义/ROOT migration/offline修改已冻结或整合通过。

本线未读凭证、运行公司、下载/解析真实原件、调用模型、写生产配置/DB、改主PWF/其他owner测试或RF。临时数据沿原pytest临时夹具，CF3临时目录由原TemporaryDirectory恢复；未复制生产资料。

ROOT后续集中独审和PR精确CI才可签整合PASS；旧失败CI与41F证据保留。RF957c6283与其已绿CI无需本线再改/部署。作者到此STOP，不启动全unit或付费原公司循环。
