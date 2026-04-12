# 上市公司知识库 — Schema（维护规范）

> 这份文件定义了 LLM 维护此知识库时应遵循的行为规范。
> 所有 ingest、lint、query 操作都应参考此文件。

## 项目概述

这是一个基于 LLM Wiki 模式的上市公司研究知识库。
- 知识以 markdown 文件形式持久化在文件系统中
- LLM 负责整理、更新、维护 wiki
- 人类负责提供数据源、指导方向、审核结果

## 目录规范

- `companies/{公司名}/` — 公司所有原始文档（新闻 .md、财报/研报 .pdf 直接存放）
- `companies/{公司名}/raw/` — （可选）旧版按类型分的子目录，新文件直接存公司根目录
- `companies/{公司名}/wiki/` — LLM 生成的主题时间线文档
- `sectors/{行业名}/raw/` — 行业原始文档
- `sectors/{行业名}/wiki/` — 行业 wiki 页面
- `themes/{主题名}/` — 跨行业主题信息
- `config.yaml` — 全局配置（公司列表、问题清单等）
- `index.md` — 全局索引
- `log.md` — 操作日志（append-only）

文件来源：
- `collect_news.py` → 新闻存入 `companies/{name}/raw/news/*.md`
- `StockInfoDownloader` → 财报/研报直接存入 `companies/{name}/*.pdf`
- `ingest.py` → 扫描 `companies/{name}/` 下所有非 wiki 文件

## Wiki 文档格式

每个 wiki 文档必须包含：

### Frontmatter（YAML）
```yaml
---
title: {文档标题}
entity: {所属实体名}
type: company_topic | sector_topic | theme_topic | overview
last_updated: YYYY-MM-DD
sources_count: N
tags: [tag1, tag2]
---
```

### 核心问题
列出本文档跟踪的核心问题，这些来自 config.yaml 中对应 topic 的 questions。

### 时间线
按时间倒序排列条目，每个条目格式：
```
### YYYY-MM-DD | {来源类型} | {标题}
- 要点1
- 要点2
- [来源说明](../raw/{path})
```

来源类型包括：财报、公告、研报、新闻、投资者关系

### 综合评估
对该主题的阶段性总结和判断，用引用块格式。

## Ingest 规则

1. **读取新文件**：从 raw/ 目录读取新到达的文档
2. **判断相关性**：对照 config.yaml 判断该文档影响哪些 topics
3. **更新时间线**：对每个相关 topic，读取现有 wiki 文档，按日期插入新条目
4. **双向更新**：一条新闻可能同时影响公司 wiki 和行业/主题 wiki，都要更新
5. **更新 frontmatter**：修改 last_updated 和 sources_count
6. **记录日志**：在 log.md 中记录本次 ingest
7. **更新索引**：如有新增页面，在 index.md 中添加

## 时间线条目原则

- **精炼**：每个条目 2-5 个要点，不要复制原文
- **有判断**：不只是事实罗列，要指出这意味着什么
- **可追溯**：每个条目都要有来源链接
- **关联性**：如果与其他 topic 有关联，用 wikilinks 引用（如 [[AI产业链/大模型竞争]]）

## Lint 规则

定期检查以下内容：
1. 矛盾：不同页面之间是否有矛盾的陈述？
2. 过时：是否有页面长期未更新？
3. 孤儿：是否有页面没有被任何其他页面引用？
4. 缺失：是否有重要概念被提及但没有自己的页面？
5. 问题更新：哪些问题长期无新进展？哪些新信息没有对应问题？

## 进化规则

- 如果 ingest 时发现不属于任何现有 topic 的重要信息，创建新 topic 草稿
- 如果新闻频繁提及一个未跟踪的公司，建议用户添加
- 定期审查问题清单，标记过时的问题，建议新问题

## 使用的工具

- 文件读写：直接操作文件系统
- 搜索：ripgrep 搜索 wiki 内容
- 版本控制：git
