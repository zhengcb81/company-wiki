---
title: "行业概览"
type: overview
last_updated: "2026-04-21"
---

# 行业概览

> 本页面使用 Dataview 插件自动生成，展示所有跟踪行业的最新动态。

## 最近更新的行业

```dataview
TABLE entity as 行业, last_updated as 最后更新, sources_count as 来源数
FROM "sectors"
WHERE type = "sector_topic"
SORT last_updated DESC
```

## 按来源数排序

```dataview
TABLE entity as 行业, sources_count as 来源数, last_updated as 最后更新
FROM "sectors"
WHERE type = "sector_topic"
SORT sources_count DESC
```

## 产业链导航

见 [[companies/_产业链导航|产业链导航图]]
