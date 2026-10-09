"""Metadata enumeration and original candidate verification have distinct finite budgets."""

import json
import pytest
from helpers.source_fact_fixture import lake, close
from company_wiki.source_catalog.local_inventory import LocalPrepareLimits
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from company_wiki.source_catalog.resolver import SourceRequest


def request():
    return SourceRequest(
        entity="Acme",
        market="US",
        security_id="ACME",
        document_kind="annual_report",
        fiscal_year=2026,
        form_type="10-K",
        as_of_date="2026-10-08",
        mode="exact",
    )


def groups(cat, count):
    base = cat.config.roots[1].path / "ACME/filings"
    base.mkdir(parents=True)
    for i in range(count):
        group = base / f"fil_0000012345-25-{i:06d}"
        group.mkdir()
        (group / "meta.json").write_text(json.dumps({"primary_document": "old.htm"}))
        (group / "old.htm").write_text("old unrelated issuer original")
    # Register nothing: observation below must independently reach discovery.


def test_twenty_six_metadata_groups_do_not_consume_sixteen_raw_candidates(tmp_path):
    cat = lake(tmp_path, portfolio=True)
    try:
        groups(cat, 26)
        # Missing primary is a directory observation, not a candidate original.
        for f in cat.config.roots[1].path.rglob("old.htm"):
            f.unlink()
        result = prepare_local_source(
            cat, request(), limits=LocalPrepareLimits(max_candidates=16)
        )
        assert result["status"] == "not_found" and not result["blocks_download"]
        assert result["download_events"] == 0
    finally:
        close(cat)


def test_metadata_discovery_limit_is_finite_and_distinct(tmp_path):
    cat = lake(tmp_path, portfolio=True)
    try:
        groups(cat, 4)
        result = prepare_local_source(
            cat,
            request(),
            limits=LocalPrepareLimits(max_candidates=16, max_discovery_groups=3),
        )
        assert result["status"] == "unavailable" and result["blocks_download"]
        assert result["reason"] == "local_source_group_limit"
    finally:
        close(cat)


@pytest.mark.parametrize("value", [0, True, 100001])
def test_invalid_discovery_ceiling_is_rejected(value):
    with pytest.raises(ValueError):
        LocalPrepareLimits(max_discovery_groups=value)


def test_discovery_entry_cap_is_not_false_absence(tmp_path):
    cat = lake(tmp_path)
    try:
        base = cat.config.roots[0].path / "Acme"
        base.mkdir()
        for i in range(5):
            (base / f"ignored{i}.log").write_text("not a filing")
        result = prepare_local_source(
            cat, request(), limits=LocalPrepareLimits(max_discovery_entries=3)
        )
        assert result["status"] == "unavailable" and result["blocks_download"]
        assert result["reason"] == "local_discovery_entry_limit"
    finally:
        close(cat)
