"""A child keeps the actual routed purpose even when a legacy profile ID is shared."""

import pytest

from company_wiki.document_understanding import understand_units
from company_wiki.document_understanding.profiles import route_document
from fixtures.document_understanding_profiles.builders import observation, unit
from unit.document_understanding_profiles.wire_contract import assert_route_shape


def attached_interim():
    return [
        unit("container", 0, "FORM 6-K", kind="heading", page=1),
        unit("exhibit", 1, "Exhibit 99.1 Interim Report 2026", kind="heading", page=2),
        unit("review", 2, "管理層討論與分析", kind="heading", page=2),
        unit("business", 3, "Our company launched a new product for overseas customers.", page=2),
    ]


def test_actual_child_route_carries_interim_family_market_and_unknown_form():
    routed = route_document(observation(attached_interim(), title="FORM 6-K", form_type="6-K", regime="sec"))
    assert_route_shape(routed)
    child = next(row for row in routed["child_routes"] if row["reason"] == "IN_DOCUMENT_ATTACHMENT_RANGE")
    assert {"family", "regime", "form_type", "subtype"} <= child.keys()
    assert child["profile_id"] == "hk_periodic"
    assert child.get("family") == "interim", "the shared profile ID must not erase the actual child purpose"
    assert child.get("regime") == "hkex"
    assert child.get("form_type") == "unknown", "the parent 6-K is not the attachment's form"


def test_real_pipeline_selects_hk_interim_policy_for_the_read_child_and_keeps_resolved_map():
    from company_wiki.source_catalog.narrative_evidence import _make_unit
    from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

    sid = source_id_for_sha256("a" * 64)
    native = [_make_unit(source_id=sid, parser_version="1.0.0",
        coordinates=EvidenceCoordinates(page_number=row["page"], paragraph_index=row["ordinal"]),
        raw_text=row["text"], unit_kind="html_heading" if row["kind"] == "heading" else "html_paragraph",
        source_role="company_filing", language="en", metadata={}) for row in attached_interim()]
    pipeline = understand_units(native, source_id=sid, source_sha256="a" * 64,
        title="FORM 6-K", declared_kind="unknown", language="en", metadata={"regime": "sec", "form_type": "6-K"})
    child = next(row for row in pipeline["route"]["child_routes"] if row["reason"] == "IN_DOCUMENT_ATTACHMENT_RANGE")
    key = child["reading_profile_key"]
    view = pipeline["reading_plan"]["unit_profiles"][native[3].unit_id]
    assert view["family"] == "interim"
    assert view["family_policy"]["id"] == "hk_interim_report"
    assert pipeline["child_profiles"][key]["family"] == "interim"
    assert pipeline["child_profiles"][key]["regime"] == "hkex"
    assert pipeline["reading_plan"]["unit_profiles"][native[0].unit_id]["family"] == pipeline["profile"]["family"]


@pytest.mark.parametrize("form,family", [("10-Q", "quarterly"), ("20-F", "annual"), ("F-1", "prospectus")])
def test_observed_sec_child_form_is_preserved_without_borrowing_container_identity(form, family):
    units = [unit("parent", 0, "FORM 8-K", kind="heading", page=1),
        unit("exhibit", 1, "Exhibit 99.1", kind="heading", page=2),
        unit("form", 2, "FORM " + form, kind="heading", page=2),
        unit("business", 3, "Our company launched a new product for customers.", page=2)]
    routed = route_document(observation(units, title="FORM 8-K", form_type="8-K", regime="sec"))
    child = next(row for row in routed["child_routes"] if row["reason"] == "IN_DOCUMENT_ATTACHMENT_RANGE")
    assert child.get("family") == family
    assert child.get("regime") == "sec"
    assert child.get("form_type") == form


def test_unread_external_attachment_does_not_gain_resolved_child_policy_fields():
    routed = route_document(observation([unit("link", 0,
        "Exhibit 99.1 https://example.invalid/interim-report.pdf", kind="reference", page=1)]))
    assert all("family" not in child and "regime" not in child for child in routed["child_routes"])


def test_child_form_is_actual_signal_data_and_does_not_depend_on_diagnostic_wording(monkeypatch):
    from company_wiki.document_understanding.profiles import child_ranges, signals

    original_add = signals.SignalBag.add
    original_detect = child_ranges.detect_signals
    child_probes = []

    def changed_diagnostic(bag, bucket, code, unit_ids, detail, **fields):
        if detail.startswith("SEC 表单"):
            detail = "Display wording changed; source evidence is unchanged."
        return original_add(bag, bucket, code, unit_ids, detail, **fields)

    def observed_child_probe(parsed):
        bag = original_detect(parsed)
        child_probes.append(bag)
        return bag

    monkeypatch.setattr(signals.SignalBag, "add", changed_diagnostic)
    monkeypatch.setattr(child_ranges, "detect_signals", observed_child_probe)
    units = [unit("parent", 0, "FORM 8-K", kind="heading", page=1),
        unit("exhibit", 1, "Exhibit 99.1", kind="heading", page=2),
        unit("form", 2, "FORM 10-Q", kind="heading", page=2),
        unit("business", 3, "Our company launched a new product for customers.", page=2)]
    routed = route_document(observation(units, title="FORM 8-K", form_type="8-K", regime="sec"))
    child = next(row for row in routed["child_routes"] if row["reason"] == "IN_DOCUMENT_ATTACHMENT_RANGE")
    assert len(child_probes) == 1, "child form must reuse the existing source signal pass"
    assert any(getattr(signal, "form_type", None) == "10-Q" for signal in child_probes[0].all)
    assert (child["family"], child["regime"], child["form_type"]) == ("quarterly", "sec", "10-Q")
