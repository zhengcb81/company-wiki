"""Real source-metric work grows with text, with semantic recognition intact."""
import re

import pytest

from company_wiki.source_catalog import narrative_business_policy as policy
from company_wiki.source_catalog import narrative_predicate_state as predicates
from unit.document_understanding_selection.test_prepared_predicate_context import RegexMeter


@pytest.mark.parametrize("actor", ("our ", ""))
def test_result_subject_many_metrics_uses_bounded_real_regex_windows(monkeypatch, actor):
    rows = []
    for count in (16, 32, 64):
        text = " and ".join([actor + "paid subscribers totaled 2,370"] * count)
        text += " and " + actor + "customers increased by 12%."
        totals = {}
        with monkeypatch.context() as patch:
            for module in (policy, predicates):
                for name, value in vars(module).items():
                    if isinstance(value, re.Pattern):
                        patch.setattr(module, name, RegexMeter(value, totals, module.__name__ + name))
            start = text.index("increased")
            assert policy.source_result_subject(text, start, start + len("increased"))
        rows.append((len(text), sum(totals.values())))
        # Do not obtain linearity by returning before recognition: every stock
        # metric and the final observed direction retain original source spans.
        relations = policy._source_metric_relations(text)
        assert sum(kind == "quantity" for kind, _, _ in relations) == count
        assert sum(kind == "direction" for kind, _, _ in relations) == 1
        assert all(text[left:right] in {"subscribers", "customers"} for _, left, right in relations)
        assert len(predicates.prepare_predicate_context(text).assertion_spans) == (count + 1 if actor else 1)
    for (old_len, old_work), (new_len, new_work) in zip(rows, rows[1:]):
        assert new_work / old_work <= 1.15 * new_len / old_len, rows
