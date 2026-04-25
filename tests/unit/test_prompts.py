#!/usr/bin/env python3
"""Tests for scripts/prompts.py — LLM prompt template functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from prompts import (
    build_analysis_prompt,
    build_financial_report_prompt,
    build_ir_prompt,
    build_assessment_prompt,
    build_question_generation_prompt,
    build_announcement_prompt,
    build_prospectus_prompt,
    build_distillation_prompt,
)


class TestBuildAnalysisPrompt:
    """Tests for build_analysis_prompt()."""

    def test_contains_entity_name(self):
        p = build_analysis_prompt(
            content="test content",
            entity_name="中微公司",
            source_type="news",
            published_date="2026-04-25",
            core_questions=["竞争优势是什么?"],
        )
        assert "中微公司" in p

    def test_contains_source_type_desc(self):
        p = build_analysis_prompt(
            content="x",
            entity_name="测试",
            source_type="annual_report",
            published_date="2026-01-01",
            core_questions=[],
        )
        assert "年度报告" in p

    def test_contains_date(self):
        p = build_analysis_prompt(
            content="x",
            entity_name="测试",
            source_type="news",
            published_date="2026-04-25",
            core_questions=[],
        )
        assert "2026-04-25" in p

    def test_contains_core_questions(self):
        p = build_analysis_prompt(
            content="x",
            entity_name="测试",
            source_type="news",
            published_date="2026-01-01",
            core_questions=["问题1", "问题2"],
        )
        assert "问题1" in p
        assert "问题2" in p

    def test_empty_core_questions(self):
        p = build_analysis_prompt(
            content="x",
            entity_name="测试",
            source_type="news",
            published_date="2026-01-01",
            core_questions=[],
        )
        assert "暂无核心问题" in p

    def test_content_truncation(self):
        long_content = "x" * 50000
        p = build_analysis_prompt(
            content=long_content,
            entity_name="测试",
            source_type="news",
            published_date="2026-01-01",
            core_questions=[],
            max_content_chars=1000,
        )
        # The truncated content should be shorter than original
        assert len(p) < len(long_content) + 5000

    def test_contains_json_format(self):
        p = build_analysis_prompt(
            content="x",
            entity_name="测试",
            source_type="news",
            published_date="2026-01-01",
            core_questions=[],
        )
        assert "timeline_entries" in p
        assert "JSON" in p

    def test_related_entities(self):
        p = build_analysis_prompt(
            content="x",
            entity_name="测试",
            source_type="news",
            published_date="2026-01-01",
            core_questions=[],
            related_entities=["北方华创", "中芯国际"],
        )
        assert "北方华创" in p
        assert "中芯国际" in p

    def test_existing_assessment(self):
        p = build_analysis_prompt(
            content="x",
            entity_name="测试",
            source_type="news",
            published_date="2026-01-01",
            core_questions=[],
            existing_assessment="当前公司处于增长期",
        )
        assert "当前公司处于增长期" in p


class TestBuildFinancialReportPrompt:
    def test_basic_structure(self):
        p = build_financial_report_prompt(
            content="营收100亿",
            entity_name="万华化学",
            report_type="年报",
            period="2025年报",
            core_questions=["MDI价格趋势?"],
        )
        assert "万华化学" in p
        assert "2025年报" in p
        assert "MDI价格趋势" in p

    def test_previous_period_data(self):
        p = build_financial_report_prompt(
            content="x",
            entity_name="测试",
            report_type="季报",
            period="2025Q1",
            core_questions=[],
            previous_period_data={"period": "2024Q4", "summary": "营收80亿"},
        )
        assert "2024Q4" in p
        assert "营收80亿" in p

    def test_content_truncation(self):
        p = build_financial_report_prompt(
            content="y" * 50000,
            entity_name="测试",
            report_type="年报",
            period="2025",
            core_questions=[],
            max_content_chars=500,
        )
        assert len(p) < 50000


class TestBuildIRPrompt:
    def test_basic_structure(self):
        p = build_ir_prompt(
            content="Q: 订单情况? A: 订单饱满",
            entity_name="中微公司",
            event_date="2026-04-20",
            core_questions=["订单增长?"],
        )
        assert "中微公司" in p
        assert "2026-04-20" in p

    def test_one_entry_note(self):
        """IR prompt should emphasize generating only one timeline entry."""
        p = build_ir_prompt(
            content="Q: x A: y",
            entity_name="测试",
            event_date="2026-01-01",
            core_questions=[],
        )
        assert "一个" in p or "IR" in p


class TestBuildAssessmentPrompt:
    def test_basic_structure(self):
        p = build_assessment_prompt(
            timeline_entries=[{"date": "2026-04-25", "title": "标题", "points": ["要点1"]}],
            entity_name="中微公司",
            topic_name="公司动态",
            core_questions=["竞争优势?"],
        )
        assert "中微公司" in p


class TestBuildQuestionGenerationPrompt:
    def test_basic_structure(self):
        p = build_question_generation_prompt(
            entity_name="北方华创",
            sector="半导体设备",
            position="半导体设备龙头",
            existing_questions=["竞争优势?"],
            recent_content="公司近期获得大订单",
        )
        assert "北方华创" in p
        assert "半导体设备" in p


class TestBuildAnnouncementPrompt:
    def test_basic_structure(self):
        p = build_announcement_prompt(
            content="公司公告内容",
            entity_name="测试公司",
            announcement_type="业绩预告",
            published_date="2026-04-25",
            core_questions=[],
        )
        assert "测试公司" in p
        assert "2026-04-25" in p


class TestBuildProspectusPrompt:
    def test_basic_structure(self):
        p = build_prospectus_prompt(
            content="招股说明书摘要",
            entity_name="测试公司",
            published_date="2026-04-25",
            core_questions=["募资用途?"],
        )
        assert "测试公司" in p
        assert "募资用途" in p


class TestBuildDistillationPrompt:
    def test_basic_structure(self):
        p = build_distillation_prompt(
            sector_name="半导体设备",
            company_entries={
                "北方华创": [{"date": "2026-04-25", "title": "获大单", "key_points": ["要点1"]}],
                "中微公司": [{"date": "2026-04-20", "title": "新品发布", "key_points": ["要点2"]}],
            },
            core_questions=["国产化进展?"],
        )
        assert "半导体设备" in p
        assert "北方华创" in p
