"""Real PDF paragraph indices restart per page; observed ordinal is global."""
from company_wiki.document_understanding.narrative_continuity import SourcePageFlow, build_native_continuity
from company_wiki.document_understanding.operating_states.relations import independent_statement_start
from unit.document_understanding_selection.test_reading_native_continuity import native


def inspect(rows, furniture=()):
    return build_native_continuity([row[0] for row in rows],
        provenance={row[0]["unit_id"]: row[1] for row in rows},
        unit_profiles={row[0]["unit_id"]: row[2] for row in rows},
        source_page_flow=SourcePageFlow(frozenset(furniture), independent_statement_start))


def test_observed_next_page_starts_with_its_own_paragraph_zero():
    left = native("The company plans to deliver the products to", 33, page=7,
                  box=[90, 720, 550, 732], block=34, column=0)
    right = native("our customers next year.", 34, page=8,
                   box=[90, 80, 550, 92], block=0, column=0)
    right[1]["paragraph_index"] = 0
    result = inspect([left, right])
    assert len(result["windows"]) == 1
    assert result["windows"][0]["member_unit_ids"] == [left[0]["unit_id"], right[0]["unit_id"]]


def test_proven_next_page_prefix_uses_local_paragraph_order_not_previous_page_numbers():
    left = native("The company plans to deliver the products to", 33, page=7,
                  box=[90, 720, 550, 732], block=34, column=0)
    header = native("Company annual report", 34, page=8, kind="header")
    footer = native("8", 35, page=8, kind="footer")
    right = native("our customers next year.", 36, page=8,
                   box=[90, 80, 550, 92], block=2, column=0)
    for index, row in enumerate((header, footer, right)):
        row[1]["paragraph_index"] = index
    ids = [header[0]["unit_id"], footer[0]["unit_id"]]
    result = inspect([left, header, footer, right], ids)
    assert len(result["windows"]) == 1
    assert result["windows"][0]["proof"][0]["furniture_unit_ids"] == ids


def test_unobserved_next_page_prefix_does_not_certify_a_complete_suffix():
    left = native("The company plans to deliver the products to", 33, page=7,
                  box=[90, 720, 550, 732], block=34, column=0)
    right = native("our customers next year.", 36, page=8,
                   box=[90, 80, 550, 92], block=2, column=0)
    right[1]["paragraph_index"] = 2
    result = inspect([left, right])
    assert not result["windows"]
    assert {left[0]["unit_id"], right[0]["unit_id"]} <= set(result["deferred_unit_ids"])


def test_unproved_page_counter_cannot_erase_an_unfinished_preceding_body():
    left = native("The company plans to deliver the products to", 33, page=7,
                  box=[90, 720, 550, 732], block=34, column=0)
    header = native("Annual report", 34, page=8, kind="header")
    footer = native("8 / 210", 35, page=8, scope="page-marker",
                    box=[290, 770, 330, 782])
    right = native("our customers next year.", 36, page=8,
                   box=[90, 80, 550, 92], block=2, column=0)
    for index, row in enumerate((header, footer, right)):
        row[1]["paragraph_index"] = index
    result = inspect([left, header, footer, right], [header[0]["unit_id"]])
    assert not result["windows"]  # The counter lacks positive furniture proof.
    assert {left[0]["unit_id"], right[0]["unit_id"]} <= set(result["deferred_unit_ids"])
