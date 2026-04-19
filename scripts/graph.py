#!/usr/bin/env python3
"""
graph.py — 统一数据加载入口
所有脚本通过此模块访问 graph.yaml，避免各自硬编码。

用法：
    from graph import Graph
    g = Graph()                          # 自动加载 graph.yaml
    g = Graph("~/other/graph.yaml")      # 指定路径

    # 查询公司
    g.get_company("中微公司")            # → {ticker, sectors, themes, news_queries, ...}
    g.get_all_companies()                # → [{"name": ..., "ticker": ...}, ...]

    # 查询行业
    g.get_sector("半导体设备")           # → {companies, upstream, downstream, questions, ...}
    g.get_all_sectors()                  # → ["半导体设备", "半导体材料", ...]

    # 图遍历
    g.upstream_of("半导体设备")          # → [] (已是上游)
    g.downstream_of("半导体设备")        # → ["半导体代工"]
    g.supply_chain_path("半导体设备")    # → [["半导体设备", "半导体代工", "GPU与AI芯片", ...]]

    # 相关性匹配（核心：供 ingest.py 使用）
    g.find_related_entities(text)        # → [(entity_name, entity_type, topic_name), ...]

    # CLI
    python3 scripts/graph.py --overview
    python3 scripts/graph.py --company 中微公司
    python3 scripts/graph.py --sector 半导体设备
    python3 scripts/graph.py --chain 半导体设备
    python3 scripts/graph.py --find "中微公司发布新刻蚀设备"
    python3 scripts/graph.py --generate-nav
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

WIKI_ROOT = Path(__file__).resolve().parent.parent


class Graph:
    """产业链拓扑图 — 统一数据访问层"""

    def __init__(self, graph_path=None):
        self._path = Path(graph_path) if graph_path else WIKI_ROOT / "graph.yaml"
        self._data = self._load()
        self._build_indices()

    def _load(self):
        import yaml
        with open(self._path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _build_indices(self):
        """预构建索引，加速查询"""
        # 邻接表
        self._upstream = defaultdict(list)
        self._downstream = defaultdict(list)
        self._belongs_to = defaultdict(list)

        for e in self._data.get("edges", []):
            f, t, etype = e["from"], e["to"], e["type"]
            if etype == "upstream_of":
                self._downstream[f].append(t)
                self._upstream[t].append(f)
            elif etype == "belongs_to":
                self._belongs_to[t].append(f)

        # 关键词 → 实体 映射（用于 find_related_entities）
        self._keyword_index = {}
        for name, node in self._data.get("nodes", {}).items():
            keywords = node.get("keywords", [name])
            for kw in keywords:
                self._keyword_index[kw.lower()] = (name, node.get("type", "sector"))

        # 公司名 → 公司 映射
        self._company_index = {}
        for name, comp in self._data.get("companies", {}).items():
            self._company_index[name] = comp
            # 也按 ticker 索引
            ticker = comp.get("ticker", "")
            if ticker:
                self._company_index[ticker] = comp

    # ── 公司查询 ──────────────────────────────

    def get_all_companies(self):
        """返回所有公司列表"""
        result = []
        for name, comp in self._data.get("companies", {}).items():
            result.append({
                "name": name,
                "ticker": comp.get("ticker", ""),
                "exchange": comp.get("exchange", ""),
                "sectors": comp.get("sectors", []),
                "themes": comp.get("themes", []),
                "news_queries": comp.get("news_queries", [f"{name} 最新消息"]),
                "position": comp.get("position", ""),
            })
        return result

    def get_company(self, name):
        """获取单个公司详情"""
        comp = self._data.get("companies", {}).get(name)
        if not comp:
            # 尝试按 ticker 查找
            comp = self._company_index.get(name)
        if not comp:
            return None

        # 补充关联信息
        sectors = comp.get("sectors", [])
        themes = comp.get("themes", [])

        # 获取每个行业的 upstream/downstream
        sector_info = []
        for s in sectors:
            sector_info.append({
                "name": s,
                "upstream": self._upstream.get(s, []),
                "downstream": self._downstream.get(s, []),
                "tier": self._data.get("nodes", {}).get(s, {}).get("tier"),
            })

        return {
            "name": name,
            "ticker": comp.get("ticker", ""),
            "exchange": comp.get("exchange", ""),
            "sectors": sectors,
            "themes": themes,
            "news_queries": comp.get("news_queries", [f"{name} 最新消息"]),
            "position": comp.get("position", ""),
            "competes_with": comp.get("competes_with", []),
            "sector_info": sector_info,
        }

    # ── 行业查询 ──────────────────────────────

    def get_all_sectors(self):
        """返回所有行业名"""
        return [
            name for name, node in self._data.get("nodes", {}).items()
            if node.get("type") in ("sector", "subsector")
        ]

    def get_sector(self, name):
        """获取行业详情"""
        node = self._data.get("nodes", {}).get(name)
        if not node:
            return None

        # 获取该行业的公司
        companies = [
            cname for cname, comp in self._data.get("companies", {}).items()
            if name in comp.get("sectors", [])
        ]

        # 获取子领域
        subsectors = self._belongs_to.get(name, [])

        # 获取子领域的公司
        subsector_companies = {}
        for sub in subsectors:
            sub_comps = [
                cname for cname, comp in self._data.get("companies", {}).items()
                if sub in comp.get("sectors", [])
            ]
            subsector_companies[sub] = sub_comps

        return {
            "name": name,
            "type": node.get("type"),
            "description": node.get("description", ""),
            "tier": node.get("tier"),
            "keywords": node.get("keywords", [name]),
            "upstream": self._upstream.get(name, []),
            "downstream": self._downstream.get(name, []),
            "companies": companies,
            "subsectors": subsectors,
            "subsector_companies": subsector_companies,
            "questions": self._data.get("questions", {}).get(name, []),
            "parent_theme": node.get("parent_theme", []),
            "parent_sector": node.get("parent_sector", []),
        }

    # ── 图遍历 ──────────────────────────────

    def upstream_of(self, entity):
        """获取 entity 的所有上游"""
        return self._upstream.get(entity, [])

    def downstream_of(self, entity):
        """获取 entity 的所有下游"""
        return self._downstream.get(entity, [])

    def supply_chain_path(self, entity, visited=None):
        """获取从 entity 到终端应用的所有路径"""
        if visited is None:
            visited = set()
        if entity in visited:
            return []
        visited.add(entity)

        paths = []
        targets = self._downstream.get(entity, [])
        if not targets:
            paths.append([entity])
        else:
            for t in targets:
                for sp in self.supply_chain_path(t, visited.copy()):
                    paths.append([entity] + sp)
        return paths

    # ── 相关性匹配（核心 API）──────────────────

    def find_related_entities(self, text, company_hint=None):
        """
        给定一段文本，判断它与哪些实体（公司/行业/主题）相关。
        返回: [(entity_name, entity_type, topic_name), ...]

        这是 ingest.py 判断相关性的核心逻辑。
        """
        text_lower = text.lower()
        related = set()

        # 1. 如果有公司线索，直接关联该公司及其行业
        if company_hint:
            comp = self.get_company(company_hint)
            if comp:
                related.add((company_hint, "company", "公司动态"))
                for s in comp.get("sectors", []):
                    related.update(self._expand_sector_topics(s))
                for t in comp.get("themes", []):
                    related.update(self._expand_theme_topics(t))
                # 1b. 关联竞争者（竞争者的"相关动态"也会被更新）
                for competitor in comp.get("competes_with", []):
                    if self.get_company(competitor):
                        related.add((competitor, "company", "相关动态"))

        # 2. 关键词匹配行业/主题
        for keyword, (entity_name, entity_type) in self._keyword_index.items():
            if keyword in text_lower:
                if entity_type in ("sector", "subsector"):
                    related.update(self._expand_sector_topics(entity_name))
                elif entity_type == "theme":
                    related.update(self._expand_theme_topics(entity_name))

        # 3. 公司名匹配
        for comp_name in self._data.get("companies", {}):
            if comp_name in text and comp_name != company_hint:
                related.add((comp_name, "company", "相关动态"))
                # 也关联到该公司的行业
                comp = self.get_company(comp_name)
                if comp:
                    for s in comp.get("sectors", []):
                        related.update(self._expand_sector_topics(s))

        return list(related)

    def _expand_sector_topics(self, sector_name):
        """展开行业下的所有 topic"""
        result = set()
        questions = self._data.get("questions", {}).get(sector_name, [])
        if questions:
            # 每个行业就是一个 topic
            result.add((sector_name, "sector", sector_name))
        else:
            result.add((sector_name, "sector", sector_name))

        # 也检查子领域
        for sub in self._belongs_to.get(sector_name, []):
            result.add((sub, "sector", sub))

        return result

    def _expand_theme_topics(self, theme_name):
        """展开主题下的所有 topic"""
        result = set()
        result.add((theme_name, "theme", theme_name))
        return result

    def get_all_questions(self):
        """获取所有行业/主题的问题列表"""
        return dict(self._data.get("questions", {}))

    # ── 写入 ──────────────────────────────

    def save(self):
        """保存图数据到文件"""
        import yaml
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False,
                      sort_keys=False, width=120)

    def add_company(self, name, ticker, exchange, sectors, themes,
                    news_queries=None, position="", competes_with=None):
        """添加新公司到图"""
        if "companies" not in self._data:
            self._data["companies"] = {}

        self._data["companies"][name] = {
            "ticker": ticker,
            "exchange": exchange,
            "sectors": sectors,
            "themes": themes,
            "news_queries": news_queries or [f"{name} 最新消息"],
            "position": position,
        }
        if competes_with:
            self._data["companies"][name]["competes_with"] = competes_with

        # 重建索引
        self._build_indices()

    def add_edge(self, from_entity, to_entity, edge_type, label=""):
        """添加边"""
        edge = {"from": from_entity, "to": to_entity, "type": edge_type}
        if label:
            edge["label"] = label

        if "edges" not in self._data:
            self._data["edges"] = []

        # 去重
        for e in self._data["edges"]:
            if e["from"] == from_entity and e["to"] == to_entity and e["type"] == edge_type:
                return

        self._data["edges"].append(edge)
        self._build_indices()

    def add_node(self, name, node_type, description="", tier=None,
                 keywords=None, parent_theme=None, parent_sector=None):
        """添加新节点"""
        if "nodes" not in self._data:
            self._data["nodes"] = {}

        node = {
            "type": node_type,
            "description": description,
        }
        if tier is not None:
            node["tier"] = tier
        if keywords:
            node["keywords"] = keywords
        if parent_theme:
            node["parent_theme"] = parent_theme
        if parent_sector:
            node["parent_sector"] = parent_sector

        self._data["nodes"][name] = node
        self._build_indices()


# ── CLI ───────────────────────────────────

def cmd_overview(g):
    nodes = g._data.get("nodes", {})
    companies = g._data.get("companies", {})

    print("=" * 60)
    print("  产业链全景图")
    print("=" * 60)

    by_tier = defaultdict(list)
    for name, info in nodes.items():
        if info.get("type") in ("sector",):
            tier = info.get("tier", 99)
            by_tier[tier].append(name)

    tier_labels = {0: "应用层", 1: "支撑层", 2: "基础设施层",
                   3: "核心器件层", 4: "制造层", 5: "上游基础层"}

    for tier in sorted(by_tier.keys()):
        label = tier_labels.get(tier, f"Tier {tier}")
        print(f"\n── {label} (Tier {tier}) ──")
        for name in by_tier[tier]:
            s = g.get_sector(name)
            desc = s["description"]
            count = len(s["companies"])
            print(f"  {name}: {desc} [{count}家公司]")

            for sub in s["subsectors"]:
                sub_count = len(s["subsector_companies"].get(sub, []))
                print(f"    └─ {sub} [{sub_count}家]")

    print(f"\n{'=' * 60}")
    print(f"  总计: {len(nodes)} 行业/子领域, {len(companies)} 家公司, "
          f"{len(g._data.get('edges', []))} 条关系")
    print(f"{'=' * 60}")


def cmd_company(g, name):
    c = g.get_company(name)
    if not c:
        print(f"Not found: {name}")
        return

    print(f"\n{'=' * 50}")
    print(f"  {c['name']} ({c['ticker']} / {c['exchange']})")
    print(f"  {c['position']}")
    print(f"{'=' * 50}")

    for si in c["sector_info"]:
        print(f"\n  行业: {si['name']} (Tier {si['tier']})")
        if si["upstream"]:
            print(f"    上游: {', '.join(si['upstream'])}")
        if si["downstream"]:
            print(f"    下游: {', '.join(si['downstream'])}")

    if c["competes_with"]:
        print(f"\n  竞争对手: {', '.join(c['competes_with'])}")

    print(f"\n  搜索词: {', '.join(c['news_queries'])}")


def cmd_sector(g, name):
    s = g.get_sector(name)
    if not s:
        print(f"Not found: {name}")
        return

    print(f"\n{'=' * 50}")
    print(f"  {s['name']} (Tier {s['tier']})")
    print(f"  {s['description']}")
    print(f"{'=' * 50}")

    if s["upstream"]:
        print(f"  上游: {', '.join(s['upstream'])}")
    if s["downstream"]:
        print(f"  下游: {', '.join(s['downstream'])}")

    if s["subsectors"]:
        print(f"\n  子领域:")
        for sub in s["subsectors"]:
            sub_comps = s["subsector_companies"].get(sub, [])
            print(f"    {sub}: {', '.join(sub_comps) if sub_comps else '(空)'}")

    if s["companies"]:
        print(f"\n  公司 ({len(s['companies'])}家):")
        for c in s["companies"]:
            info = g.get_company(c)
            print(f"    {c} ({info['ticker']}): {info['position']}")

    if s["questions"]:
        print(f"\n  跟踪问题:")
        for q in s["questions"]:
            print(f"    - {q}")


def cmd_find(g, text):
    print(f"\n文本: {text}")
    print(f"相关实体:")
    for name, etype, topic in g.find_related_entities(text):
        print(f"  [{etype}] {name} → {topic}")


def cmd_generate_nav(g):
    nodes = g._data.get("nodes", {})

    nav = "# 产业链导航\n\n## 全景\n\n"
    nav += "```mermaid\ngraph LR\n"

    for e in g._data.get("edges", []):
        if e["type"] == "upstream_of":
            nav += f"    {e['from']} --> {e['to']}\n"
    nav += "```\n\n"

    by_tier = defaultdict(list)
    for name, info in nodes.items():
        if info.get("type") == "sector":
            by_tier[info.get("tier", 99)].append(name)

    tier_labels = {0: "应用层", 1: "支撑层", 2: "基础设施层",
                   3: "核心器件层", 4: "制造层", 5: "上游基础层"}

    for tier in sorted(by_tier.keys()):
        label = tier_labels.get(tier, f"Tier {tier}")
        nav += f"## {label}\n\n"
        for name in by_tier[tier]:
            s = g.get_sector(name)
            nav += f"### {name}\n{s['description']}\n\n"
            for sub in s["subsectors"]:
                sub_comps = s["subsector_companies"].get(sub, [])
                if sub_comps:
                    nav += f"- {sub}: {', '.join(f'[[{c}]]' for c in sub_comps)}\n"
            if s["companies"]:
                nav += f"- 公司: {', '.join(f'[[{c}]]' for c in s['companies'])}\n"
            nav += "\n"

    path = WIKI_ROOT / "companies" / "_产业链导航.md"
    path.write_text(nav, encoding="utf-8")
    print(f"Generated: {path}")


def main():
    parser = argparse.ArgumentParser(description="产业链拓扑图查询")
    parser.add_argument("--overview", action="store_true")
    parser.add_argument("--company", type=str)
    parser.add_argument("--sector", type=str)
    parser.add_argument("--chain", type=str)
    parser.add_argument("--find", type=str, help="根据文本找相关实体")
    parser.add_argument("--generate-nav", action="store_true")
    args = parser.parse_args()

    g = Graph()

    if args.overview:
        cmd_overview(g)
    elif args.company:
        cmd_company(g, args.company)
    elif args.sector:
        cmd_sector(g, args.sector)
    elif args.chain:
        for path in g.supply_chain_path(args.chain):
            print(" → ".join(path))
    elif args.find:
        cmd_find(g, args.find)
    elif args.generate_nav:
        cmd_generate_nav(g)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
