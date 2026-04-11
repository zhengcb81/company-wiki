# 上市公司知识库系统 — 实施计划

> 基于 Karpathy 的 LLM Wiki 模式，针对上市公司研究场景定制。
> 核心思想：LLM 增量构建并维护一个持久化 wiki，知识随时间复利增长。

---

## 一、整体架构

```
Raw Sources (采集) → Ingest (LLM整理) → Wiki (知识库) → Query (查询/分析)
                        ↑                      |
                    config.yaml (配置)    lint (健康检查)
```

三层架构（来自 Karpathy）：
- **Raw Sources**: 采集的原始文档（财报、公告、新闻），不可修改
- **Wiki**: LLM 生成的 markdown 文件，按主题组织的时间线文档
- **Schema**: CLAUDE.md，定义 wiki 的结构和维护规范

---

## 二、目录结构

```
~/company-wiki/
├── PLAN.md                     # 本文件：实施计划
├── config.yaml                 # 全局配置：公司列表、行业板块、主题问题清单
├── CLAUDE.md                   # Schema：LLM 维护 wiki 的行为规范
├── index.md                    # 全局索引
├── log.md                      # 操作日志（append-only，按时间记录所有 ingest/query/lint）
│
├── companies/                  # 按公司组织
│   └── {公司名}/
│       ├── raw/
│       │   ├── reports/        # 定期财报、招股书、重要公告（PDF/HTML）
│       │   ├── research/       # 券商研报
│       │   └── news/           # 新闻文章（markdown）
│       └── wiki/
│           ├── overview.md     # 公司概况
│           ├── 财务表现.md      # 主题时间线文档
│           ├── AI战略.md
│           └── ...
│
├── sectors/                    # 按行业组织
│   └── {行业名}/
│       ├── raw/
│       │   ├── research/
│       │   └── news/
│       └── wiki/
│           ├── 行业概览.md
│           ├── 竞争格局.md
│           └── ...
│
├── themes/                     # 跨行业主题
│   └── {主题名}/
│       ├── raw/
│       │   └── news/
│       └── wiki/
│           ├── 主题概述.md
│           └── ...
│
└── scripts/                    # 自动化脚本
    ├── collect_news.py         # 新闻采集
    ├── collect_reports.py      # 财报/公告采集（对接已有程序）
    ├── ingest.py               # 新数据 ingest 入口
    └── lint.py                 # 知识库健康检查
```

---

## 三、核心配置 (config.yaml)

### 3.1 公司列表

```yaml
companies:
  - ticker: "BABA"
    name: "阿里巴巴"
    exchange: "NYSE"
    sectors: ["互联网"]
    themes: ["AI产业链"]
    news_queries:
      - "阿里巴巴 最新"
      - "Alibaba earnings news"
    report_sources:
      - type: "sec-edgar"
        cik: "0001577552"
```

### 3.2 行业定义

```yaml
sectors:
  互联网:
    topics:
      - name: "行业概览"
        questions:
          - "本季度有哪些重大行业政策变化？"
          - "用户增长趋势如何？"
          - "变现模式有什么新动向？"
      - name: "竞争格局"
        questions:
          - "头部公司市占率有何变化？"
          - "有无重大并购或合作？"
      - name: "技术趋势"
        questions:
          - "AI/大模型在行业内有哪些新应用？"
      - name: "监管政策"
        questions:
          - "近期有哪些新法规或政策出台？"
```

### 3.3 跨行业主题

```yaml
themes:
  AI产业链:
    topics:
      - name: "芯片与算力"
        questions:
          - "GPU/AI芯片供需格局如何？"
          - "国产替代进展如何？"
      - name: "大模型竞争"
        questions:
          - "各家大模型能力对比如何？"
          - "开源 vs 闭源趋势？"
      - name: "应用落地"
        questions:
          - "AI 在各行业有哪些新落地场景？"
          - "商业化变现路径是否清晰？"
```

### 3.4 调度与搜索

```yaml
schedule:
  news_collection: "daily"      # 每天采集新闻
  report_check: "weekly"        # 每周检查财报
  lint: "weekly"                # 每周健康检查

search:
  engine: "tavily"
  results_per_query: 10
  language: "zh"

evolution:
  auto_discover_topics: true    # 自动发现新主题
  suggest_companies: true       # 自动建议新公司
  evolve_questions: true        # 自动更新问题清单
```

---

## 四、主题文档格式（Wiki Page）

每个主题文档采用统一格式：

```markdown
---
title: {主题名}
entity: {公司/行业/主题名}
type: company_topic | sector_topic | theme_topic
last_updated: YYYY-MM-DD
sources_count: N
tags: [tag1, tag2]
---

# {实体名} — {主题名}

## 核心问题
- 问题1？
- 问题2？

## 时间线

### YYYY-MM-DD | {来源类型} | {标题}
- 要点1
- 要点2
- [来源: {说明}](../raw/{path})

### YYYY-MM-DD | {来源类型} | {标题}
- ...

## 综合评估
> 对该主题的阶段性总结和判断。
```

---

## 五、数据采集模块

### 5.1 新闻采集流程

```
config.yaml (公司列表 + 搜索关键词)
    ↓
搜索引擎 API (Tavily / Serper / Brave)
    ↓
去重 (URL 去重 + 标题相似度)
    ↓
保存到 companies/{name}/raw/news/{date}_{hash}_{title}.md
    ↓
交叉检查：新闻是否属于某个 sector/theme？
    → 是：在 sectors/{name}/raw/news/ 或 themes/{name}/raw/news/ 下创建引用
    ↓
标记为待 ingest
```

### 5.2 财报/公告采集

```
定期检查来源 (巨潮资讯/港交所/SEC EDGAR)
    ↓
下载 PDF → companies/{name}/raw/reports/{date}_{type}_{name}.pdf
    ↓
标记为待 ingest
```

---

## 六、数据整理模块 (Ingest)

### 6.1 Ingest 触发条件
- 新文件出现在 raw/ 目录
- 手动触发
- 采集脚本完成后的自动触发

### 6.2 Ingest 流程

```
检测到新文件
    ↓
LLM 读取新文件内容
    ↓
判断相关性：
  1. 属于哪些 company topics？
  2. 属于哪些 sector topics？
  3. 属于哪些 theme topics？
    ↓
对每个相关 topic：
  - 读取现有 wiki/{topic}.md
  - 判断：是否回答了 topic 下的某个问题？
  - 如果有新进展 → 在时间线中按日期插入新条目
  - 更新 frontmatter
    ↓
更新 index.md 和 log.md
    ↓
记录本次 ingest 到 log.md
```

### 6.3 双向更新示例

一条新闻 "阿里巴巴发布新一代AI大模型" 会触发更新：
1. `companies/阿里巴巴/wiki/AI战略.md` — 公司层面
2. `companies/阿里巴巴/wiki/财务表现.md` — 如果涉及投入数据
3. `sectors/互联网/wiki/技术趋势.md` — 行业层面
4. `themes/AI产业链/wiki/大模型竞争.md` — 主题层面

---

## 七、自我进化机制

### 7.1 自动发现新主题
- ingest 时发现不属于任何现有 topic 的重要信息
- 创建新 topic 草稿，标记为 pending_review
- 在 log.md 中记录，提醒用户审核

### 7.2 自动建议新公司
- 新闻频繁提及一个未跟踪的公司
- 建议用户添加到 config.yaml

### 7.3 自动更新问题清单
- 哪些问题长期无更新 → 标记为可能过时
- 哪些信息频繁出现但无对应问题 → 建议新问题

---

## 八、技术选型

| 组件 | 方案 | 理由 |
|------|------|------|
| 存储 | Obsidian Vault + Git | wikilinks + graph view + 版本控制 |
| 新闻搜索 | Tavily API | 专为 AI 设计，返回结构化+摘要 |
| 财报采集 | 已有程序 | 直接对接 |
| LLM 编排 | Hermes Agent | cronjob 定期运行，已有 skill 体系 |
| 定时任务 | Hermes cronjob | 每日新闻采集 + 每周 lint |
| 搜索 wiki | ripgrep / qmd | 本地全文搜索 |
| 变更检测 | 文件哈希/时间戳 | 避免重复 ingest |

---

## 九、实施路线图

### Phase 1：基础框架（当前）
- [x] 创建目录结构
- [x] 编写 PLAN.md
- [ ] 编写 config.yaml（2-3家测试公司）
- [ ] 编写 CLAUDE.md（Schema）
- [ ] 创建示例 wiki 页面验证格式

### Phase 2：新闻采集
- [ ] 实现 collect_news.py
- [ ] 配置 Hermes cronjob 每日运行
- [ ] 测试采集流程

### Phase 3：Ingest 流程
- [ ] 实现 ingest.py
- [ ] 实现双向更新逻辑
- [ ] 测试完整链路

### Phase 4：自我进化
- [ ] 实现 lint 逻辑
- [ ] 实现自动发现机制
- [ ] 实现 config.yaml 动态更新

### Phase 5：完善优化
- [ ] 接入财报采集
- [ ] 扩展公司和行业
- [ ] 优化 ingest 准确性
- [ ] 考虑向量搜索

---

## 十、当前公司清单

| 股票代码 | 公司名 | 交易所 | 行业 | 主题 |
|---------|--------|--------|------|------|
| 688012 | 中微公司 | 科创板 | 半导体设备 | 半导体国产替代 |
| 300470 | 中密控股 | 创业板 | 密封件 | 高端制造 |
| 301611 | 珂玛科技 | 创业板 | 半导体设备 | 半导体国产替代 |

## 十一、进度记录

| 日期 | 进展 |
|------|------|
| 2026-04-11 | 项目启动，创建目录结构，编写 PLAN.md |
| 2026-04-11 | 配置 3 家 A 股公司，接入 Tavily API，编写 collect_news.py |
| 2026-04-11 | 编写 ingest.py（双向更新），编写 collect_reports.py（StockInfoDownloader 适配） |
| 2026-04-11 | 首次完整跑通采集→ingest 链路：53 篇新闻，204 条 topic 条目，14 个 wiki 页面 |
