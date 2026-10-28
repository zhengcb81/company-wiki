"""Neutral semantics and actual regex-input accounting for shared predicates."""
import re

import pytest

from company_wiki.source_catalog import narrative_operating_resources as resources
from company_wiki.source_catalog import narrative_predicate_state as predicates


class RegexMeter:
    """Delegate every real regex operation and charge the actual input window."""

    def __init__(self, pattern, totals, name):
        self.pattern_object, self.totals, self.name = pattern, totals, name

    def __getattr__(self, name):
        original = getattr(self.pattern_object, name)
        if name not in {"search", "match", "fullmatch", "finditer", "findall", "split", "sub"}:
            return original

        def measured(text, *args, **kwargs):
            start = args[0] if args and name not in {"split", "sub"} else 0
            end = args[1] if len(args) > 1 and name not in {"split", "sub"} else len(text)
            self.totals[self.name] = self.totals.get(self.name, 0) + end - start
            return original(text, *args, **kwargs)
        return measured


def meter(monkeypatch, totals):
    for module in (predicates, resources):
        for name, value in vars(module).items():
            if isinstance(value, re.Pattern):
                monkeypatch.setattr(module, name, RegexMeter(value, totals, module.__name__ + name))


def test_real_boundary_and_modal_scans_grow_linearly(monkeypatch):
    observations = []
    for size in (16, 32, 64):
        text = ", ".join(["our R&D staff numbered 2,400 employees"] * size)
        totals = {}
        with monkeypatch.context() as patch:
            meter(patch, totals)
            assert resources.operating_resource_relations(text) == ("operating_resource_stock",)
        observations.append((len(text), sum(totals.values())))
        # No fake probe replaces recognition. Both real boundary and modal
        # owners must have scanned, including preparation and all queries.
        assert totals[predicates.__name__ + "_BOUNDARY"] >= len(text)
        assert totals[predicates.__name__ + "_MODAL"] > 0
    for (old_len, old_work), (new_len, new_work) in zip(observations, observations[1:]):
        assert new_work / old_work <= (new_len / old_len) * 1.15, observations


@pytest.mark.parametrize("text", (
    "We have no plans to invest in research and development.",
    "We have no current plans to invest in research and development.",
    "公司暂无计划投入技术研发。", "公司不计划投资技术研发。",
    "本集團暫無計劃投資技術研發。",
))
def test_shared_owner_negates_plan_governor(text):
    start = text.index("invest") if "invest" in text else text.index("投")
    state = predicates.observe_metric_predicate(text, start, start + 2)
    assert state.modality == "negative" and not state.forward_outlook and not state.observed


def test_prepared_long_assertion_many_queries_do_not_rescan_prefixes(monkeypatch):
    observations = []
    for size in (16, 32, 64):
        text = " and ".join(["R&D staff will number 2,400 employees"] * size)
        spans = [(m.start(), m.end()) for m in re.finditer(r"R&D staff", text)]
        totals = {}
        with monkeypatch.context() as patch:
            meter(patch, totals)
            context = predicates.prepare_predicate_context(text)
            before_queries = sum(totals.values())
            for start, end in spans:
                state = context.observe(start, end)
                assert state.modality == "planned" and not state.observed
            assert sum(totals.values()) == before_queries
        observations.append((len(text), sum(totals.values())))
    for (old_len, old_work), (new_len, new_work) in zip(observations, observations[1:]):
        assert new_work / old_work <= (new_len / old_len) * 1.15, observations


@pytest.mark.parametrize("text,target,mode,period,condition", (
    ("Our R&D staff numbered 1,237 employees this year.", "R&D staff", "actual", "current", False),
    ("Next year, our research staff will number 2,400 employees.", "research staff", "planned", "future", False),
    ("If customers renew, our research staff numbered 1,237 employees.", "research staff", "conditional", "unspecified", True),
    ("We expect research staff to reach 2,400 people if customers do not renew.", "research staff", "expected", "unspecified", True),
    ("We have no plans to invest, but our research staff numbered 1,237 employees.", "research staff", "actual", "unspecified", False),
    ("公司不计划投资研发，但公司研发人员达到1,237人。", "研发人员", "actual", "unspecified", False),
    ("本集團研發人員將達到2,400人。", "研發人員", "planned", "unspecified", False),
    ("We will publish our research staff count next year.", "research staff", "referenced", "future", False),
    ("Our research staff numbered 1,237 people compared with last year.", "research staff", "actual", "unspecified", False),
    ("We expect research staff to have grown last year.", "research staff", "expected", "past", False),
    ("Our projects reached 2,400 this year.", "projects", "actual", "current", False),
    ("We project 2,400 customers next year.", "project", "referenced", "future", False),
    ("We project 2,400 customers next year.", "customers", "expected", "future", False),
    ("Our staff are below our planned headcount.", "planned headcount", "referenced", "unspecified", False),
    ("Our staff are below our planned headcount.", "our planned", "referenced", "unspecified", False),
    ("Under the assumption that customers renew, our research staff number 1,237 employees.", "research staff", "conditional", "unspecified", True),
    ("We review assumptions that customers renew, our research staff number 1,237 employees.", "research staff", "actual", "unspecified", False),
))
def test_prepared_and_single_observation_share_scope_and_state(text, target, mode, period, condition):
    start = text.index(target)
    end = start + len(target)
    context = predicates.prepare_predicate_context(text)
    state = context.observe(start, end)
    assert state == predicates.observe_metric_predicate(text, start, end)
    assert context.scope(start, end) == predicates.predicate_scope(text, start, end)
    assert (state.modality, state.period, state.has_condition) == (mode, period, condition)


def test_modality_view_keeps_offsets_and_original_numeric_commas():
    text = "Our R&D staff will number 2,400 employees, but our supplier employed 1,237 engineers."
    context = predicates.prepare_predicate_context(text)
    view = context.modality_view()
    assert context.text == text and len(view) == len(text)
    assert view == text.replace("will", "    ")
    assert len(context.assertion_spans) == 3  # comma and independent actor boundary
    assert "2,400" in view and "1,237" in view


@pytest.mark.parametrize("span", ((-1, 2), (2, 2), (0, 100)))
def test_shared_public_and_prepared_validation_agree(span):
    context = predicates.prepare_predicate_context("Our staff numbered 12 people.")
    with pytest.raises(ValueError, match="outside classification text"):
        context.observe(*span)
    with pytest.raises(ValueError, match="outside classification text"):
        predicates.observe_metric_predicate(context.text, *span)
