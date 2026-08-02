"""
tests/unit/test_quality.py — 质量快照和 SLO 测试
"""

from datetime import datetime

import pytest

from company_wiki.quality import (
    QualityAnalyzer,
    QualityReport,
    QualitySnapshot,
    SLO,
    verify_disaster_recovery,
)


# ── QualitySnapshot 测试 ──────────────────────────────

class TestQualitySnapshot:
    def test_snapshot_creation(self):
        """测试快照创建"""
        snapshot = QualitySnapshot(
            snapshot_id="qs-001",
            created_at=datetime.now(),
        )
        assert snapshot.snapshot_id == "qs-001"
        assert snapshot.total_sources == 0

    def test_snapshot_to_dict(self):
        """测试快照序列化"""
        snapshot = QualitySnapshot(
            snapshot_id="qs-001",
            created_at=datetime(2026, 7, 10),
            total_sources=100,
            verified_sources=95,
            total_claims=50,
            active_claims=45,
        )

        d = snapshot.to_dict()
        assert d["snapshot_id"] == "qs-001"
        assert d["sources"]["total"] == 100
        assert d["claims"]["active"] == 45

    def test_snapshot_save_load(self, tmp_path):
        """测试快照保存和加载"""
        snapshot = QualitySnapshot(
            snapshot_id="qs-001",
            created_at=datetime(2026, 7, 10),
            total_sources=100,
            verified_sources=95,
            total_pages=50,
            pages_with_timeline=45,
        )

        # 保存
        path = tmp_path / "snapshot.json"
        snapshot.save(path)

        # 加载
        loaded = QualitySnapshot.load(path)
        assert loaded.snapshot_id == "qs-001"
        assert loaded.total_sources == 100
        assert loaded.pages_with_timeline == 45


# ── SLO 测试 ──────────────────────────────

class TestSLO:
    def test_slo_met(self):
        """测试 SLO 达标"""
        slo = SLO(name="test", target=0.95, current=0.96)
        assert slo.is_met is True
        assert slo.gap == pytest.approx(-0.01)

    def test_slo_not_met(self):
        """测试 SLO 未达标"""
        slo = SLO(name="test", target=0.95, current=0.90)
        assert slo.is_met is False
        assert slo.gap == pytest.approx(0.05)

    def test_slo_exact(self):
        """测试 SLO 刚好达标"""
        slo = SLO(name="test", target=0.95, current=0.95)
        assert slo.is_met is True
        assert slo.gap == pytest.approx(0.0)


# ── QualityReport 测试 ──────────────────────────────

class TestQualityReport:
    def test_report_creation(self):
        """测试报告创建"""
        snapshot = QualitySnapshot(
            snapshot_id="qs-001",
            created_at=datetime.now(),
        )

        report = QualityReport(
            report_id="qr-001",
            created_at=datetime.now(),
            snapshot=snapshot,
        )

        assert report.report_id == "qr-001"
        assert len(report.slos) == 0

    def test_report_to_dict(self):
        """测试报告序列化"""
        snapshot = QualitySnapshot(
            snapshot_id="qs-001",
            created_at=datetime.now(),
        )

        report = QualityReport(
            report_id="qr-001",
            created_at=datetime(2026, 7, 10),
            snapshot=snapshot,
            slos=[
                SLO(name="test_slo", target=0.95, current=0.90),
            ],
            issues=["问题1"],
            recommendations=["建议1"],
        )

        d = report.to_dict()
        assert d["report_id"] == "qr-001"
        assert len(d["slos"]) == 1
        assert d["slos"][0]["is_met"] is False
        assert len(d["issues"]) == 1

    def test_report_save(self, tmp_path):
        """测试报告保存"""
        snapshot = QualitySnapshot(
            snapshot_id="qs-001",
            created_at=datetime.now(),
        )

        report = QualityReport(
            report_id="qr-001",
            created_at=datetime.now(),
            snapshot=snapshot,
        )

        path = tmp_path / "report.json"
        report.save(path)
        assert path.exists()


# ── QualityAnalyzer 测试 ──────────────────────────────

class TestQualityAnalyzer:
    def test_generate_snapshot_empty(self, tmp_path):
        """测试空目录生成快照"""
        analyzer = QualityAnalyzer(tmp_path)
        snapshot = analyzer.generate_snapshot()

        assert snapshot.snapshot_id.startswith("qs-")
        assert snapshot.total_pages == 0

    def test_generate_snapshot_with_pages(self, tmp_path):
        """测试有页面时生成快照"""
        # 创建测试页面
        wiki_dir = tmp_path / "companies" / "北方华创" / "wiki"
        wiki_dir.mkdir(parents=True)

        # 有时间线的页面
        (wiki_dir / "公司动态.md").write_text(
            "---\ntitle: 公司动态\n---\n## 时间线\n\n### 2026-01-01 | 新闻 | 测试\n- 内容\n\n## 综合评估\n> 评估内容\n",
            encoding="utf-8",
        )

        # 没有时间线的页面
        (wiki_dir / "概览.md").write_text(
            "---\ntitle: 概览\n---\n## 概述\n\n测试内容\n",
            encoding="utf-8",
        )

        analyzer = QualityAnalyzer(tmp_path)
        snapshot = analyzer.generate_snapshot()

        assert snapshot.total_pages == 2
        assert snapshot.pages_with_timeline == 1
        assert snapshot.pages_with_assessment == 1

    def test_generate_report(self, tmp_path):
        """测试生成报告"""
        analyzer = QualityAnalyzer(tmp_path)
        report = analyzer.generate_report()

        assert report.report_id.startswith("qr-")
        assert len(report.slos) == 4

        # 检查 SLO 名称
        slo_names = [s.name for s in report.slos]
        assert "source_verification" in slo_names
        assert "question_coverage" in slo_names
        assert "page_completeness" in slo_names
        assert "run_success_rate" in slo_names

    def test_generate_report_with_issues(self, tmp_path):
        """测试生成报告（有问题）"""
        # 创建孤立页面
        wiki_dir = tmp_path / "companies" / "测试" / "wiki"
        wiki_dir.mkdir(parents=True)
        (wiki_dir / "孤立页.md").write_text("内容", encoding="utf-8")

        analyzer = QualityAnalyzer(tmp_path)

        snapshot = analyzer.generate_snapshot()
        snapshot.orphan_pages = 1  # 模拟孤立页面
        snapshot.unverified_sources = 5

        report = analyzer.generate_report(snapshot)

        assert len(report.issues) > 0


# ── verify_disaster_recovery 测试 ──────────────────────────────

class TestVerifyDisasterRecovery:
    def test_verify_empty(self, tmp_path):
        """测试空目录验证"""
        is_recoverable, issues = verify_disaster_recovery(tmp_path, QualitySnapshot(
            snapshot_id="test",
            created_at=datetime.now(),
        ))
        assert is_recoverable is True
        assert len(issues) == 0

    def test_verify_with_files(self, tmp_path):
        """测试有文件时验证"""
        # 创建测试文件
        company_dir = tmp_path / "companies" / "北方华创"
        raw_dir = company_dir / "raw"
        raw_dir.mkdir(parents=True)
        (raw_dir / "data.md").write_text("内容", encoding="utf-8")

        wiki_dir = company_dir / "wiki"
        wiki_dir.mkdir(parents=True)
        (wiki_dir / "公司动态.md").write_text("wiki内容", encoding="utf-8")

        (tmp_path / "index.md").write_text("# 索引\n", encoding="utf-8")

        is_recoverable, issues = verify_disaster_recovery(tmp_path, QualitySnapshot(
            snapshot_id="test",
            created_at=datetime.now(),
        ))
        assert is_recoverable is True
        assert len(issues) == 0

    def test_verify_empty_index(self, tmp_path):
        """测试空 index 验证"""
        (tmp_path / "index.md").write_text("", encoding="utf-8")

        is_recoverable, issues = verify_disaster_recovery(tmp_path, QualitySnapshot(
            snapshot_id="test",
            created_at=datetime.now(),
        ))
        assert is_recoverable is False
        assert any("index.md 为空" in i for i in issues)
