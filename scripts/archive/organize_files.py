#!/usr/bin/env python3
"""
将 companies/ 下散落的文件归类到 raw/ 的对应子目录。

规则：
  - 公司根目录的 PDF → 移入 raw/ 对应子目录
  - raw/ 根层的 PDF（与子目录并列）→ 移入对应子目录
  - 不处理 wiki/ 和 raw/ 已在子目录内的文件

分类逻辑（基于文件名关键词）：
  年度报告       → raw/financial_reports/annual/
  半年度报告     → raw/financial_reports/semi_annual/
  季度报告/Q报告 → raw/financial_reports/quarterly/
  招股说明书     → raw/prospectus/
  投资者关系     → raw/investor_relations/
  港股公告       → raw/announcements/
  公告/章程/制度等 → raw/announcements/
"""

import os
import re
import shutil
from pathlib import Path

WIKI_ROOT = Path(__file__).resolve().parent.parent
COMPANIES_DIR = WIKI_ROOT / "companies"

# ── 分类规则 ──────────────────────────────────────────────
# 按优先级排列，先匹配到的先生效

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("prospectus", ["招股说明书"]),
    ("investor_relations", ["投资者关系"]),
    # 财报类 — 需区分年度/半年度/季度
    # (下面在函数中用更细致的逻辑处理)
]

# 公告类关键词（不含财报、招股书、投资者关系的其他 PDF）
ANNOUNCEMENT_KEYWORDS = [
    "公告",
    "章程",
    "制度",
    "通知",
    "决议",
    "专项",
    "述职",
    "审计报告",
    "审计委员会",
    "内控",
    "薪酬",
    "评价",
    "权益分派",
    "资金占用",
    "独立性",
    "履职",
    "会议资料",
    "港股公告",
    "治理报告",
    "法律意见",
    "核查意见",
    "权益变动",
    "说明",
    "工作报告",
    "审核报告",
    "跟踪报告",
    "督导",
    "募集资金",
    "股票期权",
    "归属期",
    "重组",
    "发行",
]


def classify_pdf(filename: str) -> str | None:
    """根据文件名返回目标子目录（相对于 raw/）。返回 None 表示无法分类。"""
    name = filename

    # 1. 招股说明书
    if "招股说明书" in name:
        return "prospectus"

    # 2. 投资者关系（含调研、业绩说明会、投关记录）
    ir_keywords = ["投资者关系", "调研活动", "业绩说明会", "投关记录"]
    if any(kw in name for kw in ir_keywords):
        return "investor_relations"

    # 3. 财报类 — 半年度报告（必须在年度之前检查，因为"半年度报告"包含"年度报告"）
    if "半年度报告" in name or "中报" in name:
        return "financial_reports/semi_annual"

    # 4. 财报类 — 年度报告
    if "年度报告" in name or "年报" in name:
        return "financial_reports/annual"

    # 5. 财报类 — 季度报告
    quarter_patterns = [
        r"季度报告",
        r"一季度报告",
        r"三季度报告",
        r"第一季度",
        r"第三季度",
        r"一季度",
        r"三季度",
        r"Q[1-4]",
        r"[一二三四]季度",
    ]
    for pat in quarter_patterns:
        if re.search(pat, name):
            return "financial_reports/quarterly"

    # 6. 港股公告（仅限非财报类公告，财报已在上面处理）
    if "港股公告" in name:
        return "announcements"

    # 7. 公告类（必须在摘要兜底之前，避免"摘要公告"被错误归类）
    for kw in ANNOUNCEMENT_KEYWORDS:
        if kw in name:
            return "announcements"

    # 8. 摘要兜底 — 只处理真正是财报摘要的文件
    #    如果到这里还没匹配但有"摘要"，通常是年度报告摘要
    if "摘要" in name:
        return "financial_reports/annual"

    # 9. 无法分类 → 归入 announcements（兜底）
    return None


def organize_company(company_dir: Path, dry_run: bool = True) -> list[dict]:
    """整理一家公司的文件。返回操作记录列表。"""
    raw_dir = company_dir / "raw"
    actions = []

    # ── 收集需要移动的文件 ──
    # 1) 公司根目录下的 PDF 文件
    root_pdfs = [f for f in company_dir.iterdir() if f.is_file() and f.suffix == ".pdf"]

    # 2) raw/ 根层下的 PDF 文件（排除已有子目录）
    raw_root_pdfs = []
    if raw_dir.exists():
        for f in raw_dir.iterdir():
            if f.is_file() and f.suffix == ".pdf":
                raw_root_pdfs.append(f)

    all_files = root_pdfs + raw_root_pdfs

    if not all_files:
        return actions

    for src in all_files:
        category = classify_pdf(src.name)
        if category is None:
            # 无法分类，跳过
            actions.append(
                {
                    "action": "SKIP",
                    "src": str(src.relative_to(WIKI_ROOT)),
                    "reason": "无法自动分类",
                }
            )
            continue

        dest_dir = raw_dir / category
        dest = dest_dir / src.name

        # 检查目标是否已存在同名文件
        if dest.exists():
            # 如果源和目标是同一个文件（已经在正确位置），跳过
            if src.resolve() == dest.resolve():
                continue
            # 目标已存在同名文件，检查是否内容一致
            if src.stat().st_size == dest.stat().st_size:
                # 内容一致（大小相同），删除源文件（去重）
                actions.append(
                    {
                        "action": "DEDUP_DELETE",
                        "src": str(src.relative_to(WIKI_ROOT)),
                        "dest": str(dest.relative_to(WIKI_ROOT)),
                        "reason": "目标已存在相同文件，删除重复源文件",
                    }
                )
                if not dry_run:
                    src.unlink()
                continue
            else:
                # 同名但内容不同，添加后缀
                stem = dest.stem
                suffix = dest.suffix
                counter = 1
                while dest.exists():
                    dest = dest_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

        action = "MOVE"
        rel_src = str(src.relative_to(WIKI_ROOT))
        rel_dest = str(dest.relative_to(WIKI_ROOT))

        actions.append(
            {
                "action": action,
                "src": rel_src,
                "dest": rel_dest,
                "category": category,
            }
        )

        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))

    return actions


def main():
    import argparse

    parser = argparse.ArgumentParser(description="归类 companies/ 下散落的文件")
    parser.add_argument(
        "--execute", action="store_true", help="默认 dry-run 模式；加此参数实际执行移动"
    )
    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        print("=" * 60)
        print("  DRY RUN 模式 — 只预览，不实际移动文件")
        print("  加 --execute 参数执行实际操作")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  执行模式 — 将实际移动文件")
        print("=" * 60)

    total_actions = 0
    companies_with_actions = []

    for company_dir in sorted(COMPANIES_DIR.iterdir()):
        if not company_dir.is_dir():
            continue
        if company_dir.name.startswith("_") or company_dir.name.startswith("."):
            continue

        actions = organize_company(company_dir, dry_run=dry_run)

        if actions:
            companies_with_actions.append(company_dir.name)
            print(f"\n{'-' * 50}")
            print(f"[{company_dir.name}/]")
            for a in actions:
                total_actions += 1
                if a["action"] == "SKIP":
                    print(f"  SKIP: {a['src']} -- {a['reason']}")
                elif a["action"] == "DEDUP_DELETE":
                    print(f"  DEDUP: {a['src']} -> exists at {a['dest']}")
                else:
                    print(f"  MOVE: {a['src']}")
                    print(f"     -> {a['dest']}")

    print(f"\n{'=' * 60}")
    print(f"  涉及公司: {len(companies_with_actions)} 家")
    print(f"  操作总数: {total_actions}")
    if dry_run and total_actions > 0:
        print(f"\n  加 --execute 参数执行实际移动操作")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
