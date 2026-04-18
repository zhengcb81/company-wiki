#!/bin/bash
# 测试环境搭建脚本
# 用法: ./scripts/setup_testing.sh

set -e

echo "=== company-wiki 测试环境搭建 ==="

# 1. 创建测试目录结构
echo "1. 创建测试目录结构..."
mkdir -p tests/{unit,integration,e2e,fixtures}
touch tests/__init__.py

# 2. 创建测试配置
echo "2. 创建测试配置..."
cat > tests/conftest.py << 'EOF'
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
EOF

# 3. 创建测试 fixtures
echo "3. 创建测试 fixtures..."
cat > tests/fixtures/sample_news.md << 'EOF'
---
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
EOF

# 4. 创建 pytest 配置
echo "4. 创建 pytest 配置..."
cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
EOF

# 5. 创建 requirements-test.txt
echo "5. 创建测试依赖..."
cat > requirements-test.txt << 'EOF'
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
pytest-asyncio>=0.21.0
pytest-timeout>=2.1.0
pytest-xdist>=3.3.0
coverage>=7.0.0
EOF

# 6. 创建第一个测试
echo "6. 创建第一个测试..."
cat > tests/unit/test_first.py << 'EOF'
"""
第一个测试 - 验证测试框架工作
"""
import pytest
import sys
from pathlib import Path

def test_framework_works():
    """验证测试框架正常工作"""
    assert True

def test_scripts_importable():
    """验证 scripts 目录可以导入"""
    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    
    # 尝试导入核心模块
    try:
        from graph import Graph
        assert Graph is not None
    except ImportError as e:
        pytest.fail(f"Failed to import Graph: {e}")

@pytest.mark.unit
def test_with_marker():
    """验证 marker 工作"""
    assert 1 + 1 == 2
EOF

# 7. 创建 E2E 测试示例
echo "7. 创建 E2E 测试示例..."
cat > tests/e2e/test_first_e2e.py << 'EOF'
"""
第一个端到端测试 - 验证测试基础设施
"""
import pytest
import tempfile
import shutil
from pathlib import Path

@pytest.mark.e2e
def test_wiki_structure_creation(temp_wiki_structure):
    """验证 wiki 目录结构创建"""
    wiki_root = temp_wiki_structure
    
    # 检查目录
    assert (wiki_root / "companies").exists()
    assert (wiki_root / "sectors").exists()
    assert (wiki_root / "themes").exists()
    
    # 检查文件
    assert (wiki_root / "graph.yaml").exists()
    assert (wiki_root / "config.yaml").exists()
    assert (wiki_root / "index.md").exists()
    assert (wiki_root / "log.md").exists()
    
    # 检查公司目录
    company_dir = wiki_root / "companies" / "中微公司"
    assert company_dir.exists()
    assert (company_dir / "wiki").exists()
    assert (company_dir / "raw").exists()
    assert (company_dir / "raw" / "news").exists()

@pytest.mark.e2e
def test_graph_yaml_parsing(sample_graph_yaml, temp_wiki_structure):
    """验证 graph.yaml 可以正确解析"""
    wiki_root = temp_wiki_structure
    
    # 读取并解析 YAML
    import yaml
    with open(wiki_root / "graph.yaml") as f:
        data = yaml.safe_load(f)
    
    # 验证结构
    assert "nodes" in data
    assert "companies" in data
    assert "半导体设备" in data["nodes"]
    assert "中微公司" in data["companies"]
    
    # 验证公司数据
    company = data["companies"]["中微公司"]
    assert company["ticker"] == "688012"
    assert company["exchange"] == "SSE STAR"
    assert "半导体设备" in company["sectors"]
EOF

# 8. 创建测试运行脚本
echo "8. 创建测试运行脚本..."
cat > scripts/run_tests.sh << 'EOF'
#!/bin/bash
# 运行测试脚本
# 用法: ./scripts/run_tests.sh [选项]

set -e

echo "=== 运行 company-wiki 测试 ==="

# 默认运行所有测试
TEST_TYPE=${1:-"all"}

case $TEST_TYPE in
    "unit")
        echo "运行单元测试..."
        python3 -m pytest tests/unit/ -v
        ;;
    "integration")
        echo "运行集成测试..."
        python3 -m pytest tests/integration/ -v
        ;;
    "e2e")
        echo "运行端到端测试..."
        python3 -m pytest tests/e2e/ -v
        ;;
    "all")
        echo "运行所有测试..."
        python3 -m pytest tests/ -v
        ;;
    "coverage")
        echo "运行测试并生成覆盖率报告..."
        python3 -m pytest tests/ --cov=scripts --cov-report=html --cov-report=term
        ;;
    "quick")
        echo "运行快速测试（排除慢速测试）..."
        python3 -m pytest tests/ -m "not slow" -v
        ;;
    *)
        echo "用法: $0 [unit|integration|e2e|all|coverage|quick]"
        exit 1
        ;;
esac

echo "=== 测试完成 ==="
EOF

chmod +x scripts/run_tests.sh

# 9. 创建 .env.example
echo "9. 创建 .env.example..."
cat > .env.example << 'EOF'
# 公司知识库环境变量配置
# 复制此文件为 .env 并填入实际值

# Tavily 搜索 API
TAVILY_API_KEY=your_tavily_api_key_here

# DeepSeek LLM API
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Wiki 根目录（可选，默认为 ~/company-wiki）
# WIKI_ROOT=~/company-wiki

# 日志级别（可选，默认为 INFO）
# LOG_LEVEL=INFO
EOF

# 10. 更新 .gitignore
echo "10. 更新 .gitignore..."
if ! grep -q ".env" .gitignore 2>/dev/null; then
    echo "" >> .gitignore
    echo "# 环境变量文件" >> .gitignore
    echo ".env" >> .gitignore
    echo ".env.local" >> .gitignore
    echo ".env.production" >> .gitignore
fi

if ! grep -q "__pycache__" .gitignore 2>/dev/null; then
    echo "" >> .gitignore
    echo "# Python" >> .gitignore
    echo "__pycache__/" >> .gitignore
    echo "*.py[cod]" >> .gitignore
    echo "*\$py.class" >> .gitignore
    echo "*.so" >> .gitignore
    echo ".Python" >> .gitignore
    echo "build/" >> .gitignore
    echo "develop-eggs/" >> .gitignore
    echo "dist/" >> .gitignore
    echo "downloads/" >> .gitignore
    echo "eggs/" >> .gitignore
    echo ".eggs/" >> .gitignore
    echo "lib/" >> .gitignore
    echo "lib64/" >> .gitignore
    echo "parts/" >> .gitignore
    echo "sdist/" >> .gitignore
    echo "var/" >> .gitignore
    echo "wheels/" >> .gitignore
    echo "*.egg-info/" >> .gitignore
    echo ".installed.cfg" >> .gitignore
    echo "*.egg" >> .gitignore
fi

if ! grep -q "htmlcov" .gitignore 2>/dev/null; then
    echo "" >> .gitignore
    echo "# 测试覆盖率" >> .gitignore
    echo "htmlcov/" >> .gitignore
    echo ".coverage" >> .gitignore
    echo ".coverage.*" >> .gitignore
    echo "coverage.xml" >> .gitignore
    echo "*.cover" >> .gitignore
    echo "*.py,cover" >> .gitignore
    echo ".hypothesis/" >> .gitignore
    echo ".pytest_cache/" >> .gitignore
fi

echo ""
echo "=== 测试环境搭建完成 ==="
echo ""
echo "下一步:"
echo "1. 安装测试依赖: pip install -r requirements-test.txt"
echo "2. 运行测试: ./scripts/run_tests.sh"
echo "3. 查看测试覆盖率: ./scripts/run_tests.sh coverage"
echo ""
echo "测试目录结构:"
tree tests/ 2>/dev/null || find tests -type f -name "*.py" | sort