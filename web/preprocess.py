#!/usr/bin/env python3
"""
preprocess.py — 将 wiki markdown 转换为 MkDocs 兼容格式

核心任务:
1. 目录映射: companies/中微公司/wiki/公司动态.md → docs/公司/中微公司/公司动态.md
2. Wikilinks 转换: [[中际旭创]] → 正确的相对路径链接
3. 索引页: 从根 index.md 转换生成首页
4. 导航: 生成 mkdocs.yml 中的 nav 配置
5. 图谱数据: 从 graph.yaml 导出 JSON
"""

import re
import json
import shutil
import yaml
import logging
from pathlib import Path
from collections import defaultdict
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

WIKI_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent
DOCS_DIR = WEB_DIR / "docs"
GRAPH_PATH = WIKI_ROOT / "graph.yaml"


# ── 全局索引：页面名 → 目标路径 ──

def scan_wiki_pages() -> dict:
    """
    扫描所有 wiki 页面，构建 {页面名/实体名: 目标相对路径} 映射。

    目标路径格式:
      companies/中微公司/wiki/公司动态.md → 公司/中微公司/公司动态.md
      sectors/光模块/wiki/光模块.md       → 行业/光模块/光模块.md
      themes/AI产业链/wiki/AI产业链.md     → 主题/AI产业链/AI产业链.md
    """
    page_map = {}  # key → docs/ 下的相对路径
    seen_titles = defaultdict(list)

    patterns = [
        ("companies", "公司"),
        ("sectors", "行业"),
        ("themes", "主题"),
    ]

    for src_top, dst_top in patterns:
        src_dir = WIKI_ROOT / src_top
        if not src_dir.exists():
            continue

        for entity_dir in sorted(src_dir.iterdir()):
            if not entity_dir.is_dir():
                continue
            if entity_dir.name.startswith("_"):
                continue

            wiki_dir = entity_dir / "wiki"
            if not wiki_dir.exists():
                continue

            entity_name = entity_dir.name

            for md_file in sorted(wiki_dir.glob("*.md")):
                page_name = md_file.stem
                dst_rel = f"{dst_top}/{entity_name}/{page_name}.md"

                # 用实体名作为 key（指向第一个 wiki 页面，通常是公司动态）
                if entity_name not in page_map:
                    page_map[entity_name] = dst_rel

                # 用 "实体名/页面名" 作为 key
                page_map[f"{entity_name}/{page_name}"] = dst_rel

                # 用文件名（去重后加前缀）
                if page_name not in seen_titles or len(seen_titles[page_name]) < 5:
                    page_map[page_name] = dst_rel
                seen_titles[page_name].append(entity_name)

    # 特殊页面
    nav_page = WIKI_ROOT / "companies" / "_产业链导航.md"
    if nav_page.exists():
        page_map["_产业链导航"] = "产业链导航.md"

    return page_map


def convert_wikilinks(content: str, page_map: dict, current_rel_path: str) -> str:
    """
    将 [[wikilinks]] 转换为标准 markdown 链接。

    支持:
      [[实体名]]          → [实体名](相对路径)
      [[路径/页面|显示文字]] → [显示文字](相对路径)
      [[实体名|显示文字]]   → [显示文字](相对路径)
    """
    current_depth = current_rel_path.count("/")
    prefix = "../" * current_depth if current_depth > 0 else ""

    def replace_link(match):
        inner = match.group(1)

        # 分离显示文字
        if "|" in inner:
            target, display = inner.split("|", 1)
            target = target.strip()
            display = display.strip()
        else:
            target = inner.strip()
            display = target

        # 查找目标路径
        dst_path = page_map.get(target)

        # 尝试去掉路径前缀再找
        if dst_path is None and "/" in target:
            parts = target.split("/")
            for i in range(len(parts)):
                key = "/".join(parts[i:])
                if key in page_map:
                    dst_path = page_map[key]
                    break

        if dst_path is None:
            # 未找到目标，保持原样（MkDocs 会显示为普通文本）
            return match.group(0)

        # 计算相对路径
        if prefix:
            rel = prefix + dst_path
        else:
            rel = "./" + dst_path if not dst_path.startswith("./") else dst_path

        # 移除 .md 后缀（MkDocs 自动处理）
        if rel.endswith(".md"):
            rel = rel[:-3]

        return f"[{display}]({quote(rel, safe='/:@!$&\'()*+,;=-._~')})"

    # 匹配 [[...]] 但不匹配已在代码块中的
    result = []
    in_code_block = False
    pos = 0

    while pos < len(content):
        # 跳过代码块
        if content[pos:pos+3] == "```":
            in_code_block = not in_code_block
            result.append(content[pos:pos+3])
            pos += 3
            continue

        if in_code_block:
            result.append(content[pos])
            pos += 1
            continue

        # 跳过行内代码
        if content[pos] == "`":
            end = content.find("`", pos + 1)
            if end > pos:
                result.append(content[pos:end+1])
                pos = end + 1
                continue

        # 匹配 [[wikilink]]
        if content[pos:pos+2] == "[[":
            end = content.find("]]", pos + 2)
            if end > pos:
                link_text = content[pos+2:end]
                result.append(replace_link(type('', (), {'group': lambda self, n: link_text})()))
                pos = end + 2
                continue

        result.append(content[pos])
        pos += 1

    return "".join(result)


def copy_and_convert(page_map: dict) -> dict:
    """
    复制 wiki 文件到 docs/ 目录，同时转换 wikilinks。
    返回导航结构 {分类: {实体: [页面列表]}}
    """
    # 清理并重建 docs/ 目录
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True)

    # 创建子目录
    (DOCS_DIR / "公司").mkdir()
    (DOCS_DIR / "行业").mkdir()
    (DOCS_DIR / "主题").mkdir()
    (DOCS_DIR / "数据").mkdir()

    nav = defaultdict(lambda: defaultdict(list))
    stats = {"pages": 0, "links_converted": 0}

    patterns = [
        ("companies", "公司"),
        ("sectors", "行业"),
        ("themes", "主题"),
    ]

    for src_top, dst_top in patterns:
        src_dir = WIKI_ROOT / src_top
        if not src_dir.exists():
            continue

        for entity_dir in sorted(src_dir.iterdir()):
            if not entity_dir.is_dir():
                continue
            if entity_dir.name.startswith("_"):
                continue

            wiki_dir = entity_dir / "wiki"
            if not wiki_dir.exists():
                continue

            entity_name = entity_dir.name
            entity_dst = DOCS_DIR / dst_top / entity_name
            entity_dst.mkdir(exist_ok=True)

            for md_file in sorted(wiki_dir.glob("*.md")):
                page_name = md_file.stem
                dst_file = entity_dst / f"{page_name}.md"
                dst_rel = f"{dst_top}/{entity_name}/{page_name}.md"

                content = md_file.read_text(encoding="utf-8")

                # 统计原始链接数
                orig_links = content.count("[[")

                # 转换 wikilinks
                converted = convert_wikilinks(content, page_map, dst_rel)

                new_links = converted.count("[[")
                stats["links_converted"] += orig_links - new_links

                dst_file.write_text(converted, encoding="utf-8")
                nav[dst_top][entity_name].append(f"{dst_top}/{entity_name}/{page_name}")
                stats["pages"] += 1

    # 复制 _产业链导航.md
    nav_src = WIKI_ROOT / "companies" / "_产业链导航.md"
    if nav_src.exists():
        content = nav_src.read_text(encoding="utf-8")
        converted = convert_wikilinks(content, page_map, "产业链导航.md")
        (DOCS_DIR / "产业链导航.md").write_text(converted, encoding="utf-8")
        stats["pages"] += 1

    # 生成首页
    generate_homepage(page_map)

    # 生成 tags 页
    generate_tags_page()

    logger.info(f"转换完成: {stats['pages']} 页面, {stats['links_converted']} 个 wikilinks 已转换")
    return dict(nav)


def generate_homepage(page_map: dict):
    """生成 docs/index.md 首页"""
    # 读取原始 index.md 作为参考
    src_index = WIKI_ROOT / "index.md"
    if src_index.exists():
        content = src_index.read_text(encoding="utf-8")
        # 转换 wikilinks（相对于根目录）
        converted = convert_wikilinks(content, page_map, "index.md")
        # 替换 frontmatter 中的 title（确保 MkDocs 正确显示）
        converted = re.sub(r'^---\n', '---\nhide:\n  - navigation\n\n', converted, count=1)
        (DOCS_DIR / "index.md").write_text(converted, encoding="utf-8")
    else:
        (DOCS_DIR / "index.md").write_text("# 上市公司知识库\n\n欢迎使用知识库。\n", encoding="utf-8")


def generate_tags_page():
    """生成 docs/tags.md"""
    content = "---\ntitle: 标签\n---\n\n# 标签索引\n\n本页面由 MkDocs Tags 插件自动生成。\n"
    (DOCS_DIR / "tags.md").write_text(content, encoding="utf-8")


def update_mkdocs_nav(nav_yaml: str):
    """在 mkdocs.yml 中注入 nav 配置。

    使用标记注释 # BEGIN_AUTO_NAV / # END_AUTO_NAV 来定位替换区域，
    避免解析含 !!python/name 标签的 YAML。
    """
    mkdocs_path = WEB_DIR / "mkdocs.yml"
    content = mkdocs_path.read_text(encoding="utf-8")

    begin_marker = "# BEGIN_AUTO_NAV"
    end_marker = "# END_AUTO_NAV"

    if begin_marker not in content:
        # 首次：追加到文件末尾
        content = content.rstrip() + f"\n\n{begin_marker}\nnav:\n{nav_yaml}\n{end_marker}\n"
    else:
        # 后续：替换标记之间的内容
        begin_idx = content.index(begin_marker) + len(begin_marker)
        end_idx = content.index(end_marker)
        content = content[:begin_idx] + f"\nnav:\n{nav_yaml}\n" + content[end_idx:]

    mkdocs_path.write_text(content, encoding="utf-8")
    logger.info("已更新 mkdocs.yml nav 配置")


def generate_nav_config(nav: dict) -> dict:
    """生成 mkdocs.yml 的 nav 部分"""
    nav_items = [
        {"首页": "index.md"},
    ]

    if "产业链导航.md" in str(DOCS_DIR.iterdir() if DOCS_DIR.exists() else []):
        nav_items.append({"产业链": "产业链导航.md"})

    # 公司
    if "公司" in nav:
        company_nav = []
        for entity, pages in sorted(nav["公司"].items()):
            if len(pages) == 1:
                company_nav.append({entity: pages[0]})
            else:
                company_nav.append({entity: pages})
        nav_items.append({"公司": company_nav})

    # 行业
    if "行业" in nav:
        sector_nav = []
        for entity, pages in sorted(nav["行业"].items()):
            if len(pages) == 1:
                sector_nav.append({entity: pages[0]})
            else:
                sector_nav.append({entity: pages})
        nav_items.append({"行业": sector_nav})

    # 主题
    if "主题" in nav:
        theme_nav = []
        for entity, pages in sorted(nav["主题"].items()):
            if len(pages) == 1:
                theme_nav.append({entity: pages[0]})
            else:
                theme_nav.append({entity: pages})
        nav_items.append({"主题": theme_nav})

    # 图谱页面
    if (DOCS_DIR / "图谱.md").exists():
        nav_items.append({"图谱": "图谱.md"})

    return nav_items


# ── 图谱数据导出 ──

def export_graph_data():
    """从 graph.yaml 导出 JSON 用于 vis.js 可视化"""
    if not GRAPH_PATH.exists():
        logger.warning(f"graph.yaml 不存在: {GRAPH_PATH}")
        return

    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        g = yaml.safe_load(f)

    nodes = []
    edges = []

    # 颜色映射
    type_colors = {
        "theme":      {"background": "#FF6B00", "border": "#E65100"},
        "sector":     {"background": "#2196F3", "border": "#1565C0"},
        "subsector":  {"background": "#64B5F6", "border": "#42A5F5"},
        "company":    {"background": "#4CAF50", "border": "#2E7D32"},
    }

    tier_labels = {
        0: "应用层", 1: "支撑层", 2: "基础设施层",
        3: "核心器件层", 4: "制造层", 5: "上游基础层",
    }

    # 从 nodes 提取
    for name, info in g.get("nodes", {}).items():
        node_type = info.get("type", "sector")
        tier = info.get("tier", 99)
        node = {
            "id": name,
            "label": name,
            "type": node_type,
            "tier": tier,
            "tier_label": tier_labels.get(tier, ""),
            "description": info.get("description", ""),
            "color": type_colors.get(node_type, type_colors["sector"]),
        }
        if node_type == "sector":
            node["font"] = {"size": 16, "bold": True}
            node["size"] = 30
        elif node_type == "theme":
            node["font"] = {"size": 20, "bold": True}
            node["size"] = 40
        elif node_type == "subsector":
            node["font"] = {"size": 13}
            node["size"] = 20
        nodes.append(node)

    # 从 companies 提取
    for name, info in g.get("companies", {}).items():
        node = {
            "id": name,
            "label": f"{name}\n{info.get('ticker', '')}",
            "type": "company",
            "ticker": info.get("ticker", ""),
            "exchange": info.get("exchange", ""),
            "position": info.get("position", ""),
            "sectors": info.get("sectors", []),
            "color": type_colors["company"],
            "font": {"size": 12},
            "size": 15,
        }
        nodes.append(node)

        # 添加 company → sector 边
        for sector in info.get("sectors", []):
            edges.append({
                "from": name,
                "to": sector,
                "type": "belongs_to",
                "arrows": "to",
                "color": {"color": "#4CAF50", "opacity": 0.4},
                "width": 1,
            })

        # 添加 competes_with 边
        for competitor in info.get("competes_with", []):
            edges.append({
                "from": name,
                "to": competitor,
                "type": "competes_with",
                "arrows": "",
                "dashes": True,
                "color": {"color": "#F44336", "opacity": 0.5},
                "width": 1,
                "label": "竞争",
            })

    # 原始 edges（sector 之间的关系）
    for edge in g.get("edges", []):
        src = edge.get("from", edge.get("source", ""))
        tgt = edge.get("to", edge.get("target", ""))
        edge_type = edge.get("type", "")

        vis_edge = {
            "from": src,
            "to": tgt,
            "type": edge_type,
            "label": edge.get("label", ""),
        }

        if edge_type == "upstream_of":
            vis_edge["arrows"] = "to"
            vis_edge["color"] = {"color": "#2196F3", "opacity": 0.6}
            vis_edge["width"] = 2
        elif edge_type == "belongs_to":
            vis_edge["arrows"] = "to"
            vis_edge["color"] = {"color": "#64B5F6", "opacity": 0.4}
            vis_edge["width"] = 1
            vis_edge["dashes"] = True

        edges.append(vis_edge)

    graph_data = {"nodes": nodes, "edges": edges}

    # 写入 JSON
    data_dir = DOCS_DIR / "数据"
    data_dir.mkdir(exist_ok=True)
    data_file = data_dir / "graph_data.json"
    data_file.write_text(json.dumps(graph_data, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"图谱数据导出: {len(nodes)} 节点, {len(edges)} 边 → {data_file}")


def generate_graph_page():
    """生成 docs/图谱.md — 嵌入 vis.js 的交互式图谱页面"""
    content = """---
title: 产业链图谱
---

# 产业链图谱

交互式产业链关系图谱。拖拽节点、滚轮缩放、点击节点查看详情。

<div id="graph-controls" style="margin-bottom: 16px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
  <input type="text" id="graph-search" placeholder="搜索节点..." style="padding: 6px 12px; border-radius: 4px; border: 1px solid #555; background: var(--md-default-bg-color); color: var(--md-typeset-color); width: 200px;">
  <select id="graph-filter" style="padding: 6px 12px; border-radius: 4px; border: 1px solid #555; background: var(--md-default-bg-color); color: var(--md-typeset-color);">
    <option value="all">全部</option>
    <option value="theme">主题</option>
    <option value="sector">行业</option>
    <option value="subsector">子行业</option>
    <option value="company">公司</option>
  </select>
  <button id="graph-reset" style="padding: 6px 12px; border-radius: 4px; border: 1px solid #555; background: var(--md-default-bg-color); color: var(--md-typeset-color); cursor: pointer;">重置视图</button>
</div>

<div id="network-graph" style="width: 100%; height: 600px; border: 1px solid #555; border-radius: 8px;"></div>

<div id="node-info" style="margin-top: 16px; padding: 12px; border-radius: 8px; background: var(--md-default-bg-color); display: none;">
  <h3 id="node-title"></h3>
  <p id="node-desc"></p>
  <div id="node-links"></div>
</div>

<script src="数据/vis-network.min.js"></script>
<script>
fetch('数据/graph_data.json')
  .then(r => r.json())
  .then(data => {
    const container = document.getElementById('network-graph');
    const allNodes = new vis.DataSet(data.nodes);
    const allEdges = new vis.DataSet(data.edges);

    const options = {
      nodes: {
        shape: 'dot',
        borderWidth: 2,
        shadow: true,
      },
      edges: {
        smooth: { type: 'continuous' },
        font: { size: 10, strokeWidth: 3, strokeColor: '#ffffff' },
      },
      physics: {
        forceAtlas2Based: {
          gravitationalConstant: -80,
          centralGravity: 0.01,
          springLength: 100,
          springConstant: 0.08,
        },
        maxVelocity: 50,
        solver: 'forceAtlas2Based',
        timestep: 0.35,
        stabilization: { iterations: 150 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        navigationButtons: false,
        keyboard: true,
      },
    };

    const network = new vis.Network(container, { nodes: allNodes, edges: allEdges }, options);

    // 点击节点
    network.on('click', function(params) {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = allNodes.get(nodeId);
        const infoDiv = document.getElementById('node-info');
        const titleEl = document.getElementById('node-title');
        const descEl = document.getElementById('node-desc');
        const linksEl = document.getElementById('node-links');

        titleEl.textContent = node.label.replace(/\\n.*/, '');
        descEl.textContent = node.description || node.position || '';
        linksEl.innerHTML = '';

        if (node.type === 'company') {
          const link = document.createElement('a');
          link.href = '../公司/' + encodeURIComponent(nodeId) + '/';
          link.textContent = '查看公司 Wiki →';
          link.style.color = 'var(--md-primary-fg-color)';
          linksEl.appendChild(link);
        }

        infoDiv.style.display = 'block';
      }
    });

    // 搜索
    document.getElementById('graph-search').addEventListener('input', function(e) {
      const query = e.target.value.toLowerCase();
      if (!query) {
        allNodes.forEach(n => allNodes.update({ id: n.id, opacity: 1.0 }));
        return;
      }
      allNodes.forEach(n => {
        const match = n.label.toLowerCase().includes(query) || (n.description || '').toLowerCase().includes(query);
        allNodes.update({ id: n.id, opacity: match ? 1.0 : 0.15 });
      });
    });

    // 类型过滤
    document.getElementById('graph-filter').addEventListener('change', function(e) {
      const filter = e.target.value;
      allNodes.forEach(n => {
        const show = filter === 'all' || n.type === filter;
        allNodes.update({ id: n.id, hidden: !show });
      });
    });

    // 重置
    document.getElementById('graph-reset').addEventListener('click', function() {
      network.fit({ animation: true });
      document.getElementById('graph-search').value = '';
      document.getElementById('graph-filter').value = 'all';
      allNodes.forEach(n => allNodes.update({ id: n.id, opacity: 1.0, hidden: false }));
    });
  });
</script>
"""
    (DOCS_DIR / "图谱.md").write_text(content, encoding="utf-8")
    logger.info("已生成 docs/图谱.md")


def download_visjs():
    """下载 vis-network.min.js 到 docs/数据/ 目录"""
    target = DOCS_DIR / "数据" / "vis-network.min.js"
    if target.exists():
        logger.info("vis-network.min.js 已存在，跳过下载")
        return

    import urllib.request
    vis_url = "https://unpkg.com/vis-network@9.1.9/dist/vis-network.min.js"

    logger.info(f"下载 vis-network.min.js ...")
    try:
        urllib.request.urlretrieve(vis_url, str(target))
        logger.info(f"已下载: {target}")
    except Exception as e:
        logger.warning(f"下载失败: {e}")
        logger.warning("请手动下载 vis-network.min.js 放到 web/docs/数据/ 目录")
        # 创建一个占位文件
        target.write_text("// vis-network.min.js - 请手动下载\n", encoding="utf-8")


# ── 主流程 ──

def main():
    import subprocess
    import sys

    logger.info("=== 开始预处理 ===")

    # 1. 扫描页面，构建映射
    logger.info("扫描 wiki 页面...")
    page_map = scan_wiki_pages()
    logger.info(f"找到 {len(page_map)} 个页面映射")

    # 2. 复制并转换
    logger.info("复制并转换页面...")
    nav = copy_and_convert(page_map)

    # 3. 导出图谱数据
    logger.info("导出图谱数据...")
    export_graph_data()

    # 4. 生成图谱页面
    generate_graph_page()

    # 5. 下载 vis.js
    download_visjs()

    # 6. 更新 mkdocs.yml 的 nav（在 # AUTO_NAV 注释之间注入）
    nav_config = generate_nav_config(nav)
    nav_yaml = yaml.dump(nav_config, allow_unicode=True, default_flow_style=False, sort_keys=False)
    update_mkdocs_nav(nav_yaml)

    # 7. 构建 MkDocs 站点
    logger.info("构建 MkDocs 站点...")
    result = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--clean"],
        cwd=str(WEB_DIR),
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        logger.info("构建成功!")
        dist_dir = WEB_DIR / "dist"
        index_file = dist_dir / "index.html"
        logger.info(f"输出目录: {dist_dir}")
        logger.info(f"打开浏览器: start {index_file}")
    else:
        logger.error(f"构建失败:\n{result.stderr}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
