"""Retained real observations -> exact native IDs and positions.

The lane's saved VRSK 10-Q observation and adapter-identity observation are
read-only inputs (sha256-checked against ``fixtures/manifest.json``).  The
assertions pin the exact native unit IDs and character positions of the real
nine-character ``FORM 10-Q`` carrier and its inline ``dei:DocumentType`` value.
This is not a re-parse of the owner original and not a production route test.
"""

from __future__ import annotations

import hashlib
import json
import re

from builders import budget, carrier, observation, ref, unit

from conftest import PWF_FIXTURES

from company_wiki.document_understanding.source_signals import collect_source_signals

SOURCE_PARENT = (
    "urn:company-wiki:source:sha256:"
    "5afe631934fce5d3e23b6aa393ec599cd89b290cde1fc1667ebe22025d2479eb"
)
FORM_UNIT_ID = (
    "urn:company-wiki:narrative-unit:sha256:"
    "73ba6668bb9b633c2472632e7283ecadde0ca24c5727909b6e4275a0f7637d3a"
)
TOC_UNIT_ID = (
    "urn:company-wiki:narrative-unit:sha256:"
    "9e9c63d1d50877e1f0f908208926479b0a91899a4d49f2b8081f9c4beec3b185"
)
REVENUES_UNIT_IDS = {
    "urn:company-wiki:narrative-unit:sha256:"
    "b07d38e4b17b78b87bb56bb0a096d4135931412a1b9b1c04e3f6d82d0ac4e01a",
    "urn:company-wiki:narrative-unit:sha256:"
    "1bd8b04ea028a659cb3dbe2bb597121a76b45499cfd04ba982717d9c7e14a662",
}


def _load(name: str) -> dict:
    return json.loads((PWF_FIXTURES / name).read_text(encoding="utf-8"))


def _manifest() -> dict[str, dict]:
    entries = json.loads((PWF_FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    return {entry["path"]: entry for entry in entries}


def _check_fixture_hash(name: str) -> None:
    raw = (PWF_FIXTURES / name).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == _manifest()[name]["sha256"], f"{name} no longer matches its manifest"


def test_saved_observations_match_manifest_hashes():
    for name in ("us-10q-observation.json", "adapter-identity-observation.json"):
        _check_fixture_hash(name)


def test_real_form_unit_id_and_dei_position_survive_verbatim():
    saved = _load("us-10q-observation.json")
    form_unit = saved["actual_form_units"][0]
    assert form_unit["unit_id"] == FORM_UNIT_ID
    assert form_unit["text"] == "FORM 10-Q"
    assert form_unit["locator"] == "loc:v1/paragraph:4"

    # The retained raw DEI bytes show the inline wrapping: FORM + <ix>10-Q</ix>.
    excerpt = saved["actual_raw_dei"]["excerpt"]
    concept_match = re.search(r'name="([^"]+)"', excerpt)
    assert concept_match is not None
    concept = concept_match.group(1)
    assert concept == "dei:DocumentType"
    value_match = re.search(r">([^<]+)</ix:nonNumeric>", excerpt)
    assert value_match is not None
    dei_value = value_match.group(1)
    assert dei_value == "10-Q"
    start = form_unit["text"].index(dei_value)
    assert (start, start + len(dei_value)) == (5, 9)

    obs = observation(
        [
            unit(
                FORM_UNIT_ID,
                form_unit["text"],
                parent_id=SOURCE_PARENT,
                role=form_unit["role"],
                kind=form_unit["kind"],
                locator=form_unit["locator"],
            )
        ],
        [
            carrier(
                "visible_own_form_label",
                [FORM_UNIT_ID],
                [ref(FORM_UNIT_ID, 0, len(form_unit["text"]))],
                parent_id=SOURCE_PARENT,
            ),
            carrier(
                "visible_inline_xbrl_document_type",
                [FORM_UNIT_ID],
                [ref(FORM_UNIT_ID, start, start + len(dei_value))],
                parent_id=SOURCE_PARENT,
                attributes={"concept": concept, "visibility": "visible"},
            ),
        ],
    )
    result = collect_source_signals(obs, work_budget=budget())
    evidence = result["source_form_evidence"]
    assert [entry["value"] for entry in evidence] == ["FORM 10-Q", "10-Q"]
    for entry in evidence:
        assert entry["carrier_unit_ids"] == [FORM_UNIT_ID]
        assert entry["parent_id"] == SOURCE_PARENT
        assert entry["normalized_value"] == "10-Q"
    assert evidence[1]["value_refs"] == [ref(FORM_UNIT_ID, 5, 9)]
    assert evidence[1]["concept"] == "dei:DocumentType"
    assert result["reserved_unit_ids"] == [FORM_UNIT_ID]
    assert result["status"] == "complete"


def test_real_revenues_cell_without_native_turn_carrier_is_not_a_turn():
    saved = _load("adapter-identity-observation.json")
    wire_unit = saved["wire"]["units"][0]
    assert wire_unit["unit_id"] in REVENUES_UNIT_IDS
    assert wire_unit["text"] == "Revenues:"
    obs = observation(
        [
            unit(
                wire_unit["unit_id"],
                wire_unit["text"],
                parent_id=SOURCE_PARENT,
                role=wire_unit["role"],
                kind=wire_unit["kind"],
                locator=wire_unit["locator"],
            )
        ],
        [],
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert result["turn_evidence"] == []
    assert result["reserved_unit_ids"] == []
    assert result["status"] == "complete"


def test_real_cover_units_are_never_form_carriers():
    saved = _load("us-10q-observation.json")
    form_unit = saved["actual_form_units"][0]
    toc = next(
        entry for entry in saved["reason_units"] if entry["unit_id"] == TOC_UNIT_ID
    )
    revenues = [entry for entry in saved["reason_units"] if entry["unit_id"] in REVENUES_UNIT_IDS]
    units = [
        unit(
            form_unit["unit_id"],
            form_unit["text"],
            parent_id=SOURCE_PARENT,
            role=form_unit["role"],
            kind=form_unit["kind"],
            locator=form_unit["locator"],
        ),
        unit(
            toc["unit_id"],
            toc["text"],
            parent_id=SOURCE_PARENT,
            role=toc["role"],
            kind=toc["kind"],
            locator=toc["locator"],
        ),
    ]
    units.extend(
        unit(
            entry["unit_id"],
            entry["text"],
            parent_id=SOURCE_PARENT,
            role=entry["role"],
            kind=entry["kind"],
            locator=entry["locator"],
        )
        for entry in revenues
    )
    obs = observation(
        units,
        [carrier("visible_own_form_label", [FORM_UNIT_ID], [ref(FORM_UNIT_ID, 0, 9)], parent_id=SOURCE_PARENT)],
        declared_form=saved["observation_metadata"]["declared_kind"],
    )
    result = collect_source_signals(obs, work_budget=budget())
    cited = {
        unit_id
        for entry in result["source_form_evidence"]
        for unit_id in entry["carrier_unit_ids"]
    }
    assert cited == {FORM_UNIT_ID}
    assert result["reserved_unit_ids"] == [FORM_UNIT_ID]
