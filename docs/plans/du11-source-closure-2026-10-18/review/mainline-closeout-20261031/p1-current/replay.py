"""Free current-boundary replay of the two archived real ranking replies."""
from pathlib import Path
import gzip
import hashlib
import json
import socket
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT / "src"))
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_model_extractive import build_extractive_request, decode_extractive_result

def load(path):
    return json.loads(gzip.decompress(path.read_bytes()))

def main():
    def deny(*args, **kwargs):
        raise RuntimeError("P1_REPLAY_NO_NETWORK")
    original = socket.socket.connect
    socket.socket.connect = deny
    try:
        for row in json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))["files"]:
            body = (HERE / row["path"]).read_bytes()
            assert len(body) == row["bytes"] and hashlib.sha256(body).hexdigest() == row["sha256"]
        for case in ("berkshire", "huali"):
            material = HERE / "receipts" / case / "materials"
            selected = NarrativeSelectResult.from_dict(load(material / "selection.json.gz"))
            request = build_extractive_request(selected)
            actual = load(material / "input.json.gz")
            request = request.with_output_budget(actual.get("max_tokens", actual.get("max_completion_tokens")))
            actual_data = json.loads(actual["messages"][1]["content"])
            expected_data = json.loads(request.data_json)
            assert actual_data == expected_data
            assert actual["messages"][0]["content"] == request.instruction
            response = load(material / "response.json.gz")
            generation = load(material / "generation.json.gz")
            model = generation["model"]
            # Captured final text is decoded by the same original protocol;
            # provider envelope and network are not synthesized.
            raw = json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            decoded = decode_extractive_result(NarrativeModelResponse(
                "offline-capture", model["model_id"], request.prompt_version, raw), selected=selected)
            bundle = load(material / "bundle.json.gz")
            assert decoded.draft == bundle["summary"]["draft"]
            overall = load(material.parent / "overall.json.gz")
            captured_execution = overall["states"][0]["receipt"]["documents"][0]["model_diagnostics"][0]["execution"]
            assert decoded.execution == captured_execution
            print(case, "paid request data / complete draft / execution PASS")
    finally:
        socket.socket.connect = original

if __name__ == "__main__":
    main()
