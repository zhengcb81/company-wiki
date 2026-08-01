"""§10.7.5 FR-4: 单文档长耗时、PDF parser 与 LLM 等待可观测。"""

from __future__ import annotations

import json
import time
from pathlib import Path



def _live_status(
    tmp_path,
    *,
    elapsed=0,
    stage="normalizing",
    path="test.pdf",
    pid=99999,
    progress_current=0,
    progress_total=0,
    progress_detail=None,
):
    from company_wiki.source_catalog.control import WorkerController

    cd = tmp_path / ".source_catalog"
    cd.mkdir(parents=True, exist_ok=True)
    cfg = tmp_path / "config" / "source_catalog.yaml"
    wcfg = tmp_path / "config" / "source_catalog_worker.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("schema_version: '1.0'\n", encoding="utf-8")
    wcfg.write_text("schema_version: '1.0'\n", encoding="utf-8")
    now = time.time()
    runtime = {
        "schema_version": "1.0",
        "pid": pid,
        "executable": "C:/Python/python.exe",
        "creation_time": now - 1,
        "token": "abc",
        "started_at": now - elapsed - 10,
        "heartbeat_at": now,
        "worker_status": stage,
        "current_path": path,
        "current_path_started_at": now - elapsed,
        "current_path_elapsed_seconds": round(elapsed, 1),
        "progress_current": progress_current,
        "progress_total": progress_total,
        "progress_detail": progress_detail,
    }
    (cd / "worker_runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
    c = WorkerController(
        catalog_dir=cd,
        project_root=tmp_path,
        config_path=cfg,
        worker_config_path=wcfg,
        process_inventory_provider=lambda: {
            "production_workers": [],
            "foreign_workers": [],
            "pytest_temp_workers": [],
            "ignored_matching_processes": [],
            "inventory_error": None,
        },
    )
    c.process_identity = lambda p: (
        {
            "pid": p,
            "executable": runtime["executable"],
            "creation_time": runtime["creation_time"],
        }
        if p == pid
        else None
    )
    return c.status()


def test_runtime_exposes_current_path_and_elapsed(tmp_path):
    s = _live_status(tmp_path, elapsed=42.5)
    assert s["runtime_state"] == "running"
    assert s["current_path"] == "test.pdf"
    assert 42.5 <= s["current_path_elapsed_seconds"] < 44.0
    assert s["current_path_started_at"] is not None


def test_long_running_warning_triggers_when_elapsed_exceeds_180s(tmp_path):
    s = _live_status(tmp_path, elapsed=250)
    assert s["long_running_document_warning"] is True


def test_long_running_warning_false_when_under_180s(tmp_path):
    s = _live_status(tmp_path, elapsed=120)
    assert s["long_running_document_warning"] is False


def test_panel_shows_warning_for_long_running(tmp_path):
    ps1 = Path("scripts/source_catalog_control.ps1")
    content = ps1.read_text(encoding="utf-8", errors="replace")
    assert "long_running_document_warning" in content
    assert "current_path_elapsed_seconds" in content
    assert "WARNING" in content


def test_worker_status_exposes_progress_fields(tmp_path):
    s = _live_status(
        tmp_path,
        elapsed=10,
        progress_current=5,
        progress_total=100,
        progress_detail="page 5/100",
    )
    assert s["progress_current"] == 5
    assert s["progress_total"] == 100
    assert s["progress_detail"] == "page 5/100"
    assert s["worker_status"] == "normalizing"
