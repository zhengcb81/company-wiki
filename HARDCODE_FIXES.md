# 硬编码改进总结

## 改进内容

### 1. 新增配置文件 `config_rules.yaml`

将所有硬编码的规则提取到统一的配置文件中：

```yaml
config_rules.yaml
├── document_classification   # 文档分类规则
├── question_keywords         # 问题关键词映射
├── topic_keywords            # 主题发现关键词
├── company_name_patterns     # 公司名称模式
├── question_patterns         # 问题模式
├── low_quality_sources       # 低质量来源过滤
└── noise_patterns            # 噪音过滤模式
```

### 2. 修改的脚本

#### `classify_documents.py`
**之前**：
```python
# 年报
if re.search(r'(\d{4})年年度报告', filename):
    return DocumentType.ANNUAL_REPORT, 0.95, "文件名包含'年年度报告'"
```

**之后**：
```python
# 从配置文件加载规则
CLASSIFICATION_RULES = load_classification_rules()

for rule_name, rule_config in CLASSIFICATION_RULES.items():
    patterns = rule_config.get("patterns", [])
    # 使用配置中的模式
```

#### `ingest/updater.py`
**之前**：
```python
keyword_patterns = {
    "国产化率": ["国产化", "国产替代", "自主可控", "国产"],
    "先进制程": ["先进制程", "制程", "nm", "纳米"],
    # ... 硬编码
}
```

**之后**：
```python
def _load_question_keywords(self):
    config_path = self.wiki_root / "config_rules.yaml"
    # 从配置文件加载
    return config.get("question_keywords", default_keywords)
```

#### `auto_discover.py`
**之前**：
```python
topic_keywords = {
    "Chiplet": ["Chiplet", "芯粒", "小芯片"],
    "HBM": ["HBM", "高带宽内存", "High Bandwidth Memory"],
    # ... 硬编码
}
```

**之后**：
```python
TOPIC_KEYWORDS = load_topic_keywords()

def extract_topics(text):
    for topic, keywords in TOPIC_KEYWORDS.items():
        # 使用配置中的关键词
```

#### `extract.py`
**之前**：
```python
NOISE_PATTERNS = [
    r'^#{1,6}\s*(关于|产品|支持|联系|服务|首页|导航|菜单|公司简介|版权所有)',
    # ... 硬编码
]
```

**之后**：
```python
NOISE_PATTERNS = load_noise_patterns()
```

#### `ingest.py`
**之前**：
```python
skip_url_patterns = [
    "quote.eastmoney.com",
    "quote.futunn.com",
    # ... 硬编码
]
```

**之后**：
```python
LOW_QUALITY_SOURCES = load_low_quality_sources()
skip_url_patterns = LOW_QUALITY_SOURCES.get("url_patterns", [])
```

### 3. 配置文件结构

```yaml
# ── 文档分类规则 ──────────────────────────
document_classification:
  annual_report:
    patterns:
      - "年年度报告"
      - "年年报"
    confidence: 0.95
    target_dir: "financial_reports/annual"
  
  semi_annual_report:
    patterns:
      - "半年度报告"
      - "半年报"
    confidence: 0.95
    target_dir: "financial_reports/semi_annual"
  
  # ... 更多规则

# ── 问题关键词映射 ──────────────────────────
question_keywords:
  国产化率:
    - "国产化"
    - "国产替代"
    - "自主可控"
    - "国产"
    - "本土化"
  
  先进制程:
    - "先进制程"
    - "制程"
    - "nm"
    - "纳米"
    - "工艺节点"
  
  # ... 更多关键词

# ── 主题发现关键词 ──────────────────────────
topic_keywords:
  Chiplet:
    - "Chiplet"
    - "芯粒"
    - "小芯片"
    - "异构集成"
  
  HBM:
    - "HBM"
    - "高带宽内存"
    - "High Bandwidth Memory"
    - "HBM3"
    - "HBM3E"
  
  # ... 更多主题

# ── 低质量来源过滤 ──────────────────────────
low_quality_sources:
  url_patterns:
    - "quote.eastmoney.com"
    - "quote.futunn.com"
    # ...
  
  title_patterns:
    - "行情走势"
    - "股票股价"
    # ...
  
  file_patterns:
    - "行情走势"
    - "公司简介"
    # ...

# ── 噪音过滤 ──────────────────────────
noise_patterns:
  - "^(关于|产品|支持|联系|服务|首页|导航|菜单|公司简介|版权所有)"
  - "(登录|注册|搜索|订阅|分享|收藏|点赞|评论区|版权所有|版权声明)"
  # ...
```

### 4. 优势

#### ✅ 可维护性
- 所有规则集中在一个配置文件
- 修改规则无需修改代码
- 便于版本控制

#### ✅ 可扩展性
- 添加新规则只需修改配置文件
- 支持动态加载
- 向后兼容（有默认值）

#### ✅ 灵活性
- 用户可以根据需要自定义规则
- 支持不同行业/领域的规则
- 便于 A/B 测试

#### ✅ 可读性
- 配置文件有清晰的注释
- 结构化的组织方式
- 易于理解

### 5. 使用示例

#### 添加新的文档分类规则
```yaml
document_classification:
  # 添加新的分类
  investor_presentation:
    patterns:
      - "投资者演示"
      - "业绩说明会"
      - "路演"
    confidence: 0.85
    target_dir: "investor_relations/presentations"
```

#### 添加新的主题关键词
```yaml
topic_keywords:
  # 添加新的主题
  RISC-V:
    - "RISC-V"
    - "开源芯片"
    - "指令集"
```

#### 添加新的低质量来源
```yaml
low_quality_sources:
  url_patterns:
    - "new-spam-site.com"
    - "another-noise-source.com"
```

### 6. 测试

```bash
# 测试配置加载
python3 -c "
import sys
sys.path.insert(0, 'scripts')
from classify_documents import load_classification_rules
from extract import load_noise_patterns

rules = load_classification_rules()
print(f'Rules loaded: {len(rules)}')

noise = load_noise_patterns()
print(f'Noise patterns loaded: {len(noise)}')
"
```

### 7. 下一步

- [ ] 添加配置文件验证
- [ ] 支持多个配置文件合并
- [ ] 添加配置热重载
- [ ] 添加配置可视化工具