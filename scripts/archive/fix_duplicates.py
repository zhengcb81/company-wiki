#!/usr/bin/env python3
"""
fix_duplicates.py — 修复 wiki 时间线中的重复条目和路径格式问题

功能:
1. 扫描所有 wiki 页面，检测重复的时间线条目（基于日期+标题去重）
2. 修复路径分隔符（反斜杠 → 正斜杠）
3. 移除包含乱码的低质量条目
4. 统计修复结果

用法:
    python3 scripts/fix_duplicates.py --check      # 仅检查，不修改
    python3 scripts/fix_duplicates.py --fix        # 执行修复
"""

import argparse
import os
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent


def is_mojibake(text):
    """检测文本是否包含乱码（mojibake）"""
    # 常见中文乱码模式：Unicode replacement character 或异常字符序列
    mojibake_patterns = [
        '\ufffd',           # Unicode replacement character
        '[\u00c0-\u00ff]{3,}',  # 连续的 Latin-1 补充字符（常见于 UTF-8 被错误解读）
    ]
    for pattern in mojibake_patterns:
        if re.search(pattern, text):
            return True
    return False


def parse_timeline_entries(content):
    """解析时间线条目，返回 (entry_text, header, start_pos, end_pos) 的列表"""
    entries = []

    # 找到时间线部分
    timeline_match = re.search(r'^## 时间线\s*\n', content, re.MULTILINE)
    if not timeline_match:
        return entries

    timeline_start = timeline_match.end()

    # 找到下一个二级标题（综合评估等）
    next_section = re.search(r'\n## [^#]', content[timeline_start:])
    if next_section:
        timeline_end = timeline_start + next_section.start()
    else:
        timeline_end = len(content)

    timeline_text = content[timeline_start:timeline_end]

    # 解析每个条目（### 开头）
    entry_pattern = re.compile(r'\n(### .+?)(?=\n### |\Z)', re.DOTALL)
    for match in entry_pattern.finditer(timeline_text):
        entry_text = match.group(1)
        abs_start = timeline_start + match.start()
        abs_end = timeline_start + match.end()

        # 提取标题行
        header_line = entry_text.split('\n')[0]

        # 提取日期和标题用于去重
        header_match = re.match(r'### (\d{4}-\d{2}-\d{2})\s*\|\s*[^|]+\s*\|\s*(.*)', header_line)
        if header_match:
            date = header_match.group(1)
            title = header_match.group(2).strip()
            # 去掉 wikilink 标记
            title_clean = re.sub(r'\[\[([^]]+)\]\]', r'\1', title)
            key = f"{date}|{title_clean}"
        else:
            key = header_line

        entries.append({
            'text': entry_text,
            'header': header_line,
            'key': key,
            'start': abs_start,
            'end': abs_end,
            'date': header_match.group(1) if header_match else '',
            'title': title_clean if header_match else '',
        })

    return entries


def fix_path_separators(content):
    """修复来源链接中的路径分隔符"""
    # 将反斜杠替换为正斜杠（在 markdown 链接中）
    def normalize_link(match):
        link_text = match.group(1)
        link_url = match.group(2)
        # 将反斜杠替换为正斜杠
        fixed_url = link_url.replace('\\', '/')
        return f'- [{link_text}]({fixed_url})'

    content = re.sub(
        r'- \[(来源)\]\((.+?)\)',
        normalize_link,
        content
    )
    return content


def process_wiki_file(wiki_path, fix_mode=False):
    """处理单个 wiki 文件，检测并修复问题"""
    content = wiki_path.read_text(encoding="utf-8")
    original_content = content

    entries = parse_timeline_entries(content)
    if not entries:
        return {'file': str(wiki_path), 'duplicates': 0, 'mojibake': 0, 'path_fixes': 0}

    # 检测重复
    seen_keys = {}
    duplicates = []
    mojibake_entries = []

    for i, entry in enumerate(entries):
        key = entry['key']

        # 检查乱码
        if is_mojibake(entry['text']):
            mojibake_entries.append(i)

        # 检查重复
        if key in seen_keys:
            # 保留信息更丰富的版本（更长的摘要）
            prev_idx = seen_keys[key]
            prev_len = len(entries[prev_idx]['text'])
            curr_len = len(entry['text'])

            if curr_len > prev_len:
                # 当前条目更丰富，删除之前的
                duplicates.append(prev_idx)
                seen_keys[key] = i
            else:
                # 保留之前的，删除当前
                duplicates.append(i)
        else:
            seen_keys[key] = i

    # 修复路径分隔符
    fixed_content = fix_path_separators(content)
    path_fixes = 1 if fixed_content != content else 0

    # 修复模式：移除重复和乱码条目
    if fix_mode and (duplicates or mojibake_entries):
        # 从后往前删除（不影响前面的索引）
        to_remove = sorted(set(duplicates + mojibake_entries), reverse=True)
        for idx in to_remove:
            entry = entries[idx]
            # 移除这个条目（包括前导换行）
            start = entry['start']
            end = entry['end']
            # 检查前面是否有空行
            while start > 0 and fixed_content[start - 1] == '\n':
                start -= 1
            fixed_content = fixed_content[:start] + fixed_content[end:]

        # 更新 sources_count
        removed_count = len(set(duplicates)) + len(set(mojibake_entries))
        if removed_count > 0:
            count_match = re.search(r'sources_count: (\d+)', fixed_content)
            if count_match:
                old_count = int(count_match.group(1))
                new_count = max(0, old_count - removed_count)
                fixed_content = fixed_content.replace(
                    f"sources_count: {old_count}",
                    f"sources_count: {new_count}"
                )

    if fix_mode and fixed_content != original_content:
        wiki_path.write_text(fixed_content, encoding="utf-8")

    return {
        'file': str(wiki_path),
        'duplicates': len(set(duplicates)),
        'mojibake': len(mojibake_entries),
        'path_fixes': path_fixes,
        'fixed': fix_mode and fixed_content != original_content,
    }


def main():
    parser = argparse.ArgumentParser(description="修复 wiki 时间线重复条目")
    parser.add_argument("--check", action="store_true", help="仅检查，不修改")
    parser.add_argument("--fix", action="store_true", help="执行修复")
    args = parser.parse_args()

    if not args.check and not args.fix:
        args.check = True  # 默认检查模式

    # 扫描所有 wiki 文件
    wiki_files = []
    for directory in ['companies', 'sectors', 'themes']:
        dir_path = WIKI_ROOT / directory
        if dir_path.exists():
            wiki_files.extend(dir_path.rglob("wiki/*.md"))

    print(f"扫描 {len(wiki_files)} 个 wiki 文件...")

    total_duplicates = 0
    total_mojibake = 0
    total_path_fixes = 0
    total_fixed = 0
    issues_found = []

    for wiki_path in sorted(wiki_files):
        result = process_wiki_file(wiki_path, fix_mode=args.fix)

        if result['duplicates'] > 0 or result['mojibake'] > 0 or result['path_fixes'] > 0:
            issues_found.append(result)
            total_duplicates += result['duplicates']
            total_mojibake += result['mojibake']
            total_path_fixes += result['path_fixes']
            if result.get('fixed'):
                total_fixed += 1

            rel = wiki_path.relative_to(WIKI_ROOT)
            status = "FIXED" if result.get('fixed') else "FOUND"
            print(f"  [{status}] {rel}: {result['duplicates']} dupes, {result['mojibake']} mojibake, {result['path_fixes']} path fixes")

    print(f"\n{'='*50}")
    print(f"总计: {len(issues_found)} 个文件有问题")
    print(f"  重复条目: {total_duplicates}")
    print(f"  乱码条目: {total_mojibake}")
    print(f"  路径修复: {total_path_fixes}")
    if args.fix:
        print(f"  已修复: {total_fixed} 个文件")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
