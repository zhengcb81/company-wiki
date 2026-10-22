"""Fresh non-author W03-A RF probes. Static public wire, no CWP imports/API."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

import pytest

RF = Path(os.environ["W03_RF_ROOT"])
sys.path.insert(0, str(RF / "scripts"))
import company_wiki_narrative_contracts as wire
from company_wiki_narrative_reader import read_narrative_context

GOLDEN = RF / "tests/fixtures/cwp_narrative_transport_v1"
BODY = (GOLDEN / "bundle.json").read_bytes()


def base():
    request = json.loads((GOLDEN / "read_request.json").read_bytes())
    receipt = json.loads((GOLDEN / "read_receipt.json").read_bytes())
    return request, receipt


def proof(sha, *, available="2026-08-01", basis="prior_verified_capture"):
    return {"schema_version": "source-availability-evidence/1",
            "source_sha256": sha, "available_by": available, "basis": basis,
            "evidence_ref": "source-provenance:independent:receipt", "locator": "/receipt/content_sha256"}


def unknown(*, basis="prior_verified_capture"):
    request, receipt = base()
    receipt["manifest"]["published_date"] = None
    receipt["availability_evidence"] = proof(receipt["manifest"]["content_sha256"], basis=basis)
    return request, receipt


def validate(request, receipt):
    return wire.validate_narrative_response(
        request, BODY, wire.canonical_bytes(receipt) + b"\n").to_dict()


@pytest.mark.parametrize("basis", ["prior_verified_capture", "primary_archive", "current_verified_open"])
def test_same_sha_proof_is_retained_only_in_receipt_without_body_or_publication_rewrite(basis):
    request, receipt = unknown(basis=basis)
    before = deepcopy(receipt)
    value = validate(request, receipt)
    assert value["manifest"]["published_date"] is None
    assert value["read_receipt"]["availability_evidence"] == receipt["availability_evidence"]
    assert "availability_evidence" not in value
    assert value["summary"] == json.loads(BODY)["summary"]
    assert receipt == before


@pytest.mark.parametrize("mutation", ["schema", "sha", "extra_path", "extra_unknown", "date", "basis_type"])
def test_malformed_or_foreign_proof_never_qualifies_unknown_publication(mutation):
    request, receipt = unknown()
    item = receipt["availability_evidence"]
    if mutation == "schema": item["schema_version"] = "source-availability-evidence/99"
    elif mutation == "sha": item["source_sha256"] = "b" * 64
    elif mutation == "extra_path": item["physical_path"] = "original.pdf"
    elif mutation == "extra_unknown": item["signed_by_user"] = True
    elif mutation == "date": item["available_by"] = "2026-02-30"
    else: item["basis"] = ["current_verified_open"]
    with pytest.raises(wire.NarrativeTransportError):
        validate(request, receipt)


@pytest.mark.parametrize("missing", [True, False])
def test_unknown_historical_no_proof_remains_named_gap(missing):
    request, receipt = unknown()
    if missing: receipt.pop("availability_evidence")
    else: receipt["availability_evidence"] = None
    with pytest.raises(wire.NarrativeTransportError) as error:
        validate(request, receipt)
    assert error.value.reason == "source_publication_unknown"


@pytest.mark.parametrize("published", ["2026-09-02", "2026-02-30"])
def test_known_future_or_invalid_publication_wins_even_over_bad_earlier_proof(published):
    request, receipt = unknown()
    receipt["manifest"]["published_date"] = published
    receipt["availability_evidence"]["source_sha256"] = "b" * 64
    with pytest.raises(wire.NarrativeTransportError) as error:
        validate(request, receipt)
    assert error.value.reason == ("source_after_as_of" if published == "2026-09-02" else "invalid_as_of_date")


def test_unknown_proof_later_than_historical_cutoff_is_refused():
    request, receipt = unknown()
    receipt["availability_evidence"]["available_by"] = "2026-09-02"
    with pytest.raises(wire.NarrativeTransportError, match="source_availability_after_asof"):
        validate(request, receipt)


def test_actual_read_cannot_precede_its_qualifying_availability():
    request, receipt = unknown()
    receipt["availability_evidence"]["available_by"] = "2026-08-15"
    receipt["manifest"]["retrieved_at"] = None
    receipt["read_at"] = "2026-08-02T00:00:00Z"
    with pytest.raises(wire.NarrativeTransportError, match="source_clock_conflict"):
        validate(request, receipt)


def test_original_retrieval_cannot_be_after_actual_read():
    request, receipt = unknown()
    receipt["manifest"]["retrieved_at"] = "2026-10-04T00:00:00Z"
    with pytest.raises(wire.NarrativeTransportError, match="source_clock_conflict"):
        validate(request, receipt)


@pytest.mark.parametrize("published", [None, "2027-01-01"])
@pytest.mark.parametrize("include_null", [False, True])
def test_legacy_current_without_proof_gains_no_historical_gate(published, include_null):
    request, receipt = base()
    request["as_of_date"] = receipt["as_of_date"] = None
    receipt["manifest"]["published_date"] = published
    receipt["manifest"]["retrieved_at"] = "2027-01-02T00:00:00Z"
    if include_null: receipt["availability_evidence"] = None
    value = validate(request, receipt)
    assert value["as_of_date"] is None and value["manifest"]["published_date"] == published


@pytest.mark.parametrize("late", [False, True])
def test_current_with_explicit_proof_uses_actual_read_day_and_not_a_new_authorization(late):
    request, receipt = unknown()
    request["as_of_date"] = receipt["as_of_date"] = None
    receipt["manifest"]["retrieved_at"] = None
    receipt["availability_evidence"]["available_by"] = "2026-10-04" if late else "2026-10-03"
    if late:
        with pytest.raises(wire.NarrativeTransportError, match="source_availability_after_asof"):
            validate(request, receipt)
    else:
        assert validate(request, receipt)["manifest"]["published_date"] is None


def test_known_past_publication_is_not_replaced_by_later_capture():
    request, receipt = base()
    receipt["availability_evidence"] = proof(receipt["manifest"]["content_sha256"], available="2026-10-04")
    assert validate(request, receipt)["manifest"]["published_date"] == "2026-08-01"


@pytest.mark.parametrize("value", [None, "proof"])
def test_projected_receipt_shape_cannot_accept_a_single_parent_root_proof(value):
    ref = {"schema_version": "narrative-ref/3", "artifact_version_id": "independent-projection",
           "artifact_sha256": "a" * 64, "byte_size": 1000, "generation_sha256": "d" * 64,
           "subject_ref": {"schema_version": "narrative-subject-ref/1", "kind": "official_json",
                           "item_key": "urn:company-wiki:source-projection:sha256:" + "c" * 64,
                           "subject_sha256": "c" * 64}}
    request = {"schema_version": "narrative-read-request/3", "narrative_ref": ref,
               "as_of_date": "2026-09-01", "expected_issuer": None}
    receipt = {"schema_version": "narrative-read-receipt/3", "status": "ok", "narrative_ref": ref,
               "as_of_date": request["as_of_date"], "observed_at": "2026-10-03T00:00:00Z",
               "locator_count": 2, "parent_count": 2, "lineage_sha256": "e" * 64,
               "selection_status": "selected", "quality_status": "verified", "replay_status": "verified"}
    wire._projected_receipt(receipt, request)  # Shape control, not projected-body acceptance.
    receipt["availability_evidence"] = None if value is None else proof("a" * 64)
    with pytest.raises(wire.NarrativeTransportError, match="invalid_read_receipt"):
        wire._projected_receipt(receipt, request)


def test_actual_bounded_rf_reader_child_keeps_the_complete_optional_proof(tmp_path):
    request, receipt = unknown(basis="current_verified_open")
    (tmp_path / "body.bin").write_bytes(BODY)
    (tmp_path / "receipt.jsonl").write_bytes(wire.canonical_bytes(receipt) + b"\n")
    child = tmp_path / "emit.py"
    child.write_text("import sys\nfrom pathlib import Path\np=Path(__file__).parent\n"
                     "sys.stdin.buffer.read()\n"
                     "sys.stdout.buffer.write((p/'body.bin').read_bytes())\n"
                     "sys.stderr.buffer.write((p/'receipt.jsonl').read_bytes())\n", encoding="utf-8")
    result = read_narrative_context(
        request, catalog_config=(tmp_path / "not-opened.yaml").resolve(),
        reader_command=[sys.executable, "-S", str(child)], timeout_seconds=10).to_dict()
    assert result["read_receipt"] == receipt
    assert result["manifest"]["published_date"] is None
