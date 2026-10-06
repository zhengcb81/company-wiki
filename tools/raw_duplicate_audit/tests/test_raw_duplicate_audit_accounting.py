"""RED accounting tests: the four duplicate shapes must never be summed alike."""

from __future__ import annotations

from raw_duplicate_audit.classify import Group, Member, account_group, upper_bound_bytes
from raw_duplicate_audit.catalog import LocationRecord

SHA = "a" * 64
SIZE = 1000


def _record(
    location_id: str, relative_path: str, *, source_id: str = "urn:src:1"
) -> LocationRecord:
    return LocationRecord(
        location_id=location_id,
        root_id="root_a",
        relative_path=relative_path,
        absolute_path="",
        source_id=source_id,
        document_id="doc:1",
        role="original_primary",
        location_status="active",
        observed_size=SIZE,
        content_sha256=SHA,
        byte_size=SIZE,
    )


def _member(
    record: LocationRecord,
    *,
    state: str = "ok",
    normalized: str | None = None,
    identity: tuple[int, int] | None = (1, 7),
    allocated: int | None = 1024,
) -> Member:
    return Member(
        record=record,
        path_state=state,
        normalized_path=normalized,
        identity=identity,
        size=SIZE,
        allocated_bytes=allocated,
        hydrate_risk=False,
        observed_mtime_ns=1,
    )


def _group(*members: Member) -> Group:
    return Group(
        group_id="grp:1",
        content_sha256=SHA,
        byte_size=SIZE,
        members=list(members),
    )


def test_same_path_three_location_references_is_not_a_duplicate_copy():
    records = [_record(f"loc:{n}", "same.bin") for n in range(3)]
    group = _group(
        *(_member(r, normalized=r"C:/data/same.bin", identity=(1, 7)) for r in records)
    )

    account = account_group(group)

    assert account["classification"] == "same_path_references"
    assert account["distinct_paths"] == 1
    assert account["distinct_physical_copies"] == 1
    assert account["logical_duplicate_bytes"] == 0
    assert account["reference_counts"]["locations"] == 3
    assert account["reference_counts"]["sources"] == 1


def test_hardlink_two_names_is_one_physical_copy():
    records = [_record("loc:1", "a.bin"), _record("loc:2", "b.bin")]
    group = _group(
        _member(records[0], normalized="C:/data/a.bin", identity=(1, 7)),
        _member(records[1], normalized="C:/data/b.bin", identity=(1, 7)),
    )

    account = account_group(group)

    assert account["classification"] == "shared_physical_file"
    assert account["distinct_paths"] == 2
    assert account["distinct_physical_copies"] == 1
    assert account["logical_duplicate_bytes"] == 0
    assert account["physical_allocated_bytes"] == 0


def test_two_distinct_physical_copies_with_same_content_count_once():
    records = [_record("loc:1", "a.bin"), _record("loc:2", "b.bin")]
    group = _group(
        _member(
            records[0], normalized="C:/data/a.bin", identity=(1, 7), allocated=4096
        ),
        _member(
            records[1], normalized="C:/data/b.bin", identity=(1, 9), allocated=4096
        ),
    )

    account = account_group(group)

    assert account["classification"] == "distinct_physical_copies"
    assert account["distinct_physical_copies"] == 2
    assert account["logical_duplicate_bytes"] == SIZE
    assert account["physical_allocated_bytes"] == 4096
    assert account["certainty"] == "known"


def test_three_distinct_copies_yield_two_redundant_copies():
    records = [_record(f"loc:{n}", f"{n}.bin") for n in range(3)]
    group = _group(
        *(
            _member(r, normalized=f"C:/data/{n}.bin", identity=(1, 100 + n))
            for n, r in enumerate(records)
        )
    )

    account = account_group(group)

    assert account["distinct_physical_copies"] == 3
    assert account["logical_duplicate_bytes"] == 2 * SIZE


def test_same_size_different_bytes_is_not_a_duplicate():
    left = _record("loc:1", "a.bin", source_id="urn:src:1")
    right = LocationRecord(
        location_id="loc:2",
        root_id="root_a",
        relative_path="b.bin",
        absolute_path="",
        source_id="urn:src:2",
        document_id="doc:2",
        role="original_primary",
        location_status="active",
        observed_size=SIZE,
        content_sha256="b" * 64,
        byte_size=SIZE,
    )
    group = Group(
        group_id="grp:2",
        content_sha256=SHA,
        byte_size=SIZE,
        members=[
            _member(left, normalized="C:/data/a.bin", identity=(1, 7)),
            _member(right, normalized="C:/data/b.bin", identity=(1, 9)),
        ],
        similar=True,
    )

    account = account_group(group)

    assert account["classification"] == "similar_size_different_content"
    assert account["logical_duplicate_bytes"] == 0


def test_unknown_physical_identity_is_reported_uncertain_not_pseudo_counted():
    records = [_record("loc:1", "a.bin"), _record("loc:2", "b.bin")]
    group = _group(
        _member(records[0], normalized="C:/data/a.bin", identity=(1, 7)),
        _member(records[1], normalized="C:/data/b.bin", identity=None),
    )

    account = account_group(group)

    assert account["classification"] == "uncertain_physical_identity"
    assert account["certainty"] == "uncertain"
    assert account["logical_duplicate_bytes"] is None
    assert account["distinct_physical_copies"] is None


def test_all_members_missing_is_unresolved_and_contributes_no_bytes():
    records = [_record("loc:1", "a.bin"), _record("loc:2", "b.bin")]
    group = _group(
        _member(records[0], state="missing", normalized=None, identity=None),
        _member(records[1], state="acl_denied", normalized=None, identity=None),
    )

    account = account_group(group)

    assert account["classification"] == "unresolved"
    assert account["certainty"] == "unresolved"
    assert account["logical_duplicate_bytes"] is None
    assert account["unresolved_members"] == 2


def test_partially_resolved_group_counts_only_existing_copies():
    records = [
        _record("loc:1", "a.bin"),
        _record("loc:2", "b.bin"),
        _record("loc:3", "c.bin"),
    ]
    group = _group(
        _member(records[0], normalized="C:/data/a.bin", identity=(1, 7)),
        _member(records[1], normalized="C:/data/b.bin", identity=(1, 9)),
        _member(records[2], state="missing", normalized=None, identity=None),
    )

    account = account_group(group)

    assert account["unresolved_members"] == 1
    assert account["distinct_physical_copies"] == 2
    assert account["logical_duplicate_bytes"] == SIZE


def test_upper_bound_excludes_uncertain_and_unresolved_groups():
    ok = account_group(
        _group(
            _member(
                _record("loc:1", "a.bin"), normalized="C:/data/a.bin", identity=(1, 7)
            ),
            _member(
                _record("loc:2", "b.bin"), normalized="C:/data/b.bin", identity=(1, 9)
            ),
        )
    )
    uncertain = account_group(
        _group(
            _member(
                _record("loc:3", "c.bin"), normalized="C:/data/c.bin", identity=(1, 11)
            ),
            _member(
                _record("loc:4", "d.bin"), normalized="C:/data/d.bin", identity=None
            ),
        )
    )
    unresolved = account_group(
        _group(
            _member(
                _record("loc:5", "e.bin"),
                state="missing",
                normalized=None,
                identity=None,
            ),
            _member(
                _record("loc:6", "f.bin"),
                state="missing",
                normalized=None,
                identity=None,
            ),
        )
    )
    shared = account_group(
        _group(
            _member(
                _record("loc:7", "g.bin"), normalized="C:/data/g.bin", identity=(1, 13)
            ),
            _member(
                _record("loc:8", "h.bin"), normalized="C:/data/h.bin", identity=(1, 13)
            ),
        )
    )

    assert upper_bound_bytes([ok, uncertain, unresolved, shared]) == SIZE
    assert uncertain["logical_duplicate_bytes"] is None
    assert unresolved["logical_duplicate_bytes"] is None


def test_allocation_unknown_makes_physical_allocated_bytes_null():
    group = _group(
        _member(
            _record("loc:1", "a.bin"),
            normalized="C:/data/a.bin",
            identity=(1, 7),
            allocated=None,
        ),
        _member(
            _record("loc:2", "b.bin"),
            normalized="C:/data/b.bin",
            identity=(1, 9),
            allocated=4096,
        ),
    )

    account = account_group(group)

    assert account["logical_duplicate_bytes"] == SIZE
    assert account["physical_allocated_bytes"] is None


def test_reference_counts_keep_source_document_and_location_totals():
    members = [
        _member(
            _record("loc:1", "a.bin", source_id="urn:src:1"), normalized="C:/data/a.bin"
        ),
        _member(
            _record("loc:2", "b.bin", source_id="urn:src:2"), normalized="C:/data/b.bin"
        ),
    ]
    members[1].record = LocationRecord(
        location_id="loc:2",
        root_id="root_a",
        relative_path="b.bin",
        absolute_path="",
        source_id="urn:src:2",
        document_id="doc:2",
        role="original_primary",
        location_status="active",
        observed_size=SIZE,
        content_sha256=SHA,
        byte_size=SIZE,
    )

    account = account_group(_group(*members))

    assert account["reference_counts"] == {
        "sources": 2,
        "versions": 1,
        "documents": 2,
        "locations": 2,
    }
