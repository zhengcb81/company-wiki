"""
Graph 模块重构测试
验证 models 子模块和 facade
"""
import pytest
import sys
from pathlib import Path

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from models import GraphData, GraphLoader, GraphQueries, Company, Sector, Theme, Edge


class TestGraphDataModels:
    """测试数据模型"""
    
    def test_company_model(self):
        """测试公司模型"""
        company = Company(
            name="中微公司",
            ticker="688012",
            exchange="SSE STAR",
            sectors=["半导体设备"],
            themes=["AI产业链"],
            position="刻蚀设备龙头",
            news_queries=["中微公司 最新消息"],
            aliases=["688012", "AMEC"],
        )
        
        assert company.name == "中微公司"
        assert company.ticker == "688012"
        assert company.exchange == "SSE STAR"
        assert "半导体设备" in company.sectors
        
        # 测试转换为字典
        data = company.to_dict()
        assert data["ticker"] == "688012"
        assert data["exchange"] == "SSE STAR"
        
        # 测试从字典创建
        company2 = Company.from_dict("中微公司", data)
        assert company2.name == company.name
        assert company2.ticker == company.ticker
    
    def test_sector_model(self):
        """测试行业模型"""
        sector = Sector(
            name="半导体设备",
            type="sector",
            description="半导体制造设备",
            tier=5,
            keywords=["半导体设备", "芯片设备"],
            parent_theme=["AI产业链"],
        )
        
        assert sector.name == "半导体设备"
        assert sector.type == "sector"
        assert sector.tier == 5
        
        # 测试转换为字典
        data = sector.to_dict()
        assert data["type"] == "sector"
        assert data["tier"] == 5
        
        # 测试从字典创建
        sector2 = Sector.from_dict("半导体设备", data)
        assert sector2.name == sector.name
        assert sector2.tier == sector.tier
    
    def test_theme_model(self):
        """测试主题模型"""
        theme = Theme(
            name="AI产业链",
            description="从芯片到应用的完整AI产业链",
            keywords=["AI产业链"],
        )
        
        assert theme.name == "AI产业链"
        assert theme.description == "从芯片到应用的完整AI产业链"
        
        # 测试转换为字典
        data = theme.to_dict()
        assert data["type"] == "theme"
        assert data["description"] == theme.description
    
    def test_graph_data_container(self):
        """测试图数据容器"""
        data = GraphData(
            nodes={
                "半导体设备": {
                    "type": "sector",
                    "description": "半导体制造设备",
                    "tier": 5,
                }
            },
            companies={
                "中微公司": {
                    "ticker": "688012",
                    "exchange": "SSE STAR",
                    "sectors": ["半导体设备"],
                }
            },
            edges=[
                {
                    "from": "半导体设备",
                    "to": "半导体代工",
                    "type": "upstream_of",
                }
            ],
            questions={
                "半导体设备": ["各环节设备国产化率？"]
            },
        )
        
        # 测试获取公司
        company = data.get_company("中微公司")
        assert company is not None
        assert company.ticker == "688012"
        
        # 测试获取行业
        sector = data.get_sector("半导体设备")
        assert sector is not None
        assert sector.tier == 5
        
        # 测试获取所有公司
        companies = data.get_all_companies()
        assert len(companies) == 1
        assert companies[0].name == "中微公司"
        
        # 测试获取所有行业
        sectors = data.get_all_sectors()
        assert len(sectors) == 1
        assert sectors[0].name == "半导体设备"
        
        # 测试获取边
        edges = data.get_edges()
        assert len(edges) == 1
        assert edges[0].from_entity == "半导体设备"
        assert edges[0].to_entity == "半导体代工"


class TestGraphLoader:
    """测试数据加载器"""
    
    def test_load_from_file(self, tmp_path):
        """测试从文件加载"""
        # 创建测试文件
        graph_yaml = tmp_path / "graph.yaml"
        graph_yaml.write_text("""
nodes:
  半导体设备:
    type: sector
    description: 半导体制造设备
    tier: 5

companies:
  中微公司:
    ticker: '688012'
    exchange: SSE STAR
    sectors:
    - 半导体设备

edges:
  - from: 半导体设备
    to: 半导体代工
    type: upstream_of
""", encoding="utf-8")
        
        loader = GraphLoader(graph_yaml)
        data = loader.load()
        
        assert data is not None
        assert "半导体设备" in data.nodes
        assert "中微公司" in data.companies
        assert len(data.edges) == 1
    
    def test_save_to_file(self, tmp_path):
        """测试保存到文件"""
        graph_yaml = tmp_path / "graph.yaml"
        
        # 创建数据
        data = GraphData(
            nodes={"半导体设备": {"type": "sector", "description": "半导体制造设备"}},
            companies={"中微公司": {"ticker": "688012", "exchange": "SSE STAR"}},
            edges=[],
            questions={},
            settings={},
        )
        
        loader = GraphLoader(graph_yaml)
        loader.save(data)
        
        # 验证文件已创建
        assert graph_yaml.exists()
        
        # 验证内容
        import yaml
        with open(graph_yaml, encoding="utf-8") as f:
            content = yaml.safe_load(f)
        
        assert "nodes" in content
        assert "companies" in content
        assert "半导体设备" in content["nodes"]
        assert "中微公司" in content["companies"]
    
    def test_backup_and_restore(self, tmp_path):
        """测试备份和恢复"""
        graph_yaml = tmp_path / "graph.yaml"
        graph_yaml.write_text("""
nodes:
  半导体设备:
    type: sector
    description: 半导体制造设备
""", encoding="utf-8")
        
        loader = GraphLoader(graph_yaml)
        data = loader.load()
        
        # 创建备份
        backup_path = loader.backup()
        assert backup_path.exists()
        
        # 修改数据
        data.nodes["新节点"] = {"type": "sector", "description": "新描述"}
        loader.save(data)
        
        # 从备份恢复
        restored_data = loader.restore(backup_path)
        
        # 验证恢复的数据
        assert "新节点" not in restored_data.nodes
        assert "半导体设备" in restored_data.nodes


class TestGraphQueries:
    """测试查询接口"""
    
    def test_company_queries(self):
        """测试公司查询"""
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
                "北方华创": {
                    "ticker": "002371",
                    "exchange": "SZSE",
                    "sectors": ["半导体设备"],
                    "themes": ["AI产业链"],
                    "position": "国产半导体设备龙头",
                },
            },
            edges=[],
            questions={},
        )
        
        queries = GraphQueries(data)
        
        # 测试获取所有公司
        companies = queries.get_all_companies()
        assert len(companies) == 2
        
        # 测试获取单个公司
        company = queries.get_company("中微公司")
        assert company is not None
        assert company.ticker == "688012"
        
        # 测试按行业获取公司
        sector_companies = queries.get_companies_by_sector("半导体设备")
        assert len(sector_companies) == 2
        
        # 测试按主题获取公司
        theme_companies = queries.get_companies_by_theme("AI产业链")
        assert len(theme_companies) == 2
    
    def test_sector_queries(self):
        """测试行业查询"""
        data = GraphData(
            nodes={
                "半导体设备": {"type": "sector", "description": "半导体制造设备", "tier": 5},
                "刻蚀设备": {"type": "subsector", "description": "刻蚀设备", "parent_sector": ["半导体设备"]},
            },
            companies={
                "中微公司": {"ticker": "688012", "exchange": "SSE STAR", "sectors": ["刻蚀设备"]},
            },
            edges=[
                {"from": "刻蚀设备", "to": "半导体设备", "type": "belongs_to"},
            ],
            questions={"半导体设备": ["各环节设备国产化率？"]},
        )
        
        queries = GraphQueries(data)
        
        # 测试获取所有行业
        sectors = queries.get_all_sectors()
        assert len(sectors) == 2
        
        # 测试获取单个行业
        sector = queries.get_sector("半导体设备")
        assert sector is not None
        assert sector.tier == 5
        assert sector.questions == ["各环节设备国产化率？"]
        
        # 测试获取子行业
        subsectors = queries.get_subsectors("半导体设备")
        assert len(subsectors) == 1
        assert subsectors[0].name == "刻蚀设备"
    
    def test_graph_traversal(self):
        """测试图遍历"""
        data = GraphData(
            nodes={
                "半导体设备": {"type": "sector"},
                "半导体代工": {"type": "sector"},
                "GPU与AI芯片": {"type": "sector"},
            },
            companies={},
            edges=[
                {"from": "半导体设备", "to": "半导体代工", "type": "upstream_of"},
                {"from": "半导体代工", "to": "GPU与AI芯片", "type": "upstream_of"},
            ],
            questions={},
        )
        
        queries = GraphQueries(data)
        
        # 测试上游查询
        upstream = queries.upstream_of("半导体代工")
        assert "半导体设备" in upstream
        
        # 测试下游查询
        downstream = queries.downstream_of("半导体设备")
        assert "半导体代工" in downstream
        
        # 测试供应链路径
        paths = queries.supply_chain_path("半导体设备")
        assert len(paths) == 1
        assert paths[0] == ["半导体设备", "半导体代工", "GPU与AI芯片"]
        
        # 测试路径查找
        path = queries.find_path("半导体设备", "GPU与AI芯片")
        assert path == ["半导体设备", "半导体代工", "GPU与AI芯片"]
    
    def test_find_related_entities(self):
        """测试相关性匹配"""
        data = GraphData(
            nodes={
                "半导体设备": {"type": "sector", "keywords": ["半导体设备", "芯片设备"]},
            },
            companies={
                "中微公司": {
                    "ticker": "688012",
                    "exchange": "SSE STAR",
                    "sectors": ["半导体设备"],
                    "themes": ["AI产业链"],
                },
            },
            edges=[],
            questions={},
        )
        
        queries = GraphQueries(data)
        
        # 测试关键词匹配
        related = queries.find_related_entities("中微公司发布新一代刻蚀设备")
        assert len(related) > 0
        
        # 应该包含公司
        company_entities = [r for r in related if r[1] == "company"]
        assert len(company_entities) > 0
        
        # 测试公司线索
        related = queries.find_related_entities("测试文本", company_hint="中微公司")
        assert len(related) > 0
        
        # 应该包含公司动态
        company_dynamic = [r for r in related if r[2] == "公司动态"]
        assert len(company_dynamic) > 0


@pytest.mark.unit
def test_graph_facade():
    """测试 Graph facade"""
    from graph import Graph
    
    # 创建临时 graph.yaml
    import tempfile
    import yaml
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({
            "nodes": {
                "半导体设备": {"type": "sector", "description": "半导体制造设备", "tier": 5},
            },
            "companies": {
                "中微公司": {
                    "ticker": "688012",
                    "exchange": "SSE STAR",
                    "sectors": ["半导体设备"],
                    "themes": ["AI产业链"],
                    "position": "刻蚀设备龙头",
                    "news_queries": ["中微公司 最新消息"],
                },
            },
            "edges": [
                {"from": "半导体设备", "to": "半导体代工", "type": "upstream_of"},
            ],
            "questions": {"半导体设备": ["各环节设备国产化率？"]},
        }, f)
        temp_path = f.name
    
    try:
        # 测试加载
        g = Graph(temp_path)
        
        # 测试公司查询
        companies = g.get_all_companies()
        assert len(companies) == 1
        assert companies[0]["name"] == "中微公司"
        
        company = g.get_company("中微公司")
        assert company is not None
        assert company["ticker"] == "688012"
        
        # 测试行业查询
        sectors = g.get_all_sectors()
        assert len(sectors) == 1
        assert sectors[0] == "半导体设备"
        
        sector = g.get_sector("半导体设备")
        assert sector is not None
        assert sector["tier"] == 5
        
        # 测试图遍历
        downstream = g.downstream_of("半导体设备")
        assert "半导体代工" in downstream
        
        # 测试相关性匹配
        related = g.find_related_entities("中微公司发布新设备")
        assert len(related) > 0
        
        print("✓ Graph facade 测试通过")
        
    finally:
        import os
        os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])