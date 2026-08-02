#!/usr/bin/env python3
"""Tests for scripts/batch_assessment.py — assessment generation functions."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from batch_assessment import (
    has_assessment,
    is_assessment_stale,
    extract_timeline_entries,
    add_assessment_section,
)


def _write_wiki(tmp_path: Path, content: str) -> Path:
    """Helper to create a temp wiki file."""
    p = tmp_path / "test_wiki.md"
    p.write_text(content, encoding="utf-8")
    return p


WIKI_WITH_ASSESSMENT = """---
title: 公司动态
entity: 测试公司
type: company_topic
last_updated: 2026-04-25
---

## 核心问题
- 竞争优势?

### 2026-04-25 | 新闻 | 标题
- 要点1
- 要点2

## 综合评估
> 公司目前处于增长期，订单饱满。
> 预计未来营收将持续增长。
"""

WIKI_WITHOUT_ASSESSMENT = """---
title: 公司动态
entity: 测试公司
type: company_topic
last_updated: 2026-04-25
---

## 核心问题
- 竞争优势?

### 2026-04-25 | 新闻 | 标题
- 要点1
- 要点2
"""

WIKI_WITH_PLACEHOLDER = """---
title: 公司动态
entity: 测试公司
type: company_topic
last_updated: 2026-04-25
---

## 综合评估
（暂无）
"""

WIKI_EMPTY = ""


class TestHasAssessment:
    def test_with_assessment(self, tmp_path):
        p = _write_wiki(tmp_path, WIKI_WITH_ASSESSMENT)
        assert has_assessment(p) is True

    def test_without_assessment(self, tmp_path):
        p = _write_wiki(tmp_path, WIKI_WITHOUT_ASSESSMENT)
        assert has_assessment(p) is False

    def test_with_placeholder(self, tmp_path):
        p = _write_wiki(tmp_path, WIKI_WITH_PLACEHOLDER)
        assert has_assessment(p) is False

    def test_empty_file(self, tmp_path):
        p = _write_wiki(tmp_path, WIKI_EMPTY)
        assert has_assessment(p) is False

    def test_nonexistent_file(self, tmp_path):
        p = tmp_path / "nonexistent.md"
        assert has_assessment(p) is False


class TestIsAssessmentStale:
    def test_recent_is_not_stale(self, tmp_path):
        reference_time = datetime(2026, 4, 25, 12, 0, 0)
        content = WIKI_WITH_ASSESSMENT.replace("2026-04-25", "2026-04-24")
        p = _write_wiki(tmp_path, content)
        assert is_assessment_stale(p, stale_days=60, now=reference_time) is False

    def test_old_is_stale(self, tmp_path):
        reference_time = datetime(2026, 4, 25, 12, 0, 0)
        content = WIKI_WITH_ASSESSMENT.replace("2026-04-25", "2025-01-01")
        p = _write_wiki(tmp_path, content)
        assert is_assessment_stale(p, stale_days=60, now=reference_time) is True

    def test_missing_last_updated_is_stale(self, tmp_path):
        content = """---
title: 公司动态
entity: 测试公司
type: company_topic
---

## 综合评估
> 有评估
"""
        p = _write_wiki(tmp_path, content)
        assert is_assessment_stale(p, stale_days=60) is True

    def test_custom_stale_days(self, tmp_path):
        reference_time = datetime(2026, 4, 25, 12, 0, 0)
        date_55_days_ago = (reference_time - timedelta(days=55)).strftime("%Y-%m-%d")
        content = WIKI_WITH_ASSESSMENT.replace("2026-04-25", date_55_days_ago)
        p = _write_wiki(tmp_path, content)
        # 55 days ago, 60-day threshold → not stale
        assert is_assessment_stale(p, stale_days=60, now=reference_time) is False

    def test_exact_threshold_is_not_stale(self, tmp_path):
        reference_time = datetime(2026, 4, 25, 12, 0, 0)
        threshold_date = (reference_time - timedelta(days=60)).strftime("%Y-%m-%d")
        content = WIKI_WITH_ASSESSMENT.replace("2026-04-25", threshold_date)
        p = _write_wiki(tmp_path, content)
        assert is_assessment_stale(p, stale_days=60, now=reference_time) is False
        # 55 days ago, 30-day threshold → stale
        assert is_assessment_stale(p, stale_days=30) is True


class TestExtractTimelineEntries:
    def test_extracts_entries(self, tmp_path):
        p = _write_wiki(tmp_path, WIKI_WITHOUT_ASSESSMENT)
        entries = extract_timeline_entries(p)
        assert len(entries) >= 1
        assert entries[0]["date"] == "2026-04-25"
        assert "标题" in entries[0]["title"]

    def test_empty_file(self, tmp_path):
        p = _write_wiki(tmp_path, "")
        entries = extract_timeline_entries(p)
        assert entries == []

    def test_no_timeline_section(self, tmp_path):
        content = """---
title: 催化剂日历
entity: 测试公司
type: company_topic
last_updated: 2026-04-25
---
"""
        p = _write_wiki(tmp_path, content)
        entries = extract_timeline_entries(p)
        assert entries == []

    def test_multiple_entries(self, tmp_path):
        content = """---
title: 公司动态
entity: 测试公司
type: company_topic
last_updated: 2026-04-25
---

### 2026-04-25 | 新闻 | 标题1
- 要点1

### 2026-04-20 | 公告 | 标题2
- 要点2

### 2026-04-15 | 研报 | 标题3
- 要点3
"""
        p = _write_wiki(tmp_path, content)
        entries = extract_timeline_entries(p)
        assert len(entries) == 3


class TestAddAssessmentSection:
    def test_adds_assessment(self, tmp_path):
        p = _write_wiki(tmp_path, WIKI_WITHOUT_ASSESSMENT)
        result = add_assessment_section(p, "这是新的综合评估内容")
        assert result is True
        content = p.read_text(encoding="utf-8")
        assert "## 综合评估" in content
        assert "这是新的综合评估内容" in content

    def test_preserves_existing_content(self, tmp_path):
        p = _write_wiki(tmp_path, WIKI_WITHOUT_ASSESSMENT)
        add_assessment_section(p, "评估内容")
        content = p.read_text(encoding="utf-8")
        assert "要点1" in content  # Original content preserved
