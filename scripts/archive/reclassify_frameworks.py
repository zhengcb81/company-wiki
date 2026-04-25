#!/usr/bin/env python3
"""
将 半导体材料/raw/ 中被错误归类的框架文档重新分类到正确的 sector。
"""

import os
import shutil
from pathlib import Path

SECTORS_DIR = Path("C:/Users/郑曾波/Projects/company-wiki/sectors")

# ── 文件名关键词 → 正确的 sector ────────────────────────
# 按优先级排列，先匹配更具体的
RECLASSIFY_RULES: list[tuple[str, str]] = [
    # 芯片设计类 → 新建 "芯片设计" sector
    ("CPU研究框架", "芯片设计"),
    ("CPU，研究框架", "芯片设计"),
    ("国产CPU", "芯片设计"),
    ("服务器CPU", "芯片设计"),
    ("GPU研究框架", "GPU与AI芯片"),
    ("GPU框架", "GPU与AI芯片"),
    ("FPGA研究框架", "芯片设计"),
    ("MCU深度报告", "芯片设计"),
    ("微控制器研究框架", "芯片设计"),
    ("SoC芯片", "芯片设计"),
    ("AIoT芯片", "芯片设计"),
    ("模拟芯片", "芯片设计"),
    ("基带芯片", "芯片设计"),
    ("存储芯片", "芯片设计"),
    ("NOR深度报告", "芯片设计"),
    ("DRAM深度", "芯片设计"),
    ("射频PA", "芯片设计"),
    ("MOSFET", "芯片设计"),
    ("射频前端滤波器", "芯片设计"),
    ("IGBT", "芯片设计"),
    # IP/EDA → 已有 sector
    ("IP研究框架", "EDA与IP"),
    ("EDA行业", "EDA与IP"),
    # 设备类 → 已有 sector
    ("光刻机", "光刻设备"),
    ("刻蚀机", "刻蚀设备"),
    ("半导体设备", "半导体设备"),
    ("测试行业", "量检测设备"),
    # 材料类 → 留在原处
    ("半导体材料", "半导体材料"),
    ("大硅片", "硅片"),
    ("电子气体", "电子特气"),
    ("被动元器件", "半导体材料"),
    # 第三代半导体 / 化合物半导体 → 留在材料
    ("SiC研究框架", "半导体材料"),
    ("GaN研究框架", "半导体材料"),
    ("III_V族", "半导体材料"),
    ("化合物半导体", "半导体材料"),
    # 封装
    ("TSV", "封测"),
]

def classify_file(filename: str) -> str | None:
    """返回目标 sector，或 None 表示留在原处（半导体材料）。"""
    for keyword, sector in RECLASSIFY_RULES:
        if keyword in filename:
            return sector
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    dry_run = not args.execute

    if dry_run:
        print("=" * 60)
        print("  DRY RUN -- preview only")
        print("  Add --execute to actually move")
        print("=" * 60)

    src_dir = SECTORS_DIR / "半导体材料" / "raw"

    # 只处理含"框架"的文件
    framework_files = [f for f in os.listdir(src_dir) if "框架" in f and f.endswith(".pdf")]

    moves: dict[str, list[str]] = {}   # sector → [filenames]
    stays: list[str] = []

    for fname in sorted(framework_files):
        target = classify_file(fname)
        if target and target != "半导体材料":
            moves.setdefault(target, []).append(fname)
        else:
            stays.append(fname)

    total_moves = sum(len(v) for v in moves.values())

    print(f"\nFramework files in 半导体材料/raw/: {len(framework_files)}")
    print(f"Will reclassify: {total_moves}")
    print(f"Will stay: {len(stays)}")

    for sector in sorted(moves.keys()):
        files = moves[sector]
        target_dir = SECTORS_DIR / sector / "raw"
        is_new = not (SECTORS_DIR / sector).exists()

        print(f"\n{'-' * 50}")
        label = "NEW SECTOR" if is_new else sector
        print(f"[{label}] {sector}/ ({len(files)} files)")

        for fname in files:
            src_file = src_dir / fname
            dest_file = target_dir / fname

            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
                sector_dir = SECTORS_DIR / sector
                if not (sector_dir / "wiki").exists():
                    (sector_dir / "wiki").mkdir(parents=True, exist_ok=True)

                # 检查目标是否已存在
                if dest_file.exists():
                    print(f"  SKIP (exists): {fname}")
                else:
                    shutil.move(str(src_file), str(dest_file))
                    print(f"  MOVED: {fname}")
            else:
                print(f"  {fname}")

    if stays:
        print(f"\n{'-' * 50}")
        print(f"Staying in 半导体材料/ ({len(stays)} files):")
        for f in stays:
            print(f"  {f}")

    print(f"\n{'=' * 60}")
    print(f"  Reclassified: {total_moves} files")
    print(f"  New sectors: {sum(1 for s in moves if not (SECTORS_DIR / s).exists())}")
    print(f"  Stayed in 半导体材料: {len(stays)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
