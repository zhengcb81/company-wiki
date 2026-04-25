---
title: "公司概览"
type: overview
last_updated: "2026-04-21"
---

# 公司概览

> 本页面使用 Dataview 插件自动生成，展示所有跟踪公司的最新动态。

## 最近更新的公司

```dataview
TABLE entity as 公司, last_updated as 最后更新, sources_count as 来源数
FROM "companies"
WHERE type = "company_topic"
SORT last_updated DESC
LIMIT 20
```

## 按来源数排序

```dataview
TABLE entity as 公司, sources_count as 来源数, last_updated as 最后更新
FROM "companies"
WHERE type = "company_topic"
SORT sources_count DESC
LIMIT 20
```

## 待处理问题

```dataview
TASK
FROM "companies"
WHERE !completed
GROUP BY file.link
```
