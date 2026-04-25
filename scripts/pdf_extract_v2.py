#!/usr/bin/env python3
"""
pdf_extract_v2.py — PDF 文本提取模块（v2，LLM驱动简化版）

核心设计变更：
- 去掉60页限制，提取全部可识别文本
- 删除章节提取逻辑（交给LLM判断文档结构）
- 删除截断逻辑（交给LLM决定如何处理超长文本）
- 只做一件事：PDF → 纯文本

用法：
    from pdf_extract_v2 import extract_pdf_text
    result = extract_pdf_text("path/to/report.pdf")
    print(result['text'])
"""

import html
import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


def _clean_text(text: str) -> str:
    """清理提取的文本：移除 surrogates、标准化换行、去除多余空白。"""
    # 移除 UTF-16 surrogates（PyMuPDF 某些旧版本可能产生）
    text = text.encode("utf-8", "surrogatepass").decode("utf-8", "replace")
    # 标准化换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 移除连续空行，保留段落结构
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def _text_quality_score(text: str) -> float:
    """
    评估提取文本的质量分数（0.0 ~ 1.0）。
    分数越低表示越可能是乱码或提取失败。
    """
    if not text:
        return 0.0

    total = len(text)
    if total == 0:
        return 0.0

    # 统计各类字符
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    ascii_chars = len(re.findall(r"[a-zA-Z0-9]", text))
    replacement = text.count("\ufffd")  # Unicode 替换字符 �
    control = sum(1 for c in text if ord(c) < 32 and c not in "\n\t\r")
    high_private = sum(1 for c in text if 0xE000 <= ord(c) <= 0xF8FF)

    # 有效文本比例
    effective = chinese + ascii_chars
    effective_ratio = effective / total

    # 替换字符比例
    replacement_ratio = replacement / total

    # 基础分数
    score = effective_ratio

    # 替换字符惩罚
    score -= replacement_ratio * 2.0

    # 控制字符惩罚
    score -= (control / total) * 0.5

    # 如果完全没有中文和英文，分数归零
    if effective == 0:
        score = 0.0

    return max(0.0, min(1.0, score))


def _extract_page_text(page) -> str:
    """
    从单页提取文本，采用多策略回退机制。

    某些中文 PDF（特别是由 PDFsharp 等工具生成的）会将中文字体错误地声明为
    WinAnsiEncoding，导致 PyMuPDF 的 text 模式在某些环境/版本下返回乱码。
    通过尝试 html / xhtml / dict 等模式，可以在 text 模式失效时获得正确文本。
    """
    strategies = [
        ("text", lambda p: p.get_text("text")),
        ("dict", lambda p: _text_from_dict(p.get_text("dict"))),
        ("xhtml", lambda p: _text_from_html(p.get_text("xhtml"))),
        ("html", lambda p: _text_from_html(p.get_text("html"))),
    ]

    candidates = []
    for name, fn in strategies:
        try:
            raw = fn(page)
            cleaned = _clean_text(raw)
            score = _text_quality_score(cleaned)
            candidates.append((score, cleaned, name))
        except Exception:
            continue

    if not candidates:
        return ""

    # 按质量分数降序排序，选择最佳结果
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_text, best_name = candidates[0]

    # 如果最佳结果质量太低（< 0.05），记录日志（如果有日志系统）
    # 这里静默处理，由调用方通过 is_scanned 等字段判断
    return best_text


def _text_from_dict(text_dict: dict) -> str:
    """从 get_text('dict') 的结构中提取纯文本。"""
    parts = []
    for block in text_dict.get("blocks", []):
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line.get("spans", []):
                parts.append(span.get("text", ""))
        parts.append("\n")
    return "".join(parts)


def _text_from_html(html_text: str) -> str:
    """从 get_text('html') / get_text('xhtml') 中提取纯文本，并解码 HTML entities。"""
    # 先解码 numeric character references，如 &#x66d9; → 曙
    decoded = html.unescape(html_text)
    # 用简单正则去掉 HTML 标签
    text = re.sub(r"<[^>]+>", "", decoded)
    # 将多个空白压缩
    text = re.sub(r"[ \t]+", " ", text)
    # 保留换行结构
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def extract_pdf_text(pdf_path: str, max_pages: Optional[int] = None) -> Dict:
    """
    从 PDF 提取全部可识别文本。

    Args:
        pdf_path: PDF 文件路径
        max_pages: 可选，最大提取页数。None=提取全部

    Returns:
        {
            'text': str,           # 提取的完整文本
            'pages_read': int,     # 实际读取的页数
            'total_pages': int,    # PDF 总页数
            'total_chars': int,    # 提取文本总字符数
            'error': str or None,  # 错误信息
            'is_scanned': bool,    # 是否为扫描版（无法提取文字）
        }
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        return {
            "text": "",
            "pages_read": 0,
            "total_pages": 0,
            "total_chars": 0,
            "error": f"File not found: {pdf_path}",
            "is_scanned": False,
        }

    if fitz is None:
        return {
            "text": "",
            "pages_read": 0,
            "total_pages": 0,
            "total_chars": 0,
            "error": "PyMuPDF not installed. Run: pip install PyMuPDF",
            "is_scanned": False,
        }

    try:
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        text_parts = []
        read_pages = 0
        total_quality_scores = []

        # 确定读取范围
        end_page = max_pages if max_pages else total_pages
        end_page = min(end_page, total_pages)

        for page_idx in range(end_page):
            page = doc[page_idx]
            text = _extract_page_text(page)
            if text.strip():
                text_parts.append(text)
                read_pages += 1
                total_quality_scores.append(_text_quality_score(text))

        doc.close()

        full_text = "\n\n".join(text_parts)
        total_chars = len(full_text)

        # 扫描版判断逻辑：
        # 1. 读取了较多页但字符极少（每页平均 < 50 字符）
        # 2. 或有效文本质量分数极低（平均 < 0.01）
        is_scanned = False
        avg_quality = (
            sum(total_quality_scores) / len(total_quality_scores)
            if total_quality_scores
            else 0.0
        )
        if read_pages >= 5 and total_chars < read_pages * 50:
            is_scanned = True
        elif read_pages >= 3 and avg_quality < 0.01:
            is_scanned = True

        return {
            "text": full_text,
            "pages_read": read_pages,
            "total_pages": total_pages,
            "total_chars": total_chars,
            "error": None,
            "is_scanned": is_scanned,
        }

    except Exception as e:
        return {
            "text": "",
            "pages_read": 0,
            "total_pages": 0,
            "total_chars": 0,
            "error": str(e),
            "is_scanned": False,
        }


def classify_pdf(filename: str) -> str:
    """根据文件名判断 PDF 类型"""
    name = filename.lower()

    if any(kw in name for kw in ["年报", "半年报", "季报", "年度报告", "季度报告", "半年度报告"]):
        return "annual_report"
    elif any(kw in name for kw in ["招股"]):
        return "prospectus"
    elif any(kw in name for kw in ["投资者关系", "调研", "交流", "投资者活动"]):
        return "investor_relations"
    elif any(kw in name for kw in ["研报", "深度", "首次覆盖", "点评"]):
        return "research_report"
    elif any(kw in name for kw in ["公告", "通知", "决议", "提示"]):
        return "announcement"
    else:
        return "unknown"


def split_long_text(text: str, max_chunk_size: int = 15000) -> List[str]:
    """
    将超长文本分段，每段不超过 max_chunk_size 字符。
    分段点优先选择段落边界（\n\n）。
    """
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


# ── CLI ───────────────────────────────────
if __name__ == "__main__":
    # Windows 控制台默认使用 GBK 编码，UTF-8 中文会被显示为乱码（����）。
    # 这里强制将 stdout / stderr 重配置为 UTF-8，确保 CLI 输出正常。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    if len(sys.argv) < 2:
        print("Usage: python3 pdf_extract_v2.py <pdf_path>")
        sys.exit(1)

    result = extract_pdf_text(sys.argv[1])

    if result["error"]:
        print(f"ERROR: {result['error']}")
    else:
        print(f"Total pages: {result['total_pages']}")
        print(f"Pages read: {result['pages_read']}")
        print(f"Total chars: {result['total_chars']}")
        print(f"Is scanned: {result['is_scanned']}")
        print(f"\nFirst 1000 chars:\n{result['text'][:1000]}")
