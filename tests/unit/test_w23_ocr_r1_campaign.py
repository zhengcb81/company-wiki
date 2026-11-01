"""R1 campaign ledger and budget contracts (TDD, no model, no network)."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.ocr_comparison.campaign import (  # noqa: E402
    LedgerCorrupt,
    create_ledger,
    load_ledger,
    record,
    remaining_seconds,
    request_budget,
)


def test_ledger_create_load_roundtrip(tmp_path):
    path = tmp_path / "ledger.json"
    create_ledger(path, plan_id="w23-ocr-r1-2026-10-31", budget_seconds=1800.0)
    ledger = load_ledger(path)
    assert ledger["budget_seconds"] == 1800.0
    assert ledger["spent_seconds"] == 0.0
    assert ledger["entries"] == []
    assert remaining_seconds(ledger) == 1800.0
    with pytest.raises(FileExistsError):
        create_ledger(path, plan_id="x", budget_seconds=1800.0)


def test_ledger_record_updates_remaining_and_persists(tmp_path):
    path = tmp_path / "ledger.json"
    create_ledger(path, plan_id="p", budget_seconds=100.0)
    ledger = load_ledger(path)
    record(ledger, path, arm="X1F", page_id="p1", seconds=40.5, status="ok")
    reloaded = load_ledger(path)
    assert reloaded["spent_seconds"] == 40.5
    assert remaining_seconds(reloaded) == pytest.approx(59.5)
    assert reloaded["entries"][0]["page_id"] == "p1"


def test_ledger_record_refuses_overspend(tmp_path):
    path = tmp_path / "ledger.json"
    create_ledger(path, plan_id="p", budget_seconds=10.0)
    ledger = load_ledger(path)
    with pytest.raises(ValueError):
        record(ledger, path, arm="X1F", page_id="p1", seconds=11.0, status="ok")
    # the refused entry must not be persisted
    assert load_ledger(path)["spent_seconds"] == 0.0


@pytest.mark.parametrize("corrupt", [
    "not json at all {{{",
    '{"schema_version": "cwp-ocr-campaign-ledger/2", "budget_seconds": 1, "spent_seconds": 0, "entries": []}',
    '{"schema_version": "cwp-ocr-campaign-ledger/1", "budget_seconds": -5, "spent_seconds": 0, "entries": []}',
    '{"schema_version": "cwp-ocr-campaign-ledger/1", "budget_seconds": 10, "spent_seconds": 99, "entries": []}',
    '{"schema_version": "cwp-ocr-campaign-ledger/1", "budget_seconds": 10, "spent_seconds": 5, '
    '"entries": [{"arm": "X1F", "page_id": "p", "seconds": "many", "status": "ok"}]}',
])
def test_corrupt_ledger_is_refused_not_renewed(tmp_path, corrupt):
    path = tmp_path / "ledger.json"
    path.write_text(corrupt, encoding="utf-8")
    with pytest.raises(LedgerCorrupt):
        load_ledger(path)


def test_request_budget_caps_at_180_and_stops_when_exhausted(tmp_path):
    path = tmp_path / "ledger.json"
    create_ledger(path, plan_id="p", budget_seconds=1800.0)
    assert request_budget(load_ledger(path)) == 180.0
    ledger = load_ledger(path)
    record(ledger, path, arm="X1F", page_id="p1", seconds=1750.0, status="ok")
    assert request_budget(load_ledger(path)) == pytest.approx(50.0)
    record(load_ledger(path), path, arm="X1F", page_id="p2", seconds=50.0, status="timeout")
    assert remaining_seconds(load_ledger(path)) == pytest.approx(0.0)
    assert request_budget(load_ledger(path)) == 0.0
