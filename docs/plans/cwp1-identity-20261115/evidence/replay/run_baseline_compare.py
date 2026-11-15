"""CANDIDATES-FIX-01 baseline comparison: master (unfixed) vs CWP1 lane (fixed).

Runs the same three identity queries, the same FF reuse_only 20-F request and
the same RF route3 request against the unfixed master source tree. Only the
PYTHONPATH differs; catalog data and tmp configs are identical. Read-only,
zero downloads, zero models.
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
EV = LANE / "docs/plans/cwp1-identity-20261115/evidence/baseline-master"
PY = "C:/Miniconda/python.exe"
CFG = str(TMP / "catalog_probe.yaml").replace("\\", "/")


def env_for(src_root: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONPATH"] = os.pathsep.join([
        str(src_root / "src"), str(FF / "scripts"), str(RF / "scripts"),
        env.get("PYTHONPATH", ""),
    ])
    return env


def run(command: list[str], cwd: Path, env: dict, tag: str) -> tuple[int, bytes, bytes]:
    p = subprocess.run(command, capture_output=True, cwd=str(cwd), env=env, timeout=300)
    (EV / f"{tag}.command.json").write_text(
        json.dumps(command, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EV / f"{tag}.stdout").write_bytes(p.stdout)
    (EV / f"{tag}.stderr").write_bytes(p.stderr)
    (EV / f"{tag}.exit.txt").write_text(str(p.returncode) + "\n", encoding="utf-8")
    return p.returncode, p.stdout, p.stderr


def main() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    env = env_for(MAIN)

    # 1. three identity queries on unfixed master
    for q in ("Alibaba Group Holding Limited", "BABA", "09988"):
        tag = "master-identify-" + q.replace(" ", "_")
        rc, out, _ = run([PY, "-B", "-m", "company_wiki.source_catalog.cli",
                          "--config", CFG, "identify", "--query", q], MAIN, env, tag)
        try:
            d = json.loads(out)
            print(json.dumps({"probe": tag, "exit": rc, "status": d.get("status"),
                              "reason": d.get("reason"),
                              "resolved": (d.get("resolved") or {}).get("security_id"),
                              "candidates": len(d.get("candidates") or [])}, ensure_ascii=False))
        except Exception as exc:
            print(tag, "parse_error", exc, out[:200])

    # 2. FF reuse_only Alibaba 20-F on unfixed master
    rc, out, err = run([PY, "-B", str(FF / "scripts" / "fetch_filing.py"),
                        "--config", str(TMP / "company_wiki_probe.json"),
                        "--request-file", str(TMP / "ff-alibaba-20f-reuse.json"),
                        "--timeout-seconds", "120"], FF, env, "master-ff-20f-reuse")
    try:
        d = json.loads(out)
        print(json.dumps({"probe": "master-ff-20f-reuse", "exit": rc,
                          "status": d.get("status"),
                          "reason": (d.get("filing") or {}).get("reason"),
                          "downloads": d.get("downloads")}, ensure_ascii=False))
    except Exception as exc:
        print("master-ff-20f-reuse parse_error", exc, out[:300], err[:300])

    # 3. RF route3 on unfixed master (attribution control)
    rc, out, err = run([PY, "-B", str(RF / "scripts" / "source_preparation.py"),
                        "--result-envelope",
                        "--request-file", str(RF / ".planning/rf-input-prep-01/requests/route3-hk-fy2025-reuse.json"),
                        "--company-wiki-config", str(TMP / "company_wiki_probe.json"),
                        "--filing-fetch-root", str(FF),
                        "--company-wiki-catalog-config", str(TMP / "catalog_probe.yaml"),
                        "--source-reader-receipt-version", "2.2",
                        "--timeout-seconds", "180"], RF, env, "master-rf-route3")
    print(json.dumps({"probe": "master-rf-route3", "exit": rc,
                      "stdout_bytes": len(out),
                      "stderr_head": err.decode("utf-8", "replace")[:300]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
