"""One model citation namespace; pinned unit compilation never infers new facts."""
from base64 import b64decode
from dataclasses import asdict
import gzip
from hashlib import sha256
import json
from pathlib import Path
import re
import socket

import pytest

from company_wiki.automation import narrative_model as model
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_contracts import NarrativeContractError, NarrativeSelectResult
from company_wiki.source_contract import EvidenceSpan
from support.narrative_model_request_fixture import selection
from unit.test_narrative_reading_transport import with_reading
from unit.test_narrative_source_owned_model_boundary import official_reading, http_port
from unit.test_narrative_output_language_binding import selected_english

V3 = "reading-model-input/3"
FROZEN = Path(__file__).parents[1] / "support/reading_citation_v2_snapshots.json.gz"
FROZEN_CASES = json.loads(gzip.decompress(FROZEN.read_bytes()))["cases"]


@pytest.fixture(autouse=True)
def protected_config_and_zero_network(monkeypatch):
    project = Path(__file__).resolve().parents[2]
    paths = [project / "config.yaml", project / "config/source_catalog.yaml",
        project / "src/company_wiki/automation/narrative_model.py",
        project / "src/company_wiki/automation/narrative_model_citations.py"]
    def fingerprint(path):
        return sha256(path.read_bytes()).hexdigest(), path.stat().st_size, path.stat().st_mtime_ns
    before = {path: fingerprint(path) for path in paths}
    def forbid(*args, **kwargs):
        raise AssertionError("pure model boundary tests must not use HTTP")
    monkeypatch.setattr(socket, "create_connection", forbid)
    monkeypatch.setattr(socket.socket, "connect", forbid)
    yield
    assert before == {path: fingerprint(path) for path in paths}


def request(selected):
    return model.NarrativeModelRequest.from_selection(selected, reading_projection_version=V3)


def envelope(selected):
    return json.loads(request(selected).data_json)


def unit_for(data, *evidence):
    matches = [row[0] for row in data["citation_units"] if set(row[1]) == set(evidence)]
    assert len(matches) == 1
    return matches[0]


def claim(units, *, claim_id="one", text="公司新产品已完成海外客户认证。", kind="company_statement", modality="actual", **extra):
    return {"claim_id": claim_id, "text": text, "citation_unit_ids": units,
        "claim_type": kind, "modality": modality, **extra}


def decode(selected, claims, *, payload=None):
    reply = model.NarrativeModelResponse("offline", "configured-model", request(selected).prompt_version,
        canonical_json({"claims": claims} if payload is None else payload).encode())
    return model.decode_model_draft(reply, selected=selected, reading_projection_version=V3)


@pytest.mark.parametrize("case", FROZEN_CASES, ids=lambda case: case["case"])
def test_explicit_v2_request_and_actual_http_bytes_remain_frozen(case):
    assert sha256(FROZEN.read_bytes()).hexdigest() == "010a09825ca73c3b0ffea5f7208be7dddee76917eba3fa5f74f52d73a8b5f8a4"
    selected = NarrativeSelectResult.from_dict(case["selected"])
    actual = model.NarrativeModelRequest.from_selection(selected, reading_projection_version="reading-model-input/2")
    assert asdict(actual) == case["request"]
    assert http_port().request_bytes(actual) == b64decode(case["http_bytes"])


def test_v3_resolves_one_finite_source_owned_boundary_for_raw_and_official():
    assert model.CITATION_UNIT_READING_MODEL_PROJECTION_VERSION == V3
    raw = model.resolve_model_boundary(V3)
    assert raw == model.resolve_model_boundary(V3, projected=True)
    assert raw.source_owned and raw.request_schema == "narrative-model-request/4"
    assert raw.prompt_version != model.resolve_model_boundary("reading-model-input/2").prompt_version
    assert not model.resolve_model_boundary(None).source_owned
    assert not model.resolve_model_boundary("reading-model-input/1").source_owned


def test_actual_v3_input_has_one_unit_namespace_and_unique_original_evidence():
    selected = with_reading()
    before = selected.to_dict()
    data = envelope(selected)
    assert data["schema_version"] == "narrative-model-request/4"
    assert data["citation_unit_columns"] == ["id", "evidence_ids", "support_evidence_ids"]
    assert all(row[2] == row[1] for row in data["citation_units"])
    assert "evidence_groups" not in data and "evidence_group_columns" not in data
    assert data["evidence"] == [["e1", selected.evidence_spans[0].raw_text],
        ["e2", selected.evidence_spans[1].raw_text], ["e3", selected.evidence_spans[2].raw_text]]
    first, second = unit_for(data, "e1", "e2"), unit_for(data, "e2", "e3")
    assert [row["id"] for row in data["reading_strategy"]["groups"]] == [first, second]
    assert all(re.fullmatch(r"u_[a-f0-9]{16,64}", row[0]) for row in data["citation_units"])
    assert set(data["source"]) == {"title", "language", "document_kind"}
    schema = data["response_schema"]
    assert schema["required"] == ["claims"] and "draft" not in schema["properties"]
    fields = schema["properties"]["claims"]["items"]["properties"]
    assert set(fields) == {"claim_id", "text", "citation_unit_ids", "claim_type", "modality"}
    assert fields["citation_unit_ids"]["maxItems"] == len(data["citation_units"])
    assert selected.to_dict() == before


def test_one_explicit_unit_expands_only_its_pinned_group_not_overlap_neighbors():
    selected = with_reading()
    data = envelope(selected)
    first = unit_for(data, "e1", "e2")
    actual = decode(selected, [claim([first])])
    assert actual["claims"][0]["evidence_ids"] == [s.span_id for s in selected.evidence_spans[:2]]
    assert actual["claims"][0]["needs_review"] is False
    assert actual["status"] == "draft"
    assert set(actual["claims"][0]) == {"claim_id", "text", "evidence_ids", "claim_type", "modality", "needs_review"}


def test_two_explicit_overlapping_units_deduplicate_members_without_model_repetition():
    selected = with_reading()
    data = envelope(selected)
    ids = [row[0] for row in data["citation_units"]]
    actual = decode(selected, [claim(list(reversed(ids)))])
    assert actual["claims"][0]["evidence_ids"] == [s.span_id for s in selected.evidence_spans]
    assert actual["claims"][0]["text"] == "公司新产品已完成海外客户认证。"


def test_only_truly_ungrouped_spans_get_standalone_units():
    wire = with_reading().to_dict()
    wire["reading_context"]["groups"].pop()
    selected = NarrativeSelectResult.from_dict(wire)
    data = envelope(selected)
    assert sorted(len(row[1]) for row in data["citation_units"]) == [1, 2]
    standalone = unit_for(data, "e3")
    actual = decode(selected, [claim([standalone])])
    assert actual["claims"][0]["evidence_ids"] == [selected.evidence_spans[2].span_id]
    assert not any(row[1] == ["e1"] or row[1] == ["e2"] for row in data["citation_units"])


@pytest.mark.parametrize("bad", [[], ["e1"], ["g1"], ["u_unknown"], None, "u_wrong", [True]])
def test_missing_unknown_old_namespace_or_bad_unit_shape_rejects_whole_claim(bad):
    selected = with_reading()
    good = envelope(selected)["citation_units"][0][0]
    actual = decode(selected, [claim(bad, claim_id="bad"), claim([good], claim_id="good")])
    assert [row["claim_id"] for row in actual["claims"]] == ["good"]
    assert actual["status"] == "needs_review"
    with pytest.raises((model.ModelResponseError, NarrativeContractError)):
        decode(selected, [claim(bad)])


def test_duplicate_unit_or_dual_citation_fields_never_silently_repair():
    selected = with_reading()
    unit = envelope(selected)["citation_units"][0][0]
    for bad in (claim([unit, unit]), claim([unit], evidence_ids=["e1"]),
                claim([unit], evidence_group_ids=["g1"])):
        with pytest.raises((model.ModelResponseError, NarrativeContractError)):
            decode(selected, [bad])


def test_aliases_bind_actual_source_members_not_evidence_or_group_numbers():
    first = with_reading()
    original = envelope(first)
    wire = first.to_dict()
    wire["evidence_spans"].reverse()
    wire["reading_context"]["groups"].reverse()
    reordered = envelope(NarrativeSelectResult.from_dict(wire))
    assert {row[0] for row in reordered["citation_units"]} == {row[0] for row in original["citation_units"]}
    changed = selection(3, text_suffix="different actual source excerpt")
    changed = with_reading(changed)
    foreign = envelope(changed)["citation_units"][0][0]
    assert foreign not in {row[0] for row in original["citation_units"]}
    with pytest.raises(model.ModelResponseError):
        decode(first, [claim([foreign])])


def test_unit_aliases_do_not_depend_on_native_group_labels():
    first = with_reading()
    wire = first.to_dict()
    for index, row in enumerate(wire["reading_context"]["groups"]):
        row["group_id"] = "unrelated-sequence-label-" + str(index + 526)
    assert envelope(NarrativeSelectResult.from_dict(wire))["citation_units"] == envelope(first)["citation_units"]


def test_same_member_groups_share_one_unit_and_more_units_than_spans_is_supported():
    wire = with_reading().to_dict()
    refs = [span["span_id"] for span in wire["evidence_spans"]]
    wire["reading_context"]["groups"] = [
        {"group_id": str(index), "kind": "native_continuity", "section_role": "business",
         "evidence_ids": members}
        for index, members in enumerate(([refs[0]], [refs[1]], [refs[2]], refs[:2], refs))]
    selected = NarrativeSelectResult.from_dict(wire)
    data = envelope(selected)
    assert len(data["citation_units"]) == 5 > len(data["evidence"])
    assert data["response_schema"]["properties"]["claims"]["items"]["properties"]["citation_unit_ids"]["maxItems"] == 5
    wire["reading_context"]["groups"].append({**wire["reading_context"]["groups"][0], "group_id": "same-closure-other-group"})
    duplicated = envelope(NarrativeSelectResult.from_dict(wire))
    assert duplicated["citation_units"] == data["citation_units"]


@pytest.mark.parametrize("selected", [official_reading(), official_reading(same_groups=True)])
def test_official_projection_units_remain_bound_to_actual_original_parent_roles(selected):
    data = envelope(selected)
    company = unit_for(data, "e3")
    actual = decode(selected, [claim([company], text="The company disclosed product progress.")])
    assert actual["subject_id"] == selected.subject.item_key
    assert actual["subject_sha256"] == selected.subject.subject_sha256
    assert actual["claims"][0]["evidence_ids"] == [selected.evidence_spans[2].span_id]
    question = unit_for(data, "e1", "e2")
    with pytest.raises(NarrativeContractError, match="non-company evidence"):
        decode(selected, [claim([question])])


def test_operating_row_unit_preserves_header_unit_and_avoids_neighbor_row():
    selected = with_reading(selection(4))
    wire = selected.to_dict()
    texts = ["单位：亿元", "项目名称 | 本期投入金额 | 进展阶段", "项目甲 | 1.16 | 客户端验证", "项目乙 | 9.80 | 开发中"]
    spans = [EvidenceSpan.create(source_id=span.source_id, coordinates=span.coordinates,
        raw_text=text, structured_value=span.structured_value, parser_name=span.parser_name,
        parser_version=span.parser_version, parse_status="parsed", quality_flags=())
        for span, text in zip(selected.evidence_spans, texts, strict=True)]
    wire["evidence_spans"] = [span.to_dict() for span in spans]
    refs = [span.span_id for span in spans]
    wire["reading_context"]["groups"] = [
        {"group_id": "row-one", "kind": "operating_table", "section_role": "management_discussion", "evidence_ids": refs[:3]}]
    selected = NarrativeSelectResult.from_dict(wire)
    data = envelope(selected)
    unit = unit_for(data, "e1", "e2", "e3")
    actual = decode(selected, [claim([unit], text="项目投入1.16亿元，处于客户端验证阶段。")])
    assert actual["claims"][0]["evidence_ids"] == refs[:3]
    assert actual["claims"][0]["modality"] == "actual"
    assert refs[3] not in actual["claims"][0]["evidence_ids"]


def test_english_cited_prose_language_cannot_be_overridden_by_policy_language():
    selected = selected_english()
    data = envelope(selected)
    assert data["source"]["language"] == "en"
    assert "English" in request(selected).instruction
    assert "policy" in request(selected).instruction
    assert "Do not translate" in request(selected).instruction
    text = selected.evidence_spans[0].raw_text
    actual = decode(selected, [claim([data["citation_units"][0][0]], text=text)])
    assert actual["language"] == "en" and actual["claims"][0]["text"] == text


@pytest.mark.parametrize("condition", ["21_claims", "long_text", "translation", "old_draft", "extra_brace", "duplicate_key", "path"])
def test_v3_preserves_actual_output_limits_strict_json_and_translation_guards(condition):
    selected = with_reading()
    unit = envelope(selected)["citation_units"][0][0]
    one = claim([unit])
    claims = [one]
    if condition == "21_claims":
        claims = [{**one, "claim_id": str(n)} for n in range(21)]
    if condition == "long_text":
        claims = [{**one, "text": "x" * 281}]
    if condition == "path":
        claims = [{**one, "text": "file:///C:/secret/material.pdf"}]
    payload = {"claims": claims}
    if condition == "translation":
        payload["translate"] = True
    if condition == "old_draft":
        payload = {"draft": payload}
    body = canonical_json(payload).encode()
    if condition == "extra_brace":
        body += b"}"
    if condition == "duplicate_key":
        body = b'{"claims":[],"claims":[]}'
    response = model.NarrativeModelResponse("offline", "model", request(selected).prompt_version, body)
    with pytest.raises((model.ModelResponseError, NarrativeContractError)):
        model.decode_model_draft(response, selected=selected, reading_projection_version=V3)


def test_v3_causal_identity_and_actual_http_body_keep_caps_without_legacy_namespace():
    selected = with_reading()
    actual = request(selected)
    old = model.NarrativeModelRequest.from_selection(selected, reading_projection_version="reading-model-input/2")
    assert actual.input_sha256 != old.input_sha256
    assert actual.with_output_budget(400).input_sha256 != actual.input_sha256
    body = json.loads(http_port().request_bytes(actual))
    data = json.loads(body["messages"][1]["content"])
    assert body["max_tokens"] == 8192 and body["temperature"] == 1.0
    assert body["thinking"] == {"type": "disabled"}
    assert data["output_plan"]["configured_output_tokens"] == 8192
    assert data["response_schema"]["properties"]["claims"]["maxItems"] == 20
    identity = model.reading_model_boundary_identity(V3)
    assert identity["instruction_sha256"] == sha256(actual.instruction.encode()).hexdigest()
    assert identity["decoder_sha256"] != model.reading_model_boundary_identity("reading-model-input/2")["decoder_sha256"]


def test_actual_causal_descriptor_binds_both_decoder_and_unit_compiler_bytes():
    from company_wiki.automation import narrative_model_citations as citations
    def actual_lf_sha(module):
        data = Path(module.__file__).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        return sha256(data).hexdigest()
    expected = sha256(canonical_json({"decoder": actual_lf_sha(model), "citations": actual_lf_sha(citations)}).encode()).hexdigest()
    assert model.reading_model_boundary_identity(V3)["decoder_sha256"] == expected


def test_all_claims_use_one_immutable_unit_compilation(monkeypatch):
    selected = with_reading()
    unit = envelope(selected)["citation_units"][0][0]
    actual = model.compile_citation_units
    calls = []
    def count(*args, **kwargs):
        result = actual(*args, **kwargs)
        calls.append(result)
        return result
    monkeypatch.setattr(model, "compile_citation_units", count)
    # Build the response before counting decoder compilation; request compilation
    # is independently required when the actual input is rendered.
    reply = model.NarrativeModelResponse("offline", "model", model.resolve_model_boundary(V3).prompt_version,
        canonical_json({"claims": [claim([unit], claim_id=str(n)) for n in range(20)]}).encode())
    result = model.decode_model_draft(reply, selected=selected, reading_projection_version=V3)
    assert len(result["claims"]) == 20 and len(calls) == 1
    with pytest.raises(TypeError):
        calls[0]._members["foreign"] = ()


def test_short_alias_collision_is_typed_failure_and_never_rebinds(monkeypatch):
    from company_wiki.automation import narrative_model_citations as citations
    monkeypatch.setattr(citations, "_alias_for_members", lambda members, support: "u_collision")
    with pytest.raises(model.ModelCitationError, match="collision"):
        request(with_reading())


def test_v2_incomplete_group_still_fails_instead_of_silently_expanding():
    selected = with_reading()
    old = model.NarrativeModelRequest.from_selection(selected, reading_projection_version="reading-model-input/2")
    reply = model.NarrativeModelResponse("offline", "model", old.prompt_version, canonical_json({"draft": {"claims": [
        {"claim_id": "old", "text": "公司新产品已完成海外客户认证。", "evidence_ids": ["e1"],
         "evidence_group_ids": ["g1"], "claim_type": "company_statement", "modality": "actual"}]}}).encode())
    with pytest.raises(NarrativeContractError, match="group coverage is incomplete"):
        model.decode_model_draft(reply, selected=selected, reading_projection_version="reading-model-input/2")


def test_native_group_cannot_cross_source_parents_before_model_projection():
    selected = official_reading()
    wire = selected.to_dict()
    wire["reading_context"]["groups"][0]["evidence_ids"] = [selected.evidence_spans[0].span_id,
                                                             selected.evidence_spans[2].span_id]
    with pytest.raises(NarrativeContractError, match="parent"):
        NarrativeSelectResult.from_dict(wire)
