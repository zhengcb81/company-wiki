"""Neutral independent C3 semantic counterexamples; no live corpus or IO."""
import json
from pathlib import Path

import pytest

from company_wiki.source_catalog import narrative_business_policy as policy
from company_wiki.source_catalog import narrative_operating_resources as resources

ACTUAL = {"operating_resource_stock", "operating_resource_allocation"}


@pytest.mark.parametrize("text", (
    "We have no plans to invest in research and development.",
    "We have no current plans to invest in research and development.",
    "公司暂无计划投入技术研发。",
    "公司不计划投资技术研发。",
    "本集團暫無計劃投資技術研發。",
    "We will not invest USD 4 million in research and development.",
    "公司尚未确定计划投入技术研发。",
))
def test_negated_resource_plan_is_not_an_actual_or_positive_plan(text):
    fact = policy.project_reading_business_fact(text, {"relations": []})
    assert not (ACTUAL | {"operating_plan"}).intersection(fact.reasons), (text, fact)


@pytest.mark.parametrize("text", (
    "Our research staff will number 2,400 people next year.",
    "Our R&D staff will reach 2,400 employees next year.",
    "公司研发人员将达到2,400人。",
    "本集團研發人員將達到2,400人。",
    "We expect our research staff to reach 2,400 people next year.",
))
def test_explicit_future_resource_quantity_is_retained_as_plan_only(text):
    fact = policy.project_reading_business_fact(text, {"relations": []})
    assert "operating_plan" in fact.reasons, (text, fact)
    assert not ACTUAL.intersection(fact.reasons), (text, fact)


def test_resource_predicate_scan_work_grows_linearly_with_assertions(monkeypatch):
    original = resources.observe_metric_predicate
    rows = []
    for count in (16, 32, 64):
        observed_sizes = []
        def observed(text, start, end):
            observed_sizes.append(len(text))
            return original(text, start, end)
        monkeypatch.setattr(resources, "observe_metric_predicate", observed)
        text = ", ".join(["our R&D staff numbered 2,400 employees"] * count)
        reasons = resources.operating_resource_relations(text)
        rows.append({"assertions": count, "chars": len(text), "calls": len(observed_sizes),
                     "predicate_input_chars": sum(observed_sizes),
                     "declared_resource_work": resources.RESOURCE_READING_SCAN_PASSES * len(text),
                     "reasons": reasons})
    (Path(__file__).parent / "scan-counts.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    assert rows[-1]["predicate_input_chars"] <= 2.25 * rows[-2]["predicate_input_chars"], rows
