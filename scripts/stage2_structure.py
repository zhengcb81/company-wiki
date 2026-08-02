#!/usr/bin/env python3
"""
stage2_structure.py — 阶段2 Pipeline：结构化处理

从 companies/{name}/extracts/ 读取提取的 Markdown，
提取财务数据和章节标记，保存为结构化 JSON。

用法：
    python scripts/stage2_structure.py                    # 处理所有公司
    python scripts/stage2_structure.py --company 北方华创  # 只处理指定公司
    python scripts/stage2_structure.py --check             # 列出待处理文件
    python scripts/stage2_structure.py --dry-run           # 预览
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from common import WIKI_ROOT


# ── 财务数据提取 ──────────────────────────


def normalize_financial_value(value: float, unit: str) -> tuple:
    """
    标准化财务数值为统一单位（亿元或万元）。

    规则：
    - 数值 >= 1亿: 使用 亿元
    - 1万元 <= 数值 < 1亿: 使用 万元
    - 数值 < 1万元: 保持原单位

    返回: (normalized_value, normalized_unit)
    """
    if unit == "元":
        if value >= 100000000:
            return value / 100000000, "亿元"
        elif value >= 10000:
            return value / 10000, "万元"
        else:
            return value, "元"
    elif unit == "万元":
        if value >= 10000:
            return value / 10000, "亿元"
        else:
            return value, "万元"
    elif unit == "亿元":
        return value, "亿元"
    else:
        return value, unit


def extract_financial_data(text: str, doc_type: str) -> dict:
    """
    从文本中提取关键财务指标。

    返回: {
        "revenue": {"value": float, "unit": str, "yoy": float},
        "net_profit": {"value": float, "unit": str, "yoy": float},
        "gross_margin": {"value": float, "unit": str},
        "total_assets": {"value": float, "unit": str},
        "total_liabilities": {"value": float, "unit": str},
        "equity": {"value": float, "unit": str},
        "operating_cash_flow": {"value": float, "unit": str},
        "rd_expense": {"value": float, "unit": str},
    }
    """
    financial_data = {}

    # 营业收入模式
    revenue_patterns = [
        r"营业收入[^\d]*?([\d,]+\.?\d*)\s*(?:万元|亿元|元)",
        r"营业总收入[^\d]*?([\d,]+\.?\d*)\s*(?:万元|亿元|元)",
        r"主营业务收入[^\d]*?([\d,]+\.?\d*)\s*(?:万元|亿元|元)",
    ]

    for pattern in revenue_patterns:
        match = re.search(pattern, text)
        if match:
            value_str = match.group(1).replace(",", "")
            try:
                value = float(value_str)
                # 判断单位（搜索匹配位置附近的单位词）
                context = text[match.start() : match.end() + 20]
                if "亿元" in context:
                    unit = "亿元"
                elif "万元" in context:
                    unit = "万元"
                else:
                    unit = "元"

                # 标准化为亿元（便于统一比较）
                normalized_value, normalized_unit = normalize_financial_value(
                    value, unit
                )
                financial_data["revenue"] = {
                    "value": normalized_value,
                    "unit": normalized_unit,
                    "raw_value": value,
                    "raw_unit": unit,
                }
                break
            except ValueError:
                continue

    # 净利润模式
    profit_patterns = [
        r"归属于上市公司股东的净利润[^\d]*?([\d,]+\.?\d*)\s*(?:万元|亿元|元)",
        r"净利润[^\d]*?([\d,]+\.?\d*)\s*(?:万元|亿元|元)",
        r"归属于母公司所有者的净利润[^\d]*?([\d,]+\.?\d*)\s*(?:万元|亿元|元)",
    ]

    for pattern in profit_patterns:
        match = re.search(pattern, text)
        if match:
            value_str = match.group(1).replace(",", "")
            try:
                value = float(value_str)
                context = text[match.start() : match.end() + 20]
                if "亿元" in context:
                    unit = "亿元"
                elif "万元" in context:
                    unit = "万元"
                else:
                    unit = "元"

                normalized_value, normalized_unit = normalize_financial_value(
                    value, unit
                )
                financial_data["net_profit"] = {
                    "value": normalized_value,
                    "unit": normalized_unit,
                    "raw_value": value,
                    "raw_unit": unit,
                }
                break
            except ValueError:
                continue

    # 毛利率模式
    margin_patterns = [
        r"毛利率[^\d]*?([\d.]+)\s*%",
        r"综合毛利率[^\d]*?([\d.]+)\s*%",
        r"主营业务毛利率[^\d]*?([\d.]+)\s*%",
    ]

    for pattern in margin_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                value = float(match.group(1))
                financial_data["gross_margin"] = {"value": value, "unit": "%"}
                break
            except ValueError:
                continue

    # 总资产模式 - 优先匹配主要财务数据，避免子公司表格
    asset_patterns = [
        # 主要财务指标摘要中的总资产（优先）
        r"总资产\s*[:：]?\s*([\d,]+\.?\d*)\s*(?:万元|亿元|元)?",
        # 合并资产负债表中的总资产
        r"资产总计\s*[:：]?\s*([\d,]+\.?\d*)\s*(?:万元|亿元|元)?",
        r"资产总额\s*[:：]?\s*([\d,]+\.?\d*)\s*(?:万元|亿元|元)?",
    ]

    for pattern in asset_patterns:
        matches = list(re.finditer(pattern, text))
        for match in matches:
            value_str = match.group(1).replace(",", "")
            try:
                value = float(value_str)

                # 获取上下文（前后100字符）以判断单位
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]

                # 检查是否是子公司表格（包含"子公司"、"注册资本"等关键词）
                if "子公司" in context and "注册资本" in context:
                    continue
                if "主要控股参股公司" in context:
                    continue

                # 判断单位
                if "亿元" in context:
                    unit = "亿元"
                elif "万元" in context:
                    unit = "万元"
                else:
                    # 没有明确单位时，根据数值大小推断
                    if value >= 100000000:
                        unit = "元"
                    elif value >= 10000:
                        unit = "万元"
                    else:
                        unit = "亿元"

                normalized_value, normalized_unit = normalize_financial_value(
                    value, unit
                )

                # 合理性检查：中微公司总资产应该在100-500亿元之间
                if normalized_value < 10 or normalized_value > 1000:
                    # 可能是子公司数据或提取错误，跳过
                    continue

                financial_data["total_assets"] = {
                    "value": normalized_value,
                    "unit": normalized_unit,
                    "raw_value": value,
                    "raw_unit": unit,
                }
                break
            except ValueError:
                continue
        if "total_assets" in financial_data:
            break

    # 净资产模式 - 优先匹配主要财务数据，避免子公司表格
    equity_patterns = [
        # 主要财务指标摘要中的净资产（优先）
        r"归属于上市公司股东的净资产\s*[:：]?\s*([\d,]+\.?\d*)\s*(?:万元|亿元|元)?",
        r"归属于母公司所有者权益\s*[:：]?\s*([\d,]+\.?\d*)\s*(?:万元|亿元|元)?",
        r"所有者权益合计\s*[:：]?\s*([\d,]+\.?\d*)\s*(?:万元|亿元|元)?",
        r"净资产\s*[:：]?\s*([\d,]+\.?\d*)\s*(?:万元|亿元|元)?",
    ]

    for pattern in equity_patterns:
        matches = list(re.finditer(pattern, text))
        for match in matches:
            value_str = match.group(1).replace(",", "")
            try:
                value = float(value_str)

                # 获取上下文（前后100字符）以判断单位
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]

                # 检查是否是子公司表格（包含"子公司"、"注册资本"等关键词）
                if "子公司" in context and "注册资本" in context:
                    continue
                if "主要控股参股公司" in context:
                    continue

                # 判断单位
                if "亿元" in context:
                    unit = "亿元"
                elif "万元" in context:
                    unit = "万元"
                else:
                    # 没有明确单位时，根据数值大小推断
                    if value >= 100000000:
                        unit = "元"
                    elif value >= 10000:
                        unit = "万元"
                    else:
                        unit = "亿元"

                normalized_value, normalized_unit = normalize_financial_value(
                    value, unit
                )

                # 合理性检查：中微公司净资产应该在100-300亿元之间
                if normalized_value < 10 or normalized_value > 500:
                    # 可能是子公司数据或提取错误，跳过
                    continue

                financial_data["equity"] = {
                    "value": normalized_value,
                    "unit": normalized_unit,
                    "raw_value": value,
                    "raw_unit": unit,
                }
                break
            except ValueError:
                continue
        if "equity" in financial_data:
            break

    # 经营现金流模式
    cashflow_patterns = [
        r"经营活动产生的现金流量净额[^\d]*?([\d,]+\.?\d*)\s*(?:万元|亿元|元)",
        r"经营活动现金流量净额[^\d]*?([\d,]+\.?\d*)\s*(?:万元|亿元|元)",
    ]

    for pattern in cashflow_patterns:
        match = re.search(pattern, text)
        if match:
            value_str = match.group(1).replace(",", "")
            try:
                value = float(value_str)
                context = text[match.start() : match.end() + 20]
                if "亿元" in context:
                    unit = "亿元"
                elif "万元" in context:
                    unit = "万元"
                else:
                    unit = "元"

                normalized_value, normalized_unit = normalize_financial_value(
                    value, unit
                )
                financial_data["operating_cash_flow"] = {
                    "value": normalized_value,
                    "unit": normalized_unit,
                    "raw_value": value,
                    "raw_unit": unit,
                }
                break
            except ValueError:
                continue

    # 研发投入模式
    rd_patterns = [
        r"研发支出[^\d]*?([\d,]+\.?\d*)\s*(?:万元|亿元|元)",
        r"研发投入[^\d]*?([\d,]+\.?\d*)\s*(?:万元|亿元|元)",
        r"研发费用[^\d]*?([\d,]+\.?\d*)\s*(?:万元|亿元|元)",
    ]

    for pattern in rd_patterns:
        match = re.search(pattern, text)
        if match:
            value_str = match.group(1).replace(",", "")
            try:
                value = float(value_str)
                context = text[match.start() : match.end() + 20]
                if "亿元" in context:
                    unit = "亿元"
                elif "万元" in context:
                    unit = "万元"
                else:
                    unit = "元"

                normalized_value, normalized_unit = normalize_financial_value(
                    value, unit
                )
                financial_data["rd_expense"] = {
                    "value": normalized_value,
                    "unit": normalized_unit,
                    "raw_value": value,
                    "raw_unit": unit,
                }
                break
            except ValueError:
                continue

    return financial_data


def extract_sections(text: str, doc_type: str) -> list:
    """
    从文本中提取章节标记。

    返回: [
        {
            "title": str,
            "type": str,  # management_discussion, financial_data, risk_factors, etc.
            "importance": str,  # high, medium, low
            "start_pos": int,
            "end_pos": int
        }
    ]
    """
    sections = []

    # 章节关键词映射
    section_keywords = {
        "管理层讨论与分析": {"type": "management_discussion", "importance": "high"},
        "经营情况讨论与分析": {"type": "management_discussion", "importance": "high"},
        "业务概要": {"type": "business_overview", "importance": "high"},
        "主要业务": {"type": "business_overview", "importance": "high"},
        "财务报告": {"type": "financial_statements", "importance": "high"},
        "主要会计数据": {"type": "financial_data", "importance": "high"},
        "主要财务指标": {"type": "financial_data", "importance": "high"},
        "资产负债表": {"type": "balance_sheet", "importance": "high"},
        "利润表": {"type": "income_statement", "importance": "high"},
        "现金流量表": {"type": "cash_flow", "importance": "high"},
        "风险因素": {"type": "risk_factors", "importance": "medium"},
        "重要事项": {"type": "important_events", "importance": "medium"},
        "股东情况": {"type": "shareholders", "importance": "medium"},
        "董事、监事、高级管理人员": {"type": "management_team", "importance": "medium"},
        "公司治理": {"type": "corporate_governance", "importance": "medium"},
    }

    # 查找章节标题
    seen_positions = set()
    for keyword, info in section_keywords.items():
        # 使用正则表达式查找章节标题
        pattern = rf"第[一二三四五六七八九十]+节\s*{re.escape(keyword)}"
        matches = list(re.finditer(pattern, text))

        for match in matches:
            # 去重：如果这个位置附近（±100字符）已经有相同类型的章节，跳过
            pos = match.start()
            is_duplicate = any(abs(pos - seen_pos) < 100 for seen_pos in seen_positions)
            if is_duplicate:
                continue

            seen_positions.add(pos)
            sections.append(
                {
                    "title": match.group(),
                    "type": info["type"],
                    "importance": info["importance"],
                    "start_pos": pos,
                    "end_pos": -1,  # 稍后计算
                }
            )

    # 按位置排序
    sections.sort(key=lambda x: x["start_pos"])

    # 计算每个章节的结束位置
    for i in range(len(sections)):
        if i < len(sections) - 1:
            sections[i]["end_pos"] = sections[i + 1]["start_pos"]
        else:
            sections[i]["end_pos"] = len(text)

    return sections


def structure_single_file(extract_path: Path, dry_run=False) -> dict:
    """处理单个提取文件"""
    try:
        content = extract_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"status": "error", "error": str(e)}

    # 从 frontmatter 提取信息
    frontmatter_match = re.match(r"---\n(.*?)\n---\n", content, re.DOTALL)
    if not frontmatter_match:
        return {"status": "error", "error": "No frontmatter found"}

    frontmatter = frontmatter_match.group(1)
    body = content[frontmatter_match.end() :]

    # 解析 frontmatter（支持YAML格式）
    metadata = {}
    sections_from_frontmatter = []
    current_section = None
    in_sections = False

    for line in frontmatter.split("\n"):
        # 检测sections字段开始
        if line.strip() == "sections:":
            in_sections = True
            continue

        if in_sections:
            # 解析sections列表项
            if line.strip().startswith("- number:"):
                if current_section:
                    sections_from_frontmatter.append(current_section)
                current_section = {"number": line.split(":")[1].strip().strip('"')}
            elif line.strip().startswith("title:") and current_section:
                current_section["title"] = line.split(":")[1].strip().strip('"')
            elif line.strip().startswith("position:") and current_section:
                try:
                    current_section["position"] = int(line.split(":")[1].strip())
                except ValueError:
                    current_section["position"] = 0
            elif not line.strip().startswith("-") and not line.strip().startswith(" "):
                # sections块结束
                if current_section:
                    sections_from_frontmatter.append(current_section)
                    current_section = None
                in_sections = False
                # 继续解析普通metadata
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip().strip('"')
        else:
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip().strip('"')

    # 处理最后一个section
    if current_section:
        sections_from_frontmatter.append(current_section)

    doc_type = metadata.get("doc_type", "unknown")
    metadata.get("company", "unknown")
    metadata.get("period", "")

    # 提取财务数据
    financial_data = extract_financial_data(body, doc_type)

    # 提取章节（用于向后兼容）
    sections = extract_sections(body, doc_type)

    # 构建结构化数据
    structured = {
        "metadata": metadata,
        "financial_data": financial_data,
        "sections": [
            {
                "title": s["title"],
                "type": s["type"],
                "importance": s["importance"],
            }
            for s in sections
        ],
        "text_length": len(body),
        "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # 如果frontmatter中有sections，添加到metadata中
    if sections_from_frontmatter:
        structured["metadata"]["sections"] = sections_from_frontmatter

    if dry_run:
        return {
            "status": "dry_run",
            "structured": structured,
        }

    # 保存结构化数据
    struct_path = extract_path.with_suffix(".json")
    struct_path.write_text(
        json.dumps(structured, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "status": "success",
        "struct_path": str(struct_path),
        "financial_data": financial_data,
        "sections_count": len(sections),
    }


def main():
    parser = argparse.ArgumentParser(description="阶段2：结构化处理")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--check", action="store_true", help="列出待处理文件")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--limit", type=int, default=0, help="最多处理 N 个文件")
    args = parser.parse_args()

    print("=" * 60)
    print("  阶段2：结构化处理")
    print("=" * 60)

    # 扫描所有提取文件
    extract_files = []
    companies_dir = WIKI_ROOT / "companies"

    if args.company:
        company_dirs = [companies_dir / args.company]
    else:
        company_dirs = list(companies_dir.iterdir())

    for company_dir in company_dirs:
        if not company_dir.is_dir():
            continue
        extracts_dir = company_dir / "extracts"
        if not extracts_dir.exists():
            continue
        for md_file in extracts_dir.rglob("*.md"):
            # 检查是否已有对应的 JSON 文件
            json_file = md_file.with_suffix(".json")
            if not json_file.exists():
                extract_files.append(md_file)

    print(f"找到 {len(extract_files)} 个待处理文件")

    if args.check:
        for f in extract_files[:20]:
            print(f"  {f.relative_to(WIKI_ROOT)}")
        if len(extract_files) > 20:
            print(f"  ... 还有 {len(extract_files) - 20} 个")
        return 0

    if not extract_files:
        print("没有待处理的文件")
        return 0

    if args.limit > 0:
        extract_files = extract_files[: args.limit]
        print(f"限制处理 {len(extract_files)} 个文件")

    success = 0
    errors = 0

    for i, extract_path in enumerate(extract_files, 1):
        print(f"\n[{i}/{len(extract_files)}] {extract_path.relative_to(WIKI_ROOT)}")
        result = structure_single_file(extract_path, dry_run=args.dry_run)

        status = result["status"]
        if status == "success":
            success += 1
            print(
                f"  -> OK | 财务数据: {len(result['financial_data'])} 项, "
                f"章节: {result['sections_count']} 个"
            )
        elif status == "dry_run":
            print(
                f"  -> DRY-RUN | 财务数据: {len(result['structured']['financial_data'])} 项, "
                f"章节: {len(result['structured']['sections'])} 个"
            )
        else:
            errors += 1
            print(f"  -> ERR | {result.get('error', '')}")

    print(f"\n{'=' * 60}")
    print(f"完成: {success} 成功, {errors} 错误")
    print(f"{'=' * 60}")

    return 0


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    sys.exit(main())
