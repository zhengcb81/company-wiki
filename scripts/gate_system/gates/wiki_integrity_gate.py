#!/usr/bin/env python3
"""
gate_system/gates/wiki_integrity_gate.py — Gate 5: Wiki完整性

检查Wiki入库后的页面完整性：
- Frontmatter是否完整（title, entity, type, last_updated, sources_count）
- 来源链接是否可访问
- 是否有重复条目
- 是否符合 CLAUDE.md 的格式规范
"""

import re
from pathlib import Path
from typing import Dict, List

from gate_system.base import (
    Gate,
    GateResult,
    PipelineContext,
    create_passed_result,
    create_failed_result,
)


class WikiIntegrityGate(Gate):
    """
    Gate 5: Wiki 完整性检查。

    验证入库后的 wiki 页面是否符合规范。
    """

    name = "gate_5_wiki_integrity"
    doc_types = [
        "annual_report",
        "semi_annual_report",
        "quarterly_report",
        "investor_relations",
        "prospectus",
    ]
    description = "检查Wiki页面的frontmatter、链接和重复条目"

    def run(self, context: PipelineContext) -> GateResult:
        wiki_dir = Path.home() / "company-wiki" / "companies" / context.company / "wiki"
        wiki_path = wiki_dir / "公司动态.md"

        if not wiki_path.exists():
            return create_passed_result(
                score=5.0,
                issues=["Wiki页面不存在（可能是首次处理）"],
            )

        try:
            content = wiki_path.read_text(encoding="utf-8")
        except Exception as e:
            return create_failed_result(
                issues=[f"读取Wiki页面失败: {e}"],
                diagnosis={"root_cause": "execution_error", "fixable": False},
            )

        issues = []

        # 1. 检查 frontmatter
        frontmatter = self._parse_frontmatter(content)
        required_fm_fields = [
            "title",
            "entity",
            "type",
            "last_updated",
            "sources_count",
        ]
        missing_fm = [f for f in required_fm_fields if f not in frontmatter]
        if missing_fm:
            issues.append(f"Frontmatter缺少字段: {missing_fm}")

        # 2. 检查时间线条目格式
        timeline_entries = self._extract_timeline_entries(content)
        malformed_entries = []
        for i, entry in enumerate(timeline_entries):
            if not re.match(r"\d{4}-\d{2}-\d{2}", entry.get("date", "")):
                malformed_entries.append(f"条目{i}: 日期格式错误")
            if not entry.get("title"):
                malformed_entries.append(f"条目{i}: 缺少标题")
            if not entry.get("source"):
                malformed_entries.append(f"条目{i}: 缺少来源链接")

        if malformed_entries:
            issues.append(f"时间线条目格式问题: {malformed_entries[:3]}")

        # 3. 检查重复条目
        duplicates = self._find_duplicates(timeline_entries)
        if duplicates:
            issues.append(f"发现重复条目: {duplicates}")

        # 4. 检查来源链接
        broken_links = self._check_source_links(content, wiki_path.parent)
        if broken_links:
            issues.append(f"来源链接不可访问: {broken_links[:3]}")

        # 5. 检查 sources_count 与实际条目数是否一致
        if "sources_count" in frontmatter:
            try:
                declared_count = int(frontmatter["sources_count"])
                actual_count = len(timeline_entries)
                if abs(declared_count - actual_count) > 1:  # 允许1条误差
                    issues.append(
                        f"sources_count不匹配: 声明{declared_count}, 实际{actual_count}"
                    )
            except ValueError:
                issues.append("sources_count 不是有效数字")

        if not issues:
            return create_passed_result(score=5.0)

        return create_failed_result(
            issues=issues,
            diagnosis={
                "root_cause": "schema_violation",
                "fixable": True,
                "fix_method": "retry_with_different_strategy",
                "max_retries": 1,
            },
        )

    def _parse_frontmatter(self, content: str) -> Dict[str, str]:
        """解析 frontmatter"""
        fm = {}
        match = re.match(r"---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if match:
            for line in match.group(1).split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    fm[key.strip()] = value.strip().strip('"').strip("'")
        return fm

    def _extract_timeline_entries(self, content: str) -> List[Dict]:
        """提取时间线条目"""
        entries = []
        # 匹配 ### YYYY-MM-DD | type | title 格式
        pattern = r"###\s+(\d{4}-\d{2}-\d{2})\s+\|\s+([^\|]+)\|\s+(.+?)(?=\n-|\n###|$)"
        for match in re.finditer(pattern, content, re.DOTALL):
            entries.append(
                {
                    "date": match.group(1).strip(),
                    "type": match.group(2).strip(),
                    "title": match.group(3).strip().split("\n")[0],
                    "source": self._extract_source(content, match.end()),
                }
            )
        return entries

    def _extract_source(self, content: str, pos: int) -> str:
        """提取来源链接"""
        after = content[pos : pos + 500]
        link_match = re.search(r"\[来源\]\((.+?)\)", after)
        if link_match:
            return link_match.group(1)
        return ""

    def _find_duplicates(self, entries: List[Dict]) -> List[str]:
        """查找重复条目（相同日期+标题）"""
        seen = {}
        duplicates = []
        for entry in entries:
            key = f"{entry['date']}|{entry['title']}"
            if key in seen:
                duplicates.append(key)
            else:
                seen[key] = True
        return duplicates

    def _check_source_links(self, content: str, wiki_dir: Path) -> List[str]:
        """检查来源链接是否指向存在的文件"""
        broken = []
        for match in re.finditer(r"\[来源\]\((.+?)\)", content):
            link = match.group(1)
            # 解析相对路径
            if link.startswith("../"):
                target = wiki_dir.parent / link.replace("../", "")
                if not target.exists():
                    broken.append(link)
            elif link.startswith("/"):
                target = Path.home() / "company-wiki" / link.lstrip("/")
                if not target.exists():
                    broken.append(link)
        return broken
