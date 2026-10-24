"""Independent component review; no paid calls or full-corpus acceptance."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import runpy

import pytest

from company_wiki.document_understanding.profiles import get_profile, resolve_reading_profile
from company_wiki.document_understanding.profiles import registry
from company_wiki.document_understanding.strategy_binding import _match_rule


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
FAMILIES = ROOT / "docs/plans/document-understanding-2026-10-13/review/deliverables/families"
PLAN = ROOT / "docs/plans/du11-source-closure-2026-10-18/review/market-family-upgrade-20261024"


def resolved(pid, family, regime, form=None):
    obs = {"schema_version": "du-input/1", "source_ref": {"source_id": "original", "source_sha256": "a" * 64},
        "metadata": {"regime": regime, "form_type": form}, "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []}, "units": []}
    return resolve_reading_profile(get_profile(pid), obs, {"family": family, "regime": regime, "form_type": form})


@pytest.mark.parametrize("parent,child,expected", (
    ("Item 3. Key Information", "D. Risk Factors", "risk"),
    ("Item 3 Key Information", "D. Risk Factors", "risk"),
    ("Item 30. Key Information", "D. Risk Factors", None),
    ("Item 3. Directors", "D. Risk Factors", None),
    ("Item 6. Directors, Senior Management and Employees", "D. Risk Factors", None),
    ("Item 4. Information on the Company", "C. Organizational Structure", None),
))
def test_exact_scoped_20f_path_and_number_title_counterexamples(parent, child, expected):
    p = resolved("sec_20f", "annual", "sec", "20-F")
    rule = _match_rule("b", p, {"a": None, "b": "a"}, {"a": parent, "b": child}, [])
    assert (rule["role"] if rule else None) == expected


def test_compiler_matches_all_runtime_records_and_only_intended_family_specs_changed():
    compiler = runpy.run_path(str(ROOT / "tools/import_reading_policies.py"))["compile_catalog"]
    compiled = compiler(ROOT)
    runtime = json.loads((ROOT / "src/company_wiki/document_understanding/profiles/reading_catalog.json").read_text(encoding="utf-8"))
    assert compiled == runtime
    assert {f["id"] for f in compiled["families"]} == {json.loads((FAMILIES / name).read_text(encoding="utf-8"))["id"] for name in json.loads((FAMILIES / "index.json").read_text(encoding="utf-8"))["records"]}
    assert len(compiled["families"]) == 24 and len(compiled["facets"]) == 14


@pytest.mark.parametrize("regime,heading,expected", (
    ("hkex", "我們的市場機會", "industry"),
    ("hkex", "募集資金用途", "fundraising"),
    ("hkex", "我們的業務", "business"),
    ("cn_exchange", "第六节 业务与技术", "business"),
    ("cn_exchange", "我們的市場機會", None),
))
def test_ipo_real_title_variants_and_cross_market_scope(regime, heading, expected):
    p = resolved("prospectus", "prospectus", regime)
    rule = _match_rule("root", p, {"root": None}, {"root": heading}, [])
    assert (rule["role"] if rule else None) == expected


@pytest.mark.parametrize("regime,heading", (("hkex", "我們的業務"), ("cn_exchange", "第六节 业务与技术")))
def test_ipo_native_heading_body_reaches_actual_shared_reading_plan(regime, heading):
    from company_wiki.document_understanding import understand_units
    from company_wiki.source_catalog.narrative_evidence import _make_unit
    from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

    # This tests native-unit binding through the real pipeline; it does not
    # claim PDF extraction or whole-document business recall acceptance.
    sid = source_id_for_sha256("a" * 64)
    cover = "全球發售 招股章程" if regime == "hkex" else "首次公开发行股票并上市招股说明书"
    texts = ((cover, 1), (heading, 1), ("公司为客户提供软件服务，通过经销渠道销售产品。", None))
    units = [_make_unit(source_id=sid, parser_version="1.0.0",
        coordinates=EvidenceCoordinates(paragraph_index=i), raw_text=text,
        unit_kind="html_heading" if level else "html_paragraph", source_role="company_filing", language="zh",
        metadata={"heading_level": level, "tag_name": "h1"} if level else {})
        for i, (text, level) in enumerate(texts)]
    observed = understand_units(units, source_id=sid, source_sha256="a" * 64,
        title="招股說明書 PROSPECTUS", declared_kind="prospectus", mime_type="text/html", language="zh", metadata={"regime": regime})
    body = observed["reading_plan"]["unit_profiles"][units[-1].unit_id]
    assert body["section_role"] == "business"
    assert body["matched_section_rule"] is not None
    assert body["family_policy"]["id"] == ("prospectus_hk" if regime == "hkex" else "prospectus_cn")


def test_old_case_bytes_preserved_and_active_case_quotes_both_original_qualifiers():
    receipt = json.loads((PLAN / "case-revision.json").read_text(encoding="utf-8"))
    old_path = FAMILIES / "cases/case-earnings-call-roles-01.json"
    new_path = FAMILIES / "cases/case-earnings-call-roles-02.json"
    assert sha256(old_path.read_bytes()).hexdigest() == receipt["old_case_sha256"]
    assert sha256(new_path.read_bytes()).hexdigest() == receipt["new_case_sha256"]
    prior_review = json.loads((PLAN / "independent-policy-review/report.json").read_text(encoding="utf-8"))
    old_key = str(old_path.relative_to(ROOT)).replace("\\", "/")
    assert sha256(old_path.read_bytes()).hexdigest() == prior_review["source_snapshot_sha256"][old_key]
    case = json.loads(new_path.read_text(encoding="utf-8"))
    raw = (ROOT / "companies/Microsoft/raw/transcripts/MSFT_Q4_2026_earnings_call.txt").read_bytes()
    assert sha256(raw).hexdigest() == case["source"]["source_sha256"]
    lines = raw.decode("utf-8").splitlines()
    for unit_id, line_number in (("u5", 130), ("u3", 132)):
        unit = next(u for u in case["observation"]["units"] if u["unit_id"] == unit_id)
        assert unit["anchor"]["exact_quote"] in lines[line_number - 1]
    expectation = next(f for f in case["expectations"]["facts"] if f["id"] == "f2-global-qualifier-follows-local-facts")
    assert expectation["any_support_sets"] == [["u5", "u3"]]
    index = json.loads((FAMILIES / "index.json").read_text(encoding="utf-8"))
    coverage = next(c for c in index["coverage"] if c["shape"] == "earnings_call_transcript")
    assert coverage["case_ids"] == [receipt["active_case_id"]]
    family = next(f for f in registry._CATALOG["families"] if f["id"] == "earnings_call_transcript")
    assert family["case_ids"] == [receipt["active_case_id"]]
    assert family["evidence_status"]["real_samples"] == [receipt["active_case_id"]]


def test_actual_scoped_request_carries_conditional_policy_keeps_source_and_invalidates_input(monkeypatch):
    from company_wiki.automation.narrative_contracts import NarrativeSelectResult
    from company_wiki.automation.narrative_model_scoped import build_scoped_request
    from unit.test_narrative_reading_transport import with_reading

    wire = with_reading().to_dict()
    keys = wire["reading_context"]["reading_policies"][0].keys()
    current = resolved("earnings_call", "earnings_call", "unknown")
    wire["reading_context"]["reading_policies"] = [{key: current[key] for key in keys}]
    before = deepcopy(wire)
    selected = NarrativeSelectResult.from_dict(wire)
    request = build_scoped_request(selected)
    envelope = json.loads(request.data_json)
    policy = envelope["reading_strategy"]["reading_policies"][0]
    assert any("reported/constant currency" in q and "两者相同时" in q for q in policy["reading_questions"])
    assert wire == before and selected.to_dict() == before

    def text_values(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "text" and isinstance(child, str):
                    yield child
                yield from text_values(child)
        elif isinstance(value, list):
            for child in value:
                yield from text_values(child)
    assert set(text_values(envelope["material"])) <= {span.raw_text for span in selected.evidence_spans}
    assert list(text_values(envelope["material"]))
    oldish = deepcopy(registry._CATALOG)
    record = next(f for f in oldish["families"] if f["id"] == "earnings_call_transcript")
    record["reading_questions"] = [q for q in record["reading_questions"] if "reported/constant currency" not in q]
    monkeypatch.setattr(registry, "_CATALOG", oldish)
    changed = resolved("earnings_call", "earnings_call", "unknown")
    assert changed["profile_version"] != current["profile_version"]
    alternate = deepcopy(wire)
    alternate["reading_context"]["reading_policies"] = [{key: changed[key] for key in keys}]
    alternate_request = build_scoped_request(NarrativeSelectResult.from_dict(alternate))
    assert alternate_request.input_sha256 != request.input_sha256
    assert json.loads(alternate_request.data_json)["material"] == envelope["material"]


@pytest.mark.parametrize("changed_family,expected", (("hk_interim_report", "changed"), ("prospectus_us", "same"), ("prospectus_hk", "same"), ("prospectus_cn", "same")))
def test_complete_actual_manifest_depends_only_on_relevant_profile_content(monkeypatch, changed_family, expected):
    from company_wiki.document_normalization import normalize_document
    from company_wiki.document_understanding import understand_units, decision_inventory
    from company_wiki.document_understanding.decision_dependencies import freeze_decision_dependencies, compare_decision_dependencies

    raw = b"<h1>INTERIM REPORT 2026</h1><h2>Business Review</h2><p>Our company launched a new customer software platform.</p>"
    digest = sha256(raw).hexdigest()
    sid = "urn:company-wiki:source:sha256:" + digest
    normalized = normalize_document(raw, source_id=sid, source_sha256=digest, mime_type="text/html")
    observed = understand_units(normalized.structure.units, source_id=sid, source_sha256=digest, title="INTERIM REPORT 2026",
        declared_kind="semi_annual_report", language="en", mime_type="text/html", metadata={"regime": "hkex"})
    trace = decision_inventory.build_decision_trace(observed)
    frozen = freeze_decision_dependencies(trace)
    assert frozen["status"] == "complete"
    assert compare_decision_dependencies(frozen, decision_inventory.current_decision_trace(trace))["status"] == "same"
    catalog = deepcopy(registry._CATALOG)
    record = next(f for f in catalog["families"] if f["id"] == changed_family)
    record["reading_questions"].append("Independent policy content-only change, same declared version.")
    monkeypatch.setattr(registry, "_CATALOG", catalog)
    assert compare_decision_dependencies(frozen, decision_inventory.current_decision_trace(trace))["status"] == expected
