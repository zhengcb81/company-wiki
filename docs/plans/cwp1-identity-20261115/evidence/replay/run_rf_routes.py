"""CANDIDATES-FIX-01 §5.3 RF six-route linkage probe.

Read-only replay: drives revenue-forecast's sanctioned source_preparation.py
-> filing_fetch_client -> filing-fetch -> company-wiki. The company-wiki code
under test is the CWP1 lane (fixed); catalog data is read from the main repo
through an absolute-path tmp config. No production config is modified.
No downloads, no models: every route carries explicit zero-cost limits and
reuse-only / bounded fetch-if-missing intents; download_events are asserted 0.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RF = Path("C:/Users/郑曾波/Projects/revenue-forecast")
FF = Path("C:/Users/郑曾波/Projects/filing-fetch")
LANE = Path("C:/Users/郑曾波/Projects/company-wiki-cwp1-identity-20261115")
TMP = Path("C:/Users/郑曾波/AppData/Local/Temp/cwp1-probe")
EVIDENCE = LANE / "docs/plans/cwp1-identity-20261115/evidence/rf-routes"
PY = "C:/Miniconda/python.exe"

FF_CONFIG = TMP / "company_wiki_probe.json"
CATALOG_CONFIG = TMP / "catalog_probe.yaml"
LIMITS = {"max_bytes": 8000000, "timeout_seconds": 120, "max_cost_usd": "0.00"}

# Reuse the exact six request bodies recorded by RF INPUT-PREP (read-only).
ROUTE_REQUESTS = RF / ".planning/rf-input-prep-01/requests"
ROUTE_NAMES = [
    "route1-hk-fy2026-reuse",
    "route2-hk-fy2026-fetch-if-missing",
    "route3-hk-fy2025-reuse",
    "route4-us-fy2026-fetch-if-missing",
    "route5-hk-latest-as-of-reuse",
    "route6-hk-latest-as-of-fetch-if-missing",
]


def summarise(raw: str) -> dict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"parse": "not_json", "raw_head": raw[:300]}
    ff = payload.get("filing_fetch_result") or {}
    filing = ff.get("filing") or {}
    return {
        "status": ff.get("status"),
        "reason": filing.get("reason"),
        "resolution_outcome": filing.get("resolution_outcome"),
        "download_events": filing.get("download_events"),
        "calls": ff.get("calls"),
        "downloads": ff.get("downloads"),
        "upstream_cause": filing.get("upstream_cause"),
    }


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    summary = []
    for label in ROUTE_NAMES:
        request_path = ROUTE_REQUESTS / f"{label}.json"
        command = [
            PY, "-B", str(RF / "scripts" / "source_preparation.py"),
            "--result-envelope",
            "--request-file", str(request_path),
            "--company-wiki-config", str(FF_CONFIG),
            "--filing-fetch-root", str(FF),
            "--company-wiki-catalog-config", str(CATALOG_CONFIG),
            "--source-reader-receipt-version", "2.2",
            "--timeout-seconds", "180",
        ]
        (EVIDENCE / f"{label}.command.json").write_text(
            json.dumps(command, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env["PYTHONPATH"] = os.pathsep.join([
            str(LANE / "src"), str(FF / "scripts"), str(RF / "scripts"),
            env.get("PYTHONPATH", ""),
        ])
        proc = subprocess.run(command, capture_output=True, cwd=str(RF), timeout=300, env=env)
        (EVIDENCE / f"{label}.stdout.json").write_bytes(proc.stdout)
        (EVIDENCE / f"{label}.stderr.json").write_bytes(proc.stderr)
        (EVIDENCE / f"{label}.exit.txt").write_text(str(proc.returncode) + "\n", encoding="utf-8")
        observed = summarise(proc.stderr.decode("utf-8", "replace"))
        row = {"route": label, "exit_code": proc.returncode,
               "stdout_bytes": len(proc.stdout), "observed": observed}
        summary.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    (EVIDENCE / "alibaba-routes-after-fix.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
