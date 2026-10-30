"""Read-only replay of captured JSON; no model, source download or PDF parsing.

Run from repository root: python .planning/source-description-20261030/real-summary-independent/reproduce.py
The mutation probe is synthetic and never replaces the captured response or bundle.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model_scoped import (
    MAX_SUMMARY_CLAIMS, compile_scoped_model_view, decode_scoped_draft,
)

CAPTURE = ROOT / ".planning/source-description-20261030/real-summary-v3"
OUT = Path(__file__).parent


def read_gz(path):
    return json.loads(gzip.open(path, "rt", encoding="utf-8").read())


def run():
    input_path = next((CAPTURE / "materials").glob("*.input.json.gz"))
    response_path = next((CAPTURE / "materials").glob("*.response.json.gz"))
    selection_path = next((CAPTURE / "materials").glob("*.selection.json.gz"))
    bundle_path = next(CAPTURE.glob("*.bundle.json.gz"))
    request = read_gz(input_path)
    model_payload = json.loads(next(m["content"] for m in request["messages"] if m["role"] == "user"))
    selected = NarrativeSelectResult.from_dict(read_gz(selection_path))
    response = read_gz(response_path)
    bundle = read_gz(bundle_path)
    raw = gzip.open(response_path, "rb").read()

    def decode(body):
        return decode_scoped_draft(SimpleNamespace(
            prompt_version="reading-source-scoped/4.1.0", response_bytes=body), selected=selected)

    decoded = decode(raw)
    plan = compile_scoped_model_view(selected, max_claims=MAX_SUMMARY_CLAIMS).plan
    emitted = [c["claim_id"].rsplit("-", 1)[0] for c in decoded["claims"]]
    coverage = plan.coverage(emitted)
    # Deliberately impossible acquisition claim: a validator-boundary probe only.
    mutation = json.loads(raw)
    mutation["drafts_by_task"]["t2"][0]["text"] = "九目化学已完成对三星家电业务的收购。"
    mutated = decode(json.dumps(mutation, ensure_ascii=False).encode())
    mutation_claim = next(c for c in mutated["claims"] if c["claim_id"] == "t2-1")
    result = {
        "scope": "captured_json_replay_only_no_model_no_pdf_parse",
        "sent_task_keys": [t["key"] for t in model_payload["material"]["tasks"]],
        "response_task_keys": list(response["drafts_by_task"]),
        "final_task_keys": [c["claim_id"].rsplit("-", 1)[0] for c in bundle["summary"]["draft"]["claims"]],
        "decoded_claim_count": len(decoded["claims"]),
        "decoded_matches_final_draft": decoded == bundle["summary"]["draft"],
        "decoded_status": decoded["status"],
        "decoded_needs_review": [c["needs_review"] for c in decoded["claims"]],
        "bundle_quality_status": bundle["quality_status"],
        "computed_task_coverage": coverage,
        "coverage_serialized_in_bundle": "source_task_coverage_complete" in json.dumps(bundle),
        "output_plan": model_payload["output_plan"],
        "mutation_probe": {
            "synthetic_not_model_output": True,
            "unsupported_acquisition_claim_retained": mutation_claim,
            "decoded_status": mutated["status"],
        },
        "artifact_hashes": {
            str(p.relative_to(ROOT)): {
                "compressed_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "uncompressed_sha256": hashlib.sha256(gzip.open(p, "rb").read()).hexdigest(),
            } for p in [input_path, response_path, selection_path, bundle_path]
        },
    }
    (OUT / "reproduction.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
