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

## [2026-04-25 23:00] INFO collect_news | scheduler采集 115 篇新文章
- SHEIN: +7
- 七一二: +2
- 万华化学: +4
- 万润股份: +3
- 万科: +4
- 三七互娱: +3
- 三只松鼠: +4
- 三德科技: +3
- 三环集团: +4
- 三联虹普: +1
- 三角防务: +3
- 上峰水泥: +1
- 世华科技: +6
- 世茂: +3
- 东方雨虹: +5
- 东珠生态: +3
- 东睦股份: +3
- 中信建投: +6
- 中国巨石: +6
- 中国平安: +3
- 中国生物制药: +6
- 中大力德: +4
- 中望软件: +7
- 中直股份: +2
- 中航光电: +4
- 中航机电: +5
- 中航沈飞: +2
- 中航电子: +6
- 中航电测: +4
- 中航西飞: +1

## [2026-04-25 23:11] INFO collect_news | scheduler采集 128 篇新文章
- 中航重机: +2
- 中颖电子: +6
- 丸美股份: +5
- 久吾高科: +2
- 五芳斋: +6
- 京东: +6
- 京东方: +5
- 亿华通: +6
- 伊利股份: +2
- 优利德: +8
- 伟星新材: +1
- 信达生物: +6
- 元祖股份: +2
- 兆易创新: +4
- 光明乳业: +6
- 光线传媒: +6
- 八方股份: +2
- 共创草坪: +2
- 养元饮品: +5
- 凯赛生物: +4
- 分众传媒: +4
- 北新建材: +3
- 华住酒店: +7
- 华利集团: +4
- 华卓精科: +5
- 华铁应急: +4
- 华锐精密: +5
- 卓胜微: +0
- 博威合金: +5
- 双环传动: +5

## [2026-04-25 23:12] INFO collect_news | scheduler采集 99 篇新文章
- 北新建材: +3
- 华住酒店: +3
- 华利集团: +0
- 华卓精科: +0
- 华铁应急: +2
- 华锐精密: +3
- 卓胜微: +4
- 博威合金: +4
- 双环传动: +3
- 古井贡酒: +6
- 吉比特: +5
- 周大生: +0
- 哔哩哔哩: +2
- 国恩股份: +0
- 国检集团: +3
- 地素时尚: +4
- 坤彩科技: +1
- 埃斯顿: +2
- 大全能源: +5
- 天宜上佳: +5
- 天马股份: +6
- 奥普特: +5
- 奥来德: +5
- 好未来: +7
- 妙可蓝多: +4
- 字节跳动: +8
- 安博通: +5
- 安宁股份: +2
- 安杰思: +1
- 安集科技: +1

## [2026-04-25 23:14] INFO collect_news | scheduler采集 132 篇新文章
- 安杰思: +3
- 安集科技: +5
- 宋城演艺: +6
- 完美世界: +7
- 密尔克卫: +6
- 富森美: +5
- 小米集团: +2
- 尚品宅配: +3
- 山石网科: +4
- 广州酒家: +4
- 广联达: +7
- 康基医疗: +4
- 康拓医疗: +3
- 开润股份: +3
- 弘亚数控: +7
- 微创医疗: +6
- 德林海: +7
- 德赛西威: +4
- 快克股份: +5
- 快手: +6
- 恒锋工具: +4
- 恩华药业: +2
- 惠泰医疗: +4
- 拓尔思: +4
- 拓斯达: +6
- 拼多多: +4
- 新产业: +6
- 新华保险: +3
- 方大特钢: +0
- 方邦股份: +2

## [2026-04-25 23:14] INFO collect_news | scheduler采集 80 篇新文章
- 宋城演艺: +0
- 完美世界: +2
- 密尔克卫: +4
- 富森美: +0
- 小米集团: +0
- 尚品宅配: +0
- 山石网科: +2
- 广州酒家: +6
- 广联达: +6
- 康基医疗: +4
- 康拓医疗: +1
- 开润股份: +0
- 弘亚数控: +0
- 微创医疗: +4
- 德林海: +0
- 德赛西威: +1
- 快克股份: +6
- 快手: +3
- 恒锋工具: +4
- 恩华药业: +4
- 惠泰医疗: +0
- 拓尔思: +2
- 拓斯达: +0
- 拼多多: +5
- 新产业: +6
- 新华保险: +6
- 方大特钢: +3
- 方邦股份: +1
- 时代天使: +7
- 时代新材: +3

## [2026-04-26 09:02] INFO query | Query answer saved: 测试问题？ -> 中微公司

## [2026-04-26 09:09] INFO query | Query answer saved: 测试问题？ -> 中微公司
