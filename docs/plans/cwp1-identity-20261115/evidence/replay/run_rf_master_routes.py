"""Attribution control: replay all six RF routes on unfixed master source.

Only PYTHONPATH changes (master/src instead of lane/src). Same tmp configs,
same request files, same catalog data. Read-only, zero downloads, zero models.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

MAIN = Path("C:/Users/郑曾波/Projects/company-wiki")
LANE = Path("C:/Users/郑曾波/Projects/company-wiki-cwp1-identity-20261115")
FF = Path("C:/Users/郑曾波/Projects/filing-fetch")
RF = Path("C:/Users/郑曾波/Projects/revenue-forecast")
TMP = Path("C:/Users/郑曾波/AppData/Local/Temp/cwp1-probe")
EV = LANE / "docs/plans/cwp1-identity-20261115/evidence/rf-routes-master"
PY = "C:/Miniconda/python.exe"
ROUTE_NAMES = [
    "route1-hk-fy2026-reuse",
    "route2-hk-fy2026-fetch-if-missing",
    "route3-hk-fy2025-reuse",
    "route4-us-fy2026-fetch-if-missing",
    "route5-hk-latest-as-of-reuse",
    "route6-hk-latest-as-of-fetch-if-missing",
]


def main() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONPATH"] = os.pathsep.join([
        str(MAIN / "src"), str(FF / "scripts"), str(RF / "scripts"),
        env.get("PYTHONPATH", ""),
    ])
    rows = []
    for label in ROUTE_NAMES:
        req = RF / ".planning/rf-input-prep-01/requests" / f"{label}.json"
        command = [
            PY, "-B", str(RF / "scripts" / "source_preparation.py"),
            "--result-envelope", "--request-file", str(req),
            "--company-wiki-config", str(TMP / "company_wiki_probe.json"),
            "--filing-fetch-root", str(FF),
            "--company-wiki-catalog-config", str(TMP / "catalog_probe.yaml"),
            "--source-reader-receipt-version", "2.2",
            "--timeout-seconds", "180",
        ]
        (EV / f"{label}.command.json").write_text(
            json.dumps(command, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        p = subprocess.run(command, capture_output=True, cwd=str(RF), env=env, timeout=300)
        (EV / f"{label}.stdout.json").write_bytes(p.stdout)
        (EV / f"{label}.stderr.json").write_bytes(p.stderr)
        (EV / f"{label}.exit.txt").write_text(str(p.returncode) + "\n", encoding="utf-8")
        row = {"route": label, "exit_code": p.returncode, "stdout_bytes": len(p.stdout)}
        if p.returncode == 0 and p.stdout:
            src = (json.loads(p.stdout).get("source") or {})
            row["observed"] = {"status": "found_capture_ready", "title": src.get("title")}
        else:
            try:
                e = json.loads(p.stderr.decode("utf-8", "replace"))
                fr = e.get("filing_fetch_result") or {}
                f = fr.get("filing") or {}
                row["observed"] = {"status": fr.get("status"), "reason": f.get("reason"),
                                   "upstream_cause": (f.get("upstream_cause") or {}).get("code"),
                                   "local_prepare_reason": (fr.get("local_preparation_observation") or {}).get("reason"),
                                   "downloads": fr.get("downloads")}
            except Exception as ex:
                row["observed"] = {"status": "parse_error", "detail": str(ex)}
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    (EV / "alibaba-routes-master.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
