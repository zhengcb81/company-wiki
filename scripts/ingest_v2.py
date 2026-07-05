#!/usr/bin/env python3
"""
ingest_v2.py — LLM 驱动的 Ingest 主流程（v2）

核心设计变更：
- 删除 extract.py 的规则打分取top3逻辑
- 新增：调用 prompts.py 构建 LLM prompt
- 新增：调用 llm_client 进行 LLM 内容理解
- 新增：解析 LLM JSON 输出，批量写入 wiki
- 保留：文件扫描、来源判断、wiki写入（机械操作）

用法：
    python3 scripts/ingest_v2.py                       # 处理所有待ingest文件
    python3 scripts/ingest_v2.py --company 中微公司      # 只处理指定公司
    python3 scripts/ingest_v2.py --check                 # 列出待处理文件
    python3 scripts/ingest_v2.py --limit 3               # 最多处理3个（调试用）
    python3 scripts/ingest_v2.py --dry-run               # 只打印不写入
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 公共基础设施（路径、环境、配置）
from common import WIKI_ROOT

from pdf_extract_v2 import extract_pdf_text, classify_pdf
from extract_v2 import (
    clean_text,
    extract_frontmatter,
    classify_source,
)
from prompts import (
    build_analysis_prompt,
    build_financial_report_prompt,
    build_ir_prompt,
    build_announcement_prompt,
    build_prospectus_prompt,
)
from llm_client import LLMClient, get_llm_client
from graph import Graph
from log_writer import append_log


def _atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """原子写入文件：写临时文件然后 rename，防止崩溃导致数据丢失"""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_text(content, encoding=encoding)
        os.replace(str(tmp_path), str(path))
    except Exception as e:
        # 如果原子写入失败，回退到直接写入（好过丢数据）
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        try:
            path.write_text(content, encoding=encoding)
        except Exception as e2:
            print(f"[ERROR] 文件写入完全失败 {path}: {e2}")
            raise


# ── 标记管理 ──────────────────────────────
from ingested_db import get_db


def get_ingested_set():
    return get_db().get_ingested_set()


def mark_ingested(file_path):
    get_db().mark_ingested(str(file_path))


def is_ingested(file_path, ingested_set):
    return get_db().is_ingested(str(file_path), ingested_set)


def _pdf_metadata_date(file_path: str) -> Optional[str]:
    """从 PDF 元数据读取创建/修改日期，格式 D:YYYYMMDDHHMMSS+TZ'ZZ'。"""
    if not file_path.lower().endswith(".pdf"):
        return None
    try:
        import fitz
    except ImportError:
        return None
    try:
        doc = fitz.open(file_path)
    except Exception:
        return None
    md = doc.metadata or {}
    for k in ("creationDate", "modDate"):
        s = md.get(k, "") or ""
        if s.startswith("D:"):
            digits = re.sub(r"\D", "", s[2:])
            if len(digits) >= 8:
                y, mo, d = digits[:4], digits[4:6], digits[6:8]
                if 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
                    return f"{y}-{mo}-{d}"
    return None


# ── 扫描待处理文件 ─────────────────────────
def scan_pending_files(graph, company_name=None):
    ingested = get_ingested_set()
    pending = []

    companies = graph.get_all_companies()
    if company_name:
        companies = [c for c in companies if c["name"] == company_name]

    # 公司扫描时跳过明显属于行业层面的文件（防污染）
    _sector_file_patterns = ["行业分析", "行业研究", "行业报告"]

    # 跳过的中间处理目录（非原始数据源）
    _skip_dir_patterns = [
        "/wiki/",
        "\\wiki\\",
        "/extracts/",
        "\\extracts\\",
        "/segments/",
        "\\segments\\",
    ]

    for company in companies:
        name = company["name"]
        company_dir = WIKI_ROOT / "companies" / name
        if not company_dir.exists():
            continue
        for f in sorted(company_dir.rglob("*")):
            if not f.is_file() or is_ingested(f, ingested):
                continue
            fp_str = str(f)
            if any(p in fp_str for p in _skip_dir_patterns):
                continue
            # 跳过行业层面的文件（可能在旧操作中误放入公司目录）
            if any(p in f.name for p in _sector_file_patterns):
                continue
            pending.append((str(f), name, "company"))

    # 仅在未指定公司过滤时扫描行业目录
    if not company_name:
        for sector_name in graph.get_all_sectors():
            sector_dir = WIKI_ROOT / "sectors" / sector_name
            if not sector_dir.exists():
                continue
            for f in sorted(sector_dir.rglob("*")):
                if f.is_file() and not is_ingested(f, ingested):
                    if "/wiki/" in str(f) or "\\wiki\\" in str(f):
                        continue
                    pending.append((str(f), sector_name, "sector"))

    return pending


# ── 读取文件内容 ──────────────────────────
def read_file_content(file_path: str) -> Tuple[Optional[str], Optional[Dict], str]:
    """
    读取文件内容，返回 (正文, frontmatter, 来源类型)
    """
    path = Path(file_path)
    filename = path.name

    # PDF 文件
    if filename.lower().endswith(".pdf"):
        result = extract_pdf_text(str(file_path))
        if result["error"]:
            return None, None, "unknown"
        if result["is_scanned"]:
            return None, None, "scanned"
        text = result["text"]
        pdf_type = classify_pdf(filename)
        return text, {"type": pdf_type, "pages": result["pages_read"]}, pdf_type

    # Markdown 文件
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None, None, "unknown"

    front, body = extract_frontmatter(content)
    source_type = classify_source(filename, content[:500])
    return body, front, source_type


# ── 获取核心问题 ──────────────────────────
def extract_report_date(file_path: str, source_type: str) -> Optional[str]:
    """
    从文件名提取实际报告日期，避免所有 PDF 都被标记为处理当天。

    支持的文件名模式：
      - 2023年年度报告.pdf → 2023-12-31
      - 2024-04-26_投资者关系活动记录表.pdf → 2024-04-26
      - 2023semi_annual.pdf → 2023-06-30
      - 2024_Q1_report.pdf → 2024-03-31
    """
    import re
    from pathlib import Path

    name = Path(file_path).stem

    # 尝试从文件名提取年份和季度/月份
    year_match = re.search(r"(20\d{2})", name)
    if not year_match:
        return None

    year = int(year_match.group(1))

    # Q1 根因修复完善：文件名是日期事实层，不依赖容易错分类的 source_type
    # （preexisting bug：classify_source 把"半年度报告.pdf"归为 annual_report，
    #   导致 extract_report_date 走年报分支返回 12-31。先按文件名关键字判定。）
    name_lower = name.lower()
    if (
        any(k in name for k in ["半年度", "半年报", "半年"])
        or "semi_annual" in name_lower
    ):
        return f"{year}-06-30"
    if any(k in name for k in ["一季", "第一季度", "1季", "Q1"]) or "q1" in name_lower:
        return f"{year}-03-31"
    if any(k in name for k in ["三季", "第三季度", "3季", "Q3"]) or "q3" in name_lower:
        return f"{year}-09-30"
    if any(k in name for k in ["二季", "第二季度", "2季", "Q2"]) or "q2" in name_lower:
        return f"{year}-06-30"
    if any(k in name for k in ["四季", "第四季度", "4季", "Q4"]) or "q4" in name_lower:
        return f"{year}-12-31"
    if any(k in name for k in ["年报", "年度报告", "年度"]) or "annual" in name_lower:
        return f"{year}-12-31"

    # Q1 修复扩展：非财报类（券商研报/公告/新闻等）从文件名提取真实发布日期，
    # 避免走 datetime.now() 兜底成今天的日期。
    # 券商研报常见格式：20190227-东北证券-北方华创-002371-... (YYYYMMDD 包含 8 位连续数字)
    # 也支持 YYYY-MM-DD / YYYY_MM_DD 等分隔日期
    date_match = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", name)
    if date_match:
        y, m, d = date_match.group(1), date_match.group(2), date_match.group(3)
        if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
            return f"{y}-{m}-{d}"

    # Fallback：source_type 不可靠时的回退逻辑
    if source_type in ["annual_report", "年报"]:
        return f"{year}-12-31"
    elif source_type in ["semi_annual_report", "半年报"]:
        return f"{year}-06-30"
    elif source_type in ["investor_relations", "ir", "投资者关系"]:
        # IR 活动记录表尝试从文件名提取具体日期
        # 支持格式：2022-04-16, 2022_0416, 20220416
        date_match = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", name)
        if date_match:
            y, m, d = date_match.group(1), date_match.group(2), date_match.group(3)
            # 验证是合理的日期（月 01-12，日 01-31）
            if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
                return f"{y}-{m}-{d}"
        # 只有年份时，默认年中
        return f"{year}-06-30"
    elif source_type == "prospectus":
        # 招股书用年份+年初
        return f"{year}-01-01"

    return None


def get_core_questions(graph, entity_name: str, entity_type: str) -> List[str]:
    """从 graph.yaml 获取实体的核心问题"""
    questions = []
    if entity_type == "company":
        company = graph.get_company(entity_name)
        if company:
            questions = company.get("questions", [])
    elif entity_type == "sector":
        sector = graph.get_sector(entity_name)
        if sector:
            questions = sector.get("questions", [])
    return questions if questions else ["公司/行业最新动态如何？"]


# ── 获取现有评估 ──────────────────────────
def get_existing_assessment(wiki_path: Path) -> str:
    """读取 wiki 页面的现有综合评估"""
    if not wiki_path.exists():
        return ""
    try:
        text = wiki_path.read_text(encoding="utf-8")
        # 找到综合评估部分
        match = re.search(r"## 综合评估\n+>\s*(.+?)(?=\n## |\Z)", text, re.DOTALL)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return ""


# ── 获取 wiki 路径 ─────────────────────────
def get_wiki_path(
    entity_name: str, entity_type: str, topic_name: str
) -> Optional[Path]:
    if entity_type == "company":
        return WIKI_ROOT / "companies" / entity_name / "wiki" / f"{topic_name}.md"
    elif entity_type == "sector":
        return WIKI_ROOT / "sectors" / entity_name / "wiki" / f"{topic_name}.md"
    elif entity_type == "theme":
        return WIKI_ROOT / "themes" / entity_name / "wiki" / f"{topic_name}.md"
    return None


# ── 创建 wiki 模板 ─────────────────────────
def create_wiki_template(
    wiki_path: Path, entity_name: str, topic_name: str, entity_type: str
):
    wiki_path.parent.mkdir(parents=True, exist_ok=True)
    template = f"""---
title: "{topic_name}"
description: ""
entity: "{entity_name}"
type: {entity_type}_topic
last_updated: "{datetime.now().strftime("%Y-%m-%d")}"
sources_count: 0
tags: []
---

# {entity_name} — {topic_name}

## 核心问题
- （待设定）

## 时间线

（暂无条目）

## 综合评估
> 待积累数据后补充。
"""
    _atomic_write(wiki_path, template)


# ── 添加时间线条目 ─────────────────────────
def add_timeline_entries(
    wiki_path: Path, entries: List[Dict], source_file: str = ""
) -> int:
    """向 wiki 文档批量添加时间线条目"""
    if not wiki_path.exists():
        return 0

    wiki_text = wiki_path.read_text(encoding="utf-8")
    added = 0

    # 构建来源链接（相对 wiki 文件位置，对齐 AGENTS.md 规范 ../raw/{path}）
    # wiki 文件在 companies/{name}/wiki/{topic}.md，源在 companies/{name}/raw/{...}
    # 所以从 wiki 文件回退一级到 companies/{name}/，再进 raw/ → ../raw/{tail}
    source_link = ""
    if source_file:
        norm = source_file.replace("\\", "/")
        m = re.search(r"companies/[^/]+/raw/(.+)$", norm)
        if m:
            source_link = f"\n- [来源](../raw/{m.group(1)})"
        else:
            try:
                rel_path = Path(source_file).relative_to(WIKI_ROOT)
                source_link = f"\n- [来源](../{rel_path.as_posix()})"
            except ValueError:
                pass

    for entry in entries:
        date = entry.get("date", datetime.now().strftime("%Y-%m-%d"))
        title = entry.get("title", "未命名")
        key_points = entry.get("key_points") or entry.get("points") or []
        source_type = entry.get("source_type", "新闻")

        # 构建条目文本
        points_text = "\n".join(f"- {p}" for p in key_points)
        entry_text = f"""
### {date} | {source_type} | {title}
{points_text}{source_link}

"""

        # 去重检查
        title_clean = re.sub(r"\[\[([^]]+)\]\]", r"\1", title)
        dedup_pattern = re.compile(
            rf"^###\s+{re.escape(date)}\s*\|[^|]+\|\s*{re.escape(title_clean)}\s*$",
            re.MULTILINE,
        )
        if dedup_pattern.search(wiki_text):
            continue

        # 插入到时间线部分
        timeline_pos = wiki_text.find("## 时间线")
        if timeline_pos < 0:
            continue

        after_timeline = wiki_text[timeline_pos:]
        first_entry = after_timeline.find("\n### ", 1)

        if first_entry < 0:
            insert_pos = timeline_pos + len("## 时间线")
            wiki_text = wiki_text[:insert_pos] + entry_text + wiki_text[insert_pos:]
        else:
            abs_first_entry = timeline_pos + first_entry
            wiki_text = (
                wiki_text[:abs_first_entry] + entry_text + wiki_text[abs_first_entry:]
            )

        added += 1

    if added > 0:
        # 更新 frontmatter
        wiki_text = re.sub(
            r'last_updated: "?\d{4}-\d{2}-\d{2}"?',
            f'last_updated: "{datetime.now().strftime("%Y-%m-%d")}"',
            wiki_text,
        )
        count_match = re.search(r"sources_count: (\d+)", wiki_text)
        if count_match:
            old_count = int(count_match.group(1))
            wiki_text = re.sub(
                r"sources_count: \d+",
                f"sources_count: {old_count + added}",
                wiki_text,
                count=1,
            )
        wiki_text = wiki_text.replace("（暂无条目）\n", "")
        _atomic_write(wiki_path, wiki_text)

    return added


# ── 提取上一期财务数据 ──────────────────────
def extract_previous_period_data(
    wiki_path: Path, current_period: str
) -> Optional[Dict]:
    """
    从 wiki 时间线中提取最近一期的财务数据，用于季度对比。
    返回 {period, summary} 或 None。
    """
    if not wiki_path.exists():
        return None

    wiki_text = wiki_path.read_text(encoding="utf-8")
    lines = wiki_text.splitlines()

    # 寻找包含财务关键词的时间线条目
    financial_keywords = [
        "营收",
        "净利润",
        "扣非",
        "毛利率",
        "研发投入",
        "现金流",
        "同比",
        "环比",
    ]
    entries = []
    current_entry = []
    in_entry = False

    for line in lines:
        if line.strip().startswith("### 20"):
            if current_entry:
                entries.append("\n".join(current_entry))
            current_entry = [line]
            in_entry = True
        elif in_entry:
            if line.strip().startswith("## ") and not line.strip().startswith("### "):
                in_entry = False
                if current_entry:
                    entries.append("\n".join(current_entry))
                    current_entry = []
            else:
                current_entry.append(line)

    if current_entry:
        entries.append("\n".join(current_entry))

    # 从后向前找包含财务数据的条目
    for entry_text in reversed(entries):
        if any(kw in entry_text for kw in financial_keywords):
            # 提取要点（- 开头的行）
            points = [
                l.strip()[2:]
                for l in entry_text.splitlines()
                if l.strip().startswith("- ")
            ]
            if points:
                # 尝试提取日期作为 period
                date_match = re.search(r"###\s+(\d{4}-\d{2}-\d{2})", entry_text)
                period = date_match.group(1) if date_match else "上期"
                return {
                    "period": period,
                    "summary": "\n".join(points[:8]),  # 最多取8个要点
                }

    return None


# ── 更新综合评估 ──────────────────────────
def update_assessment(wiki_path: Path, assessment: str) -> bool:
    """更新 wiki 页面的综合评估"""
    if not wiki_path.exists() or not assessment:
        return False

    # 确保评估文本以 > 开头（引用块格式）
    assessment = assessment.strip()
    if not assessment.startswith(">"):
        # 将多行文本转换为引用块格式
        lines = assessment.split("\n")
        assessment = "\n".join(f"> {line}" if line.strip() else ">" for line in lines)

    wiki_text = wiki_path.read_text(encoding="utf-8")

    # 替换现有评估（匹配 ## 综合评估 后面的内容直到下一个 ## 标题）
    old_pattern = r"(## 综合评估\n+)([\s\S]*?)(?=\n## |\Z)"
    match = re.search(old_pattern, wiki_text)
    if match:
        # 替换现有评估内容
        old_content = match.group(2)
        wiki_text = wiki_text.replace(
            f"## 综合评估\n{old_content}", f"## 综合评估\n{assessment}\n"
        )
    else:
        # 在时间线之后添加
        timeline_pos = wiki_text.find("## 时间线")
        if timeline_pos >= 0:
            # 在时间线之后找下一个 ## 标题
            after_timeline = wiki_text[timeline_pos + len("## 时间线") :]
            next_section = after_timeline.find("\n## ")
            if next_section >= 0:
                insert_pos = timeline_pos + len("## 时间线") + next_section
                wiki_text = (
                    wiki_text[:insert_pos]
                    + "\n\n## 综合评估\n"
                    + assessment
                    + "\n"
                    + wiki_text[insert_pos:]
                )
            else:
                wiki_text = wiki_text.rstrip() + f"\n\n## 综合评估\n{assessment}\n"

    _atomic_write(wiki_path, wiki_text)
    return True


# ── 写入矛盾警告 ──────────────────────────
def write_contradictions(wiki_path: Path, contradictions: List[Dict]):
    """在 wiki 页面中写入矛盾警告。只保留真正的事实矛盾，最多3条。"""
    if not contradictions:
        return

    if not wiki_path.exists():
        return

    # 过滤：跳过明显的"内容不同"误报，只保留事实性矛盾
    filtered = []
    skip_keywords = [
        "内容完全不同",
        "文件类型不同",
        "性质完全不同",
        "不存在事实矛盾",
        "并非矛盾",
        "并不直接矛盾",
        "没有直接信息冲突",
        "不同事件",
        "描述完全不符",
        "描述完全错误",
        "描述不准确",
        "严重低估",
    ]
    for c in contradictions:
        # 处理 LLM 返回字符串而非字典的情况
        if isinstance(c, str):
            expl = c
        elif isinstance(c, dict):
            expl = c.get("explanation", "")
        else:
            continue
        if any(kw in expl for kw in skip_keywords):
            continue
        # 只保留有具体数据/事实冲突的
        if isinstance(c, dict) and (
            c.get("field") or c.get("old_value") or c.get("new_value")
        ):
            filtered.append(c)
        elif any(ch.isdigit() for ch in expl):
            filtered.append(c)

    if not filtered:
        return

    wiki_text = wiki_path.read_text(encoding="utf-8")

    # 清理旧警告（防止堆积）
    import re

    wiki_text = re.sub(r"> ⚠️ \*\*矛盾警告\*\*\n(?:> .+\n)*\n?", "", wiki_text)

    # 只保留最新的 3 条
    filtered = filtered[-3:]
    warning_lines = ["> [!warning] **矛盾警告**"]
    for c in filtered:
        if isinstance(c, str):
            warning_lines.append(f"> - {c}")
        elif isinstance(c, dict):
            warning_lines.append(f"> - {c.get('explanation', '发现矛盾')}")

    warning_text = "\n".join(warning_lines) + "\n\n"

    # 插入到综合评估之前
    assessment_pos = wiki_text.find("## 综合评估")
    if assessment_pos > 0:
        wiki_text = (
            wiki_text[:assessment_pos] + warning_text + wiki_text[assessment_pos:]
        )
    else:
        # 回退：插入到标题之后
        title_end = wiki_text.find("\n## ")
        if title_end > 0:
            wiki_text = (
                wiki_text[:title_end] + "\n" + warning_text + wiki_text[title_end:]
            )

    _atomic_write(wiki_path, wiki_text)


def is_assessment_stale(wiki_path: Path, max_age_days: int = 30) -> bool:
    """
    检查综合评估是否过期。

    判断标准：
    1. 评估中标注了"需要更新"
    2. 评估日期超过 max_age_days 天
    3. 评估中引用的数据年份过旧（如 2023 年）
    """
    if not wiki_path.exists():
        return False

    content = wiki_path.read_text(encoding="utf-8")

    # 检查是否有"需要更新"标记
    if "需要更新综合评估" in content:
        return True

    # 提取评估部分
    assessment_match = re.search(r"## 综合评估\n+([\s\S]*?)(?=\n## |\Z)", content)
    if not assessment_match:
        return True  # 没有评估，需要生成

    assessment = assessment_match.group(1)

    # 检查评估中提到的年份
    year_pattern = re.compile(r"20(\d{2})年")
    years = year_pattern.findall(assessment)
    if years:
        max_year = max(int(y) for y in years)
        current_year = datetime.now().year % 100  # 取后两位
        if max_year < current_year - 1:  # 如果最新年份比去年还早
            return True

    # 检查"截至"日期
    date_pattern = re.compile(r"截至\s*(\d{4})[年/]")
    dates = date_pattern.findall(assessment)
    if dates:
        max_date_year = max(int(y) for y in dates)
        if max_date_year < datetime.now().year - 1:
            return True

    return False


# ── 条目质量检查 ────────────────────────────
def validate_entries(entries: List[Dict]) -> Tuple[List[Dict], List[str]]:
    """
    验证时间线条目质量，返回 (有效条目, 警告列表)。

    检查项：
    - 条目是否包含 HTML 残留
    - 条目是否过长（单条目 > 200 字）
    - 条目是否为空或过短
    - 条目是否包含 DISCLAIMER 或无关内容
    """
    valid_entries = []
    warnings = []

    # HTML 残留检测
    html_pattern = re.compile(r"<[^>]+>|&[a-z]+;|&#\d+;")
    # 不相关内容检测
    garbage_patterns = [
        "DISCLAIMER",
        "AASTOCKS",
        "YouTube",
        "Reddit",
        "stock prices",
        "authored by",
        "click here",
        "subscribe",
        "follow us",
    ]

    for entry in entries:
        title = entry.get("title", "")
        points = entry.get("points") or entry.get("key_points") or []

        # 跳过空条目
        if not title or not points:
            continue

        # 统一字段名
        entry["points"] = points

        # 检查标题
        if html_pattern.search(title):
            warnings.append(f"HTML残留: {title[:30]}")
            continue

        # 检查是否包含垃圾内容
        full_text = title + " ".join(points)
        if any(garbage.lower() in full_text.lower() for garbage in garbage_patterns):
            warnings.append(f"垃圾内容: {title[:30]}")
            continue

        # 检查条目长度
        total_len = sum(len(p) for p in points)
        if total_len > 200:
            # 截断过长的条目
            new_points = []
            current_len = 0
            for p in points:
                if current_len + len(p) > 180:
                    if current_len == 0:
                        new_points.append(p[:180] + "...")
                    break
                new_points.append(p)
                current_len += len(p)
            entry["points"] = new_points
            warnings.append(f"条目过长已截断: {title[:30]}")

        # 检查要点是否过短
        if all(len(p) < 10 for p in entry["points"]):
            warnings.append(f"要点过短: {title[:30]}")
            continue

        valid_entries.append(entry)

    return valid_entries, warnings


# ── 实体元数据缓存 ────────────────────────
_COMPANY_META: Optional[Dict[str, Dict]] = None


def _load_company_meta() -> Dict[str, Dict]:
    """加载 companies.yaml 中的元数据（别名、负向关键词等）"""
    global _COMPANY_META
    if _COMPANY_META is not None:
        return _COMPANY_META

    meta = {}
    companies_yaml = WIKI_ROOT / "companies.yaml"
    if companies_yaml.exists():
        import yaml

        with open(companies_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for name, info in data.get("companies", {}).items():
            meta[name] = {
                "aliases": [
                    a.lower() for a in info.get("aliases", []) if isinstance(a, str)
                ],
                "negative_keywords": [
                    k.lower()
                    for k in info.get("negative_keywords", [])
                    if isinstance(k, str)
                ],
            }
    _COMPANY_META = meta
    return meta


# ── 相关性检查 ────────────────────────────
def check_relevance(text: str, entity_name: str, entity_type: str) -> int:
    """
    检查文本与目标实体的相关性，返回 0-10 分。
    低于 3 分的内容不应写入 wiki。

    评分规则：
    - 实体名出现：+3 分
    - 实体名出现多次（>3次）：+2 分
    - 行业/主题关键词：+2 分
    - 不相关关键词（负分）：-3 分
    - 负向关键词（防止子串误匹配）：-5 分
    - 文本质量（长度、结构）：+1-2 分
    """
    score = 0
    text_lower = text.lower()
    entity_lower = entity_name.lower()

    # 1. 实体名出现
    entity_count = text_lower.count(entity_lower)
    if entity_count > 0:
        score += 3
        if entity_count > 3:
            score += 2

    # 1.5 负向关键词检查（防止子串误匹配，如 "京东" 匹配到 "京东方"）
    meta = _load_company_meta()
    entity_meta = meta.get(entity_name, {})
    for neg_kw in entity_meta.get("negative_keywords", []):
        if neg_kw in text_lower:
            score -= 5  # 强惩罚，直接判为不相关
            break

    # 2. 行业/主题关键词
    if entity_type == "sector":
        # 行业关键词
        sector_keywords = {
            "半导体设备": [
                "刻蚀",
                "薄膜沉积",
                "清洗设备",
                "光刻",
                "离子注入",
                "CMP",
                "量检测",
                "国产化率",
            ],
            "光模块": ["800G", "1.6T", "CPO", "光模块", "EML", "硅光"],
            "GPU与AI芯片": ["GPU", "AI芯片", "CUDA", "算力", "训练", "推理"],
            "储能": ["储能", "电池", "锂电", "钠电", "液流电池"],
        }
        keywords = sector_keywords.get(entity_name, [])
        for kw in keywords:
            if kw in text:
                score += 2
                break

    elif entity_type == "theme":
        # 主题关键词
        theme_keywords = {
            "半导体国产替代": [
                "国产替代",
                "国产化率",
                "自主可控",
                "进口替代",
                "供应链",
            ],
            "AI产业链": ["AI", "人工智能", "大模型", "算力", "芯片"],
            "高端制造": ["高端制造", "智能制造", "工业4.0", "自动化"],
        }
        keywords = theme_keywords.get(entity_name, [])
        for kw in keywords:
            if kw in text:
                score += 2
                break

    # 3. 不相关关键词（负分）
    irrelevant_keywords = {
        "半导体设备": ["机器人", "工业软件", "CAD", "CAE", "MES", "建筑IT"],
        "光模块": ["房地产", "保险", "银行"],
        "GPU与AI芯片": ["房地产", "保险", "银行"],
    }
    irrelevant = irrelevant_keywords.get(entity_name, [])
    for kw in irrelevant:
        if kw in text:
            score -= 3
            break

    # 4. 文本质量
    if len(text) > 1000:
        score += 1
    if len(text) > 3000:
        score += 1

    # 限制在 0-10 范围
    return max(0, min(10, score))


# ── 主处理逻辑 ────────────────────────────
def process_file(
    file_path: str,
    entity_name: str,
    entity_type: str,
    graph: Graph,
    llm_client: LLMClient,
    dry_run: bool = False,
) -> Dict:
    """
    使用 LLM 处理单个文件。
    返回处理结果摘要。
    """
    result = {
        "file": file_path,
        "status": "pending",
        "entries_added": 0,
        "assessment_updated": False,
        "contradictions_found": 0,
        "error": None,
    }

    # 1. 读取内容
    text, front, source_type = read_file_content(file_path)
    if text is None:
        result["status"] = "skip"
        result["error"] = "无法读取内容或扫描版PDF"
        return result

    # 2. 清洗文本
    cleaned = clean_text(text)
    if len(cleaned) < 100:
        result["status"] = "skip"
        result["error"] = "内容过短"
        return result

    # 2.3 相关性检查（防止内容污染）
    relevance_score = check_relevance(cleaned, entity_name, entity_type)
    if relevance_score < 3:
        result["status"] = "skip"
        result["error"] = f"相关性过低 (score={relevance_score}/10)"
        return result

    # 2.5 跳过摘要文件（与完整报告重复）
    filename_lower = Path(file_path).name.lower()
    if "摘要" in filename_lower and source_type in [
        "annual_report",
        "semi_annual_report",
        "quarterly_report",
    ]:
        result["status"] = "skip"
        result["error"] = "摘要文件跳过（完整报告已覆盖）"
        return result

    # 3. 获取上下文信息
    core_questions = get_core_questions(graph, entity_name, entity_type)
    topic_name = "公司动态" if entity_type == "company" else entity_name
    wiki_path = get_wiki_path(entity_name, entity_type, topic_name)

    # 4. 确定使用哪个 prompt
    published_date = front.get("published_date", "") if front else ""
    if not published_date:
        # 尝试从文件名提取实际报告日期，避免所有 PDF 都被标记为处理当天
        published_date = extract_report_date(file_path, source_type)
    if not published_date:
        # Q1 修复再扩展：文件名无日期 pattern 时，从 PDF/MD 顶部前 800 字符扫日期
        # （如研报 PDF 文件名"非公开发行股票预案.PDF"无日期，但内容开头通常含
        #   "二〇一九年一月四日董事会审议通过..."）
        head = cleaned[:800] if cleaned else ""
        m = re.search(r"(20\d{2})[年\-/_](\d{1,2})[月\-/_](\d{1,2})", head)
        if m:
            y = m.group(1)
            mo = f"{int(m.group(2)):02d}"
            d = f"{int(m.group(3)):02d}"
            if 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
                published_date = f"{y}-{mo}-{d}"
    if not published_date:
        # Q1 修复终兜底：内容 head 也无日期时（PDF 是 GBK 编码、cleaned 是 latin-1 mangled），
        # 回看 PDF metadata 创建日期（fitz 读出的 D:YYYYMMDDHHMMSS+TZ'ZZ'）
        pdf_md_date = _pdf_metadata_date(file_path)
        if pdf_md_date:
            published_date = pdf_md_date
    if not published_date:
        published_date = datetime.now().strftime("%Y-%m-%d")

    if source_type in ["annual_report", "semi_annual_report", "quarterly_report"]:
        # 财报专用 prompt — 尝试传入上期数据用于季度对比
        report_type = {
            "annual_report": "年度报告",
            "semi_annual_report": "半年度报告",
            "quarterly_report": "季度报告",
        }.get(source_type, "财务报告")
        prev_data = None
        if source_type == "quarterly_report" and wiki_path and wiki_path.exists():
            prev_data = extract_previous_period_data(wiki_path, Path(file_path).stem)
        prompt = build_financial_report_prompt(
            content=cleaned,
            entity_name=entity_name,
            report_type=report_type,
            period=Path(file_path).stem,
            core_questions=core_questions,
            previous_period_data=prev_data,
        )
    elif source_type == "investor_relations":
        # IR 专用 prompt
        prompt = build_ir_prompt(
            content=cleaned,
            entity_name=entity_name,
            event_date=published_date,
            core_questions=core_questions,
        )
    elif source_type == "announcement":
        # 公告专用 prompt
        announcement_type = "重大公告"
        filename = Path(file_path).name
        if any(k in filename for k in ["并购", "收购"]):
            announcement_type = "并购/收购公告"
        elif any(k in filename for k in ["定增", "增发"]):
            announcement_type = "定增/增发公告"
        elif any(k in filename for k in ["股权激励"]):
            announcement_type = "股权激励公告"
        elif any(k in filename for k in ["重大合同"]):
            announcement_type = "重大合同公告"
        elif any(k in filename for k in ["业绩预告"]):
            announcement_type = "业绩预告公告"
        prompt = build_announcement_prompt(
            content=cleaned,
            entity_name=entity_name,
            announcement_type=announcement_type,
            published_date=published_date,
            core_questions=core_questions,
        )
    elif source_type == "prospectus":
        # 招股书专用 prompt
        prompt = build_prospectus_prompt(
            content=cleaned,
            entity_name=entity_name,
            published_date=published_date,
            core_questions=core_questions,
        )
    else:
        # 通用 prompt
        prompt = build_analysis_prompt(
            content=cleaned,
            entity_name=entity_name,
            source_type=source_type,
            published_date=published_date,
            core_questions=core_questions,
        )

    # 5. 调用 LLM
    if dry_run:
        result["status"] = "dry_run"
        return result

    try:
        # 判断是否使用整篇文档分析（利用 1M 上下文）
        # 条件：文档超过 30000 字符 且 是大型文档类型
        use_full_doc = len(cleaned) > 30000 and source_type in (
            "annual_report",
            "semi_annual_report",
            "quarterly_report",
            "prospectus",
        )

        if use_full_doc:
            # B1: 整篇文档直接分析（不分段）
            prev_data = None
            if source_type == "quarterly_report" and wiki_path and wiki_path.exists():
                prev_data = extract_previous_period_data(
                    wiki_path, Path(file_path).stem
                )

            doc_type_map = {
                "annual_report": "annual_report",
                "semi_annual_report": "半年度报告",
                "quarterly_report": "quarterly_report",
                "prospectus": "prospectus",
            }
            doc_type = doc_type_map.get(source_type, source_type)

            parsed = llm_client.analyze_full_document(
                content=cleaned,
                entity_name=entity_name,
                doc_type=doc_type,
                previous_period_data=json.dumps(prev_data, ensure_ascii=False)
                if prev_data
                else "",
                published_date=published_date,
            )
            llm_response = None  # 不需要单独的 LLM 响应对象
        else:
            # 原有方式：prompt-based + chat_with_retry
            llm_response = llm_client.chat_with_retry(
                prompt,
                "你是一个专业的上市公司研究分析助手。请严格按照要求的JSON格式输出。",
            )
            if not llm_response.success:
                result["status"] = "llm_error"
                result["error"] = llm_response.error
                return result

            # 6. 解析 JSON
            parsed = llm_client._parse_json_response(llm_response.content)

        if not parsed:
            result["status"] = "parse_error"
            result["error"] = "无法解析 LLM 输出为 JSON"
            return result

        # 7. 写入 wiki
        if wiki_path and not wiki_path.exists():
            create_wiki_template(wiki_path, entity_name, topic_name, entity_type)

        # 写入时间线条目（含质量检查）
        entries = parsed.get("timeline_entries", [])
        # Q1 根因修复第二层保险：对所有 source_type 强制覆盖 entry.date 为 published_date
        # 日期是结构字段（来源发布日期），应由文件名/frontmatter 事实层决定，
        # 而非 LLM 看到文档正文里出现的年份自填（会导致全部条目标今天日期）。
        # news/announcement 一份源里的多 entry 共享发布日期也安全。
        if published_date:
            for e in entries:
                if "date" not in e or not e.get("date") or e["date"] != published_date:
                    e["date"] = published_date
        if entries and wiki_path:
            # 7.1 质量检查
            original_count = len(entries)
            entries, quality_warnings = validate_entries(entries)
            if quality_warnings:
                print(f"  质量警告: {'; '.join(quality_warnings[:3])}")

            # 如果所有条目都被过滤，标记为质量拒绝
            if not entries and original_count > 0:
                result["status"] = "quality_rejected"
                result["error"] = f"所有 {original_count} 个条目未通过质量检查"
                return result

            added = add_timeline_entries(wiki_path, entries, file_path)
            result["entries_added"] = added

        # 更新综合评估
        assessment = parsed.get("assessment_update", "")
        if assessment and wiki_path:
            if update_assessment(wiki_path, assessment):
                result["assessment_updated"] = True

        # 检查评估是否过期（如果本次 ingest 新增了条目）
        if wiki_path and result["entries_added"] > 0:
            if is_assessment_stale(wiki_path):
                # 标记需要刷新评估（由 batch_assessment.py 处理）
                result["assessment_stale"] = True

        # 写入矛盾警告
        contradictions = parsed.get("contradictions", [])
        if contradictions and wiki_path:
            write_contradictions(wiki_path, contradictions)
            result["contradictions_found"] = len(contradictions)

        # ── 双向更新：更新相关行业/主题 wiki ──
        if result["entries_added"] > 0 and not dry_run:
            try:
                _update_related_entities(
                    graph, entity_name, entity_type, entries, file_path, llm_client
                )
            except Exception:
                pass  # 不阻塞主流程

        result["status"] = "success"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


# ── 双向更新：更新相关行业/主题 ───────────
def _update_related_entities(
    graph, entity_name, entity_type, entries, file_path, llm_client
):
    """
    更新与主实体相关的行业/主题 wiki。
    使用 graph.find_related_entities() 找到相关实体，将条目复制过去（标记为 secondary）。
    """
    if entity_type != "company":
        return

    # 找到相关行业/主题
    related = graph.find_related_entities(entity_name, top_k=3)
    if not related:
        return

    for rel in related:
        rel_name = rel.get("name", "")
        rel_type = rel.get("type", "")
        relevance = rel.get("relevance_score", 0)

        # 只处理高相关性的行业/主题
        if relevance < 0.5:
            continue

        if rel_type == "sector":
            rel_wiki = get_wiki_path(rel_name, "sector", rel_name)
        elif rel_type == "theme":
            rel_wiki = get_wiki_path(rel_name, "theme", rel_name)
        else:
            continue

        if not rel_wiki:
            continue

        # 创建或更新相关实体 wiki
        if not rel_wiki.exists():
            create_wiki_template(rel_wiki, rel_name, rel_name, rel_type)

        # 添加条目（标记为相关公司动态）
        for entry in entries[:3]:  # 最多添加 3 个条目
            entry_copy = entry.copy()
            entry_copy["title"] = f"[{entity_name}] {entry_copy.get('title', '')}"
            entry_copy["points"] = entry_copy.get("points", []) + [
                f"来源: {entity_name}"
            ]

            add_timeline_entries(rel_wiki, [entry_copy], file_path)


# ── Segments 模式支持 ─────────────────────


def scan_pending_segments(graph, company_name=None):
    """扫描待处理的 segments 文件（JSONL）"""
    companies = graph.get_all_companies()
    if company_name:
        companies = [c for c in companies if c["name"] == company_name]

    pending = []
    ingested = get_ingested_set()

    for company in companies:
        name = company["name"]
        segments_dir = WIKI_ROOT / "companies" / name / "segments"
        if not segments_dir.exists():
            continue
        for seg_file in sorted(segments_dir.rglob("*.jsonl")):
            if is_ingested(seg_file, ingested):
                continue
            pending.append((str(seg_file), name, "company"))

    return pending


CATEGORY_TO_SOURCE = {
    "财务": "财报",
    "业务": "新闻",
    "战略": "新闻",
    "风险": "公告",
    "市场": "新闻",
    "治理": "公告",
    "技术": "新闻",
    "其他": "新闻",
}


def process_segments_file(
    seg_file: str, entity_name: str, entity_type: str, graph, dry_run=False
) -> dict:
    """从 segments JSONL 合成 wiki 时间线条目"""
    result = {
        "status": "pending",
        "entries_added": 0,
        "assessment_updated": False,
        "contradictions_found": 0,
        "error": None,
    }

    seg_path = Path(seg_file)
    try:
        segments = []
        with open(seg_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                segments.append(json.loads(line))
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"读取 segments 失败: {e}"
        return result

    if not segments:
        result["status"] = "skip"
        result["error"] = "无 segments"
        return result

    # 过滤低重要性段落
    important = [s for s in segments if s.get("importance") in ("高", "中")]
    if not important:
        important = segments[:5]  # 如果没有高/中，取前5个

    # 推断来源信息
    first_meta = segments[0].get("_meta", {}) if segments else {}
    doc_type = first_meta.get("doc_type", "unknown")
    source_rel = first_meta.get("source", "")

    # 优先从 segment _meta 读取原始日期，否则从 source 推断
    published_date = first_meta.get("original_date", "")
    if not published_date and source_rel:
        # 构造一个假文件名用于 extract_report_date
        fake_path = f"companies/{entity_name}/extracts/{source_rel}"
        published_date = extract_report_date(fake_path, doc_type) or ""
    if not published_date:
        published_date = datetime.now().strftime("%Y-%m-%d")

    # 推断标题
    title = source_rel.replace(".md", "").split("/")[-1] if source_rel else "分段合成"
    if len(title) > 60:
        title = title[:60] + "..."

    # 构建 key_points
    key_points = []
    for seg in important[:8]:  # 最多8个要点
        text = seg.get("text", "").strip()
        if not text:
            continue
        # 截断过长
        if len(text) > 200:
            text = text[:197] + "..."
        # 添加标签前缀
        cat = seg.get("category", "其他")
        imp = seg.get("importance", "中")
        prefix = f"[{cat}/{imp}] " if cat != "其他" else ""
        key_points.append(prefix + text)

    if not key_points:
        result["status"] = "skip"
        result["error"] = "无有效要点"
        return result

    # 确定 source_type
    category_counts = {}
    for seg in important:
        cat = seg.get("category", "其他")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    if category_counts:
        dominant_category = max(category_counts.items(), key=lambda x: x[1])[0]
    else:
        dominant_category = "其他"
    source_type = CATEGORY_TO_SOURCE.get(dominant_category, "新闻")

    # 映射 doc_type → source_type
    if doc_type in ["annual_report", "semi_annual_report", "quarterly_report"]:
        source_type = "财报"
    elif doc_type == "prospectus":
        source_type = "招股"
    elif doc_type == "investor_relations":
        source_type = "投资者关系"
    elif doc_type == "announcement":
        source_type = "公告"
    elif doc_type == "research_report":
        source_type = "研报"

    entry = {
        "date": published_date,
        "source_type": source_type,
        "title": title,
        "key_points": key_points,
    }

    # 写入 wiki
    topic_name = "公司动态" if entity_type == "company" else entity_name
    wiki_path = get_wiki_path(entity_name, entity_type, topic_name)

    if dry_run:
        result["status"] = "dry_run"
        result["entries_added"] = 1
        return result

    if wiki_path and not wiki_path.exists():
        create_wiki_template(wiki_path, entity_name, topic_name, entity_type)

    if wiki_path:
        added = add_timeline_entries(wiki_path, [entry], seg_file)
        result["entries_added"] = added
        if added > 0:
            result["status"] = "success"
        else:
            result["status"] = "skip"
            result["error"] = "条目已存在或写入失败"
    else:
        result["status"] = "error"
        result["error"] = "无法确定 wiki 路径"

    return result


# ── 主流程 ────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="LLM 驱动的数据整理 — Ingest v2")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--dry-run", action="store_true", help="只检查不执行")
    parser.add_argument("--check", action="store_true", help="列出待处理文件")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 个文件")
    parser.add_argument("--file", type=str, help="处理指定文件")
    parser.add_argument(
        "--source",
        type=str,
        choices=["raw", "segments", "all"],
        default="raw",
        help="数据来源: raw=原始文件(默认), segments=标签化分段, all=两者都处理",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  上市公司知识库 — Ingest v2 (LLM 驱动)")
    print(f"  Source: {args.source}")
    print("=" * 60)

    # 加载图数据和 LLM
    graph = Graph(str(WIKI_ROOT / "graph.yaml"))
    llm_client = get_llm_client()
    llm_client._timeout = 120  # large documents may take longer

    if not llm_client.available:
        print("\n  ERROR: LLM 不可用。请检查 DEEPSEEK_API_KEY 配置。")
        sys.exit(1)

    # 处理指定文件
    if args.file:
        print(f"\n  Processing single file: {args.file}")
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = WIKI_ROOT / file_path
        # 自动推断 entity_type 和 entity_name
        rel_parts = file_path.relative_to(WIKI_ROOT).parts
        if len(rel_parts) >= 2 and rel_parts[0] == "sectors":
            inferred_type = "sector"
            inferred_name = rel_parts[1]
        elif len(rel_parts) >= 2 and rel_parts[0] == "companies":
            inferred_type = "company"
            inferred_name = rel_parts[1]
        else:
            inferred_type = "company"
            inferred_name = args.company or "未知"
        result = process_file(
            args.file,
            args.company or inferred_name,
            inferred_type,
            graph,
            llm_client,
            args.dry_run,
        )
        print(f"  Entity: {inferred_name} ({inferred_type})")
        print(f"  Status: {result['status']}")
        print(f"  Entries added: {result['entries_added']}")
        return

    # 扫描待处理文件
    pending_raw = []
    pending_segments = []

    if args.source in ("raw", "all"):
        pending_raw = scan_pending_files(graph, args.company)
    if args.source in ("segments", "all"):
        pending_segments = scan_pending_segments(graph, args.company)

    pending = []
    if args.source in ("raw", "all"):
        pending.extend([("raw", fp, ent, etype) for fp, ent, etype in pending_raw])
    if args.source in ("segments", "all"):
        pending.extend(
            [("segments", fp, ent, etype) for fp, ent, etype in pending_segments]
        )

    if args.limit > 0:
        pending = pending[: args.limit]

    if not pending:
        print("\n  No pending files to ingest.")
        return

    print(
        f"\n  Pending: {len(pending)} (raw:{len(pending_raw)}, segments:{len(pending_segments)})"
    )

    if args.check:
        for source_type, fp, ent, etype in pending:
            rel = Path(fp).relative_to(WIKI_ROOT)
            print(f"    [{source_type}] [{etype}] {ent}: {rel}")
        return

    # 处理文件
    total_entries = 0
    total_assessments = 0
    total_contradictions = 0
    total_skipped = 0
    total_errors = 0

    for i, (source_type, fp, ent, etype) in enumerate(pending):
        rel = Path(fp).relative_to(WIKI_ROOT)
        print(f"\n  [{i + 1}/{len(pending)}] [{source_type}] {rel}")

        if source_type == "raw":
            result = process_file(fp, ent, etype, graph, llm_client, args.dry_run)
        else:
            result = process_segments_file(fp, ent, etype, graph, args.dry_run)

        status_emoji = {
            "success": "[OK]",
            "skip": "[SKIP]",
            "llm_error": "[ERR LLM]",
            "parse_error": "[ERR Parse]",
            "error": "[ERR]",
            "dry_run": "[DRY]",
        }.get(result["status"], "[?]")

        print(f"    {status_emoji} {result['status']}")

        if result["entries_added"] > 0:
            print(f"       → Entries: +{result['entries_added']}")
            total_entries += result["entries_added"]
        if result["assessment_updated"]:
            print(f"       → Assessment updated")
            total_assessments += 1
        if result["contradictions_found"] > 0:
            print(f"       → Contradictions: {result['contradictions_found']}")
            total_contradictions += result["contradictions_found"]
        if result["error"]:
            print(f"       → Error: {result['error'][:80]}")

        if result["status"] == "skip":
            total_skipped += 1
        elif result["status"] in ["llm_error", "parse_error", "error"]:
            total_errors += 1

        if not args.dry_run and result["status"] in ["success", "skip"]:
            mark_ingested(fp)

    print(f"\n{'=' * 60}")
    print(f"  Done.")
    print(f"  Entries added: {total_entries}")
    print(f"  Assessments updated: {total_assessments}")
    print(f"  Contradictions found: {total_contradictions}")
    print(f"  Skipped: {total_skipped}")
    print(f"  Errors: {total_errors}")
    print(f"{'=' * 60}")

    if not args.dry_run and total_entries > 0:
        append_log(
            "ingest_v2",
            f"LLM ingest ({args.source}): {len(pending)} files, +{total_entries} entries, {total_assessments} assessments",
        )


if __name__ == "__main__":
    main()
