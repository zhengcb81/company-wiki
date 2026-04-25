#!/usr/bin/env python3
"""Tests for scripts/state_store.py — SQLite-backed state store."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from state_store import StateStore


class TestStateStoreInit:
    def test_creates_db(self, tmp_path):
        db_path = tmp_path / "test_state.db"
        store = StateStore(db_path=db_path)
        assert db_path.exists()

    def test_creates_tables(self, tmp_path):
        db_path = tmp_path / "test_state.db"
        store = StateStore(db_path=db_path)
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "company_state" in tables
        assert "page_state" in tables
        assert "prompt_stats" in tables
        assert "error_counter" in tables


class TestCompanyState:
    def test_set_and_get_last_collect(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        store.set_last_collect("中微公司", "2026-04-25T10:00:00")
        state = store.get_company_state("中微公司")
        assert state is not None
        assert state["last_collect_time"] == "2026-04-25T10:00:00"

    def test_set_and_get_last_ingest(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        store.set_last_ingest("北方华创", "2026-04-25T12:00:00")
        state = store.get_company_state("北方华创")
        assert state is not None
        assert state["last_ingest_time"] == "2026-04-25T12:00:00"

    def test_set_and_get_last_assessment(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        store.set_last_assessment("万华化学", "2026-04-25")
        state = store.get_company_state("万华化学")
        assert state is not None
        assert state["last_assessment_time"] == "2026-04-25"

    def test_update_overwrites(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        store.set_last_collect("公司A", "2026-01-01")
        store.set_last_collect("公司A", "2026-04-25")
        state = store.get_company_state("公司A")
        assert state["last_collect_time"] == "2026-04-25"

    def test_nonexistent_company_returns_none(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        assert store.get_company_state("不存在的公司") is None

    def test_get_all_company_states(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        store.set_last_collect("公司A", "2026-01-01")
        store.set_last_collect("公司B", "2026-02-01")
        states = store.get_all_company_states()
        names = {s["company_name"] for s in states}
        assert "公司A" in names
        assert "公司B" in names

    def test_update_entry_stats(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        store.update_entry_stats("公司A", 42, 0.85)
        state = store.get_company_state("公司A")
        assert state["entry_count"] == 42
        assert abs(state["avg_entry_quality"] - 0.85) < 0.01

    def test_companies_needing_collect(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        # Company with no state
        store.set_last_collect("公司A", "2026-04-25")  # recent
        # CompanyB has no state at all
        need = store.get_companies_needing_collect(days=7)
        assert "公司B" not in need  # Not in DB, so won't show up
        assert "公司A" not in need  # Recently collected


class TestPromptStats:
    def test_record_and_get(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        store.record_prompt_call("analysis", "v1", success=True, tokens=500, latency_ms=200)
        stats = store.get_prompt_stats("analysis")
        assert stats is not None
        assert stats["call_count"] == 1
        assert stats["success_count"] == 1

    def test_incremental_stats(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        store.record_prompt_call("analysis", "v1", success=True, tokens=500, latency_ms=200)
        store.record_prompt_call("analysis", "v1", success=False, parse_error=True, tokens=300, latency_ms=100)
        stats = store.get_prompt_stats("analysis")
        assert stats["call_count"] == 2
        assert stats["success_count"] == 1
        assert stats["parse_error_count"] == 1

    def test_nonexistent_prompt(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        assert store.get_prompt_stats("nonexistent") is None


class TestErrorCounter:
    def test_increment_and_read(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        store.increment_error_count("ingest_v2", "parse_error")
        store.increment_error_count("ingest_v2", "parse_error")
        # Read directly from DB to verify
        conn = store._conn()
        row = conn.execute(
            "SELECT count FROM error_counter WHERE module=? AND error_type=?",
            ("ingest_v2", "parse_error"),
        ).fetchone()
        assert row["count"] == 2

    def test_different_error_types(self, tmp_path):
        store = StateStore(db_path=tmp_path / "test.db")
        store.increment_error_count("module1", "error_a")
        store.increment_error_count("module1", "error_b")
        conn = store._conn()
        rows = conn.execute(
            "SELECT error_type, count FROM error_counter WHERE module=?",
            ("module1",),
        ).fetchall()
        types = {row["error_type"]: row["count"] for row in rows}
        assert types == {"error_a": 1, "error_b": 1}
