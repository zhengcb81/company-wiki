"""Read the existing production TXT artifact; no worker/model invocation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

PLAN = Path(__file__).resolve().parent
CWP = PLAN.parents[2]
PREVIOUS = CWP / "docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/results/r3_production_consumption_2026-10-08.json"
prior = json.loads(PREVIOUS.read_text(encoding="utf-8"))["documents"][0]
manifest = prior["read_receipt"]["manifest"]
constraints = {key: manifest[key] for key in ("canonical_entity_id", "market", "security_id", "document_kind", "fiscal_year", "fiscal_period")}
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1",
           PYTHONPATH=os.pathsep.join((str(PLAN / "process_trace"), str(CWP / "src"))),
           CWP_AUDIT_PROCESS_DIR=str(PLAN / "main_processes"))
tools = {
    "CWP": [sys.executable, "-B", "-m", "company_wiki.source_catalog.narrative_transport_cli", "--config", str(CWP / "config/source_catalog.yaml")],
    "RF": [sys.executable, "-B", "C:/Users/郑曾波/.agents/skills/revenue-forecast/scripts/narrative_source_preparation.py",
           "--company-wiki-catalog-config", str(CWP / "config/source_catalog.yaml")],
}
rows = []
for consumer, command in tools.items():
    for as_of in (None, "2026-10-08"):
        request = {"schema_version": "narrative-read-request/1", "narrative_ref": prior["narrative_ref"],
                   "expected_source": constraints, "as_of_date": as_of}
        completed = subprocess.run(command, cwd=CWP, env=env, input=json.dumps(request).encode(), capture_output=True, check=False, timeout=60)
        row = {"consumer": consumer, "request": request, "command": command, "returncode": completed.returncode,
               "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(), "stdout_bytes": len(completed.stdout)}
        if as_of is None:
            assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
            body = json.loads(completed.stdout)
            row.update(quality_status=body["quality_status"], evidence_span_count=len(body["evidence_spans"]),
                       source_language=body["source_metadata"]["language"])
            if consumer == "CWP":
                assert hashlib.sha256(completed.stdout).hexdigest() == prior["narrative_ref"]["artifact_sha256"]
                row["receipt"] = json.loads(completed.stderr)
            else:
                assert body["narrative_ref"] == prior["narrative_ref"]
                row["receipt"] = body["read_receipt"]
            assert row["evidence_span_count"] == 49
            assert row["receipt"]["manifest"]["published_date"] is None
        else:
            assert completed.returncode != 0 and not completed.stdout
            row["refusal"] = json.loads(completed.stderr)
        rows.append(row)
record = {"schema_version": "existing-production-narrative-check/1", "artifact_already_existed": True,
          "new_worker_runs": 0, "new_model_calls": 0, "published_date_invented": False,
          "forecast_input_consumption_proven": False, "checks": rows,
          "interpretation": "Current material read passes for the existing production TXT artifact. Explicit information-date forecast eligibility remains refused due to unknown source publication date; this does not prove a new FF/ET acquisition or SEC HTML processing."}
(PLAN / "existing_narrative_current_vs_asof.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"current_reads": 2, "asof_refusals": 2, "new_model_calls": 0, "artifact_sha256": prior["narrative_ref"]["artifact_sha256"]}))
