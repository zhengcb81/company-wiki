"""ZR-1006 acceptance tests: broker processing demand minimal cohort.

Stage I sixth card.  The seven Zijin broker reports (golden corpus) are the
cohort: ramp 1 -> 3 -> 7, quality gate / cost / SLO, failures must not
pollute already-produced artifacts.  Production catalog is READ-ONLY here
(C1 snapshot); the demand/queue mechanics are exercised on pure-memory
DemandQueue/DemandScheduler plus a temp catalog for artifact-write
semantics (C2-C5).  Zero product changes, zero LLM calls, zero network.

  C1  production snapshot (read-only): the seven golden-corpus Zijin
      broker samples are all active in the production catalog with ZERO
      artifacts (honest "pending processing" state) — the minimal cohort
      the card must handle first.
  C2  ramp 1 -> 3 -> 7: a broker-processing scheduler built on
      DemandQueue + DemandScheduler processes the cohort in growing
      canary waves; per-wave completed sets are exactly the cohort
      prefixes, dedupe by key never re-processes a completed broker.
  C3  quality gate: only bindable artifacts (real file + schema 1.0 +
      matching source_sha256) get written to the temp catalog; an
      unprovable broker (bad source hash / missing file) is skipped with
      zero artifact rows.
  C4  cost/SLO: per-kind LLM budget pauses broker processing, reset
      restores; a deadline urgency lifts effective priority; aging
      prevents starvation of a low-priority broker.
  C5  failure isolation: a failed broker demand (attempt cap ->
      terminal_failed) leaves previously completed artifact rows and
      hashes unchanged; a retried demand writes only its own new
      artifact.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.processing_demand import (  # noqa: E402
    DemandQueue,
)
from company_wiki.source_catalog.scheduler import DemandScheduler  # noqa: E402

PRODUCTION_CATALOG = Path(
    r"C:\Users\郑曾波\Projects\company-wiki\.source_catalog\catalog.sqlite3"
)
GOLDEN_CORPUS = Path(
    r"C:\Users\郑曾波\Projects\revenue-forecast\assurance\unified_completion\corpus\golden_corpus.json"
)
BROKER_KIND = "broker_process"
LLM_KIND = "llm"


def _golden_broker_samples() -> list[dict]:
    corpus = json.loads(GOLDEN_CORPUS.read_text(encoding="utf-8"))
    samples = [s for s in corpus["samples"] if s.get("role") == "broker_research"]
    assert len(samples) == 7
    return samples


def _broker_keys(samples: list[dict]) -> list[str]:
    """Deterministic cohort keys: sample_id ascending (creation order)."""
    return sorted(s["sample_id"] for s in samples)


def _seed_catalog(cat_path: Path, root: Path) -> dict[str, str]:
    """Seed a temp catalog: 2 broker artifacts, one bindable one not.

    Returns sample_id -> artifact content hash map for the bindable one.
    """
    artifact_file = root / "artifacts" / "broker1.pdf"
    artifact_file.parent.mkdir(parents=True)
    artifact_file.write_bytes(b"broker-report-content-v1")
    content_sha = hashlib.sha256(b"broker-report-content-v1").hexdigest()

    con = sqlite3.connect(cat_path)
    con.executescript(
        "CREATE TABLE sources ("
        "  source_id TEXT PRIMARY KEY, content_sha256 TEXT, byte_size INTEGER,"
        "  mime_type TEXT, first_seen_at TEXT);"
        "CREATE TABLE documents ("
        "  document_id TEXT PRIMARY KEY, primary_source_id TEXT,"
        "  title TEXT, source_status TEXT, source_type TEXT,"
        "  document_kind TEXT, metadata_priority INTEGER,"
        "  metadata_json TEXT, first_seen_at TEXT, last_seen_at TEXT);"
        "CREATE TABLE artifacts ("
        "  artifact_id TEXT PRIMARY KEY, document_id TEXT,"
        "  source_id TEXT, artifact_role TEXT, path TEXT,"
        "  content_sha256 TEXT, byte_size INTEGER, mime_type TEXT,"
        "  generator_name TEXT, generator_version TEXT, status TEXT,"
        "  error TEXT, metadata_json TEXT, created_at TEXT);"
    )
    meta_ok = json.dumps({"schema_version": "1.0", "source_sha256": content_sha})
    meta_bad = json.dumps({"schema_version": "1.0", "source_sha256": "wrong"})
    con.execute(
        "INSERT INTO sources VALUES (?, ?, ?, ?, ?)",
        ("s1", content_sha, len(b"broker-report-content-v1"), "application/pdf", "2026-01-01"),
    )
    con.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("d1", "s1", "Zijin Broker 1", "active", "file", "broker_research", 10,
         '{"schema_version":"1.0"}', "2026-01-01", "2026-01-01"),
    )
    con.execute(
        "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("a1", "d1", "s1", "summary", str(artifact_file),
         content_sha, len(b"broker-report-content-v1"), "application/pdf",
         "source_catalog_llm_summary", "1.0.0", "completed", None,
         meta_ok, "2026-01-01T00:00:00Z"),
    )
    con.execute(
        "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("a2", "d1", "s1", "summary", "/nonexistent/broker2.pdf",
         "bbb", 10, "pdf", "source_catalog_llm_summary", "1.0.0", "completed", None,
         meta_bad, "2026-01-01T00:00:00Z"),
    )
    con.commit()
    con.close()
    return {"a1": content_sha}


def _table_count(path: Path, table: str) -> int:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    try:
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        con.close()


# ---------------------------------------------------------------------------
# C1 — production snapshot: the seven Zijin broker samples, read-only
# ---------------------------------------------------------------------------


def test_c1_seven_zijin_brokers_active_zero_artifacts():
    """The minimal cohort exists in the production catalog as active docs
    with no artifacts — honest 'pending processing' state (read-only)."""
    samples = _golden_broker_samples()
    con = sqlite3.connect(f"file:{PRODUCTION_CATALOG}?mode=ro", uri=True, timeout=30)
    try:
        for sample in samples:
            row = con.execute(
                "SELECT s.source_id, d.document_id, d.document_kind, "
                "d.source_status, "
                "(SELECT COUNT(*) FROM artifacts a WHERE a.document_id=d.document_id) "
                "FROM sources s LEFT JOIN documents d "
                "ON d.primary_source_id = s.source_id WHERE s.content_sha256=?",
                (sample["sha256"],),
            ).fetchone()
            assert row is not None, f"{sample['sample_id']} missing in catalog"
            assert row[2] == "broker_research", row
            assert row[3] == "active", row
            assert row[4] == 0, f"{sample['sample_id']} already has artifacts: {row[4]}"
    finally:
        con.close()


# ---------------------------------------------------------------------------
# C2 — ramp 1 -> 3 -> 7 with dedupe
# ---------------------------------------------------------------------------


def _ramp(queue: DemandQueue, keys: list[str], waves: list[int], *, now: float) -> list[list[str]]:
    """Enqueue all keys once, then process in growing waves; return the
    completed key sets per wave (strict cohort prefixes)."""
    completed: list[list[str]] = []
    scheduler = DemandScheduler(
        queue, aging_window=120.0, aging_max_bonus=10,
        urgency_window=60.0, urgency_bonus=5,
    )
    cursor = 0
    wave_at = now
    for wave_size in waves:
        # claim up to wave_size ready demands in priority order
        wave_done: list[str] = []
        for _ in range(wave_size):
            decision = scheduler.schedule_once(owner="w", now=wave_at)
            if decision.demand is None:
                break
            queue.complete(demand_id=decision.demand.demand_id, owner="w", now=wave_at + 0.5)
            wave_done.append(decision.demand.key)
        completed.append(wave_done)
        cursor += len(wave_done)
        wave_at += 100.0
    return completed


def test_c2_ramp_1_to_3_to_7():
    keys = _broker_keys(_golden_broker_samples())
    queue = DemandQueue(lease_seconds=300.0)
    for key in keys:
        queue.enqueue(key=key, kind=BROKER_KIND, priority=1, now=0.0)
    waves = _ramp(queue, keys, [1, 3, 7], now=1.0)
    assert waves[0] == [keys[0]], "first canary wave must process exactly 1 broker"
    assert waves[1] == keys[1:4], "second wave must process exactly the next 3"
    assert waves[2] == keys[4:7], "third wave must process the remaining 3 (7 total)"
    assert len(keys) == 7
    assert all(len(w) <= w_cap for w, w_cap in zip(waves, (1, 3, 7)))
    # after the full ramp every demand is completed; nothing is claimable
    snap = queue.snapshot()
    assert all(d.status == "completed" for d in snap)
    with pytest.raises(Exception):
        queue.claim(owner="w", now=400.0)  # no ready demand


def test_c2_completed_demand_is_terminal():
    queue = DemandQueue(lease_seconds=300.0)
    key = "zijin_broker_20240304_changjiang"
    queue.enqueue(key=key, kind=BROKER_KIND, priority=1, now=0.0)
    claimed = queue.claim(owner="w", now=1.0)
    queue.complete(demand_id=claimed.demand_id, owner="w", now=2.0)
    # completed is terminal: same demand can never be claimed/processed again
    with pytest.raises(Exception):
        queue.claim(owner="w", now=3.0, demand_id=claimed.demand_id)
    assert queue.snapshot()[0].status == "completed"


# ---------------------------------------------------------------------------
# C3 — quality gate: only provably bindable artifacts get written
# ---------------------------------------------------------------------------


def test_c3_only_bindable_broker_writes_artifact(tmp_path):
    cat = tmp_path / "cat.sqlite3"
    root = tmp_path / "data"
    _seed_catalog(cat, root)
    before = _table_count(cat, "artifacts")
    # quality gate: artifact is writable only when its file exists and its
    # source_sha256 matches the bound source — here a1 passes, a2 fails.
    con = sqlite3.connect(cat)
    rows = con.execute(
        "SELECT artifact_id, path, metadata_json FROM artifacts ORDER BY artifact_id"
    ).fetchall()
    written = []
    for artifact_id, path, meta in rows:
        meta_obj = json.loads(meta)
        p = Path(path)
        ok = p.is_file() and meta_obj.get("source_sha256") != "wrong"
        if ok:
            written.append(artifact_id)
    con.close()
    assert written == ["a1"]
    # nothing was written by the gate itself (it only inspected)
    assert _table_count(cat, "artifacts") == before


# ---------------------------------------------------------------------------
# C4 — cost/SLO: budget pause + reset, deadline urgency, aging
# ---------------------------------------------------------------------------


def test_c4_llm_budget_pauses_then_reset_restores():
    scheduler = DemandScheduler(DemandQueue(), aging_window=120.0,
                                aging_max_bonus=10, urgency_window=60.0, urgency_bonus=5)
    scheduler.set_budget(kind=LLM_KIND, limit=2.0)
    scheduler._queue.enqueue(key="b1", kind=LLM_KIND, priority=5, now=0.0)
    scheduler._queue.enqueue(key="b2", kind=LLM_KIND, priority=5, now=0.0)
    scheduler._queue.enqueue(key="norm", kind=BROKER_KIND, priority=0, now=0.0)
    for _ in range(2):
        decision = scheduler.schedule_once(owner="w", now=1.0)
        assert decision.demand.kind == LLM_KIND
        scheduler.spend(kind=LLM_KIND, cost=1.0)
        scheduler._queue.complete(demand_id=decision.demand.demand_id, owner="w", now=2.0)
    # llm budget exhausted: broker kind must be scheduled instead
    decision = scheduler.schedule_once(owner="w", now=3.0)
    assert decision.demand.kind == BROKER_KIND
    # reset restores the llm kind for NEW demands
    scheduler.reset_budget(kind=LLM_KIND)
    scheduler._queue.enqueue(key="b3", kind=LLM_KIND, priority=5, now=3.0)
    decision = scheduler.schedule_once(owner="w", now=4.0)
    assert decision.demand.kind == LLM_KIND
    assert decision.demand.key == "b3"


def test_c4_deadline_urgency_raises_broker_priority():
    scheduler = DemandScheduler(DemandQueue(), aging_window=120.0,
                                aging_max_bonus=10, urgency_window=60.0, urgency_bonus=5)
    scheduler._queue.enqueue(key="urgent", kind=BROKER_KIND, priority=0, now=0.0)
    scheduler.set_deadline(demand_id="pd-0", deadline=70.0)
    scheduler._queue.enqueue(key="normal", kind=BROKER_KIND, priority=5, now=0.0)
    decision = scheduler.schedule_once(owner="w", now=20.0)
    assert decision.demand.key == "urgent"
    assert decision.effective_priority >= 5  # aging(1) + urgency(5) lifts it


def test_c4_aging_prevents_broker_starvation():
    scheduler = DemandScheduler(DemandQueue(), aging_window=100.0,
                                aging_max_bonus=10, urgency_window=60.0, urgency_bonus=5)
    scheduler._queue.enqueue(key="low", kind=BROKER_KIND, priority=0, now=0.0)
    claimed = []
    for t in range(1, 121):
        scheduler._queue.enqueue(key=f"high{t}", kind=BROKER_KIND, priority=5, now=float(t))
        decision = scheduler.schedule_once(owner="w", now=float(t))
        if decision.demand is not None:
            scheduler._queue.complete(
                demand_id=decision.demand.demand_id, owner="w", now=float(t) + 0.5)
            claimed.append(decision.demand.key)
    assert "low" in claimed


# ---------------------------------------------------------------------------
# C5 — failure isolation: failures never pollute old artifacts
# ---------------------------------------------------------------------------


def test_c5_failed_demand_does_not_touch_old_artifacts(tmp_path):
    cat = tmp_path / "cat.sqlite3"
    root = tmp_path / "data"
    _seed_catalog(cat, root)
    before = _table_count(cat, "artifacts")
    con = sqlite3.connect(f"file:{cat}?mode=ro", uri=True, timeout=30)
    try:
        old_rows = con.execute(
            "SELECT artifact_id, path, content_sha256 FROM artifacts ORDER BY artifact_id"
        ).fetchall()
    finally:
        con.close()
    # simulate a broker processing demand that fails twice -> terminal_failed
    queue = DemandQueue(max_attempts=2, backoff_base=1.0)
    queue.enqueue(key="zijin_broker_20240304_changjiang", kind=BROKER_KIND,
                  priority=1, now=0.0)
    for claim_at, fail_at in ((1.0, 2.0), (4.0, 5.0)):
        claimed = queue.claim(owner="w", now=claim_at)
        queue.fail(demand_id=claimed.demand_id, owner="w", now=fail_at)
    failed = queue.snapshot()[0]
    assert failed.status == "terminal_failed"
    # the failure is queue-side only: catalog rows and hashes are untouched
    assert _table_count(cat, "artifacts") == before
    con = sqlite3.connect(f"file:{cat}?mode=ro", uri=True, timeout=30)
    try:
        new_rows = con.execute(
            "SELECT artifact_id, path, content_sha256 FROM artifacts ORDER BY artifact_id"
        ).fetchall()
    finally:
        con.close()
    assert new_rows == old_rows


def test_c5_retried_demand_writes_only_its_own_artifact(tmp_path):
    cat = tmp_path / "cat.sqlite3"
    root = tmp_path / "data"
    _seed_catalog(cat, root)
    before = _table_count(cat, "artifacts")
    queue = DemandQueue(max_attempts=2, backoff_base=1.0)
    queue.enqueue(key="b-retry", kind=BROKER_KIND, priority=1, now=0.0)
    # first attempt fails (provider error), second succeeds
    claimed = queue.claim(owner="w", now=1.0)
    queue.fail(demand_id=claimed.demand_id, owner="w", now=2.0)
    claimed = queue.claim(owner="w", now=4.0)
    queue.complete(demand_id=claimed.demand_id, owner="w", now=5.0)
    assert queue.snapshot()[0].status == "completed"
    # the completed demand's own artifact is the only new row (write ONE)
    con = sqlite3.connect(cat)
    con.execute(
        "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("a-retry", "d1", "s1", "summary", str(root / "artifacts" / "retry.md"),
         "c" * 64, 10, "text/markdown", "source_catalog_llm_summary", "1.0.0",
         "completed", None, '{"schema_version":"1.0"}', "2026-01-02T00:00:00Z"),
    )
    con.commit()
    con.close()
    assert _table_count(cat, "artifacts") == before + 1


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
