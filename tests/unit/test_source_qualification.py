"""Publication time and byte availability are independent observations."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "published,status,date_eligible",
    [
        (None, "unknown", False),
        ("", "unknown", False),
        ("2026-10-07", "eligible", True),
        ("2026-10-08", "eligible", True),
        ("2026-10-09", "after_as_of", False),
        ("2026-02-30", "invalid", False),
        ("20261007", "invalid", False),
        ("2026-10-07T00:00:00Z", "invalid", False),
        (True, "invalid", False),
        (20261007, "invalid", False),
    ],
)
def test_publication_cutoff_is_exact_and_never_guessed(published, status, date_eligible):
    from company_wiki.source_catalog.qualification import qualify_source

    result = qualify_source(published, as_of_date="2026-10-08")
    assert result.publication_status == status
    assert result.historical_date_eligible is date_eligible
    assert result.local_bytes_status == "not_checked"
    assert result.historical_reuse_eligible is (None if date_eligible else False)


@pytest.mark.parametrize("availability,eligible", [
    ("not_checked", None), ("verified", True), ("unavailable", False),
])
def test_indexed_does_not_mean_bytes_were_verified(availability, eligible):
    from company_wiki.source_catalog.qualification import qualify_source

    result = qualify_source("2026-10-01", as_of_date="2026-10-08",
                            local_bytes_status=availability)
    assert result.historical_reuse_eligible is eligible
    assert result.to_dict()["schema_version"] == "source-qualification/1"


def test_current_read_does_not_invent_a_historical_cutoff():
    from company_wiki.source_catalog.qualification import qualify_source

    for published, status in [(None, "unknown"), ("2026-10-01", "known")]:
        result = qualify_source(published, as_of_date=None, local_bytes_status="verified")
        assert result.publication_status == status
        assert result.historical_date_eligible is None
        assert result.historical_reuse_eligible is None


@pytest.mark.parametrize("as_of", ["", "20261008", "2026-02-30", True, 20261008])
def test_bad_cutoff_is_a_request_error(as_of):
    from company_wiki.source_catalog.qualification import qualify_source

    with pytest.raises(ValueError):
        qualify_source("2026-10-01", as_of_date=as_of)


@pytest.mark.parametrize("availability", ["exists", "indexed", True, None])
def test_unknown_availability_is_not_a_byte_receipt(availability):
    from company_wiki.source_catalog.qualification import qualify_source

    with pytest.raises(ValueError):
        qualify_source(None, as_of_date=None, local_bytes_status=availability)


@pytest.mark.parametrize("basis", ["prior_verified_capture", "current_verified_open", "primary_archive"])
def test_unknown_publication_uses_bound_availability_without_inventing_a_date(basis):
    from company_wiki.source_catalog.qualification import qualify_source

    sha = "a" * 64
    proof = {"schema_version": "source-availability-evidence/1", "source_sha256": sha,
             "available_by": "2026-10-08", "basis": basis,
             "evidence_ref": "source-provenance:example:observation", "locator": "/verified_at"}
    result = qualify_source(None, as_of_date="2026-10-08", local_bytes_status="verified",
                            availability_evidence=proof, source_sha256=sha)
    assert result.publication_status == "unknown"
    assert result.historical_date_eligible is True and result.historical_reuse_eligible is True
    assert not qualify_source(None, as_of_date="2026-10-07", local_bytes_status="verified",
                              availability_evidence=proof, source_sha256=sha).historical_date_eligible
    assert not qualify_source("2026-10-09", as_of_date="2026-10-08", local_bytes_status="verified",
                              availability_evidence=proof, source_sha256=sha).historical_date_eligible
    assert not qualify_source(None, as_of_date="2026-10-08", local_bytes_status="verified",
                              availability_evidence=proof, source_sha256="b" * 64).historical_date_eligible


@pytest.mark.parametrize("field,value", [("basis", "mtime"), ("available_by", "2026-99-08"),
                                        ("evidence_ref", ""), ("locator", "")])
def test_availability_labels_without_byte_bound_proof_do_not_qualify(field, value):
    from company_wiki.source_catalog.qualification import qualify_source
    proof = {"schema_version": "source-availability-evidence/1", "source_sha256": "a" * 64,
             "available_by": "2026-10-08", "basis": "prior_verified_capture",
             "evidence_ref": "source-provenance:example", "locator": "/receipt"}
    proof[field] = value
    assert not qualify_source(None, as_of_date="2026-10-08", local_bytes_status="verified",
                              availability_evidence=proof, source_sha256="a" * 64).historical_date_eligible


def test_latest_fiscal_scope_does_not_sort_by_availability_or_old_report_republication():
    from company_wiki.source_catalog.qualification import latest_source_index
    versions = [{"fiscal_year": 2025, "fiscal_period": "H1", "scope_verified": True,
                 "published_date": "2026-10-07", "source_id": "old"},
                {"fiscal_year": 2026, "fiscal_period": "H1", "scope_verified": True,
                 "published_date": None, "available_by": "2026-10-08", "source_id": "new"}]
    assert latest_source_index(versions) == 1
    versions.append({**versions[1], "source_id": "unknown-revision", "available_by": "2026-10-09"})
    assert latest_source_index(versions) is None
    # Existing fully dated legacy consumers retain their prior election.
    assert latest_source_index([{"published_date": "2026-10-07"}, {"published_date": "2026-10-08"}]) == 1
