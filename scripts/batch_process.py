#!/usr/bin/env python3
"""
batch_process.py — 批量处理脚本

对指定Tier的公司运行完整Pipeline。

用法：
    python scripts/batch_process.py --tier 1 --dry-run    # 预览处理计划
    python scripts/batch_process.py --tier 1 --limit 5    # 每公司限制5个文件
    python scripts/batch_process.py --company 中微公司     # 处理指定公司
"""

import argparse
import subprocess
import sys
from datetime import datetime

from common import WIKI_ROOT, require_legacy_writer_permission

# Tier 1 公司列表（半导体设备核心公司）
TIER_1_COMPANIES = [
    "中微公司",
    "北方华创",
    "拓荆科技",
    "盛美上海",
    "华海清科",
    "长川科技",
    "精测电子",
    "至纯科技",
]

# Tier 2 公司列表（扩展覆盖）
TIER_2_COMPANIES = [
    "中芯国际",
    "韦尔股份",
    "兆易创新",
    "卓胜微",
    "圣邦股份",
    "澜起科技",
    "沪硅产业",
    "安集科技",
]


def get_companies_by_tier(tier: int) -> list:
    """获取指定Tier的公司列表"""
    if tier == 1:
        return TIER_1_COMPANIES
    elif tier == 2:
        return TIER_2_COMPANIES
    else:
        return []


def check_company_status(company: str) -> dict:
    """检查公司数据状态"""
    company_dir = WIKI_ROOT / "companies" / company

    # 检查raw目录
    raw_dir = company_dir / "raw"
    raw_files = list(raw_dir.rglob("*.pdf")) if raw_dir.exists() else []

    # 检查extracts目录
    extracts_dir = company_dir / "extracts"
    extract_files = list(extracts_dir.rglob("*.md")) if extracts_dir.exists() else []

    # 检查analysis文件
    analysis_files = (
        list(extracts_dir.rglob("*.analysis.json")) if extracts_dir.exists() else []
    )

    # 检查wiki目录
    wiki_dir = company_dir / "wiki"
    wiki_files = list(wiki_dir.glob("*.md")) if wiki_dir.exists() else []

    return {
        "company": company,
        "raw_files": len(raw_files),
        "extract_files": len(extract_files),
        "analysis_files": len(analysis_files),
        "wiki_files": len(wiki_files),
        "needs_processing": len(extract_files) > len(analysis_files),
    }


def process_company(company: str, limit: int = 0, dry_run: bool = False) -> dict:
    """处理单个公司"""
    print(f"\n{'=' * 60}")
    print(f"  处理公司: {company}")
    print(f"{'=' * 60}")

    # 检查状态
    status = check_company_status(company)
    print(f"  Raw文件: {status['raw_files']}")
    print(f"  Extract文件: {status['extract_files']}")
    print(f"  Analysis文件: {status['analysis_files']}")
    print(f"  Wiki文件: {status['wiki_files']}")

    if not status["needs_processing"]:
        print("  状态: 已完成，无需处理")
        return {"company": company, "status": "skipped", "reason": "already_complete"}

    if dry_run:
        print("  状态: 预览模式，不执行")
        return {"company": company, "status": "dry_run"}

    # 运行Pipeline
    cmd = [
        sys.executable,
        "scripts/full_pipeline.py",
        "--company",
        company,
        "--no-gates",
    ]

    if limit > 0:
        cmd.extend(["--limit", str(limit)])

    print(f"  运行Pipeline: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(WIKI_ROOT),
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode == 0:
            print("  状态: 成功")
            return {"company": company, "status": "success"}
        else:
            print("  状态: 失败")
            print(f"  错误: {result.stderr[:200]}")
            return {
                "company": company,
                "status": "failed",
                "error": result.stderr[:200],
            }
    except subprocess.TimeoutExpired:
        print("  状态: 超时")
        return {"company": company, "status": "timeout"}
    except Exception as e:
        print("  状态: 错误")
        print(f"  错误: {str(e)}")
        return {"company": company, "status": "error", "error": str(e)}


def generate_report(results: list):
    """生成处理报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    report = f"""# 批量处理报告

**生成时间**: {timestamp}
**处理公司数**: {len(results)}

---

## 处理结果

| 公司 | 状态 | 说明 |
|------|------|------|
"""

    success_count = 0
    failed_count = 0
    skipped_count = 0

    for result in results:
        company = result["company"]
        status = result["status"]

        if status == "success":
            success_count += 1
            status_icon = "✅"
        elif status == "skipped":
            skipped_count += 1
            status_icon = "⏭️"
        else:
            failed_count += 1
            status_icon = "❌"

        reason = result.get("reason", result.get("error", ""))[:30]
        report += f"| {company} | {status_icon} {status} | {reason} |\n"

    report += f"""
---

## 统计

- 成功: {success_count}
- 跳过: {skipped_count}
- 失败: {failed_count}
- 总计: {len(results)}
"""

    # 保存报告
    report_path = (
        WIKI_ROOT
        / "docs"
        / f"batch_process_report_{datetime.now().strftime('%Y%m%d')}.md"
    )
    report_path.write_text(report, encoding="utf-8")
    print(f"\n报告已保存: {report_path}")

    return report


def main():
    if not require_legacy_writer_permission("batch_process.py"):
        return

    parser = argparse.ArgumentParser(description="批量处理脚本")
    parser.add_argument("--tier", type=int, choices=[1, 2], help="公司Tier")
    parser.add_argument("--company", type=str, help="指定公司")
    parser.add_argument("--limit", type=int, default=0, help="每公司限制文件数")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    args = parser.parse_args()

    # 确定要处理的公司列表
    if args.company:
        companies = [args.company]
    elif args.tier:
        companies = get_companies_by_tier(args.tier)
    else:
        print("请指定 --tier 或 --company")
        return

    print("=" * 60)
    print("  批量处理")
    print("=" * 60)
    print(f"\n公司数量: {len(companies)}")
    print(f"限制: {args.limit if args.limit > 0 else '无'}")
    print(f"模式: {'预览' if args.dry_run else '执行'}")

    # 检查所有公司状态
    print("\n公司状态检查:")
    print("-" * 60)

    results = []
    for company in companies:
        status = check_company_status(company)
        needs = "需要处理" if status["needs_processing"] else "已完成"
        print(
            f"  {company:<15} {needs} (extract={status['extract_files']}, analysis={status['analysis_files']})"
        )

    # 处理公司
    if not args.dry_run:
        print("\n开始处理:")
        print("-" * 60)

        for company in companies:
            result = process_company(company, limit=args.limit, dry_run=args.dry_run)
            results.append(result)

        # 生成报告
        generate_report(results)
    else:
        print("\n预览模式，不执行处理")


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    main()
