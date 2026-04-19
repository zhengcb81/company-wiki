"""
源发现模块测试
测试知识缺口分析和来源建议生成
"""
import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from source_discoverer import SourceDiscoverer, KnowledgeGap, SourceSuggestion


@pytest.fixture
def test_wiki_with_gaps(tmp_path):
    """创建带有知识缺口的测试 wiki"""
    wiki_root = tmp_path / "wiki"
    wiki_root.mkdir()
    
    # 创建 graph.yaml
    graph_yaml = """
nodes:
  半导体设备:
    type: sector
    description: 半导体制造设备
    keywords:
    - 半导体设备

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
  北方华创:
    ticker: '002371'
    exchange: SZSE
    sectors:
    - 半导体设备
    themes:
    - AI产业链
    position: 国产半导体设备龙头
    news_queries:
    - 北方华创 最新消息

questions:
  半导体设备:
  - 各环节设备国产化率？
  - 先进制程设备进展？
"""
    (wiki_root / "graph.yaml").write_text(graph_yaml, encoding="utf-8")
    
    # 创建公司目录（有wiki但时间线为空）
    company_dir = wiki_root / "companies" / "中微公司"
    company_dir.mkdir(parents=True)
    (company_dir / "wiki").mkdir()
    
    wiki_content = """---
title: "公司动态"
entity: "中微公司"
type: company_topic
last_updated: "2026-03-01"
sources_count: 0
---

# 中微公司 — 公司动态

## 核心问题
- （待设定）

## 时间线

（暂无条目）

## 综合评估
> 待积累数据后补充。
"""
    
    (company_dir / "wiki" / "公司动态.md").write_text(wiki_content, encoding="utf-8")
    
    # 创建另一个公司（没有wiki）
    company_dir2 = wiki_root / "companies" / "北方华创"
    company_dir2.mkdir(parents=True)
    
    # 创建行业目录
    sector_dir = wiki_root / "sectors" / "半导体设备"
    sector_dir.mkdir(parents=True)
    (sector_dir / "wiki").mkdir()
    
    sector_content = """---
title: "半导体设备"
entity: "半导体设备"
type: sector_topic
last_updated: "2026-04-17"
sources_count: 5
---

# 半导体设备 — 行业概览

## 时间线

### 2026-04-17 | 研报 | 行业深度报告
- 国产化率持续提升

- [来源](../raw/research/report.md)
"""
    
    (sector_dir / "wiki" / "半导体设备.md").write_text(sector_content, encoding="utf-8")
    
    return wiki_root


class TestSourceDiscoverer:
    """测试源发现器"""
    
    def test_discoverer_initialization(self, test_wiki_with_gaps):
        """测试发现器初始化"""
        discoverer = SourceDiscoverer(test_wiki_with_gaps)
        
        assert discoverer.wiki_root == test_wiki_with_gaps
        assert discoverer.graph is not None
    
    def test_analyze_gaps(self, test_wiki_with_gaps):
        """测试分析知识缺口"""
        discoverer = SourceDiscoverer(test_wiki_with_gaps)
        
        gaps = discoverer.analyze_gaps()
        
        # 应该有知识缺口
        assert len(gaps) > 0
        
        # 检查缺口类型
        gap_types = [g.gap_type for g in gaps]
        assert len(set(gap_types)) > 0
    
    def test_check_missing_pages(self, test_wiki_with_gaps):
        """测试检查缺失页面"""
        discoverer = SourceDiscoverer(test_wiki_with_gaps)
        
        gaps = discoverer._check_missing_pages()
        
        # 应该检测到北方华创没有wiki页面
        missing_gaps = [g for g in gaps if g.entity_name == "北方华创"]
        assert len(missing_gaps) > 0
    
    def test_check_empty_timelines(self, test_wiki_with_gaps):
        """测试检查空时间线"""
        discoverer = SourceDiscoverer(test_wiki_with_gaps)
        
        gaps = discoverer._check_empty_timelines()
        
        # 应该检测到中微公司的时间线为空
        empty_gaps = [g for g in gaps if g.entity_name == "中微公司"]
        assert len(empty_gaps) > 0
    
    def test_check_outdated_pages(self, test_wiki_with_gaps):
        """测试检查过时页面"""
        discoverer = SourceDiscoverer(test_wiki_with_gaps)
        
        gaps = discoverer._check_outdated_pages()
        
        # 应该检测到中微公司的页面过时
        outdated_gaps = [g for g in gaps if g.entity_name == "中微公司"]
        assert len(outdated_gaps) > 0
    
    def test_generate_suggestions(self, test_wiki_with_gaps):
        """测试生成来源建议"""
        discoverer = SourceDiscoverer(test_wiki_with_gaps)
        
        gaps = discoverer.analyze_gaps()
        suggestions = discoverer.generate_suggestions(gaps)
        
        # 应该有建议
        assert len(suggestions) > 0
        
        # 检查建议结构
        for suggestion in suggestions:
            assert isinstance(suggestion, SourceSuggestion)
            assert suggestion.title
            assert suggestion.description
            assert len(suggestion.search_queries) > 0


class TestKnowledgeGap:
    """测试知识缺口"""
    
    def test_knowledge_gap_creation(self):
        """测试创建知识缺口"""
        gap = KnowledgeGap(
            entity_name="中微公司",
            entity_type="company",
            topic_name="公司动态",
            gap_type="empty_timeline",
            description="时间线为空",
            priority="high",
        )
        
        assert gap.entity_name == "中微公司"
        assert gap.gap_type == "empty_timeline"
        assert gap.priority == "high"
    
    def test_knowledge_gap_with_suggestions(self):
        """测试带建议的知识缺口"""
        gap = KnowledgeGap(
            entity_name="中微公司",
            entity_type="company",
            topic_name="公司动态",
            gap_type="empty_timeline",
            description="时间线为空",
            priority="medium",
            suggestions=["添加新闻", "添加公告"],
        )
        
        assert len(gap.suggestions) == 2
        assert "添加新闻" in gap.suggestions


class TestSourceSuggestion:
    """测试来源建议"""
    
    def test_source_suggestion_creation(self):
        """测试创建来源建议"""
        suggestion = SourceSuggestion(
            title="测试建议",
            description="测试描述",
            search_queries=["查询1", "查询2"],
            related_entities=["实体1"],
            priority="high",
            reason="测试原因",
        )
        
        assert suggestion.title == "测试建议"
        assert len(suggestion.search_queries) == 2
        assert suggestion.priority == "high"


@pytest.mark.unit
def test_source_discoverer_module_import():
    """测试源发现模块导入"""
    from source_discoverer import SourceDiscoverer, KnowledgeGap, SourceSuggestion
    
    assert SourceDiscoverer is not None
    assert KnowledgeGap is not None
    assert SourceSuggestion is not None
    
    print("✓ 源发现模块导入成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])