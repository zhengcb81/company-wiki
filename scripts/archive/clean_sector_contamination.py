#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理行业 wiki 中的污染内容

从半导体设备等行业 wiki 中移除不相关的条目（如机器人、工业软件等）。
"""
import re
from pathlib import Path

WIKI_ROOT = Path('.')

# 定义每个行业的不相关关键词
CONTAMINATION_RULES = {
    '半导体设备': {
        'irrelevant': ['机器人', '工业软件', 'CAD', 'CAE', 'MES', 'PLM', 'ERP', 'DCS', 'SCADA',
                       '建筑IT', '建筑行业', '造价', '施工', 'MCU', '伺服电机', '减速器',
                       '人形机器人', 'Optimus', 'CyberOne', '特斯拉Bot', '广联达', '中望软件',
                       '宝信软件', '中控技术', '华大九天'],
        'relevant': ['半导体设备', '刻蚀', '薄膜沉积', '清洗设备', '光刻', '离子注入', 'CMP',
                     '量检测', '国产化率', '晶圆', '北方华创', '中微公司', '盛美上海',
                     '拓荆科技', '华海清科', '精测电子', '芯源微', '华峰测控', '赛腾股份',
                     '微导纳米', '晶盛机电', '半导体', 'SEMI', '前道', '后道', '资本开支'],
    },
}


def is_entry_contaminated(header, body, rules):
    """判断一个时间线条目是否是污染内容"""
    text = header + body
    has_irrelevant = any(kw in text for kw in rules['irrelevant'])
    has_relevant = any(kw in text for kw in rules['relevant'])
    # 如果有不相关关键词且没有相关关键词，则是污染
    return has_irrelevant and not has_relevant


def clean_wiki(entity_name):
    """清理指定行业的 wiki 页面"""
    if entity_name not in CONTAMINATION_RULES:
        print(f"No contamination rules for {entity_name}")
        return

    rules = CONTAMINATION_RULES[entity_name]
    wiki_file = WIKI_ROOT / 'sectors' / entity_name / 'wiki' / f'{entity_name}.md'

    if not wiki_file.exists():
        print(f"Wiki file not found: {wiki_file}")
        return

    content = wiki_file.read_text(encoding='utf-8')

    # Split content into frontmatter + header and timeline sections
    parts = content.split('## 时间线', 1)
    if len(parts) != 2:
        print(f"Could not find 时间线 section in {wiki_file}")
        return

    header_part = parts[0] + '## 时间线'
    timeline_part = parts[1]

    # Split timeline into entries (### headers)
    # Use regex to split on ### headers while keeping them
    entry_pattern = r'(### [^\n]+)'
    segments = re.split(entry_pattern, timeline_part)

    cleaned_entries = []
    removed_count = 0

    i = 0
    while i < len(segments):
        segment = segments[i]

        # Check if this is a header
        if segment.startswith('### '):
            header = segment
            body = segments[i + 1] if i + 1 < len(segments) else ''

            if is_entry_contaminated(header, body, rules):
                removed_count += 1
                i += 2
                continue

            cleaned_entries.append(header)
            cleaned_entries.append(body)
            i += 2
        else:
            # Non-header content (between entries, or at start/end)
            cleaned_entries.append(segment)
            i += 1

    new_content = header_part + ''.join(cleaned_entries)

    if removed_count > 0:
        wiki_file.write_text(new_content, encoding='utf-8')
        print(f"Cleaned {wiki_file}: removed {removed_count} contaminated entries")
    else:
        print(f"No contamination found in {wiki_file}")


def main():
    import sys
    entities = sys.argv[1:] if len(sys.argv) > 1 else list(CONTAMINATION_RULES.keys())

    for entity in entities:
        print(f"\nProcessing: {entity}")
        clean_wiki(entity)


if __name__ == '__main__':
    main()
