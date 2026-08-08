# company-wiki

StockWiki 的上游公司资料供应与来源智能平台：采集并不可变保存上市公司资料，生成可追溯的 source manifest 与 EvidenceSpan，提供资料检索和只读 export。

## 产品边界

company-wiki 只拥有上游来源与解析职责；StockWiki 独占研究语义、人工证据裁决、投资模型、研究 Wiki 和报告发布。两者通过版本化、只读的 ID/hash 契约集成，不共享可变数据库，也不互相写目录。

本项目不生成或保存目标价、评级、仓位建议、估值/SOTP、正式研究报告或 accepted/rejected 投资结论。历史 `companies/**/wiki`、行业/主题 Wiki 和相关 writer 仅作只读兼容或 source-oriented projection，不能形成第二套 authoritative research state。

## 功能特性

- 📰 **新闻采集**: 自动搜索和采集上市公司新闻
- 📊 **财报下载**: 自动下载年报、季报、招股说明书等
- 🔒 **不可变来源**: 保存原文、SHA-256、采集器版本和来源时间
- 🧭 **证据定位**: 解析页码、段落、表格坐标和稳定 locator
- 🔍 **资料查询**: 返回带 `source_id + locator` 的答案或 evidence bundle
- 📦 **只读导出**: 向 StockWiki 等消费者提供版本化、可重放的来源契约

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
export MINIMAX_API_KEY="your_minimax_api_key"
# 可选：MiMo 2.5 Pro 通用次模型
export MIMO_API_KEY="your_mimo_api_key"
export TAVILY_API_KEY="your_tavily_api_key"
```

### 3. 初始化数据

```bash
# 检查配置
python3 scripts/config.py

# 采集新闻
python3 scripts/collect_news.py

# 运行当前兼容 ingest（CW-2 将收敛为 canonical IngestService）
python3 scripts/ingest.py
```

### 4. 采集一份交易所原公告

```bash
python -m company_wiki.source_contract.announcement_cli \
  --root . \
  --company 中微公司 \
  --entity-id SSE:688012 \
  --url https://star.sse.com.cn/.../announcement.pdf \
  --title 关于召开2025年度业绩说明会的公告 \
  --published-date 2026-03-25
```

该命令只接受显式 SSE/SZSE 官方 HTTPS URL，单线程下载并验证 PDF，以 content-addressed、create-once 方式生成 raw、source manifest 和 provenance；重复采集同一内容不会改写文件。完整边界见 [Announcement Collector v1](docs/contracts/announcement-collector-v1.md)。

### 5. 验证并导出 source contract

```bash
python -m company_wiki.source_contract.cli export \
  --root . \
  --manifests manifests.jsonl \
  --spans evidence-spans.jsonl
```

CLI 会重新校验 manifest 指向的 raw，并只向 stdout 输出一行确定性 bundle；add-only 增量重放使用 `--base previous-export.json`。完整输入格式、hash 算法和失败语义见 [Source Export v1](docs/contracts/source-export-v1.md)。

### 6. 将 parser result 接入 canonical ingest

```python
from pathlib import Path

from company_wiki.ingest import IngestService, ParserResult
from company_wiki.source_contract import EvidenceCoordinates, ParseStatus

result = ParserResult(
    source_id=manifest.source_id,
    coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
    raw_text="原文……",
    structured_value=None,
    parser_name="pdf_parser",
    parser_version="1.0.0",
    parse_status=ParseStatus.PARSED,
    quality_flags=(),
)
bundle = IngestService(root=Path(".")).ingest(
    manifest=manifest,
    parser_results=(result,),
)
```

该服务只验证 immutable raw/source identity，并生成 `EvidenceSpan` 与确定性 `SourceExportBundle`；不下载、不写 raw/Wiki/StockWiki，也不生成研究语义。公告 receipt 可用 `ingest_announcement()` 接入同一路径。完整合同见 [Canonical IngestService v1](docs/contracts/ingest-service-v1.md)。legacy parser/scheduler 的批量迁移仍属于 CW-2 后续工作，不能用旧 research writer 代替。

consumer 在读取 bundle 前必须按 [Source Contract Compatibility Policy v1](docs/contracts/source-contract-compatibility-v1.md) 声明三个契约的精确稳定 SemVer 并完成 `exact_highest` 协商；任一契约无共同版本时整组 fail closed。

### 7. 扫描分布式原始资料并生成 Markdown 索引

```bash
# 只读统计，不创建 catalog
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml scan --dry-run

# 安装登录后常驻任务；安装时不会立即启动
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml install-startup

# 查看原件索引与后台进度
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml status
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml worker-status
```

日常使用可直接双击 `scripts/source_catalog_control.cmd`：Pause 会立即停止并跨重启保持暂停，Resume 会恢复并立即启动，Stop 只结束本次运行但保留下次登录自启动；菜单 6 可搜索完全重复资料，清楚标出必须保留的 canonical 和可回收副本，并只在用户逐项选择、输入确认短语、执行前再次核验双边 SHA-256 后把该副本移入 Windows 回收站。没有自动清理或批量删除。

默认配置覆盖 `companies/*/raw/**`、Dropbox Stock 和 dayu-agent portfolio。后台扫描/解析绝不移动、复制或改写外部原件；只有用户在控制中心明确确认的非 canonical exact-copy 可以被移入回收站，并写入 append-only cleanup audit。`scan` 每小时独立更新可查询索引，低优先级 worker 只在用户空闲且接通电源时逐份生成 normalized Markdown、EvidenceSpan 和配置 LLM 的 source-only summary。索引会在 `locations.csv/duplicates.csv` 显式标记同内容副本。缺失来源默认只查询；显式 `ensure --allow-download` 时，A 股走 StockInfo，港股/美股由本项目调用 Dayu 现有 `python -m dayu.cli download`，不修改或导入 Dayu 代码；下载经隔离临时 workspace、staging 和二次 SHA 去重后才由 company-wiki 写入 canonical raw。Pause 会同时阻止后台后处理与该统一下载入口。全部派生物写入可重建的 `.source_catalog/`。完整格式、命令、路由、空闲门控、登录启动、控制和恢复语义见 [分布式原始资料目录与 Markdown 索引](docs/source-catalog.md)。

### 4. 使用系统

```bash
# 查看产业链概览
python3 scripts/graph.py --overview

# 查询公司资料；输出应包含 source ID 与 locator
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
│       └── wiki/           # legacy 只读兼容/source-oriented projection
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
print(config.llm.provider)
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

### 数据整理（legacy 兼容入口）

以下 API 说明当前兼容实现，不代表新的 source contract 已交付；新功能不得继续扩建研究 Wiki writer。

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

### 数据处理（上游解析）

```bash
# 整理数据
python3 scripts/ingest.py

# 分类文档
python3 scripts/classify_documents.py

# legacy 诊断；不得把结果升级为投资结论
python3 scripts/contradiction_detector.py
```

### 资料发现

```bash
# 查看产业链
python3 scripts/graph.py --overview

# 查询公司资料；不得自动存回研究结论
python3 scripts/query.py "问题"

# 发现新公司
python3 scripts/auto_discover.py
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `MINIMAX_API_KEY` | MiniMax-M3 主 LLM API Key | ✅ |
| `MIMO_API_KEY` | MiMo 2.5 Pro 通用次 LLM API Key | ❌ |
| `TAVILY_API_KEY` | Tavily 搜索 API Key | ✅ |
| `WIKI_ROOT` | legacy projection 根目录 | ❌ |

### config.yaml

```yaml
# LLM 配置
llm:
  provider: "minimax"
  model: "MiniMax-M3"
  base_url: "https://api.minimaxi.com/v1"
  fallback:
    provider: "mimo"
    model: "mimo-v2.5-pro"
    base_url: "https://token-plan-cn.xiaomimimo.com/v1"
    usage_scope: "general"

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

# 运行端到端测试（注：tests/e2e/ 目前只有 config 加载冒烟测试；
# 真实管线覆盖在 tests/integration/ — tests/test_full_pipeline.py 等）
python3 -m pytest tests/e2e/ tests/integration/ -v
```

## 文档

- [架构与职责边界](docs/ARCHITECTURE.md)
- [安全运维入口](docs/OPERATIONS.md)
- [ADR 适用范围](docs/adr/README.md)
- [Source Manifest v1 合同](docs/contracts/source-manifest-v1.md)
- [Announcement Collector v1 合同](docs/contracts/announcement-collector-v1.md)
- [Evidence Span v1 合同](docs/contracts/evidence-span-v1.md)
- [Source Export v1 合同与只读 CLI](docs/contracts/source-export-v1.md)
- [Canonical IngestService v1 合同](docs/contracts/ingest-service-v1.md)
- [PDF Extract v3 纯适配器合同](docs/contracts/pdf-extract-v3-adapter-v1.md)
- [Page-aware PDF Parser 纯适配器合同](docs/contracts/pdf-page-aware-parser-v1.md)
- [Source Contract Compatibility Policy v1](docs/contracts/source-contract-compatibility-v1.md)
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
