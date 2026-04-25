#!/usr/bin/env python3
"""
从 Dropbox/Stock 中找出所有含"框架"的研究文档，
按源目录的行业分类拷贝到项目 sectors/ 对应子目录。
目标子目录不存在则创建。基于 SHA256 去重。
"""

import hashlib
import os
import shutil
from pathlib import Path

STOCK_ROOT = Path("C:/Users/郑曾波/Dropbox/Stock")
SECTORS_DIR = Path("C:/Users/郑曾波/Projects/company-wiki/sectors")

# ── 源路径 → 目标 sector 名称映射 ──────────────────────
# 格式：(路径中需包含的关键词列表, 目标sector名)
# 从具体到宽泛排列，先命中的生效
PATH_TO_SECTOR: list[tuple[list[str], str]] = [
    # ── 已有 sector 的直接映射 ──
    (["工业与信息化", "电子"], "半导体材料"),
    (["工业与信息化", "AI"], "AI应用"),
    (["工业与信息化", "智能制造"], "半导体设备"),
    (["工业与信息化", "机器人"], "半导体设备"),
    (["工业与信息化", "检测"], "量检测设备"),
    (["工业与信息化", "燃料电池"], "储能"),
    (["化工", "电子化工"], "电子特气"),
    (["能源与环境", "储能"], "储能"),
    (["能源与环境", "核"], "发电设备"),
    (["能源与环境", "氢能"], "储能"),
    # ── 新建 sector：直接用行业名 ──
    (["互联网", "电商与零售"], "电商与零售"),
    (["互联网", "短视频"], "短视频"),
    (["互联网", "移动互联网"], "互联网平台"),
    (["互联网", "物联网"], "互联网平台"),
    (["互联网"], "互联网"),
    (["交通运输物流", "汽车"], "汽车"),
    (["交通运输物流", "物流"], "物流"),
    (["交通运输物流", "航空"], "航空"),
    (["交通运输物流", "铁路"], "铁路"),
    (["交通运输物流"], "交运物流"),
    (["军工", "航天"], "军工"),
    (["军工", "航空"], "军工"),
    (["军工"], "军工"),
    (["化工"], "化工"),
    (["医药与健康", "制药"], "医药"),
    (["医药与健康", "医疗器械"], "医疗器械"),
    (["医药与健康", "医疗信息化"], "医疗信息化"),
    (["医药与健康", "医疗美容"], "医美"),
    (["医药与健康", "医疗服务"], "医疗服务"),
    (["医药与健康", "合成生物"], "合成生物"),
    (["医药与健康"], "医药"),
    (["多级市场", "量化交易"], "量化投资"),
    (["多级市场", "对冲基金"], "量化投资"),
    (["多级市场"], "量化投资"),
    (["宏观"], "宏观研究"),
    (["工业与信息化", "刀具"], "刀具"),
    (["工业与信息化", "工业服务"], "工业服务"),
    (["工业与信息化", "显示面板"], "显示面板"),
    (["工业与信息化", "机械设备"], "机械设备"),
    (["工业与信息化", "网络安全"], "网络安全"),
    (["工业与信息化", "软件"], "软件与IT"),
    (["工业与信息化", "船舶"], "船舶"),
    (["工业与信息化"], "工业与信息化"),
    (["工程与建筑"], "工程与建筑"),
    (["房地产"], "房地产"),
    (["教育"], "教育"),
    (["文化传媒电影", "VRAR"], "VR与元宇宙"),
    (["文化传媒电影", "元宇宙"], "VR与元宇宙"),
    (["文化传媒电影"], "文化传媒"),
    (["新材料"], "新材料"),
    (["旅游", "酒店"], "酒店与旅游"),
    (["旅游"], "酒店与旅游"),
    (["消费品", "家具"], "家具"),
    (["消费品", "食品饮料"], "食品饮料"),
    (["消费品", "化妆品"], "化妆品"),
    (["消费品", "珠宝"], "珠宝"),
    (["消费品", "服装"], "服装"),
    (["消费品"], "消费品"),
    (["策略"], "策略研究"),
    (["纺织"], "纺织"),
    (["金融", "保险"], "保险"),
    (["金融"], "金融"),
    (["金属及加工"], "金属与材料"),
    (["安防"], "安防"),
    (["能源与环境", "石油天然气"], "传统能源"),
    (["能源与环境", "资源"], "环保"),
    (["能源与环境"], "能源与环境"),
    (["其他"], "策略研究"),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def determine_sector(rel_path: str) -> str:
    """根据文件在 Stock 中的相对路径确定 sector。"""
    parts = [p.replace("\\", "/") for p in Path(rel_path).parts]
    path_str = "/".join(parts)

    for keywords, sector in PATH_TO_SECTOR:
        key_str = "/".join(keywords)
        if key_str in path_str:
            return sector

    # Fallback：用路径第一层目录名
    return Path(rel_path).parts[0]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    dry_run = not args.execute

    if dry_run:
        print("=" * 60)
        print("  DRY RUN -- preview only")
        print("  Add --execute to actually copy")
        print("=" * 60)

    # 扫描
    files = []
    for root, dirs, fnames in os.walk(STOCK_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in fnames:
            if "框架" in f and f.endswith(".pdf"):
                src = Path(root) / f
                rel = str(src.relative_to(STOCK_ROOT))
                sector = determine_sector(rel)
                files.append((sector, src, rel))

    print(f"\nFound {len(files)} framework documents\n")

    # 按 sector 分组
    sector_files: dict[str, list[tuple[Path, str]]] = {}
    for sector, src, rel in files:
        sector_files.setdefault(sector, []).append((src, rel))

    total_copy = 0
    total_skip = 0
    new_sectors = []

    for sector in sorted(sector_files.keys()):
        items = sector_files[sector]
        target_dir = SECTORS_DIR / sector / "raw"
        sector_dir = SECTORS_DIR / sector
        is_new = not sector_dir.exists()

        print(f"{'-' * 50}")
        label = "NEW" if is_new else "EXISTS"
        print(f"[{label}] {sector}/ ({len(items)} files)")

        if is_new:
            new_sectors.append(sector)

        # 建目标 hash 索引
        hash_index: dict[str, Path] = {}
        if target_dir.exists():
            for f in target_dir.rglob("*.pdf"):
                try:
                    h = sha256_file(f)
                    hash_index[h] = f
                except (OSError, PermissionError):
                    pass

        for src, rel in items:
            if not dry_run:
                try:
                    src_hash = sha256_file(src)
                except (OSError, PermissionError):
                    print(f"  SKIP: {src.name}")
                    total_skip += 1
                    continue

                if src_hash in hash_index:
                    total_skip += 1
                    continue

                target_file = target_dir / src.name
                if target_file.exists():
                    stem, suffix = target_file.stem, target_file.suffix
                    c = 1
                    while target_file.exists():
                        target_file = target_dir / f"{stem}_{c}{suffix}"
                        c += 1

                target_dir.mkdir(parents=True, exist_ok=True)
                if not (sector_dir / "wiki").exists():
                    (sector_dir / "wiki").mkdir(parents=True, exist_ok=True)

                shutil.copy2(str(src), str(target_file))
                hash_index[src_hash] = target_file
                total_copy += 1
                print(f"  COPY: {src.name}")
            else:
                total_copy += 1
                print(f"  {src.name}")

    print(f"\n{'=' * 60}")
    print(f"  Sectors: {len(sector_files)} (new: {len(new_sectors)})")
    for s in sorted(new_sectors):
        print(f"    + {s}")
    print(f"  Copied: {total_copy}")
    print(f"  Skipped (dup): {total_skip}")
    if dry_run:
        print(f"\n  Add --execute to actually copy files")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
