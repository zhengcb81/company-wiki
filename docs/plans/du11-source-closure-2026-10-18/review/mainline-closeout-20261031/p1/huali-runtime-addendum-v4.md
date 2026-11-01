# P1 华利组件最终独审增补

组件代码/语义/恢复审查通过，P1整体仍OPEN，P2不代签。

收据小问题P1-RECEIPT-01已闭合：旧收据不动，新correction-v3明确撤回“0 PDF parse”，改为无新来源选取、实际执行locator回放、调用数未仪表化/null；同body、generation和收费事实不变。

新增guard合理：优先保留既有exact-byte可用性证据，已有责任层检查完整Ref及非未来时点。显式intake首次才新增真实current-open，普通preview仍不写；未知publication不捏造历史日期。新增参数例验证更早证据不被今天覆盖。未新增许可门禁，也未重复跑整批或收费。

当前代码SHA：

- `tools/document_understanding_benchmark/phase_c_readonly_source.py`：`ce31b57e1661a8991cff0c92c73cbebf013ac2e2158ea9de91ece0aea5c132e7`
- `tests/test_phase_c_readonly_source.py`：`0ffe11af757d6a496919ec0164ee77909d691d2d28185701ecd02e5eeb67e2dc`

附带发现P1-PACKAGING-01：证据包manifest的24项中16份text仍绑定LF规范化前的CRLF SHA/字节数；已逐项证明全为换行差异。ROOT只需在规范化和复制最终审查后重建manifest，无须重跑模型/测试。8份其余文件校验正确。修复情况以其后独立逐项manifest核对为准。

继续保留Berkshire 0POST/重要材料未处理、全文partial、/5仅排名原文卡、P2时间限定与实际公式采用尚未验收等边界。
