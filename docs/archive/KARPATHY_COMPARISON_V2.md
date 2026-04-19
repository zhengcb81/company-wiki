# Karpathy LLM Wiki 对比分析

> 参考: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
> 更新日期: 2026-04-17

## 一、Karpathy 核心概念

### 核心理念

> "Instead of just retrieving from raw documents at query time, the LLM **incrementally builds and maintains a persistent wiki** — a structured, interlinked collection of markdown files that sits between you and the raw sources."

**关键区别**: Wiki 是一个**持久化、累积的工件**，而不是每次查询都重新推导。

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

## 二、对比分析

### 2.1 架构一致性 (90/100)

| Karpathy 概念 | 我们的实现 | 状态 |
|--------------|-----------|------|
| Raw Sources | `companies/{公司}/raw/` | ✅ 完全匹配 |
| The Wiki | `companies/{公司}/wiki/` | ✅ 完全匹配 |
| Schema | `CLAUDE.md` | ✅ 完全匹配 |

**评价**: 三层架构完全匹配，目录结构清晰。

### 2.2 Ingest 流程 (95/100)

| Karpathy 概念 | 我们的实现 | 状态 |
|--------------|-----------|------|
| LLM 读取来源 | `extract.py` 提取内容 | ✅ 完全匹配 |
| 提取关键信息 | 摘要提取 + 关键词 | ✅ 完全匹配 |
| 整合到 wiki | `ingest.py` 自动更新 | ✅ 完全匹配 |
| 更新多个页面 | 交叉引用更新 | ✅ 完全匹配 |
| 记录日志 | `log.md` 自动记录 | ✅ 完全匹配 |

**优势**: 我们的 ingest 是完全自动化的（cron job），而 Karpathy 是手动的。

**评价**: 自动化程度更高，但缺少 LLM 参与。

### 2.3 Query 能力 (60/100)

| Karpathy 概念 | 我们的实现 | 状态 |
|--------------|-----------|------|
| 对 wiki 提问 | `query.py` 搜索 | ⚠️ 基础实现 |
| 答案存回 wiki | `AnswerSaver` | ⚠️ 部分实现 |
| 综合答案 | `AnswerSynthesizer` | ⚠️ 基础实现 |
| 支持多种格式 | 仅 markdown | ❌ 未实现 |

**差距**: 
- Query → Wiki 存回不完善
- 缺少 LLM 综合答案
- 缺少 Marp、图表等格式支持

### 2.4 Lint 能力 (75/100)

| Karpathy 概念 | 我们的实现 | 状态 |
|--------------|-----------|------|
| 矛盾检测 | `contradiction_detector.py` | ⚠️ 基础实现 |
| 过时检测 | `lint.py` | ✅ 完全匹配 |
| 孤儿页面 | `lint.py` | ✅ 完全匹配 |
| 缺失交叉引用 | `lint.py` | ⚠️ 基础实现 |
| 源发现建议 | `source_discoverer.py` | ⚠️ 基础实现 |

**差距**: 矛盾检测和源发现需要增强。

### 2.5 索引和日志 (100/100)

| Karpathy 概念 | 我们的实现 | 状态 |
|--------------|-----------|------|
| index.md | `index.md` 自动生成 | ✅ 完全匹配 |
| log.md | `log.md` 自动记录 | ✅ 完全匹配 |
| 内容导向 | 按行业/公司组织 | ✅ 完全匹配 |
| 时间顺序 | append-only | ✅ 完全匹配 |

**评价**: 完全匹配，甚至更好（自动生成）。

### 2.6 自进化能力 (80/100)

| Karpathy 概念 | 我们的实现 | 状态 |
|--------------|-----------|------|
| 新公司发现 | `auto_discover.py` | ✅ 已实现 |
| 新主题发现 | `auto_discover.py` | ✅ 已实现 |
| 新问题建议 | `auto_discover.py` | ✅ 已实现 |
| LLM 建议 | 无 LLM 参与 | ❌ 未实现 |

**差距**: 缺少 LLM 参与的建议生成。

### 2.7 LLM 集成 (30/100)

| Karpathy 概念 | 我们的实现 | 状态 |
|--------------|-----------|------|
| LLM 读取来源 | 脚本提取 | ❌ 无 LLM |
| LLM 提取信息 | 规则提取 | ❌ 无 LLM |
| LLM 整合 wiki | 脚本更新 | ❌ 无 LLM |
| LLM 综合答案 | 无 LLM | ❌ 无 LLM |
| LLM 健康检查 | 脚本检查 | ❌ 无 LLM |

**这是最核心的差距**: 我们的系统是纯脚本驱动，无 LLM 参与。

---

## 三、差距总结

### 评分汇总

| 维度 | Karpathy | 我们 | 评分 |
|------|----------|------|------|
| 架构一致性 | 三层架构 | 三层架构 | 90/100 |
| Ingest 流程 | LLM 手动 | 脚本自动 | 95/100 |
| Query 能力 | LLM 综合 | 基础搜索 | 60/100 |
| Lint 能力 | LLM 检查 | 脚本检查 | 75/100 |
| 索引和日志 | 自动生成 | 自动生成 | 100/100 |
| 自进化能力 | LLM 建议 | 脚本发现 | 80/100 |
| LLM 集成 | 完全集成 | 无集成 | 30/100 |
| **平均** | | | **75.7/100** |

### 核心差距

1. **LLM 自动维护 (30/100)** - 最核心差距
   - Karpathy: LLM 读取来源，自动整合到 wiki
   - 我们: 脚本自动处理，无 LLM 参与

2. **Query 答案存回 (60/100)**
   - Karpathy: 好答案可以存回 wiki
   - 我们: 有基础实现但不完善

3. **矛盾检测 (75/100)**
   - Karpathy: 自动标记矛盾
   - 我们: 有基础实现

### 我们的优势

1. **自动化程度更高**
   - Karpathy: 手动 ingest
   - 我们: 完全自动化的 cron job

2. **数据采集更完善**
   - Karpathy: 手动收集来源
   - 我们: 自动新闻搜索 + 财报下载

3. **结构化程度更高**
   - Karpathy: 通用 markdown
   - 我们: YAML frontmatter + 时间线格式

4. **领域特化**
   - Karpathy: 通用知识库
   - 我们: 上市公司研究专用

---

## 四、改进建议

### P0: 添加 LLM 集成（最核心）

```python
# ingest_with_llm.py
def ingest_with_llm(source_file: Path, wiki_context: str) -> List[WikiUpdate]:
    """
    LLM 参与的 ingest 流程
    
    1. LLM 读取来源
    2. LLM 提取关键信息
    3. LLM 判断相关性
    4. LLM 生成 wiki 更新
    5. LLM 检查矛盾
    """
    content = source_file.read_text()
    
    # 调用 LLM
    prompt = f"""
    来源内容:
    {content}
    
    现有 wiki 上下文:
    {wiki_context}
    
    请:
    1. 提取关键信息
    2. 判断影响哪些主题
    3. 生成时间线条目
    4. 检查是否与现有信息矛盾
    """
    
    response = llm.generate(prompt)
    return parse_llm_response(response)
```

### P1: 完善 Query → Wiki 存回

```python
def save_query_result(question: str, answer: str, sources: List[str]) -> Path:
    """
    将查询结果存回 wiki
    
    1. 判断答案质量
    2. 确定目标实体
    3. 生成 wiki 页面
    4. 更新交叉引用
    """
    if answer_quality(answer) < 0.7:
        return None
    
    target_entity = find_relevant_entity(question, sources)
    wiki_page = generate_wiki_page(question, answer, sources)
    
    return save_to_wiki(target_entity, wiki_page)
```

### P2: 增强矛盾检测

```python
def detect_contradictions_llm(old_claim: str, new_claim: str) -> Optional[Contradiction]:
    """
    使用 LLM 检测矛盾
    
    1. LLM 比较两个声明
    2. 判断是否矛盾
    3. 生成解释
    """
    prompt = f"""
    旧声明: {old_claim}
    新声明: {new_claim}
    
    这两个声明是否矛盾？请解释。
    """
    
    response = llm.generate(prompt)
    return parse_contradiction(response)
```

---

## 五、结论

### 总体完成度: 75.7%

**已完成**:
- ✅ 三层架构 (90%)
- ✅ Ingest 流程 (95%)
- ✅ 索引和日志 (100%)
- ✅ 自进化能力 (80%)

**需要改进**:
- ⚠️ Query 能力 (60%)
- ⚠️ Lint 能力 (75%)
- ❌ LLM 集成 (30%)

### 核心差距

**LLM 集成是最大差距**，但这可能是有意为之：
- 我们的系统是全自动化的
- 不需要人工参与
- 适合批量处理大量数据
- 成本更低（无 LLM API 调用）

### 建议

如果要完全匹配 Karpathy 概念：
1. 添加 LLM 参与 ingest 流程
2. 完善 Query → Wiki 存回
3. 增强矛盾检测

如果要保持当前优势：
1. 保持自动化程度
2. 保持数据采集能力
3. 保持结构化程度
4. 在需要时添加 LLM 增强

**我们的系统更适合批量处理大量数据，而 Karpathy 的概念更适合深度研究少量主题。**