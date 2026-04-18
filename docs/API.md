# API 文档

> 最后更新: 2026-04-17

## 核心模块

### 1. Config - 统一配置管理

```python
from config import Config, load_config
```

#### Config.load(config_path=None)
加载配置

**参数**:
- `config_path` (Path, 可选): 配置文件路径，默认为 `~/company-wiki/config.yaml`

**返回**: Config 对象

**异常**:
- `FileNotFoundError`: 配置文件不存在
- `ValueError`: 配置验证失败

**示例**:
```python
from config import Config

# 加载默认配置
config = Config.load()

# 加载指定配置
config = Config.load(Path("/path/to/config.yaml"))
```

#### Config.validate(strict=True)
验证配置

**参数**:
- `strict` (bool): 是否严格验证

**异常**:
- `ValueError`: 配置验证失败

#### Config.get_llm_api_key()
获取 LLM API Key

**返回**: str

#### Config.get_search_api_key()
获取搜索 API Key

**返回**: str

#### Config.get_wiki_root()
获取 Wiki 根目录

**返回**: Path

#### Config.to_dict()
转换为字典

**返回**: Dict[str, Any]

---

### 2. Logger - 统一日志管理

```python
from logger import get_logger, setup_logging, LogContext
```

#### get_logger(name)
获取日志器

**参数**:
- `name` (str): 日志器名称，通常使用 `__name__`

**返回**: logging.Logger

**示例**:
```python
from logger import get_logger

logger = get_logger(__name__)
logger.info("处理完成")
logger.error("发生错误", exc_info=True)
```

#### setup_logging(level="INFO", log_file=None, console=True)
设置全局日志配置

**参数**:
- `level` (str): 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `log_file` (Path, 可选): 日志文件路径
- `console` (bool): 是否输出到控制台

#### LogContext(logger, message)
日志上下文管理器

**示例**:
```python
from logger import LogContext

with LogContext(logger, "处理文件"):
    # 处理逻辑
    pass
```

---

### 3. Utils - 公共工具函数

```python
from utils import (
    log_message,
    load_yaml, save_yaml,
    ensure_dir, safe_read_file, safe_write_file,
    extract_frontmatter, clean_text, extract_keywords,
    to_bool, to_int, to_float,
    is_valid_ticker, is_empty_dir,
)
```

#### 日志相关

##### log_message(message, log_path=None)
记录日志消息到文件

**参数**:
- `message` (str): 日志消息
- `log_path` (Path, 可选): 日志文件路径

#### 文件操作

##### ensure_dir(path)
确保目录存在

**参数**:
- `path` (Path): 目录路径

**返回**: Path

##### safe_read_file(file_path, encoding="utf-8")
安全读取文件

**参数**:
- `file_path` (Path): 文件路径
- `encoding` (str): 编码

**返回**: Optional[str]

##### safe_write_file(file_path, content, encoding="utf-8")
安全写入文件

**参数**:
- `file_path` (Path): 文件路径
- `content` (str): 内容
- `encoding` (str): 编码

**返回**: bool

#### 配置加载

##### load_yaml(file_path)
加载 YAML 文件

**参数**:
- `file_path` (Path): 文件路径

**返回**: Dict[str, Any]

##### save_yaml(file_path, data)
保存 YAML 文件

**参数**:
- `file_path` (Path): 文件路径
- `data` (Dict): 数据

**返回**: bool

#### 路径工具

##### get_wiki_root()
获取 Wiki 根目录

**返回**: Path

##### get_companies_dir()
获取公司目录

**返回**: Path

##### get_company_dir(company_name)
获取指定公司的目录

**参数**:
- `company_name` (str): 公司名称

**返回**: Path

#### 文本处理

##### extract_frontmatter(content)
提取 Markdown frontmatter

**参数**:
- `content` (str): Markdown 内容

**返回**: Dict[str, str]

**示例**:
```python
content = '''---
title: "测试"
date: "2026-04-17"
---

# 内容
'''

frontmatter = extract_frontmatter(content)
# {'title': '测试', 'date': '2026-04-17'}
```

##### clean_text(text)
清理文本

**参数**:
- `text` (str): 原始文本

**返回**: str

##### extract_keywords(text, min_length=2, max_length=10)
提取关键词

**参数**:
- `text` (str): 文本
- `min_length` (int): 最小长度
- `max_length` (int): 最大长度

**返回**: List[str]

#### 数据转换

##### to_bool(value)
转换为布尔值

**参数**:
- `value` (Any): 任意值

**返回**: bool

##### to_int(value, default=0)
转换为整数

**参数**:
- `value` (Any): 任意值
- `default` (int): 默认值

**返回**: int

##### to_float(value, default=0.0)
转换为浮点数

**参数**:
- `value` (Any): 任意值
- `default` (float): 默认值

**返回**: float

#### 验证工具

##### is_valid_ticker(ticker)
检查是否是有效的股票代码

**参数**:
- `ticker` (str): 股票代码

**返回**: bool

**示例**:
```python
is_valid_ticker("688012")  # True (A股)
is_valid_ticker("NVDA")    # True (美股)
is_valid_ticker("0020.HK") # True (港股)
```

##### is_empty_dir(path)
检查目录是否为空

**参数**:
- `path` (Path): 目录路径

**返回**: bool

---

### 4. Graph - 图数据查询

```python
from graph import Graph
```

#### Graph(graph_path=None)
创建 Graph 实例

**参数**:
- `graph_path` (str, 可选): graph.yaml 路径

**示例**:
```python
from graph import Graph

g = Graph()
```

#### Graph.get_all_companies()
获取所有公司

**返回**: List[Dict]

#### Graph.get_company(name)
获取单个公司

**参数**:
- `name` (str): 公司名称

**返回**: Optional[Dict]

#### Graph.get_all_sectors()
获取所有行业

**返回**: List[str]

#### Graph.get_sector(name)
获取单个行业

**参数**:
- `name` (str): 行业名称

**返回**: Optional[Dict]

#### Graph.find_related_entities(text, company_hint=None)
查找相关实体

**参数**:
- `text` (str): 文本
- `company_hint` (str, 可选): 公司提示

**返回**: List[Tuple[str, str, str]]

---

### 5. Ingest - 数据整理

```python
from ingest import IngestPipeline
```

#### IngestPipeline(config, graph_queries)
创建流水线

**参数**:
- `config` (Config): 配置对象
- `graph_queries` (GraphQueries): 图查询接口

#### IngestPipeline.run(company=None, dry_run=False, limit=0)
运行流水线

**参数**:
- `company` (str, 可选): 只处理指定公司
- `dry_run` (bool): 只检查不执行
- `limit` (int): 最多处理文件数

**返回**: PipelineResult

**示例**:
```python
from config import Config
from graph import Graph
from ingest import IngestPipeline

config = Config.load()
graph = Graph()
pipeline = IngestPipeline(config, graph._queries)

result = pipeline.run(company="中微公司")
print(result.summary())
```

---

### 6. Query - 智能查询

```python
from query import WikiSearcher, AnswerSynthesizer
```

#### WikiSearcher(wiki_root)
创建搜索器

**参数**:
- `wiki_root` (Path): Wiki 根目录

#### WikiSearcher.search(query, max_results=10)
搜索 wiki 页面

**参数**:
- `query` (str): 搜索查询
- `max_results` (int): 最大结果数

**返回**: List[SearchResult]

#### AnswerSynthesizer(wiki_root)
创建答案综合器

**参数**:
- `wiki_root` (Path): Wiki 根目录

#### AnswerSynthesizer.synthesize(question, search_results)
综合答案

**参数**:
- `question` (str): 问题
- `search_results` (List[SearchResult]): 搜索结果

**返回**: QueryAnswer

---

## 数据模型

### Config
```python
@dataclass
class Config:
    llm: LLMConfig
    search: SearchConfig
    schedule: ScheduleConfig
    downloader: DownloaderConfig
    paths: PathsConfig
```

### PipelineResult
```python
@dataclass
class PipelineResult:
    updated: List[Tuple[str, str]]
    skipped: List[str]
    errors: List[Tuple[str, str]]
    
    @property
    def success_count(self) -> int
    @property
    def error_count(self) -> int
    @property
    def success_rate(self) -> float
    def summary(self) -> str
```

### SearchResult
```python
@dataclass
class SearchResult:
    page: WikiPage
    relevance_score: float
    matched_sections: List[str]
```

### QueryAnswer
```python
@dataclass
class QueryAnswer:
    question: str
    answer: str
    sources: List[WikiPage]
    confidence: str
    generated_at: str
```

---

## CLI 命令

### 配置检查
```bash
python3 scripts/config.py
```

### 数据采集
```bash
# 采集新闻
python3 scripts/collect_news.py

# 下载财报
python3 scripts/download_reports_v2.py --company 中微公司
```

### 数据处理
```bash
# 整理数据
python3 scripts/ingest.py

# 分类文档
python3 scripts/classify_documents.py
```

### 查询分析
```bash
# 查看产业链
python3 scripts/graph.py --overview

# 查询公司
python3 scripts/query.py "中微公司的刻蚀设备进展？"
```

### 测试
```bash
# 运行所有测试
python3 -m pytest tests/ -v

# 运行单元测试
python3 -m pytest tests/unit/ -v
```