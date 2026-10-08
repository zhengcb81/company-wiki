# 来源资格与入库身份责任：第一集中节点

日期：2026-10-08。状态：责任测试通过，冻结版本三市场 E2E 待运行。该状态不表示整个门禁简化或 Phase6 已完成。

## 实际改造

- writer 的存储结果改为 schema2 `SourceRef`，没有完整语义 resolve、日期专用身份签收或旧 metadata 标题搜索；原文 sidecar 仍为 schema1。
- 查询已归属公司的原文时，辅助 market/security 缺失只诊断；明确错误的候选仍被排除，可以继续获取正确来源。
- coordinator/writer 共用公司规范化、请求范围和响应绑定比较；不创建许可标记。直接 writer 仍拒绝错公司/错期间/错 receipt，未指定市场不构成冲突。
- 普通年报与 TXT 一样允许未知公开日保存；历史查询仍不能假称未知日已公开。未知日原件删失可以恢复，恢复后再次请求不重复下载。
- query/resolve 显式返回被历史日期排除的逻辑引用及资格观察；DB-only 不冒称字节已验证；当前摘要元数据修正不重新付费生成。

## 验证证据

| 节点 | 结果 | 秒 |
|---|---|---:|
| 新18项责任测试，改造前 | 8真实RED、10PASS | 11.84 |
| 补充 writer无语义查询/未知日年报/冲突候选 | 3真实RED | 3.82 |
| 第一88项集中 | 86PASS/2FAIL，fixture与stage顺序均修正 | 14.33 |
| 更广261项 | 259PASS/2FAIL，stage顺序及过期HTTP测试要求 | 85.29 |
| HEAD旧resolver HTTP对照 | 同一旧测试真实FAIL；不是本次回归 | 0.97 |
| 公开v2/envelope/原文/CLI/Worker/并发集中 | **300PASS** | **106.36** |
| 未指定市场额外责任 RED | 1RED/5PASS，新 helper 误把 None 当冲突 | 2.26 |
| 共用范围、全部 writer、single-intent 联调 | **49PASS** | **15.10** |

最后49项是针对最后实际风险的补充，和300项有重叠，不宣称总计349个独立用例。大节点没有调用外部 LLM；供应商调用为明确 fixtures/本机子进程。生产原件与 source_catalog 配置写入0。

责任集中命令：

```powershell
python -B -m pytest tests/unit/test_source_qualification.py tests/unit/test_canonical_import_reference.py tests/contract/test_source_qualification.py tests/integration/test_source_qualification_e2e.py tests/contract/test_source_catalog_resolver.py tests/contract/test_source_catalog_latest_mode.py tests/contract/test_source_version_reader.py tests/contract/test_source_version_reader_cli.py tests/unit/test_source_facts.py tests/integration/test_narrative_transport.py tests/contract/test_single_intent_latest_acquisition.py tests/contract/test_source_catalog_canonical_writer.py tests/contract/test_source_catalog_acquisition.py tests/contract/test_source_catalog_identity_resolver.py tests/contract/test_strict_identity_fc702.py tests/contract/test_fc1301_reason_taxonomy.py tests/unit/test_stage_taxonomy.py tests/contract/test_resolution_envelope_fc704.py tests/contract/test_source_operation_v2.py tests/contract/test_canonical_ingest_service.py -q -p no:cacheprovider --basetemp=tmp/p1identity-final
python -B -m pytest tests/unit/test_acquisition_scope_responsibility.py tests/contract/test_source_catalog_canonical_writer.py tests/contract/test_single_intent_latest_acquisition.py -q -p no:cacheprovider --basetemp=tmp/p1scope-green
```

正常 OS 执行；此前默认沙箱的子进程/原子 prepare 失败已经在正常 OS 相同断言全部通过，不作为产品缺陷。ruff全部改动文件通过；mypy五个责任模块通过。commit仍只跑原有轻静态检查，CI没有新增真实下载或收费调用。

## 明确保留的下一工作

[责任收敛方案](identity_responsibility_simplification.md) 的“连续下一节点”仍待实现：全局元数据争议门、formal身份/期间状态、自动旧runtime许可、Transport重复检查、latest未知日期分流。官方发布日期真实性、新格式Worker、RF输入/消费及两组三家公司完整新研究也未完成。

清理证据见 identity_responsibility_cleanup.json；只删除列名的owned测试根，三外包工作树和原件保留。三市场报告完成后补精确commit及同模式compare，不改原基线。
