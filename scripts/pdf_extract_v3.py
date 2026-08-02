#!/usr/bin/env python3
"""
pdf_extract_v3.py — 增强版 PDF 提取模块

核心改进：
1. classify_pdf_v2: 多策略分类（精确匹配 → LLM辅助 → 规则兜底）
2. extract_tables: 表格提取与 Markdown 格式化
3. validate_extraction: 检查点1（提取质量验证）

用法：
    from pdf_extract_v3 import classify_pdf_v2, extract_pdf_text_v3, validate_extraction

    # 分类
    result = classify_pdf_v2("东方电缆：2024年半年度报告.pdf")
    print(result)  # {"doc_type": "semi_annual", "period": "2024-06-30", ...}

    # 提取
    extract = extract_pdf_text_v3("path/to/report.pdf")

    # 验证
    validation = validate_extraction(extract, "semi_annual")
"""

import re
import html
from pathlib import Path
from typing import Dict, List, Optional, Union

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# ── 文档类型定义 ──────────────────────────
DOC_TYPES = {
    "annual_report": {
        "min_chars": 50000,
        "required_sections": ["管理层讨论", "财务报告"],
    },
    "semi_annual_report": {
        "min_chars": 20000,
        "required_sections": ["管理层讨论", "主要会计数据"],
    },
    "quarterly_report": {"min_chars": 10000, "required_sections": ["主要会计数据"]},
    "prospectus": {
        "min_chars": 80000,
        "required_sections": ["业务与技术", "财务会计信息"],
    },
    "investor_relations": {"min_chars": 1000, "required_sections": ["投资者关系"]},
    "research_report": {"min_chars": 5000, "required_sections": []},
    "announcement": {"min_chars": 500, "required_sections": []},
    "abstract": {"min_chars": 0, "required_sections": []},  # 摘要，跳过
    "unknown": {"min_chars": 0, "required_sections": []},
}


# ── 精确匹配规则（按优先级排序）──────────────────
# 顺序很重要！必须先匹配更具体的模式（半年报）再匹配泛化模式（年报）
EXACT_PATTERNS = [
    # 摘要（必须最先检查，避免被后续规则匹配）
    (r"摘要", "abstract", None, True),  # skip=True
    # 半年报（必须在年报前检查！）
    (r"半年度?报告", "semi_annual_report", "06-30", False),
    # 季报（按季度细分）
    (r"第一季度|一季度|Q1|1季报", "quarterly_report", "03-31", False),
    (r"第二季度|二季度|Q2|2季报", "quarterly_report", "06-30", False),
    (r"第三季度|三季度|Q3|3季报", "quarterly_report", "09-30", False),
    (r"第四季度|四季度|Q4|4季报", "quarterly_report", "12-31", False),
    # 年报（必须在半年报/季报后检查！）
    (r"年度?报告", "annual_report", "12-31", False),
    # 招股说明书
    (r"招股说明书|招股意向书", "prospectus", None, False),
    # 投资者关系
    (r"投资者关系|投资者活动|调研|交流", "investor_relations", None, False),
    # 研报
    (r"深度报告|首次覆盖|点评报告|研究报告|行业研究", "research_report", None, False),
    # 券商研报格式：日期-证券公司-公司名-代码-标题
    # 支持：中信建投、国泰君安、海通证券、华泰证券等
    (
        r"^\d{8}-.+(证券|建投|君安|海通|华泰|国泰|中信|招商|广发|申万|中泰|国信|兴业|光大|东方|长江|平安|民生|方正|长城|华创|太平洋|开源|东北|西南|浙商|中银|华西|国金|天风|东吴|首创|万联|德邦|财通|华安|中航|信达|华融|中金)",
        "research_report",
        None,
        False,
    ),
    # 公司研究报告格式：公司名+系列报告/研究
    (r"系列报告|系列研究|深度研究|行业研究", "research_report", None, False),
    # 公告
    (r"公告|通知|决议|提示|预案", "announcement", None, False),
]


def classify_pdf_v2(filename: str, pdf_path: str = None) -> Dict:
    """
    多策略 PDF 分类器。

    Args:
        filename: PDF 文件名（如 "东方电缆：2024年半年度报告.pdf"）
        pdf_path: PDF 文件路径（可选，用于 LLM 辅助分类）

    Returns:
        {
            "doc_type": str,          # 文档类型
            "confidence": float,      # 置信度 0.0-1.0
            "method": str,            # 分类方法: "exact_match" | "llm_assist" | "fallback"
            "period": str,            # 推断的报告期 YYYY-MM-DD
            "needs_review": bool,     # 是否需要人工确认
            "skip": bool              # 是否跳过（摘要等）
        }
    """
    # 预处理文件名
    name = filename.replace(".pdf", "").replace(".PDF", "")

    # 策略1：精确匹配（优先级最高）
    result = _exact_match(name)
    if result:
        return result

    # 策略2：年份+报告类型组合匹配（处理复杂文件名）
    result = _year_report_match(name)
    if result:
        return result

    # 策略3：LLM 辅助分类 (如果启用了且提供了文件路径)
    if pdf_path:
        llm_result = _llm_assist_classify(filename, pdf_path)
        if llm_result:
            return llm_result

    # 策略4：规则兜底（基于目录结构和关键词）
    result = _fallback_match(name, pdf_path)
    if result:
        return result

    # 默认返回 unknown
    return {
        "doc_type": "unknown",
        "confidence": 0.0,
        "method": "fallback",
        "period": None,
        "needs_review": True,
        "skip": False,
    }


def _llm_assist_classify(filename: str, pdf_path: str) -> Optional[Dict]:
    """使用 LLM 根据首页内容和文件名推断文档类型"""
    if not fitz:
        return None
    try:
        doc = fitz.open(pdf_path)
        first_page = doc[0].get_text() if len(doc) > 0 else ""
        doc.close()
    except Exception:
        return None

    if not first_page.strip():
        return None

    try:
        from llm_client import get_llm_client
        import json
        client = get_llm_client()
        prompt = f"""请根据以下PDF文件的文件名和首页内容，判断该文档的类型和报告期。

文件名: {filename}
首页内容片段:
{first_page[:800]}

文档类型可选值：
- annual_report (年报)
- semi_annual_report (半年报)
- quarterly_report (季报)
- prospectus (招股书)
- investor_relations (投资者调研纪要/交流)
- research_report (券商研报)
- announcement (其他公告)
- unknown (未知)

请只返回一个JSON对象，包含：
{{
  "doc_type": "类型",
  "period": "YYYY-MM-DD 或 null" (季报/半年报/年报对应的最后一天，如 2024年一季报填 2024-03-31)
}}
"""
        resp = client.chat(prompt, max_tokens=100)
        content = resp.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        data = json.loads(content)
        if data.get("doc_type") in DOC_TYPES:
            return {
                "doc_type": data["doc_type"],
                "confidence": 0.85,
                "method": "llm_assist",
                "period": data.get("period"),
                "needs_review": False,
                "skip": False
            }
    except Exception:
        pass
    return None


def _exact_match(name: str) -> Optional[Dict]:
    """策略1：精确正则匹配（按优先级排序）"""
    for pattern, doc_type, period_suffix, skip in EXACT_PATTERNS:
        if re.search(pattern, name):
            # 提取年份
            year = _extract_year(name)
            period = f"{year}-{period_suffix}" if year and period_suffix else None

            return {
                "doc_type": doc_type,
                "confidence": 0.99 if doc_type != "abstract" else 1.0,
                "method": "exact_match",
                "period": period,
                "needs_review": False,
                "skip": skip,
            }
    return None


def _year_report_match(name: str) -> Optional[Dict]:
    """策略2：年份+报告类型组合匹配（处理复杂文件名）"""
    # 提取年份
    year = _extract_year(name)
    if not year:
        return None

    # 检查是否包含报告类型关键词
    if "半年" in name:
        return {
            "doc_type": "semi_annual_report",
            "confidence": 0.95,
            "method": "year_report_match",
            "period": f"{year}-06-30",
            "needs_review": False,
            "skip": False,
        }

    # 季度匹配（更精确）
    quarter_match = re.search(r"第?(\d)季度|Q(\d)|(\d)季报", name, re.IGNORECASE)
    if quarter_match:
        quarter = int(
            quarter_match.group(1) or quarter_match.group(2) or quarter_match.group(3)
        )
        period_map = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
        return {
            "doc_type": "quarterly_report",
            "confidence": 0.95,
            "method": "year_report_match",
            "period": f"{year}-{period_map.get(quarter, '12-31')}",
            "needs_review": False,
            "skip": False,
        }

    # 年报匹配（最宽松）
    if "年报" in name or "年度" in name:
        return {
            "doc_type": "annual_report",
            "confidence": 0.90,
            "method": "year_report_match",
            "period": f"{year}-12-31",
            "needs_review": False,
            "skip": False,
        }

    return None


def _fallback_match(name: str, pdf_path: str = None) -> Optional[Dict]:
    """策略3：基于目录结构的兜底匹配"""
    # 如果有路径信息，根据目录结构判断
    if pdf_path:
        path_str = str(pdf_path).lower()
        if "/financial_reports/" in path_str or "\\financial_reports\\" in path_str:
            # 财务报告目录，尝试从文件名推断
            if "招股" in name:
                return {
                    "doc_type": "prospectus",
                    "confidence": 0.70,
                    "method": "fallback_path",
                    "period": None,
                    "needs_review": True,
                    "skip": False,
                }
            elif "公告" in name or "通知" in name:
                return {
                    "doc_type": "announcement",
                    "confidence": 0.70,
                    "method": "fallback_path",
                    "period": None,
                    "needs_review": True,
                    "skip": False,
                }
        elif "/prospectus/" in path_str or "\\prospectus\\" in path_str:
            return {
                "doc_type": "prospectus",
                "confidence": 0.80,
                "method": "fallback_path",
                "period": None,
                "needs_review": True,
                "skip": False,
            }
        elif "/research/" in path_str or "\\research\\" in path_str:
            # 研报目录 - 任何在research目录下的PDF默认都是研报
            research_keywords = [
                "深度",
                "首次覆盖",
                "点评",
                "研究报告",
                "证券研究",
                "行业研究",
                "公司研究",
                "研究",
                "证券",
            ]
            if any(kw in name for kw in research_keywords):
                return {
                    "doc_type": "research_report",
                    "confidence": 0.80,
                    "method": "fallback_path",
                    "period": None,
                    "needs_review": True,
                    "skip": False,
                }
            elif "投资者" in name or "调研" in name:
                return {
                    "doc_type": "investor_relations",
                    "confidence": 0.80,
                    "method": "fallback_path",
                    "period": None,
                    "needs_review": True,
                    "skip": False,
                }
            else:
                # 在research目录下但没有明确关键词，默认归类为研报
                return {
                    "doc_type": "research_report",
                    "confidence": 0.60,
                    "method": "fallback_path_default",
                    "period": None,
                    "needs_review": True,
                    "skip": False,
                }

    # 关键词兜底
    if "招股" in name:
        return {
            "doc_type": "prospectus",
            "confidence": 0.60,
            "method": "fallback_keyword",
            "period": None,
            "needs_review": True,
            "skip": False,
        }
    elif "投资者" in name or "调研" in name:
        return {
            "doc_type": "investor_relations",
            "confidence": 0.60,
            "method": "fallback_keyword",
            "period": None,
            "needs_review": True,
            "skip": False,
        }
    elif "深度" in name or "研报" in name:
        return {
            "doc_type": "research_report",
            "confidence": 0.60,
            "method": "fallback_keyword",
            "period": None,
            "needs_review": True,
            "skip": False,
        }

    return None


def _extract_year(name: str) -> Optional[int]:
    """从文件名中提取年份"""
    # 匹配 4 位数年份（2000-2099）
    year_match = re.search(r"(20\d{2})", name)
    if year_match:
        return int(year_match.group(1))
    return None


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
    replacement = text.count("\ufffd")  # Unicode 替换字符
    control = sum(1 for c in text if ord(c) < 32 and c not in "\n\t\r")

    # 有效文本比例
    effective = chinese + ascii_chars
    effective_ratio = effective / total

    # 替换字符惩罚
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


def _extract_tables_from_page(page) -> List[Dict]:
    """
    从单页提取表格，转换为 Markdown 格式。

    返回: [
        {
            "markdown": str,  # Markdown 格式的表格
            "rows": int,
            "cols": int,
            "data": list      # 原始数据
        }
    ]
    """
    tables = []

    try:
        page_tables = page.find_tables()

        for table in page_tables.tables:
            data = table.extract()
            if not data or len(data) < 2:  # 至少需要表头+1行数据
                continue

            # 转换为 Markdown
            markdown_lines = []
            for i, row in enumerate(data):
                # 清理单元格文本
                cleaned_row = []
                for cell in row:
                    if cell is None:
                        cleaned_row.append("")
                    else:
                        # 移除换行符，保留空格
                        cell_text = str(cell).replace("\n", " ").strip()
                        cleaned_row.append(cell_text)

                markdown_lines.append("| " + " | ".join(cleaned_row) + " |")

                # 第一行后添加分隔符
                if i == 0:
                    separator = "|" + "|".join(["---"] * len(row)) + "|"
                    markdown_lines.append(separator)

            tables.append(
                {
                    "markdown": "\n".join(markdown_lines),
                    "rows": table.row_count,
                    "cols": table.col_count,
                    "data": data,
                }
            )
    except Exception:
        # 表格提取失败不影响文本提取
        pass

    return tables


def _extract_page_text(page, include_tables: bool = True) -> str:
    """从单页提取文本，采用多策略回退机制。"""
    strategies = [
        ("text", lambda p: p.get_text("text")),
        ("xhtml", lambda p: p.get_text("xhtml")),
        ("html", lambda p: p.get_text("html")),
    ]

    candidates = []
    for name, fn in strategies:
        try:
            raw = fn(page)
            # 解码 HTML entities
            decoded = html.unescape(raw)
            # 移除 HTML 标签
            cleaned = re.sub(r"<[^>]+>", " ", decoded)
            # 标准化空白
            cleaned = re.sub(r"\s+", " ", cleaned).strip()

            if cleaned:
                score = _text_quality_score(cleaned)
                candidates.append((score, cleaned))
        except Exception:
            continue

    if not candidates:
        return ""

    # 选择质量最高的结果
    candidates.sort(key=lambda x: x[0], reverse=True)
    text = candidates[0][1]

    # 如果启用表格提取，将表格插入到文本中
    if include_tables:
        tables = _extract_tables_from_page(page)
        if tables:
            # 在文本末尾添加表格
            table_texts = []
            for i, table in enumerate(tables):
                table_texts.append(f"\n[TABLE {i + 1}]\n{table['markdown']}\n")
            text += "\n" + "\n".join(table_texts)

    return text


def extract_pdf_text_v3(
    pdf_path: Union[str, Path], max_pages: Optional[int] = None
) -> Dict:
    """
    增强版 PDF 提取。

    Args:
        pdf_path: PDF 文件路径
        max_pages: 最大提取页数（None=全部）

    Returns:
        {
            "text": str,              # 完整文本
            "pages_read": int,
            "total_pages": int,
            "total_chars": int,
            "quality_score": float,
            "is_scanned": bool,
            "scan_confidence": float,
            "error": str or None
        }
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        return {
            "text": "",
            "pages_read": 0,
            "total_pages": 0,
            "total_chars": 0,
            "quality_score": 0.0,
            "is_scanned": False,
            "scan_confidence": 0.0,
            "error": f"File not found: {pdf_path}",
        }

    if fitz is None:
        return {
            "text": "",
            "pages_read": 0,
            "total_pages": 0,
            "total_chars": 0,
            "quality_score": 0.0,
            "is_scanned": False,
            "scan_confidence": 0.0,
            "error": "PyMuPDF not installed. Run: pip install PyMuPDF",
        }

    try:
        with fitz.open(str(pdf_path)) as doc:
            total_pages = len(doc)
            text_parts = []
            read_pages = 0
            quality_scores = []

            end_page = min(max_pages or total_pages, total_pages)

            for page_idx in range(end_page):
                page = doc[page_idx]
                text = _extract_page_text(page)
                if text.strip():
                    text_parts.append(text)
                    read_pages += 1
                    quality_scores.append(_text_quality_score(text))

        full_text = "\n\n".join(text_parts)
        total_chars = len(full_text)

        avg_quality = (
            sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        )

        # 扫描版检测
        is_scanned, scan_confidence = _detect_scanned(
            doc if "doc" in locals() else None, read_pages, total_chars, avg_quality
        )

        return {
            "text": full_text,
            "pages_read": read_pages,
            "total_pages": total_pages,
            "total_chars": total_chars,
            "quality_score": avg_quality,
            "is_scanned": is_scanned,
            "scan_confidence": scan_confidence,
            "error": None,
        }

    except Exception as e:
        return {
            "text": "",
            "pages_read": 0,
            "total_pages": 0,
            "total_chars": 0,
            "quality_score": 0.0,
            "is_scanned": False,
            "scan_confidence": 0.0,
            "error": str(e),
        }


def _detect_scanned(
    doc, read_pages: int, total_chars: int, avg_quality: float
) -> tuple:
    """
    多指标扫描版检测。
    返回 (is_scanned: bool, confidence: float)

    检测指标：
    1. 文本密度：每页平均字符数（正常PDF > 100，扫描版 < 50）
    2. 质量评分：文本质量（正常PDF > 0.3，扫描版 < 0.01）
    3. 字符数极低：大量空白页
    4. 图像比例：扫描版通常有大量图像
    """
    # 指标1：文本密度（每页平均字符数）
    if read_pages >= 5:
        chars_per_page = total_chars / read_pages
        if chars_per_page < 50:
            return True, 0.95
        elif chars_per_page < 100:
            # 可能是扫描版，但不确定
            pass

    # 指标2：质量评分
    if read_pages >= 3 and avg_quality < 0.01:
        return True, 0.90

    # 指标3：字符数极低
    if read_pages >= 10 and total_chars < 100:
        return True, 0.99

    # 指标4：综合判断
    # 如果有文档对象，检查图像数量
    if doc is not None:
        try:
            image_count = 0
            for page_idx in range(min(read_pages, 10)):  # 只检查前10页
                page = doc[page_idx]
                image_list = page.get_images()
                image_count += len(image_list)

            # 如果平均每页有超过2个图像，可能是扫描版
            if read_pages > 0 and image_count / read_pages > 2:
                return True, 0.85
        except Exception:
            pass

    return False, 0.0


def validate_extraction(extract_result: Dict, doc_type: str) -> Dict:
    """
    检查点1：提取质量验证。

    Args:
        extract_result: extract_pdf_text_v3 的输出
        doc_type: 文档类型（如 "annual_report"）

    Returns:
        {
            "status": "passed|failed|needs_review",
            "checks": {
                "length": {"expected": int, "actual": int, "passed": bool},
                "quality_score": {"score": float, "threshold": float, "passed": bool},
                "is_scanned": {"is_scanned": bool, "passed": bool},
            },
            "failed_checks": list,
            "review_reason": str
        }
    """
    checks = {}
    failed_checks = []

    # 获取文档类型的阈值
    type_config = DOC_TYPES.get(doc_type, DOC_TYPES["unknown"])
    min_chars = type_config["min_chars"]
    quality_threshold = 0.30  # 默认阈值

    # 检查1：文本长度
    actual_chars = extract_result.get("total_chars", 0)
    length_passed = actual_chars >= min_chars
    checks["length"] = {
        "expected": min_chars,
        "actual": actual_chars,
        "passed": length_passed,
    }
    if not length_passed:
        failed_checks.append("length")

    # 检查2：质量评分
    quality_score = extract_result.get("quality_score", 0.0)
    quality_passed = quality_score >= quality_threshold
    checks["quality_score"] = {
        "score": quality_score,
        "threshold": quality_threshold,
        "passed": quality_passed,
    }
    if not quality_passed:
        failed_checks.append("quality_score")

    # 检查3：扫描版检测
    is_scanned = extract_result.get("is_scanned", False)
    scan_passed = not is_scanned
    checks["is_scanned"] = {
        "is_scanned": is_scanned,
        "passed": scan_passed,
    }
    if not scan_passed:
        failed_checks.append("is_scanned")

    # 检查4：错误检查
    has_error = extract_result.get("error") is not None
    checks["no_error"] = {"passed": not has_error}
    if has_error:
        failed_checks.append("error")

    # 确定状态
    if not failed_checks:
        status = "passed"
        review_reason = ""
    elif "is_scanned" in failed_checks:
        status = "needs_review"
        review_reason = "扫描版PDF，需要OCR处理"
    elif "length" in failed_checks:
        status = "needs_review"
        review_reason = f"文本长度不足（{actual_chars} < {min_chars}）"
    else:
        status = "failed"
        review_reason = f"检查失败: {', '.join(failed_checks)}"

    return {
        "status": status,
        "checks": checks,
        "failed_checks": failed_checks,
        "review_reason": review_reason,
    }


# ── CLI 测试 ──────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_extract_v3.py <pdf_path_or_filename>")
        sys.exit(1)

    target = sys.argv[1]

    # 如果是文件名（不含路径），只测试分类
    if "/" not in target and "\\" not in target:
        result = classify_pdf_v2(target)
        print(f"Classification: {result}")
    else:
        # 完整路径，测试提取和验证
        result = extract_pdf_text_v3(target)
        if result["error"]:
            print(f"ERROR: {result['error']}")
        else:
            print(f"Pages: {result['total_pages']}")
            print(f"Chars: {result['total_chars']}")
            print(f"Quality: {result['quality_score']:.2f}")
            print(f"Scanned: {result['is_scanned']}")

            # 验证
            doc_type = classify_pdf_v2(Path(target).name)["doc_type"]
            validation = validate_extraction(result, doc_type)
            print(f"\nValidation: {validation['status']}")
            if validation["review_reason"]:
                print(f"Reason: {validation['review_reason']}")
