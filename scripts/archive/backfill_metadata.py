#!/usr/bin/env python3
"""
backfill_metadata.py -- 回填所有 wiki 页面的 Dataview 兼容 frontmatter 字段

为每个 wiki 页面补充以下字段（仅在字段不存在时添加）：
- aliases: 从 title 和 entity 名称生成
- sector: 实体所属行业列表（来自 graph.yaml）
- date: 与 last_updated 相同
- ticker: 公司股票代码（仅公司页面）

用法:
    python scripts/backfill_metadata.py              # 执行回填
    python scripts/backfill_metadata.py --dry-run    # 只检查不修改
"""

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from graph import Graph

# Wiki 页面 glob 模式
WIKI_PATTERNS = [
    "companies/*/wiki/*.md",
    "sectors/*/wiki/*.md",
    "themes/*/wiki/*.md",
]


def parse_frontmatter(content):
    """解析 markdown 文件的 YAML frontmatter。

    返回 (metadata_dict, yaml_text, body_start_index)。
    如果没有 frontmatter，返回 ({}, "", 0)。
    yaml_text 是原始的 frontmatter 行文本（不含 --- 标记），用于保留格式。
    """
    if not content.startswith("---"):
        return {}, "", 0

    end = content.find("\n---", 3)
    if end == -1:
        return {}, "", 0

    yaml_text = content[3:end]
    meta = {}
    for line in yaml_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        colon = line.find(":")
        if colon == -1:
            continue
        key = line[:colon].strip()
        value = line[colon + 1:].strip()

        # 解析值
        if value.startswith("[") and value.endswith("]"):
            # YAML 内联列表
            inner = value[1:-1].strip()
            if inner:
                items = [item.strip().strip("'\"") for item in inner.split(",")]
                meta[key] = items
            else:
                meta[key] = []
        elif value.startswith("'") and value.endswith("'"):
            meta[key] = value[1:-1]
        elif value.startswith('"') and value.endswith('"'):
            meta[key] = value[1:-1]
        else:
            # 尝试转数字
            try:
                meta[key] = int(value)
            except ValueError:
                meta[key] = value

    return meta, yaml_text, end + 4  # 跳过 closing ---


def format_yaml_value(value):
    """将 Python 值格式化为 YAML 行文本。"""
    if isinstance(value, list):
        if not value:
            return "[]"
        items = ", ".join(value)
        return f"[{items}]"
    if isinstance(value, int):
        return str(value)
    # 字符串：加引号
    return f'"{value}"'


def append_fields_to_frontmatter(yaml_text, new_fields):
    """在现有的 frontmatter 文本末尾追加新字段行。

    保留原有行的格式不变，仅在末尾追加新字段。
    确保结果以换行符结尾，以便与 closing --- 之间有正确的空行。
    """
    new_lines = []
    for key, value in new_fields:
        new_lines.append(f"{key}: {format_yaml_value(value)}")

    appended = "\n".join(new_lines)

    # 确保 yaml_text 和 appended 之间恰好有一个换行符
    if yaml_text.endswith("\n"):
        return yaml_text + appended + "\n"
    else:
        return yaml_text + "\n" + appended + "\n"


def determine_entity_type_and_name(filepath):
    """从文件路径推断实体类型和实体名称。
    返回 (entity_type, entity_name)，其中 entity_type 为 company/sector/theme。"""
    parts = filepath.relative_to(WIKI_ROOT).parts
    if len(parts) < 4:
        return None, None

    category = parts[0]  # companies, sectors, themes
    entity_name = parts[1]

    if category == "companies":
        return "company", entity_name
    elif category == "sectors":
        return "sector", entity_name
    elif category == "themes":
        return "theme", entity_name

    return None, None


def get_sectors_for_entity(graph, entity_type, entity_name):
    """从 graph.yaml 获取实体所属的行业列表。"""
    if entity_type == "company":
        comp = graph.get_company(entity_name)
        if comp:
            return comp.get("sectors", [])
    elif entity_type == "sector":
        # 行业节点自身
        node_data = graph._data.get("nodes", {}).get(entity_name, {})
        sectors = []
        # 如果有 parent_sector，加入
        for ps in node_data.get("parent_sector", []):
            sectors.append(ps)
        # 自身也算一个行业
        sectors.append(entity_name)
        return sectors
    elif entity_type == "theme":
        # 主题下包含哪些行业？从 edges 找 parent_theme 指向该主题的行业
        sectors = []
        for sname in graph.get_all_sectors():
            node = graph._data.get("nodes", {}).get(sname, {})
            if entity_name in node.get("parent_theme", []):
                sectors.append(sname)
        return sectors

    return []


def get_ticker_for_entity(graph, entity_type, entity_name):
    """获取公司的股票代码，非公司页面返回 None。"""
    if entity_type != "company":
        return None
    comp = graph.get_company(entity_name)
    if comp:
        return comp.get("ticker", "")
    return None


def get_aliases_from_graph(graph, entity_type, entity_name):
    """从 graph.yaml 获取公司预定义的 aliases。"""
    if entity_type != "company":
        return []
    comp_raw = graph._data.get("companies", {}).get(entity_name, {})
    return comp_raw.get("aliases", [])


def generate_aliases(meta, graph, entity_type, entity_name):
    """生成 aliases 列表。基于 title、entity 以及 graph.yaml 中的别名。"""
    aliases = set()

    # 从 title 生成
    title = meta.get("title", "")
    if title:
        aliases.add(title)

    # 从 entity 生成
    entity = meta.get("entity", "")
    if entity:
        aliases.add(entity)

    # 从 graph.yaml 获取预定义别名（仅公司）
    graph_aliases = get_aliases_from_graph(graph, entity_type, entity_name)
    for a in graph_aliases:
        aliases.add(a)

    return sorted(aliases)



def process_file(filepath, graph, dry_run=False):
    """处理单个 wiki 文件，回填缺失的 metadata 字段。
    返回 (updated_fields: list[str], skipped: bool)。"""
    content = filepath.read_text(encoding="utf-8")
    meta, yaml_text, body_start = parse_frontmatter(content)

    if not meta:
        return [], True

    entity_type, entity_name = determine_entity_type_and_name(filepath)
    if not entity_type:
        return [], True

    # 按顺序收集需要追加的新字段
    new_fields = []

    # 1. aliases
    if "aliases" not in meta:
        aliases = generate_aliases(meta, graph, entity_type, entity_name)
        if aliases:
            new_fields.append(("aliases", aliases))

    # 2. sector
    if "sector" not in meta:
        sectors = get_sectors_for_entity(graph, entity_type, entity_name)
        if sectors:
            new_fields.append(("sector", sectors))

    # 3. date (与 last_updated 相同)
    if "date" not in meta:
        last_updated = meta.get("last_updated", "")
        if last_updated:
            new_fields.append(("date", last_updated))

    # 4. ticker (仅公司页面)
    if "ticker" not in meta and entity_type == "company":
        ticker = get_ticker_for_entity(graph, entity_type, entity_name)
        if ticker:
            new_fields.append(("ticker", ticker))

    if not new_fields:
        return [], False

    # 在原始 frontmatter 末尾追加新字段，保留原有格式
    updated_yaml = append_fields_to_frontmatter(yaml_text, new_fields)
    new_frontmatter = "---" + updated_yaml + "---"
    body = content[body_start:]
    new_content = new_frontmatter + body

    if not dry_run:
        filepath.write_text(new_content, encoding="utf-8")

    updated_field_names = [f[0] for f in new_fields]
    return updated_field_names, True


def main():
    parser = argparse.ArgumentParser(description="回填 wiki 页面 Dataview 兼容 metadata")
    parser.add_argument("--dry-run", action="store_true", help="只检查不修改")
    args = parser.parse_args()

    graph = Graph()

    # 收集所有 wiki 文件
    all_files = []
    for pattern in WIKI_PATTERNS:
        all_files.extend(WIKI_ROOT.glob(pattern))

    print(f"扫描到 {len(all_files)} 个 wiki 页面")

    stats = {
        "total": len(all_files),
        "updated": 0,
        "skipped": 0,
        "fields": {
            "aliases": 0,
            "sector": 0,
            "date": 0,
            "ticker": 0,
        },
    }

    for filepath in sorted(all_files):
        fields, was_updated = process_file(filepath, graph, dry_run=args.dry_run)
        if was_updated and fields:
            stats["updated"] += 1
            rel = filepath.relative_to(WIKI_ROOT)
            action = "[DRY-RUN] 将更新" if args.dry_run else "已更新"
            print(f"  {action}: {rel} (+{', '.join(fields)})")
            for f in fields:
                stats["fields"][f] = stats["fields"].get(f, 0) + 1
        else:
            stats["skipped"] += 1

    # 汇总
    print(f"\n{'=' * 50}")
    print(f"总页面: {stats['total']}")
    print(f"{'将更新' if args.dry_run else '已更新'}: {stats['updated']}")
    print(f"跳过: {stats['skipped']}")
    print(f"字段统计:")
    for field, count in stats["fields"].items():
        print(f"  {field}: {count}")
    print(f"{'=' * 50}")

    if args.dry_run and stats["updated"] > 0:
        print("\n使用 --dry-run 模式，未实际修改文件。去掉 --dry-run 以执行更新。")


if __name__ == "__main__":
    main()
