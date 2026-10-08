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
