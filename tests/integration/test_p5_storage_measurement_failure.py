"""Missing post-operation observations are unknown, never copied from before."""
import sqlite3

from support.p5_storage_catalog_fixture import build_catalog
from legacy_storage import shrink


def test_vacuum_readback_failure_does_not_invent_after_values(tmp_path, monkeypatch):
    config, _, _ = build_catalog(tmp_path)
    snapshot = shrink._snapshot
    calls = 0

    def unavailable_after(database, catalog):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise sqlite3.OperationalError("injected post-operation readback unavailable")
        return snapshot(database, catalog)

    monkeypatch.setattr(shrink, "_snapshot", unavailable_after)
    report = shrink.run_vacuum(config)
    assert report["status"] == "failed"
    assert report["database_bytes_before"] > 0
    assert report["database_bytes_after"] is None
    assert report["source_facts_after"] is None
    assert report["after_measurement_available"] is False
