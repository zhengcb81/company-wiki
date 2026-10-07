"""Deliverable contract checks (card section 7).

Validates the committed reports themselves: unknown/conflict evidence never
becomes an applied field, every id is a production id or explicitly null, the
read budgets add up, and every net-release field is zero or explicitly unknown.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from g3_source_facts.proposals import ACTIONS

REPORTS = (
    Path(__file__).resolve().parents[3] / "docs" / "implementation" / "g3-source-facts"
)
_PROPOSALS = REPORTS / "metadata_proposals.json"
_RAW_SPACE = REPORTS / "raw_space_decision.json"
_HANDOFF = REPORTS / "handoff.json"

_HASH_AND_COVER_BYTES = 75_886_072
_PHASE5_REHASH_BYTES = 37_943_036
_RAW_DUP_READ_BYTES = 122_369_272


@pytest.fixture(scope="module")
def proposals() -> dict:
    return json.loads(_PROPOSALS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def raw_space() -> dict:
    return json.loads(_RAW_SPACE.read_text(encoding="utf-8"))


def test_unknown_or_conflict_evidence_never_becomes_an_applied_field(proposals):
    for item in proposals["items"]:
        statuses = {e["field"]: e["status"] for e in item["evidence"]}
        blocked = {f for f, s in statuses.items() if s in {"unknown", "conflict"}}
        applied = set(item["proposed"]) - set(item["current"])
        assert not (applied & blocked), (
            f"{item['sample_id']} proposes {sorted(applied & blocked)} from "
            f"{sorted(applied & blocked)} unknown/conflict evidence"
        )
        if (
            any(e["status"] == "conflict" for e in item["evidence"])
            or item["conflicts"]
        ):
            assert item["action"] == "unresolved", item["sample_id"]


def test_every_id_is_a_production_urn_or_explicitly_null(proposals):
    for item in proposals["items"]:
        for field in ("source_id", "document_id", "source_version_id", "location_id"):
            value = item[field]
            if value is None:
                continue
            assert value.startswith("urn:company-wiki:"), (
                item["sample_id"],
                field,
                value,
            )
            assert not value.startswith(("S0", "P0", "T0")), value
        if not item["source_id"]:
            assert item["action"] == "register_new", item["sample_id"]


def test_actions_stay_inside_the_closed_vocabulary(proposals):
    for item in proposals["items"]:
        assert item["action"] in ACTIONS
    assert len(proposals["items"]) == 9


def test_report_keeps_unknowns_and_conflicts_visible(proposals):
    assert proposals["unknowns"], "unknown evidence must be surfaced, not dropped"
    assert proposals["conflicts"], "the S08 date conflict must stay visible"
    assert all("status" in row for row in proposals["unknowns"])
    assert all("code" in row for row in proposals["conflicts"])


def test_read_budgets_add_up_and_stay_inside_the_limits(proposals, raw_space):
    budget = proposals["budget"]
    assert budget["status"] == "complete"
    assert budget["consumed_bytes"] == _HASH_AND_COVER_BYTES
    assert (
        budget["consumed_bytes"] + budget["remaining_bytes"]
        == budget["total_limit_bytes"]
    )
    assert budget["total_limit_bytes"] == 512 * 1024 * 1024
    assert raw_space["read_bytes"] == _RAW_DUP_READ_BYTES
    assert raw_space["read_bytes"] <= raw_space["limits"]["max_read_bytes"]
    assert raw_space["read_bytes"] <= 268_435_456

    handoff = json.loads(_HANDOFF.read_text(encoding="utf-8"))
    effects = handoff["external_effects"]
    assert effects["read_bytes"] == (
        _HASH_AND_COVER_BYTES + _PHASE5_REHASH_BYTES + _RAW_DUP_READ_BYTES
    )
    assert effects["read_bytes"] <= effects["read_budget_bytes"]


def test_all_net_release_fields_are_zero_or_explicitly_unknown(raw_space):
    assert raw_space["deleted_bytes"] == 0
    assert raw_space["releasable_bytes"] is None
    assert raw_space["allocated_bytes"] is None
    assert raw_space["scope"] == "company_raw"
    assert raw_space["decision"] in {
        "no_migration_recommended",
        "prepare_followup",
        "not_enough_evidence",
    }
    assert raw_space["global_registered_totals"]["scope"] == "whole_database"
    assert any("unproven" in entry for entry in raw_space["unknowns"])


def test_handoff_declares_zero_external_side_effects():
    handoff = json.loads(_HANDOFF.read_text(encoding="utf-8"))
    effects = handoff["external_effects"]
    assert effects["model_posts"] == 0
    assert effects["production_writes"] == 0
    assert effects["raw_deleted"] == 0
    assert handoff["lane"] == "G3-SOURCE-FACTS"
    assert handoff["base"] == "5930a644453ed46494c2c83c5ecfb97767fa9492"
    assert handoff["tests"][0]["exit"] == 0
