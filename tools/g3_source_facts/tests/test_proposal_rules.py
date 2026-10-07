"""Counter-examples that fence the G3 metadata proposal rules (card section 4).

Every test here encodes a *refusal*, not a happy path: a proposal must be
downgraded, blocked or reported as unknown when its evidence is weak.
"""

from __future__ import annotations

import pytest

from g3_source_facts.proposals import (
    ACTIONS,
    Evidence,
    ProposalItem,
    build_item_report,
)


def _item(**overrides) -> ProposalItem:
    base = dict(
        sample_id="S01",
        source_id="urn:company-wiki:source:sha256:" + "a" * 64,
        document_id="urn:company-wiki:document:sha256:" + "a" * 64,
        source_version_id=None,
        location_id="urn:company-wiki:location:sha256:" + "b" * 64,
        registered=True,
        content_sha256="d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5",
        registered_content_sha256=(
            "d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5"
        ),
        retired=False,
        retired_reason=None,
        restore_record=False,
        superseded=False,
        current={},
        proposed={},
        evidence=[],
    )
    base.update(overrides)
    return ProposalItem(**base)


def _published_evidence(locator: str, value: str, status: str = "verified"):
    official = locator.casefold().startswith(
        ("cninfo:", "sse:", "szse:", "sec:", "ir:")
    )
    return Evidence(
        field="published_date",
        url="https://example.invalid/announcement" if official else None,
        locator=locator,
        observed_value=value,
        status=status,
    )


# --- counter-example 1: a date inferred from the file name is never verified ---


def test_filename_derived_published_date_must_be_unverified():
    item = _item(
        evidence=[
            _published_evidence("filename:中微公司：2025年年度报告.pdf", "2025-04-25")
        ],
        proposed={"published_date": "2025-04-25"},
    )
    report = build_item_report(item)
    published = [e for e in report.evidence if e["field"] == "published_date"]
    assert published and published[0]["status"] == "unverified"
    assert report.action == "unresolved"
    assert any(
        p["code"] == "published_date_lacks_verified_evidence" for p in report.problems
    )


def test_filename_locator_is_classified_as_filename_basis():
    item = _item(evidence=[_published_evidence("filename:x.pdf", "2025-01-01")])
    report = build_item_report(item)
    assert report.evidence[0]["status"] == "unverified"


# --- counter-example 2: an activity date is not a publication date ---


def test_activity_date_cannot_become_published_date():
    activity = Evidence(
        field="activity_date",
        url=None,
        locator="activity:2023-06-26/2023-06-28",
        observed_value="2023-06-26",
        status="verified",
    )
    item = _item(
        sample_id="S08",
        current={"published_date": "2023-12-31"},
        evidence=[activity],
        proposed={"published_date": "2023-06-26"},
    )
    report = build_item_report(item)
    assert report.action == "unresolved"
    assert any(c["code"] == "activity_date_vs_published_date" for c in report.conflicts)
    assert any(
        p["code"] == "activity_date_cannot_be_published_date" for p in report.problems
    )


# --- counter-example 3: a digest mismatch forbids a verified recommendation ---


def test_content_sha_mismatch_forbids_verified_and_no_change():
    item = _item(
        content_sha256="f" * 64,
        registered_content_sha256="d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5",
        evidence=[_published_evidence("cninfo:announcementId=1", "2026-04-25")],
        proposed={"published_date": "2026-04-25"},
    )
    report = build_item_report(item)
    assert report.action == "unresolved"
    assert all(e["status"] != "verified" for e in report.evidence)
    assert any(c["code"] == "content_sha256_mismatch" for c in report.conflicts)


# --- counter-example 4: an unknown retirement reason never yields an active state ---


@pytest.mark.parametrize("reason", [None, ""])
def test_unknown_retired_reason_never_suggests_active(reason):
    item = _item(
        retired=True, retired_reason=reason, proposed={"document_kind": "annual_report"}
    )
    report = build_item_report(item)
    assert report.action in {"do_not_reactivate", "unresolved"}
    assert report.action not in {"no_change", "update_metadata", "register_new"}


def test_known_retired_reason_without_restore_record_stays_do_not_reactivate():
    item = _item(
        retired=True,
        retired_reason="legacy sidecar lacks source_url; batch governance Phase 15.6 (F13)",
        proposed={"security_id": "688012"},
        evidence=[
            Evidence(
                field="security_id",
                url="https://www.cninfo.com.cn/new/data/szse_stock.json",
                locator="security_master:cn/688012",
                observed_value="688012",
                status="verified",
            )
        ],
    )
    report = build_item_report(item)
    assert report.action == "do_not_reactivate"
    assert report.retired_reason.startswith("legacy sidecar")


# --- counter-example 5: two conflicting official records stay a conflict ---


def test_two_conflicting_official_records_stay_conflict_and_unresolved():
    first = _published_evidence("cninfo:announcementId=1", "2026-04-25")
    second = _published_evidence("sse:announcementId=2", "2026-04-27")
    item = _item(evidence=[first, second], proposed={"published_date": "2026-04-25"})
    report = build_item_report(item)
    assert report.action == "unresolved"
    assert any(c["code"] == "official_records_conflict" for c in report.conflicts)
    statuses = {e["status"] for e in report.evidence if e["field"] == "published_date"}
    assert statuses == {"conflict"}


# --- counter-example 6: a sample / fixture id is never a production id ---


@pytest.mark.parametrize(
    "field", ["source_id", "document_id", "location_id", "source_version_id"]
)
def test_sample_id_cannot_be_used_as_production_id(field):
    item = _item(**{field: "S07"})
    report = build_item_report(item)
    assert report.action == "unresolved"
    assert any(p["code"] == "sample_id_used_as_production_id" for p in report.problems)


def test_fixture_alias_prefix_is_rejected_as_production_id():
    item = _item(document_id="P01")
    report = build_item_report(item)
    assert report.action == "unresolved"
    assert any(p["code"] == "sample_id_used_as_production_id" for p in report.problems)


def test_urn_ids_are_accepted_as_production_ids():
    report = build_item_report(_item(proposed={"security_id": "688012"}))
    assert report.action == "update_metadata"


# --- report shape: no action outside the closed vocabulary ---


def test_action_vocabulary_is_closed():
    report = build_item_report(_item())
    assert report.action in ACTIONS


def test_no_change_when_proposed_equals_current():
    report = build_item_report(
        _item(
            current={"document_kind": "annual_report"},
            proposed={"document_kind": "annual_report"},
        )
    )
    assert report.action == "no_change"
    assert report.problems == []


def test_register_new_requires_an_unregistered_sample():
    registered = build_item_report(_item(proposed={"document_kind": "annual_report"}))
    assert registered.action == "update_metadata"
    unregistered = build_item_report(
        _item(
            registered=False,
            source_id=None,
            document_id=None,
            location_id=None,
            current={},
            proposed={"document_kind": "investor_call_transcript"},
        )
    )
    assert unregistered.action == "register_new"


def test_missing_date_stays_unknown_and_never_ready():
    item = _item(
        evidence=[
            Evidence(
                field="published_date",
                url=None,
                locator="catalog:documents.published_date",
                observed_value=None,
                status="unknown",
            )
        ]
    )
    report = build_item_report(item)
    assert all(
        e["status"] in {"unknown", "conflict", "unverified"} for e in report.evidence
    )
    assert report.action in {"no_change", "unresolved"}


def test_evidence_record_exposes_exactly_the_five_contract_keys():
    item = _item(
        evidence=[_published_evidence("cninfo:announcementId=9", "2026-04-25")]
    )
    report = build_item_report(item)
    assert set(report.evidence[0]) == {
        "field",
        "url",
        "locator",
        "observed_value",
        "status",
    }
