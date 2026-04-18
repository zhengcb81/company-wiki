"""
Query 模块测试
测试 wiki 搜索、答案综合和存回功能
"""
import pytest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from query import WikiSearcher, AnswerSynthesizer, AnswerSaver, QueryAnswer, WikiPage


@pytest.fixture
def test_wiki(tmp_path):
    """创建测试 wiki 结构"""
    wiki_root = tmp_path / "wiki"
    wiki_root.mkdir()
    
    # 创建公司目录
    company_dir = wiki_root / "companies" / "中微公司"
    company_dir.mkdir(parents=True)
    (company_dir / "wiki").mkdir()
    (company_dir / "raw").mkdir()
    
    # 创建测试 wiki 页面
    wiki_content = """---
title: "公司动态"
entity: "中微公司"
type: company_topic
last_updated: "2026-04-17"
sources_count: 5
tags: []
---

# 中微公司 — 公司动态

## 核心问题
- 各环节设备国产化率？
- 先进制程设备进展？

## 时间线

### 2026-04-17 | 新闻 | 中微公司发布新一代刻蚀设备
- 刻蚀精度提升30%，支持5nm以下先进制程
- 产能提高20%
- 国产化率达到85%

- [来源](../raw/news/test.md)

### 2026-04-16 | 公告 | 中微公司获得大订单
- 与中芯国际签署大额订单
- 预计2026年量产

- [来源](../raw/news/test2.md)

## 综合评估
> 中微公司在刻蚀设备领域取得重要突破。
"""
    
    wiki_file = company_dir / "wiki" / "公司动态.md"
    wiki_file.write_text(wiki_content, encoding="utf-8")
    
    # 创建行业目录
    sector_dir = wiki_root / "sectors" / "半导体设备"
    sector_dir.mkdir(parents=True)
    (sector_dir / "wiki").mkdir()
    
    sector_content = """---
title: "半导体设备"
entity: "半导体设备"
type: sector_topic
last_updated: "2026-04-17"
sources_count: 10
---

# 半导体设备 — 行业概览

## 核心问题
- 各环节设备国产化率？

## 时间线

### 2026-04-17 | 研报 | 半导体设备行业深度报告
- 国产化率持续提升
- 刻蚀设备国产化率达到30%

- [来源](../raw/research/report.md)

## 综合评估
> 半导体设备国产化进程加速。
"""
    
    sector_file = sector_dir / "wiki" / "半导体设备.md"
    sector_file.write_text(sector_content, encoding="utf-8")
    
    # 创建 log.md
    log_file = wiki_root / "log.md"
    log_file.write_text("# 知识库操作日志\n", encoding="utf-8")
    
    return wiki_root


class TestWikiSearcher:
    """测试 Wiki 搜索器"""
    
    def test_search_by_keyword(self, test_wiki):
        """测试关键词搜索"""
        searcher = WikiSearcher(test_wiki)
        
        results = searcher.search("刻蚀设备")
        
        assert len(results) > 0
        # 应该找到中微公司的页面
        entity_names = [r.page.entity_name for r in results]
        assert "中微公司" in entity_names
    
    def test_search_by_entity(self, test_wiki):
        """测试实体搜索"""
        searcher = WikiSearcher(test_wiki)
        
        results = searcher.search("中微公司")
        
        assert len(results) > 0
        # 第一个结果应该是中微公司
        assert results[0].page.entity_name == "中微公司"
    
    def test_search_relevance_sorting(self, test_wiki):
        """测试相关性排序"""
        searcher = WikiSearcher(test_wiki)
        
        results = searcher.search("国产化率")
        
        # 应该有结果
        assert len(results) > 0
        
        # 相关性应该递减
        for i in range(len(results) - 1):
            assert results[i].relevance_score >= results[i + 1].relevance_score
    
    def test_search_empty_query(self, test_wiki):
        """测试空查询"""
        searcher = WikiSearcher(test_wiki)
        
        results = searcher.search("")
        
        # 空查询应该返回空结果或所有页面
        assert isinstance(results, list)
    
    def test_scan_all_pages(self, test_wiki):
        """测试扫描所有页面"""
        searcher = WikiSearcher(test_wiki)
        
        pages = searcher._scan_all_pages()
        
        assert len(pages) >= 2  # 至少有2个页面
        
        # 检查页面类型
        entity_types = [p.entity_type for p in pages]
        assert "company" in entity_types
        assert "sector" in entity_types


class TestAnswerSynthesizer:
    """测试答案综合器"""
    
    def test_synthesize_with_results(self, test_wiki):
        """测试有结果时的综合"""
        searcher = WikiSearcher(test_wiki)
        synthesizer = AnswerSynthesizer(test_wiki)
        
        results = searcher.search("刻蚀设备进展")
        answer = synthesizer.synthesize("刻蚀设备进展如何？", results)
        
        assert answer.question == "刻蚀设备进展如何？"
        assert answer.answer != "未找到相关信息"
        assert len(answer.sources) > 0
        assert answer.confidence in ["high", "medium", "low"]
    
    def test_synthesize_without_results(self, test_wiki):
        """测试无结果时的综合"""
        synthesizer = AnswerSynthesizer(test_wiki)
        
        answer = synthesizer.synthesize("不存在的问题", [])
        
        assert answer.answer == "未找到相关信息"
        assert answer.confidence == "low"
        assert len(answer.sources) == 0
    
    def test_extract_timeline_entries(self, test_wiki):
        """测试提取时间线条目"""
        synthesizer = AnswerSynthesizer(test_wiki)
        
        content = """## 时间线

### 2026-04-17 | 新闻 | 测试新闻
- 内容1

### 2026-04-16 | 公告 | 测试公告
- 内容2

## 综合评估
> 评估
"""
        
        entries = synthesizer._extract_timeline_entries(content)
        
        assert len(entries) == 2
        assert "2026-04-17" in entries[0]
        assert "2026-04-16" in entries[1]


class TestAnswerSaver:
    """测试答案保存器"""
    
    def test_save_to_wiki(self, test_wiki):
        """测试保存到 wiki"""
        saver = AnswerSaver(test_wiki)
        
        answer = QueryAnswer(
            question="测试问题？",
            answer="测试答案内容",
            confidence="high",
        )
        
        # 创建一个测试来源
        test_page = WikiPage(
            path=test_wiki / "companies" / "中微公司" / "wiki" / "公司动态.md",
            title="公司动态",
            entity_name="中微公司",
            entity_type="company",
            topic_name="公司动态",
            content="测试内容",
        )
        answer.sources = [test_page]
        
        # 保存
        saved_path = saver.save_to_wiki(answer, "中微公司", "company")
        
        assert saved_path is not None
        assert saved_path.exists()
        
        # 检查内容
        content = saved_path.read_text(encoding="utf-8")
        assert "测试问题？" in content
        assert "测试答案内容" in content
        assert "query" in content
    
    def test_save_as_timeline_entry(self, test_wiki):
        """测试保存为时间线条目"""
        saver = AnswerSaver(test_wiki)
        
        answer = QueryAnswer(
            question="新问题？",
            answer="新答案内容",
            confidence="medium",
        )
        
        # 保存为时间线条目
        success = saver.save_as_timeline_entry(
            answer,
            "中微公司",
            "company",
            "公司动态",
        )
        
        assert success
        
        # 检查文件是否更新
        wiki_file = test_wiki / "companies" / "中微公司" / "wiki" / "公司动态.md"
        content = wiki_file.read_text(encoding="utf-8")
        
        assert "新问题？" in content
        assert "查询" in content
    
    def test_append_log(self, test_wiki):
        """测试追加日志"""
        saver = AnswerSaver(test_wiki)
        
        # 追加日志
        saver._append_log("测试日志消息")
        
        # 检查日志文件
        log_file = test_wiki / "log.md"
        content = log_file.read_text(encoding="utf-8")
        
        assert "测试日志消息" in content
        assert "query" in content


class TestQueryAnswer:
    """测试查询答案"""
    
    def test_query_answer_creation(self):
        """测试创建查询答案"""
        answer = QueryAnswer(
            question="测试问题",
            answer="测试答案",
            confidence="high",
        )
        
        assert answer.question == "测试问题"
        assert answer.answer == "测试答案"
        assert answer.confidence == "high"
        assert answer.generated_at  # 应该自动生成时间戳
    
    def test_query_answer_with_sources(self):
        """测试带来源的查询答案"""
        page = WikiPage(
            path=Path("/test/path.md"),
            title="测试页面",
            entity_name="测试实体",
            entity_type="company",
            topic_name="测试主题",
            content="测试内容",
        )
        
        answer = QueryAnswer(
            question="测试问题",
            answer="测试答案",
            sources=[page],
        )
        
        assert len(answer.sources) == 1
        assert answer.sources[0].entity_name == "测试实体"


@pytest.mark.unit
def test_query_module_import():
    """测试 query 模块导入"""
    from query import WikiSearcher, AnswerSynthesizer, AnswerSaver, QueryAnswer
    
    assert WikiSearcher is not None
    assert AnswerSynthesizer is not None
    assert AnswerSaver is not None
    assert QueryAnswer is not None
    
    print("✓ Query 模块导入成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])