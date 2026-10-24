# W08 跨页共享观察与公共读取：独立终审

**结论：本有限工程节点 PASS；未签公司全内容通过。** 独立13例全部通过，ROOT集中自然包2121通过/11既有跳过，失败与错误为0。本人未参与产品实现，source/test/Git写入0，网络/模型调用0。

## 绑定与实际执行

基线HEAD为`7b1c015b03edaf72f86fbf6527e44450ab5f7088`加有意工作树改动，不能将基线HEAD说成最终代码。最终freeze文件：`C:\Users\郑曾波\Projects\company-wiki-r1-local-observation\docs\plans\r1-final3-source-semantics-20261022\resume\cross-page-root-20261024\root-composed-v3-freeze.json`，SHA256 `a5d822e7a0cc4677563cc3cf5dbeb604683e5d7deb008e8fcc1fad4c0892fb40`。全部source/test准确SHA与前后守恒见report.json及independent-execution-v3.json。原9测试SHA仍为`b8878d3c5734aa73f0dc61553d8fb7feb40e152ad51d6efc71a6a12b80d3b6e0`；原77/20/24、semantic_value、scope、multi-target组合由完整自然包覆盖，没有删除oracles。

独立脚本原13case字节SHA `8484f3b815a9b4a0c678f486117e5c22b41ff10ef418211160ea2980ebcab239`；通过真实`_understand→select→citation→model`，输入只有原native observations，未注入parent/sections/包或模型结果。实际执行收据：independent-execution-v3.json；ROOT自然包收据：`C:\Users\郑曾波\Projects\company-wiki-r1-local-observation\docs\plans\r1-final3-source-semantics-20261022\resume\cross-page-combined-20261024-v3-final\receipt.json`，独立读取核对，未重复大全包。

## 覆盖与根因质量

- 一个call-local NativeSourceContext供sections和reading复用；公共执行按原ID计数最多1次物理观察，JSON无Python对象。原column、frame/font/lane/order/coverage和真实页序继续决定物理边。
- sections独占业务parent/intro，Roman大小写与glyph同语法；公共事实自己的parent/intro进入citation及模型，sibling不串入。独立完整的前一业务bullet只作结构见证时，其无关数字未自动入下一target模型；source proof原ID、页序、edge端点和两条家具仍保留。
- 同ID真实语义责任不会被proof标签消除：英文与繁体跨页限制确实进入对应事实的citation/model。真超2048材料延期、unknown栏位不造跨页父级、missing/foreign/wrong-page proof诊断、零工作账不输出证据均实测通过。现有96/48000、16M、8units/4blocks/2048原字符及list两页/members+skip24不变；旧未完句不套新增24限制。
- 订单中/繁/英实际变化、未来`to increase`、裸infinitive、否定与金融余额反控通过。policy保持17，legacy源码SHA `3cef483033d1b54e4fe6aa908cfd129fc3d370bdd5b89f915eac12cb47fc92cb`不变。
- pipeline/structure/sections/native helper/text_view五个owner逐项scoped read_bytes反控均使现有cache算法身份变化，恢复后身份相同；从未改真实源码字节或备份源码树。

原失败保留：V1自然包63F/1908P/11skip，其中42是generic公开输入被新增属性要求破坏，19是空diagnostic污染输入，2是sparse checkout缺tracked策略JSON。修复复用既有adapter source信息并让诊断随结果返回；缺资产按同HEAD恢复，不改测试。V2独立12P/1F找到英文复数产品被分类为actor而丢真实限制；共同语义owner修后原13例复验通过，原失败和诊断JSON保留。声明标记修复保持原offset、真实分隔及不同主语边界，未加reading设备特判。

## 业务验收边界与恢复

保留的V2真实249页/5647units回放，96条/8518字符，同16M账用8,630,449，两个自身业务归属检查通过、无sibling污染；仍partial且whole_content=false。该历史真实回放不能代签最终V3全内容，更不能代签收费摘要、live cache恢复、RF预测/四审或整个R1完成。

本审查仅写自有目录。未创建pytest/Temp根，无需删除；Python -B避免字节缓存，scoped monkeypatch退出即恢复。cleanup.json记录执行前后实际源码SHA与0外部调用；不宣称其他任务临时目录或全仓已清空。

## 最终源码SHA

| 文件 | SHA256原字节 |
|---|---|
| src/company_wiki/document_understanding/narrative_continuity.py | `3ed9d08ba8c8d7cdfe0bbb5dbed1817803b395e41531e69660e659004150dd46` |
| src/company_wiki/document_understanding/observation_adapter.py | `66bd55c80e6d07f0a752ab3787f9fdbb04270b16491da36ef4a3b9d21564c8e4` |
| src/company_wiki/document_understanding/pipeline.py | `46d3cbd934bbada230eb384d6122230f1efb00bda8120707bad4796175207020` |
| src/company_wiki/document_understanding/structure/__init__.py | `166b9215ce5d5e9a40916a0ee7a6171ff7e51152051d4b1caa5a28e891254bbf` |
| src/company_wiki/document_understanding/structure/sections.py | `dacb853d631ee328b4c3d518b638428c01068d32852dbdf0dea435fbc77faf16` |
| src/company_wiki/document_understanding/structure/contract.py | `e653137a48f287928fc9e8784dd00a562194c8abda57ab27af192f19b6cd1b5a` |
| src/company_wiki/document_understanding/decision_inventory.py | `85630848914f0487020ea3f41d395a9dff2ffb9d37cfd6b382fb045a3f260676` |
| src/company_wiki/source_catalog/narrative_reading.py | `be21d48f7970861ebb1f9403b3f259d935cbea82a3f2b194979f23be1ccf163f` |
| src/company_wiki/source_catalog/narrative_native_dependencies.py | `07f063af239325c54af6928d3448bd1f76775d1b16a4abcbad10ad67d62cf76c` |
| src/company_wiki/source_catalog/narrative_predicate_state.py | `2ed1433ec5b227528bd5fad4083a7df642ca87bdb86a524d9ab092b6648e7460` |
| src/company_wiki/source_catalog/narrative_business_policy.py | `1efe57913a98b92803c33c0349c656bd495ce171645c698c43f6eb214743007b` |
| src/company_wiki/source_catalog/narrative_operating_relations.py | `c98cd4cc4371b43d314e6ffbcca2b61947b146128cb569bfd226dc3f3da2b142` |
| src/company_wiki/document_understanding/operating_states/text_view.py | `240ca4e89b78c4dfa96618c850d4448db12cd50d198e3f85d775c5ac86621914` |
| src/company_wiki/document_understanding/operating_states/relations.py | `ae047f44521fccc7f640e6b80fbfe945af41002181c8749f6596dae5a36e188d` |
| src/company_wiki/document_understanding/operating_states/patterns.py | `28a5f7f20f9c2cde99564eeb288605b694979080c9df69419c8375ffca35a380` |
| src/company_wiki/document_understanding/operating_states/product_reference.py | `7e5d0ccb0b85342081578a9c37e927835ccab6b21bb2aacebddeafe53ebd43d7` |
