# ZIP fixture 独立定点验收

接受此 fixture-only 修复。精确 source 为 `ee293769037d0a9a205d75d15d64f0600929eaad`；未发现材料问题。

原 CI38105648234 的 Linux Python 3.12.15 日志只有两个旧完整 record 指纹断言失败，实际值 `63c83b5638f54e4454dd66e69fbd51b89cd5b69f8f2f9a1146298e87c64e7c97`。独立反例以同一 XML、顺序与时间戳重建 baseline：宿主 0 得到旧源 SHA `d428ad041147fb650671ee805c38a03539b4f28529a5516bce325cc3a8541761` 和旧指纹 `a6580fca5dcd6c063e2447bf5cf489aaabd8f61c52856646db744cb68d0031e4`；宿主 3 精确得到远端失败指纹。两者只有 5 个 ZIP creator-system 字节不同，各 XML payload SHA 均相同。

独立运行 4 个 probe case（baseline 0/3、fixed 0/3），另仅运行新增参数化 host 测试 2 项，全部符合预期。修复后两个模拟宿主输出字节彼此相等且逐字节等于封存 `evidence/docx-heading-implementation/legacy-original.docx`，仍为 2729 B、6 units，旧 SHA 和完整指纹保持。定位、单位 identity、metadata 集合与 replay 均通过。

与精确 source commit 的 AST 比较证明：原有所有函数（除 package 封套生成）及原有非函数语句未改，包括 complete-record serializer、旧 fingerprint、metadata、locator、replay、source mutation 拒绝与 parser/version 断言。新增原 SHA 常量与两宿主反例增强守卫；保护范围内 Git 唯一测试差异是 `tests/unit/test_docx_heading_normalization.py`。7 个产品源及 2 份配置的 SHA 与保存 GREEN 前后完全一致。

已核验原 RED/GREEN 日志 SHA：RED 1 fail/1 pass，GREEN 39 pass/0.74s；本次未重跑 39/3196/public E2E，未访问网络、公司审查材料或付费供应商。

**新精确 Linux CI 尚未由本审查观察，不能代签。** 本结论接受该 fixture-only 实施及局部证据，不宣称新远端 CI 已通过。

完整证据 SHA、4 probe case 与本次两宿主测试日志 SHA 见 review.json。

STOP
