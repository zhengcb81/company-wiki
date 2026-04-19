# 架构文档

> 最后更新: 2026-04-17

## 系统概述

company-wiki 是一个基于 LLM 的上市公司知识库系统，自动采集、整理、分析上市公司信息。

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                │
│  CLI 命令 / Python API / 查询界面                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       应用层                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   采集模块   │  │   处理模块   │  │   查询模块   │         │
│  │ collect_news │  │   ingest    │  │    query    │         │
│  │   download   │  │   extract   │  │    graph    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       基础设施层                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   配置管理   │  │   日志管理   │  │   工具函数   │         │
│  │   config    │  │   logger    │  │    utils    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   存储层    │  │   异步处理   │  │   错误处理   │         │
│  │   storage   │  │ async_utils │  │error_handling│         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       数据层                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  文件系统                             │   │
│  │  graph.yaml / companies/ / sectors/ / themes/        │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  SQLite 数据库                       │   │
│  │  wiki.db (可选，用于大规模数据)                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 核心模块

### 1. 数据采集模块

**职责**: 从外部数据源采集原始数据

**组件**:
- `collect_news.py`: 新闻采集（Tavily API）
- `collect_reports.py`: 财报/公告/投资者关系下载（StockInfoDownloader）

**数据流**:
```
外部数据源 → 采集脚本 → companies/{公司}/raw/
```

### 2. 数据处理模块

**职责**: 将原始数据整理为结构化知识

**组件**:
- `ingest.py`: 主处理流水线
- `extract.py`: 内容提取
- `classify_documents.py`: 文档分类
- `refine.py`: 内容精炼

**数据流**:
```
companies/{公司}/raw/ → 处理流水线 → companies/{公司}/wiki/
```

### 3. 查询分析模块

**职责**: 提供知识查询和分析功能

**组件**:
- `query.py`: 智能查询
- `graph.py`: 图数据查询
- `auto_discover.py`: 自动发现
- `contradiction_detector.py`: 矛盾检测

**数据流**:
```
用户查询 → 查询模块 → wiki 文件 → 答案
```

### 4. 基础设施模块

**职责**: 提供通用功能支持

**组件**:
- `config.py`: 统一配置管理
- `logger.py`: 统一日志管理
- `utils.py`: 公共工具函数
- `storage/`: 存储层
- `async_utils/`: 异步处理
- `error_handling/`: 错误处理

## 数据模型

### 实体模型

```yaml
# 公司
Company:
  name: str
  ticker: str
  exchange: str
  sectors: List[str]
  themes: List[str]
  position: str
  news_queries: List[str]

# 行业
Sector:
  name: str
  type: str  # sector | subsector
  description: str
  tier: int
  keywords: List[str]
  parent_theme: List[str]
  parent_sector: List[str]

# 主题
Theme:
  name: str
  description: str
  keywords: List[str]
```

### 关系模型

```yaml
# 边
Edge:
  from: str
  to: str
  type: str  # upstream_of | belongs_to
  label: str
```

## 数据流

### 1. 数据采集流

```
定时任务 (cronjob)
    │
    ▼
collect_news.py
    │
    ├─→ companies/{公司}/raw/news/*.md
    │
    ▼
collect_reports.py (StockInfoDownloader)
    │
    ├─→ companies/{公司}/raw/financial_reports/*.pdf
    ├─→ companies/{公司}/raw/prospectus/*.pdf
    └─→ companies/{公司}/raw/investor_relations/*.pdf
```

### 2. 数据处理流

```
companies/{公司}/raw/
    │
    ▼
ingest.py
    │
    ├─→ 读取新文件
    ├─→ 提取摘要 (extract.py)
    ├─→ 判断相关性 (graph.py)
    └─→ 更新 wiki (ingest/updater.py)
            │
            ├─→ companies/{公司}/wiki/*.md
            ├─→ sectors/{行业}/wiki/*.md
            └─→ themes/{主题}/wiki/*.md
```

### 3. 查询流

```
用户查询
    │
    ▼
query.py
    │
    ├─→ 搜索 wiki (WikiSearcher)
    ├─→ 综合答案 (AnswerSynthesizer)
    └─→ 存回 wiki (AnswerSaver)
```

## 配置管理

### 配置层次

```
环境变量 (最高优先级)
    │
    ▼
config.yaml
    │
    ▼
默认值 (最低优先级)
```

### 配置文件

```
config.yaml          # 主配置
config_rules.yaml    # 分类规则
graph.yaml          # 公司/行业/主题数据
pytest.ini          # 测试配置
```

## 存储设计

### 文件存储

```
~/company-wiki/
├── companies/
│   └── {公司名}/
│       ├── raw/
│       │   ├── news/
│       │   ├── financial_reports/
│       │   │   ├── annual/
│       │   │   ├── semi_annual/
│       │   │   └── quarterly/
│       │   ├── prospectus/
│       │   ├── investor_relations/
│       │   ├── research/
│       │   └── announcements/
│       └── wiki/
│           ├── 公司动态.md
│           └── 相关动态.md
├── sectors/
│   └── {行业名}/
│       ├── raw/
│       └── wiki/
├── themes/
│   └── {主题名}/
│       ├── raw/
│       └── wiki/
├── graph.yaml
├── config.yaml
└── logs/
```

### 数据库存储（可选）

```sql
-- 公司表
CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    ticker TEXT,
    exchange TEXT,
    sectors TEXT,  -- JSON
    themes TEXT,   -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Wiki 条目表
CREATE TABLE wiki_entries (
    id INTEGER PRIMARY KEY,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    topic_name TEXT NOT NULL,
    content TEXT,
    last_updated DATE,
    sources_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 错误处理

### 错误分类

```
RetryableError: 可重试错误（网络超时、API 限流）
PermanentError: 永久性错误（配置错误、权限不足）
```

### 重试策略

```python
from error_handling import RetryPolicy

policy = RetryPolicy(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    strategy="exponential",  # exponential | fixed | random
)

@policy
def flaky_function():
    # 可能失败的函数
    pass
```

### 熔断器

```python
from error_handling import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
)

@breaker
def protected_function():
    # 受保护的函数
    pass
```

## 监控

### 日志

```python
from logger import get_logger

logger = get_logger(__name__)
logger.info("处理完成")
logger.error("发生错误", exc_info=True)
```

### 指标

```python
from monitoring import MetricsCollector

metrics = MetricsCollector()
metrics.counter("requests_total", 1.0)
metrics.gauge("memory_usage", 1024.0)
```

### 健康检查

```python
from monitoring import HealthChecker

checker = HealthChecker()
checker.register_check("database", check_database)
status = checker.get_overall_status()
```

## 扩展点

### 1. 数据源扩展

- 添加新的新闻源
- 添加新的文档类型
- 添加新的 API 集成

### 2. 处理逻辑扩展

- 自定义分类规则
- 自定义提取逻辑
- 自定义分析算法

### 3. 查询功能扩展

- 自定义查询接口
- 自定义答案格式
- 自定义可视化

## 部署架构

### 单机部署

```
┌─────────────────────────────────────────┐
│              单机部署                    │
├─────────────────────────────────────────┤
│  应用: company-wiki                      │
│  数据: ~/company-wiki/                   │
│  配置: config.yaml                       │
│  日志: ~/company-wiki/logs/              │
│  定时: cronjob                           │
└─────────────────────────────────────────┘
```

### 分布式部署（未来）

```
┌─────────────────────────────────────────┐
│              分布式部署                  │
├─────────────────────────────────────────┤
│  采集服务: collect-service               │
│  处理服务: process-service               │
│  查询服务: query-service                 │
│  存储服务: storage-service               │
└─────────────────────────────────────────┘
```

## 性能优化

### 1. 并发处理

```python
from async_utils import AsyncExecutor

executor = AsyncExecutor(max_workers=10, max_concurrent=5)
results = await executor.run_tasks(tasks)
```

### 2. 缓存

- 文件哈希缓存
- 查询结果缓存
- 配置缓存

### 3. 批量处理

- 批量文件扫描
- 批量数据库操作
- 批量 API 调用

## 安全考虑

### 1. 密钥管理

- 使用环境变量存储密钥
- 不将密钥提交到代码库
- 定期轮换密钥

### 2. 文件权限

- 限制文件访问权限
- 使用最小权限原则

### 3. 输入验证

- 验证文件路径
- 验证配置格式
- 验证 API 输入