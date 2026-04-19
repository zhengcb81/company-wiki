# Dataview 查询示例

在 Obsidian 中安装 [Dataview](https://blacksmithgu.github.io/obsidian-dataview/) 插件后，可在任意 .md 文件中使用以下查询。

## 最近更新的 Wiki 页面

```dataview
TABLE last_updated AS "更新日期", sources_count AS "来源数", type AS "类型", entity AS "实体"
FROM "companies" OR "sectors" OR "themes"
WHERE last_updated
SORT last_updated DESC
LIMIT 30
```

## 按公司查看所有 Wiki 页面

```dataview
TABLE type AS "类型", last_updated AS "更新日期", sources_count AS "来源数"
FROM "companies"
WHERE entity
SORT entity ASC, type ASC
```

## 按标签查找

```dataview
LIST
FROM #半导体设备
SORT last_updated DESC
```

## 来源数量 Top 20

```dataview
TABLE entity AS "实体", type AS "类型", last_updated AS "更新日期"
FROM "companies" OR "sectors" OR "themes"
WHERE sources_count >= 10
SORT sources_count DESC
LIMIT 20
```

## 各类型页面统计

```dataview
TABLE length(rows) AS "页面数", sum(rows.sources_count) AS "总来源数"
FROM "companies" OR "sectors" OR "themes"
WHERE type
GROUP BY type
SORT length(rows) DESC
```

## 长期未更新的页面（超过 30 天）

```dataview
TABLE entity AS "实体", type AS "类型", last_updated AS "最后更新"
FROM "companies" OR "sectors" OR "themes"
WHERE last_updated AND date(today) - date(last_updated) > dur(30 days)
SORT last_updated ASC
```
