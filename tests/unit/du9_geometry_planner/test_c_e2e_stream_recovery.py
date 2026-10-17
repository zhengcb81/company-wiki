"""Node C: one real parse round through the public entries only.

Simulates the physical page event stream of the 96-page hand calculation,
proves the back is not starved under the unchanged shared limit, proves
stop/serialize/replay equals a one-shot run, and proves by counters (not
timing) that the component performs no IO, model calls or native parsing.
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import json
import os
from pathlib import Path
import socket
import sys

import company_wiki.document_understanding.geometry_intent as geometry_intent
from company_wiki.document_understanding.geometry_intent import (
    admit_geometry_request,
    new_admission_state,
    plan_geometry_requests,
    summarize_admission_state,
)
from company_wiki.document_understanding.layout_hints.contract import WorkBudget

from . import helpers

ROOT = Path(__file__).resolve().parents[3]


def _plan(fixture):
    return plan_geometry_requests(
        fixture["policy"], fixture["windows"],
        page_count=fixture["page_count"], limits=fixture["limits"],
        work_budget=WorkBudget(max_work_units=2_000_000),
    )


def _run_stream(plan, state, fixture, events, *, start_position: int = 1):
    """Sequential physical-page arrival; a repeated page-71 ACK is injected."""
    decisions = []
    for position, (page, keys) in enumerate(events, start=start_position):
        decision, state = admit_geometry_request(
            plan, state, page=page, window_keys=keys,
            tabular_evidence="observed_candidate",
            remaining=fixture["limits"]["max_pages"],
        )
        decisions.append(decision)
        if position == 71:  # repeated ACK of an already-charged page
            ack, state = admit_geometry_request(
                plan, state, page=71, window_keys=["w-proj-a", "w-proj-parent"],
                tabular_evidence="observed_candidate",
                remaining=fixture["limits"]["max_pages"],
            )
            decisions.append(ack)
    return decisions, state


def test_full_stream_back_not_starved_and_exact_causal_counts():
    fixture = helpers.load_fixture()
    limits_before = json.dumps(fixture["limits"], sort_keys=True)
    budget = WorkBudget(max_work_units=2_000_000)
    plan = _plan(fixture)
    state = new_admission_state(plan)
    used_before = budget.used

    decisions, state = _run_stream(plan, state, fixture, helpers.all_candidate_events(fixture))
    summary = summarize_admission_state(plan, state)

    # The deep windows get their real机会 under the unchanged 64-page limit.
    assert summary["window_admissions"]["w-attach-op"] == 7
    assert (
        summary["window_admissions"]["w-proj-a"] + summary["window_admissions"]["w-proj-parent"] == 16
    )
    assert summary["window_admissions"]["w-proj-b"] == 0  # transparent, fully nested
    assert summary["spent"] == {"pages": 64, "requests": 64}, "exactly the shared limit, never more"

    # Frozen causal accounting of the whole round.
    assert summary["reason_counts"] == {
        "admitted": 64,
        "deduplicated": 1,
        "not_found": 0,
        "unknown": 0,
        "exhausted": 29,
        "cancelled": 3,
        "rejected": 0,
    }
    assert summary["not_arrived"] == 0, "every reserved page arrived in this round"
    assert summary["class_spent"] == {
        "administrative": 6, "context": 26, "operating": 16, "project": 16,
    }
    assert summary["window_admissions"] == {
        "w-toc": 0, "w-admin": 6, "w-risk": 11, "w-notes": 13, "w-gov": 2,
        "w-mda": 6, "w-outlook": 3, "w-attach-op": 7,
        "w-proj-a": 9, "w-proj-parent": 7, "w-proj-b": 0,
    }

    # The repeated ACK never double-charged.
    ack = decisions[71]  # index 71 is the injected page-71 ACK after event 71
    assert ack["decision"] == "deduplicated"
    assert ack["charged"] == {"pages": 0, "requests": 0}

    # Caller limits and the budget object are untouched, only consumed forward.
    assert json.dumps(fixture["limits"], sort_keys=True) == limits_before
    assert budget.max_work_units == 2_000_000
    assert budget.used >= used_before


def test_stop_serialize_replay_equals_one_shot_run():
    fixture = helpers.load_fixture()
    plan = _plan(fixture)
    events = helpers.all_candidate_events(fixture)

    # One-shot reference run.
    state = new_admission_state(plan)
    decisions_full, state_full = _run_stream(plan, state, fixture, events)
    summary_full = summarize_admission_state(plan, state_full)

    # Interrupted run: stop after page 48, JSON round-trip BOTH plan and
    # state, then continue the identical stream.
    state = new_admission_state(plan)
    decisions_head, state = _run_stream(plan, state, fixture, events[:48])
    plan_restored = json.loads(json.dumps(plan, ensure_ascii=False))
    state_restored = json.loads(json.dumps(state, ensure_ascii=False))
    decisions_tail, state_restored = _run_stream(
        plan_restored, state_restored, fixture, events[48:], start_position=49
    )
    summary_restored = summarize_admission_state(plan_restored, state_restored)

    assert decisions_head == decisions_full[: len(decisions_head)]
    assert decisions_tail == decisions_full[len(decisions_head):]
    assert summary_restored == summary_full


def test_component_performs_no_io_model_or_native_parse():
    """Counter proof: zero filesystem/network calls; stdlib+WorkBudget imports only."""
    fixture = helpers.load_fixture()
    counters = {"open": 0, "stat": 0, "scandir": 0, "socket": 0}

    real_open, real_stat, real_scandir, real_socket = (
        builtins.open, os.stat, os.scandir, socket.socket,
    )

    def counting_open(*args, **kwargs):
        counters["open"] += 1
        return real_open(*args, **kwargs)

    def counting_stat(*args, **kwargs):
        counters["stat"] += 1
        return real_stat(*args, **kwargs)

    def counting_scandir(*args, **kwargs):
        counters["scandir"] += 1
        return real_scandir(*args, **kwargs)

    def counting_socket(*args, **kwargs):
        counters["socket"] += 1
        return real_socket(*args, **kwargs)

    builtins.open, os.stat, os.scandir, socket.socket = (
        counting_open, counting_stat, counting_scandir, counting_socket,
    )
    try:
        plan = _plan(fixture)
        state = new_admission_state(plan)
        _run_stream(plan, state, fixture, helpers.all_candidate_events(fixture))
        summarize_admission_state(plan, state)
    finally:
        builtins.open, os.stat, os.scandir, socket.socket = (
            real_open, real_stat, real_scandir, real_socket,
        )

    assert counters == {"open": 0, "stat": 0, "scandir": 0, "socket": 0}

    # Static proof: the package imports stdlib plus the WorkBudget contract only,
    # and never *references* the matcher/parser/model internals (docstrings may
    # name them in prose; code must not).
    package_dir = Path(geometry_intent.__file__).parent
    imported: set[str] = set()
    referenced: set[str] = set()
    for py_file in sorted(package_dir.glob("*.py")):
        text = py_file.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Name):
                referenced.add(node.id)
            elif isinstance(node, ast.Attribute):
                referenced.add(node.attr)
    for name in imported:
        root = name.split(".")[0]
        if root == "company_wiki":
            assert name == "company_wiki.document_understanding.layout_hints.contract", name
        else:
            assert root in sys.stdlib_module_names, f"non-stdlib import: {name}"
    forbidden = ("_match_rule", "find_tables", "TextPage", "strategy_binding", "llm_client")
    for token in forbidden:
        assert token not in referenced, f"code must not reference {token}"


def test_fixture_and_production_config_untouched():
    """Isolation receipt: inputs and production config keep SHA + mtime."""
    fixture_path = helpers.FIXTURE_PATH
    config_path = ROOT / "config" / "source_catalog.yaml"

    def fingerprint(path: Path) -> tuple[str, int]:
        return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns

    before = {"fixture": fingerprint(fixture_path)}
    if config_path.exists():
        before["config"] = fingerprint(config_path)

    fixture = helpers.load_fixture()
    plan = _plan(fixture)
    state = new_admission_state(plan)
    _run_stream(plan, state, fixture, helpers.all_candidate_events(fixture))

    assert fingerprint(fixture_path) == before["fixture"]
    if "config" in before:
        assert fingerprint(config_path) == before["config"], "production config must not be written"


def test_public_surface_is_exactly_the_frozen_entries():
    expected_functions = {
        "plan_geometry_requests",
        "admit_geometry_request",
        "new_admission_state",
        "summarize_admission_state",
    }
    expected_constants = {
        "DEMAND_CLASSES", "DISCOVER_VALUES", "EVIDENCE_VALUES", "FINE_VALUES",
        "NAVIGATION_VALUES", "SCHEMA_ADMISSION", "SCHEMA_PLAN", "SCHEMA_POLICY",
        "SCHEMA_RUN_SUMMARY", "SCHEMA_STATE",
    }
    assert set(geometry_intent.__all__) == expected_functions | expected_constants
    for name in expected_functions:
        assert callable(getattr(geometry_intent, name))
