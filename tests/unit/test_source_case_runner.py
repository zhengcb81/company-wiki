"""The source observer must survive its own output failure, without source I/O."""
from copy import deepcopy
from hashlib import sha256
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tools import source_case_runner as runner


def producer_record():
    return {
        "case_id": "synthetic", "status": "OBSERVED_NOT_COMPANY_OR_ECONOMIC_ACCEPTANCE",
        "model_posts": 0, "downloads": 0, "source_select_calls": 1,
        "database_before": {"synthetic": {"sha256": "before"}},
        "database_after": {"synthetic": {"sha256": "before"}},
        "original_files_before": {"fixture": {"sha256": "source"}},
        "original_files_after": {"fixture": {"sha256": "source"}},
        "database_unchanged": True, "original_files_unchanged": True, "runtime_unchanged": True,
        "required_units": [{"unit_id": "u1", "represented": True}],
        "source_excerpt_units": [{"unit_id": "u1", "raw_text": "原始主体引介。"}],
        "context_original_member_checks": [{"oracle_id": "o1", "previous_bad_context_observed": False}],
        "selection_material_sha256": "material-digest",
        "span_original_member_index": [{"span_id": "s1", "raw_text": "原始文本。" * 100000,
                                        "native_members": [{"unit_id": "u1", "valid_slice": True}]}],
        "reading_context_observations": {"source_processing_complete": False,
                                         "selection_trace": ["debug" * 10000] * 4},
    }


def cli(tmp_path, monkeypatch, *, worker=True):
    manifest = tmp_path / "cases.json"
    manifest.write_text(json.dumps({"cases": [{
        "case_id": "synthetic", "max_seconds": 90,
        "request": {"source_ref": {"source_id": "synthetic"}},
    }]}), encoding="utf-8")
    output = tmp_path / "result.json"
    args = ["source_case_runner", "--manifest", str(manifest), "--case", "synthetic", "--output", str(output)]
    if worker:
        args.append("--worker")
    monkeypatch.setattr(sys, "argv", args)
    return output, output.with_suffix(".json.checkpoint.json")


def test_large_completed_result_is_durable_and_keeps_checkpoint_evidence(tmp_path, monkeypatch):
    output, checkpoint = cli(tmp_path, monkeypatch)
    record = producer_record()

    def execute(_case, *, checkpoint_sink):
        checkpoint_sink(record, "ORIGINAL_BEFORE_OPEN")
        saved = json.loads(checkpoint.read_bytes())
        assert saved["original_files_before"] == record["original_files_before"]
        assert saved["database_before"] == record["database_before"]
        return deepcopy(record)

    monkeypatch.setattr(runner, "execute", execute)
    runner.main()
    saved = json.loads(output.read_bytes())
    assert len(output.read_bytes()) > 300000
    assert saved["span_original_member_index"] == record["span_original_member_index"]
    assert saved["reading_context_observations"] == record["reading_context_observations"]
    assert saved["status"] == record["status"]
    assert saved["required_units"] == record["required_units"]
    assert saved["source_excerpt_units"] == record["source_excerpt_units"]
    assert saved["context_original_member_checks"] == record["context_original_member_checks"]
    assert saved["database_before"] == record["database_before"]
    assert saved["database_after"] == record["database_after"]
    assert not checkpoint.exists()
    assert not list(tmp_path.glob("*.writing-*"))


def test_encoder_error_keeps_result_ready_checkpoint_and_incomplete_receipt(tmp_path, monkeypatch):
    output, checkpoint = cli(tmp_path, monkeypatch)
    record = producer_record()
    original = runner.encode_receipt

    def fail_final(value, **kwargs):
        if value.get("selection_material_sha256") and "phase" not in value:
            raise RuntimeError("do not serialize exception body")
        return original(value, **kwargs)

    monkeypatch.setattr(runner, "encode_receipt", fail_final)
    monkeypatch.setattr(runner, "execute", lambda _case, **_kwargs: deepcopy(record))
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 2
    saved = json.loads(output.read_bytes())
    assert saved["status"] == "OBSERVATION_INCOMPLETE"
    assert saved["source_status"] == record["status"]
    durable = json.loads(checkpoint.read_bytes())
    assert durable["phase"] == "RESULT_READY"
    assert durable["database_unchanged"] is True
    assert durable["required_checkpoints"][0]["represented"] is True
    assert "do not serialize" not in output.read_text(encoding="utf-8")


def test_unexpected_execution_failure_retains_prior_checkpoint_without_inventing_after_proof(tmp_path, monkeypatch):
    output, _checkpoint = cli(tmp_path, monkeypatch)

    def fail_after_checkpoint(_case, *, checkpoint_sink):
        checkpoint_sink({"case_id": "synthetic", "database_before": {"db": "observed-before"}}, "SOURCE_READY")
        raise OSError("unexpected reader or observer failure")

    monkeypatch.setattr(runner, "execute", fail_after_checkpoint)
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 2
    saved = json.loads(output.read_bytes())
    assert saved["status"] == "FAILED"
    assert saved["execution_checkpoint"]["database_before"] == {"db": "observed-before"}
    assert saved["database_unchanged"] is None
    assert saved["original_files_unchanged"] is None
    assert saved["runtime_unchanged"] is None


def test_observer_code_change_is_recorded_and_cannot_validate_the_source_run(tmp_path, monkeypatch):
    output, _checkpoint = cli(tmp_path, monkeypatch)
    states = iter(({"synthetic": "before"}, {"synthetic": "after"}))
    monkeypatch.setattr(runner, "observer_state", lambda: next(states))
    monkeypatch.setattr(runner, "execute", lambda _case, **_kwargs: producer_record())
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 2
    saved = json.loads(output.read_bytes())
    assert saved["observer_unchanged"] is False
    assert saved["observer_before"] == {"synthetic": "before"}
    assert saved["observer_after"] == {"synthetic": "after"}
    assert saved["required_units"][0]["represented"] is True


def test_owned_writer_does_not_overwrite_foreign_result(tmp_path):
    output = tmp_path / "foreign.json"
    output.write_bytes(b"foreign")
    with pytest.raises(FileExistsError):
        runner.atomic_owned_write(output, b"new", {}, root_dir=tmp_path)
    assert output.read_bytes() == b"foreign"
    assert not list(tmp_path.glob("*.writing-*"))


@pytest.mark.parametrize("previously_owned", (False, True))
def test_late_foreign_writer_wins_without_observer_clobber(tmp_path, monkeypatch, previously_owned):
    output = tmp_path / "race.json"
    owned = {}
    if previously_owned:
        runner.atomic_owned_write(output, b"own-checkpoint", owned, root_dir=tmp_path)
    fsync = runner.os.fsync

    def foreign_writer_after_preflight(fd):
        fsync(fd)
        output.write_bytes(b"foreign-winner")

    monkeypatch.setattr(runner.os, "fsync", foreign_writer_after_preflight)
    with pytest.raises(FileExistsError):
        runner.atomic_owned_write(output, b"own-result", owned, root_dir=tmp_path)
    assert output.read_bytes() == b"foreign-winner"
    assert not list(tmp_path.glob("*.writing-*"))


def test_owned_writer_stays_in_declared_test_directory(tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "-outside.json")
    assert not outside.exists()
    with pytest.raises(ValueError):
        runner.atomic_owned_write(outside, b"new", {}, root_dir=tmp_path)
    assert not outside.exists()


def test_atomic_replace_failure_preserves_previous_checkpoint(tmp_path, monkeypatch):
    path = tmp_path / "checkpoint.json"
    owned = {}
    runner.atomic_owned_write(path, b"previous", owned, root_dir=tmp_path)

    def fail_replace(*_args):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(runner.os, "replace", fail_replace)
    with pytest.raises(OSError):
        runner.atomic_owned_write(path, b"new", owned, root_dir=tmp_path)
    assert path.read_bytes() == b"previous"
    assert owned[path.resolve()] == sha256(b"previous").hexdigest()
    assert not list(tmp_path.glob("*.writing-*"))


@pytest.mark.parametrize("completed", (False, True))
def test_parent_timeout_preserves_child_checkpoint_or_committed_result(tmp_path, monkeypatch, completed):
    output, checkpoint = cli(tmp_path, monkeypatch, worker=False)
    original_bytes = b'{"status":"child-result-already-durable"}'

    def timeout(command, **_kwargs):
        checkpoint.write_bytes(b'{"phase":"ORIGINAL_BEFORE_OPEN","before":"observed"}')
        if completed:
            output.write_bytes(original_bytes)
        raise subprocess.TimeoutExpired(command, 90)

    monkeypatch.setattr(runner.subprocess, "run", timeout)
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 124
    assert checkpoint.exists()
    if completed:
        assert output.read_bytes() == original_bytes
    else:
        saved = json.loads(output.read_bytes())
        assert saved["status"] == "PARENT_TIMEOUT"
        assert saved["checkpoint_sha256"] == sha256(checkpoint.read_bytes()).hexdigest()
        assert "database_unchanged" not in saved


def test_fixed_oracle_excerpts_keep_current_intro_and_explicit_missing_lineage():
    def unit(uid, text):
        return SimpleNamespace(unit_id=uid, source_id="synthetic", source_role="company_filing",
                               raw_text=text, coordinates=SimpleNamespace(locator=lambda: "loc:" + uid))

    originals = {"current": unit("current", "本公司作出当前承诺。"),
                 "intro": unit("intro", "新主体的原始引介：")}
    rows, coverage = runner.excerpt_units_for_checkpoints(
        [{"current_original_unit_id": "current"}],
        [{"original_support_unit_ids": ["current"], "original_forbidden_context_unit_ids": ["old-missing"],
          "mapped_support_span_ids": ["support"]}],
        [{"span_id": "context", "native_members": [{"unit_id": "intro", "valid_slice": True}]},
         {"span_id": "untraceable", "native_members": [{"unit_id": "invented", "valid_slice": False}]}],
        [{"support_evidence_ids": ["support"], "context_evidence_ids": ["context", "untraceable"]}],
        originals,
    )
    assert {row["unit_id"] for row in rows} == {"current", "intro"}
    intro = next(row for row in rows if row["unit_id"] == "intro")
    assert intro["raw_text"] == originals["intro"].raw_text
    assert intro["text_sha256"] == sha256(intro["raw_text"].encode()).hexdigest()
    assert coverage["unavailable_original_ids"] == ["old-missing"]
    assert coverage["untraceable_current_context_span_ids"] == ["untraceable"]


def test_unselected_target_keeps_actual_tree_intro_and_required_context():
    oracles = [{"oracle_id": "unselected", "original_support_unit_ids": ["body"],
                "original_forbidden_context_unit_ids": ["previous-intro"]}]
    structure = {
        "sections": [
            {"section_id": "outer", "parent_id": None, "heading_unit_ids": ["outer-title"]},
            {"section_id": "current-note", "parent_id": "outer", "heading_unit_ids": ["current-intro"],
             "body_unit_ids": ["body"]},
        ],
        "semantic_units": [{"required_context_by_unit_id": {"body": ["local-qualifier"]}}],
    }
    originals = {uid: object() for uid in ("outer-title", "current-intro", "body", "local-qualifier")}
    rows, contexts = runner.structure_context_checkpoints(oracles, structure, originals)
    actual = rows[0]["support_units"][0]
    assert contexts == {"outer-title", "current-intro", "local-qualifier"}
    assert actual["forbidden_context_ids_observed"] == []
    assert actual["section_paths"][0]["ancestry_path_complete"] is True
    assert rows[0]["status"] == "STRUCTURE_OBSERVED_NO_ACTOR_INFERENCE"


@pytest.mark.parametrize("fault", ("missing", "cycle", "anonymous"))
def test_structure_projection_reports_incomplete_ancestry_without_inventing_scope(fault):
    parent = "absent" if fault == "missing" else "child"
    structure = {"sections": [{"section_id": None if fault == "anonymous" else "child", "parent_id": parent,
                                "heading_unit_ids": ["intro"], "body_unit_ids": ["body"]}],
                 "diagnostics": [{"code": "SOURCE_SCOPE_UNPROVEN", "unit_ids": ["body"]}]}
    rows, _contexts = runner.structure_context_checkpoints(
        [{"oracle_id": "unknown", "original_support_unit_ids": ["body"]}], structure,
        {"body": object()},
    )
    target = rows[0]["support_units"][0]
    assert target["section_paths"][0]["ancestry_path_complete"] is False
    assert target["source_diagnostics"] == [{"code": "SOURCE_SCOPE_UNPROVEN", "unit_ids": ["body"]}]
    assert rows[0]["status"] == "STRUCTURE_OBSERVED_NO_ACTOR_INFERENCE"


def test_fresh_process_entry_keeps_config_preflight_failure_without_source_access(tmp_path):
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "receipt.json"
    manifest.write_text(json.dumps({"cases": [{
        "case_id": "synthetic-preflight", "max_seconds": 20,
        "catalog_config": str(tmp_path / "absent-config.yaml"),
        "request": {"source_ref": {"source_id": "synthetic"}},
    }]}), encoding="utf-8")
    command = [sys.executable, "-B", "-X", "utf8", "-m", "tools.source_case_runner",
               "--manifest", str(manifest), "--case", "synthetic-preflight", "--output", str(output)]
    result = subprocess.run(command, cwd=runner.ROOT, capture_output=True, timeout=30, check=False)
    assert result.returncode == 2, result.stderr.decode("utf-8", "replace")
    saved = json.loads(output.read_bytes())
    assert saved["status"] == "FAILED"
    assert saved["observation_execution_failed"] is True
    assert saved["execution_checkpoint"]["phase"] == "RUN_START"
    assert saved["database_unchanged"] is None
    assert saved["original_files_unchanged"] is None
    assert saved["model_posts"] == 0 and saved["downloads"] == 0
    assert not (tmp_path / "absent-config.yaml").exists()
    assert not output.with_suffix(".json.checkpoint.json").exists()


def test_valid_deep_ancestry_is_complete_without_an_arbitrary_cutoff():
    sections = [{"section_id": str(i), "parent_id": str(i+1) if i < 99 else None,
                 "heading_unit_ids": ["h" + str(i)], "body_unit_ids": ["body"] if i == 0 else []}
                for i in range(100)]
    rows, contexts = runner.structure_context_checkpoints(
        [{"oracle_id": "deep", "original_support_unit_ids": ["body"]}],
        {"sections": sections}, {"body": object(), **{"h"+str(i): object() for i in range(100)}})
    actual = rows[0]["support_units"][0]
    assert actual["section_paths"][0]["ancestry_path_complete"] is True
    assert len(actual["section_paths"][0]["sections"]) == 100
    assert len(contexts) == 100


def test_physical_source_proof_is_not_semantic_context_but_remains_traceable():
    oracles = [{"oracle_id": "roles", "original_support_unit_ids": ["body"],
                "original_forbidden_context_unit_ids": ["old-tail"]}]
    semantic = {"required_context_by_unit_id": {"body": ["current-intro"]},
                "required_source_unit_ids_by_unit_id": {"body": ["old-tail"]}}
    rows, contexts = runner.structure_context_checkpoints(
        oracles, {"semantic_units": [semantic]},
        {uid: object() for uid in ("body", "current-intro", "old-tail")})
    actual = rows[0]["support_units"][0]
    assert actual["forbidden_context_ids_observed"] == []
    assert actual["semantic_context_unit_ids"] == ["current-intro"]
    assert actual["physical_source_proof_unit_ids"] == ["old-tail"]
    assert contexts == {"current-intro", "old-tail"}
    semantic["required_context_by_unit_id"]["body"].append("old-tail")
    rows, _ = runner.structure_context_checkpoints(oracles, {"semantic_units": [semantic]}, {})
    assert rows[0]["support_units"][0]["forbidden_context_ids_observed"] == ["old-tail"]


def test_checkpoint_larger_than_old_16k_is_durable(tmp_path, monkeypatch):
    output, checkpoint = cli(tmp_path, monkeypatch)
    record = producer_record()
    record["database_before"] = {str(i): {"sha256": "a" * 64} for i in range(400)}
    def execute(_case, *, checkpoint_sink):
        checkpoint_sink(record, "SOURCE_READY")
        assert checkpoint.stat().st_size > 16384
        assert json.loads(checkpoint.read_bytes())["database_before"] == record["database_before"]
        return record
    monkeypatch.setattr(runner, "execute", execute)
    runner.main()
    assert json.loads(output.read_bytes())["database_before"] == record["database_before"]
    assert not checkpoint.exists()
