"""Usability behavior invalidates relevant reading reuse without host paths."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from company_wiki.document_understanding import decision_inventory as inventory
from company_wiki.document_understanding.decision_dependencies import (
    compare_decision_dependencies, freeze_decision_dependencies,
)
from unit.document_understanding_selection.test_reading_decision_inventory import _real_interim_pipeline


MODULES = (
    "company_wiki.automation.narrative_select",
    "company_wiki.document_normalization.replay",
    "company_wiki.source_catalog.narrative_replay",
)


def post_parse_material(mime_type, *, normalized=False):
    """A pure parser handoff fixture; no file/media parser is called."""
    from company_wiki.source_catalog.narrative_document import DocumentStructure
    from company_wiki.source_catalog.narrative_evidence import _make_unit, TRANSCRIPT_PARSER_VERSION
    from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

    source_sha = "a" * 64
    source_id = source_id_for_sha256(source_sha)
    text = "We launched a new product and received repeat orders abroad."
    coordinates = EvidenceCoordinates(paragraph_index=1, char_start=0, char_end=len(text))
    if normalized:
        from company_wiki.document_normalization.units import build_unit
        unit = build_unit(source_id=source_id, source_sha256=source_sha, format_name="html",
            coordinates=coordinates, raw_text=text, unit_kind="html_paragraph",
            source_locator="cwp-html-dom/1|p=/html[1]/body[1]/p[1]|k=text", transform="html_text")
        unit = replace(unit, language="en")
    else:
        unit = _make_unit(source_id=source_id, parser_version=TRANSCRIPT_PARSER_VERSION,
            coordinates=coordinates, raw_text=text, unit_kind="transcript_speaker_block",
            source_role="management", language="en",
            metadata={"speaker": "Company executive", "section": "prepared_remarks"})
    return DocumentStructure(source_id, source_sha, "en", (unit,), line_count=3, mime_type=mime_type)


@pytest.mark.parametrize("mime_type", ["text/plain", "application/json", "text/html", "application/xhtml+xml"])
@pytest.mark.parametrize("forged_parser", [False, True])
def test_transcript_selected_material_uses_actual_non_normalized_matcher(monkeypatch, mime_type, forged_parser):
    """Exercise the post-parse source-owner boundary, without parsing originals."""
    from company_wiki.automation import narrative_select as select
    from company_wiki.source_catalog import narrative_replay as replay
    from company_wiki.source_catalog.narrative_document import NarrativeEvidencePackage

    parsed = post_parse_material(mime_type)
    unit = parsed.units[0]
    span = unit.to_evidence_span(topics=("new_business",), selection_reasons=("business_progress",))
    if forged_parser:
        span = replace(span, parser_version="9.9.9")
    package = NarrativeEvidencePackage(parsed.source_id, parsed.source_sha256, "investor_call_transcript",
        "selected", (span,), 96, 1, 0, 1, 0, True)
    calls = []
    actual_matcher = replay.verify_replayed_pdf_spans
    assert actual_matcher.__module__ == MODULES[2]
    assert select.verify_replayed_pdf_spans is actual_matcher

    def counted_matcher(spans, units):
        calls.append((spans, units))
        return actual_matcher(spans, units)

    def no_parse_or_normalized_matcher(*_args, **_kwargs):
        pytest.fail("transcript material proof must use its existing units, without parsing or normalization")

    monkeypatch.setattr(select, "verify_replayed_pdf_spans", counted_matcher)
    monkeypatch.setattr(select, "verify_parsed_evidence_spans", no_parse_or_normalized_matcher)
    monkeypatch.setattr(select, "parse_transcript_text", no_parse_or_normalized_matcher)
    monkeypatch.setattr(select, "parse_pdf_bytes", no_parse_or_normalized_matcher)
    if forged_parser:
        with pytest.raises(select._SelectFailure) as rejected:
            select.NarrativeSelectHandler._verify_selected_material(parsed, package)
        assert rejected.value.code == "PARSER_INCOMPLETE"
    else:
        select.NarrativeSelectHandler._verify_selected_material(parsed, package)
    assert calls == [((span,), (unit,))]


@pytest.mark.parametrize("mime_type", ["text/html", "application/xhtml+xml"])
@pytest.mark.parametrize("normalized", [False, True])
def test_same_html_mime_binds_actual_source_parser_matcher_through_selection(tmp_path, monkeypatch, mime_type, normalized):
    from company_wiki.automation.narrative_select import NarrativeSelectHandler
    from company_wiki.source_catalog.narrative_reading import select_reading_evidence

    files = fake_sources(tmp_path, monkeypatch)
    parsed = post_parse_material(mime_type, normalized=normalized)
    kind = "results_release" if normalized else "investor_call_transcript"
    package = select_reading_evidence(parsed, title="Company results", existing_kind=kind)
    assert package.evidence_spans
    NarrativeSelectHandler._verify_selected_material(parsed, package)
    frozen = package.reading_dependencies
    assert frozen["status"] == "complete"
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(frozen))["status"] == "same"
    actual_module = MODULES[1] if normalized else MODULES[2]
    irrelevant_module = MODULES[2] if normalized else MODULES[1]
    files[irrelevant_module].write_bytes(b"def verify_selected():\n    return False\n")
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(frozen))["status"] == "same"
    files[actual_module].write_bytes(b"def verify_selected():\n    return False\n")
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(frozen))["status"] == "changed"


def observed_carrier(mime_type):
    observed = _real_interim_pipeline()
    observed["observation"]["metadata"]["mime_type"] = mime_type
    if mime_type == "application/pdf":
        from company_wiki.source_catalog.narrative_pdf_layout import PDF_READING_LAYOUT_FEATURE_VERSION
        observed["observation"]["metadata"]["native_layout_frontend_version"] = PDF_READING_LAYOUT_FEATURE_VERSION
    return observed


def fake_sources(tmp_path, monkeypatch):
    files = {}
    original = inventory.import_module
    for index, module in enumerate(MODULES):
        path = tmp_path / f"owned-source-{index}.py"
        path.write_bytes(b"def verify_selected():\n    return True\n")
        files[module] = path

    def load(name):
        return SimpleNamespace(__file__=str(files[name])) if name in files else original(name)

    monkeypatch.setattr(inventory, "import_module", load)
    return files


@pytest.mark.parametrize("module,mime_type", [
    (MODULES[0], "text/html"), (MODULES[1], "text/html"), (MODULES[2], "application/pdf"),
    (MODULES[2], "text/plain"), (MODULES[2], "application/json"),
])
def test_actual_changed_usability_code_changes_existing_complete_decision_dependency(tmp_path, monkeypatch, module, mime_type):
    observed = observed_carrier(mime_type)
    files = fake_sources(tmp_path, monkeypatch)
    before = inventory.build_decision_trace(observed)
    assert before["versions"].get("source_usability"), "actual source usability is a causal reading dependency"
    frozen = freeze_decision_dependencies(before)
    assert frozen["status"] == "complete"
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(before))["status"] == "same"
    files[module].write_bytes(b"def verify_selected():\n    return False\n")
    current = inventory.current_decision_trace(before)
    assert compare_decision_dependencies(frozen, current)["status"] == "changed"
    assert {k: v for k, v in current.items() if k != "versions"} == {k: v for k, v in before.items() if k != "versions"}


@pytest.mark.parametrize("mime_type,normalized", [
    ("text/html", None), ("application/pdf", None), ("text/plain", None), ("application/json", None),
    ("text/html", True), ("text/html", False), ("application/xhtml+xml", False),
])
def test_same_code_other_install_path_and_crlf_keeps_portable_dependency(tmp_path, monkeypatch, mime_type, normalized):
    observed = observed_carrier(mime_type)
    files = fake_sources(tmp_path, monkeypatch)
    names = (None if normalized is None
             else tuple(unit.parser_name for unit in post_parse_material(mime_type, normalized=normalized).units))
    before = inventory.build_decision_trace(observed, source_parser_names=names)
    assert before["versions"].get("source_usability")
    for module, path in list(files.items()):
        moved = tmp_path / "other-install" / path.name
        moved.parent.mkdir(exist_ok=True)
        moved.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        files[module] = moved
    assert inventory.current_decision_trace(before) == before
    assert str(tmp_path) not in str(before["versions"])


@pytest.mark.parametrize("mime_type", ["text/html", "application/pdf", "text/plain", "application/json"])
@pytest.mark.parametrize("missing_names", [None, ()])
def test_missing_parser_names_keep_existing_call_interface_and_trace(tmp_path, monkeypatch, mime_type, missing_names):
    fake_sources(tmp_path, monkeypatch)
    observed = observed_carrier(mime_type)
    default = inventory.build_decision_trace(observed)
    assert inventory.build_decision_trace(observed, source_parser_names=missing_names) == default
    assert inventory.current_decision_trace(default) == default


def test_pre_fix_html_trace_cannot_reuse_ambiguous_material_matcher_cache(tmp_path, monkeypatch):
    fake_sources(tmp_path, monkeypatch)
    legacy = inventory.build_decision_trace(observed_carrier("text/html"))
    # Previous inventories only recorded MIME: they cannot prove which of the
    # two HTML material matchers actually ran. Existing caches must miss once.
    legacy["versions"]["source_usability"] = legacy["versions"]["source_usability"].replace(
        "source-usability/3+", "source-usability/2+")
    frozen = freeze_decision_dependencies(legacy)
    assert frozen["status"] == "complete"
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(frozen))["status"] == "changed"


def test_mixed_actual_parser_names_use_non_normalized_source_matcher(tmp_path, monkeypatch):
    from company_wiki.document_normalization.units import PARSER_NAME
    from company_wiki.source_catalog.narrative_evidence import NARRATIVE_PARSER_NAME

    files = fake_sources(tmp_path, monkeypatch)
    trace = inventory.build_decision_trace(observed_carrier("text/html"),
        source_parser_names=(PARSER_NAME, NARRATIVE_PARSER_NAME))
    frozen = freeze_decision_dependencies(trace)
    assert frozen["status"] == "complete"
    files[MODULES[1]].write_bytes(b"def verify_selected():\n    return False\n")
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(frozen))["status"] == "same"
    files[MODULES[2]].write_bytes(b"def verify_selected():\n    return False\n")
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(frozen))["status"] == "changed"


@pytest.mark.parametrize("irrelevant,mime_type", [
    (MODULES[1], "application/pdf"), (MODULES[2], "text/html"),
    (MODULES[1], "text/plain"), (MODULES[1], "application/json"),
])
def test_other_carrier_replay_code_does_not_invalidate_current_source(tmp_path, monkeypatch, irrelevant, mime_type):
    files = fake_sources(tmp_path, monkeypatch)
    before = inventory.build_decision_trace(observed_carrier(mime_type))
    files[irrelevant].write_bytes(b"def verify_selected():\n    return False\n")
    assert inventory.current_decision_trace(before) == before
