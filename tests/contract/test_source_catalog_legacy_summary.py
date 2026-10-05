"""Keep the legacy on-demand summary contract during storage migration."""

from __future__ import annotations

import json
from pathlib import Path


def _catalog(tmp_path: Path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "meeting.txt").write_text(
        "2025年公司收入增长20%，新增客户12家，产能达到100万台。",
        encoding="utf-8",
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("sources", sources, "directory"),),
        )
    )
    catalog.scan()
    catalog.normalize()
    return catalog, sources


class _Response:
    def __init__(self, content: str, *, success: bool = True, error: str = ""):
        self.content = content
        self.success = success
        self.error = error
        self.model = "MiniMax-M3"
        self.usage = {"total_tokens": 321}


class _FakeLLM:
    provider = "minimax"
    model = "MiniMax-M3"

    def __init__(self, content: str):
        self.content = content
        self.prompts: list[str] = []
        self.generate_kwargs: list[dict] = []

    def generate(self, prompt: str, **kwargs):
        self.prompts.append(prompt)
        self.generate_kwargs.append(kwargs)
        return _Response(self.content)


class _ProviderFailingLLM(_FakeLLM):
    def generate(self, prompt: str, **kwargs):
        self.prompts.append(prompt)
        self.generate_kwargs.append(kwargs)
        response = _Response("", success=False, error="HTTP 429 rate limited")
        response.provider = "mimo"
        response.model = "mimo-v2.5-pro"
        return response


def test_llm_summary_is_source_bound_auditable_and_replaces_extractive_summary(
    tmp_path,
):
    catalog, source_root = _catalog(tmp_path)
    before = source_root.joinpath("meeting.txt").read_bytes()
    catalog.summarize()
    client = _FakeLLM(
        json.dumps(
            {
                "overview": "文档记录了2025年的经营进展。",
                "key_facts": [
                    "公司收入增长20%。",
                    "新增客户12家。",
                    "产能达到100万台。",
                ],
                "topics": ["收入", "客户", "产能"],
                "limitations": ["仅依据当前规范化文本。"],
            },
            ensure_ascii=False,
        )
    )

    progress_events: list[dict] = []
    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=1200,
        progress=lambda **details: progress_events.append(details),
    )

    assert report.completed == 1
    row = catalog.query(limit=1)[0]
    content = Path(row["summary_path"]).read_text(encoding="utf-8")
    assert "summary_method: llm" in content
    assert "llm_provider: minimax" in content
    assert "llm_model: MiniMax-M3" in content
    assert "公司收入增长20%" in content
    assert row["source_id"] in content
    assert source_root.joinpath("meeting.txt").read_bytes() == before
    summary_artifacts = [a for a in row["artifacts"] if a["artifact_role"] == "summary"]
    assert len(summary_artifacts) == 1
    assert summary_artifacts[0]["generator_name"] == "source_catalog_llm_summary"
    assert len(client.generate_kwargs) == 1
    assert client.generate_kwargs[0]["max_tokens"] == 1200
    assert client.generate_kwargs[0]["json_mode"] is True
    assert progress_events == [
        {
            "current_path": str(source_root.joinpath("meeting.txt")),
            "current": 1,
            "total": 1,
            "detail": "calling LLM summary",
        }
    ]


def test_llm_summary_deterministically_bounds_overlong_lists(tmp_path):
    catalog, _ = _catalog(tmp_path)
    client = _FakeLLM(
        json.dumps(
            {
                "overview": "文档记录了可核对的经营数据。",
                "key_facts": [f"事实{i}" for i in range(10)],
                "topics": [f"主题{i}" for i in range(10)],
                "limitations": [f"局限{i}" for i in range(6)],
            },
            ensure_ascii=False,
        )
    )

    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=2400,
    )

    assert report.completed == 1
    assert report.failed == 0
    content = Path(catalog.query(limit=1)[0]["summary_path"]).read_text(
        encoding="utf-8"
    )
    assert "事实7" in content and "事实8" not in content
    assert "主题7" in content and "主题8" not in content
    assert "局限3" in content and "局限4" not in content


def test_llm_summary_rejects_generated_investment_conclusions(tmp_path):
    catalog, _ = _catalog(tmp_path)
    client = _FakeLLM(
        json.dumps(
            {
                "overview": "建议买入评级，目标价100元。",
                "key_facts": ["公司收入增长20%。"],
                "topics": [],
                "limitations": [],
            },
            ensure_ascii=False,
        )
    )

    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )

    assert report.completed == 0
    assert report.failed == 1
    assert (
        report.error
        == "LLMSummaryError: LLM response contains a forbidden investment conclusion"
    )
    assert report.failed_document_id
    assert report.failure_scope == "permanent_document"
    # CW-3.5 / Phase 10: permanent_document errors still get recorded
    # in the failure table with a long retry window, but the report's
    # retry_after/retry_count fields are None (no immediate backoff needed).
    assert report.retry_after is not None or report.retry_count is None
    assert catalog.query(limit=1)[0]["summary_path"] is None

    failure = catalog.store.fetchone(
        "SELECT * FROM llm_summary_failures WHERE document_id=?",
        (report.failed_document_id,),
    )
    assert failure is not None
    assert failure["failure_scope"] == "permanent_document"
    assert failure["attempt_count"] >= 1
    assert failure["retry_after"] == report.retry_after


def test_document_scoped_llm_failure_does_not_block_the_next_document(tmp_path):
    from company_wiki.source_catalog.store import read_pipeline_status

    catalog, source_root = _catalog(tmp_path)
    bad_client = _FakeLLM(
        json.dumps(
            {
                "overview": "建议买入评级。",
                "key_facts": ["公司收入增长20%。"],
                "topics": [],
                "limitations": [],
            },
            ensure_ascii=False,
        )
    )
    first = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: bad_client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )
    assert first.failure_scope in ("document", "permanent_document")

    (source_root / "second.txt").write_text(
        "2026年新增订单20亿元，交付产品1000台。", encoding="utf-8"
    )
    catalog.scan()
    catalog.normalize()
    good_client = _FakeLLM(
        json.dumps(
            {
                "overview": "文档记录新增订单与产品交付。",
                "key_facts": ["新增订单20亿元。", "交付产品1000台。"],
                "topics": ["订单", "交付"],
                "limitations": [],
            },
            ensure_ascii=False,
        )
    )

    second = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: good_client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )

    assert second.completed == 1
    assert second.failed == 0
    assert len(good_client.prompts) == 1
    status = read_pipeline_status(catalog.config.database_path)
    assert status["llm_summary"]["completed"] == 1
    assert status["llm_summary"]["failed"] == 1
    assert status["llm_summary"]["pending"] == 0

    no_retry_client = _FakeLLM(good_client.content)
    deferred_document = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: no_retry_client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )
    assert deferred_document.completed == 0
    assert deferred_document.failed == 0
    assert no_retry_client.prompts == []


def test_provider_failure_requests_global_retry_without_document_quarantine(tmp_path):
    catalog, _ = _catalog(tmp_path)
    client = _ProviderFailingLLM("")

    report = catalog.summarize_with_llm(
        limit=1,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )

    assert report.completed == 0
    assert report.failed == 1
    assert report.failure_scope == "global"
    assert report.retry_after is None
    assert report.retry_count is None
    assert "mimo/mimo-v2.5-pro" in report.error
    assert (
        catalog.store.fetchone("SELECT COUNT(*) AS count FROM llm_summary_failures")[
            "count"
        ]
        == 0
    )


def test_configured_llm_uses_mimo_when_primary_credentials_are_absent(monkeypatch):
    from company_wiki.source_catalog.llm_summarizer import build_configured_llm_client

    project = Path(__file__).resolve().parents[2]
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.setenv("MIMO_API_KEY", "test-only-placeholder")
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")

    client = build_configured_llm_client(project, project / "config.yaml")

    assert client.provider == "mimo"
    assert client.model == "mimo-v2.6-flash"
    assert client.available is True
    assert client.workload == "source"


def test_configured_llm_uses_project_dotenv_over_stale_inherited_keys(
    tmp_path, monkeypatch
):
    import config as config_module
    from company_wiki.source_catalog.llm_summarizer import build_configured_llm_client

    project = Path(__file__).resolve().parents[2]
    runtime_config = tmp_path / "config.yaml"
    runtime_config.write_text(
        """
llm:
  provider: minimax
  model: MiniMax-M3
  base_url: https://api.minimaxi.com/v1
  fallback:
    provider: mimo
    model: mimo-v2.5-pro
    base_url: https://token-plan-cn.xiaomimimo.com/v1
    enabled: true
    usage_scope: general
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "MINIMAX_API_KEY=file-primary-test-only\n"
        "MIMO_API_KEY=file-fallback-test-only\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "WIKI_ROOT", tmp_path)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.setenv("MINIMAX_API_KEY", "stale-primary-test-only")
    monkeypatch.setenv("MIMO_API_KEY", "stale-fallback-test-only")

    client = build_configured_llm_client(project, runtime_config)

    assert client.api_key == "file-primary-test-only"
    assert client.workload == "source"
    assert client.fallback_client is not None
    assert client.fallback_client.api_key == "file-fallback-test-only"
    assert client.fallback_client.workload == "source"
