#!/usr/bin/env python3
"""
refine.py — LLM 精炼摘要模块
扫描 wiki 页面中质量较低的条目，生成精炼清单供 LLM 处理。

用法：
    # 步骤1：生成待精炼清单
    python3 scripts/refine.py --generate-manifest > refine_manifest.json

    # 步骤2：用 LLM 处理清单（由 Hermes agent 或外部脚本完成）
    # LLM 读取 manifest + raw 内容，输出 refined_summary

    # 步骤3：应用精炼结果
    python3 scripts/refine.py --apply refined_output.json

工作流设计：
    refine.py 负责"扫描+格式化+应用"
    LLM（通过 agent 或 API）负责"理解+总结"
    两者通过 JSON manifest 解耦
"""

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
from extract import extract_summary, clean_text


def scan_wiki_entries(wiki_root):
    """
    扫描所有 wiki 页面，提取时间线条目。
    返回: [{
        'wiki_path': str,       # wiki 文件路径
        'entity': str,          # 公司/行业/主题名
        'topic': str,           # topic 名
        'title': str,           # 条目标题
        'date': str,            # 日期
        'source_type': str,     # 来源类型
        'current_summary': str, # 当前摘要
        'source_file': str,     # 原始文件路径
        'needs_refinement': bool
    }, ...]
    """
    entries = []

    for pattern in [
        f"{wiki_root}/companies/*/wiki/*.md",
        f"{wiki_root}/sectors/*/wiki/*.md",
        f"{wiki_root}/themes/*/wiki/*.md",
    ]:
        for wiki_file in glob.glob(pattern):
            content = Path(wiki_file).read_text(encoding="utf-8")

            # 提取 entity 和 topic
            entity_match = re.search(r'entity:\s*"([^"]+)"', content)
            title_match = re.search(r'title:\s*"([^"]+)"', content)
            entity = entity_match.group(1) if entity_match else ""
            topic = title_match.group(1) if title_match else ""

            # 提取时间线条目
            timeline_pos = content.find("## 时间线")
            if timeline_pos < 0:
                continue

            timeline_section = content[timeline_pos:]

            # 匹配每个 ### 条目
            entry_pattern = r'### (\d{4}-\d{2}-\d{2}) \| ([^|]+) \| (.+?)\n(.*?)(?=\n### |\n## |$)'
            matches = re.findall(entry_pattern, timeline_section, re.DOTALL)

            for date, source_type, entry_title, body in matches:
                # 提取当前摘要（去掉 - [来源] 行）
                summary_lines = []
                for line in body.strip().split('\n'):
                    line = line.strip()
                    if line.startswith('- [来源]') or not line:
                        continue
                    if line.startswith('- '):
                        summary_lines.append(line[2:])
                    else:
                        summary_lines.append(line)

                current_summary = '\n'.join(summary_lines)

                # 提取来源文件路径
                source_match = re.search(r'\[来源\]\(([^)]+)\)', body)
                source_file = ""
                if source_match:
                    source_file = os.path.normpath(
                        os.path.join(os.path.dirname(wiki_file), source_match.group(1))
                    )

                # 判断是否需要精炼
                needs_refinement = _needs_refinement(current_summary, entry_title)

                entries.append({
                    'wiki_path': os.path.relpath(wiki_file, wiki_root),
                    'entity': entity,
                    'topic': topic,
                    'title': entry_title.strip(),
                    'date': date,
                    'source_type': source_type.strip(),
                    'current_summary': current_summary,
                    'source_file': os.path.relpath(source_file, wiki_root) if source_file else "",
                    'needs_refinement': needs_refinement,
                })

    return entries


def _needs_refinement(summary, title):
    """判断条目是否需要 LLM 精炼"""
    # 空摘要
    if not summary or not summary.strip():
        return True

    # 摘要就是标题本身
    if summary.strip() == title.strip():
        return True

    # 摘要过短（少于 20 字）
    if len(summary.strip()) < 20:
        return True

    # 摘要包含网站导航/垃圾文字
    garbage_patterns = [
        '关于我们', '服务条例', '版权声明', '备案号',
        '登录', '注册', '搜索', '订阅',
        '公司 公司新闻', '传递中微芯片',
        '更多', '详情',
    ]
    for p in garbage_patterns:
        if p in summary:
            return True

    return False


def generate_refine_manifest(entries, only_needed=True):
    """
    生成精炼清单。
    返回 JSON 格式，每个条目包含需要 LLM 处理的信息。
    """
    manifest = []
    for e in entries:
        if only_needed and not e['needs_refinement']:
            continue

        # 读取原始文件内容
        raw_content = ""
        if e['source_file']:
            raw_path = WIKI_ROOT / e['source_file']
            if raw_path.exists():
                raw_content = raw_path.read_text(encoding="utf-8", errors="replace")
                # 跳过 frontmatter
                if raw_content.startswith("---"):
                    end = raw_content.find("---", 3)
                    if end > 0:
                        raw_content = raw_content[end+3:]

        manifest.append({
            'wiki_path': e['wiki_path'],
            'entity': e['entity'],
            'topic': e['topic'],
            'date': e['date'],
            'source_type': e['source_type'],
            'title': e['title'],
            'current_summary': e['current_summary'],
            'raw_content': clean_text(raw_content)[:1000],  # 限制长度
        })

    return manifest


def apply_refinements(refinements):
    """
    应用精炼结果到 wiki 文件。
    refinements: [{
        'wiki_path': str,
        'date': str,
        'title': str,
        'refined_summary': str,  # LLM 精炼后的摘要（要点列表）
    }]
    """
    # 按 wiki 文件分组
    by_file = {}
    for r in refinements:
        path = r['wiki_path']
        if path not in by_file:
            by_file[path] = []
        by_file[path].append(r)

    updated_files = 0

    for wiki_relpath, file_refinements in by_file.items():
        wiki_path = WIKI_ROOT / wiki_relpath
        if not wiki_path.exists():
            print(f"  SKIP: {wiki_relpath} not found")
            continue

        content = wiki_path.read_text(encoding="utf-8")
        original = content

        for ref in file_refinements:
            date = ref['date']
            title = ref['title']
            refined = ref['refined_summary']

            # 找到对应的条目并替换摘要
            # 条目格式: ### {date} | {source_type} | {title}\n{summary}\n\n- [来源]
            # 我们需要匹配这个条目并替换 {summary} 部分

            # 构建匹配模式
            entry_start = f"### {date}"
            # 找到标题行
            title_pattern = re.escape(title[:30])  # 取前30字符匹配

            # 找到条目位置
            pos = content.find(entry_start)
            while pos >= 0:
                # 检查标题是否匹配
                line_end = content.find('\n', pos)
                if line_end < 0:
                    break

                entry_line = content[pos:line_end]
                if title[:30] in entry_line:
                    # 找到条目，替换摘要部分
                    # 摘要从条目标题行之后到 "- [来源]" 之前
                    next_entry = content.find('\n### ', line_end)
                    next_section = content.find('\n## ', line_end)
                    source_line = content.find('\n- [来源]', line_end)

                    if source_line < 0:
                        source_line = line_end + 1

                    # 确定摘要区域的结束位置
                    if next_entry > 0 and (next_section < 0 or next_entry < next_section):
                        end_pos = next_entry
                    elif next_section > 0:
                        end_pos = next_section
                    else:
                        end_pos = len(content)

                    # 提取并格式化精炼摘要
                    refined_lines = refined.strip().split('\n')
                    formatted_lines = []
                    for rl in refined_lines:
                        rl = rl.strip()
                        if not rl:
                            continue
                        if rl.startswith('- '):
                            formatted_lines.append(rl)
                        elif rl.startswith('-'):
                            formatted_lines.append(f"- {rl[1:].strip()}")
                        else:
                            formatted_lines.append(f"- {rl}")

                    refined_block = '\n'.join(formatted_lines)

                    # 替换
                    old_summary = content[line_end+1:source_line].strip()
                    new_content = content[:line_end+1] + refined_block + content[source_line:]
                    content = new_content
                    break

                pos = content.find(entry_start, pos + 1)

        if content != original:
            wiki_path.write_text(content, encoding="utf-8")
            updated_files += 1
            print(f"  Updated: {wiki_relpath}")

    return updated_files


def main():
    parser = argparse.ArgumentParser(description="LLM 精炼摘要")
    parser.add_argument("--generate-manifest", action="store_true",
                        help="生成待精炼清单（输出 JSON）")
    parser.add_argument("--all", action="store_true",
                        help="生成清单时包含所有条目（不仅需要精炼的）")
    parser.add_argument("--apply", type=str,
                        help="应用精炼结果（输入 JSON 文件路径）")
    parser.add_argument("--stats", action="store_true",
                        help="显示统计信息")
    args = parser.parse_args()

    if args.stats:
        entries = scan_wiki_entries(WIKI_ROOT)
        needs = [e for e in entries if e['needs_refinement']]
        print(f"Total entries: {len(entries)}")
        print(f"Needs refinement: {len(needs)}")
        print(f"Quality entries: {len(entries) - len(needs)}")
        return

    if args.generate_manifest:
        entries = scan_wiki_entries(WIKI_ROOT)
        manifest = generate_refine_manifest(entries, only_needed=not args.all)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return

    if args.apply:
        with open(args.apply, 'r', encoding='utf-8') as f:
            refinements = json.load(f)
        count = apply_refinements(refinements)
        print(f"\nUpdated {count} files")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
