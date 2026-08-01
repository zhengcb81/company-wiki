# 架构文档

> 最后更新: 2026-07-17

## 系统概述

company-wiki 是 StockWiki 的上游来源系统。canonical 职责是采集、immutable raw、source manifest、文档规范化、EvidenceSpan、解析质量、全文索引和只读 export；StockWiki 独占投资研究、人工证据裁决、估值、研究 Wiki 与报告发布。

系统不生成或持久化 accepted/rejected 投资结论，不写入 StockWiki 的目录或数据库。legacy Wiki/Index/Log 仅保留为只读兼容或 source-oriented projection，不是 canonical state。

## 架构图

```
外部来源
   │
   ▼
collect / download
   │
   ▼
immutable raw ──→ source manifest（稳定 ID、hash、采集元数据）
   │
   ▼
normalize / parse ──→ EvidenceSpan（locator、原文/结构化值、解析质量）
   │
   ├──→ 全文索引 / 原文预览 / 资料型问答
   └──→ 版本化只读 export ──→ StockWiki 等消费者
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

### 2. 规范化与解析模块

**职责**: 验证 immutable raw 身份，生成 source manifest、规范化内容、EvidenceSpan 和 extraction quality；相同输入与版本必须产生相同 ID/hash。

`company_wiki.ingest.IngestService` 已发布首个 source-only 垂直切片：接收 `SourceManifest + ParserResult`，生成 `EvidenceSpan + SourceExportBundle`，并保持全程只读。`scripts/ingest_v2.py`、`stage5_ingest.py`、`extract.py`、`classify_documents.py`、`refine.py` 等仍是待迁移的 legacy 实现，不得把其中的 Wiki/review writer 当作新功能入口。

**数据流**:
```
immutable raw → normalize/parse → manifest + evidence spans + parse diagnostics
```

### 3. 资料检索与导出模块

**职责**: 提供全文检索、原文预览、带 source ID/locator 的资料答案，以及版本化只读 export。

**组件**:
- `company_wiki.source_contract.cli`: 校验 raw/manifest/span，执行 add-only incremental merge，并向 stdout 输出 canonical Source Export v1
- `query.py`: legacy 查询入口，迁移后只返回资料答案/evidence bundle
- `graph.py`: 图数据查询
- `auto_discover.py`: 自动发现
- `contradiction_detector.py`: 来源/解析诊断；不得裁决投资命题

**数据流**:
```
用户/消费者 → manifest/span/index → 带 locator 的答案或只读 export
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

### Canonical source contract（CW-1）

正式字段、身份算法与失败语义见 [Announcement Collector v1](contracts/announcement-collector-v1.md)、[Source Manifest v1](contracts/source-manifest-v1.md)、[Evidence Span v1](contracts/evidence-span-v1.md)、[Source Export v1](contracts/source-export-v1.md)、[Canonical IngestService v1](contracts/ingest-service-v1.md) 和 [Source Contract Compatibility Policy v1](contracts/source-contract-compatibility-v1.md)。

- **AnnouncementCollectionReceipt**：把显式交易所官方 URL、最终 URL、标题、HTTP provenance 和 content-addressed raw/manifest 路径绑定到稳定 collection ID；采集仅允许 create-once，不具备 overwrite 权限。
- **SourceRecord / source manifest**：稳定 `source_id`、entity ID、original path、SHA-256、source type、发布时间/采集时间、collector/version、MIME、size 和 immutable 状态。
- **EvidenceSpan**：绑定 `source_id` 的稳定 locator，包含页/段/表格坐标、原文或结构化值、parser/version、output hash、parse status 和 quality flags。
- **SourceExportBundle**：按 ID 排序的 manifest/span 快照；不含运行时间，通过 `bundle_sha256` 和内容寻址 `export_id` 支持 full replay 与 add-only incremental merge。
- **ParserResult / IngestService**：进程内不可变 parser 适配值与唯一 source-only ingest 边界；复用 manifest/span/export 合同完成 raw 验证、source 绑定、冲突检测和重放，不新增持久化研究状态。
- **CompatibilityPolicy**：机器可读地列出三个 contract 的 current/supported 精确版本、允许的完整版本组合、兼容窗口与弃用通知；consumer 必须只从 `compatible_version_sets` 做原子 `exact_highest` 协商，不能构造未发布组合或假设同 major 自动兼容。
- **状态语义**：只表达 source/extraction quality。任何 `accepted` 都不表示 accepted investment conclusion。
- **集成语义**：消费者通过只读 export 按 ID/hash 引用；不得共享可变数据库或反向改写 raw。

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

### 2. Canonical 规范化与解析流

```
companies/{公司}/raw/
    │
    ▼
IngestService（CW-2 收敛目标）
    │
    ├─→ 校验 raw 不可变身份与 SHA-256
    ├─→ 写入/复用 source manifest
    ├─→ normalize / parse
    ├─→ 生成 EvidenceSpan 与解析质量
    └─→ 更新全文索引和只读 export
```

legacy wiki updater 不在 canonical 流程中；只允许维护历史只读内容或 source-oriented projection。

### 3. 查询与 export 流

```
用户查询
    │
    ▼
query.py
    │
    ├─→ 搜索 manifest/span/index
    ├─→ 返回 source ID + locator + 原文片段
    └─→ 不存回研究 Wiki，不形成投资结论

consumer export
    │
    └─→ 版本化 manifest/span bundle（只读）→ StockWiki
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
│       └── wiki/                 # legacy 只读兼容/source projection
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

### Legacy 数据库存储示例（非 canonical）

以下 `wiki_entries` 草案仅记录旧设计，不得作为新 schema 实施。CW-1 的正式 source manifest/evidence span schema 将独立版本化发布。

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
- 自定义 parser 与 extraction-quality 检查

### 3. 查询功能扩展

- 自定义查询接口
- 自定义带 locator 的 evidence bundle 格式
- 自定义可视化

扩展不得增加投资模型、估值、研究报告 writer 或跨仓写入。

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

当前生产约束为单线程顺序执行；`LLMClient` 和现有状态管理不是线程安全的。下列异步示例只保留为未来设想，必须先完成无状态重构和并发契约测试，不能直接用于当前 scheduler。

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
