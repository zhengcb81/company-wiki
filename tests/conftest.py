"""
pytest 配置文件
"""

import os
import sys
import pytest
import socket
from pathlib import Path

# Hermetic defaults apply during collection as well as individual tests.  This
# prevents imported modules from loading the repository's real .env before an
# autouse fixture has a chance to run.
for _secret_name in (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "MINIMAX_API_KEY",
    "MIMO_API_KEY",
    "TAVILY_API_KEY",
    "ANTHROPIC_API_KEY",
):
    os.environ.pop(_secret_name, None)
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["COMPANY_WIKI_NETWORK"] = "blocked"
os.environ["COMPANY_WIKI_REAL_LLM"] = "0"


@pytest.fixture(autouse=True)
def hermetic_runtime(monkeypatch):
    """Fail every real socket connection in the ordinary pytest suite."""
    for secret_name in (
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "MINIMAX_API_KEY",
        "MIMO_API_KEY",
        "TAVILY_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(secret_name, raising=False)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("COMPANY_WIKI_NETWORK", "blocked")
    monkeypatch.setenv("COMPANY_WIKI_REAL_LLM", "0")

    def blocked_connection(*_args, **_kwargs):
        raise RuntimeError(
            "HERMETIC NETWORK BLOCKED: ordinary tests cannot open sockets"
        )

    monkeypatch.setattr(socket.socket, "connect", blocked_connection)
    monkeypatch.setattr(socket, "create_connection", blocked_connection)


# 添加 scripts 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
# 添加 src 目录到 Python 路径（src 布局的 company_wiki 包，CI 不装 editable）
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
# 添加 tests 目录到 Python 路径（供 tests/helpers 等测试内部模块导入；RR-12.2d-4 evaluator）
sys.path.insert(0, str(Path(__file__).parent))


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
  provider: "minimax"
  model: "MiniMax-M3"
  base_url: "https://api.minimaxi.com/v1"
  max_tokens: 8192
  temperature: 1.0

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
    (wiki_root / "companies").mkdir(exist_ok=True)
    (wiki_root / "sectors").mkdir(exist_ok=True)
    (wiki_root / "themes").mkdir(exist_ok=True)
    (wiki_root / "scripts").mkdir(exist_ok=True)

    # 创建文件
    (wiki_root / "graph.yaml").write_text(sample_graph_yaml)
    (wiki_root / "config.yaml").write_text(sample_config_yaml)
    (wiki_root / "index.md").write_text("# 知识库索引\n")
    (wiki_root / "log.md").write_text("# 知识库操作日志\n")

    # 创建公司目录
    company_dir = wiki_root / "companies" / "中微公司"
    company_dir.mkdir(exist_ok=True)
    (company_dir / "wiki").mkdir(exist_ok=True)
    (company_dir / "raw").mkdir(exist_ok=True)
    (company_dir / "raw" / "news").mkdir(exist_ok=True)

    return wiki_root


@pytest.fixture
def mock_env_vars(monkeypatch):
    """设置模拟环境变量"""
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("WIKI_ROOT", "/tmp/test-wiki")


@pytest.fixture
def synthetic_announcement_pdf(tmp_path):
    """Create a small deterministic text PDF without production/raw dependencies."""
    import fitz

    pdf_path = tmp_path / "测试公司：2026年重大事项公告.pdf"
    document = fitz.open()
    for page_number in range(3):
        page = document.new_page()
        for line_number in range(18):
            text = (
                f"Page {page_number + 1} line {line_number + 1}: Company announcement "
                "revenue 100 million assets 500 million net profit 20 million."
            )
            page.insert_text((36, 48 + line_number * 38), text, fontsize=9)
    document.save(pdf_path)
    document.close()
    return pdf_path
