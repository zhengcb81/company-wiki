"""Generic network/mode/stock reading, not a company or golden-quote patch."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from company_wiki.document_understanding import understand_units  # noqa: E402
from company_wiki.document_understanding.profiles import registry  # noqa: E402
from company_wiki.source_catalog.narrative_business_policy import detect_business_fact, detect_reading_business_fact  # noqa: E402
from company_wiki.source_catalog.narrative_document import DocumentStructure  # noqa: E402
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence  # noqa: E402
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256  # noqa: E402


def unit(text, index=0, *, heading=None):
    return _make_unit(source_id=source_id_for_sha256("e" * 64), parser_version="1.0.0",
        coordinates=EvidenceCoordinates(paragraph_index=index), raw_text=text,
        unit_kind="html_heading" if heading else "html_paragraph", source_role="company_filing", language="en",
        metadata={"tag_name": f"h{heading}", "heading_level": heading} if heading else {})


@pytest.mark.parametrize("text", [
    "As of March 31, 2026, we operated a network of 820 stores, including 600 domestic stores and 220 overseas stores.",
    "Our network comprised a total of 540 outlets at the end of the reporting period.",
    "截至2026年3月31日，我们共有820家门店，其中600家位于境内，220家位于海外。",
    "截至2026年3月31日，我們共有820家門店，其中600家位於境內，220家位於海外。",
    "At period end, our store network consisted of 315 branches serving local consumers.",
])
def test_stock_relations_are_operating_facts_without_inventing_period_increments(text):
    fact = detect_reading_business_fact(text)
    assert fact.eligible
    assert "store_network_stock" in fact.reasons
    assert "store_network_progress" not in fact.reasons


@pytest.mark.parametrize("text", [
    "We serve consumers through directly operated stores and retail partners, while distributors operate our overseas stores.",
    "Our stores operate under direct-operation, retail-partner and distributor models.",
    "我们通过直营店、合伙人门店和代理门店为消费者提供服务。",
    "我們通過直營店、合夥人門店和代理門店為消費者提供服務。",
    "Our outlets are operated by franchisees rather than by the company itself.",
])
def test_operating_modes_are_meaningful_without_any_numeric_metric(text):
    fact = detect_reading_business_fact(text)
    assert fact.eligible and "store_operating_model" in fact.reasons


@pytest.mark.parametrize("text", [
    "We expanded our store network into additional overseas markets during the reporting period.",
    "We plan to open stores in new overseas markets next year.",
    "我们已拓展海外门店网络，并计划进入新的区域。",
    "我們已拓展海外門店網絡，並計劃進入新的區域。",
    "Our outlet network contracted after we closed locations that failed to meet customer demand.",
])
def test_network_activity_preserves_plans_negation_and_observed_progress(text):
    fact = detect_reading_business_fact(text)
    assert fact.eligible and "store_network_progress" in fact.reasons
    native = unit(text)
    document = DocumentStructure(native.source_id, "e" * 64, "en", (native,), mime_type="text/html")
    selected = select_narrative_evidence(document, title="Company update", existing_kind="unknown",
        selector_version="0.9.0", max_selected=4)
    assert [span.raw_text for span in selected.evidence_spans] == [text]


@pytest.mark.parametrize("text", [
    "As of March 31, 2026, we served consumers through\na network of 820 stores in domestic and overseas markets.",
    "截至2026年3月31日，我們共有820家門\n店，通過直營及合夥人模式服務消費者。",
])
def test_native_line_wrapping_does_not_destroy_stock_and_mode_relationships(text):
    assert detect_reading_business_fact(text).eligible


@pytest.mark.parametrize("text", [
    "Revenue increased 12% and net income increased 8%; total assets were $900 million.",
    "Our treasury stock consisted of 820 ordinary shares at the end of the reporting period.",
    "Cash flows from operations were $500 million; stores are listed in an unrelated glossary.",
    "Store Network",
    "Directly operated stores",
    "A store network is defined as a collection of retail locations, without company operating information.",
    "Revenue was 100 million in prior years. Retail partner models appear only as glossary headings.",
    "Our store lease contracts carry financial liability balances.",
    "Our store network generated revenue of $900 million during the year.",
    "公司拥有营业收入100万元，门店名称仅在术语表列示。",
    "Store rent reimbursements paid by distributors were included in cash flow.",
    "We closed the cash account used for our stores; there was no change to our retail network.",
    "Our outlets serve enterprise buyers.",
    "Our stores are closer to local consumers.",
])
def test_financial_totals_glossary_and_unrelated_network_nouns_are_not_facts(text):
    assert not detect_reading_business_fact(text).eligible


def table_signal(text):
    value = getattr(registry, "configured_table_signal", None)
    assert callable(value), "new table triage must use the one installed reading catalog"
    return value(text)


@pytest.mark.parametrize("text", [
    "Number of stores | As of March 31 | 2025 | 2026\nDirectly operated stores | 40 | 52\nRetail partner stores | 110 | 120",
    "門店數量 | 截至3月31日 | 2025年 | 2026年\n直營店 | 40 | 52\n合夥人門店 | 110 | 120",
    "门店数量 | 截至3月31日 | 2025年 | 2026年\n直营店 | 40 | 52\n代理门店 | 110 | 120",
    "Production capacity | designed capacity | actual output | utilization rate | reporting period",
])
def test_real_operating_table_signals_trigger_possible_table_reading(text):
    assert table_signal(text) is True


def test_traditional_table_label_keeps_its_meaning_across_native_line_wrap():
    assert table_signal("門\n店數量 | 2025年 | 2026年\n直營店 | 40 | 52") is True


@pytest.mark.parametrize("text", [
    "Total revenue | net income | total assets | cash flow\n2025 | 2026\n100 | 120 | 300 | 20",
    "营业收入 | 净利润 | 资产总额 | 占比\n2025年 | 2026年\n100 | 120 | 300 | 20",
    "海外收入 | 中国内地收入 | 分地区 | 占比\n100 | 200 | 33%",
    "全球發售所得款項、收入、資產、利潤及普通股金額列示於歷史財務報表。",
    "Business outlook and general company philosophy, no operating table information.",
])
def test_empty_financial_amount_tables_and_weak_region_words_do_not_trigger_scan(text):
    assert table_signal(text) is False


def test_table_scan_is_the_configured_row_evidence_not_a_second_literal_registry(monkeypatch):
    catalog = deepcopy(registry._CATALOG)
    target = next(e for f in catalog["facets"] for e in f["positive_evidence"]
                  if "pdf_table_row" in e["unit_kinds"])
    target["signals"] = ["new-configured-operating-row"]
    target["table_scan"] = True
    monkeypatch.setattr(registry, "_CATALOG", catalog)
    assert table_signal("new-configured-operating-row | period | units") is True
    target["table_scan"] = False
    assert table_signal("new-configured-operating-row | period | units") is False


@pytest.mark.parametrize("flag", ["true", 1, None])
def test_table_scan_flag_is_boolean_configuration_not_truthy_permission(flag, monkeypatch):
    catalog = deepcopy(registry._CATALOG)
    target = next(e for f in catalog["facets"] for e in f["positive_evidence"]
                  if "pdf_table_row" in e["unit_kinds"])
    target["table_scan"] = flag
    monkeypatch.setattr(registry, "_CATALOG", catalog)
    with pytest.raises((TypeError, ValueError), match="table_scan"):
        table_signal("ordinary page")


@pytest.mark.parametrize("flag", ["true", 1, None])
def test_catalog_compiler_rejects_the_same_invalid_table_scan_types(flag, monkeypatch):
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("owned_reading_compiler", ROOT / "tools/import_reading_policies.py")
    assert spec and spec.loader
    compiler = module_from_spec(spec)
    spec.loader.exec_module(compiler)
    original = compiler._records

    def records(package, schema):
        rows, coverage = original(package, schema)
        if schema == "du2-facet-spec/1":
            rows[0]["positive_evidence"][0]["table_scan"] = flag
        return rows, coverage

    monkeypatch.setattr(compiler, "_records", records)
    with pytest.raises(ValueError, match="table_scan"):
        compiler.compile_catalog(ROOT)


def test_legacy_catalog_without_scan_flags_remains_valid_and_prose_is_not_a_fake_row(monkeypatch):
    catalog = deepcopy(registry._CATALOG)
    for facet in catalog["facets"]:
        for entry in facet["positive_evidence"]:
            entry.pop("table_scan", None)
    target = next(e for f in catalog["facets"] for e in f["positive_evidence"]
                  if "pdf_table_row" not in e["unit_kinds"])
    target["signals"] = ["source-descriptive-prose-only"]
    target["table_scan"] = True
    monkeypatch.setattr(registry, "_CATALOG", catalog)
    assert table_signal("source-descriptive-prose-only") is False


def test_table_scan_query_does_not_reopen_catalog_or_original_files(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("table query performed IO")

    with monkeypatch.context() as patch:
        patch.setattr(registry, "files", forbidden)
        patch.setattr(Path, "read_text", forbidden)
        patch.setattr(Path, "read_bytes", forbidden)
        assert table_signal("門店數量 | period | unit") is True


@pytest.mark.parametrize("cover,family", [("ANNUAL REPORT 2026", "annual"), ("INTERIM REPORT 2026", "interim")])
@pytest.mark.parametrize("heading", ["Business Review and Outlook", "業務回顧及展望", "业务回顾及展望"])
def test_actual_hk_business_heading_binds_at_its_real_single_level(cover, family, heading):
    units = (unit(cover, 0, heading=1), unit(heading, 1, heading=1),
             unit("Our outlets serve consumers through retail partners.", 2))
    pipeline = understand_units(units, source_id=units[0].source_id, source_sha256="e" * 64,
        mime_type="text/html", metadata={"regime": "hkex"})
    assert pipeline["route"]["family"] == family
    assert pipeline["reading_plan"]["unit_profiles"][units[2].unit_id]["section_role"] == "business"
    assert pipeline["reading_plan"]["unit_profiles"][units[2].unit_id]["priority"] == 1


def test_table_scan_mutation_invalidates_unused_facet_matcher_dependencies(monkeypatch):
    from company_wiki.document_understanding.decision_inventory import build_decision_trace, current_decision_trace

    units = (unit("ANNUAL REPORT 2026", 0, heading=1), unit("Our network serves consumers.", 1))
    pipeline = understand_units(units, source_id=units[0].source_id, source_sha256="e" * 64,
        mime_type="text/html", metadata={"regime": "hkex"})
    before = build_decision_trace(pipeline, used_facet_ids=())
    catalog = deepcopy(registry._CATALOG)
    targets = [e for f in catalog["facets"] for e in f["positive_evidence"]
               if "pdf_table_row" in e["unit_kinds"] and e.get("table_scan") is True]
    assert targets, "actual catalog must declare the strong row signals used for table scanning"
    target = targets[0]
    target["table_scan"] = False
    monkeypatch.setattr(registry, "_CATALOG", catalog)
    assert current_decision_trace(before) != before


def test_original_header_period_and_mode_text_are_preserved_in_one_complete_table_package():
    # Existing source table normalization, not a synthetic table-shaped page.
    from company_wiki.document_normalization import normalize_document

    html = b'<h1>ANNUAL REPORT 2026</h1><h2>Business Review and Outlook</h2><h3>Store Network</h3><table><tr><th>Number of stores</th><th>As of March 31, 2025</th><th>As of March 31, 2026</th></tr><tr><td>Directly operated stores</td><td>40</td><td>52</td></tr><tr><td>Retail partner stores</td><td>110</td><td>120</td></tr></table>'
    import hashlib
    digest = hashlib.sha256(html).hexdigest()
    parsed = normalize_document(html, source_id=source_id_for_sha256(digest), source_sha256=digest,
                                mime_type="text/html").structure
    before = tuple((u.unit_id, u.raw_text, u.coordinates) for u in parsed.units)
    parsed = replace(parsed, language="en")
    result = select_narrative_evidence(parsed, title="Annual Report", existing_kind="annual_report",
                                       selector_version="0.9.0", max_selected=24)
    rows = {span.span_id: span.raw_text for span in result.evidence_spans}
    required = ("Number of stores", "As of March 31, 2025", "As of March 31, 2026",
                "Directly operated stores", "40", "52")
    assert any(all(any(text in rows[sid] for sid in group["evidence_ids"]) for text in required)
               for group in result.reading_context["groups"])
    assert tuple((u.unit_id, u.raw_text, u.coordinates) for u in parsed.units) == before


def test_opt_in_retail_relations_preserve_explicit_legacy_recognition():
    text = "Our stores operate under direct-operation, retail-partner and distributor models."
    assert not detect_business_fact(text).eligible
    assert detect_reading_business_fact(text).eligible
