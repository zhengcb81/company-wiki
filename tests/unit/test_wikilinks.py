"""
WikilinkEngine 测试
测试 wikilinks.py 的核心功能: 图谱加载、相关页面发现、链接注入
"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from wikilinks import WikilinkEngine


@pytest.fixture
def wiki_env(tmp_path):
    """创建测试 wiki 环境"""
    wiki_root = tmp_path

    # graph.yaml
    graph_yaml = """
companies:
  中微公司:
    ticker: "688012"
    sectors:
      - 半导体设备
    themes:
      - 半导体国产替代
    aliases:
      - AMEC
      - 中微
  北方华创:
    ticker: "002371"
    sectors:
      - 半导体设备
    themes:
      - 半导体国产替代
  英伟达:
    ticker: "NVDA"
    sectors:
      - GPU与AI芯片
    themes:
      - AI产业链

nodes:
  半导体设备:
    type: sector
    keywords:
      - 刻蚀
      - 沉积
  GPU与AI芯片:
    type: sector
    keywords:
      - GPU
      - AI芯片
  半导体国产替代:
    type: theme
  AI产业链:
    type: theme
"""
    (wiki_root / "graph.yaml").write_text(graph_yaml, encoding="utf-8")

    # 创建公司 wiki 目录和页面
    for company in ["中微公司", "北方华创", "英伟达"]:
        wiki_dir = wiki_root / "companies" / company / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        page = wiki_dir / "公司动态.md"
        page.write_text(f"""---
title: {company}动态
entity: {company}
type: company_topic
last_updated: 2026-04-01
---

## 核心问题

- {company}的核心业务是什么？

## 时间线

### 2026-03-15 | 新闻 | {company}发布新产品

- 要点1
- 要点2
""", encoding="utf-8")

    # 创建行业 wiki 目录和页面
    for sector in ["半导体设备", "GPU与AI芯片"]:
        wiki_dir = wiki_root / "sectors" / sector / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        page = wiki_dir / f"{sector}.md"
        page.write_text(f"""---
title: {sector}
entity: {sector}
type: sector_topic
last_updated: 2026-04-01
---

## 核心问题

- {sector}的市场格局如何？

## 时间线

### 2026-03-10 | 研报 | {sector}市场分析

- 要点1
""", encoding="utf-8")

    # 创建主题 wiki 目录和页面
    for theme in ["半导体国产替代", "AI产业链"]:
        wiki_dir = wiki_root / "themes" / theme / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        page = wiki_dir / f"{theme}.md"
        page.write_text(f"""---
title: {theme}
entity: {theme}
type: theme_topic
last_updated: 2026-04-01
---

## 核心问题

- {theme}的进展如何？
""", encoding="utf-8")

    return wiki_root


@pytest.mark.unit
class TestWikilinkEngine:

    def test_initialization(self, wiki_env):
        """测试引擎初始化"""
        engine = WikilinkEngine(
            graph_path=str(wiki_env / "graph.yaml"),
            wiki_root=str(wiki_env)
        )
        assert engine.wiki_root == wiki_env
        assert engine.graph_path == wiki_env / "graph.yaml"

    def test_graph_loading(self, wiki_env):
        """测试图谱数据加载"""
        engine = WikilinkEngine(
            graph_path=str(wiki_env / "graph.yaml"),
            wiki_root=str(wiki_env)
        )
        data = engine.graph_data
        assert "中微公司" in data["companies"]
        assert "北方华创" in data["companies"]
        assert "半导体设备" in data["sectors"]

    def test_scan_all_pages(self, wiki_env):
        """测试页面扫描"""
        engine = WikilinkEngine(
            graph_path=str(wiki_env / "graph.yaml"),
            wiki_root=str(wiki_env)
        )
        pages = engine.scan_all_pages()
        assert len(pages) > 0
        # 应该包含公司、行业、主题页面
        page_stems = {p.stem for p in pages.values()}
        assert "公司动态" in page_stems or "中微公司" in pages

    def test_get_related_pages_company(self, wiki_env):
        """测试公司相关页面发现"""
        engine = WikilinkEngine(
            graph_path=str(wiki_env / "graph.yaml"),
            wiki_root=str(wiki_env)
        )
        related = engine.get_related_pages("中微公司")
        # 中微公司应该关联到: 半导体设备(行业), 半导体国产替代(主题), 北方华创(同行业)
        assert len(related) > 0

    def test_get_related_pages_sector(self, wiki_env):
        """测试行业相关页面发现"""
        engine = WikilinkEngine(
            graph_path=str(wiki_env / "graph.yaml"),
            wiki_root=str(wiki_env)
        )
        related = engine.get_related_pages("半导体设备")
        # 行业应该关联到所属公司
        assert len(related) > 0

    def test_inject_wikilinks_adds_related_section(self, wiki_env):
        """测试注入 wikilinks 添加相关页面区域"""
        engine = WikilinkEngine(
            graph_path=str(wiki_env / "graph.yaml"),
            wiki_root=str(wiki_env)
        )
        content = """---
title: 测试
entity: 中微公司
---

## 时间线

中微公司在刻蚀领域有所突破。
"""
        result = engine.inject_wikilinks(content, entity="中微公司", topic="公司动态")
        # 应该包含 "相关页面" 区域
        assert "## 相关页面" in result

    def test_inject_wikilinks_preserves_frontmatter(self, wiki_env):
        """测试注入不破坏 frontmatter"""
        engine = WikilinkEngine(
            graph_path=str(wiki_env / "graph.yaml"),
            wiki_root=str(wiki_env)
        )
        content = """---
title: 测试
entity: 中微公司
last_updated: 2026-04-01
---

## 时间线

内容
"""
        result = engine.inject_wikilinks(content, entity="中微公司", topic="公司动态")
        assert result.startswith("---")
        assert "title: 测试" in result
        assert "entity: 中微公司" in result

    def test_inject_wikilinks_does_not_link_self(self, wiki_env):
        """测试不会链接自身实体"""
        engine = WikilinkEngine(
            graph_path=str(wiki_env / "graph.yaml"),
            wiki_root=str(wiki_env)
        )
        content = """---
title: 测试
entity: 中微公司
---

## 时间线

刻蚀设备领域取得进展。
"""
        result = engine.inject_wikilinks(content, entity="中微公司", topic="公司动态")
        # 不应该出现 [[中微公司]] 自链接
        assert "[[中微公司]]" not in result

    def test_empty_graph(self, tmp_path):
        """测试空图谱不报错"""
        (tmp_path / "graph.yaml").write_text("{}", encoding="utf-8")
        engine = WikilinkEngine(
            graph_path=str(tmp_path / "graph.yaml"),
            wiki_root=str(tmp_path)
        )
        data = engine.graph_data
        assert data["companies"] == {}
        assert engine.get_related_pages("不存在") == []
