"""Contracts for the live worker's explicit source-only stage policy."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import importlib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _policy_module():
    return importlib.import_module("company_wiki.source_catalog.scheduler_policy")


@dataclass
class _Report:
    completed: int = 1
    partial: int = 0
    unsupported: int = 0
    failed: int = 0
    failure_scope: str | None = None

    def to_dict(self):
        return dict(self.__dict__)


class _Catalog:
    def __init__(self, events: list[tuple[str, str]]):
        self.events = events

    def scan(self, *, progress=None):
        self.events.append(("call", "scan"))
        return _Report()

    def normalize(self, *, limit, progress=None, **kwargs):
        del limit, progress, kwargs
        self.events.append(("call", "normalize"))
        return _Report()

    def backfill_text_fingerprints(self, *, limit, progress=None,
                                    should_stop=None, retry_limit=3,
                                    retry_backoff_seconds=900, **kwargs):
        del limit, progress, should_stop, retry_limit, retry_backoff_seconds, kwargs
        self.events.append(("call", "backfill_text_fingerprints"))
        return _Report()

    def extract_sections(self, *, limit, progress=None, should_stop=None, **kwargs):
        del limit, progress, should_stop, kwargs
        self.events.append(("call", "extract_sections"))
        return _Report()

    def summarize_with_llm(self, **kwargs):
        self.events.append(("call", "summarize_with_llm"))
        return _Report()

    def export_indexes(self, *, progress=None):
        self.events.append(("call", "export_indexes"))
        return {"index": Path("index.md")}


class _Idle:
    def idle_seconds(self):
        return 0.0

    def on_battery(self):
        return False


def _worker(tmp_path, catalog):
    from company_wiki.source_catalog.worker import SourceCatalogWorker, WorkerConfig

    return SourceCatalogWorker(
        catalog,
        WorkerConfig(
            runtime_config=tmp_path / "config.yaml",
            scan_interval_seconds=60,
            export_interval_seconds=60,
            poll_interval_seconds=30,
            active_poll_interval_seconds=1,
            idle_seconds_required=600,
            normalize_batch_size=1,
            llm_summary_batch_size=1,
            llm_max_input_chars=1000,
            llm_max_output_tokens=200,
            llm_retry_backoff_seconds=60,
            allow_processing_on_battery=False,
            require_user_idle=False,
        ),
        state_path=tmp_path / "worker_state.json",
        idle_detector=_Idle(),
        llm_client_factory=lambda: object(),
    )


def test_public_policy_freezes_exact_source_only_stage_order_and_methods():
    public = importlib.import_module("company_wiki.source_catalog")
    policy_module = _policy_module()
    policy = policy_module.SourceOnlySchedulerPolicy()

    assert public.SourceOnlySchedulerPolicy is policy_module.SourceOnlySchedulerPolicy
    assert policy.to_dict() == {
        "schema_version": "1.0.0",
        "stages": [
            {"stage": "scanning", "catalog_method": "scan"},
            {"stage": "normalizing", "catalog_method": "normalize"},
            {"stage": "fingerprinting", "catalog_method": "backfill_text_fingerprints"},
            {"stage": "section_extracting", "catalog_method": "extract_sections"},
            {
                "stage": "summarizing",
                "catalog_method": "summarize_with_llm",
            },
            {"stage": "exporting", "catalog_method": "export_indexes"},
        ],
    }
    serialized = str(policy.to_dict()).casefold()
    for forbidden in (
        "research",
        "valuation",
        "assessment",
        "rating",
        "target_price",
        "stockwiki",
        "wiki_writer",
    ):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    ("stage", "method"),
    (
        ("unknown", "scan"),
        ("scanning", "normalize"),
        ("scanning", "run_research"),
        ("summarizing", "write_valuation"),
        ("exporting", "wiki_writer"),
    ),
)
def test_policy_fails_closed_for_unknown_mismatched_or_research_dispatch(
    stage, method
):
    policy_module = _policy_module()
    with pytest.raises(policy_module.SourceOnlySchedulerPolicyError):
        policy_module.SourceOnlySchedulerPolicy().require_dispatch(stage, method)


def test_worker_guards_each_catalog_call_in_exact_stage_order(tmp_path, monkeypatch):
    policy_module = _policy_module()
    events: list[tuple[str, str]] = []
    catalog = _Catalog(events)
    real = policy_module.SourceOnlySchedulerPolicy.require_dispatch

    def traced(self, stage, method):
        events.append(("guard", f"{getattr(stage, 'value', stage)}:{method}"))
        return real(self, stage, method)

    monkeypatch.setattr(
        policy_module.SourceOnlySchedulerPolicy, "require_dispatch", traced
    )
    _worker(tmp_path, catalog).run_cycle(now=10_000)

    assert events == [
        ("guard", "scanning:scan"),
        ("call", "scan"),
        ("guard", "normalizing:normalize"),
        ("call", "normalize"),
        ("guard", "fingerprinting:backfill_text_fingerprints"),
        ("call", "backfill_text_fingerprints"),
        ("guard", "section_extracting:extract_sections"),
        ("call", "extract_sections"),
        ("guard", "summarizing:summarize_with_llm"),
        ("call", "summarize_with_llm"),
        ("guard", "exporting:export_indexes"),
        ("call", "export_indexes"),
    ]


def test_policy_rejection_happens_before_catalog_or_llm_call(tmp_path, monkeypatch):
    policy_module = _policy_module()
    events: list[tuple[str, str]] = []
    catalog = _Catalog(events)

    def reject(_self, _stage, _method):
        raise policy_module.SourceOnlySchedulerPolicyError("rejected by fixture")

    monkeypatch.setattr(
        policy_module.SourceOnlySchedulerPolicy, "require_dispatch", reject
    )
    with pytest.raises(policy_module.SourceOnlySchedulerPolicyError):
        _worker(tmp_path, catalog).run_cycle(now=10_000)
    assert events == []


def test_worker_has_no_dynamic_catalog_dispatch_or_legacy_scheduler_import():
    path = ROOT / "src" / "company_wiki" / "source_catalog" / "worker.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = []
    catalog_calls = []
    dynamic_catalog_dispatch = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            value = node.func.value
            if (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and value.value.id == "self"
                and value.attr == "catalog"
            ):
                catalog_calls.append(node.func.attr)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and node.args
            and isinstance(node.args[0], ast.Attribute)
            and isinstance(node.args[0].value, ast.Name)
            and node.args[0].value.id == "self"
            and node.args[0].attr == "catalog"
        ):
            dynamic_catalog_dispatch.append(node.lineno)

    assert set(catalog_calls) == {
        "scan",
        "normalize",
        "backfill_text_fingerprints",
        "extract_sections",
        "summarize_with_llm",
        "export_indexes",
    }
    assert dynamic_catalog_dispatch == []
    assert not any(name in {"scheduler", "scripts.scheduler"} for name in imports)
    assert "scheduler_policy.require_dispatch" in path.read_text(encoding="utf-8")


def test_scheduler_policy_docs_state_source_only_and_on_demand_quality_boundary():
    docs = (ROOT / "docs" / "source-catalog.md").read_text(encoding="utf-8")
    for phrase in (
        "Source-only scheduler policy",
        "scanning → normalizing → fingerprinting → summarizing → exporting",
        "fail-closed",
        "workload=`source`",
        "extraction-quality",
        "on-demand",
        "不调度投资研究",
    ):
        assert phrase in docs
