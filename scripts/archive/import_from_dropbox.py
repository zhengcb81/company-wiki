#!/usr/bin/env python3
"""
从 Dropbox/Stock 导入公司研究文档到知识库。

功能：
1. 递归扫描 Stock 目录，识别以公司名命名的子目录
2. 检查公司是否在项目公司名单中，不在则新建目录结构
3. 将文档按类型分类拷贝到对应的 raw/ 子目录
4. 基于 SHA256 hash 去重，不重复拷贝已有文件
"""

import hashlib
import os
import re
import shutil
from pathlib import Path

# ── 路径配置 ─────────────────────────────────────────────
WIKI_ROOT = Path(r"C:\Users\郑曾波\Projects\company-wiki")
COMPANIES_DIR = WIKI_ROOT / "companies"
STOCK_ROOT = Path("C:/Users/郑曾波/Dropbox/Stock")

# ── 文件分类规则 ─────────────────────────────────────────
# 基于文件名关键词判断文件类型
FINANCIAL_REPORT_KEYWORDS = [
    "年度报告", "年报", "半年度报告", "中报", "季度报告",
    "一季度报告", "三季度报告", "第一季度", "第三季度",
]
INVESTOR_RELATIONS_KEYWORDS = [
    "投资者关系", "调研活动", "业绩说明会", "投关记录",
    "调研纪要", "交流纪要", "电话会议",
]
PROSPECTUS_KEYWORDS = [
    "招股说明书", "IPO",
]

# ── 已知行业/主题目录名（非公司名）──────────────────────────
KNOWN_SECTOR_DIRS = {
    # 一级行业
    "互联网", "交通运输物流", "工程与建筑", "化工", "工业与信息化",
    "宏观", "房地产", "教育", "新材料", "旅游", "军工", "农业",
    "能源与环境", "消费品", "策略", "纺织", "金融", "金属及加工",
    "安防", "其他", "文化传媒电影", "医药与健康", "多级市场", "重点关注",
    # 二级细分行业
    "短视频", "移动互联网", "电商与零售", "物联网",
    "汽车及零部件", "物流及生产性服务业", "航空", "铁路", "轮胎",
    "建材", "检测与设计", "水泥", "防水",
    "电子化工", "石化",
    "AI", "云计算与边缘计算", "刀具", "工业服务", "显示面板",
    "智能制造与工业互联网", "机器人", "机械设备", "检测",
    "燃料电池", "电子", "网络安全", "软件与自动化控制", "自动化控制",
    "航天", "海军", "航空",
    "医疗信息化", "医疗器械", "医疗服务", "医疗美容", "制药", "合成生物",
    "储能", "新能源", "核能", "氢能", "石油天然气_传统能源",
    "资源_环境_水", "天然气",
    "出行装备", "化妆品", "宠物食品", "家具", "家电", "床垫",
    "服装", "母婴用品", "珠宝", "电子烟", "钟表", "食品饮料",
    "保险", "有色金属", "钢铁", "机床", "轴承",
    "VRAR", "云游戏", "元宇宙",
    "酒店", "商业地产",
    "对冲基金", "量化交易_Quant",
    "IB statements",
    "A股投资启示录", "A股涅槃论", "专精特新", "中国优势制造",
    "中国股市行业轮动启示录", "产业之思", "产业链研究的跬步",
    "供应链安全", "出海", "十倍股", "十论复苏牛",
    "华泰行业基本面轮动", "周期转型与投资时钟", "基本面量化",
    "复盘", "宏观伴读", "广开金股", "成长股", "护城河",
    "深挖财报", "策略研究视角的财务选股", "自由现金流",
    "行业比较新视野", "选股",
    "手术机器人", "糖尿病专题",
    "金刚石", "智能汽车",
    # 三级时间/主题目录
    "2011年中期", "2011年二季度", "云卷云舒", "周期复辟",
    "寻找中国成长的线索", "结构主义", "花开花谢", "过渡.变革.中坚",
    "产业之思2022",
    "CPPI", "基础因子研究",
    "金山系",
    ".claude",
}


def sha256_file(path: Path) -> str:
    """计算文件的 SHA256 hash。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def is_company_directory(dirpath: Path) -> bool:
    """
    判断一个目录是否是公司目录（而非行业/主题目录）。
    规则：
    1. 目录名不在已知行业名列表中
    2. 目录下有 PDF 文件
    3. PDF 文件名中包含目录名（研究报报告通常含公司名）
    """
    dirname = dirpath.name

    # 明确排除已知行业目录
    if dirname in KNOWN_SECTOR_DIRS:
        return False

    # 没有PDF文件，不是公司目录
    pdfs = list(dirpath.glob("*.pdf"))
    if not pdfs:
        return False

    # 检查 PDF 文件名中是否包含目录名
    # 研究报告格式通常为：YYYYMMDD-券商-公司名-股票代码-标题.pdf
    match_count = 0
    for pdf in pdfs[:10]:
        if dirname in pdf.name:
            match_count += 1

    # 至少有一半的 PDF 文件名包含目录名，认为是公司目录
    # 或者目录下没有子目录（叶子节点）且有少量PDF
    has_subdirs = any(d.is_dir() for d in dirpath.iterdir())
    if not has_subdirs and pdfs:
        # 叶子目录有PDF，如果文件名匹配也算
        return match_count >= 1

    return match_count >= len(pdfs[:10]) * 0.3


def classify_file(filename: str) -> str:
    """根据文件名判断文件应归入哪个子目录。"""
    name = filename

    # 招股说明书
    for kw in PROSPECTUS_KEYWORDS:
        if kw in name:
            return "prospectus"

    # 投资者关系
    for kw in INVESTOR_RELATIONS_KEYWORDS:
        if kw in name:
            return "investor_relations"

    # 财报（注意半年度要在年度之前匹配）
    if "半年度报告" in name or "中报" in name:
        return "financial_reports/semi_annual"
    if "年度报告" in name or "年报" in name:
        return "financial_reports/annual"
    for pat in ["季度报告", "一季度报告", "三季度报告", "第一季度", "第三季度"]:
        if pat in name:
            return "financial_reports/quarterly"

    # 其余全部归入 research
    return "research"


def get_existing_companies() -> set[str]:
    """获取项目中已有的公司名列表。"""
    companies = set()
    if not COMPANIES_DIR.exists():
        return companies
    for d in COMPANIES_DIR.iterdir():
        if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_"):
            companies.add(d.name)
    return companies


def create_company_dirs(company_name: str) -> Path:
    """为公司创建标准目录结构。返回公司根目录。"""
    company_dir = COMPANIES_DIR / company_name
    company_dir.mkdir(parents=True, exist_ok=True)
    (company_dir / "raw" / "financial_reports" / "annual").mkdir(parents=True, exist_ok=True)
    (company_dir / "raw" / "financial_reports" / "semi_annual").mkdir(parents=True, exist_ok=True)
    (company_dir / "raw" / "financial_reports" / "quarterly").mkdir(parents=True, exist_ok=True)
    (company_dir / "raw" / "news").mkdir(parents=True, exist_ok=True)
    (company_dir / "raw" / "investor_relations").mkdir(parents=True, exist_ok=True)
    (company_dir / "raw" / "prospectus").mkdir(parents=True, exist_ok=True)
    (company_dir / "raw" / "research").mkdir(parents=True, exist_ok=True)
    (company_dir / "wiki").mkdir(parents=True, exist_ok=True)
    return company_dir


def build_hash_index(company_name: str) -> dict[str, Path]:
    """
    为一个公司目录下所有文件建立 hash → path 索引。
    用于快速判断文件是否已存在。
    """
    index = {}
    company_dir = COMPANIES_DIR / company_name
    if not company_dir.exists():
        return index

    for f in company_dir.rglob("*"):
        if f.is_file() and f.suffix in (".pdf", ".md"):
            try:
                h = sha256_file(f)
                index[h] = f
            except (OSError, PermissionError):
                pass
    return index


def import_company(src_dir: Path, company_name: str,
                   existing_companies: set[str],
                   dry_run: bool = True) -> list[dict]:
    """导入一个公司目录下的所有文档。"""
    actions = []

    # 1. 检查公司是否存在，不存在则新建
    is_new = company_name not in existing_companies
    if is_new:
        actions.append({
            "action": "NEW_COMPANY",
            "company": company_name,
        })
        if not dry_run:
            create_company_dirs(company_name)
            existing_companies.add(company_name)

    # 2. 建立 hash 索引（用于去重）
    if not dry_run:
        hash_index = build_hash_index(company_name)
    else:
        hash_index = {}

    # 3. 遍历源目录下的所有文件
    company_dir = COMPANIES_DIR / company_name
    for src_file in sorted(src_dir.rglob("*")):
        if not src_file.is_file():
            continue
        if src_file.suffix not in (".pdf", ".md", ".doc", ".docx", ".xlsx", ".pptx"):
            continue
        if src_file.name.startswith(".") or src_file.name.startswith("~"):
            continue

        # 分类
        category = classify_file(src_file.name)
        dest_dir = company_dir / "raw" / category
        dest_file = dest_dir / src_file.name

        # 去重：检查 hash
        if not dry_run:
            src_hash = sha256_file(src_file)

            # 先检查目标路径是否存在同名文件
            if dest_file.exists():
                dest_hash = sha256_file(dest_file)
                if dest_hash == src_hash:
                    actions.append({
                        "action": "SKIP_DUP",
                        "src": str(src_file.relative_to(STOCK_ROOT)),
                        "dest": str(dest_file.relative_to(WIKI_ROOT)),
                        "reason": "目标已存在相同内容文件",
                    })
                    continue
                else:
                    # 同名不同内容，加后缀
                    counter = 1
                    stem = dest_file.stem
                    suffix = dest_file.suffix
                    while dest_file.exists():
                        dest_file = dest_dir / f"{stem}_{counter}{suffix}"
                        counter += 1

            # 再检查 hash 索引（文件可能以不同名字存在）
            if src_hash in hash_index:
                existing_path = hash_index[src_hash]
                actions.append({
                    "action": "SKIP_DUP_HASH",
                    "src": str(src_file.relative_to(STOCK_ROOT)),
                    "existing": str(existing_path.relative_to(WIKI_ROOT)),
                    "reason": f"hash相同，文件已存在于 {existing_path.name}",
                })
                continue

            # 拷贝
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_file), str(dest_file))
            hash_index[src_hash] = dest_file
            actions.append({
                "action": "COPY",
                "src": str(src_file.relative_to(STOCK_ROOT)),
                "dest": str(dest_file.relative_to(WIKI_ROOT)),
                "category": category,
            })
        else:
            # Dry run - 简化处理，只检查文件名
            actions.append({
                "action": "WOULD_COPY",
                "src": str(src_file.relative_to(STOCK_ROOT)),
                "dest": str(dest_file.relative_to(WIKI_ROOT)),
                "category": category,
                "is_new_company": is_new,
            })

    return actions


def scan_company_dirs() -> list[tuple[str, Path]]:
    """扫描 Stock 目录，返回所有公司目录及其路径。"""
    results = []

    for root, dirs, files in os.walk(STOCK_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        dirpath = Path(root)

        if is_company_directory(dirpath):
            results.append((dirpath.name, dirpath))

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="从 Dropbox/Stock 导入公司研究文档")
    parser.add_argument("--execute", action="store_true",
                        help="默认 dry-run；加此参数实际执行拷贝")
    parser.add_argument("--company", type=str, default=None,
                        help="只导入指定公司（支持逗号分隔多个）")
    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        print("=" * 60)
        print("  DRY RUN -- preview only, no files copied")
        print("  Add --execute to actually copy files")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  EXECUTE MODE -- files will be copied")
        print("=" * 60)

    # 扫描公司目录
    print("\nScanning Stock directory for company folders...")
    company_dirs = scan_company_dirs()
    print(f"Found {len(company_dirs)} company directories\n")

    # 获取已有公司列表
    existing_companies = get_existing_companies()
    print(f"Existing companies in project: {len(existing_companies)}")

    # 过滤
    if args.company:
        filter_names = set(args.company.split(","))
        company_dirs = [(n, p) for n, p in company_dirs if n in filter_names]
        print(f"Filtered to: {filter_names}")

    # 统计
    new_companies = []
    existing_matches = []
    total_copies = 0
    total_skips = 0

    for company_name, src_dir in sorted(company_dirs):
        is_new = company_name not in existing_companies

        actions = import_company(src_dir, company_name, existing_companies, dry_run)

        if not actions:
            continue

        print(f"\n{'-' * 50}")
        label = "NEW" if is_new else "EXISTS"
        print(f"[{label}] {company_name}/  ({src_dir.relative_to(STOCK_ROOT)})")

        for a in actions:
            if a["action"] == "NEW_COMPANY":
                new_companies.append(company_name)
                print(f"  + New company, will create directory structure")

            elif a["action"] in ("COPY", "WOULD_COPY"):
                total_copies += 1
                cat = a.get("category", "?")
                print(f"  COPY [{cat}]: {Path(a['src']).name}")

            elif a["action"] in ("SKIP_DUP", "SKIP_DUP_HASH"):
                total_skips += 1
                # 不逐条打印去重，太多了

        if not is_new:
            existing_matches.append(company_name)

    # 汇总
    print(f"\n{'=' * 60}")
    print(f"  New companies to add: {len(new_companies)}")
    for c in sorted(new_companies):
        print(f"    + {c}")
    print(f"  Existing companies matched: {len(existing_matches)}")
    print(f"  Files to copy: {total_copies}")
    print(f"  Files skipped (duplicate): {total_skips}")
    if dry_run and (total_copies > 0 or new_companies):
        print(f"\n  Add --execute to actually copy files")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
