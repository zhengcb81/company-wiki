"""Tests for src/company_wiki/ new modules"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from company_wiki.config import load_config, ConfigError, ScheduleConfig
from company_wiki.graph_adapter import GraphAdapter
from company_wiki.source_registry import SourceRegistry
from company_wiki.run_store import RunStore
from company_wiki.question_registry import QuestionRegistry
from company_wiki.domain import (
    SourceKind, Question, AnswerState,
)


# ── Config Tests ──────────────────────────────

class TestConfig:
    def test_schedule_valid_intervals(self):
        s = ScheduleConfig(news_collection="daily", lint="weekly")
        assert s.validate() == []

    def test_schedule_invalid_interval(self):
        s = ScheduleConfig(news_collection="never")
        errors = s.validate()
        assert len(errors) > 0
        assert "never" in errors[0]

    def test_load_config_missing_file(self, tmp_path):
        with pytest.raises(ConfigError, match="不存在"):
            load_config(tmp_path / "nonexistent.yaml")

    def test_load_config_valid(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
schedule:
  news_collection: daily
  lint: weekly
llm:
  provider: deepseek
  model: deepseek-v4-flash
search:
  engine: tavily
""", encoding="utf-8")
        config = load_config(config_path)
        assert config.llm.provider == "deepseek"
        assert config.schedule.news_collection == "daily"


# ── GraphAdapter Tests ──────────────────────────────

class TestGraphAdapter:
    def test_resolve_targets_competitor(self, tmp_path):
        graph_path = tmp_path / "graph.yaml"
        graph_path.write_text("""
edges:
- from: 北方华创
  to: 半导体设备
  type: belongs_to
questions:
  半导体设备:
    - 各环节设备国产化率？
""", encoding="utf-8")

        companies = {
            "北方华创": type("Company", (), {
                "sectors": ["半导体设备"],
                "themes": ["国产替代"],
                "competes_with": ["中微公司"],
            })(),
        }

        adapter = GraphAdapter(graph_path, companies)
        targets = adapter.resolve_targets("北方华创")

        names = [t.entity_name for t in targets]
        assert "中微公司" in names
        assert "半导体设备" in names

    def test_get_questions(self, tmp_path):
        graph_path = tmp_path / "graph.yaml"
        graph_path.write_text("""
questions:
  半导体设备:
    - 各环节设备国产化率？
    - 先进制程设备进展？
""", encoding="utf-8")

        adapter = GraphAdapter(graph_path)
        qs = adapter.get_questions("半导体设备")
        assert len(qs) == 2


# ── SourceRegistry Tests ──────────────────────────────

class TestSourceRegistry:
    def test_register_and_get(self, tmp_path):
        db_path = tmp_path / "sources.db"
        registry = SourceRegistry(db_path)

        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("test content", encoding="utf-8")

        record = registry.register(test_file, SourceKind.REGULATORY)
        assert record.source_id
        assert record.source_kind == SourceKind.REGULATORY

        # Get by ID
        got = registry.get(record.source_id)
        assert got is not None
        assert got.path == str(test_file)

        registry.close()

    def test_duplicate_content(self, tmp_path):
        db_path = tmp_path / "sources.db"
        registry = SourceRegistry(db_path)

        file1 = tmp_path / "test1.md"
        file1.write_text("same content", encoding="utf-8")
        file2 = tmp_path / "test2.md"
        file2.write_text("same content", encoding="utf-8")

        r1 = registry.register(file1, SourceKind.REGULATORY)
        r2 = registry.register(file2, SourceKind.REGULATORY)

        # Same content → same source_id
        assert r1.source_id == r2.source_id

        registry.close()

    def test_count_by_status(self, tmp_path):
        db_path = tmp_path / "sources.db"
        registry = SourceRegistry(db_path)

        test_file = tmp_path / "test.md"
        test_file.write_text("content", encoding="utf-8")
        registry.register(test_file, SourceKind.REGULATORY)

        counts = registry.count_by_status()
        assert counts.get("registered", 0) == 1

        registry.close()


# ── RunStore Tests ──────────────────────────────

class TestRunStore:
    def test_create_and_complete_run(self, tmp_path):
        db_path = tmp_path / "runs.db"
        store = RunStore(db_path)

        run_id = store.create_run("source-001", "v1.0")
        assert run_id

        store.start_run(run_id)
        run = store.get_run(run_id)
        assert run["status"] == "running"

        store.complete_run(run_id, "output-hash")
        run = store.get_run(run_id)
        assert run["status"] == "completed"

        store.close()

    def test_fail_run(self, tmp_path):
        db_path = tmp_path / "runs.db"
        store = RunStore(db_path)

        run_id = store.create_run("source-002", "v1.0")
        store.fail_run(run_id, "API timeout")

        run = store.get_run(run_id)
        assert run["status"] == "failed"
        assert "timeout" in run["error"]

        store.close()

    def test_delivery_outbox(self, tmp_path):
        db_path = tmp_path / "runs.db"
        store = RunStore(db_path)

        run_id = store.create_run("source-003", "v1.0")
        delivery_id = store.create_delivery(
            run_id, "patch-001", "北方华创", "companies/北方华创/wiki/公司动态.md"
        )
        assert delivery_id

        deliveries = store.get_deliveries(run_id)
        assert len(deliveries) == 1
        assert deliveries[0]["status"] == "planned"

        store.close()

    def test_idempotent_delivery(self, tmp_path):
        db_path = tmp_path / "runs.db"
        store = RunStore(db_path)

        run_id = store.create_run("source-004", "v1.0")
        id1 = store.create_delivery(
            run_id, "patch-002", "北方华创", "page.md",
            idempotency_key="key-001",
        )
        id2 = store.create_delivery(
            run_id, "patch-002", "北方华创", "page.md",
            idempotency_key="key-001",
        )

        # Same idempotency_key → same delivery_id
        assert id1 == id2

        store.close()

    def test_budget(self, tmp_path):
        db_path = tmp_path / "runs.db"
        store = RunStore(db_path)

        run_id = store.create_run("source-005", "v1.0")
        store.log_cost(run_id, 0.5, "LLM call")
        store.log_cost(run_id, 0.3, "Search")

        total = store.get_total_cost(run_id)
        assert abs(total - 0.8) < 0.01

        store.close()


# ── QuestionRegistry Tests ──────────────────────────────

class TestQuestionRegistry:
    def test_add_and_get(self, tmp_path):
        db_path = tmp_path / "questions.db"
        registry = QuestionRegistry(db_path)

        q = Question(id="Q001", text="北方华创订单增速？", owner="北方华创", priority="high")
        registry.add(q)

        got = registry.get("Q001")
        assert got is not None
        assert got.text == "北方华创订单增速？"
        assert got.answer_state == AnswerState.UNANSWERED

        registry.close()

    def test_update_answer_state(self, tmp_path):
        db_path = tmp_path / "questions.db"
        registry = QuestionRegistry(db_path)

        q = Question(id="Q002", text="测试问题？", owner="测试公司")
        registry.add(q)

        registry.update_answer_state("Q002", AnswerState.SUPPORTED, supporting_claim_id="claim-001")
        got = registry.get("Q002")
        assert got.answer_state == AnswerState.SUPPORTED

        registry.close()

    def test_list_by_owner(self, tmp_path):
        db_path = tmp_path / "questions.db"
        registry = QuestionRegistry(db_path)

        registry.add(Question(id="Q003", text="问题A？", owner="公司A"))
        registry.add(Question(id="Q004", text="问题B？", owner="公司A"))
        registry.add(Question(id="Q005", text="问题C？", owner="公司B"))

        qs = registry.list_by_owner("公司A")
        assert len(qs) == 2

        registry.close()

    def test_count_by_answer_state(self, tmp_path):
        db_path = tmp_path / "questions.db"
        registry = QuestionRegistry(db_path)

        registry.add(Question(id="Q006", text="问题？", owner="测试"))
        registry.update_answer_state("Q006", AnswerState.PARTIAL)

        counts = registry.count_by_answer_state()
        assert counts.get("partial", 0) == 1

        registry.close()
