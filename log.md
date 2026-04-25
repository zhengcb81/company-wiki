# 知识库操作日志

> Append-only 日志，记录所有 ingest、query、lint 操作。
> 格式：`## [YYYY-MM-DD HH:MM] {LEVEL} {操作类型} | {描述}`

## [2026-04-23 22:43] INFO collect_news | scheduler采集 16 篇新文章
- 寒武纪: +16

## [2026-04-23 22:52] INFO ingest | scheduler处理 40 文件, +109 条目, 0 错误

## [2026-04-23 22:53] INFO lint | scheduler矛盾检测: 1366522 潜在, 0 高置信度

## [2026-04-23 22:53] INFO enrich | scheduler投资判断: 1 公司

## [2026-04-23 22:53] INFO scheduler | 调度周期完成
- elapsed=631s
- collect=+16
- ingest=40/109
- assess=+0
- detect=0high
- distill=+0entries
- judgment=1companies

## [2026-04-24 22:57] INFO evolve | scheduler schema进化: 8 指标, 建议 424 chars

## [2026-04-24 22:57] INFO scheduler | 调度周期完成
- elapsed=7s
- schema_evolve=8metrics/424chars

## [2026-04-24 23:26] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 07:31] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 07:31] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 07:32] INFO collect_news | scheduler采集 19 篇新文章
- 北方华创: +19

## [2026-04-25 07:32] INFO scheduler | 调度周期完成
- elapsed=8s
- collect=+19

## [2026-04-25 07:49] INFO scheduler | 调度周期完成
- elapsed=0s
- assess=+0

## [2026-04-25 07:50] INFO enrich | scheduler投资判断: 1 公司

## [2026-04-25 07:50] INFO scheduler | 调度周期完成
- elapsed=0s
- judgment=1companies

## [2026-04-25 07:52] INFO lint | scheduler矛盾检测: 200 潜在, 0 高置信度

## [2026-04-25 07:52] INFO scheduler | 调度周期完成
- elapsed=78s
- detect=0high

## [2026-04-25 07:52] INFO scheduler | 调度周期完成
- elapsed=0s
- distill=+0entries

## [2026-04-25 07:52] INFO enrich | scheduler投资判断: 233 公司

## [2026-04-25 07:52] INFO scheduler | 调度周期完成
- elapsed=0s
- judgment=233companies

## [2026-04-25 07:53] INFO enrich | scheduler补全 3 页评估

## [2026-04-25 07:53] INFO scheduler | 调度周期完成
- elapsed=33s
- assess=+3

## [2026-04-25 07:54] INFO distill | scheduler蒸馏 3 行业, +9 条目

## [2026-04-25 07:54] INFO scheduler | 调度周期完成
- elapsed=81s
- distill=+9entries

## [2026-04-25 07:56] INFO lint | scheduler矛盾检测: 200 潜在, 0 高置信度

## [2026-04-25 07:56] INFO scheduler | 调度周期完成
- elapsed=90s
- detect=0high

## [2026-04-25 07:56] INFO evolve | scheduler schema进化: 8 指标, 建议 473 chars

## [2026-04-25 07:56] INFO scheduler | 调度周期完成
- elapsed=10s
- schema_evolve=8metrics/473chars

## [2026-04-25 08:35] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 09:31] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 09:32] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 09:32] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 09:32] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 09:33] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 09:33] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 09:38] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 10:24] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 10:25] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 10:27] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 11:05] INFO enrich | 知识压缩: 19 页面, 19833 -> 4191 行

## [2026-04-25 11:41] INFO query | Answer filed as concept page: 中微公司的竞争优势是什么 -> themes\中微公司的竞争优势是什么\wiki\中微公司的竞争优势是什么.md

## [2026-04-25 13:21] INFO consolidate | 压缩 33 个页面, 总行数 17765 -> 9538, 压缩率 46.3%

## [2026-04-25 13:52] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 14:29] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 14:31] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 14:32] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 14:32] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 14:33] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 14:33] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 14:33] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 14:34] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 14:41] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 14:47] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 14:48] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 15:27] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 16:45] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 16:46] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 18:10] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 18:11] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 18:14] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 18:15] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 18:17] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 19:57] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 20:02] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 20:03] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 20:09] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 20:32] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 20:44] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 21:23] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 21:25] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 21:43] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 21:50] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 21:53] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 21:58] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 21:59] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 22:01] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 22:01] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 22:02] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 22:03] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-25 22:05] INFO query | Query answer saved: 测试问题？ -> 中微公司
