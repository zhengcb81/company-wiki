"""
pytest 配置文件
"""
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path

# 添加 scripts 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

@pytest.fixture(scope="session")
def wiki_root(tmp_path_factory):
    """创建临时 wiki 根目录"""
    return tmp_path_factory.mktemp("wiki")

@pytest.fixture
def sample_graph_yaml():
    """示例 graph.yaml 内容"""
    return """
nodes:
  半导体设备:
    type: sector
    description: 半导体制造设备
    tier: 5
    keywords:
    - 半导体设备
    - 芯片设备

companies:
  中微公司:
    ticker: '688012'
    exchange: SSE STAR
    sectors:
    - 半导体设备
    themes:
    - AI产业链
    position: 刻蚀设备龙头
    news_queries:
    - 中微公司 最新消息
    aliases:
    - '688012'
    - AMEC

questions:
  半导体设备:
  - 各环节设备国产化率？
  - 先进制程设备进展？
"""

@pytest.fixture
def sample_config_yaml():
    """示例 config.yaml 内容"""
    return """
schedule:
  news_collection: "daily"
  report_check: "weekly"

llm:
  provider: "deepseek"
  api_key: "sk-test-key-12345"
  model: "deepseek-reasoner"
  base_url: "https://api.deepseek.com"
  max_tokens: 1024
  temperature: 0.3

search:
  engine: "tavily"
  tavily_api_key: "tvly-dev-test-key-12345"
  results_per_query: 8
  language: "zh"
  max_age_days: 7

paths:
  wiki_root: "~/company-wiki"
"""

@pytest.fixture
def sample_news_content():
    """示例新闻内容"""
    return """---
title: "中微公司发布新一代刻蚀设备"
source_url: "https://example.com/news/123"
published_date: "2026-04-15"
collected_date: "2026-04-16 10:00"
company: "中微公司"
type: news
---

# 中微公司发布新一代刻蚀设备

中微公司（688012）今日宣布推出新一代电感耦合ICP等离子体刻蚀设备，该设备在先进制程节点表现出色。

## 主要亮点

1. 刻蚀精度提升30%
2. 产能提高20%
3. 已获得多家客户验证

公司董事长尹志尧表示，这标志着国产半导体设备在高端领域取得重要突破。
"""

@pytest.fixture
def temp_wiki_structure(wiki_root, sample_graph_yaml, sample_config_yaml):
    """创建临时 wiki 目录结构"""
    # 创建目录
    (wiki_root / "companies").mkdir()
    (wiki_root / "sectors").mkdir()
    (wiki_root / "themes").mkdir()
    (wiki_root / "scripts").mkdir()
    
    # 创建文件
    (wiki_root / "graph.yaml").write_text(sample_graph_yaml)
    (wiki_root / "config.yaml").write_text(sample_config_yaml)
    (wiki_root / "index.md").write_text("# 知识库索引\n")
    (wiki_root / "log.md").write_text("# 知识库操作日志\n")
    
    # 创建公司目录
    company_dir = wiki_root / "companies" / "中微公司"
    company_dir.mkdir()
    (company_dir / "wiki").mkdir()
    (company_dir / "raw").mkdir()
    (company_dir / "raw" / "news").mkdir()
    
    return wiki_root

@pytest.fixture
def mock_env_vars(monkeypatch):
    """设置模拟环境变量"""
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("WIKI_ROOT", "/tmp/test-wiki")