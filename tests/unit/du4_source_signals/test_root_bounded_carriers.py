"""ROOT: source signal work is paid before walking, and values stay contiguous."""
import pytest

from .builders import budget, carrier, code_set, observation, ref, unit
from company_wiki.document_understanding.source_signals import collect_source_signals


class CountedList(list):
    def __init__(self, rows):
        super().__init__(rows)
        self.visited = 0

    def __iter__(self):
        for row in super().__iter__():
            self.visited += 1
            yield row


def test_exhausted_budget_never_walks_a_carrier_unit_list():
    ids = CountedList(["u"] + [f"unknown-{i}" for i in range(20000)])
    obs = observation([unit("u", "FORM 10-Q")], [carrier("visible_own_form_label", ids, [])])
    obs["carriers"][0]["unit_ids"] = ids
    ids.visited = 0  # builders copy lists; observe only collector work
    result = collect_source_signals(obs, work_budget=budget(1))
    assert result["status"] == "partial" and result["work_used"] == 1
    assert ids.visited == 0


def test_unpaid_value_refs_are_not_walked_for_raw_carrier_deduplication():
    refs = CountedList([ref("u", 0, 9) for _ in range(20000)])
    obs = observation([unit("u", "FORM 10-Q")], [carrier("visible_own_form_label", ["u"], refs)])
    obs["carriers"][0]["value_refs"] = refs
    refs.visited = 0
    result = collect_source_signals(obs, work_budget=budget(2))
    assert result["status"] == "partial" and result["work_used"] == 2
    assert refs.visited == 0


def test_ignored_attributes_and_top_level_extensions_are_never_serialized():
    class ForbiddenValue:
        def __str__(self):
            raise AssertionError("ignored native extension must not be inspected")
    obs = observation([unit("u", "FORM 10-Q")], [carrier("visible_own_form_label", ["u"],
        [ref("u", 0, 9)], attributes={"ignored_blob": ForbiddenValue()})])
    obs["carriers"][0]["arbitrary_extension"] = ForbiddenValue()
    result = collect_source_signals(obs, work_budget=budget())
    assert [row["value"] for row in result["source_form_evidence"]] == ["FORM 10-Q"]
    assert "DECLARED_ATTRIBUTE_IGNORED" in code_set(result)


def test_reserved_membership_is_indexed_not_quadratic():
    class CountedId(str):
        calls = 0
        __hash__ = str.__hash__
        def __eq__(self, other):
            type(self).calls += 1
            return super().__eq__(other)
    ids = [CountedId(f"u-{i}") for i in range(200)]
    obs = observation([unit(uid, "x") for uid in ids], [carrier("native_speaker_turn", [uid], [],
        attributes={"turn_id": f"turn-{i}"}) for i, uid in enumerate(ids)])
    CountedId.calls = 0
    result = collect_source_signals(obs, work_budget=budget())
    assert len(result["reserved_unit_ids"]) == 200
    assert CountedId.calls < 2000


def test_discontinuous_owner_spans_cannot_manufacture_a_form():
    obs = observation([unit("u", "FORM 10-notaform-Q")], [carrier("visible_own_form_label", ["u"],
        [ref("u", 0, 7), ref("u", 16, 18)])])
    result = collect_source_signals(obs, work_budget=budget())
    assert result["source_form_evidence"] == []
    assert "DISCONTINUOUS_VALUE_REFS" in code_set(result)
    assert result["status"] == "unavailable"


@pytest.mark.parametrize("kind", [{}, []])
def test_invalid_kind_is_a_structural_value_error(kind):
    obs = observation([unit("u", "FORM 10-Q")], [carrier("visible_own_form_label", ["u"], [ref("u", 0, 9)])])
    obs["carriers"][0]["kind"] = kind
    with pytest.raises(ValueError):
        collect_source_signals(obs, work_budget=budget())


def test_duplicate_identity_ignores_declarative_extension_values():
    a = carrier("visible_own_form_label", ["u"], [ref("u", 0, 9)], attributes={"ignored": "a"})
    b = carrier("visible_own_form_label", ["u"], [ref("u", 0, 9)], attributes={"ignored": "b"})
    result = collect_source_signals(observation([unit("u", "FORM 10-Q")], [a,b]), work_budget=budget())
    assert len(result["source_form_evidence"]) == 1
    assert "DUPLICATE_CARRIER" in code_set(result)


def test_repeated_unresolvable_carrier_does_not_become_resolved_by_dedup():
    c = carrier("visible_own_form_label", ["u"], [ref("u", 0, 9)], attributes={"visibility":"hidden"})
    c["kind"] = "visible_inline_xbrl_document_type"
    result = collect_source_signals(observation([unit("u", "FORM 10-Q")], [c,c]), work_budget=budget())
    assert result["source_form_evidence"] == []
    assert result["observed_counts"]["carriers_resolved"] == 0
    assert result["observed_counts"]["carriers_dropped"] == 2
