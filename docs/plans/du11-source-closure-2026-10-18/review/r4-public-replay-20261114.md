# R4 半年报公开回放基线

2026-11-14。样本 `r4-cn-h1-real` 是既有冻结半年报，SHA-256 `d0dba19ede6e35ae3e127a1da91a42f04262e90d14efeb847bdfbff9b6354a5f`，1,216,470 字节。保留此前 [9/12 与工作量分诊](../current-main-replay-20261110/README.md) 作为历史对照。

## 验收入口

回放经正式 `NarrativeSelectHandler`，以 `SourceVersionReader.open_described_version` 公开端口取经过验真的字节和来源描述。阅读 owner 在同一次选择中产生独立观察快照。选择、文件快照和报告分别归其 owner，回放调用不会改写类、私有函数或选择会话。工作量仍使用同一个配置账户。

从公司资料仓运行 `python -B -X utf8 -m tools.source_case_runner --manifest <现有冻结cases.json> --case r4-cn-h1-real --original-file <匹配SHA的冻结测试原件> --output <全新临时目录>/r4.json`。原 manifest 位于 `.planning/architecture-quality-20261101/real-acceptance/cases.json`。测试原件可用 `.planning/shared-reading-production/r1-holdout-20261021/CN-603259` 下同 SHA 的既有本地件。显式指定的原件只读且前后核 SHA，路径不会交给来源读取端口，也不用于选择。没有独立指定文件时，文件前后对照为未知。文件不匹配时保留读取诊断，工程验收失败。

## 实际结果

| 指标 | 观察 |
|---|---|
| 冻结目标 | 12/12 原文已解析并选中，112 个 spans，101 个有效原始成员 |
| 引用闭合 | 68 个组与引用视图，零引用缺失，零错误原始成员 |
| 本地工作 | 15,996,656 / 16,000,000，exhausted=true，来源整体处理仍 partial |
| 只读与恢复 | 原件同 SHA、DB 字节相同、源码及观察器同签名，零下载/模型请求，隔离目录恢复为不存在 |
| 定向回归 | 53 项通过。实际文件匹配、未指定、无关文件、空证据、材料校验失败诊断及预算隔离均覆盖 |
| 独立审查 | PASS。已修复空证据被标为完成回放及验证失败丢失已观察工作量、片段和诊断两项问题 |

真实回放 11.85 秒。选材摘要 SHA-256 为 `3520a72cd9f817a5c068bf86699d90e2bf55008f972b5638a80124d1ff5d8fa9`，临时完整收据 378,372 字节，归一检查后已清理。用于后续比较的下一步为同一 16M 下按实际扫描归账，同时保留真实耗尽时的部分输出及限定。暂无付费摘要、缓存恢复或公司层验收结论。
