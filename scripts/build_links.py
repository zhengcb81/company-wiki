#!/usr/bin/env python3
"""构建 wikilink 跨页面关联索引 links.yml.

基于 graph.yaml 拓扑 + wiki 页面内容中的实体名提及，
构建正向和反向引用关系，检测孤立页面。
"""

import os, re, sys
import yaml
from pathlib import Path
from collections import defaultdict

from common import WIKI_ROOT as BASE
from graph import Graph


def main():
    base = BASE
    # 修：用 Graph 类加载 companies/sectors（Graph 从 companies.yaml/sectors.yaml 读，
    # 不是 graph.yaml；graph.yaml 只有 edges/questions/settings）
    g = Graph(str(base / "graph.yaml"))
    companies = {c["name"]: g.get_company(c["name"]) for c in g.get_all_companies()}

    sector_names = g.get_all_sectors()
    sectors = {name: g.get_sector(name) for name in sector_names}
    sectors = {k: v for k, v in sectors.items() if v is not None}

    # themes 暂无独立数据源，留空（graph.yaml 无 themes section）
    themes = {}

    all_names = set()
    all_names.update(companies.keys())
    all_names.update(sectors.keys())
    all_names.update(themes.keys())

    # 扫描 wiki 页面
    wiki_pages = {}  # entity_key -> {topic: rel_path}
    for md in sorted(base.rglob("wiki/*.md")):
        rel = str(md.relative_to(base)).replace("\\", "/")
        parts = rel.split("/")
        if len(parts) >= 3:
            entity_key = f"{parts[0]}/{parts[1]}"
            topic = parts[3].replace(".md", "") if len(parts) >= 4 else md.stem
            if entity_key not in wiki_pages:
                wiki_pages[entity_key] = {}
            wiki_pages[entity_key][topic] = rel

    # 1) 基于拓扑构建关联
    topology_links = defaultdict(set)
    for name, info in companies.items():
        comp_key = f"companies/{name}"
        for sec_name in info.get("sectors", []):
            sec_key = f"sectors/{sec_name}"
            topology_links[comp_key].add(sec_key)
            topology_links[sec_key].add(comp_key)
        for theme_name in info.get("themes", []):
            theme_key = f"themes/{theme_name}"
            topology_links[comp_key].add(theme_key)
            topology_links[theme_key].add(comp_key)
        for comp_name in info.get("competes_with", []):
            comp2_key = f"companies/{comp_name}"
            topology_links[comp_key].add(comp2_key)

    # 2) 基于内容中的实体名提及构建关联
    content_links = defaultdict(set)
    for md in sorted(base.rglob("wiki/*.md")):
        rel = str(md.relative_to(base)).replace("\\", "/")
        parts = rel.split("/")
        if len(parts) < 2:
            continue
        entity_key = f"{parts[0]}/{parts[1]}"
        self_name = parts[1]
        content = md.read_text(encoding="utf-8")

        for name in all_names:
            if name in content and name != self_name:
                # 推断目标实体类型
                if name in companies:
                    content_links[entity_key].add(f"companies/{name}")
                elif name in sectors:
                    content_links[entity_key].add(f"sectors/{name}")
                elif name in themes:
                    content_links[entity_key].add(f"themes/{name}")

    # 合并
    all_links = defaultdict(set)
    for key, targets in topology_links.items():
        all_links[key].update(targets)
    for key, targets in content_links.items():
        all_links[key].update(targets)

    # 构建输出
    links_data = {"links": {}, "entities": {}}
    for key in sorted(all_links.keys()):
        links_data["links"][key] = sorted(all_links[key])
    for key, topics in wiki_pages.items():
        links_data["entities"][key] = topics

    out_path = base / "links.yml"
    out_path.write_text(
        yaml.dump(links_data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    total = sum(len(v) for v in links_data["links"].values())
    print(f"Generated {out_path}")
    print(f"  Entities: {len(links_data['entities'])}")
    print(f"  Connected: {len(links_data['links'])}")
    print(f"  Total links: {total}")

    # 检查孤立实体
    all_entity_keys = set(links_data["entities"].keys())
    connected_keys = set(links_data["links"].keys())
    orphans = sorted(all_entity_keys - connected_keys)
    if orphans:
        print(f"  Orphans: {len(orphans)}")
        for o in orphans[:5]:
            print(f"    {o}")


if __name__ == "__main__":
    main()
