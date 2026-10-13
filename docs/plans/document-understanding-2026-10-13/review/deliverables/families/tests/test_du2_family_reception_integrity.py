"""ROOT reception invariants: observed semantic scope and original facts survive."""
from __future__ import annotations
import hashlib
import json
import _support as support

def test_modifier_axes_are_allowed_value_arrays():
    for record in support.load_records().values():
        modifiers = record["applies_to"]["modifiers"]
        for axis, allowed in (("extent", support.EXTENTS), ("revision", support.REVISIONS)):
            values = modifiers[axis]
            assert isinstance(values, list) and values
            assert len(values) == len(set(values)) and set(values) <= allowed

def test_periodic_profiles_do_not_exclude_summary_or_amendment_variants():
    for key in ("cn_annual_report", "cn_interim_report", "sec_10k", "sec_10q", "sec_20f"):
        modifiers = support.load_records()[key]["applies_to"]["modifiers"]
        assert {"full", "summary", "unknown"} <= set(modifiers["extent"])
        assert {"original", "amended", "supplement", "unknown"} <= set(modifiers["revision"])

def _section_for(phrase):
    return [section for section in support.load_records()["sec_10q"]["sections"]
            if any(phrase in alias for alias in section["aliases"])]

def test_controls_belongs_to_part_i_item_four():
    sections = _section_for("Controls")
    assert sections
    for section in sections:
        assert "PART I" in section["heading_path"][0]
        assert any("Item 4" in value for value in section["heading_path"][-1])

def test_legal_proceedings_belongs_to_part_ii_item_one():
    sections = _section_for("Legal Proceedings")
    assert sections
    for section in sections:
        assert "PART II" in section["heading_path"][0]
        assert any("Item 1. Legal Proceedings" in value for value in section["heading_path"][-1])
        assert not any("Item 3. Legal Proceedings" in value for level in section["heading_path"] for value in level)

def test_overlay_does_not_conjoin_extent_and_revision():
    record = support.load_records()["lifecycle_revision_overlay"]
    assert set(record["applies_to"]["modifiers"]["extent"]) == support.EXTENTS
    assert set(record["applies_to"]["modifiers"]["revision"]) == support.REVISIONS
    assert "6-K" not in record["applies_to"]["forms"]

def test_all_fact_targets_are_explicit_and_financials_are_not_mandatory():
    cases = support.load_cases()
    for case in cases.values():
        for fact in case["expectations"]["facts"]:
            assert fact.get("target_kind") in {"required_business", "disposition_context", "correctness_if_emitted"}
    financial = cases["case-cn-quarterly-sparse-02"]["expectations"]["facts"][1]
    assert financial["target_kind"] == "correctness_if_emitted"
    for key in ("case-cn-interim-stage-01", "case-cn-equity-project-phases-01", "case-hk-annual-stores-01", "case-sec-10k-rpo-02"):
        assert all(f["target_kind"] == "required_business" for f in cases[key]["expectations"]["facts"])

def test_original_fact_content_importance_and_support_are_unchanged():
    cases = support.load_cases()
    original = {key: [{k: v for k, v in fact.items() if k != "target_kind"}
                      for fact in case["expectations"]["facts"]] for key, case in cases.items()}
    digest = hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":")).encode("utf-8")).hexdigest()
    assert digest == "861dc4141511eb98d72b8d7b8e979c5245337c7cb68f52b9845f60c66704d129"

def test_quote_quota_counts_utf8_bytes_and_all_cases_on_a_source():
    function = getattr(support, "quote_bytes_per_source", None)
    assert function is not None, "8KiB is a byte limit, not a character limit"
    cases = {"one": {"source": {"source_sha256": "same"}, "case_id": "one",
                     "observation": {"units": [{"text": "汉" * 2000}]}},
             "two": {"source": {"source_sha256": "same"}, "case_id": "two",
                     "observation": {"units": [{"text": "汉" * 800}]}}}
    totals = function(cases)
    assert totals["same"] == 8400 and totals["same"] > support.QUOTE_QUOTA_BYTES

def test_real_source_count_is_not_stale_in_readme():
    cases = support.load_cases()
    count = len({c["source"]["source_sha256"] for c in cases.values() if c["kind"] == "real_excerpt"})
    text = (support.PKG_ROOT / "README.md").read_text(encoding="utf-8")
    assert f"{count} 份原件" in text
