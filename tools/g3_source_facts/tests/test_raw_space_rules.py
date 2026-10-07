"""Counter-examples for the company_raw internal duplicate accounting (card 4/6)."""

from __future__ import annotations

import pytest

from g3_source_facts.raw_space import build_raw_space_decision, internal_groups


def _group(
    group_id,
    *,
    root_ids,
    classification="distinct_physical_copies",
    byte_size=1000,
    members=3,
    verification=None,
    logical=None,
    allocated=None,
):
    return {
        "group_id": group_id,
        "content_sha256": "c" * 64,
        "byte_size": byte_size,
        "classification": classification,
        "distinct_physical_copies": members,
        "logical_duplicate_bytes": (byte_size * (members - 1))
        if logical is None
        else logical,
        "physical_allocated_bytes": allocated,
        "locators": [
            {
                "location_id": f"{group_id}-l{i}",
                "source_id": f"{group_id}-s",
                "document_id": f"{group_id}-d",
                "root_id": root_id,
                "relative_path": f"companies/x/{group_id}-{i}.pdf",
                "location_status": "active",
                "role": "original_primary",
            }
            for i, root_id in enumerate(root_ids)
        ],
        "verification": verification
        or {
            "attempted": False,
            "status": "not_attempted",
            "files": [],
            "unread_members": [],
            "bytes_read": 0,
            "aborted_by": None,
        },
    }


def _report(groups, **overrides):
    base = {
        "schema_version": "raw-duplicate-assessment/1",
        "operation": "verify",
        "status": "succeeded",
        "limits": {
            "max_groups": 20,
            "max_read_bytes": 268435456,
            "deadline_seconds": 120.0,
            "max_detail_rows": 100,
            "max_similar_groups": 100,
        },
        "limits_hit": [],
        "read_bytes": 0,
        "duplicate_groups": groups,
        "deleted_bytes": 0,
    }
    base.update(overrides)
    return base


def _verified_files(group_id, n, byte_size):
    return [
        {
            "root_id": "company_raw",
            "relative_path": f"companies/x/{group_id}-{i}.pdf",
            "location_ids": [f"{group_id}-l{i}"],
            "status": "verified_identical",
            "registered_sha256": "c" * 64,
            "actual_sha256": "c" * 64,
            "bytes_read": byte_size,
            "detail": "",
        }
        for i in range(n)
    ]


# --- counter-example 7: outside roots / same physical file are not internal copies ---


def test_groups_bearing_an_outside_root_are_not_internal():
    mixed = _group("g1", root_ids=["company_raw", "dayu_portfolio"])
    internal = _group("g2", root_ids=["company_raw", "company_raw"])
    groups = internal_groups(_report([mixed, internal]))
    assert [g["group_id"] for g in groups] == ["g2"]


def test_same_path_and_hardlink_groups_never_count_as_distinct_copies():
    same_path = _group(
        "g1",
        root_ids=["company_raw", "company_raw"],
        classification="same_path_references",
    )
    shared = _group(
        "g2",
        root_ids=["company_raw", "company_raw"],
        classification="shared_physical_file",
    )
    decision = build_raw_space_decision(
        _report([same_path, shared], duplicate_groups=[same_path, shared]),
        command="scan",
        input_version="raw-duplicate-assessment/1",
    )
    assert decision["registered_upper_bound_bytes"] == 0
    assert decision["verified_distinct_copy_bytes"] == 0
    assert decision["counted_groups"] == []


def test_cross_root_or_missing_members_are_reported_not_savings():
    missing = _group(
        "g3",
        root_ids=["company_raw", "company_raw"],
        classification="distinct_physical_copies",
        verification={
            "attempted": True,
            "status": "missing",
            "files": [],
            "unread_members": [
                {
                    "location_id": "g3-l1",
                    "root_id": "company_raw",
                    "relative_path": "companies/x/g3-1.pdf",
                    "status": "missing",
                    "detail": "missing",
                }
            ],
            "bytes_read": 0,
            "aborted_by": None,
        },
    )
    decision = build_raw_space_decision(
        _report([missing]), command="verify", input_version="raw-duplicate-assessment/1"
    )
    assert decision["verified_distinct_copy_bytes"] == 0
    assert decision["incomplete_groups"] == 1


# --- counter-example 8: unread bytes are never counted as verified savings ---


def test_unverified_group_contributes_registered_bound_but_no_verified_bytes():
    group = _group("g1", root_ids=["company_raw", "company_raw"])
    decision = build_raw_space_decision(
        _report([group]), command="scan", input_version="raw-duplicate-assessment/1"
    )
    assert decision["registered_upper_bound_bytes"] == 1000
    assert decision["verified_distinct_copy_bytes"] == 0
    assert decision["incomplete_groups"] == 1


def test_fully_verified_group_counts_only_the_redundant_copies():
    byte_size = 4096
    group = _group(
        "g1",
        root_ids=["company_raw"] * 4,
        byte_size=byte_size,
        members=4,
        verification={
            "attempted": True,
            "status": "verified",
            "files": _verified_files("g1", 4, byte_size),
            "unread_members": [],
            "bytes_read": byte_size * 4,
            "aborted_by": None,
        },
    )
    decision = build_raw_space_decision(
        _report([group]), command="verify", input_version="raw-duplicate-assessment/1"
    )
    assert decision["candidate_groups"] == 1
    assert decision["verified_groups"] == 1
    assert decision["incomplete_groups"] == 0
    assert decision["verified_distinct_copy_bytes"] == byte_size * 3
    assert decision["registered_upper_bound_bytes"] == byte_size * 3


def test_partially_read_group_is_incomplete_and_counts_no_verified_bytes():
    byte_size = 4096
    files = _verified_files("g1", 2, byte_size)
    group = _group(
        "g1",
        root_ids=["company_raw"] * 3,
        byte_size=byte_size,
        members=3,
        verification={
            "attempted": True,
            "status": "verified",
            "files": files,
            "unread_members": [
                {
                    "location_id": "g1-l2",
                    "root_id": "company_raw",
                    "relative_path": "companies/x/g1-2.pdf",
                    "status": "skipped_cloud_placeholder",
                    "detail": "",
                }
            ],
            "bytes_read": byte_size * 2,
            "aborted_by": None,
        },
    )
    decision = build_raw_space_decision(
        _report([group]), command="verify", input_version="raw-duplicate-assessment/1"
    )
    assert decision["verified_groups"] == 0
    assert decision["incomplete_groups"] == 1
    assert decision["verified_distinct_copy_bytes"] == 0


# --- allocation / release fields stay unknown instead of collapsing to zero ---


def test_unproven_allocation_is_null_not_zero():
    group = _group("g1", root_ids=["company_raw", "company_raw"])
    decision = build_raw_space_decision(
        _report([group]), command="verify", input_version="raw-duplicate-assessment/1"
    )
    assert decision["allocated_bytes"] is None
    assert decision["releasable_bytes"] is None
    assert decision["deleted_bytes"] == 0


def test_unknown_internal_share_is_not_written_as_zero():
    decision = build_raw_space_decision(
        _report([], status="partial", limits_hit=["deadline"]),
        command="verify",
        input_version="raw-duplicate-assessment/1",
        limits_hit=["deadline"],
    )
    assert decision["registered_upper_bound_bytes"] == 0
    assert decision["unknowns"]
    assert decision["deleted_bytes"] == 0


def test_partial_scan_forces_not_enough_evidence():
    decision = build_raw_space_decision(
        _report([], status="partial", limits_hit=["read_bytes"]),
        command="verify",
        input_version="raw-duplicate-assessment/1",
        limits_hit=["read_bytes"],
    )
    assert decision["decision"] == "not_enough_evidence"


def test_small_verified_benefit_recommends_no_migration():
    byte_size = 1_000_000
    group = _group(
        "g1",
        root_ids=["company_raw"] * 2,
        byte_size=byte_size,
        members=2,
        verification={
            "attempted": True,
            "status": "verified",
            "files": _verified_files("g1", 2, byte_size),
            "unread_members": [],
            "bytes_read": byte_size * 2,
            "aborted_by": None,
        },
    )
    decision = build_raw_space_decision(
        _report([group]), command="verify", input_version="raw-duplicate-assessment/1"
    )
    assert decision["decision"] == "no_migration_recommended"
    assert decision["verified_distinct_copy_bytes"] == byte_size
    assert decision["releasable_bytes"] is None
    assert decision["deleted_bytes"] == 0


def test_whole_database_totals_are_labelled_as_global_not_company_raw():
    group = _group("g1", root_ids=["company_raw", "company_raw"])
    decision = build_raw_space_decision(
        _report([group], counts={"registered_sources": 43112, "registered_bytes": 123}),
        command="scan",
        input_version="raw-duplicate-assessment/1",
    )
    assert decision["global_registered_totals"]["scope"] == "whole_database"
    assert decision["global_registered_totals"]["registered_bytes"] == 123
    assert decision["scope"] == "company_raw"


@pytest.mark.parametrize("value", [None, 0])
def test_deleted_bytes_always_zero(value):
    decision = build_raw_space_decision(
        _report([]), command="scan", input_version="raw-duplicate-assessment/1"
    )
    assert decision["deleted_bytes"] == 0
