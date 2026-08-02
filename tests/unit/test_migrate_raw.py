"""
tests/unit/test_migrate_raw.py — Raw 迁移脚本测试
"""

from pathlib import Path


from company_wiki.migration import EntryClassification


# ── 测试 classify_file ──────────────────────────────

class TestClassifyFile:
    def test_annual_report(self):
        """年报应该分类为 VERIFIED"""
        from scripts.migrate_raw import classify_file
        assert classify_file(Path("北方华创_2025年报.md")) == EntryClassification.VERIFIED

    def test_quarterly_report(self):
        """季报应该分类为 VERIFIED"""
        from scripts.migrate_raw import classify_file
        assert classify_file(Path("北方华创_2025Q1季报.md")) == EntryClassification.VERIFIED

    def test_announcement(self):
        """公告应该分类为 VERIFIED"""
        from scripts.migrate_raw import classify_file
        assert classify_file(Path("北方华创_公告.md")) == EntryClassification.VERIFIED

    def test_pdf_file(self):
        """PDF 文件应该分类为 VERIFIED"""
        from scripts.migrate_raw import classify_file
        assert classify_file(Path("report.pdf")) == EntryClassification.VERIFIED

    def test_news_with_date(self):
        """有日期的新闻应该分类为 VERIFIED"""
        from scripts.migrate_raw import classify_file
        assert classify_file(Path("北方华创_2025年业绩快报.md")) == EntryClassification.VERIFIED

    def test_unknown_file(self):
        """未知文件应该分类为 UNVERIFIED"""
        from scripts.migrate_raw import classify_file
        assert classify_file(Path("notes.txt")) == EntryClassification.UNVERIFIED


# ── 测试 plan_migration ──────────────────────────────

class TestPlanMigration:
    def test_plan_empty_directory(self, tmp_path):
        """空目录应该返回空清单"""
        from scripts.migrate_raw import plan_migration
        manifest = plan_migration(tmp_path)
        assert len(manifest.entries) == 0

    def test_plan_with_files(self, tmp_path):
        """有文件时应该返回清单"""
        # 创建测试文件
        company_dir = tmp_path / "companies" / "北方华创"
        company_dir.mkdir(parents=True)
        (company_dir / "年报.md").write_text("年报内容", encoding="utf-8")
        (company_dir / "公告.pdf").write_bytes(b"pdf content")

        from scripts.migrate_raw import plan_migration
        manifest = plan_migration(tmp_path)

        assert len(manifest.entries) == 2
        # 都应该分类为 VERIFIED
        for entry in manifest.entries:
            assert entry.classification == EntryClassification.VERIFIED


# ── 测试 _classify_to_source_kind ──────────────────────────────

class TestClassifyToSourceKind:
    def test_verified_maps_to_regulatory(self):
        """VERIFIED 应该映射为 regulatory"""
        from scripts.migrate_raw import _classify_to_source_kind
        assert _classify_to_source_kind(EntryClassification.VERIFIED) == "regulatory"

    def test_recoverable_maps_to_original_news(self):
        """RECOVERABLE 应该映射为 original_news"""
        from scripts.migrate_raw import _classify_to_source_kind
        assert _classify_to_source_kind(EntryClassification.RECOVERABLE) == "original_news"

    def test_unverified_maps_to_aggregated_news(self):
        """UNVERIFIED 应该映射为 aggregated_news"""
        from scripts.migrate_raw import _classify_to_source_kind
        assert _classify_to_source_kind(EntryClassification.UNVERIFIED) == "aggregated_news"
