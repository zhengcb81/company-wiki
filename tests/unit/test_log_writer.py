#!/usr/bin/env python3
"""Tests for scripts/log_writer.py — structured log writing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from log_writer import append_log, _rotate_if_needed, _clean_old_archives


class TestAppendLog:
    def test_creates_log_file(self, tmp_path):
        log_path = tmp_path / "log.md"
        append_log("collect_news", "采集5篇", log_path=log_path)
        assert log_path.exists()

    def test_contains_message(self, tmp_path):
        log_path = tmp_path / "log.md"
        append_log("ingest", "处理3个文件", log_path=log_path)
        content = log_path.read_text(encoding="utf-8")
        assert "处理3个文件" in content
        assert "ingest" in content

    def test_contains_details(self, tmp_path):
        log_path = tmp_path / "log.md"
        append_log("collect_news", "采集结果", details=["公司A: +3", "公司B: +2"], log_path=log_path)
        content = log_path.read_text(encoding="utf-8")
        assert "公司A: +3" in content
        assert "公司B: +2" in content

    def test_level_tags(self, tmp_path):
        log_path = tmp_path / "log.md"
        append_log("ingest", "正常操作", log_path=log_path, level="INFO")
        append_log("ingest", "出错了", log_path=log_path, level="ERROR")
        append_log("ingest", "警告", log_path=log_path, level="WARN")
        content = log_path.read_text(encoding="utf-8")
        assert "INFO" in content
        assert "ERROR" in content
        assert "WARN" in content

    def test_appends_to_existing(self, tmp_path):
        log_path = tmp_path / "log.md"
        append_log("op1", "msg1", log_path=log_path)
        append_log("op2", "msg2", log_path=log_path)
        content = log_path.read_text(encoding="utf-8")
        assert "msg1" in content
        assert "msg2" in content


class TestLogRotation:
    def test_no_rotation_when_small(self, tmp_path):
        log_path = tmp_path / "log.md"
        log_path.write_text("small content", encoding="utf-8")
        _rotate_if_needed(log_path)
        assert log_path.exists()
        # No archive created
        archives = list(tmp_path.glob("log_*.md"))
        assert len(archives) == 0

    def test_rotation_when_large(self, tmp_path):
        log_path = tmp_path / "log.md"
        # Create a file larger than the threshold
        large_content = "x" * (600 * 1024)  # 600KB > 500KB threshold
        log_path.write_text(large_content, encoding="utf-8")

        # Patch MAX_LOG_SIZE for this test
        import log_writer
        original = log_writer.MAX_LOG_SIZE
        log_writer.MAX_LOG_SIZE = 500 * 1024

        try:
            _rotate_if_needed(log_path)
            # Original file should be replaced with header
            content = log_path.read_text(encoding="utf-8")
            assert "操作日志" in content  # Header content
            # Archive should exist
            archives = list(tmp_path.glob("log_*.md"))
            assert len(archives) == 1
        finally:
            log_writer.MAX_LOG_SIZE = original


class TestCleanOldArchives:
    def test_removes_old_archives(self, tmp_path):
        # Create more than MAX_ARCHIVES archives
        import log_writer
        original_max = log_writer.MAX_ARCHIVES
        log_writer.MAX_ARCHIVES = 3

        try:
            log_path = tmp_path / "log.md"
            for i in range(5):
                (tmp_path / f"log_2026-04-{i:02d}.md").write_text(f"archive {i}", encoding="utf-8")

            _clean_old_archives(log_path)

            archives = sorted(tmp_path.glob("log_*.md"))
            assert len(archives) == 3
        finally:
            log_writer.MAX_ARCHIVES = original_max
