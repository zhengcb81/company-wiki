#!/usr/bin/env python3
"""
lint.py — 知识库健康检查模块
定期检查 wiki 的健康状态，发现问题并报告。

用法：
    python3 scripts/lint.py                    # 完整检查
    python3 scripts/lint.py --check stale      # 只检查过时页面
    python3 scripts/lint.py --check orphans    # 只检查孤儿页面
    python3 scripts/lint.py --check quality    # 只检查质量
    python3 scripts/lint.py --fix              # 自动修复可修复的问题

检查项：
    1. 过时：页面长期未更新
    2. 孤儿：页面没有被其他页面引用
    3. 空页面：时间线没有条目的页面
    4. 质量：摘要质量统计
    5. 配置一致性：config.yaml 与目录结构是否匹配
    6. 引用完整性：wiki 中的来源链接是否有效
"""

import argparse
import glob
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
CONFIG_PATH = WIKI_ROOT / "config.yaml"
LOG_PATH = WIKI_ROOT / "log.md"


def load_config():
    import yaml
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class LintResult:
    def __init__(self):
        self.issues = []
        self.stats = {}

    def add(self, level, category, message, file_path=None):
        self.issues.append({
            'level': level,      # ERROR, WARNING, INFO
            'category': category,
            'message': message,
            'file': str(file_path) if file_path else None,
        })

    def summary(self):
        errors = sum(1 for i in self.issues if i['level'] == 'ERROR')
        warnings = sum(1 for i in self.issues if i['level'] == 'WARNING')
        infos = sum(1 for i in self.issues if i['level'] == 'INFO')
        return errors, warnings, infos


def check_stale_pages(result, max_age_days=30):
    """检查过时页面"""
    cutoff = (datetime.now() - timedelta(days=max_age_days)).strftime("%Y-%m-%d")

    for pattern in [
        f"{WIKI_ROOT}/companies/*/wiki/*.md",
        f"{WIKI_ROOT}/sectors/*/wiki/*.md",
        f"{WIKI_ROOT}/themes/*/wiki/*.md",
    ]:
        for wiki_file in glob.glob(pattern):
            content = Path(wiki_file).read_text(encoding="utf-8")

            # 从 frontmatter 提取 last_updated
            match = re.search(r'last_updated:\s*"?(\d{4}-\d{2}-\d{2})"?', content)
            if match:
                last_updated = match.group(1)
                if last_updated < cutoff:
                    age = (datetime.now() - datetime.strptime(last_updated, "%Y-%m-%d")).days
                    relpath = os.path.relpath(wiki_file, WIKI_ROOT)
                    result.add("WARNING", "stale",
                              f"Page not updated for {age} days (last: {last_updated})",
                              relpath)
            else:
                relpath = os.path.relpath(wiki_file, WIKI_ROOT)
                result.add("INFO", "stale", "No last_updated in frontmatter", relpath)


def check_orphan_pages(result):
    """检查孤儿页面（没有被其他页面引用的页面）"""
    all_pages = set()
    referenced = set()

    # 收集所有页面
    for pattern in [
        f"{WIKI_ROOT}/companies/*/wiki/*.md",
        f"{WIKI_ROOT}/sectors/*/wiki/*.md",
        f"{WIKI_ROOT}/themes/*/wiki/*.md",
    ]:
        for f in glob.glob(pattern):
            rel = os.path.relpath(f, WIKI_ROOT)
            all_pages.add(rel)

    # 扫描引用关系
    for wiki_file in glob.glob(f"{WIKI_ROOT}/**/wiki/*.md", recursive=True):
        content = Path(wiki_file).read_text(encoding="utf-8")
        # 提取 wikilinks [[...]]
        for match in re.finditer(r'\[\[([^\]]+)\]\]', content):
            referenced.add(match.group(1))
        # 提取相对路径链接 [text](path)
        for match in re.finditer(r'\[.*?\]\(([^)]+)\)', content):
            ref = match.group(1)
            if ref.startswith("../") or ref.startswith("../../"):
                # 解析相对路径
                base = os.path.dirname(wiki_file)
                resolved = os.path.normpath(os.path.join(base, ref))
                referenced.add(os.path.relpath(resolved, WIKI_ROOT))

    # 检查孤儿
    for page in all_pages:
        # index.md 和 overview.md 不算孤儿
        if page.endswith("index.md") or page.endswith("overview.md"):
            continue
        # 检查是否有其他页面引用此页面
        basename = os.path.basename(page).replace(".md", "")
        if basename not in referenced and page not in referenced:
            result.add("INFO", "orphan", f"Page may be orphaned (no inbound references)", page)


def check_empty_pages(result):
    """检查空页面（时间线没有条目）"""
    for pattern in [
        f"{WIKI_ROOT}/companies/*/wiki/*.md",
        f"{WIKI_ROOT}/sectors/*/wiki/*.md",
        f"{WIKI_ROOT}/themes/*/wiki/*.md",
    ]:
        for wiki_file in glob.glob(pattern):
            content = Path(wiki_file).read_text(encoding="utf-8")

            # 检查时间线部分是否有条目
            timeline_pos = content.find("## 时间线")
            if timeline_pos < 0:
                continue

            after_timeline = content[timeline_pos:]
            has_entries = "### 2" in after_timeline  # 日期格式 20xx-xx-xx

            if not has_entries:
                relpath = os.path.relpath(wiki_file, WIKI_ROOT)
                result.add("WARNING", "empty", "Timeline has no entries", relpath)


def check_broken_links(result):
    """检查来源链接是否有效"""
    for pattern in [
        f"{WIKI_ROOT}/companies/*/wiki/*.md",
        f"{WIKI_ROOT}/sectors/*/wiki/*.md",
        f"{WIKI_ROOT}/themes/*/wiki/*.md",
    ]:
        for wiki_file in glob.glob(pattern):
            content = Path(wiki_file).read_text(encoding="utf-8")
            wiki_dir = os.path.dirname(wiki_file)

            # 提取 [来源](path) 链接
            for match in re.finditer(r'\[来源\]\(([^)]+)\)', content):
                ref = match.group(1)
                resolved = os.path.normpath(os.path.join(wiki_dir, ref))
                if not os.path.exists(resolved):
                    relpath = os.path.relpath(wiki_file, WIKI_ROOT)
                    result.add("WARNING", "broken_link",
                              f"Source file not found: {ref}", relpath)


def check_config_consistency(result, config):
    """检查 config.yaml 与目录结构是否一致"""
    # 检查公司目录
    for company in config.get("companies", []):
        name = company["name"]
        company_dir = WIKI_ROOT / "companies" / name
        if not company_dir.exists():
            result.add("ERROR", "config", f"Company directory missing: {name}")

    # 检查行业目录
    for sector_name in config.get("sectors", {}):
        sector_dir = WIKI_ROOT / "sectors" / sector_name
        if not sector_dir.exists():
            result.add("ERROR", "config", f"Sector directory missing: {sector_name}")

    # 检查主题目录
    for theme_name in config.get("themes", {}):
        theme_dir = WIKI_ROOT / "themes" / theme_name
        if not theme_dir.exists():
            result.add("ERROR", "config", f"Theme directory missing: {theme_name}")


def check_data_freshness(result):
    """检查数据新鲜度（最近一次采集时间）"""
    log_content = LOG_PATH.read_text(encoding="utf-8") if LOG_PATH.exists() else ""

    # 查找最后一次 collect_news 的时间
    last_collect = None
    for match in re.finditer(r'## \[(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}\] collect_news', log_content):
        last_collect = match.group(1)

    if last_collect:
        age = (datetime.now() - datetime.strptime(last_collect, "%Y-%m-%d")).days
        if age > 1:
            result.add("WARNING", "freshness",
                      f"Last news collection was {age} days ago ({last_collect})")
        else:
            result.add("INFO", "freshness", f"Data is fresh (last collected: {last_collect})")
    else:
        result.add("WARNING", "freshness", "No news collection found in log")


# ── LLM 驱动的检查 ──────────────────────────

def _get_llm_client():
    """懒加载 LLM 客户端"""
    sys.path.insert(0, str(SCRIPTS_DIR))
    from llm_client import get_llm_client
    return get_llm_client()


def _load_all_wiki_pages():
    """加载所有 wiki 页面内容，返回 [(relpath, content), ...]"""
    pages = []
    for pattern in [
        f"{WIKI_ROOT}/companies/*/wiki/*.md",
        f"{WIKI_ROOT}/sectors/*/wiki/*.md",
        f"{WIKI_ROOT}/themes/*/wiki/*.md",
    ]:
        for wiki_file in glob.glob(pattern):
            content = Path(wiki_file).read_text(encoding="utf-8")
            relpath = os.path.relpath(wiki_file, WIKI_ROOT)
            pages.append((relpath, content))
    return pages


def _extract_entity_name(relpath):
    """从路径提取实体名"""
    parts = Path(relpath).parts
    if len(parts) >= 2:
        return parts[1]  # companies/X/... → X
    return ""


def check_semantic_contradictions(result):
    """用 LLM 检测语义级矛盾（跨页面不一致陈述）"""
    pages = _load_all_wiki_pages()
    # 按实体分组，只检查有多个页面的实体
    from collections import defaultdict
    by_entity = defaultdict(list)
    for relpath, content in pages:
        entity = _extract_entity_name(relpath)
        if entity:
            by_entity[entity].append((relpath, content))

    client = _get_llm_client()

    for entity, entity_pages in by_entity.items():
        if len(entity_pages) < 2:
            continue
        # 拼接同一实体的所有页面摘要
        combined = ""
        for relpath, content in entity_pages:
            # 只取时间线部分的前 1500 字
            tl_start = content.find("## 时间线")
            if tl_start >= 0:
                combined += f"\n--- {relpath} ---\n{content[tl_start:tl_start+1500]}\n"

        if len(combined) < 200:
            continue

        prompt = f"""检查以下关于"{entity}"的多条信息中是否存在矛盾或不一致的陈述。
只报告明确的矛盾（同一事实有不同说法），忽略时间变化导致的数据更新。

{combined}

请用以下格式输出，每行一条矛盾：
矛盾: [简要描述矛盾] | 页面1: [陈述1] | 页面2: [陈述2]

如果没有矛盾，输出: 无矛盾"""

        try:
            response = client.chat(prompt, max_tokens=512)
            if response and "无矛盾" not in response:
                for line in response.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("矛盾:") or line.startswith("矛盾："):
                        result.add("WARNING", "semantic",
                                  line.replace("矛盾:", "").replace("矛盾：", "").strip(),
                                  entity)
        except Exception as e:
            result.add("INFO", "semantic", f"LLM check skipped for {entity}: {e}")


def discover_missing_concepts(result):
    """发现被提及但未建立 wiki 页面的重要概念"""
    pages = _load_all_wiki_pages()

    # 收集已有页面名
    existing_pages = set()
    for relpath, _ in pages:
        basename = Path(relpath).stem
        existing_pages.add(basename)
        entity = _extract_entity_name(relpath)
        if entity:
            existing_pages.add(entity)

    # 从 graph.yaml 获取所有实体
    import yaml
    graph_path = WIKI_ROOT / "graph.yaml"
    if not graph_path.exists():
        result.add("INFO", "missing", "graph.yaml not found, skipping concept discovery")
        return

    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = yaml.safe_load(f)

    graph_entities = set()
    for comp_name in graph_data.get("companies", {}):
        graph_entities.add(comp_name)
    for sector_name in graph_data.get("sectors", {}):
        graph_entities.add(sector_name)
    for theme_name in graph_data.get("themes", {}):
        graph_entities.add(theme_name)

    # 检查 graph.yaml 中有但 wiki 中没有页面的实体
    for entity in graph_entities:
        if entity not in existing_pages:
            result.add("INFO", "missing",
                      f"Entity in graph.yaml but no wiki page: {entity}")

    # 用 LLM 抽取前 20 个页面中频繁提及但未建页的概念
    client = _get_llm_client()
    sample_pages = pages[:20]
    combined = ""
    for relpath, content in sample_pages:
        tl_start = content.find("## 时间线")
        if tl_start >= 0:
            combined += f"\n--- {relpath} ---\n{content[tl_start:tl_start+800]}\n"

    if len(combined) < 200:
        return

    prompt = f"""分析以下 wiki 内容，找出被频繁提及但可能需要独立 wiki 页面的重要概念（如技术、产品、事件）。
排除已有页面的实体: {', '.join(list(graph_entities)[:30])}

{combined[:4000]}

请列出最多5个值得创建独立页面的概念，每行一个：
概念: [名称] | 理由: [为什么需要独立页面]

如果没有明显缺失，输出: 无缺失概念"""

    try:
        response = client.chat(prompt, max_tokens=512)
        if response and "无缺失概念" not in response:
            for line in response.strip().split("\n"):
                line = line.strip()
                if line.startswith("概念:") or line.startswith("概念："):
                    result.add("INFO", "missing",
                              line.replace("概念:", "").replace("概念：", "").strip())
    except Exception as e:
        result.add("INFO", "missing", f"LLM concept discovery skipped: {e}")


def check_claim_freshness(result):
    """用 LLM 判断哪些结论可能已过时"""
    pages = _load_all_wiki_pages()
    cutoff = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

    # 筛选 60 天以上未更新的页面
    stale_pages = []
    for relpath, content in pages:
        match = re.search(r'last_updated:\s*"?(\d{4}-\d{2}-\d{2})"?', content)
        if match and match.group(1) < cutoff:
            stale_pages.append((relpath, content))

    if not stale_pages:
        result.add("INFO", "freshness_llm", "All pages are reasonably fresh")
        return

    client = _get_llm_client()

    for relpath, content in stale_pages[:15]:
        # 提取综合评估部分
        eval_start = content.find("## 综合评估")
        if eval_start < 0:
            continue
        eval_section = content[eval_start:eval_start+500]

        prompt = f"""以下是一段关于某公司的综合评估，最后更新时间较早。
判断其中哪些结论可能已经过时或需要更新。只列出明显可能过时的结论。

{eval_section}

请用以下格式输出：
过时: [结论] | 原因: [为什么可能过时]

如果没有明显过时的结论，输出: 无过时结论"""

        try:
            response = client.chat(prompt, max_tokens=256)
            if response and "无过时结论" not in response:
                for line in response.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("过时:") or line.startswith("过时："):
                        result.add("WARNING", "freshness_llm",
                                  line.replace("过时:", "").replace("过时：", "").strip(),
                                  relpath)
        except Exception as e:
            result.add("INFO", "freshness_llm", f"LLM freshness check skipped for {relpath}: {e}")


def run_lint(checks=None, use_llm=False):
    """运行指定的检查项"""
    result = LintResult()
    config = load_config()

    all_checks = {
        'stale': lambda: check_stale_pages(result),
        'orphans': lambda: check_orphan_pages(result),
        'empty': lambda: check_empty_pages(result),
        'links': lambda: check_broken_links(result),
        'config': lambda: check_config_consistency(result, config),
        'freshness': lambda: check_data_freshness(result),
    }

    if use_llm:
        all_checks['semantic'] = lambda: check_semantic_contradictions(result)
        all_checks['missing'] = lambda: discover_missing_concepts(result)
        all_checks['freshness_llm'] = lambda: check_claim_freshness(result)

    if checks is None or 'all' in checks:
        checks = list(all_checks.keys())

    for check_name in checks:
        if check_name in all_checks:
            all_checks[check_name]()

    return result


def main():
    parser = argparse.ArgumentParser(description="知识库健康检查")
    parser.add_argument("--check", type=str, default="all",
                        help="检查项: all|stale|orphans|empty|links|config|freshness|semantic|missing|freshness_llm")
    parser.add_argument("--llm", action="store_true",
                        help="启用 LLM 驱动的检查 (semantic, missing, freshness_llm)")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    checks = args.check.split(",") if args.check != "all" else ["all"]
    result = run_lint(checks, use_llm=args.llm)

    if args.json:
        import json
        print(json.dumps(result.issues, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print("  上市公司知识库 — 健康检查")
        print("=" * 50)

        if not result.issues:
            print("\n  All checks passed! No issues found.")
        else:
            # 按级别分组
            for level in ["ERROR", "WARNING", "INFO"]:
                issues = [i for i in result.issues if i['level'] == level]
                if issues:
                    icon = {"ERROR": "X", "WARNING": "!", "INFO": "i"}[level]
                    print(f"\n  [{level}] ({len(issues)})")
                    for i in issues:
                        file_info = f" ({i['file']})" if i['file'] else ""
                        print(f"    {icon} [{i['category']}] {i['message']}{file_info}")

        errors, warnings, infos = result.summary()
        print(f"\n{'=' * 50}")
        print(f"  Summary: {errors} errors, {warnings} warnings, {infos} info")
        print(f"{'=' * 50}")

    # 记录到 log
    errors, warnings, infos = result.summary()
    if errors > 0 or warnings > 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## [{now}] lint | {errors} errors, {warnings} warnings, {infos} info\n"
        for i in result.issues:
            if i['level'] in ('ERROR', 'WARNING'):
                entry += f"- [{i['level']}] {i['category']}: {i['message']}\n"
        if LOG_PATH.exists():
            content = LOG_PATH.read_text(encoding="utf-8")
        else:
            content = "# 知识库操作日志\n"
        content += entry
        LOG_PATH.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
