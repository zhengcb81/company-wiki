"""
矛盾检测模块测试
测试数值矛盾、时间矛盾、分类矛盾检测
"""
import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from contradiction_detector import ContradictionDetector, Contradiction


@pytest.fixture
def test_wiki_with_contradictions(tmp_path):
    """创建带有矛盾的测试 wiki"""
    wiki_root = tmp_path / "wiki"
    wiki_root.mkdir()
    
    # 创建 graph.yaml
    graph_yaml = """
nodes:
  半导体设备:
    type: sector
    description: 半导体制造设备

companies:
  中微公司:
    ticker: '688012'
    exchange: SSE STAR
    sectors:
    - 半导体设备
"""
    (wiki_root / "graph.yaml").write_text(graph_yaml)
    
    # 创建公司目录
    company_dir = wiki_root / "companies" / "中微公司"
    company_dir.mkdir(parents=True)
    (company_dir / "wiki").mkdir()
    
    # 创建带有数值矛盾的页面
    page1_content = """---
title: "公司动态"
entity: "中微公司"
type: company_topic
last_updated: "2026-04-17"
---

# 中微公司 — 公司动态

## 时间线

### 2026-04-17 | 新闻 | 中微公司发布新品
- 刻蚀精度提升30%
- 国产化率达到85%

- [来源](../raw/news/test1.md)
"""
    
    page2_content = """---
title: "相关动态"
entity: "中微公司"
type: company_related
last_updated: "2026-04-16"
---

# 中微公司 — 相关动态

## 时间线

### 2026-04-16 | 研报 | 中微公司深度报告
- 刻蚀精度提升50%  # 与页面1的30%矛盾
- 国产化率达到90%  # 与页面1的85%矛盾

- [来源](../raw/research/report1.md)
"""
    
    (company_dir / "wiki" / "公司动态.md").write_text(page1_content)
    (company_dir / "wiki" / "相关动态.md").write_text(page2_content)
    
    # 创建带有时间矛盾的页面
    page3_content = """---
title: "财务数据"
entity: "中微公司"
type: company_finance
last_updated: "2026-04-15"
---

# 中微公司 — 财务数据

## 时间线

### 2026-04-15 | 财报 | 2025年年报
- 营收123.85亿元

- [来源](../raw/reports/annual.md)

### 2026-04-14 | 财报 | 2025年年报  # 同一事件，不同日期
- 营收120亿元

- [来源](../raw/reports/annual2.md)
"""
    
    (company_dir / "wiki" / "财务数据.md").write_text(page3_content)
    
    return wiki_root


class TestContradictionDetector:
    """测试矛盾检测器"""
    
    def test_detector_initialization(self, test_wiki_with_contradictions):
        """测试检测器初始化"""
        detector = ContradictionDetector(test_wiki_with_contradictions)
        
        assert detector.wiki_root == test_wiki_with_contradictions
        assert detector.graph is not None
    
    def test_detect_numeric_contradictions(self, test_wiki_with_contradictions):
        """测试数值矛盾检测"""
        detector = ContradictionDetector(test_wiki_with_contradictions)
        
        contradictions = detector._detect_numeric_contradictions()
        
        # 应该检测到数值矛盾
        assert len(contradictions) > 0
        
        # 检查矛盾类型
        numeric_contradictions = [c for c in contradictions if c.contradiction_type == "numeric"]
        assert len(numeric_contradictions) > 0
    
    def test_detect_temporal_contradictions(self, test_wiki_with_contradictions):
        """测试时间矛盾检测"""
        detector = ContradictionDetector(test_wiki_with_contradictions)
        
        contradictions = detector._detect_temporal_contradictions()
        
        # 应该检测到时间矛盾
        assert len(contradictions) > 0
        
        # 检查矛盾类型
        temporal_contradictions = [c for c in contradictions if c.contradiction_type == "temporal"]
        assert len(temporal_contradictions) > 0
    
    def test_detect_all(self, test_wiki_with_contradictions):
        """测试检测所有矛盾"""
        detector = ContradictionDetector(test_wiki_with_contradictions)
        
        contradictions = detector.detect_all()
        
        # 应该有矛盾
        assert len(contradictions) > 0
        
        # 检查矛盾结构
        for c in contradictions:
            assert isinstance(c, Contradiction)
            assert c.entity1
            assert c.entity2
            assert c.contradiction_type in ["numeric", "temporal", "categorical"]
            assert c.confidence in ["high", "medium", "low"]
    
    def test_collect_numeric_statements(self, test_wiki_with_contradictions):
        """测试收集数值陈述"""
        detector = ContradictionDetector(test_wiki_with_contradictions)
        
        statements = detector._collect_numeric_statements()
        
        # 应该有数值陈述
        assert len(statements) > 0
        
        # 检查结构
        for stmt in statements:
            assert "entity" in stmt
            assert "value" in stmt
            assert "metric" in stmt
            assert "statement" in stmt
    
    def test_is_numeric_contradiction(self, test_wiki_with_contradictions):
        """测试数值矛盾判断"""
        detector = ContradictionDetector(test_wiki_with_contradictions)
        
        # 相同数值，不矛盾
        stmt1 = {"value": 30.0, "entity": "中微公司", "entity_type": "company", "metric": "百分比"}
        stmt2 = {"value": 30.0, "entity": "中微公司", "entity_type": "company", "metric": "百分比"}
        assert not detector._is_numeric_contradiction(stmt1, stmt2)
        
        # 不同实体，不矛盾
        stmt1 = {"value": 30.0, "entity": "中微公司", "entity_type": "company", "metric": "百分比"}
        stmt2 = {"value": 50.0, "entity": "北方华创", "entity_type": "company", "metric": "百分比"}
        assert not detector._is_numeric_contradiction(stmt1, stmt2)
        
        # 同一实体，差异超过30%，矛盾
        stmt1 = {"value": 30.0, "entity": "中微公司", "entity_type": "company", "metric": "百分比"}
        stmt2 = {"value": 50.0, "entity": "中微公司", "entity_type": "company", "metric": "百分比"}
        assert detector._is_numeric_contradiction(stmt1, stmt2)
        
        # 同一实体，差异小于30%，不矛盾
        stmt1 = {"value": 100.0, "entity": "中微公司", "entity_type": "company", "metric": "百分比"}
        stmt2 = {"value": 110.0, "entity": "中微公司", "entity_type": "company", "metric": "百分比"}
        assert not detector._is_numeric_contradiction(stmt1, stmt2)


class TestContradiction:
    """测试矛盾类"""
    
    def test_contradiction_creation(self):
        """测试创建矛盾"""
        contradiction = Contradiction(
            entity1="中微公司",
            entity1_type="company",
            page1="companies/中微公司/wiki/公司动态.md",
            statement1="刻蚀精度提升30%",
            entity2="中微公司",
            entity2_type="company",
            page2="companies/中微公司/wiki/相关动态.md",
            statement2="刻蚀精度提升50%",
            contradiction_type="numeric",
            confidence="medium",
            description="数值矛盾",
        )
        
        assert contradiction.entity1 == "中微公司"
        assert contradiction.contradiction_type == "numeric"
        assert contradiction.confidence == "medium"
    
    def test_contradiction_to_dict(self):
        """测试转换为字典"""
        contradiction = Contradiction(
            entity1="中微公司",
            entity1_type="company",
            page1="page1.md",
            statement1="statement1",
            entity2="中微公司",
            entity2_type="company",
            page2="page2.md",
            statement2="statement2",
            contradiction_type="numeric",
            confidence="high",
            description="test",
        )
        
        data = contradiction.to_dict()
        
        assert data["entity1"] == "中微公司"
        assert data["contradiction_type"] == "numeric"
        assert data["confidence"] == "high"


@pytest.mark.unit
def test_contradiction_detector_module_import():
    """测试矛盾检测模块导入"""
    from contradiction_detector import ContradictionDetector, Contradiction
    
    assert ContradictionDetector is not None
    assert Contradiction is not None
    
    print("✓ 矛盾检测模块导入成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])