"""A causal explanation consumes full source scope, including modality."""
import json
from pathlib import Path

import pytest

from company_wiki.source_catalog import narrative_business_policy as policy

_CASES=json.loads((Path(__file__).resolve().parents[2] /
    "fixtures/narrative_measure_scope_cases.json").read_text(encoding="utf-8"))["cases"]
_MEASURE_REASONS={"operating_quantity", "operating_metric_change", "business_revenue_measure",
                  "operating_causal_driver", "product_operating_driver"}


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["id"])
def test_observed_measure_and_causal_scope(case):
    clauses=policy._reading_clauses(policy._reading_text(case["text"]))
    kinds={kind for clause in clauses for kind, _start, _end in policy._source_measure_relations(clause)}
    assert kinds == set(case["expected_measure_kinds"])
    fact=policy.detect_reading_business_fact(case["text"])
    if case["expected_reason"] is None:
        assert not set(fact.reasons) & _MEASURE_REASONS
    else:
        assert case["expected_reason"] in fact.reasons
