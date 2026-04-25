---
title: "近期更新"
type: overview
last_updated: "2026-04-21"
---

# 近期更新

> 本页面展示最近 7 天内更新的 wiki 页面。

## 今日更新

```dataview
TABLE entity as 实体, type as 类型, sources_count as 来源数
FROM "companies" OR "sectors" OR "themes"
WHERE last_updated = date(today)
SORT sources_count DESC
```

## 本周更新

```dataview
TABLE entity as 实体, type as 类型, last_updated as 更新日期
FROM "companies" OR "sectors" OR "themes"
WHERE last_updated >= date(today) - dur(7 days)
SORT last_updated DESC
```

## 本月更新

```dataview
TABLE entity as 实体, type as 类型, last_updated as 更新日期, sources_count as 来源数
FROM "companies" OR "sectors" OR "themes"
WHERE last_updated >= date(today) - dur(30 days)
SORT last_updated DESC
```
