#!/usr/bin/env python3
"""
fix_encoding.py — 编码修复工具

扫描所有 raw markdown 文件，检测 GBK-as-UTF-8 乱码，
尝试用 charset_normalizer 重新解码，生成修复版本供人工审查。

用法：
    python3 scripts/fix_encoding.py                    # 扫描所有文件
    python3 scripts/fix_encoding.py --company 中微公司  # 只扫描指定公司
    python3 scripts/fix_encoding.py --fix               # 尝试修复
    python3 scripts/fix_encoding.py --fix --execute      # 实际覆盖原文件
"""

import argparse
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent


def has_mojibake(text):
    """检测文本是否包含 GBK-as-UTF-8 乱码特征"""
    if not text:
        return False
    # Unicode replacement character
    if '\ufffd' in text:
        return True
    # 拉丁扩展字符连续出现（GBK 误读为 UTF-8 的典型模式）
    if re.search(r'[\u00c0-\u00ff]{4,}', text):
        return True
    # 控制字符混入（GBK 字节被误解析）
    if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]{3,}', text):
        return True
    return False


def try_fix_encoding(raw_bytes):
    """
    尝试用 charset_normalizer 修复编码。
    返回: (decoded_text, detected_encoding) 或 (None, None)
    """
    try:
        from charset_normalizer import from_bytes
    except ImportError:
        # 回退：手动尝试常见中文编码
        for encoding in ['gbk', 'gb18030', 'big5', 'gb2312']:
            try:
                decoded = raw_bytes.decode(encoding)
                if decoded and not has_mojibake(decoded):
                    return decoded, encoding
            except (UnicodeDecodeError, LookupError):
                continue
        return None, None

    results = from_bytes(raw_bytes)
    if results:
        best = results.best()
        if best and best.encoding and best.encoding.lower() not in ('utf-8', 'ascii'):
            decoded = str(best)
            if not has_mojibake(decoded):
                return decoded, best.encoding
    return None, None


def scan_file(file_path):
    """
    扫描单个文件的编码状态。
    返回: dict with path, status, details
    """
    raw = file_path.read_bytes()

    # 先尝试 UTF-8
    try:
        text = raw.decode('utf-8')
        if not has_mojibake(text):
            return {"path": str(file_path), "status": "ok", "encoding": "utf-8"}
        # UTF-8 解码成功但有乱码
        return {"path": str(file_path), "status": "mojibake_in_utf8", "encoding": "utf-8"}
    except UnicodeDecodeError:
        pass

    # UTF-8 解码失败，尝试其他编码
    decoded, enc = try_fix_encoding(raw)
    if decoded:
        return {
            "path": str(file_path),
            "status": "wrong_encoding",
            "detected_encoding": enc,
            "can_fix": True
        }

    return {"path": str(file_path), "status": "unreadable", "can_fix": False}


def main():
    parser = argparse.ArgumentParser(description="编码修复工具")
    parser.add_argument("--company", type=str, help="只扫描指定公司")
    parser.add_argument("--fix", action="store_true", help="尝试修复")
    parser.add_argument("--execute", action="store_true", help="实际覆盖原文件")
    args = parser.parse_args()

    print("=" * 60)
    print("  编码修复工具")
    print("=" * 60)

    # 收集要扫描的目录
    scan_dirs = []
    companies_dir = WIKI_ROOT / "companies"

    if args.company:
        company_dir = companies_dir / args.company
        if company_dir.exists():
            scan_dirs.append(company_dir)
        else:
            print(f"  Company not found: {args.company}")
            sys.exit(1)
    else:
        scan_dirs.append(companies_dir)
        if (WIKI_ROOT / "sectors").exists():
            scan_dirs.append(WIKI_ROOT / "sectors")
        if (WIKI_ROOT / "themes").exists():
            scan_dirs.append(WIKI_ROOT / "themes")

    # 扫描所有 .md 文件
    ok_count = 0
    mojibake_count = 0
    wrong_enc_count = 0
    unreadable_count = 0
    fixed_count = 0
    problems = []

    for scan_dir in scan_dirs:
        for md_file in scan_dir.rglob("*.md"):
            # 跳过 wiki 目录下的文件（那些是生成的，不需要修复）
            if "/wiki/" in str(md_file) or "\\wiki\\" in str(md_file):
                continue

            result = scan_file(md_file)

            if result["status"] == "ok":
                ok_count += 1
            elif result["status"] == "mojibake_in_utf8":
                mojibake_count += 1
                problems.append(result)
            elif result["status"] == "wrong_encoding":
                wrong_enc_count += 1
                problems.append(result)
            elif result["status"] == "unreadable":
                unreadable_count += 1
                problems.append(result)

    # 输出报告
    print(f"\n  扫描结果:")
    print(f"    正常 (UTF-8):       {ok_count}")
    print(f"    UTF-8 含乱码:       {mojibake_count}")
    print(f"    编码错误:           {wrong_enc_count}")
    print(f"    无法读取:           {unreadable_count}")
    print(f"    总问题文件:         {len(problems)}")

    if problems:
        print(f"\n  问题文件列表:")
        for p in problems[:30]:
            rel = Path(p["path"]).relative_to(WIKI_ROOT)
            status = p["status"]
            enc = p.get("detected_encoding", "")
            print(f"    [{status}] {rel}" + (f" (detected: {enc})" if enc else ""))

    # 修复
    if args.fix and problems:
        fixable = [p for p in problems if p.get("can_fix")]
        print(f"\n  可修复文件: {len(fixable)}")

        for p in fixable:
            file_path = Path(p["path"])
            raw = file_path.read_bytes()
            decoded, enc = try_fix_encoding(raw)

            if decoded:
                rel = file_path.relative_to(WIKI_ROOT)
                if args.execute:
                    # 备份原文件
                    backup = file_path.with_suffix(f".{enc}.bak")
                    backup.write_bytes(raw)
                    # 写入修复后的内容
                    file_path.write_text(decoded, encoding="utf-8")
                    print(f"    FIXED: {rel} ({enc} -> utf-8, backup: {backup.name})")
                    fixed_count += 1
                else:
                    print(f"    WOULD FIX: {rel} ({enc} -> utf-8)")

    print(f"\n{'=' * 60}")
    if args.fix and not args.execute:
        print("  Use --execute to actually fix files")
    if fixed_count > 0:
        print(f"  Fixed: {fixed_count} files")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
