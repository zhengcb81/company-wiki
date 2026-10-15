"""Quote scoring consumes closure; source attribution remains the owner's job."""
from copy import deepcopy

import pytest

from tools.document_understanding_benchmark.closed_group_support import score_facts
from unit.document_understanding_selection.test_closed_group_support import SOURCE, context, fact, span


def attributed(rows):
    value = deepcopy(context(rows))
    value["schema_version"] = "du-production-reading/2"
    for group in value["groups"]:
        group["citation_views"] = [{"support_evidence_ids": group["evidence_ids"],
                                    "context_evidence_ids": []}]
    return value


@pytest.mark.parametrize("quote", ["公司新产品进入客户验证，尚未量产。", "2024年门店共4386家。"])
def test_new_canonical_context_keeps_the_exact_old_quote_denominator_and_result(quote):
    rows = [span("公司新产品进入客户", 0, reason="reading_plan"), span("验证，尚未量产。", 1)]
    selected_fact = fact(quote)
    previous = score_facts([selected_fact], evidence_spans=rows, reading_context=context(rows), source_id=SOURCE)
    current = score_facts([selected_fact], evidence_spans=rows, reading_context=attributed(rows), source_id=SOURCE)
    assert current == previous
    assert current[0]["supported"] == (quote == "公司新产品进入客户验证，尚未量产。")


def test_unknown_context_version_is_not_silently_accepted():
    rows = [span("公司完成海外客户验证。", 0)]
    value = attributed(rows)
    value["schema_version"] = "future-not-supported/99"
    with pytest.raises(ValueError, match="canonical production"):
        score_facts([fact("公司完成海外客户验证。")], evidence_spans=rows, reading_context=value, source_id=SOURCE)
