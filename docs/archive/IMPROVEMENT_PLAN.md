# company-wiki 改进计划

> 版本: 1.0
> 创建日期: 2026-04-17
> 目标: 完全实现原始设计理念

## 当前状态分析

### 已完成 ✅
1. 每个公司有独立子目录
2. 文件已在 raw 目录下（reports/research/news）
3. 按主题的时间线文档
4. 行业/主题子目录
5. 交叉引用（一条新闻可更新公司和行业）
6. 新闻搜索和采集
7. 定期运行（cronjob）
8. 自动整理到时间线

### 未完全实现 ⚠️/❌

#### 1. 原始文档按类型细分 ⚠️
**当前**：
```
companies/中微公司/raw/
├── reports/      # 所有PDF报告
├── research/     # 研究文档
└── news/         # 新闻
```

**需求**：
```
companies/中微公司/raw/
├── financial_reports/      # 定期财报（年报、季报、半年报）
├── prospectus/             # 招股说明书
├── announcements/          # 重要公告（股权变动、高管变动等）
├── investor_relations/     # 投资者关系文档
├── research/               # 券商研报
└── news/                   # 新闻文章
```

#### 2. 问题匹配机制 ❌
**当前**：只是提取摘要，没有与问题清单对比

**需求**：根据预设问题检查新闻/公告是否提供了更新回答

#### 3. 自动进化能力 ❌
**当前**：只能手动添加公司/主题

**需求**：从新闻中自动发现新公司、新主题

---

## 改进计划

### Phase 1: 原始文档按类型细分 (1-2天)

#### 1.1 分析现有文件类型
- 扫描所有 PDF 文件
- 根据文件名识别类型（财报、招股说明书、公告等）
- 生成分类报告

#### 1.2 创建新的目录结构
```
companies/{公司名}/raw/
├── financial_reports/      # 定期财报
│   ├── annual/            # 年报
│   ├── semi_annual/       # 半年报
│   └── quarterly/         # 季报
├── prospectus/            # 招股说明书
├── announcements/         # 重要公告
├── investor_relations/    # 投资者关系文档
├── research/              # 券商研报
└── news/                  # 新闻文章
```

#### 1.3 移动现有文件
- 根据文件名模式自动分类
- 移动到对应的子目录
- 保持向后兼容（ingest.py 仍能扫描所有文件）

#### 1.4 更新采集脚本
- 更新 StockInfoDownloader 配置，将文件保存到正确目录
- 更新 ingest.py，识别文件类型

### Phase 2: 问题匹配机制 (2-3天)

#### 2.1 设计问题匹配算法
```python
def match_content_to_questions(content, questions):
    """
    检查内容是否回答了预设问题
    
    Args:
        content: 新闻/公告内容
        questions: 问题列表
        
    Returns:
        [
            {
                "question": "各环节设备国产化率？",
                "relevance_score": 0.85,
                "answer_summary": "中微公司刻蚀设备国产化率达到...",
                "key_points": ["国产化率提升", "技术突破"]
            }
        ]
    """
```

#### 2.2 实现语义匹配
- 使用 LLM 进行语义匹配
- 或使用 Embedding 进行相似度计算

#### 2.3 集成到 ingest 流程
- 在提取摘要后，检查问题匹配
- 如果匹配，记录到时间线条目中

#### 2.4 更新时间线格式
```markdown
### 2026-04-16 | 新闻 | 中微公司发布新一代刻蚀设备
- 刻蚀精度提升30%
- 产能提高20%

**回答问题**：
- [各环节设备国产化率？] 刻蚀设备国产化率提升至...
- [先进制程设备进展？] 新设备支持5nm以下制程...

- [来源](../raw/news/2026-04-16_xxx.md)
```

### Phase 3: 自动进化能力 (3-5天)

#### 3.1 新公司发现
```python
def discover_new_companies(news_content, known_companies):
    """
    从新闻中发现未跟踪的公司
    
    Args:
        news_content: 新闻内容
        known_companies: 已知公司列表
        
    Returns:
        [
            {
                "name": "新公司名称",
                "context": "新闻中提及的上下文",
                "suggested_sectors": ["半导体设备"],
                "confidence": 0.8
            }
        ]
    """
```

#### 3.2 新主题发现
```python
def discover_new_topics(news_cluster):
    """
    从新闻聚类中发现新主题
    
    Args:
        news_cluster: 相关新闻集合
        
    Returns:
        [
            {
                "topic_name": "Chiplet技术",
                "description": "芯片封装新技术",
                "related_companies": ["长电科技", "通富微电"],
                "suggested_questions": [
                    "Chiplet技术进展？",
                    "主要厂商布局？"
                ]
            }
        ]
    """
```

#### 3.3 问题清单进化
```python
def evolve_questions(existing_questions, news_insights):
    """
    根据新闻洞察更新问题清单
    
    Args:
        existing_questions: 现有问题
        news_insights: 新闻洞察
        
    Returns:
        {
            "new_questions": ["新问题1", "新问题2"],
            "outdated_questions": ["过时问题1"],
            "updated_questions": {
                "旧问题": "更新后的问题"
            }
        }
    """
```

#### 3.4 实现自动建议
- 定期运行发现脚本
- 生成建议报告
- 用户确认后自动执行

### Phase 4: 增强监控和报告 (1-2天)

#### 4.1 覆盖度报告
- 哪些公司有数据
- 哪些主题有更新
- 哪些问题有回答

#### 4.2 质量报告
- 时间线条目质量
- 来源覆盖度
- 信息新鲜度

#### 4.3 建议报告
- 建议添加的公司
- 建议添加的主题
- 建议更新的问题

---

## 实施步骤

### Step 1: 文档分类重构
```bash
# 1. 创建分类脚本
python3 scripts/classify_documents.py

# 2. 运行分类
python3 scripts/classify_documents.py --company 中微公司

# 3. 验证结果
python3 scripts/classify_documents.py --verify
```

### Step 2: 问题匹配实现
```bash
# 1. 测试问题匹配
python3 scripts/question_matcher.py --test

# 2. 集成到 ingest
python3 scripts/ingest.py --enable-question-matching

# 3. 验证结果
python3 scripts/ingest.py --verify-questions
```

### Step 3: 自动进化实现
```bash
# 1. 运行发现脚本
python3 scripts/auto_discover.py

# 2. 查看建议
python3 scripts/auto_discover.py --show-suggestions

# 3. 应用建议
python3 scripts/auto_discover.py --apply
```

---

## 测试计划

### Phase 1 测试
- [ ] 文件分类正确性测试
- [ ] 向后兼容性测试
- [ ] 采集脚本测试

### Phase 2 测试
- [ ] 问题匹配准确性测试
- [ ] 时间线格式测试
- [ ] 性能测试

### Phase 3 测试
- [ ] 新公司发现测试
- [ ] 新主题发现测试
- [ ] 问题进化测试

### Phase 4 测试
- [ ] 报告生成测试
- [ ] 端到端测试

---

## 时间表

| Phase | 任务 | 预计时间 | 状态 |
|-------|------|----------|------|
| 1 | 文档分类重构 | 1-2天 | ✅ 完成 |
| 2 | 问题匹配机制 | 2-3天 | ✅ 完成 |
| 3 | 自动进化能力 | 3-5天 | ✅ 完成 |
| 4 | 监控和报告 | 1-2天 | ✅ 完成 |
| **总计** | | **7-12天** | ✅ **全部完成** |

---

## 风险和缓解

### 风险1: 文件分类不准确
**缓解**：使用多种规则（文件名、内容、PDF元数据）进行分类，人工审核边界情况

### 风险2: 问题匹配不准确
**缓解**：结合规则匹配和语义匹配，提供人工确认机制

### 风险3: 自动发现产生噪音
**缓解**：设置置信度阈值，提供人工审核机制

### 风险4: 性能问题
**缓解**：异步处理，增量更新，缓存机制