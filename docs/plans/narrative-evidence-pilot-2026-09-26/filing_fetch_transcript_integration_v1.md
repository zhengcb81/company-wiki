# Filing Fetch × Earnings Transcripts × Company Wiki（v1 草案已退役）

> **状态：按旧权限设计编写的草案已整体退役。** 弱模型不得照本页旧流程重建逐期用户授权、双阶段下载审批、provider rights hash policy 或人工签字。现行集成只按跨仓总计划 §2.1/S4b 实施。

## 当前契约摘要

- 在明确公司/证券与 fiscal year/quarter 的 filing-fetch 采集请求中，自动追加该准确期次的 earnings-transcripts 请求；不把全年年报猜为 Q4。已有原始 transcript 时先按身份/期次/hash 复用。
- 调用现有可用的 earnings-transcripts 工具一次。工具/API 的直接技术错误、凭证或服务限额照实返回；不追加 CWP 自建的多层授权和 provider rights policy。
- TXT 保持原语言，不翻译，不走 PDF 转录；canonical 原文由 company-wiki 统一保存一次，附原件 SHA、来源身份和取得时间。
- 摘要、选择证据及 locator 由 company-wiki 自动处理；确定性校验负责身份、期次、SHA、引用、locator 和输出 schema。无法确认时标为 skip/partial/error 并给原因，不进入人工审批队列。
- filing 与 transcript 分项返回状态。filing 成功不因 transcript 失败回滚；重试不生成重复原件。
- 一次隔离 E2E 覆盖真实 filing-fetch 编排、真实 CWP importer 和 ET tool 边界（provider 用 fake HTTP）：成功、复用零下载、未请求/期次歧义零网络、身份/期次漂移、坏 payload/超限、filing 成功而 transcript 失败、原语言 TXT/locator 回读及测试目录恢复。

本页保留为历史链接兼容文件。原 v1 的阶段记录与 provider 调查见 progress.md / findings.md；测试和放行规则以当前总计划为准。
