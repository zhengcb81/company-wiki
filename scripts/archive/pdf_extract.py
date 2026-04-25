#!/usr/bin/env python3
"""
pdf_extract.py — PDF 智能提取模块
从财报/研报 PDF 中提取关键章节，生成可用于 ingest 的摘要。

核心思路：不读全文，只提取主营业务相关的章节。

用法：
    from pdf_extract import extract_pdf_summary
    result = extract_pdf_summary("path/to/report.pdf")
    print(result['summary'])
    print(result['sections'])
"""

import re
import os
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# ── 章节识别模式 ──────────────────────────

# 财报中的关键章节标题（按优先级排列）
REPORT_SECTIONS = [
    # 经营讨论与分析（最重要的部分）
    {
        "name": "经营讨论与分析",
        "patterns": [
            r"(?:第.{1,3}节|[\d.]+)\s*管理层.{0,5}讨论.{0,5}分析",
            r"(?:第.{1,3}节|[\d.]+)\s*经营情况.{0,5}讨论",
            r"(?:第.{1,3}节|[\d.]+)\s*经营.{0,3}分析",
            r"管理层讨论与分析",
            r"经营情况讨论与分析",
            r"经营情况的讨论与分析",
        ],
        "max_chars": 8000,
    },
    # 主营业务
    {
        "name": "主营业务",
        "patterns": [
            r"(?:第.{1,3}节|[\d.]+)\s*主营业务.{0,10}分析",
            r"(?:第.{1,3}节|[\d.]+)\s*公司.{0,5}业务",
            r"主营业务分析",
            r"公司主营业务",
            r"业务回顾",
        ],
        "max_chars": 5000,
    },
    # 核心竞争力
    {
        "name": "核心竞争力",
        "patterns": [
            r"(?:第.{1,3}节|[\d.]+)\s*核心竞争力",
            r"(?:第.{1,3}节|[\d.]+)\s*竞争优势",
            r"核心竞争力分析",
        ],
        "max_chars": 3000,
    },
    # 行业格局
    {
        "name": "行业格局",
        "patterns": [
            r"(?:第.{1,3}节|[\d.]+)\s*行业.{0,5}(?:格局|情况|发展)",
            r"所处行业情况",
            r"行业发展趋势",
            r"行业发展",
        ],
        "max_chars": 3000,
    },
    # 未来发展
    {
        "name": "未来展望",
        "patterns": [
            r"(?:第.{1,3}节|[\d.]+)\s*未来.{0,5}(?:发展|展望|规划|计划)",
            r"公司发展战略",
            r"经营计划",
            r"未来展望",
        ],
        "max_chars": 3000,
    },
]

# 投资者关系活动记录的关键模式
IR_SECTIONS = [
    {
        "name": "交流内容",
        "patterns": [
            r"问题.{0,3}[：:]",
            r"问[：:]",
            r"Q[\s：:]",
            r"交流内容",
            r"调研内容",
        ],
        "max_chars": 8000,
    },
]


def find_section_pages_by_scan(doc, total_pages):
    """
    逐页扫描，找到关键章节的正文起始页（跳过目录中的条目）。
    区分方法：目录页中章节标题后跟点号，正文页中标题后跟实际内容。
    """
    section_headers = [
        ("公司简介和主要财务指标", ["公司简介和主要财务指标", "公司简介及主要财务"]),
        ("管理层讨论与分析", ["管理层讨论与分析", "经营情况讨论与分析", "经营情况的讨论与分析"]),
    ]

    found = []
    for page_idx in range(min(60, total_pages)):
        text = doc[page_idx].get_text()
        for name, headers in section_headers:
            if any(f[0] == name for f in found):
                continue
            for header in headers:
                if header in text:
                    # 检查是否是正文页（标题后有实际内容，不是点号）
                    pos = text.find(header)
                    after = text[pos + len(header):pos + len(header) + 100]
                    # 如果标题后紧跟点号，是目录页，跳过
                    if re.match(r'^[.\s·•—–\-]{5,}', after):
                        continue
                    # 是正文页
                    found.append((name, page_idx + 1))
                    break

    # 推算结束页
    result = []
    for i, (name, start) in enumerate(found):
        if i + 1 < len(found):
            end = found[i + 1][1] - 1
        else:
            end = min(start + 30, total_pages)
        result.append((name, start, end))

    return result


def extract_text_from_pdf(pdf_path, max_pages=60):
    """
    从 PDF 智能提取两个关键章节。
    1. 扫描前 60 页找到"公司简介+财务指标"和"管理层讨论与分析"的位置
    2. 只读这两个章节的页面
    """
    if fitz is None:
        return {"error": "PyMuPDF not installed. Run: pip install PyMuPDF"}

    try:
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        text_parts = []
        read_pages = set()

        # 定位章节
        sections = find_section_pages_by_scan(doc, total_pages)

        # 读取目标章节
        for name, start, end in sections:
            for page_idx in range(start - 1, min(end, total_pages)):
                if page_idx not in read_pages and len(read_pages) < max_pages:
                    text = doc[page_idx].get_text()
                    if text.strip():
                        text_parts.append(text)
                    read_pages.add(page_idx)

        # 如果没找到章节，读前 25 页兜底
        if not sections:
            for i in range(min(25, total_pages)):
                text = doc[i].get_text()
                if text.strip():
                    text_parts.append(text)

        doc.close()

        return {
            "text": "\n".join(text_parts),
            "pages_read": len(read_pages) if read_pages else min(25, total_pages),
            "total_pages": total_pages,
            "sections_found": [s[0] for s in sections],
            "total_chars": len("\n".join(text_parts)),
        }
    except Exception as e:
        return {"error": str(e)}


def find_sections(text, section_patterns):
    """在文本中找到匹配的章节"""
    found = []

    for section_def in section_patterns:
        name = section_def["name"]
        patterns = section_def["patterns"]
        max_chars = section_def.get("max_chars", 5000)

        for pattern in patterns:
            matches = list(re.finditer(pattern, text))
            if matches:
                # 取第一个匹配
                m = matches[0]
                start = m.start()

                # 找到章节结束位置（下一个章节标题或字数限制）
                end = min(start + max_chars, len(text))

                # 尝试找下一个主要章节标题
                next_section = re.search(
                    r'\n(?:第[一二三四五六七八九十]+节|[\d]+\.?\d*\s+[^\n]{2,30})\n',
                    text[start + 100:]  # 跳过当前标题
                )
                if next_section:
                    end = min(start + 100 + next_section.start(), end)

                content = text[start:end].strip()

                # 清理：去除多余空白
                content = re.sub(r'\n{3,}', '\n\n', content)
                content = re.sub(r' {2,}', ' ', content)

                if len(content) > 100:  # 忽略太短的匹配
                    found.append({
                        "name": name,
                        "content": content[:max_chars],
                        "char_count": len(content),
                    })
                    break  # 找到一个就够了

    return found


def classify_pdf(filename):
    """根据文件名判断 PDF 类型"""
    name = filename.lower()

    if any(kw in name for kw in ["年报", "半年报", "季报", "年度报告", "季度报告"]):
        return "annual_report"
    elif any(kw in name for kw in ["招股"]):
        return "prospectus"
    elif any(kw in name for kw in ["投资者关系", "调研", "交流"]):
        return "investor_relations"
    elif any(kw in name for kw in ["研报", "深度", "首次覆盖"]):
        return "research_report"
    else:
        return "unknown"


def extract_pdf_summary(pdf_path):
    """
    从 PDF 提取关键摘要。
    返回: {
        'type': 'annual_report' | 'investor_relations' | ...,
        'sections': [{'name': ..., 'content': ...}, ...],
        'summary': '合并后的摘要文本',
        'error': None | 'error message',
    }
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        return {"error": f"File not found: {pdf_path}", "type": "unknown", "sections": [], "summary": ""}

    # 1. 提取文本
    extraction = extract_text_from_pdf(pdf_path)
    if "error" in extraction:
        return {"error": extraction["error"], "type": "unknown", "sections": [], "summary": ""}

    text = extraction["text"]
    if len(text) < 200:
        return {"error": "PDF text too short (may be scanned image)", "type": "unknown", "sections": [], "summary": ""}

    # 2. 判断类型
    pdf_type = classify_pdf(pdf_path.name)

    # 3. 提取关键章节
    if pdf_type == "investor_relations":
        sections = find_sections(text, IR_SECTIONS)
    else:
        sections = find_sections(text, REPORT_SECTIONS)

    # 4. 如果没找到特定章节，取前 3000 字符
    if not sections:
        # 清理后取前 N 字符
        clean = re.sub(r'\s+', ' ', text[:5000]).strip()
        sections = [{"name": "全文摘要", "content": clean[:3000], "char_count": len(clean[:3000])}]

    # 5. 合并为摘要
    summary_parts = []
    for s in sections:
        summary_parts.append(f"【{s['name']}】\n{s['content']}")
    summary = "\n\n".join(summary_parts)

    # 6. 截断到合理长度
    if len(summary) > 10000:
        summary = summary[:10000] + "\n...(truncated)"

    return {
        "type": pdf_type,
        "sections": sections,
        "summary": summary,
        "pages_extracted": extraction.get("pages", 0),
        "total_chars": extraction.get("total_chars", 0),
        "error": None,
    }


# ── CLI ───────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 pdf_extract.py <pdf_path>")
        sys.exit(1)

    result = extract_pdf_summary(sys.argv[1])

    if result["error"]:
        print(f"ERROR: {result['error']}")
    else:
        print(f"Type: {result['type']}")
        print(f"Pages: {result['pages_extracted']}")
        print(f"Sections found: {len(result['sections'])}")
        for s in result["sections"]:
            print(f"\n{'='*50}")
            print(f"  {s['name']} ({s['char_count']} chars)")
            print(f"{'='*50}")
            print(s["content"][:1000])
