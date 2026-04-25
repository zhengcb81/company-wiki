#!/usr/bin/env python3
"""清理 sectors/ 目录下行业 wiki 页面的污染数据."""

from pathlib import Path
import sys


def split_sections(lines):
    """将 markdown 行分割为 frontmatter/标题/各 section."""
    sections = {
        'frontmatter': [],
        'title': None,
        'core_issues': [],
        'timeline': [],
        'assessment': [],
        'related': [],
        'other': [],
        'pre': [],          # frontmatter 与第一个 #/## 之间的空行/杂物
    }

    i = 0
    n = len(lines)

    # 1. frontmatter
    if i < n and lines[i].strip() == '---':
        sections['frontmatter'].append(lines[i])
        i += 1
        while i < n and lines[i].strip() != '---':
            sections['frontmatter'].append(lines[i])
            i += 1
        if i < n:
            sections['frontmatter'].append(lines[i])
            i += 1

    # 2. 收集 frontmatter 后到第一个 #/## 之间的内容（通常是空行）
    while i < n:
        stripped = lines[i].strip()
        if stripped.startswith('# '):
            sections['title'] = lines[i]
            i += 1
            break
        if stripped.startswith('## '):
            break
        sections['pre'].append(lines[i])
        i += 1

    # 3. 按 ## 分 section
    current = 'other'
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith('## '):
            name = stripped[3:].strip()
            if name.startswith('核心问题'):
                current = 'core_issues'
            elif name.startswith('时间线'):
                current = 'timeline'
            elif name.startswith('综合评估'):
                current = 'assessment'
            elif name.startswith('相关页面'):
                current = 'related'
            else:
                current = 'other'
            sections[current].append(line)
        else:
            sections[current].append(line)
        i += 1

    return sections


def rebuild(sections):
    """根据规则重建 markdown 内容."""
    out = []

    # frontmatter
    if sections['frontmatter']:
        out.extend(sections['frontmatter'])
        out.append('')

    # title
    if sections['title']:
        out.append(sections['title'])
        out.append('')

    # 核心问题
    if sections['core_issues']:
        out.extend(sections['core_issues'])
        # 保持末尾一个空行，如果原来有的话；简单处理：直接加
        if out and out[-1].strip() != '':
            out.append('')

    # 时间线（清空）
    out.append('## 时间线')
    out.append('')
    out.append('（待补充）')
    out.append('')

    # 相关页面
    if sections['related']:
        out.extend(sections['related'])
        if out and out[-1].strip() != '':
            out.append('')

    # 其他 section（保留）
    if sections['other']:
        out.extend(sections['other'])
        if out and out[-1].strip() != '':
            out.append('')

    # 去掉尾部多余空行，保留一个换行结尾
    while len(out) > 1 and out[-1] == '' and out[-2] == '':
        out.pop()

    return '\n'.join(out) + '\n'


def main():
    root = Path('sectors')
    files = sorted(root.rglob('*.md'))
    processed = 0

    for f in files:
        raw = f.read_text(encoding='utf-8')
        lines = raw.splitlines()
        sections = split_sections(lines)
        new_content = rebuild(sections)

        # 只在内容变化时写回，避免无意义 IO
        if new_content != raw:
            f.write_text(new_content, encoding='utf-8')
            processed += 1
            print(f'[已修改] {f}')
        else:
            print(f'[无变化] {f}')

    print(f'\n总计处理文件数: {len(files)}')
    print(f'实际修改文件数: {processed}')


if __name__ == '__main__':
    main()
