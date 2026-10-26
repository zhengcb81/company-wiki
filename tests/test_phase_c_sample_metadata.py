"""Phase C company/carrier choice comes from prepared source facts, not IDs."""
from copy import deepcopy

import pytest

from tools.document_understanding_benchmark import phase_c_runner as runner


def prepared_sample():
    return {
        "sample_id": "unseen-letter-17",
        "provider": "configured-provider",
        "source_metadata_observation": {
            "entity": "Example Issuer",
            "publisher": "Example Holdings",
            "market": "US",
            "security_id": "EXMP",
            "language": "zh-hant",
            "title": "Shareholder letter",
            "document_kind": "investor_relations",
            "fiscal_year": 2019,
            "filing_date": "2020-03-11",
        },
    }


def test_unseen_sample_uses_explicit_company_and_language_without_id_mapping():
    sample = prepared_sample()
    before = deepcopy(sample)
    descriptor = runner.source_descriptor(sample)
    assert descriptor["entity"] == "Example Issuer"
    assert descriptor["publisher"] == "Example Holdings"
    assert descriptor["language"] == "zh-hant", "market cannot determine source language"
    assert descriptor["document_kind"] == "investor_relations"
    assert descriptor["published_date"] == "2020-03-11"
    assert sample == before


def test_source_owned_correction_supersedes_unreliable_observation_for_every_field():
    sample = prepared_sample()
    sample["verified_official_descriptor"] = {
        "entity": "Verified Issuer", "publisher": "Verified Holdings",
        "market": "HK", "security_id": "00123", "language": "en",
        "title": "Interim announcement", "document_kind": "semi_annual_report",
        "published_date": "2020-08-03", "fiscal_year": 2020,
    }
    descriptor = runner.source_descriptor(sample)
    for key, value in sample["verified_official_descriptor"].items():
        assert descriptor[key] == value


def test_legacy_source_identifier_is_usable_without_inventing_company_or_language():
    sample = prepared_sample()
    observation = sample["source_metadata_observation"]
    for key in ("entity", "publisher", "language"):
        del observation[key]
    # A familiar historical ID must not secretly restore a fixed company name.
    sample["sample_id"] = "cn-h1"
    descriptor = runner.source_descriptor(sample)
    assert descriptor["entity"] == "EXMP"
    assert descriptor["language"] is None


def test_missing_source_identity_is_explained_without_guessing_from_sample_id():
    sample = prepared_sample()
    for key in ("entity", "security_id"):
        del sample["source_metadata_observation"][key]
    with pytest.raises(ValueError, match="source identity"):
        runner.source_descriptor(sample)


def test_cli_accepts_prepared_sample_ids_without_creating_any_io(tmp_path):
    destination = tmp_path / "not-created"
    args = runner.argument_parser().parse_args([
        "--mode", "live", "--sample", "unseen-letter-17", "--output", str(destination)
    ])
    assert args.sample == "unseen-letter-17"
    assert not destination.exists()


def test_live_input_selection_is_exact_and_reuses_the_prepared_provider():
    sample = prepared_sample()
    provider = {"provider": "configured-provider", "options": {"model_id": "existing-model"}}
    metadata = {"samples": [sample], "providers": [provider]}
    selected, configured = runner.prepared_live_input(metadata, "unseen-letter-17")
    assert selected is sample and configured is provider


@pytest.mark.parametrize("part", ["samples", "providers"])
def test_ambiguous_preparation_cannot_silently_select_first_row(part):
    metadata = {"samples": [prepared_sample()], "providers": [{"provider": "configured-provider"}]}
    metadata[part].append(deepcopy(metadata[part][0]))
    with pytest.raises(ValueError, match="unique prepared"):
        runner.prepared_live_input(metadata, "unseen-letter-17")


def test_unknown_sample_is_explicit_metadata_error():
    with pytest.raises(ValueError, match="unique prepared sample"):
        runner.prepared_live_input({"samples": [], "providers": []}, "missing")


def test_real_main_rejects_ambiguous_metadata_before_preflight_or_output(tmp_path, monkeypatch):
    import json
    import sys

    sample = prepared_sample()
    metadata = tmp_path / "preparation.json"
    metadata.write_text(json.dumps({"samples": [sample, deepcopy(sample)]}), encoding="utf-8")
    destination = tmp_path / "must-not-exist"
    monkeypatch.setattr(sys, "argv", ["phase_c_runner", "--mode", "live", "--sample", sample["sample_id"],
                        "--metadata", str(metadata), "--usage-ledger", str(tmp_path / "usage.jsonl"),
                        "--output", str(destination)])
    def unexpected_preflight(*_args, **_kwargs):
        raise AssertionError("ambiguous selection must be explained before any preparation IO")
    monkeypatch.setattr(runner, "verify_preparation", unexpected_preflight)
    with pytest.raises(ValueError, match="unique prepared sample"):
        runner.main()
    assert not destination.exists()


def live_fixture(tmp_path):
    sample = prepared_sample()
    raw, gold, output = tmp_path / "source.txt", tmp_path / "gold.json", tmp_path / "output"
    raw.write_text("Original operating statement.", encoding="utf-8")
    gold.write_text('{"facts": []}', encoding="utf-8")
    output.mkdir()
    sample.update(original=str(raw), fingerprint=runner.fingerprint(raw), gold=str(gold), mime_type="text/plain")
    metadata = runner.loopback_preparation()
    return sample, metadata["providers"][0], metadata, output


@pytest.mark.parametrize("fault", ["missing_original", "malformed_gold"])
def test_setup_exceptions_restore_owned_directory_before_any_model_call(tmp_path, monkeypatch, fault):
    from pathlib import Path
    import json

    sample, provider, metadata, output = live_fixture(tmp_path)
    if fault == "missing_original":
        Path(sample["original"]).unlink()
        expected = FileNotFoundError
    else:
        Path(sample["gold"]).write_text("not JSON", encoding="utf-8")
        expected = json.JSONDecodeError
    monkeypatch.setattr(runner.tempfile, "tempdir", str(tmp_path))
    def no_model(*_args, **_kwargs):
        raise AssertionError("setup failure cannot reach source acquisition or model")
    monkeypatch.setattr(runner, "seed_identity", no_model)
    with pytest.raises(expected):
        runner.run_pair(sample, provider, metadata, mode="live", output=output, selected_versions="0.9.0")
    assert not list(tmp_path.glob("cwplC-*"))
    assert not (output / "events.jsonl").exists()


@pytest.mark.parametrize("known_date", [True, False])
def test_unrelated_correction_never_certifies_publication_date(tmp_path, monkeypatch, known_date):
    sample, provider, metadata, output = live_fixture(tmp_path)
    sample["verified_official_descriptor"] = {"title": "Verified title only"}
    if not known_date:
        del sample["source_metadata_observation"]["filing_date"]
    monkeypatch.setattr(runner.tempfile, "tempdir", str(tmp_path))
    def stop_before_model(*_args, **_kwargs):
        raise RuntimeError("bounded source setup probe")
    monkeypatch.setattr(runner, "seed_identity", stop_before_model)
    result = runner.run_pair(sample, provider, metadata, mode="live", output=output, selected_versions="0.9.0")
    actual = result["availability_date_provenance"]
    assert actual["method"] == ("source_metadata_observation.filing_date" if known_date else "unknown_public_availability")
    assert actual["registered_published_date"] == ("2020-03-11" if known_date else None)
    assert result["model_post_attempts"] == 0 and result["temporary_lake_removed"]
