"""R1 campaign across two fresh processes: budget closure, no renewal, no
re-inference, conservative charging.  Uses the declared fake backend only —
no model, no network."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def campaign(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [PYTHON, "-X", "utf8", "-m", "tools.ocr_comparison.campaign", *args],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", timeout=300,
        env={"PYTHONUTF8": "1", "SYSTEMROOT": __import__("os").environ["SYSTEMROOT"],
             "USERPROFILE": __import__("os").environ["USERPROFILE"]},
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_budget_closes_across_two_processes_with_cache_resume(tmp_path):
    ledger = tmp_path / "ledger.json"
    cache_dir = tmp_path / "cache"

    rc, out = campaign("init", "--ledger", str(ledger), "--budget", "1.0")
    assert rc == 0, out

    # Process 1: three fake pages at 0.45 s each against a 1.0 s budget.
    # pA ok (0.45 charged), pB would start with 0.55 remaining but the request
    # budget is min(180, 0.55)=0.55 -> ok (0.45 charged), pC gets 0.1 remaining
    # -> fake sleeps only 0.1 and reports timeout charged 0.1.
    rc1, out1 = campaign(
        "run", "--ledger", str(ledger), "--arm", "X1F-fake",
        "--pages", "pA,pB,pC", "--page-sleep", "0.45",
        "--cache-dir", str(cache_dir), "--out", str(tmp_path / "batch1.json"),
    )
    assert rc1 == 0, out1
    ledger1 = json.loads(ledger.read_text(encoding="utf-8"))
    assert ledger1["spent_seconds"] <= 1.0
    assert len(ledger1["entries"]) == 3
    statuses = {e["page_id"]: e["status"] for e in ledger1["entries"]}
    assert statuses == {"pA": "ok", "pB": "ok", "pC": "timeout"}

    # Process 2: a fresh interpreter resumes.  pA/pB are cache hits (no
    # re-inference, no re-charge); pC is a cached timeout record too.
    rc2, out2 = campaign(
        "run", "--ledger", str(ledger), "--arm", "X1F-fake",
        "--pages", "pA,pB,pC", "--page-sleep", "0.45",
        "--cache-dir", str(cache_dir), "--out", str(tmp_path / "batch2.json"),
    )
    assert rc2 == 0, out2
    batch2 = json.loads((tmp_path / "batch2.json").read_text(encoding="utf-8"))
    hits = [r for r in batch2["records"] if r.get("cache_hit")]
    assert len(hits) == 3
    ledger2 = json.loads(ledger.read_text(encoding="utf-8"))
    assert ledger2["spent_seconds"] == ledger1["spent_seconds"], (
        "cache hits must not re-charge the ledger")
    assert len(ledger2["entries"]) == 3, "no duplicate page entries on resume"


def test_exhausted_ledger_refuses_new_work(tmp_path):
    ledger = tmp_path / "ledger.json"
    campaign("init", "--ledger", str(ledger), "--budget", "0.2")
    rc1, _ = campaign("run", "--ledger", str(ledger), "--arm", "X1F-fake",
                      "--pages", "pA", "--page-sleep", "0.3",
                      "--out", str(tmp_path / "b1.json"))
    assert rc1 == 0
    assert json.loads((tmp_path / "b1.json").read_text(encoding="utf-8"))["records"][0]["status"] == "timeout"
    rc2, out2 = campaign("run", "--ledger", str(ledger), "--arm", "X1F-fake",
                         "--pages", "pB", "--page-sleep", "0.1",
                         "--out", str(tmp_path / "b2.json"))
    assert rc2 == 0, out2
    batch2 = json.loads((tmp_path / "b2.json").read_text(encoding="utf-8"))
    # zero balance: the miss is recorded honestly, never inferred
    assert batch2["records"][0]["status"] == "not_run"
    assert batch2["records"][0]["error"] == "budget_exhausted"
    ledger = json.loads(ledger.read_text(encoding="utf-8"))
    assert len(ledger["entries"]) == 2
    assert ledger["entries"][1]["seconds"] == 0.0


def test_corrupt_ledger_blocks_the_campaign(tmp_path):
    ledger = tmp_path / "ledger.json"
    campaign("init", "--ledger", str(ledger), "--budget", "10.0")
    payload = json.loads(ledger.read_text(encoding="utf-8"))
    payload["spent_seconds"] = 99.0  # tampering
    ledger.write_text(json.dumps(payload), encoding="utf-8")
    rc, out = campaign("run", "--ledger", str(ledger), "--arm", "X1F-fake",
                       "--pages", "pA", "--page-sleep", "0.05",
                       "--out", str(tmp_path / "b.json"))
    assert rc != 0
    assert "LedgerCorrupt" in out or "ledger" in out.lower()
