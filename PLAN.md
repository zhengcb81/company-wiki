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

### Phase 1：基础框架 ✅ 2026-04-11
- [x] 创建目录结构
- [x] 编写 PLAN.md
- [x] 编写 config.yaml（3家 A 股公司）
- [x] 编写 CLAUDE.md（Schema）
- [x] 创建示例 wiki 页面验证格式

### Phase 2：新闻采集 ✅ 2026-04-11
- [x] 实现 collect_news.py（Tavily API，去重，保存为 markdown）
- [ ] 配置 Hermes cronjob 每日运行
- [x] 测试采集流程（3家公司共53篇新闻）

### Phase 3：Ingest 流程 ✅ 2026-04-11
- [x] 实现 ingest.py（扫描 raw/，判断相关性，更新 wiki）
- [x] 实现双向更新逻辑（公司 → 行业 → 主题，一次新闻更新最多8个 wiki 页面）
- [x] 测试完整链路（53篇新闻 → 204条 topic 条目 → 14个 wiki 页面）

### Phase 3.5：财报采集 🔄 2026-04-11
- [x] 实现 collect_reports.py（StockInfoDownloader 适配器）
- [ ] 在本地 Windows 环境测试

### Phase 4：自我进化
- [ ] 实现 lint 逻辑（矛盾检测、过时标记、孤儿页面）
- [ ] 实现自动发现机制（新主题、新公司建议）
- [ ] 实现 config.yaml 动态更新

### Phase 4：自我进化 🔄 2026-04-12
- [x] 实现 lint 逻辑（过时、孤儿、空页、断链、配置一致性、数据新鲜度）
- [ ] 实现自动发现机制（新主题、新公司建议）
- [ ] 实现 config.yaml 动态更新

### Phase 5：完善优化 🔄 2026-04-12
- [x] 引入启发式智能摘要（extract.py：文本清洗+评分+分类）
- [x] 实现 LLM 精炼管道（refine.py：manifest 生成+应用）
- [x] 配置 cronjob 每日 9:00 自动采集+ingest
- [x] 质量过滤（43% 噪音文件自动过滤）
- [ ] 扩展公司和行业
- [ ] 考虑向量搜索（qmd）

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
| 2026-04-11 | Phase 1-3 完成，Phase 3.5（财报采集适配器已写，待本地测试） |
| 2026-04-12 | Phase 4-5 完成：extract.py 智能摘要、refine.py LLM 管道、lint.py 健康检查、cronjob 每日自动运行 |

## 十二、当前问题与重构计划

### 问题诊断

**问题 1：两个数据源，信息重复**
```
config.yaml:  companies[], sectors{}, themes{}  ← 定义公司/行业/问题
graph.yaml:   nodes{}, edges{}, companies{}     ← 定义拓扑关系
```
改一个忘改另一个就会不一致。

**问题 2：硬编码相关性判断**
```python
# ingest.py 中的硬编码（不可扩展）
sector_keywords = {"半导体设备": ["半导体", "芯片", ...]}
theme_keywords = {"半导体国产替代": ["国产替代", ...]}
```
新增行业必须改代码。

**问题 3：无自动拓扑发现机制**
新公司加入时，需手动：确定所属行业、搜索关键词、上下游关系。

### 重构方案：三层架构

```
┌─────────────────────────────────────────────────┐
│  graph.yaml（单一数据源，动态扩展）                │
│  - nodes: 行业/子领域/主题（含 description, tier）│
│  - edges: 上下游/竞争/从属关系                    │
│  - companies: 公司（含 sectors, themes,           │
│               news_queries, position）            │
│  - questions: 每个行业的核心跟踪问题              │
├─────────────────────────────────────────────────┤
│  config.yaml（纯运维配置，不包含业务数据）         │
│  - API keys (tavily, deepseek)                   │
│  - schedule, paths                               │
│  - report_downloader 设置                        │
├─────────────────────────────────────────────────┤
│  scripts/（从 graph.yaml 动态读取）              │
│  - graph.py: 图查询 + 数据加载（统一入口）        │
│  - ingest.py: 从 graph 推导相关性                │
│  - collect_news.py: 从 graph 读取公司+查询词      │
│  - enrich.py: 新公司自动拓扑发现                  │
│  - lint.py: 配置一致性检查                        │
└─────────────────────────────────────────────────┘
```

### 实施步骤

#### Step 1: graph.yaml 增强 — 补全数据结构
给 graph.yaml 中的 nodes 和 companies 补全必要字段：
- nodes 加 `keywords` 字段（用于 ingest 相关性匹配）
- companies 加 `news_queries` 字段（用于 collect_news）
- 新增 `questions` 部分（每个行业/主题的核心问题）

#### Step 2: graph.py 增强 — 统一数据加载入口
给 graph.py 添加：
- `load_all(config_path)` → 返回统一的图数据结构
- `get_company(name)` → 公司详情+关联行业+搜索词
- `get_sector(name)` → 行业详情+公司列表+上游+下游+问题
- `get_relevance_keywords()` → 动态生成所有行业/主题的关键词映射
- `get_all_companies()` → 所有公司列表（含配置）
- `find_related_sectors(text)` → 根据文本动态匹配相关行业

#### Step 3: 重构 ingest.py — 去掉硬编码
- 删掉 `sector_keywords` 和 `theme_keywords` 硬编码
- 改为从 `graph.find_related_sectors(text)` 动态推导
- 相关性判断逻辑：优先用公司 frontmatter 标签 → 再用关键词匹配 graph nodes

#### Step 4: 重构 collect_news.py — 从 graph 读取
- 删掉从 config.yaml 读取 companies 的逻辑
- 改为从 graph.yaml 读取公司列表+news_queries

#### Step 5: config.yaml 精简
- 删掉 `companies`, `sectors`, `themes` 部分
- 只保留 API keys, schedule, paths, report_downloader

#### Step 6: 实现 enrich.py — 新公司自动拓扑发现
```
输入: 公司名 + 股票代码
流程:
  1. Tavily 搜索公司业务信息
  2. LLM 分析 → 匹配 graph.yaml 中的现有行业
  3. LLM 推荐: 上下游关系、竞争对手、搜索关键词
  4. 生成 proposal → pending_enrichment.yaml
  5. --auto 模式：自动合并到 graph.yaml
  6. --review 模式：人工审核后合并
```

#### Step 7: 实现 auto_suggest.py — 新公司自动发现
```
在每日新闻采集中：
  - 如果一条新闻频繁提到一个不在 graph.yaml 中的公司名
  - → 标记为潜在新公司
  - → 调用 enrich.py 自动生成拓扑提案
```

#### Step 8: 验证 — 端到端测试
- 新增一家公司只需在 graph.yaml 加一条记录
- 所有脚本自动适配（collect_news, ingest, graph query）
- enrich.py 自动发现并融入拓扑
