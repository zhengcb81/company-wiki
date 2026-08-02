#!/usr/bin/env python3
"""
expire_tracker.py — 信息过期追踪器

标注和检测时间线条目的信息有效期。

用法：
    python scripts/expire_tracker.py --company 中微公司 --report   # 生成过期报告
    python scripts/expire_tracker.py --company 中微公司 --check    # 检查过期条目
"""

import argparse
import re
from datetime import datetime, timedelta

from common import WIKI_ROOT

# 信息类型和有效期（天）
INFO_HALF_LIFE = {
    "订单": 365,  # 订单有效期1年
    "合同": 365,  # 合同有效期1年
    "业绩": 90,  # 业绩有效期3个月（季度更新）
    "财报": 180,  # 财报有效期6个月
    "政策": 730,  # 政策有效期2年
    "技术": 1095,  # 技术突破长期有效（3年）
    "人事": 365,  # 人事变动有效期1年
    "融资": 365,  # 融资有效期1年
    "风险": 180,  # 风险有效期6个月
    "其他": 365,  # 默认1年
}


def classify_entry(entry_text: str) -> str:
    """分类时间线条目的信息类型"""
    text = entry_text.lower()

    # 订单/合同相关
    if any(kw in text for kw in ["订单", "合同", "中标", "签约", "协议"]):
        return "订单"

    # 业绩相关
    if any(kw in text for kw in ["业绩", "营收", "利润", "增长", "下滑", "净利润"]):
        return "业绩"

    # 财报相关
    if any(kw in text for kw in ["年报", "半年报", "季报", "财报", "报告期"]):
        return "财报"

    # 政策相关
    if any(kw in text for kw in ["政策", "补贴", "监管", "法规", "规划"]):
        return "政策"

    # 技术相关
    if any(kw in text for kw in ["技术", "研发", "专利", "突破", "创新"]):
        return "技术"

    # 人事相关
    if any(kw in text for kw in ["人事", "任命", "辞职", "高管", "董事"]):
        return "人事"

    # 融资相关
    if any(kw in text for kw in ["融资", "增发", "配股", "IPO", "上市"]):
        return "融资"

    # 风险相关
    if any(kw in text for kw in ["风险", "诉讼", "处罚", "违规", "调查"]):
        return "风险"

    return "其他"


def parse_entry_date(entry_text: str) -> str:
    """解析时间线条目的日期"""
    # 匹配 YYYY-MM-DD 格式
    match = re.search(r"(\d{4}-\d{2}-\d{2})", entry_text)
    if match:
        return match.group(1)
    return None


def check_expiry(entry_date: str, info_type: str) -> dict:
    """检查条目是否过期"""
    if not entry_date:
        return {"expired": False, "days_remaining": None, "reason": "no_date"}

    try:
        entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
    except ValueError:
        return {"expired": False, "days_remaining": None, "reason": "invalid_date"}

    half_life = INFO_HALF_LIFE.get(info_type, 365)
    expiry_dt = entry_dt + timedelta(days=half_life)
    now = datetime.now()

    days_remaining = (expiry_dt - now).days
    expired = days_remaining < 0

    return {
        "expired": expired,
        "expiry_date": expiry_dt.strftime("%Y-%m-%d"),
        "days_remaining": days_remaining,
        "half_life": half_life,
        "info_type": info_type,
    }


def analyze_company(company: str) -> dict:
    """分析公司的信息过期情况"""
    wiki_dir = WIKI_ROOT / "companies" / company / "wiki"
    timeline_file = wiki_dir / "公司动态.md"

    if not timeline_file.exists():
        return {"company": company, "entries": [], "expired_count": 0}

    content = timeline_file.read_text(encoding="utf-8")

    # 解析时间线条目
    entries = []
    current_entry = []

    for line in content.split("\n"):
        if line.startswith("### "):
            if current_entry:
                entries.append("\n".join(current_entry))
            current_entry = [line]
        elif current_entry:
            current_entry.append(line)

    if current_entry:
        entries.append("\n".join(current_entry))

    # 分析每个条目
    analyzed_entries = []
    expired_count = 0

    for entry in entries:
        entry_date = parse_entry_date(entry)
        info_type = classify_entry(entry)
        expiry_info = check_expiry(entry_date, info_type)

        analyzed_entries.append(
            {
                "date": entry_date,
                "type": info_type,
                "expired": expiry_info["expired"],
                "days_remaining": expiry_info.get("days_remaining"),
                "text_preview": entry[:100],
            }
        )

        if expiry_info["expired"]:
            expired_count += 1

    return {
        "company": company,
        "entries": analyzed_entries,
        "total_count": len(analyzed_entries),
        "expired_count": expired_count,
    }


def generate_report(company: str):
    """生成过期报告"""
    analysis = analyze_company(company)

    report = f"""# 信息过期报告: {company}

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
**总条目数**: {analysis["total_count"]}
**过期条目**: {analysis["expired_count"]}

---

## 过期条目

"""

    expired_entries = [e for e in analysis["entries"] if e["expired"]]

    if not expired_entries:
        report += "无过期条目\n"
    else:
        report += "| 日期 | 类型 | 过期天数 | 内容预览 |\n"
        report += "|------|------|----------|----------|\n"

        for entry in expired_entries[:20]:
            days = abs(entry["days_remaining"]) if entry["days_remaining"] else "?"
            preview = entry["text_preview"][:50]
            report += (
                f"| {entry['date']} | {entry['type']} | {days}天 | {preview}... |\n"
            )

    report += """
---

## 信息类型分布

"""

    type_counts = {}
    for entry in analysis["entries"]:
        info_type = entry["type"]
        type_counts[info_type] = type_counts.get(info_type, 0) + 1

    report += "| 类型 | 数量 | 有效期 |\n"
    report += "|------|------|--------|\n"

    for info_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        half_life = INFO_HALF_LIFE.get(info_type, 365)
        report += f"| {info_type} | {count} | {half_life}天 |\n"

    # 保存报告
    report_path = WIKI_ROOT / "docs" / f"expire_report_{company}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"报告已保存: {report_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="信息过期追踪器")
    parser.add_argument("--company", required=True, help="公司名称")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--check", action="store_true", help="检查过期条目")
    args = parser.parse_args()

    if args.report:
        generate_report(args.company)
    elif args.check:
        analysis = analyze_company(args.company)
        print(f"\n{args.company}:")
        print(f"  总条目: {analysis['total_count']}")
        print(f"  过期条目: {analysis['expired_count']}")
    else:
        # 默认检查
        analysis = analyze_company(args.company)
        expired = analysis["expired_count"]
        total = analysis["total_count"]
        print(f"{args.company}: {expired}/{total} 过期")


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    main()
