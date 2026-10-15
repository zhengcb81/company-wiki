"""Reviewed source anchors belong to this claim's support, never the whole input.

These are source-quote observations with explicit human-reviewed fact mappings.
They do not assert that lexical matching proves arbitrary summary entailment.
"""
from copy import deepcopy
import gzip
from hashlib import sha256
import json
from pathlib import Path
import socket

import pytest

from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model import (
    NarrativeModelRequest, NarrativeModelResponse, decode_model_draft,
)
from tools.document_understanding_benchmark.closed_group_support import score_claim_facts
from unit.document_understanding_selection.test_closed_group_support import (
    SOURCE, context, fact, span,
)


FIXTURES = Path(__file__).parents[1] / "fixtures/narrative_claim_grounding"


@pytest.fixture(autouse=True)
def zero_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("grounding observations must not access the network")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.fixture(scope="module")
def real_case():
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    data = (FIXTURES / manifest["fixture"]).read_bytes()
    assert sha256(data).hexdigest() == manifest["sha256"]
    value = json.loads(gzip.decompress(data))
    assert sha256(value["response_utf8"].encode()).hexdigest() == manifest["frozen_paid_response_sha256"]
    return value


def claim(rows, *, name="one", context_rows=()):
    return {"claim_id": name, "evidence_ids": [row.span_id for row in rows],
            "context_evidence_ids": [row.span_id for row in context_rows]}


def observe(rows, claims, checks, ctx=None):
    return score_claim_facts(checks, claims=claims, evidence_spans=rows,
                             reading_context=ctx, source_id=SOURCE)


def check(quote, *, name="one", **kwargs):
    return {**fact(quote, **kwargs), "claim_id": name}


def test_real_paid_response_replays_through_the_actual_decoder(real_case):
    selected = NarrativeSelectResult.from_dict(real_case["selected"])
    request = NarrativeModelRequest.from_selection(selected, reading_projection_version="reading-model-input/3").with_output_budget(8192)
    assert request.data_json == real_case["request"]["data_json"]
    assert request.instruction == real_case["request"]["instruction"]
    response = NarrativeModelResponse("saved-paid-final", "mimo-v2.6-flash", request.prompt_version,
                                      real_case["response_utf8"].encode())
    draft = decode_model_draft(response, selected=selected, reading_projection_version="reading-model-input/3")
    assert draft == real_case["expected_public_draft"]
    assert len(draft["claims"]) == 20
    # The old mechanical boundary accepts these: the new observation must not
    # rewrite this historical receipt or invent a passing semantic judgment.
    assert all(not row["needs_review"] for row in draft["claims"])
    observations = score_claim_facts(real_case["reviewed_fact_checks"], claims=draft["claims"],
        evidence_spans=selected.evidence_spans, reading_context=selected.reading_context,
        source_id=selected.source_ref.source_id)
    assert [row["claim_id"] for row in observations] == ["c1", "c10", "c11", "c12", "c13", "c14"]
    assert all(not row["supported"] for row in observations)
    assert all(row["selected_source_support_present"] for row in observations)
    assert all(row["scope"] == "reviewed_anchors_in_claim_support" for row in observations)


def test_other_claim_and_uncited_selected_text_cannot_lend_support():
    rows = [span("Device A is in customer validation.", 0, language="en"),
            span("Device B has reached volume production.", 1, language="en")]
    checks = [check(rows[1].raw_text)]
    before = deepcopy(checks)
    result = observe(rows, [claim([rows[0]]), claim([rows[1]], name="other")], checks)
    assert not result[0]["supported"] and result[0]["selected_source_support_present"]
    assert checks == before


def test_qa_question_in_context_is_not_the_answer_factual_support():
    rows = [span("Will revenue reach USD 5 billion?", 0, role="investor_question", language="en"),
            span("We have not provided a revenue target.", 1, role="management", language="en")]
    question = check(rows[0].raw_text, role="company_filing")
    result = observe(rows, [claim([rows[1]], context_rows=[rows[0]])], [question])
    # The business-fact oracle also correctly refuses the investor's question
    # as a company assertion even when observing the entire selected input.
    assert not result[0]["supported"] and not result[0]["selected_source_support_present"]


def test_filing_context_cannot_lend_a_number_even_when_source_role_is_eligible():
    rows = [span("2025年新门店为200家。", 0), span("另一业务仍在验证阶段。", 1)]
    result = observe(rows, [claim(rows[1:], context_rows=rows[:1])], [check(rows[0].raw_text)])
    assert not result[0]["supported"] and result[0]["selected_source_support_present"]


def test_multiple_actually_cited_units_can_supply_explicit_reviewed_and_anchors():
    rows = [span("公司新系列名为星云设备。", 0), span("该系列尚未投产。", 1)]
    checks = [check(rows[0].raw_text, extra=({"page": 3, "exact_quote": rows[1].raw_text},))]
    ctx = context(rows, kind="background", groups=[[row] for row in rows])
    assert observe(rows, [claim(rows)], checks, ctx)[0]["supported"]
    assert not observe(rows, [claim(rows[:1])], checks, ctx)[0]["supported"]


@pytest.mark.parametrize("quote", ["2024年收入为5亿元。", "2025年收入为5亿美元。", "该设备已经量产。"])
def test_same_number_different_period_currency_or_negation_is_not_proof(quote):
    rows = [span("2025年收入为5亿元。该设备尚未量产。", 0)]
    assert not observe(rows, [claim(rows)], [check(quote)])[0]["supported"]


def test_source_page_and_speaker_constraints_survive_claim_filtering():
    rows = [span("公司新系列已经量产。", 0, role="management")]
    assert not observe(rows, [claim(rows)], [check(rows[0].raw_text, role="company_filing")])[0]["supported"]
    assert not observe(rows, [claim(rows)], [check(rows[0].raw_text, page=4, role="management")])[0]["supported"]
    assert observe(rows, [claim(rows)], [check(rows[0].raw_text, role="management")])[0]["supported"]


def test_native_quote_continuity_needs_a_whole_actually_cited_native_window():
    rows = [span("公司新产品进入客户生产验", 0, reason="reading_plan"),
            span("证，尚未量产。", 1)]
    checks = [check("公司新产品进入客户生产验证，尚未量产。")]
    ctx = context(rows)
    assert observe(rows, [claim(rows)], checks, ctx)[0]["supported"]
    assert not observe(rows, [claim(rows[:1], context_rows=rows[1:])], checks, ctx)[0]["supported"]


def test_reviewed_anchor_observation_explicitly_is_not_free_text_entailment():
    rows = [span("设备尚未量产。", 0)]
    raw_claim = {**claim(rows), "text": "设备已经量产。"}
    # This deliberately mismatched reviewer mapping is a negative control.
    # Finding its source quote proves presence, not that claim.text entails it.
    result = observe(rows, [raw_claim], [check(rows[0].raw_text)])[0]
    assert result["supported"] is True
    assert result["scope"] == "reviewed_anchors_in_claim_support"


@pytest.mark.parametrize("bad", ["unknown_claim", "duplicate_claim", "unknown_evidence", "duplicate_evidence", "overlap_context"])
def test_malformed_review_inputs_are_not_silently_scored_as_pass(bad):
    rows = [span("公司新系列已经量产。", 0)]
    claims, checks = [claim(rows)], [check(rows[0].raw_text)]
    if bad == "unknown_claim":
        checks[0]["claim_id"] = "absent"
    elif bad == "duplicate_claim":
        claims.append(deepcopy(claims[0]))
    elif bad == "unknown_evidence":
        claims[0]["evidence_ids"] = ["not-in-pinned-selection"]
    elif bad == "duplicate_evidence":
        claims[0]["evidence_ids"] *= 2
    else:
        claims[0]["context_evidence_ids"] = claims[0]["evidence_ids"][:]
    with pytest.raises(ValueError):
        observe(rows, claims, checks)
