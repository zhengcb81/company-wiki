"""Public explicit v4 intent -> configured CLI -> actual worker/cache/read.

All original bytes, registry, AUTO and fake HTTP live in the owned temporary
lake. Copied source fragments test transport, not semantic summary quality.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import pytest

from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from integration.test_narrative_generation_reuse import exact_ref, invoke
from support import official_json_batch_fixture as fixtures


official_json_loopback_model = fixtures.official_json_loopback_model
LEGACY = Path(__file__).parents[1] / "fixtures/shared_scoped_public_request/legacy_request_hashes.json"
V4 = "reading-model-input/4"


def test_omitted_public_projection_keeps_frozen_legacy_request_bytes_and_hashes():
    for row in json.loads(LEGACY.read_text(encoding="utf-8")):
        request = NarrativeBatchRequest.from_dict(row["wire"])
        assert request.to_dict() == row["normalized"]
        assert request.request_sha256 == row["request_sha256"]
        assert request.input_hash == row["input_hash"]


@pytest.mark.parametrize("schema", ["narrative-batch-request/1", "narrative-batch-request/2"])
def test_public_projection_roundtrips_and_owns_request_identity(schema):
    wire = next(row["wire"] for row in json.loads(LEGACY.read_text())
                if row["wire"]["schema_version"] == schema and row["wire"].get("selector_version") == "0.9.0")
    legacy = NarrativeBatchRequest.from_dict(wire)
    request = NarrativeBatchRequest.from_dict({**wire, "reading_model_projection": V4})
    assert request.reading_model_projection == V4
    assert request.to_dict()["reading_model_projection"] == V4
    assert request.request_sha256 != legacy.request_sha256
    assert request.input_hash != legacy.input_hash
    assert NarrativeBatchRequest.from_dict(request.to_dict()) == request


@pytest.mark.parametrize("value", [None, "", " reading-model-input/4", "reading-model-input/6", 4])
def test_public_projection_rejects_invalid_or_unavailable_protocol(value):
    wire = json.loads(LEGACY.read_text())[2]["wire"]
    with pytest.raises(ValueError, match="reading_model_projection"):
        NarrativeBatchRequest.from_dict({**wire, "reading_model_projection": value})


@pytest.mark.parametrize("selector", [None, "0.8.0"])
def test_explicit_v4_requires_source_owned_selector(selector):
    wire = dict(json.loads(LEGACY.read_text())[0]["wire"], reading_model_projection=V4)
    if selector is not None:
        wire["selector_version"] = selector
    with pytest.raises(ValueError, match="selector_version"):
        NarrativeBatchRequest.from_dict(wire)


def _fragment_draft(data):
    if data["schema_version"] != "narrative-model-request/5":
        return _legacy_draft(data)
    material = data["material"]
    task = material["tasks"][0]
    support = task.get("support_parts", material["task_defaults"]["support_parts"])
    key = task["parts"][0]["key"] if support == "all_parts" else support[0]
    part = next(part for part in task["parts"] if part["key"] == key)
    if "shared_ref" in part:
        shared_key = part["shared_ref"]
        part = next(row for row in material["shared_fragments"] if row["source_key"] == shared_key)
    return {"drafts_by_task": {task["key"]: [
        {"text": part["text"][:200], "basis_parts": [key], "modality": "uncertain"}]}}


_legacy_draft = fixtures.model_draft


def _owned_runner_module(name):
    import importlib.util

    path = Path(__file__).parents[2] / "tools/document_understanding_benchmark" / (name + ".py")
    spec = importlib.util.spec_from_file_location("public_v4_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_existing_phase_c_observer_binds_actual_v4_material_without_another_oracle():
    from company_wiki.automation.narrative_model_runtime import build_model_request
    from unit.test_narrative_output_language_binding import selected_english

    selected = selected_english()
    envelope = json.loads(build_model_request(selected, reading_projection_version=V4).data_json)
    observer = _owned_runner_module("phase_c_observer")
    observation = observer.gold_observation({"facts": []}, selected, envelope)
    assert observation["evidence_count"] == len(selected.evidence_spans)
    assert observation["required_count"] == 0
    envelope["material"]["tasks"][0]["parts"][0]["text"] = "Foreign material must not be scored as original."
    with pytest.raises(AssertionError):
        observer.gold_observation({"facts": []}, selected, envelope)


def test_existing_phase_c_loopback_uses_actual_task_local_protocol_and_keeps_invalid_output():
    from company_wiki.automation.narrative_model_runtime import build_model_request, decode_model_draft
    from company_wiki.automation.narrative_model import NarrativeModelResponse
    from unit.test_narrative_output_language_binding import selected_english

    selected = selected_english()
    request = build_model_request(selected, reading_projection_version=V4)
    envelope = json.loads(request.data_json)
    runner = _owned_runner_module("phase_c_runner")
    for invalid in (False, True):
        reply = runner.loopback_draft(envelope, invalid_summary=invalid)
        response = NarrativeModelResponse("loopback", "stub-model", request.prompt_version,
                                          json.dumps(reply).encode())
        if invalid:
            with pytest.raises(ValueError):
                decode_model_draft(response, selected=selected, reading_projection_version=V4)
        else:
            draft = decode_model_draft(response, selected=selected, reading_projection_version=V4)
            assert draft["claims"][0]["evidence_ids"] == [selected.evidence_spans[0].span_id]


def test_tracked_phase_c_full_loopback_needs_no_planning_history_and_removes_lakes(tmp_path):
    import shutil
    import subprocess
    import sys

    repo = Path(__file__).parents[2]
    output = (tmp_path / "phase-c-receipt").resolve()
    deployed = (tmp_path / "clean-source-deployment").resolve()
    before = sorted(tmp_path.iterdir())
    # Deploy only current code/resources, never originals, config, .git or paid
    # history. .planning is physically absent in the executing project tree.
    for package in ("src", "scripts"):
        for source in (repo / package).rglob("*"):
            if source.is_file() and source.suffix in {".py", ".json"} and "__pycache__" not in source.parts:
                target = deployed / source.relative_to(repo)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    benchmark = Path("tools/document_understanding_benchmark")
    # Deploy the actual bounded tool package, not a manually maintained module
    # list that becomes incomplete whenever the runner extracts a helper.
    for source in (repo / benchmark).rglob('*.py'):
        if '__pycache__' in source.parts:
            continue
        target = deployed / source.relative_to(repo)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    assert not (deployed / ".planning").exists()
    # Also deny any accidental coordinator attempt to read an external history.
    script = """
from pathlib import Path
import sys
original = Path.open
def clean_open(self, *args, **kwargs):
    if '.planning' in self.parts:
        raise AssertionError('clean checkout must not depend on .planning')
    return original(self, *args, **kwargs)
Path.open = clean_open
from tools.document_understanding_benchmark.phase_c_runner import main
raise SystemExit(main())
"""
    try:
        process = subprocess.run(
            [sys.executable, "-B", "-c", script, "--mode", "loopback", "--output", str(output),
             "--reading-model-projection", V4], cwd=deployed,
            env={**fixtures.subprocess_env(), "PYTHONPATH": str(deployed / "src")},
            capture_output=True, timeout=240,
        )
        assert process.returncode == 0, (process.stdout.decode(errors="replace"), process.stderr.decode(errors="replace"))
        receipt = json.loads((output / "overall.json").read_bytes())
        assert receipt["status"] == "PASS" and receipt["external_POSTs"] == 0
        assert receipt["loopback_POSTs"] == 2 and receipt["mother_ledger_changed"] is False
        assert receipt["normal"]["temporary_lake_removed"] is True
        assert receipt["normal"]["states"][0]["consumers"]["status"] == "NOT_RUN"
        assert receipt["paid_transport_invalid_summary_negative"]["status"] == "PASS"
        assert not (deployed / ".planning").exists()
    finally:
        assert output.parent == tmp_path.resolve() and output.name == "phase-c-receipt"
        if output.exists():
            shutil.rmtree(output)
        assert deployed.parent == tmp_path.resolve() and deployed.name == "clean-source-deployment"
        if deployed.exists():
            shutil.rmtree(deployed)
        assert sorted(tmp_path.iterdir()) == before


@pytest.mark.parametrize("kind", ["raw-v1", "raw-v2", "official_json"])
def test_configured_public_v4_worker_recovery_reuse_protocol_separation_and_exact_read(
    tmp_path, official_json_loopback_model, monkeypatch, kind,
):
    server = official_json_loopback_model
    monkeypatch.setattr(fixtures, "model_draft", _fragment_draft)
    monkeypatch.setenv("DEEPSEEK_API_KEY", fixtures.KEY)
    with fixtures.official_batch_state(tmp_path) as state:
        item = ({"kind": "official_json", "projection_id": state.subjects[0].item_key,
                 "projection_sha256": state.subjects[0].subject_sha256}
                if kind == "official_json" else {"kind": "raw", "source_ref": state.raw_ref})
        path = fixtures.request_for(state, server.endpoint, "public-v4", items=[item])
        wire = json.loads(path.read_bytes())
        if kind == "raw-v1":
            wire["schema_version"] = "narrative-batch-request/1"
            wire["sources"] = [wire.pop("items")[0]["source_ref"]]
        wire.update(selector_version="0.9.0", reading_model_projection=V4)
        path.write_bytes(fixtures.encoded(wire))
        llm = state.root / "llm.yaml"
        llm.write_text("llm:\n  provider: deepseek\n  model: stub-model\n  base_url: "
                       + server.endpoint.removesuffix("/chat/completions")
                       + "\n  max_tokens: 8192\n  temperature: 0.7\n", encoding="utf-8")

        def run(run_id):
            return invoke(state.root, state.config_path, path, llm, run_id,
                          database=state.automation_db)

        process, first = run("public-v4")
        assert process.returncode == 0 and first["status"] == "completed", (first, process.stderr)
        assert len(server.requests) == 1 and server.errors == []
        assert server.requests[0]["schema_version"] == "narrative-model-request/5"
        assert server.requests[0]["output_plan"]["configured_output_tokens"] == 8192
        store = NarrativeRunStore(state.automation_db)
        manifest = next(iter(store.final_generations("public-v4").values()))
        assert manifest["reading_model_projection"] == V4
        assert manifest["execution_versions"]["prompt"] == "reading-source-scoped/4.0.8"
        assert manifest["reading_model_boundary"]["request_schema"] == "narrative-model-request/5"
        reservations = tuple(asdict(row) for row in store.reservations_for_run("public-v4"))
        reference = first["items"][0]["artifact_ref"] if kind != "raw-v1" else first["documents"][0]["artifact_ref"]
        if kind == "raw-v1":
            reference = exact_ref({"source_ref": state.raw_ref}, reference)
        bundle, receipt = fixtures.invoke_read(state, reference)
        assert receipt["replay_status"] == "verified" and bundle["summary"]["translate"] is False

        resumed_process, resumed = run("public-v4")
        assert resumed_process.returncode == 0 and resumed["status"] == "completed"
        result_key = "documents" if kind == "raw-v1" else "items"
        assert resumed[result_key] == first[result_key] and resumed["budget"] == first["budget"]
        assert resumed["storage"]["persistent_added_bytes"] == first["storage"]["persistent_added_bytes"]
        assert resumed["storage"]["scratch_peak_bytes"] == 0
        assert tuple(asdict(row) for row in store.reservations_for_run("public-v4")) == reservations
        assert len(server.requests) == 1
        wire["run_id"] = "public-v4-cache"
        path.write_bytes(fixtures.encoded(wire))
        reused_process, reused = run("public-v4-cache")
        assert reused_process.returncode == 0 and reused["status"] == "completed", reused
        assert reused["budget"]["tokens"] == 0 and len(server.requests) == 1
        assert not store.reservations_for_run("public-v4-cache")

        # Omission adopts the current source-extractive default, with a different
        # generation. An exact prior v4 reference still resolves after LATEST changes.
        wire.pop("reading_model_projection")
        wire["run_id"] = "public-v5"
        path.write_bytes(fixtures.encoded(wire))
        legacy_process, legacy = run("public-v5")
        assert legacy_process.returncode == 0 and legacy["status"] == "completed", legacy
        assert len(server.requests) == 2 and server.errors == []
        assert server.requests[1]["schema_version"] == "narrative-model-request/6"
        legacy_manifest = next(iter(store.final_generations("public-v5").values()))
        assert legacy_manifest["reading_model_projection"] == "reading-model-input/5"
        assert legacy_manifest != manifest
        pinned, _ = fixtures.invoke_read(state, reference)
        assert pinned == bundle

        # An existing run's intent cannot silently change protocols.
        wire["run_id"] = "public-v4"
        path.write_bytes(fixtures.encoded(wire))
        changed_process, changed = run("public-v4")
        assert changed_process.returncode != 0 and changed["status"] != "completed"
        assert len(server.requests) == 2
