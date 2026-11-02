# D3发布记录

D0–D3[独立工程验收通过](independent/review.md)。这份记录区分本地工程测试、已部署版本与远端CI。

| 仓库 | 代码版本 | 发布 |
|---|---|---|
| company-wiki | 本次ROOT实现提交 | 主线推送与精确CI待记录 |
| revenue-forecast | `f09755277473168fa439b77e6b4c1fa4af44a802` | main本地，待推送 |
| filing-fetch | `2f115c29dec4d52c1c41cf485b50dc2ab6eb169c` | main本地，待推送 |
| StockWiki | `d8d3303cb4b91fb6bfc8db6202ea3919276f833e` | 本地master，无remote；提交钩子的import排序已修正并通过 |
| earnings-transcripts | `003c1c065109d0b02c7bd4de09ad3e8461a99c0e` | 复用既有源码，仅隔离与组合验收 |
| revenue-forecast-audit | `a84455ef864d6f9e5596a894c2b1801d8ea32cfb` | 既有源码通过隔离；本地仓，无remote |

本地证据根：`.planning/decoupling-implementation-20261102/`，包含system-final、version-supplement、各独立log、real-read-only、deployment/installed-execution。仅紧凑的独审与发布记录提交，测试原文、临时湖、实际配置和旧run不提交。

生产资料不改、真实provider和模型调用0。部署只定点RF6/FF8个文件到三个逻辑技能入口，重复零写并实测。旧RF日检由遗留调度维护，未纳入当前CI或发布许可；其初始日志保留，未暂存。技术边界通过，原T4/SEM和真实公司链未签业务完成。
