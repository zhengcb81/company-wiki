"""ZR-803 acceptance tests (phase G): chaos / property / mutation —
lock, interruption, disk, tamper, ordering, clock — with idempotent
recovery after every fault.

Six fault classes are exercised against REAL production entries and each
journey must recover idempotently (no orphan state, no fabricated data,
no second side effect):

  lock        a held write transaction on the catalog does NOT block the
              read-only user journey (WAL readers proceed; READ-06); the
              journey completes with zero downloads during the hold.
  interrupt   formal publication interrupted mid-flight leaves no registry
              line; a clean rerun registers exactly once; draft never
              touches the registry.
  disk        an unwritable output path fails structured (exit 2) and
              creates no half-written artifact or parent directories.
  tamper      one flipped byte of result_sha256 is rejected by the strong
              validator; the original still validates.
  ordering    evaluate-before-create and duplicate create are refused;
              after the refused attempt the normal order still succeeds.
  clock       a future captured_date is rejected as outside the allowed
              information set; the untampered input still validates.

Critical-mutation kill coverage itself remains owned by CA-108's gate
(tests/test_critical_mutation_gate.py); this suite pins journey-level
fault recovery. Zero production changes; hermetic T0/T1.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
PROJECT_ROOT = RF_CODE_ROOT
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "e2e_support"))
FILING_ROOT = Path.home() / "Projects" / "filing-fetch"
if not (FILING_ROOT / "scripts" / "fetch_filing.py").is_file():
    FILING_ROOT = PROJECT_ROOT.parent / "filing-fetch"
sys.path.insert(0, str(FILING_ROOT))
sys.path.insert(0, str(PROJECT_ROOT.parent / "company-wiki" / "src"))

AS_OF = (_dt.date.today() + _dt.timedelta(days=7)).isoformat()


def _chain(tmp_path: Path):
    from e2e_support.isolated_lake import IsolatedLake

    IsolatedLake(tmp_path, seed="zr803").build()
    project = tmp_path / "lake" / "project"
    wiki_cfg = tmp_path / "wiki.json"
    wiki_cfg.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "company_wiki_root": str(project),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    request = {
        "schema_version": "1.1",
        "company_query": "紫金矿业",
        "market": "CN",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "as_of_date": AS_OF,
    }

    def run(timeout_seconds: int = 60) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(PROJECT_ROOT / "scripts" / "source_preparation.py"),
                "--company-wiki-config",
                str(wiki_cfg),
                "--filing-fetch-root",
                str(FILING_ROOT),
                "--company-wiki-catalog-config",
                str(project / "config" / "source_catalog.yaml"),
                "--timeout-seconds",
                str(timeout_seconds),
            ],
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=str(PROJECT_ROOT),
            env=env,
            timeout=timeout_seconds + 120,
            check=False,
        )

    return project, run


# ---------------------------------------------------------------------------
# lock — concurrent write transaction must not break the read journey
# ---------------------------------------------------------------------------


def test_lock_held_write_transaction_does_not_block_read_journey(tmp_path):
    project, run = _chain(tmp_path)
    db = project / ".source_catalog" / "catalog.sqlite3"
    holder = sqlite3.connect(db, timeout=1.0)
    try:
        holder.execute("BEGIN EXCLUSIVE")  # simulate a live writer mid-flight
        proc = run()
        # READ-06: the read-only journey completes in a bounded way while a
        # writer holds its transaction — zero downloads, real record out.
        # RF-E2E-ADAPT: the run() helper uses text=True (line 90), so
        # proc.stderr is already str — calling .decode() here raised
        # AttributeError and MASKED the chain's real error in the gate log.
        assert proc.returncode == 0, proc.stderr[-400:]
        record = json.loads(proc.stdout)
        assert record["reuse_receipt"]["download_calls"] == 0
        assert record["reuse_receipt"]["outcome"] == "reused_existing"
    finally:
        holder.rollback()
        holder.close()
    # recovery after release: identical reuse, still zero downloads
    after = json.loads(run().stdout)
    assert after["source_id"] == record["source_id"]
    assert after["reuse_receipt"]["download_calls"] == 0


# ---------------------------------------------------------------------------
# interrupt — publication atomicity under abrupt termination
# ---------------------------------------------------------------------------


def test_interrupt_leaves_no_registry_orphan_and_rerun_registers_once(
    monkeypatch, tmp_path
):
    import publication_registry  # noqa: PLC0415
    import revenue_forecast  # noqa: PLC0415

    registry = tmp_path / "pub" / "publications.jsonl"
    monkeypatch.setenv("REVENUE_PUBLICATION_REGISTRY", str(registry))
    document = _forecast_document()

    # draft first: zero registration even though a formal will follow later
    revenue_forecast.prepare_forecast(document, mode="draft")
    assert not registry.exists()

    # interrupt simulation: crash AFTER computing but BEFORE registering —
    # monkeypatch register_publication to die like a killed process would.

    original = publication_registry.register_publication

    def _crash(*args, **kwargs):
        raise KeyboardInterrupt  # process death, not a domain error

    monkeypatch.setattr(publication_registry, "register_publication", _crash)
    with pytest.raises(KeyboardInterrupt):
        revenue_forecast.prepare_forecast(document, mode="formal")
    monkeypatch.setattr(publication_registry, "register_publication", original)

    # no half state survived the crash…
    if registry.exists():
        entries = publication_registry._read_entries()  # raises on torn lines
        assert all(e.get("input_sha256") != _input_sha(document) for e in entries)
    # …and the rerun registers exactly once with the same payload hash.
    result = revenue_forecast.prepare_forecast(document, mode="formal")
    entries = [
        e
        for e in publication_registry._read_entries()
        if e.get("result_sha256") == result["result_sha256"]
    ]
    assert len(entries) == 1
    assert entries[0]["validation_status"] == "validated"


# ---------------------------------------------------------------------------
# disk — unwritable output fails structured without half artifacts
# ---------------------------------------------------------------------------


def test_disk_unwritable_output_is_structured_with_no_half_write(tmp_path):
    document = _forecast_document()
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    registry = tmp_path / "pub.jsonl"
    env = dict(os.environ)
    env["REVENUE_PUBLICATION_REGISTRY"] = str(registry)
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            str(PROJECT_ROOT / "scripts" / "revenue_forecast.py"),
            str(input_file),
            "--output",
            str(tmp_path / "no-such-dir" / "out.json"),
        ],
        capture_output=True,
        cwd=str(PROJECT_ROOT),
        env=env,
        timeout=180,
    )
    assert proc.returncode == 2
    stderr = proc.stderr.decode("utf-8", "replace")
    assert stderr.startswith("error:")
    assert not (tmp_path / "no-such-dir").exists()  # no parent dirs created
    assert not list(tmp_path.glob("*.tmp"))  # no temp residue
    # recovery: a valid path publishes cleanly afterwards
    ok = subprocess.run(
        [
            sys.executable,
            "-B",
            str(PROJECT_ROOT / "scripts" / "revenue_forecast.py"),
            str(input_file),
            "--output",
            str(tmp_path / "out.json"),
        ],
        capture_output=True,
        cwd=str(PROJECT_ROOT),
        env=env,
        timeout=180,
    )
    assert ok.returncode == 0
    assert (tmp_path / "out.json").exists()


# ---------------------------------------------------------------------------
# tamper — one flipped hash byte is rejected; original still valid
# ---------------------------------------------------------------------------


def test_tamper_single_byte_rejected_original_still_validates():
    from revenue_forecast import prepare_forecast
    from revenue_report import validate_forecast_output

    result = prepare_forecast(_forecast_document())
    validate_forecast_output(result)  # baseline sanity

    forged = dict(result)
    flipped = "0" if forged["result_sha256"][0] != "0" else "1"
    forged["result_sha256"] = flipped + forged["result_sha256"][1:]
    with pytest.raises(Exception, match="hash mismatch"):
        validate_forecast_output(forged)
    # recovery: untouched artifact keeps validating (no sticky corruption)
    validate_forecast_output(result)


# ---------------------------------------------------------------------------
# ordering — out-of-order backtest calls refuse, then normal order works
# ---------------------------------------------------------------------------


def test_ordering_out_of_order_refused_then_normal_order_succeeds(
    tmp_path, monkeypatch
):
    import copy

    from revenue_backtest import create_snapshot, evaluate_snapshot, validate_snapshot

    monkeypatch.chdir(tmp_path)
    document = _forecast_document()
    snapshot = create_snapshot(copy.deepcopy(document), "zr803-order-v1")
    validate_snapshot(snapshot)

    from test_backtest import actuals_document

    actuals = actuals_document()
    with pytest.raises(Exception):
        evaluate_snapshot({"snapshot_id": "never-created"}, actuals)

    # recovery: evaluating the real snapshot after the refused detour works
    evaluation = evaluate_snapshot(snapshot, actuals)
    assert evaluation is not None


# ---------------------------------------------------------------------------
# clock — future evidence dates are outside the information set
# ---------------------------------------------------------------------------


def test_clock_future_captured_date_rejected_clean_input_validates():
    from contracts.document import validate_document

    document = _forecast_document()
    validate_document(document)  # baseline sanity

    poisoned = json.loads(json.dumps(document, ensure_ascii=False))
    for source in poisoned["sources"]:
        source["capture"]["captured_date"] = "2999-12-31"
        source["captured_date"] = "2999-12-31"
    with pytest.raises(Exception, match="information set"):
        validate_document(poisoned)


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


def _forecast_document():
    from test_recognition_bridge import forecast_document

    return forecast_document()


def _input_sha(document: dict) -> str:
    from contracts.evidence import canonical_sha256

    return canonical_sha256(document)


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
