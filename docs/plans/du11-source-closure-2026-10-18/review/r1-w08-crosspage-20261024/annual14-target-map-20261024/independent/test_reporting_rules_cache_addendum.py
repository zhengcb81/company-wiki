"""Independent counterfactual for the one-line cache dependency registration."""
from hashlib import sha256
import inspect
from pathlib import Path

import pytest

from company_wiki.document_normalization import normalize_document
from company_wiki.document_understanding import understand_units, decision_inventory as inventory
from company_wiki.document_understanding.decision_dependencies import (
    freeze_decision_dependencies, compare_decision_dependencies,
)
from company_wiki.source_catalog import narrative_reporting_rules as rules


def _without_registration():
    source = inspect.getsource(inventory._versions)
    registration = '        "company_wiki.source_catalog.narrative_reporting_rules",\n'
    assert source.count(registration) == 1
    namespace = dict(vars(inventory))
    exec(compile(source.replace(registration, ""), "<independent-prior-versions>", "exec"), namespace)
    return namespace["_versions"]


@pytest.mark.parametrize("pdf_frontend", (False, True))
def test_rule_bytes_invalidate_current_algorithms_while_prior_closure_misses_them(monkeypatch, pdf_frontend):
    actual_file = Path(rules.__file__).resolve()
    reader = Path.read_bytes
    prior_versions = _without_registration()
    prior = prior_versions(pdf_frontend=pdf_frontend)
    current = inventory._versions(pdf_frontend=pdf_frontend)
    with monkeypatch.context() as patch:
        def changed_bytes(path):
            raw = reader(path)
            return raw + b"\n# independent rule-only byte counterfactual\n" if path.resolve() == actual_file else raw
        patch.setattr(Path, "read_bytes", changed_bytes)
        assert prior_versions(pdf_frontend=pdf_frontend) == prior
        changed = inventory._versions(pdf_frontend=pdf_frontend)
        assert changed["business_algorithms"] != current["business_algorithms"]
        assert {key: value for key, value in changed.items() if key != "business_algorithms"} == {
            key: value for key, value in current.items() if key != "business_algorithms"}
    assert inventory._versions(pdf_frontend=pdf_frontend) == current


@pytest.mark.parametrize("omit_registration", (False, True))
def test_actual_complete_decision_requires_rule_only_change_recomputation(monkeypatch, omit_registration):
    if omit_registration:
        monkeypatch.setattr(inventory, "_versions", _without_registration())
    raw = b"<html><body><h1>INTERIM REPORT 2026</h1><p>Our company launched a new software platform for customers.</p></body></html>"
    digest = sha256(raw).hexdigest()
    source_id = "urn:company-wiki:source:sha256:" + digest
    parsed = normalize_document(raw, source_id=source_id, source_sha256=digest, mime_type="text/html")
    observed = understand_units(parsed.structure.units, source_id=source_id, source_sha256=digest,
        title="INTERIM REPORT 2026", declared_kind="semi_annual_report", language="en",
        mime_type="text/html", metadata={"regime": "hkex"})
    trace = inventory.build_decision_trace(observed)
    frozen = freeze_decision_dependencies(trace)
    assert frozen["status"] == "complete"
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(trace))["status"] == "same"
    actual_file = Path(rules.__file__).resolve()
    reader = Path.read_bytes
    with monkeypatch.context() as patch:
        def changed_bytes(path):
            raw = reader(path)
            return raw + b"\n# independent rule-only byte counterfactual\n" if path.resolve() == actual_file else raw
        patch.setattr(Path, "read_bytes", changed_bytes)
        comparison = compare_decision_dependencies(frozen, inventory.current_decision_trace(trace))
        assert comparison["status"] == ("same" if omit_registration else "changed")
    assert compare_decision_dependencies(frozen, inventory.current_decision_trace(trace))["status"] == "same"
