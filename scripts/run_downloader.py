#!/usr/bin/env python3
"""
run_downloader.py — 批量下载上市公司文档（封装 StockInfoDLSimple）

用法：
    # 下载全部 205 家 A 股公司
    python scripts/run_downloader.py

    # 只下载 Tier 1 核心公司（约 30 家）
    python scripts/run_downloader.py --tier tier1

    # 强制重新下载（清除进度）
    python scripts/run_downloader.py --clean

    # 并行下载（默认 3 个 worker）
    python scripts/run_downloader.py --parallel --workers 5

    # 只下载特定公司
    python scripts/run_downloader.py --company 东方电缆

配置：
    - 使用本目录下的 config_template.json（已验证可用）
    - 使用本目录下的 a_share_companies.txt（205 家 A 股）
    - 下载结果保存到 companies/{公司名}/raw/{类型}/

前置条件：
    1. 本地已安装 StockInfoDLSimple（路径在 config.yaml -> report_downloader.tool_path）
    2. 已安装 Playwright：pip install playwright && playwright install
    3. 建议在有图形界面的 Windows 环境运行（Playwright 需要浏览器）
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── 路径 ──────────────────────────────────
WIKI_ROOT = Path(__file__).parent.parent
COMPANIES_FILE = WIKI_ROOT / "a_share_companies.txt"
CONFIG_FILE = WIKI_ROOT / "config_template.json"
LOG_FILE = WIKI_ROOT / "log.md"

# Tier 1 核心公司（半导体 + 新能源产业链，约 30 家）
TIER1_COMPANIES = {
    "北方华创",
    "中微公司",
    "拓荆科技",
    "盛美上海",
    "华海清科",
    "精测电子",
    "沪硅产业",
    "江丰电子",
    "安集科技",
    "南大光电",
    "华特气体",
    "中芯国际",
    "华虹半导体",
    "长电科技",
    "通富微电",
    "甬矽电子",
    "中际旭创",
    "新易盛",
    "天孚通信",
    "光迅科技",
    "寒武纪",
    "海光信息",
    "景嘉微",
    "英维克",
    "高澜股份",
    "中科曙光",
    "浪潮信息",
    "工业富联",
    "宁德时代",
    "阳光电源",
    "东方电缆",
    "许继电气",
    "三环集团",
    "石英股份",
    "菲利华",
}

# Tier 2 关注公司（其他有实质 wiki 内容的公司）
TIER2_COMPANIES = {
    "中密控股",
    "杭氧股份",
    "双环传动",
    "金禾实业",
    "中大力德",
    "德赛西威",
    "中航电测",
    "弘亚数控",
    "拓尔思",
    "光线传媒",
    "中颖电子",
    "三环集团",
    "丸美股份",
    "久吾高科",
    "五芳斋",
    "亿华通",
    "优利德",
    "兆易创新",
    "光迅科技",
    "八方股份",
    "凯赛生物",
    "分众传媒",
    "华卓精科",
    "华大九天",
    "华锐精密",
    "卓胜微",
    "南大光电",
    "博威合金",
    "古井贡酒",
    "吉比特",
    "商汤科技",
    "国恩股份",
    "埃斯顿",
    "大全能源",
    "天宜上佳",
    "天新药业",
    "太辰光",
    "奥普特",
    "奥来德",
    "妙可蓝多",
    "安博通",
    "安杰思",
    "宋城演艺",
    "密尔克卫",
    "小米集团",
    "山石网科",
    "广州酒家",
    "广联达",
    "康基医疗",
    "开润股份",
    "微创医疗",
    "德林海",
    "快克股份",
    "恒锋工具",
    "惠泰医疗",
    "拓斯达",
    "拼多多",
    "新产业",
    "新华保险",
    "方大特钢",
    "方邦股份",
    "时代新材",
    "时代电气",
    "春秋航空",
    "普门科技",
    "格力电器",
    "桃李面包",
    "欧派家居",
    "歌力思",
    "沃尔德",
    "洋河股份",
    "洽洽食品",
    "派克新材",
    "海康威视",
    "海澜之家",
    "珀莱雅",
    "珂玛科技",
    "申菱环境",
    "百傲化学",
    "百济神州",
    "盛美上海",
    "科大讯飞",
    "索菲亚",
    "紫光股份",
    "绿茵生态",
    "美凯龙",
    "老凤祥",
    "联影医疗",
    "至纯科技",
    "航发动力",
    "航发控制",
    "航发科技",
    "航天发展",
    "芒果超媒",
    "苏博特",
    "苏试试验",
    "贝泰妮",
    "赛轮轮胎",
    "迈瑞医疗",
    "道氏技术",
    "金达莱",
    "长安汽车",
    "长江证券",
    "长电科技",
    "阳光电源",
    "阿拉丁",
    "雅克科技",
    "雪榕生物",
    "飞亚达",
    "飞凯材料",
    "飞龙股份",
    "高澜股份",
    "鼎龙股份",
}


def find_downloader_tool() -> Path:
    """查找 StockInfoDLSimple 安装路径。"""
    # 优先使用新版 v2-clean-rewrite
    candidates = [
        Path("C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite/main.py"),
        Path.home() / "Projects/StockInfoDLSimple/v2-clean-rewrite/main.py",
        Path("C:/StockInfoDLSimple/v2-clean-rewrite/main.py"),
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "StockInfoDLSimple main.py not found. "
        "请确认已安装到 C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite/"
    )


def load_all_companies() -> list:
    """加载全部 205 家 A 股公司列表。"""
    companies = []
    with open(COMPANIES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) >= 1:
                entry = {"stock_code": parts[0]}
                if len(parts) > 1:
                    entry["company_name"] = parts[1]
                companies.append(entry)
    return companies


def filter_companies(
    companies: list, tier: str = None, company_name: str = None
) -> list:
    """按层级或公司名过滤。"""
    if company_name:
        # 查找匹配的公司
        filtered = []
        for c in companies:
            name = c.get("company_name", "")
            if company_name in name or company_name == c["stock_code"]:
                filtered.append(c)
        return filtered

    if tier == "tier1":
        return [c for c in companies if c.get("company_name", "") in TIER1_COMPANIES]
    elif tier == "tier2":
        return [c for c in companies if c.get("company_name", "") in TIER2_COMPANIES]
    elif tier == "tier3":
        tier12 = TIER1_COMPANIES | TIER2_COMPANIES
        return [c for c in companies if c.get("company_name", "") not in tier12]
    else:
        return companies


def append_log(message: str):
    """追加日志到 log.md。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{now}] download_reports | {message}\n"
    if LOG_FILE.exists():
        content = LOG_FILE.read_text(encoding="utf-8")
    else:
        content = "# 知识库操作日志\n"
    content += entry
    LOG_FILE.write_text(content, encoding="utf-8")


def run_downloader(
    companies_file: Path, clean: bool = False, parallel: bool = False, workers: int = 3
):
    """调用 StockInfoDLSimple 下载。"""
    main_py = find_downloader_tool()
    tool_dir = main_py.parent

    cmd = [
        sys.executable,
        str(main_py),
        "--config",
        str(CONFIG_FILE.absolute()),
        "--companies",
        str(companies_file.absolute()),
    ]
    if clean:
        cmd.append("--clean")
    if parallel:
        cmd.append("--parallel")
        cmd.extend(["--workers", str(workers)])

    print(f"Executing: {' '.join(cmd)}")
    print(f"Working directory: {tool_dir}")
    print()

    try:
        result = subprocess.run(
            cmd,
            cwd=str(tool_dir),
            check=False,  # 我们自己处理返回码
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("ERROR: Python executable or main.py not found")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="批量下载上市公司文档")
    parser.add_argument(
        "--tier",
        choices=["tier1", "tier2", "tier3", "all"],
        default="all",
        help="下载层级 (默认: all)",
    )
    parser.add_argument("--company", type=str, help="只下载指定公司（代码或名称）")
    parser.add_argument("--clean", action="store_true", help="清除进度，强制重新下载")
    parser.add_argument("--parallel", action="store_true", help="启用并行下载")
    parser.add_argument(
        "--workers", type=int, default=3, help="并行 worker 数量 (默认: 3)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="只显示将要下载的公司列表，不执行"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  上市公司文档批量下载")
    print("  Tool: StockInfoDLSimple v2-clean-rewrite")
    print("=" * 60)

    # 加载公司列表
    all_companies = load_all_companies()
    companies = filter_companies(all_companies, args.tier, args.company)

    if not companies:
        print("\nERROR: 没有匹配的公司")
        return

    print(f"\n总计公司: {len(all_companies)}")
    print(f"本次下载: {len(companies)} 家")
    print(f"层级过滤: {args.tier}")
    print(f"并行模式: {'是' if args.parallel else '否'} (workers={args.workers})")
    print(f"清除进度: {'是' if args.clean else '否'}")
    print()

    # 显示前 10 家
    print("公司列表（前 10 家）:")
    for c in companies[:10]:
        print(f"  {c['stock_code']:>8}  {c.get('company_name', 'N/A')}")
    if len(companies) > 10:
        print(f"  ... 还有 {len(companies) - 10} 家")

    if args.dry_run:
        print("\n[dry-run] 跳过实际下载")
        return

    # 写入临时公司列表文件
    temp_file = WIKI_ROOT / ".download_temp_companies.txt"
    with open(temp_file, "w", encoding="utf-8") as f:
        for c in companies:
            name = c.get("company_name", "")
            f.write(f"{c['stock_code']} {name}\n")

    try:
        # 执行下载
        print("\n开始下载...")
        success = run_downloader(temp_file, args.clean, args.parallel, args.workers)

        # 记录日志
        status = "成功" if success else "失败"
        append_log(f"下载 {len(companies)} 家公司文档 ({args.tier}) — {status}")

        print(f"\n{'=' * 60}")
        print(f"  下载完成: {status}")
        print("  文件保存到: companies/{公司名}/raw/")
        print(f"{'=' * 60}")

    finally:
        # 清理临时文件
        if temp_file.exists():
            temp_file.unlink()


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    main()
