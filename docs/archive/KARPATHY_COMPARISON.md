# Karpathy LLM Wiki 对比分析

## Karpathy 的核心概念

> 来源: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

### 核心理念

> "Instead of just retrieving from raw documents at query time, the LLM **incrementally builds and maintains a persistent wiki** — a structured, interlinked collection of markdown files that sits between you and the raw sources."

**关键区别**: Wiki 是一个 **持久化、累积的工件**，而不是每次查询都重新推导。

### 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│  Schema (CLAUDE.md)                                         │
│  - 告诉 LLM wiki 如何组织                                    │
│  - 定义规范和工作流                                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  The Wiki                                                   │
│  - LLM 生成的 markdown 文件                                  │
│  - 结构化、相互链接                                          │
│  - LLM 完全拥有这一层                                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Raw Sources                                                │
│  - 原始文档集合                                              │
│  - 不可变 - LLM 只读取，不修改                                │
│  - 真相的来源                                                │
└─────────────────────────────────────────────────────────────┘
```

### 三个核心操作

1. **Ingest**: LLM 读取新来源，提取关键信息，整合到现有 wiki
2. **Query**: 对 wiki 提问，答案可以存回 wiki 作为新页面
3. **Lint**: 定期健康检查 - 矛盾、过时、孤儿页面、缺失交叉引用

### 两个特殊文件

1. **index.md**: 内容导向的目录 - 页面链接 + 一行摘要 + 元数据
2. **log.md**: 时间顺序记录 - append-only 的操作日志

---

## 对比分析

### ✅ 已实现的功能

| Karpathy 概念 | 我们的实现 | 状态 |
|--------------|-----------|------|
| **三层架构** | | |
| Raw Sources (不可变) | `companies/{公司}/raw/` | ✅ 完全匹配 |
| The Wiki (LLM生成) | `companies/{公司}/wiki/` | ✅ 完全匹配 |
| Schema (CLAUDE.md) | `CLAUDE.md` | ✅ 完全匹配 |
| **核心操作** | | |
| Ingest (读取+整合) | `ingest.py` | ✅ 完全匹配 |
| Query (对wiki提问) | `graph.py --find` | ⚠️ 部分实现 |
| Lint (健康检查) | `lint.py` | ✅ 完全匹配 |
| **特殊文件** | | |
| index.md (内容目录) | `index.md` | ✅ 完全匹配 |
| log.md (时间日志) | `log.md` | ✅ 完全匹配 |
| **Wiki 特性** | | |
| 持久化累积 | 文件系统存储 | ✅ 完全匹配 |
| 结构化页面 | YAML frontmatter | ✅ 完全匹配 |
| 交叉引用 | Wikilinks `[[公司]]` | ✅ 完全匹配 |
| 时间线 | 每个主题的时间线 | ✅ 完全匹配 |
| **Ingest 细节** | | |
| 读取来源 | `extract.py` | ✅ 完全匹配 |
| 提取关键信息 | 摘要提取 | ✅ 完全匹配 |
| 更新实体页面 | 多页面更新 | ✅ 完全匹配 |
| 更新主题摘要 | 问题匹配 | ✅ 新增功能 |
| 记录日志 | `log.md` | ✅ 完全匹配 |
| **Lint 细节** | | |
| 矛盾检测 | `lint.py` | ⚠️ 基础实现 |
| 过时检测 | `lint.py` | ✅ 完全匹配 |
| 孤儿页面检测 | `lint.py` | ✅ 完全匹配 |
| 缺失交叉引用 | `lint.py` | ⚠️ 基础实现 |

### ⚠️ 部分实现的功能

| 功能 | Karpathy 概念 | 我们的实现 | 差距 |
|------|--------------|-----------|------|
| **Query** | "Answers can be filed back into the wiki" | 无自动存回 | 需要添加 |
| **矛盾检测** | "noting where new data contradicts old claims" | 基础实现 | 需要增强 |
| **动态问题** | "suggesting new questions to investigate" | `auto_discover.py` | 已实现 |
| **源发现** | "new sources to look for" | 无 | 需要添加 |

### ❌ 未实现的功能

| 功能 | Karpathy 概念 | 说明 |
|------|--------------|------|
| **Obsidian 集成** | "I have the LLM agent open on one side and Obsidian open on the other" | 可选功能 |
| **Graph View** | "Obsidian's graph view is the best way to see the shape of your wiki" | 可选功能 |
| **Marp 支持** | "Marp is a markdown-based slide deck format" | 可选功能 |
| **Dataview** | "Dataview is an Obsidian plugin that runs queries over page frontmatter" | 可选功能 |
| **图片处理** | "Download images locally" | 部分支持 |
| **搜索工具** | "qmd is a good option for search" | 基础实现 |

---

## 详细评分

### 1. 架构一致性 (90%)

**Karpathy**: "three layers: Raw sources → Wiki → Schema"

**我们**:
```
~/company-wiki/
├── companies/{公司}/raw/     ← Raw sources ✅
├── companies/{公司}/wiki/    ← The wiki ✅
├── CLAUDE.md                 ← Schema ✅
└── ...
```

**评分**: 90% - 几乎完全匹配

### 2. Ingest 流程 (95%)

**Karpathy**: "the LLM reads the source, discusses key takeaways, writes a summary page, updates the index, updates relevant entity and concept pages, and appends an entry to the log"

**我们**:
```python
# ingest.py
1. 扫描 raw/ 目录
2. 读取新文件
3. 提取摘要 (extract.py)
4. 判断相关性 (graph.py)
5. 更新多个 wiki 页面
6. 更新 index.md
7. 记录 log.md
```

**评分**: 95% - 完全匹配，甚至更强（问题匹配）

### 3. Query 能力 (60%)

**Karpathy**: "You ask questions against the wiki. The LLM searches for relevant pages, reads them, and synthesizes an answer with citations."

**我们**:
```bash
python3 scripts/graph.py --find "中微公司发布新设备"
# 返回相关实体，但没有综合答案
```

**差距**: 缺少答案综合和存回 wiki 的功能

**评分**: 60% - 基础实现

### 4. Lint 能力 (75%)

**Karpathy**: "Look for: contradictions between pages, stale claims, orphan pages, missing cross-references, data gaps"

**我们**:
```python
# lint.py
- ✅ 过时检测
- ✅ 孤儿页面检测
- ⚠️ 矛盾检测（基础）
- ⚠️ 缺失交叉引用（基础）
- ❌ 数据缺口检测
```

**评分**: 75% - 核心功能已实现

### 5. 索引和日志 (100%)

**Karpathy**: "index.md is content-oriented, log.md is chronological"

**我们**:
```markdown
# index.md
## 公司（按行业）
### 应用层
**AI应用**
  [[商汤科技]], [[百度]], [[科大讯飞]]

# log.md
## [2026-04-17 21:01] ingest | Ingested 3 files
```

**评分**: 100% - 完全匹配

### 6. 自进化能力 (80%)

**Karpathy**: "The LLM is good at suggesting new questions to investigate and new sources to look for"

**我们**:
```python
# auto_discover.py
- ✅ 发现新公司
- ✅ 发现新主题
- ✅ 建议新问题
- ❌ 建议新来源
```

**评分**: 80% - 大部分实现

---

## 总体评分

| 维度 | 权重 | 得分 | 加权得分 |
|------|------|------|----------|
| 架构一致性 | 20% | 90% | 18% |
| Ingest 流程 | 25% | 95% | 24% |
| Query 能力 | 15% | 60% | 9% |
| Lint 能力 | 15% | 75% | 11% |
| 索引和日志 | 10% | 100% | 10% |
| 自进化能力 | 15% | 80% | 12% |
| **总计** | **100%** | | **84%** |

---

## 差距分析

### 主要差距

1. **Query 答案存回** (重要)
   - Karpathy: "good answers can be filed back into the wiki as new pages"
   - 我们: 查询结果不会自动存回
   
2. **矛盾检测** (中等)
   - Karpathy: "noting where new data contradicts old claims"
   - 我们: 基础实现，需要增强

3. **源发现建议** (低优先级)
   - Karpathy: "new sources to look for"
   - 我们: 未实现

### 次要差距

4. **Obsidian 集成** (可选)
   - Karpathy 推荐使用 Obsidian
   - 我们: 可以手动使用

5. **搜索工具** (可选)
   - Karpathy 推荐 qmd
   - 我们: 有基础搜索

---

## 我们的优势

### 超越 Karpathy 的地方

1. **领域特化**
   - Karpathy: 通用知识库
   - 我们: 上市公司研究专用，有行业/主题/公司三级结构

2. **问题匹配**
   - Karpathy: 未提及
   - 我们: 自动匹配预设问题，时间线显示回答的问题

3. **自动化程度**
   - Karpathy: "I prefer to ingest sources one at a time and stay involved"
   - 我们: 完全自动化的 cron job，每日运行

4. **数据采集**
   - Karpathy: 手动收集来源
   - 我们: 自动新闻搜索 + 财报下载

5. **结构化程度**
   - Karpathy: 通用 markdown
   - 我们: 结构化的 YAML frontmatter + 时间线格式

---

## 改进建议

### 高优先级

1. **实现 Query → Wiki 存回**
   ```python
   # 当用户问了一个好问题，答案应该存回 wiki
   def save_query_result_to_wiki(question, answer, related_entities):
       # 创建新的 wiki 页面
       # 更新相关实体
       # 记录到 log.md
   ```

2. **增强矛盾检测**
   ```python
   # 检测不同页面之间的矛盾陈述
   def detect_contradictions():
       # 比较相似主题的页面
       # 标记不一致的数据
       # 提示用户确认
   ```

### 中优先级

3. **实现源发现建议**
   ```python
   # 根据现有知识缺口，建议新的数据来源
   def suggest_new_sources():
       # 分析哪些问题没有答案
       # 搜索相关的新闻/报告
       # 提供下载链接
   ```

4. **添加 Obsidian 兼容**
   - 确保所有 markdown 文件符合 Obsidian 格式
   - 添加 graph view 支持
   - 支持 Dataview 查询

### 低优先级

5. **添加搜索工具集成**
   - 集成 qmd 或类似工具
   - 支持语义搜索

6. **图片处理**
   - 下载图片到本地
   - 支持 LLM 查看图片

---

## 结论

我们的项目已经实现了 Karpathy LLM Wiki 概念的 **84%**，在某些方面甚至超越了他的原始概念：

- ✅ **架构**: 完全匹配三层架构
- ✅ **Ingest**: 95% 实现，有自动化增强
- ✅ **Lint**: 75% 实现，核心功能完整
- ✅ **索引/日志**: 100% 实现
- ⚠️ **Query**: 60% 实现，缺少答案存回
- ✅ **自进化**: 80% 实现

**主要差距**在于 Query 能力和矛盾检测，这两项可以通过后续改进实现。

**我们的优势**在于领域特化、自动化程度和结构化程度，这些是针对上市公司研究场景的专门优化。