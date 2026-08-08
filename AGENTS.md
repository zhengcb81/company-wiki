# 公司资料供应与来源智能平台 — Schema（维护规范）

> 这份文件定义了 LLM 维护 company-wiki 时应遵循的行为规范。
> 2026-07-16 起，本文件的“职责边界”高于下方 legacy Wiki 兼容规范；所有 collect、ingest、parse、index、query、export 操作都必须遵守该边界。

## 职责边界（最高优先级）

company-wiki 是 StockWiki 的上游来源系统，负责：

- 新闻、公告、财报、研报的发现与下载；
- immutable raw、去重、SHA-256、source manifest 和来源版本；
- 文档规范化、页码/段落/表格解析、EvidenceSpan 与 extraction quality；
- 全文检索、原文预览、带 `source_id + locator` 的资料型问答；
- 对上述来源/解析任务进行可恢复自动化，并提供只读、版本化 export。

StockWiki 独占投资研究语义和下游状态。company-wiki 不得生成或保存目标价、买入/卖出评级、仓位建议、估值/SOTP、正式研究报告或 accepted/rejected 投资结论；不得写入 StockWiki 的目录或数据库。`accepted` 若出现在上游，只能表示 source/extraction quality 通过质检，不能表示投资命题成立。

历史公司/行业/主题 Wiki 只作为只读兼容内容或 source-oriented projection 保留，不再是 canonical 产品目标，不得新增研究型 writer。

## 项目概述

这是一个面向上市公司资料的采集、不可变保存、规范化解析、证据定位、检索与导出系统。

- 原始资料及其 hash/manifest 是上游事实来源；
- LLM 可辅助解析与资料定位，但输出必须绑定 source ID、locator、parser/version 和质量标记；
- 人工可审核来源身份与解析质量，投资研究审核由 StockWiki 完成；
- Markdown Wiki 属 legacy 兼容层，不得成为第二套 authoritative research state。

## 配置卫生（R4.1/N-05）

- `config/source_catalog.yaml` 是生产配置：测试与调试**必须**使用 tmp 夹具，
  不得写穿生产文件；会话结束前 `git status` 必须能解释每个未提交的 config 变更，
  无法解释即事故，立即恢复并记录。
- 怀疑配置损坏时先跑 `python scripts/config_doctor.py`（exit≠0 即有问题）；
  控制面板菜单 7 也提供该体检。

## 目录规范

- `companies/{公司名}/` — 公司所有原始文档（新闻 .md、财报/研报 .pdf 直接存放）
- `companies/{公司名}/raw/` — （可选）旧版按类型分的子目录，新文件直接存公司根目录
- `companies/{公司名}/wiki/` — legacy 主题时间线，只读兼容或 source-oriented projection
- `sectors/{行业名}/raw/` — 行业原始文档
- `sectors/{行业名}/wiki/` — legacy 行业页面，只读兼容或 source-oriented projection
- `themes/{主题名}/` — 跨行业主题信息
- `config.yaml` — 全局配置（公司列表、问题清单等）
- `index.md` — 全局索引
- `log.md` — 操作日志（append-only）

文件来源：
- `collect_news.py` → 新闻存入 `companies/{name}/raw/news/*.md`
- `StockInfoDownloader` → 财报/研报直接存入 `companies/{name}/*.pdf`
- `ingest.py` → 扫描 `companies/{name}/` 下所有非 wiki 文件

## Legacy Wiki 文档格式（兼容规范，非 canonical 目标）

仅在维护既有只读页面或 source-oriented projection 时使用下列格式。禁止据此新建投资分析、估值、综合判断或正式报告页面。

每个 legacy wiki 文档必须包含：

### Frontmatter（YAML）
```yaml
---
title: {文档标题}
description: {一行摘要，≤80字，用于 index.md 展示}
entity: {所属实体名}
type: company_topic | sector_topic | theme_topic | overview | concept | comparison | synthesis
last_updated: YYYY-MM-DD
sources_count: N
tags: [tag1, tag2]
---
```

`description` 为可选字段。如果省略，generate_index.py 会自动从正文提取摘要。

### 页面类型说明

| type | 用途 | 典型来源 |
|------|------|---------|
| `company_topic` | 公司动态/相关动态 | ingest 新闻、财报 |
| `sector_topic` | 行业概览 | ingest 跨公司信息 |
| `theme_topic` | 跨行业主题 | ingest 跨行业信息 |
| `overview` | 实体总览 | LLM 生成 |
| `concept` | 概念百科（如"EUV光刻"） | Query 归档 / LLM 发现 |
| `comparison` | 对比分析（如"中微 vs 北方华创"） | Query 归档 / 用户请求 |
| `synthesis` | 综合报告（如"Q1 半导体设备回顾"） | Query 归档 / LLM 生成 |

**新增类型模板格式：**

概念页（concept）：
```markdown
## 定义
## 技术要点
## 产业影响
## 相关引用
```

对比页（comparison）：
```markdown
## 对比维度
## 时间线对比
## 综合判断
```

综合页（synthesis）：
```markdown
## 核心发现
## 详细分析
## 展望
```

这些模板仅为建议结构，LLM 可根据内容灵活调整。

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

## Legacy Wiki Ingest 规则（冻结新增调用）

下列规则只解释历史 writer 行为，不再是新 canonical ingest 的目标。新 ingest 必须优先产出 source manifest、规范化文档、EvidenceSpan、解析质量和只读索引/export，不得直接沉淀投资结论。

1. **读取新文件**：从 raw/ 目录读取新到达的文档
2. **判断相关性**：对照 config.yaml 判断该文档影响哪些 topics
3. **更新时间线**：对每个相关 topic，读取现有 wiki 文档，按日期插入新条目
4. **双向更新**：一条新闻可能同时影响公司 wiki 和行业/主题 wiki，都要更新
5. **更新 frontmatter**：修改 last_updated 和 sources_count
6. **记录日志**：在 log.md 中记录本次 ingest
7. **更新索引**：如有新增页面，在 index.md 中添加

## Legacy 时间线条目原则

- **精炼**：每个条目 2-5 个要点，不要复制原文
- **有判断**：不只是事实罗列，要指出这意味着什么
- **可追溯**：每个条目都要有来源链接
- **关联性**：如果与其他 topic 有关联，用 wikilinks 引用（如 [[AI产业链/大模型竞争]]）

## Legacy Wiki Lint 规则

定期检查以下内容：
1. 矛盾：不同页面之间是否有矛盾的陈述？
2. 过时：是否有页面长期未更新？
3. 孤儿：是否有页面没有被任何其他页面引用？
4. 缺失：是否有重要概念被提及但没有自己的页面？
5. 问题更新：哪些问题长期无新进展？哪些新信息没有对应问题？

## Legacy Wiki 进化规则（停用）

以下规则保留为历史说明，不得自动执行；上游只允许提出 source schema、collector/parser、实体来源别名和解析质量方面的变更提案。

- 如果 ingest 时发现不属于任何现有 topic 的重要信息，创建新 topic 草稿
- 如果新闻频繁提及一个未跟踪的公司，建议用户添加
- 定期审查问题清单，标记过时的问题，建议新问题

## 架构约束

- **职责单一**：canonical 对象仅限 SourceRecord/source manifest、EvidenceSpan、extraction quality、原文索引和 source-oriented projection；不得引入投资研究 state 或估值链。
- **跨仓只读**：与 StockWiki 通过版本化 export 交换 ID/hash 引用，不共享可变数据库，不跨仓写文件。
- **单线程**：整个系统以单线程顺序执行。`LLMClient` 不是线程安全的（包含全局状态和限流状态）。如需多线程，须重构为无状态设计。
- **两套 Graph 实现**：`scripts/graph.py` 是规范实现（被 39+ 脚本使用）。`scripts/models/` 是类型化版本，已弃用，仅供测试和归档脚本使用。
- **两大部分**：`llm_client.py` 分基础设施（API/限流/成本）和业务方法（分析/评估/查询）两部分。

## 使用的工具

- 文件读写：直接操作文件系统
- 搜索：ripgrep 搜索 wiki 内容
- 版本控制：git

## 反馈记录（自动生成）

> 此 section 由 scheduler.py 的 schema evolve 机制自动更新。
> 记录了系统运行中的质量指标和改进建议，供 LLM 自我优化参考。
> 最后更新：2026-04-25
> 2026-07-16 scope note：以下是 legacy Wiki 时代的历史快照，不是当前执行队列；其中评估、综合判断和研究 Wiki 生产建议已被职责边界取代。

### 运行指标
- 跟踪实体：233 家公司, 25 个行业
- Wiki 页面：345 公司页, 25 行业页
- 综合评估：157 已有, 0 过时, 213 缺失
- 审核队列：0 总计, 0 待审, 0 已批
- Lint 状态：_（暂无 lint 数据）_

### 改进建议

### 发现的问题
1. **评估缺失严重（213个缺失），且调度器评估生产量为零** → 评估生成模块未触发或配置错误。建议检查 `assess` 调度任务绑定的触发条件，确保在新闻采集、公司/行业页面更新后自动启动评估，并设置补缺机制对已有信息但无评估的条目限期生成。

2. **新闻采集极度倾斜（7天内仅北方华创19篇），其余232家公司零采集** → 采集源配置或筛选规则过于狭窄，导致数据覆盖不均衡。建议扩大采集关键词库，按行业均衡配置抓取源，并定期检查采集覆盖率指标，确保每家公司至少每周有1-2条相关新闻。

3. **矛盾检测报告200条潜在矛盾，但无高置信度结果** → 规则过于宽松或信号过滤不足，大量低价值矛盾浪费分析资源。建议调整矛盾判定阈值，增加关键字段（如营收、评级）的硬性矛盾检测，对高置信度矛盾自动生成审核工单，推动人工确认与修正。

### 重点关注
- **历史项（已取代）**：修复评估生成流程的建议不再执行；投资评估属于 StockWiki。
- **优化新闻采集调度策略**，避免单一公司垄断，提升信息发现的全面性。
