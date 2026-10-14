"""Source-owned v2 output; immutable legacy bytes and real HTTP projection."""
from base64 import b64decode
from dataclasses import FrozenInstanceError, asdict
import gzip
from hashlib import sha256
import json
import logging
from pathlib import Path

import pytest

from company_wiki.automation import narrative_model as model
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_contracts import NarrativeSelectResult, NarrativeContractError
from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
from company_wiki.source_contract import EvidenceSpan
from support.narrative_model_request_fixture import selection
from unit.test_narrative_reading_transport import reading_context, with_reading
from unit.test_official_json_model_subject import selection as official_selection

V1 = "reading-model-input/1"
V2 = "reading-model-input/2"
FROZEN = Path(__file__).parents[1] / "support/reading_boundary_legacy_snapshots.json.gz"
CASES = json.loads(gzip.decompress(FROZEN.read_bytes()))["cases"]


def official_reading(*, same_groups=False):
    selected = official_selection(same_groups=same_groups)
    wire = selected.to_dict()
    ctx = reading_context(selected)
    ctx["groups"] = [ctx["groups"][0], {
        "group_id": "parent-two", "kind": "business_progress", "section_role": "business",
        "evidence_ids": [selected.evidence_spans[2].span_id],
    }]
    wire["reading_context"] = ctx
    return NarrativeSelectResult.from_dict(wire)


def request(selected):
    return model.NarrativeModelRequest.from_selection(selected, reading_projection_version=V2)


def claim(*, claim_id="good", ids=None, groups=None, kind="company_statement", modality="actual"):
    return {"claim_id": claim_id, "text": "The company disclosed a concrete product milestone.",
        "evidence_ids": ids or ["e1"], "evidence_group_ids": [] if groups is None else groups,
        "claim_type": kind, "modality": modality}


def response(selected, claims, **echo):
    return model.NarrativeModelResponse("fixture", "configured-flash", request(selected).prompt_version,
        canonical_json({"draft": {"claims": claims, **echo}}).encode())


def decode(selected, claims, **echo):
    return model.decode_model_draft(response(selected, claims, **echo), selected=selected,
        reading_projection_version=V2)


def http_port():
    return NarrativeHTTPModel(model_id="frozen-byte-fixture", endpoint="https://fixture.invalid/v1",
        api_key_env="NO_REAL_KEY", max_output_tokens=8192, thinking="disabled", temperature=1.0)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case"])
def test_six_root_frozen_legacy_requests_and_actual_http_bytes_remain_exact(case):
    assert sha256(FROZEN.read_bytes()).hexdigest() == "b8403d5c8b3b3c75c4d70ed9c02e89dd0ea83ad3ab7aa4ef2b5898149da789dd"
    selected = NarrativeSelectResult.from_dict(case["selected"])
    actual = model.NarrativeModelRequest.from_selection(selected,
        reading_projection_version=case["reading_model_projection"])
    for field in ("instruction", "prompt_version", "data_json", "input_sha256"):
        assert getattr(actual, field) == case[field]
    body = http_port().request_bytes(actual)
    assert body == b64decode(case["http_body_base64"])
    assert sha256(body).hexdigest() == case["http_body_sha256"]


@pytest.mark.parametrize("selected", [with_reading(), official_reading()], ids=["raw", "official"])
def test_v2_body_and_schema_leave_identity_to_the_pinned_source(selected):
    before = selected.to_dict()
    actual = request(selected)
    data = json.loads(actual.data_json)
    envelope = data["subject" if selected.subject.kind == "official_json" else "source"]
    assert set(envelope) == {"title", "document_kind", "language"}
    assert actual.prompt_version == "reading-source-owned/2.0.0"
    assert data["schema_version"] == "narrative-model-request/3"
    assert data["reading_strategy"]["schema_version"] == V2
    schema = data["response_schema"]["properties"]["draft"]
    assert schema["required"] == ["claims"] and set(schema["properties"]) == {"claims"}
    assert schema["additionalProperties"] is False
    assert [row[1] for row in data["evidence"]] == [s.raw_text for s in selected.evidence_spans]
    assert "claims" in actual.instruction and "Do not echo" in actual.instruction
    assert "pure financial statement totals" in actual.instruction
    assert "No translation" in actual.instruction
    assert selected.to_dict() == before


def test_raw_and_official_v2_share_one_instruction_schema_and_decoder_boundary():
    raw = model.resolve_model_boundary(V2)
    projected = model.resolve_model_boundary(V2, projected=True)
    assert raw == projected and raw.source_owned
    assert asdict(raw) == {"reading_projection_version": V2, "prompt_version": "reading-source-owned/2.0.0",
        "request_schema": "narrative-model-request/3", "decoder_version": "reading-source-owned-decoder/2",
        "source_owned": True}
    with pytest.raises(FrozenInstanceError):
        raw.prompt_version = "mutated"
    assert request(with_reading()).instruction == request(official_reading()).instruction


@pytest.mark.parametrize("version", [False, True, "", "reading-model-input/99", "null", [], {}])
def test_unknown_version_never_silently_downgrades_request_or_decode(version):
    selected = with_reading()
    with pytest.raises(model.ModelResponseError, match="PROJECTION"):
        model.resolve_model_boundary(version)
    with pytest.raises(model.ModelResponseError, match="PROJECTION"):
        model.NarrativeModelRequest.from_selection(selected, reading_projection_version=version)
    reply = model.NarrativeModelResponse("fixture", "model", "reading-source-owned/2.0.0",
        canonical_json({"draft": {"claims": [claim()]}}).encode())
    with pytest.raises(model.ModelResponseError, match="PROJECTION"):
        model.decode_model_draft(reply, selected=selected, reading_projection_version=version)


def test_v2_requires_the_actual_selection_reading_context():
    with pytest.raises(model.ModelResponseError, match="CONTEXT"):
        request(selection())


@pytest.mark.parametrize("selected,ids", [(with_reading(), ["e1"]), (official_reading(), ["e2"]),
                                        (official_reading(same_groups=True), ["e3"])], ids=["raw", "parent1", "parent2"])
def test_claims_only_response_constructs_canonical_identity_and_language(selected, ids):
    actual = decode(selected, [claim(ids=ids)])
    if selected.subject.kind == "official_json":
        assert actual["subject_id"] == selected.subject.item_key
        assert actual["subject_sha256"] == selected.subject.subject_sha256
        assert "source_id" not in actual
    else:
        assert actual["source_id"] == selected.source_ref.source_id
        assert actual["source_sha256"] == selected.source_ref.content_sha256
    assert actual["language"] == selected.source_metadata.language
    assert actual["claims"][0]["evidence_ids"] == [selected.evidence_spans[int(alias[1:])-1].span_id for alias in ids]


def test_wrong_echo_is_ignored_once_without_raw_logging_or_model_quality_override(caplog):
    selected = with_reading()
    with caplog.at_level(logging.WARNING, logger=model.__name__):
        actual = decode(selected, [claim()], source_id="wrong-source-sensitive",
            source_sha256="e"*64, subject_id="wrong-subject-sensitive", subject_sha256="f"*64,
            language="en", status="approved")
    assert actual["source_id"] == selected.source_ref.source_id and actual["language"] == "zh"
    assert actual["status"] in {"draft", "needs_review"}
    records = [r for r in caplog.records if r.name == model.__name__]
    assert len(records) == 1
    assert records[0].getMessage() == "SOURCE_OWNED_MODEL_METADATA_ECHO_IGNORED"
    assert "sensitive" not in caplog.text and "e"*64 not in caplog.text


def test_same_http_content_still_hashes_different_pinned_originals():
    first = with_reading()
    wire = first.to_dict()
    digest = sha256(b"a different immutable original with identical selected quotations").hexdigest()
    sid = "urn:company-wiki:source:sha256:" + digest
    wire["source_ref"].update(source_id=sid, content_sha256=digest, document_id="other-original")
    replacements = {}
    new_spans = []
    for span in first.evidence_spans:
        rebound = EvidenceSpan.create(source_id=sid, coordinates=span.coordinates, raw_text=span.raw_text,
            structured_value=span.structured_value, parser_name=span.parser_name, parser_version=span.parser_version,
            parse_status=span.parse_status, quality_flags=span.quality_flags)
        replacements[span.span_id] = rebound.span_id
        new_spans.append(rebound.to_dict())
    wire["evidence_spans"] = new_spans
    for group in wire["reading_context"]["groups"]:
        group["evidence_ids"] = [replacements[x] for x in group["evidence_ids"]]
    second = NarrativeSelectResult.from_dict(wire)
    a, b = request(first), request(second)
    assert a.data_json == b.data_json
    assert http_port().request_bytes(a) == http_port().request_bytes(b)
    assert a.input_sha256 != b.input_sha256


def test_v2_http_body_retains_actual_aliases_groups_and_output_budget():
    selected = official_reading(same_groups=True)
    actual = request(selected)
    port = http_port()
    data = json.loads(json.loads(port.request_bytes(actual))["messages"][1]["content"])
    assert data["evidence_groups"] == [["g1", ["e1", "e2"]], ["g2", ["e3"]]]
    assert data["output_plan"]["configured_output_tokens"] == 8192
    assert data["output_plan"]["claim_unit"] == "one_subject_product_stage_modality"
    assert actual.with_output_budget(400).input_sha256 != actual.input_sha256
    assert json.loads(actual.with_output_budget(400).data_json)["output_plan"]["target_claim_count"] == 1


@pytest.mark.parametrize("bad", [claim(ids=["e1", "e999"]), claim(ids=["e1"], groups=["g1"]),
                                  claim(ids=["e1"], groups=["g999"]), claim(ids=["e1", "e1"]),
                                  claim(kind="invented"), claim(modality="invented")])
def test_bad_citation_group_or_claim_drops_the_entire_claim_and_keeps_recovery(bad):
    selected = with_reading()
    bad = {**bad, "claim_id": "bad"}
    actual = decode(selected, [bad, claim(claim_id="good", ids=["e3"])])
    assert [c["claim_id"] for c in actual["claims"]] == ["good"]
    assert actual["claims"][0]["evidence_ids"] == [selected.evidence_spans[2].span_id]
    assert actual["status"] == "needs_review"
    with pytest.raises((model.ModelResponseError, NarrativeContractError)):
        decode(selected, [bad])


def test_v2_does_not_convert_question_premise_to_company_statement():
    selected = official_reading()
    with pytest.raises(NarrativeContractError, match="non-company evidence"):
        decode(selected, [claim(ids=["e1"], kind="company_statement")])
    actual = decode(selected, [claim(ids=["e1"], kind="analyst_question", modality="question")])
    assert actual["claims"][0]["claim_type"] == "analyst_question"


@pytest.mark.parametrize("level", ["top", "draft", "claim"])
def test_explicit_translation_remains_whole_response_failure(level):
    selected = with_reading()
    payload = {"draft": {"claims": [claim()]}}
    node = payload if level == "top" else payload["draft"] if level == "draft" else payload["draft"]["claims"][0]
    node["translate"] = True
    reply = model.NarrativeModelResponse("fixture", "model", request(selected).prompt_version, canonical_json(payload).encode())
    with pytest.raises(model.ModelResponseError, match="untranslated"):
        model.decode_model_draft(reply, selected=selected, reading_projection_version=V2)


def test_boundary_identity_is_exact_pathless_actual_instruction_schema_and_decoder():
    actual = model.reading_model_boundary_identity(V2)
    assert set(actual) == {"schema_version", "reading_projection_version", "prompt_version", "request_schema",
        "decoder_version", "instruction_sha256", "response_schema_sha256", "decoder_sha256"}
    assert actual["schema_version"] == "reading-model-boundary/1"
    assert actual == model.reading_model_boundary_identity(V2, projected=True)
    instruction = request(with_reading()).instruction
    assert actual["instruction_sha256"] == sha256(instruction.encode()).hexdigest()
    source = Path(model.__file__).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    assert actual["decoder_sha256"] == sha256(source).hexdigest()
    assert all(len(actual[key]) == 64 for key in ("instruction_sha256", "response_schema_sha256", "decoder_sha256"))
    assert str(Path(model.__file__).parent) not in canonical_json(actual)


def test_legacy_and_v2_prompt_versions_are_not_silently_interchangeable():
    selected = with_reading()
    reply = model.NarrativeModelResponse("fixture", "model", "1.7.0",
        canonical_json({"draft": {"claims": [claim()]}}).encode())
    with pytest.raises(model.ModelResponseError, match="prompt version"):
        model.decode_model_draft(reply, selected=selected, reading_projection_version=V2)
    with pytest.raises(model.ModelResponseError, match="prompt version"):
        model.decode_model_draft(response(selected, [claim()]), selected=selected, reading_projection_version=None)


def test_actual_instruction_and_schema_changes_change_boundary_identity(monkeypatch):
    baseline = model.reading_model_boundary_identity(V2)
    monkeypatch.setattr(model, "_SOURCE_OWNED_INSTRUCTION", model._SOURCE_OWNED_INSTRUCTION + " Keep scope explicit.")
    instruction_changed = model.reading_model_boundary_identity(V2)
    assert instruction_changed["instruction_sha256"] != baseline["instruction_sha256"]
    assert sha256(request(with_reading()).instruction.encode()).hexdigest() == instruction_changed["instruction_sha256"]
    fields = model._SOURCE_OWNED_RESPONSE_SCHEMA["properties"]["draft"]["properties"]["claims"]["items"]["properties"]
    monkeypatch.setitem(fields["text"], "maxLength", 279)
    schema_changed = model.reading_model_boundary_identity(V2)
    assert schema_changed["response_schema_sha256"] != baseline["response_schema_sha256"]
    assert json.loads(request(with_reading()).data_json)["response_schema"]["properties"]["draft"]["properties"]["claims"]["items"]["properties"]["text"]["maxLength"] == 279


def test_decoder_identity_is_line_ending_and_path_independent_but_code_sensitive(tmp_path, monkeypatch):
    baseline = model.reading_model_boundary_identity(V2)
    original = Path(model.__file__).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    alternate = tmp_path / "another-install.py"
    alternate.write_bytes(original.replace(b"\n", b"\r\n"))
    monkeypatch.setattr(model, "__file__", str(alternate))
    assert model.reading_model_boundary_identity(V2) == baseline
    alternate.write_bytes(original + b"# decoder changed\n")
    assert model.reading_model_boundary_identity(V2)["decoder_sha256"] != baseline["decoder_sha256"]


@pytest.mark.parametrize("version", [None, V1])
def test_legacy_decoder_retains_its_historical_header_validation(version):
    selected = with_reading()
    payload = {"draft": {"source_id": "wrong", "source_sha256": "f"*64,
        "language": "en", "claims": [claim()]}}
    reply = model.NarrativeModelResponse("fixture", "model", "1.7.0", canonical_json(payload).encode())
    with pytest.raises(NarrativeContractError):
        model.decode_model_draft(reply, selected=selected, reading_projection_version=version)


@pytest.mark.parametrize("raw", [b'{"draft":{"claims":[],"claims":[]}}',
                                 b'{"draft":{"claims":NaN}}', b'\xff'])
def test_v2_strict_json_errors_never_reach_claim_recovery(raw):
    selected = with_reading()
    reply = model.NarrativeModelResponse("fixture", "model", "reading-source-owned/2.0.0", raw)
    with pytest.raises(model.ModelResponseError):
        model.decode_model_draft(reply, selected=selected, reading_projection_version=V2)
