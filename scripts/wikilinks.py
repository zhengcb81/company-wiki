#!/usr/bin/env python3
"""
wikilinks.py — Wiki 页面交叉引用引擎

基于 graph.yaml 知识图谱, 管理 wiki 页面间的 [[wikilinks]] 交叉引用:
- 同行业公司互相链接
- 公司 → 所属行业/主题
- 时间线条目中实体名 → 对应 wiki 页面
- 页面底部 "相关页面" 区域

用法:
    from wikilinks import WikilinkEngine

    engine = WikilinkEngine()

    # 获取某实体的所有相关页面
    related = engine.get_related_pages("中微公司")

    # 给 wiki 页面内容注入 wikilinks
    updated = engine.inject_wikilinks(content, entity="中微公司", topic="公司动态")

    # 回填所有现有 wiki 页面
    engine.backfill_all()
"""

import re
import sys
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class WikilinkEngine:
    """管理 wiki 页面间的交叉引用"""

    def __init__(self, graph_path: str = None, wiki_root: str = None):
        """
        初始化

        Args:
            graph_path: graph.yaml 路径
            wiki_root: wiki 根目录
        """
        if wiki_root is None:
            wiki_root = str(Path(__file__).resolve().parent.parent)
        if graph_path is None:
            graph_path = str(Path(wiki_root) / "graph.yaml")

        self.wiki_root = Path(wiki_root)
        self.graph_path = Path(graph_path)
        self._graph_data = None

        # 缓存
        self._all_pages = None          # 所有 wiki 页面名 → 路径
        self._company_sectors = None     # 公司 → 行业列表
        self._sector_companies = None    # 行业 → 公司列表
        self._company_themes = None      # 公司 → 主题列表
        self._theme_companies = None     # 主题 → 公司列表
        self._company_aliases = None     # 公司名 → aliases

    @property
    def graph_data(self) -> dict:
        """懒加载 graph.yaml"""
        if self._graph_data is None:
            self._graph_data = self._load_graph()
        return self._graph_data

    def _load_graph(self) -> dict:
        """加载 graph.yaml"""
        import yaml
        if not self.graph_path.exists():
            logger.warning(f"graph.yaml 不存在: {self.graph_path}")
            return {}

        with open(self.graph_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        result = {
            "companies": {},
            "sectors": {},
            "themes": {},
        }

        # 格式 1: 顶层 companies:/sectors 在 nodes 下
        for name, info in data.get("nodes", {}).items():
            node_type = info.get("type", "")
            if node_type == "company":
                result["companies"][name] = info
            elif node_type == "sector":
                result["sectors"][name] = info
            elif node_type == "theme":
                result["themes"][name] = info

        # 格式 2: 顶层 companies: 键 (本项目实际格式)
        for name, info in data.get("companies", {}).items():
            result["companies"][name] = info

        # 从 nodes 提取行业和主题
        for name, info in data.get("nodes", {}).items():
            if info.get("type") == "sector":
                result["sectors"][name] = info
            elif info.get("type") == "theme":
                result["themes"][name] = info

        # 从 edges 提取关系
        for edge in data.get("edges", []):
            source = edge.get("from", edge.get("source", ""))
            target = edge.get("to", edge.get("target", ""))

            if source in result["companies"] and target in result["sectors"]:
                result["companies"][source].setdefault("sectors", [])
                if target not in result["companies"][source]["sectors"]:
                    result["companies"][source]["sectors"].append(target)

        return result

    def _build_caches(self):
        """构建缓存索引"""
        if self._company_sectors is not None:
            return

        self._company_sectors = defaultdict(list)
        self._sector_companies = defaultdict(list)
        self._company_themes = defaultdict(list)
        self._theme_companies = defaultdict(list)
        self._company_aliases = defaultdict(list)

        for company_name, info in self.graph_data.get("companies", {}).items():
            sectors = info.get("sectors", [])
            themes = info.get("themes", [])
            aliases = info.get("aliases", [])

            self._company_sectors[company_name] = sectors
            self._company_themes[company_name] = themes
            self._company_aliases[company_name] = aliases

            for s in sectors:
                self._sector_companies[s].append(company_name)
            for t in themes:
                self._theme_companies[t].append(company_name)

    def scan_all_pages(self) -> Dict[str, Path]:
        """
        扫描所有 wiki 页面, 返回 {页面名: 文件路径}

        页面名优先使用 frontmatter title，重复时加上实体前缀。
        也使用文件 stem 作为别名。
        """
        if self._all_pages is not None:
            return self._all_pages

        self._all_pages = {}
        seen_titles = {}  # title -> count for dedup

        for pattern in [
            "companies/*/wiki/*.md",
            "sectors/*/wiki/*.md",
            "themes/*/wiki/*.md",
        ]:
            for md_file in self.wiki_root.glob(pattern):
                content = md_file.read_text(encoding='utf-8', errors='replace')
                title_match = re.search(r'title:\s*"?([^"\n]+)"?', content)
                title = title_match.group(1).strip() if title_match else md_file.stem

                # 推断实体名用于去重
                entity = self._infer_entity(md_file, title)

                # 如果标题重复，用 "实体/标题" 格式区分
                page_name = title
                if title in seen_titles:
                    page_name = f"{entity}/{title}"
                    # 也要回改之前那个
                    prev_path = seen_titles[title]
                    prev_entity = self._infer_entity(prev_path, title)
                    self._all_pages[f"{prev_entity}/{title}"] = prev_path
                    # 保留原标题作为别名（仅当不冲突时）
                seen_titles[title] = md_file

                self._all_pages[page_name] = md_file

                # 也用 "实体名" 作为 key（公司通常有 "公司动态" 页面）
                if entity and entity not in self._all_pages:
                    self._all_pages[entity] = md_file

        return self._all_pages

    def get_related_pages(self, entity: str) -> List[str]:
        """
        获取实体的所有相关页面名

        Args:
            entity: 实体名 (公司/行业/主题)

        Returns:
            相关页面名列表
        """
        self._build_caches()
        all_pages = self.scan_all_pages()
        related = set()

        # 1. 如果是公司 → 关联行业、主题、同行业公司
        if entity in self._company_sectors:
            # 所属行业
            for sector in self._company_sectors[entity]:
                related.add(sector)
                # 同行业公司
                for peer in self._sector_companies.get(sector, []):
                    if peer != entity:
                        related.add(peer)

            # 所属主题
            for theme in self._company_themes[entity]:
                related.add(theme)

        # 2. 如果是行业 → 关联公司、父主题
        if entity in self._sector_companies or entity in self.graph_data.get("sectors", {}):
            for company in self._sector_companies.get(entity, []):
                related.add(company)
            sector_info = self.graph_data.get("sectors", {}).get(entity, {})
            for theme in sector_info.get("parent_theme", []):
                related.add(theme)

        # 3. 如果是主题 → 关联行业和公司
        if entity in self._theme_companies or entity in self.graph_data.get("themes", {}):
            for company in self._theme_companies.get(entity, []):
                related.add(company)

        # 只保留有 wiki 页面的
        existing = set()
        for page_name in related:
            if page_name in all_pages:
                existing.add(page_name)
            # 也检查文件名
            if any(p.stem == page_name for p in all_pages.values()):
                existing.add(page_name)

        return sorted(existing)

    def inject_wikilinks(self, content: str, entity: str = "", topic: str = "") -> str:
        """
        在 wiki 页面内容中注入 [[wikilinks]]

        策略:
        1. 在正文首次出现实体名时添加 [[实体名]]
        2. 在页面底部添加/更新 "相关页面" 区域

        Args:
            content: wiki 页面 markdown 内容
            entity: 当前页面所属实体
            topic: 当前页面主题

        Returns:
            更新后的内容
        """
        self._build_caches()
        all_pages = self.scan_all_pages()
        related = self.get_related_pages(entity)

        # 收集所有可能的链接目标 (页面名 + aliases)
        link_targets = {}
        for page_name in all_pages:
            if page_name != entity:  # 不链接自己
                link_targets[page_name] = page_name

        # 添加 aliases
        for company_name, aliases in self._company_aliases.items():
            for alias in aliases:
                if alias and len(alias) > 1:
                    link_targets[alias] = company_name

        # 添加行业关键词
        for sector_name, sector_info in self.graph_data.get("sectors", {}).items():
            for kw in sector_info.get("keywords", []):
                if kw and len(kw) > 2:
                    link_targets[kw] = sector_name

        # 在内容中注入 wikilinks (只替换第一次出现)
        for text, target in sorted(link_targets.items(), key=lambda x: -len(x[0])):
            if text in content and f"[[{target}]]" not in content:
                # 只替换第一次出现, 避免破坏 frontmatter
                # 找到 frontmatter 结束位置
                fm_end = 0
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end > 0:
                        fm_end = end + 3

                # 在 frontmatter 之后替换
                after_fm = content[fm_end:]
                # 只替换第一次出现
                after_fm = after_fm.replace(text, f"[[{target}]]", 1)
                content = content[:fm_end] + after_fm

        # 添加/更新 "相关页面" 区域
        if related:
            content = self._update_related_section(content, related)

        return content

    def _update_related_section(self, content: str, related: List[str]) -> str:
        """更新页面底部的 "相关页面" 区域"""
        related_links = [f"- [[{name}]]" for name in related]
        related_block = "## 相关页面\n\n" + "\n".join(related_links) + "\n"

        # 检查是否已有 "相关页面" 区域
        section_match = re.search(r'\n## 相关页面\n', content)
        if section_match:
            # 替换现有区域
            start = section_match.start()
            # 找到区域结束位置
            rest = content[start + len("\n## 相关页面\n"):]
            next_section = re.search(r'\n## ', rest)
            if next_section:
                end = start + len("\n## 相关页面\n") + next_section.start()
            else:
                end = len(content)
            content = content[:start] + "\n" + related_block + content[end:]
        else:
            # 在文件末尾添加
            if not content.endswith('\n'):
                content += '\n'
            content += "\n" + related_block

        return content

    def backfill_all(self, dry_run: bool = False) -> Tuple[int, int]:
        """
        回填所有现有 wiki 页面的 wikilinks

        Returns:
            (更新文件数, 添加链接数)
        """
        all_pages = self.scan_all_pages()
        updated_files = 0
        total_links = 0

        # 去重: 同一个文件路径只处理一次
        seen_paths = set()
        for page_title, page_path in all_pages.items():
            if str(page_path) in seen_paths:
                continue
            seen_paths.add(str(page_path))

            # 推断实体名
            entity = self._infer_entity(page_path, page_title)

            content = page_path.read_text(encoding='utf-8')
            original = content

            updated = self.inject_wikilinks(content, entity=entity)

            if updated != original:
                # 计算新增链接数
                old_links = content.count('[[')
                new_links = updated.count('[[')
                added = new_links - old_links

                if not dry_run:
                    page_path.write_text(updated, encoding='utf-8')

                updated_files += 1
                total_links += max(0, added)
                logger.info(f"  更新: {page_path.relative_to(self.wiki_root)} (+{added} links)")

        return updated_files, total_links

    def _infer_entity(self, page_path: Path, page_title: str) -> str:
        """从文件路径推断实体名"""
        parts = page_path.parts

        for i, part in enumerate(parts):
            if part in ("companies", "sectors", "themes") and i + 1 < len(parts):
                return parts[i + 1]

        return page_title


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Wiki 页面交叉引用引擎")
    parser.add_argument("--backfill", action="store_true", help="回填所有现有页面的 wikilinks")
    parser.add_argument("--dry-run", action="store_true", help="只检查不执行")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--entity", type=str, help="查看指定实体的相关页面")
    args = parser.parse_args()

    print("=" * 50)
    print("  Wiki 交叉引用引擎")
    print("=" * 50)

    engine = WikilinkEngine()

    if args.stats:
        all_pages = engine.scan_all_pages()
        print(f"\nWiki 页面总数: {len(all_pages)}")

        # 统计现有 wikilinks
        total_links = 0
        pages_with_links = 0
        for page_title, page_path in all_pages.items():
            content = page_path.read_text(encoding='utf-8', errors='replace')
            links = content.count('[[')
            if links > 0:
                pages_with_links += 1
                total_links += links

        print(f"有 [[wikilinks]] 的页面: {pages_with_links}/{len(all_pages)}")
        print(f"总链接数: {total_links}")

        # 统计图谱关系
        companies = engine.graph_data.get("companies", {})
        sectors = engine.graph_data.get("sectors", {})
        themes = engine.graph_data.get("themes", {})
        print(f"\n知识图谱:")
        print(f"  公司: {len(companies)}")
        print(f"  行业: {len(sectors)}")
        print(f"  主题: {len(themes)}")
        return

    if args.entity:
        related = engine.get_related_pages(args.entity)
        print(f"\n{args.entity} 的相关页面 ({len(related)}):")
        for page in related:
            print(f"  [[{page}]]")
        return

    if args.backfill:
        print(f"\n扫描所有 wiki 页面...")
        all_pages = engine.scan_all_pages()
        print(f"找到 {len(all_pages)} 个页面")

        print(f"\n{'回填' if not args.dry_run else '检查'} wikilinks...")
        files, links = engine.backfill_all(dry_run=args.dry_run)

        action = "将更新" if args.dry_run else "已更新"
        print(f"\n{'=' * 50}")
        print(f"  {action} {files} 个文件, 添加 {links} 个链接")
        print(f"{'=' * 50}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
