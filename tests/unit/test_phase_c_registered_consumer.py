"""A pinned source is not a request to discover the latest fiscal filing."""

from pathlib import Path

import pytest

from tools.document_understanding_benchmark import phase_c_runner as runner


@pytest.mark.parametrize("fiscal_year", [None, 2025])
def test_consumer_chooses_existing_registered_entry_without_inventing_period(
    tmp_path, monkeypatch, fiscal_year
):
    ref = {"document_id": "doc", "source_id": "src", "content_sha256": "a" * 64}
    narrative = {"narrative_ref": {"source_ref": ref}}
    bundle = {"source_ref": ref, "reading_context": {}, "evidence_spans": [], "summary": {}}
    observed = []

    def cli(root, output, name, command, env, data=None, **kwargs):
        observed.append((name, command, data))
        if name == "rf-registered-source":
            assert data["candidate"]["source_ref"] == ref
            assert data["candidate"]["fiscal_year"] is None
            assert type(data["candidate"]["download_events"]) is int
            assert data["candidate"]["download_events"] == 0
            return 0, {"source": {"source_id": "src"}, "filing_fetch": None}, "", b""
        if name == "ff-reuse":
            return 0, {"downloads": 0}, "", b""
        if name == "rf-source":
            return 0, {"filing_fetch": {"downloads": 0}, "narrative": narrative}, "", b""
        assert name == "rf-narrative"
        return 0, {**bundle, **narrative, "read_receipt": {"replay_status": "verified"}}, "", b""

    monkeypatch.setattr(runner, "_cli", cli)
    descriptor = {"security_id": "XYZ", "market": "US", "document_kind": "investor_relations",
                  "fiscal_year": fiscal_year, "fiscal_period": None}
    result = runner.consumers(tmp_path, tmp_path, {}, tmp_path / "catalog.yaml",
                              descriptor, narrative, bundle, projects=Path("siblings"))
    names = [row[0] for row in observed]
    if fiscal_year is None:
        assert names == ["rf-registered-source", "rf-narrative"]
        assert result[0]["status"] == "NOT_REQUESTED_ALREADY_REGISTERED"
        assert result[0]["downloads"] == 0
        assert "exit" not in result[0], "not requested is not an invented FF success"
    else:
        assert names == ["ff-reuse", "rf-source", "rf-narrative"]


def test_fidelity_protocol_is_an_explicit_runner_option():
    args = runner.argument_parser().parse_args(
        ["--output", "owned-receipts", "--reading-model-projection", "reading-model-input/6"]
    )
    assert args.reading_model_projection == "reading-model-input/6"
    assert runner.argument_parser().parse_args(["--output", "owned-receipts"]).reading_model_projection == "reading-model-input/4"


def test_fidelity_option_survives_runner_projection_resolution():
    from company_wiki.automation.narrative_summary_protocols import FIDELITY_SCOPED

    assert runner.reading_projection_for("0.9.0", FIDELITY_SCOPED.projection) == FIDELITY_SCOPED.projection
    assert runner.reading_projection_for("0.8.0", FIDELITY_SCOPED.projection) is None


def test_fidelity_success_observes_assessment_without_inventing_extractive_report(tmp_path):
    from unit.test_narrative_fidelity_artifacts import materials
    from company_wiki.automation.narrative_verify import NarrativeVerifyHandler

    source, summary = materials()
    report = NarrativeVerifyHandler._bundle(source, summary, source.prompt_review).to_dict()["summary_assessment"]
    receipt = {"documents": [{"model_diagnostics": [{"execution": report}]}]}
    result = runner.successful_model_observation(
        receipt, [], [], tmp_path, "run", reading_model_projection="reading-model-input/6"
    )
    assert result["source_card_execution"] is None
    observed = result["summary_assessment_observation"]
    assert observed["schema_version"] == "summary-assessment/1"
    assert observed["missing_requested_task_keys"] == ["t2"]
    assert observed["semantic_status"] == observed["subfact_coverage_status"] == "not_evaluated"
    assert result["paid_response_capture"] == []


@pytest.mark.parametrize("fault", ["missing", "extractive"])
def test_fidelity_success_requires_its_actual_assessment(tmp_path, fault):
    if fault == "extractive":
        from test_phase_c_extractive import capture_fixture

        _, receipt, _, _, _ = capture_fixture(tmp_path)
    else:
        receipt = {"documents": []}
    with pytest.raises(ValueError, match="PHASE_C_FIDELITY_ASSESSMENT_NOT_OBSERVED"):
        runner.successful_model_observation(
            receipt, [], [], tmp_path, "run", reading_model_projection="reading-model-input/6"
        )


@pytest.mark.parametrize("fault", [None, "removed", "changed"])
def test_registered_consumer_cannot_drop_or_change_summary_observations(tmp_path, monkeypatch, fault):
    ref = {"document_id": "doc", "source_id": "src", "content_sha256": "a" * 64}
    narrative = {"narrative_ref": {"source_ref": ref}}
    bundle = {"source_ref": ref, "reading_context": {}, "evidence_spans": [],
              "summary": {}, "summary_assessment": {"semantic_status": "not_evaluated"}}
    observed = []

    def cli(root, output, name, command, env, data=None, **kwargs):
        observed.append(name)
        assert env["CWP_PHASE_C_NO_NETWORK"] == "1"
        if name == "rf-registered-source":
            assert type(data["candidate"]["download_events"]) is int
            assert data["candidate"]["download_events"] == 0
            return 0, {"filing_fetch": None}, "", b""
        assert name == "rf-narrative"
        value = {**bundle, **narrative, "read_receipt": {"replay_status": "verified"}}
        if fault == "removed":
            del value["summary_assessment"]
        elif fault == "changed":
            value["summary_assessment"] = {"semantic_status": "verified"}
        return 0, value, "", b""

    monkeypatch.setattr(runner, "_cli", cli)
    descriptor = {"security_id": "XYZ", "market": "US", "document_kind": "prospectus",
                  "fiscal_year": None, "fiscal_period": None}
    args = (tmp_path, tmp_path, {}, tmp_path / "catalog.yaml", descriptor, narrative, bundle)
    if fault is None:
        result = runner.consumers(*args, projects=Path("siblings"))
        assert result[-1]["summary_assessment_preserved"] is True
    else:
        with pytest.raises(AssertionError):
            runner.consumers(*args, projects=Path("siblings"))
    assert observed == ["rf-registered-source", "rf-narrative"]


def test_registered_source_failure_does_not_fall_back_to_discovery(tmp_path, monkeypatch):
    observed = []

    def cli(root, output, name, command, env, data=None, **kwargs):
        observed.append(name)
        assert name == "rf-registered-source"
        assert type(data["candidate"]["download_events"]) is int
        assert data["candidate"]["download_events"] == 0
        return 1, {"error": "registered_source_manifest_mismatch"}, "", b""

    monkeypatch.setattr(runner, "_cli", cli)
    descriptor = {"security_id": "XYZ", "market": "US", "document_kind": "investor_relations",
                  "fiscal_year": None}
    narrative = {"narrative_ref": {"source_ref": {"document_id": "doc"}}}
    with pytest.raises(AssertionError):
        runner.consumers(tmp_path, tmp_path, {}, tmp_path / "catalog.yaml", descriptor,
                         narrative, {}, projects=Path("siblings"))
    assert observed == ["rf-registered-source"], "failed exact source is not permission to select another original"
