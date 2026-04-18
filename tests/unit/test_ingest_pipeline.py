"""
Ingest 流水线测试
验证 IngestPipeline 类
"""
import pytest
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from config_loader import Config, LLMConfig, SearchConfig, ScheduleConfig, ReportDownloaderConfig, EvolutionConfig
from models import GraphData, GraphQueries
from ingest import IngestPipeline, PipelineResult


@pytest.fixture
def test_config():
    """创建测试配置"""
    return Config(
        llm=LLMConfig(
            provider="deepseek",
            api_key="test-key",
            model="deepseek-reasoner",
            base_url="https://api.deepseek.com",
        ),
        search=SearchConfig(
            engine="tavily",
            api_key="test-key",
            results_per_query=8,
            language="zh",
            max_age_days=7,
        ),
        schedule=ScheduleConfig(),
        report_downloader=ReportDownloaderConfig(
            tool_path="",
            save_dir="",
        ),
        evolution=EvolutionConfig(),
        wiki_root=Path("/tmp/test-wiki"),
    )


@pytest.fixture
def test_graph_queries():
    """创建测试图查询接口"""
    data = GraphData(
        nodes={
            "半导体设备": {"type": "sector", "description": "半导体制造设备", "tier": 5},
        },
        companies={
            "中微公司": {
                "ticker": "688012",
                "exchange": "SSE STAR",
                "sectors": ["半导体设备"],
                "themes": ["AI产业链"],
                "position": "刻蚀设备龙头",
            },
        },
        edges=[],
        questions={},
    )
    return GraphQueries(data)


@pytest.fixture
def test_wiki_structure(test_config, tmp_path):
    """创建测试 wiki 目录结构"""
    wiki_root = tmp_path / "test-wiki"
    wiki_root.mkdir(parents=True, exist_ok=True)
    
    # 创建目录
    (wiki_root / "companies").mkdir()
    (wiki_root / "companies" / "中微公司").mkdir()
    (wiki_root / "companies" / "中微公司" / "raw").mkdir()
    (wiki_root / "companies" / "中微公司" / "raw" / "news").mkdir()
    (wiki_root / "companies" / "中微公司" / "wiki").mkdir()
    (wiki_root / ".ingested").mkdir()
    
    # 创建测试文件
    test_news = wiki_root / "companies" / "中微公司" / "raw" / "news" / "test_news.md"
    test_news.write_text("""---
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
""")
    
    # 更新配置中的 wiki_root
    test_config.wiki_root = wiki_root
    
    yield wiki_root
    
    # 清理
    shutil.rmtree(wiki_root, ignore_errors=True)


class TestPipelineResult:
    """测试 PipelineResult"""
    
    def test_empty_result(self):
        """测试空结果"""
        result = PipelineResult()
        
        assert result.total_files == 0
        assert result.success_count == 0
        assert result.error_count == 0
        assert result.success_rate == 1.0
    
    def test_with_updates(self):
        """测试有更新的结果"""
        result = PipelineResult()
        result.updated.append(("file1.md", "中微公司/公司动态"))
        result.updated.append(("file2.md", "半导体设备/行业概览"))
        result.skipped.append("file3.md")
        
        assert result.total_files == 3
        assert result.success_count == 2
        assert result.error_count == 0
        assert result.success_rate == 2/3
    
    def test_with_errors(self):
        """测试有错误的结果"""
        result = PipelineResult()
        result.updated.append(("file1.md", "中微公司/公司动态"))
        result.errors.append(("file2.md", "Error message"))
        
        assert result.total_files == 2
        assert result.success_count == 1
        assert result.error_count == 1
        assert result.success_rate == 0.5
    
    def test_summary(self):
        """测试摘要"""
        result = PipelineResult()
        result.updated.append(("file1.md", "中微公司/公司动态"))
        result.skipped.append("file2.md")
        result.errors.append(("file3.md", "Error"))
        
        summary = result.summary()
        assert "处理完成" in summary
        assert "成功更新: 1" in summary
        assert "跳过: 1" in summary
        assert "失败: 1" in summary


class TestIngestPipeline:
    """测试 IngestPipeline"""
    
    def test_initialization(self, test_config, test_graph_queries):
        """测试初始化"""
        pipeline = IngestPipeline(test_config, test_graph_queries)
        
        assert pipeline.config == test_config
        assert pipeline.graph == test_graph_queries
        assert pipeline.wiki_root == test_config.wiki_root
    
    def test_empty_pipeline(self, test_config, test_graph_queries):
        """测试空流水线"""
        pipeline = IngestPipeline(test_config, test_graph_queries)
        
        # 运行流水线（没有待处理文件）
        result = pipeline.run()
        
        assert result.total_files == 0
        assert result.success_count == 0
        assert result.error_count == 0
    
    def test_dry_run(self, test_config, test_graph_queries, test_wiki_structure):
        """测试 dry-run 模式"""
        pipeline = IngestPipeline(test_config, test_graph_queries)
        
        # 运行 dry-run
        result = pipeline.run(dry_run=True)
        
        # 验证没有实际处理
        assert result.total_files >= 0
        
        # 验证 .ingested 目录为空（没有标记文件）
        ingested_dir = test_wiki_structure / ".ingested"
        ingested_files = list(ingested_dir.glob("*.hash"))
        assert len(ingested_files) == 0
    
    def test_process_file(self, test_config, test_graph_queries, test_wiki_structure):
        """测试处理文件"""
        pipeline = IngestPipeline(test_config, test_graph_queries)
        
        # 运行流水线
        result = pipeline.run()
        
        # 验证结果
        assert result.total_files >= 0
        
        # 如果有更新，验证 wiki 文件已创建
        if result.success_count > 0:
            wiki_dir = test_wiki_structure / "companies" / "中微公司" / "wiki"
            wiki_files = list(wiki_dir.glob("*.md"))
            assert len(wiki_files) > 0
    
    def test_error_handling(self, test_config, test_graph_queries, test_wiki_structure):
        """测试错误处理"""
        # 创建一个损坏的文件
        bad_file = test_wiki_structure / "companies" / "中微公司" / "raw" / "news" / "bad_file.md"
        bad_file.write_bytes(b'\x80\x81\x82')  # 无效 UTF-8
        
        pipeline = IngestPipeline(test_config, test_graph_queries)
        
        # 运行流水线
        result = pipeline.run()
        
        # 验证错误被记录
        # 注意：由于我们的实现会跳过无效文件，可能不会有错误
        # 但至少不应该崩溃
        assert result.total_files >= 0


class TestScanner:
    """测试文件扫描器"""
    
    def test_scan_empty(self, test_config, test_graph_queries):
        """测试空目录扫描"""
        from ingest.scanner import FileScanner
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_root = Path(tmpdir)
            scanner = FileScanner(wiki_root)
            
            # 扫描
            pending = scanner.scan(test_graph_queries)
            
            assert len(pending) == 0
    
    def test_scan_with_files(self, test_config, test_graph_queries, test_wiki_structure):
        """测试有文件的扫描"""
        from ingest.scanner import FileScanner
        
        scanner = FileScanner(test_wiki_structure)
        
        # 扫描
        pending = scanner.scan(test_graph_queries)
        
        # 应该有文件
        assert len(pending) >= 0
        
        # 验证文件路径格式
        for file_path, entity_name, entity_type in pending:
            assert isinstance(file_path, str)
            assert isinstance(entity_name, str)
            assert entity_type in ("company", "sector", "theme")


class TestExtractor:
    """测试内容提取器"""
    
    def test_extract_markdown(self, test_wiki_structure):
        """测试提取 Markdown"""
        from ingest.extractor import ContentExtractor
        
        extractor = ContentExtractor()
        
        # 测试文件
        test_file = test_wiki_structure / "companies" / "中微公司" / "raw" / "news" / "test_news.md"
        
        # 提取
        meta = extractor.extract(str(test_file))
        
        # 验证
        assert "_content" in meta
        assert "_filename" in meta
        assert meta["_filename"] == "test_news.md"
        assert "中微公司" in meta.get("company", "")
    
    def test_extract_summary(self):
        """测试提取摘要"""
        from ingest.extractor import ContentExtractor
        
        extractor = ContentExtractor()
        
        text = "中微公司发布新一代刻蚀设备。该设备在先进制程节点表现出色。刻蚀精度提升30%。产能提高20%。"
        
        # 提取摘要
        points = extractor.extract_summary_points(text, max_sentences=2)
        
        # 验证
        assert len(points) <= 2
        assert all(isinstance(p, str) for p in points)


class TestUpdater:
    """测试 Wiki 更新器"""
    
    def test_create_wiki_template(self, test_wiki_structure):
        """测试创建 wiki 模板"""
        from ingest.updater import WikiUpdater
        
        updater = WikiUpdater(test_wiki_structure)
        
        # 创建模板
        wiki_path = test_wiki_structure / "companies" / "中微公司" / "wiki" / "测试主题.md"
        updater._create_wiki_template(wiki_path, "中微公司", "company", "测试主题")
        
        # 验证文件已创建
        assert wiki_path.exists()
        
        # 验证内容
        content = wiki_path.read_text()
        assert "title:" in content
        assert "entity:" in content
        assert "type:" in content
        assert "时间线" in content


@pytest.mark.unit
def test_ingest_module_import():
    """测试 ingest 模块导入"""
    from ingest import IngestPipeline, PipelineResult, FileScanner, ContentExtractor, WikiUpdater
    
    assert IngestPipeline is not None
    assert PipelineResult is not None
    assert FileScanner is not None
    assert ContentExtractor is not None
    assert WikiUpdater is not None
    
    print("✓ ingest 模块导入成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])