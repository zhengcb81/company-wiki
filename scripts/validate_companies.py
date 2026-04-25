#!/usr/bin/env python3
"""
validate_companies.py — 系统性检测 companies.yaml 中的命名歧义问题

检测规则：
1. 名称子串冲突：A 的名称是 B 名称的子串（如 "京东" vs "京东方"）
2. 别名冲突：同一个别名被多家公司使用
3. 查询关键词污染：查询词包含其他公司名/别名
4. 建议修复：为冲突对添加 negative_keywords

用法：
    python scripts/validate_companies.py [--fix]
"""

import argparse
import sys
from pathlib import Path

from common import WIKI_ROOT, COMPANIES_YAML

import yaml


def load_companies():
    with open(COMPANIES_YAML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["companies"]


def check_name_conflicts(companies):
    """检测名称子串冲突（排除已配置 negative_keywords 的）"""
    conflicts = []
    names = sorted(companies.keys(), key=len, reverse=True)
    for i, n1 in enumerate(names):
        for n2 in names[i + 1 :]:
            if n2 in n1 and n1 != n2:
                # 检查较长名称的公司是否已配置 negative_keywords
                neg_kws = [
                    k.lower() for k in companies[n1].get("negative_keywords", [])
                ]
                if n2.lower() in neg_kws:
                    continue  # 已修复，跳过
                conflicts.append(
                    {
                        "type": "substring",
                        "shorter": n2,
                        "longer": n1,
                        "reason": f'"{n2}" 是 "{n1}" 的子串，可能导致误匹配',
                    }
                )
    return conflicts


def check_alias_conflicts(companies):
    """检测别名冲突"""
    aliases = {}
    for name, info in companies.items():
        for alias in info.get("aliases", []):
            aliases.setdefault(alias, []).append(name)

    conflicts = []
    for alias, names in aliases.items():
        if len(names) > 1:
            conflicts.append(
                {
                    "type": "alias_conflict",
                    "alias": alias,
                    "companies": names,
                    "reason": f'别名 "{alias}" 被多家公司使用: {names}',
                }
            )
    return conflicts


def check_query_cross_contamination(companies):
    """检测查询关键词交叉污染（排除已配置 negative_keywords 的）"""
    conflicts = []
    for name, info in companies.items():
        for q in info.get("news_queries", []):
            for other_name, other_info in companies.items():
                if other_name == name:
                    continue
                # 检查是否包含其他公司全名
                if other_name in q:
                    # 如果目标公司已配置 negative_keywords 包含该公司名，视为已修复
                    neg_kws = [k.lower() for k in info.get("negative_keywords", [])]
                    if other_name.lower() in neg_kws:
                        continue
                    conflicts.append(
                        {
                            "type": "query_contains_name",
                            "company": name,
                            "query": q,
                            "contaminated_by": other_name,
                            "reason": f'{name} 的查询 "{q}" 包含其他公司名 "{other_name}"',
                        }
                    )
                    break
                # 检查是否包含其他公司别名
                for alias in other_info.get("aliases", []):
                    if len(alias) > 3 and alias != name and alias in q:
                        # 如果目标公司已配置 negative_keywords 包含该别名，视为已修复
                        neg_kws = [k.lower() for k in info.get("negative_keywords", [])]
                        if alias.lower() in neg_kws:
                            continue
                        conflicts.append(
                            {
                                "type": "query_contains_alias",
                                "company": name,
                                "query": q,
                                "contaminated_by": other_name,
                                "alias": alias,
                                "reason": f'{name} 的查询 "{q}" 包含 {other_name} 的别名 "{alias}"',
                            }
                        )
                        break
    return conflicts


def generate_fixes(conflicts, companies):
    """为冲突生成修复建议"""
    fixes = []
    for c in conflicts:
        if c["type"] == "substring":
            shorter = c["shorter"]
            longer = c["longer"]
            # 建议：在较长名称的公司中添加 negative_keywords
            fixes.append(
                {
                    "company": longer,
                    "action": "add_negative_keywords",
                    "value": [shorter],
                    "reason": f'防止 "{shorter}" 误匹配到 "{longer}" 的内容',
                }
            )
        elif c["type"] == "alias_conflict":
            fixes.append(
                {
                    "companies": c["companies"],
                    "action": "remove_alias",
                    "value": c["alias"],
                    "reason": f'别名 "{c["alias"]}" 被多家公司使用',
                }
            )
        elif c["type"] in ("query_contains_name", "query_contains_alias"):
            fixes.append(
                {
                    "company": c["company"],
                    "action": "modify_query",
                    "value": c["query"],
                    "reason": f"查询词包含其他公司名/别名，建议加限定词",
                }
            )
    return fixes


def apply_fixes(fixes, companies):
    """应用修复（修改 companies dict）"""
    for fix in fixes:
        action = fix["action"]
        if action == "add_negative_keywords":
            company = fix["company"]
            if company in companies:
                nk = companies[company].setdefault("negative_keywords", [])
                for kw in fix["value"]:
                    if kw not in nk:
                        nk.append(kw)
        elif action == "remove_alias":
            for company in fix["companies"]:
                if company in companies:
                    aliases = companies[company].get("aliases", [])
                    if fix["value"] in aliases:
                        aliases.remove(fix["value"])


def main():
    parser = argparse.ArgumentParser(description="检测 companies.yaml 命名歧义")
    parser.add_argument("--fix", action="store_true", help="自动修复可修复的问题")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    companies = load_companies()

    conflicts = []
    conflicts.extend(check_name_conflicts(companies))
    conflicts.extend(check_alias_conflicts(companies))
    conflicts.extend(check_query_cross_contamination(companies))

    fixes = generate_fixes(conflicts, companies)

    if args.json:
        import json

        print(
            json.dumps(
                {"conflicts": conflicts, "fixes": fixes}, ensure_ascii=False, indent=2
            )
        )
        return

    # 打印报告
    print("=" * 60)
    print("  companies.yaml 命名歧义检测报告")
    print("=" * 60)

    if not conflicts:
        print("\n  未发现命名歧义问题。")
        return 0

    print(f"\n  发现 {len(conflicts)} 个问题:\n")

    for c in conflicts:
        print(f"  [{c['type']}] {c['reason']}")

    if fixes:
        print(f"\n  建议修复 ({len(fixes)} 条):\n")
        for f in fixes:
            print(f"  - {f['reason']}")
            if f["action"] == "add_negative_keywords":
                print(f"    -> 在 {f['company']} 添加 negative_keywords: {f['value']}")
            elif f["action"] == "remove_alias":
                print(f"    -> 从 {f.get('companies', [])} 移除别名: {f['value']}")
            elif f["action"] == "modify_query":
                print(f"    -> 修改 {f['company']} 的查询词: {f['value']}")

    if args.fix:
        apply_fixes(fixes, companies)
        with open(COMPANIES_YAML, "w", encoding="utf-8") as f:
            yaml.dump({"companies": companies}, f, allow_unicode=True, sort_keys=False)
        print(f"\n  已自动修复并保存到 {COMPANIES_YAML}")

    print(f"\n{'=' * 60}")
    return 1 if conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
