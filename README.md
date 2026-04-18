# company-wiki

基于 LLM 的上市公司知识库系统，自动采集、整理、分析上市公司信息。

## 功能特性

- 📰 **新闻采集**: 自动搜索和采集上市公司新闻
- 📊 **财报下载**: 自动下载年报、季报、招股说明书等
- 📝 **内容整理**: 自动提取关键信息，生成时间线
- 🔍 **智能查询**: 支持自然语言查询和答案存回
- 🔗 **关联分析**: 自动发现公司、行业、主题关联
- 📈 **矛盾检测**: 检测不同来源的数据矛盾

## 快速开始

### 1. 安装依赖

```bash
# 克隆仓库
git clone <repo-url>
cd company-wiki

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件，填入 API 密钥
export DEEPSEEK_API_KEY="your_deepseek_api_key"
export TAVILY_API_KEY="your_tavily_api_key"
```

### 3. 初始化数据

```bash
# 检查配置
python3 scripts/config.py

# 采集新闻
python3 scripts/collect_news.py

# 整理数据
python3 scripts/ingest.py
```

### 4. 使用系统

```bash
# 查看产业链概览
python3 scripts/graph.py --overview

# 查询公司信息
python3 scripts/query.py "中微公司的刻蚀设备进展？"

# 检查文档覆盖
python3 scripts/download_reports_v2.py --check
```

## 项目结构

```
company-wiki/
├── config.yaml              # 主配置文件
├── config_rules.yaml        # 分类规则配置
├── graph.yaml               # 公司/行业/主题数据
├── scripts/                 # 脚本目录
│   ├── config.py           # 统一配置管理
│   ├── logger.py           # 统一日志管理
│   ├── graph.py            # 图数据查询
│   ├── ingest.py           # 数据整理
│   ├── collect_news.py     # 新闻采集
│   ├── query.py            # 智能查询
│   ├── models/             # 数据模型
│   ├── storage/            # 存储层
│   └── ...
├── companies/               # 公司数据
│   └── {公司名}/
│       ├── raw/            # 原始文档
│       │   ├── news/       # 新闻
│       │   ├── financial_reports/  # 财报
│       │   ├── prospectus/ # 招股说明书
│       │   └── investor_relations/ # 投资者关系
│       └── wiki/           # 整理后的 wiki
├── sectors/                 # 行业数据
├── themes/                  # 主题数据
├── tests/                   # 测试目录
└── docs/                    # 文档目录
```

## 核心模块

### 配置管理

```python
from config import Config

# 加载配置
config = Config.load()

# 访问配置
print(config.llm.api_key)
print(config.search.api_key)
print(config.paths.wiki_root)
```

### 图数据查询

```python
from graph import Graph

# 创建 Graph 实例
g = Graph()

# 查询公司
company = g.get_company("中微公司")
print(company["ticker"])

# 查询行业
sector = g.get_sector("半导体设备")
print(sector["companies"])
```

### 数据整理

```python
from ingest import IngestPipeline
from config import Config

# 创建流水线
config = Config.load()
pipeline = IngestPipeline(config)

# 运行整理
result = pipeline.run(company="中微公司")
print(result.summary())
```

## 常用命令

### 数据采集

```bash
# 采集新闻
python3 scripts/collect_news.py

# 下载财报
python3 scripts/download_reports_v2.py --company 中微公司

# 从 Windows 同步文件
python3 scripts/download_reports_v2.py --sync
```

### 数据处理

```bash
# 整理数据
python3 scripts/ingest.py

# 分类文档
python3 scripts/classify_documents.py

# 检查矛盾
python3 scripts/contradiction_detector.py
```

### 查询分析

```bash
# 查看产业链
python3 scripts/graph.py --overview

# 查询公司
python3 scripts/query.py "问题"

# 发现新公司
python3 scripts/auto_discover.py
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek LLM API Key | ✅ |
| `TAVILY_API_KEY` | Tavily 搜索 API Key | ✅ |
| `WIKI_ROOT` | Wiki 根目录 | ❌ |

### config.yaml

```yaml
# LLM 配置
llm:
  provider: "deepseek"
  api_key: ""  # 使用环境变量
  model: "deepseek-reasoner"

# 搜索配置
search:
  engine: "tavily"
  tavily_api_key: ""  # 使用环境变量

# 路径配置
paths:
  wiki_root: "~/company-wiki"
```

## 测试

```bash
# 运行所有测试
python3 -m pytest tests/ -v

# 运行单元测试
python3 -m pytest tests/unit/ -v

# 运行端到端测试
python3 -m pytest tests/e2e/ -v
```

## 文档

- [重构计划](REFACTORING_PLAN.md)
- [测试指南](TESTING.md)
- [代码审查](CODE_REVIEW.md)
- [实施步骤](IMPLEMENTATION_STEPS.md)

## 贡献

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'Add xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

## 许可证

MIT License

## 致谢

- 基于 [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 概念
- 使用 [StockInfoDownloader](https://github.com/zhengcb81/StockInfoDownloader) 下载财报