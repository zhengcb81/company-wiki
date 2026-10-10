"""Read-only verification across the sealed 86-page official JSON run.

No catalog, no writes, no network: the sealed directory is only read.  The
anchors (byte totals, per-stream pagination, identity distribution, the four
representative page hashes) come from JSON_EVIDENCE_INDEX.json.
"""

from pathlib import Path
import hashlib

import pytest

from company_wiki.source_catalog.official_json_layout import describe_layout_page
from company_wiki.source_catalog.official_json_structure import (
    JsonStructureLimits,
    parse_json_structure,
)

import os

_RUN_HOME = (
    Path.home() / "Projects" / "revenue-forecast-audit"
    / "runs" / "m3-20261009T184946-cn-688012")
SEALED_RUN = Path(os.environ.get("M3_SEALED_RUN", str(_RUN_HOME)))
SEALED_SOURCES = SEALED_RUN / "execution/sources"
SEALED_AVAILABLE = SEALED_SOURCES.is_dir()
requires_sealed = pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")

TARGET_ACTIVITY_COMPANY_ID = 57790
TARGET_COMPANY_ID = 145565
TARGET_STOCK_CODE = "688012"


def _form_pages(prefix: str) -> list[Path]:
    return sorted(SEALED_SOURCES.glob(f"{prefix}-form-*.raw"))


@requires_sealed
@pytest.mark.parametrize("prefix,pages,records,total", [
    ("qa-latest", 65, 195, 195),
    ("qa-questions", 11, 33, 33),
    ("qa-precollect", 10, 29, 29),
])
def test_stream_pages_parse_with_declared_layout_and_stable_counts(
        prefix, pages, records, total):
    page_files = _form_pages(prefix)
    assert len(page_files) == pages
    seen_records = 0
    seen_ids: set[int] = set()
    currents: set[int] = set()
    declared_pages = None
    declared_total = None
    byte_sum = 0
    for path in page_files:
        raw = path.read_bytes()
        byte_sum += len(raw)
        doc = parse_json_structure(raw, limits=JsonStructureLimits())
        observation = describe_layout_page("official-paged-qa", doc)
        assert observation.envelope_status == "ok"
        assert observation.business_evidence is True
        assert observation.pagination["total"] == total
        assert observation.pagination["size"] == 3
        assert observation.pagination["pages"] == pages
        currents.add(observation.pagination["current"])
        declared_pages = observation.pagination["pages"]
        declared_total = observation.pagination["total"]
        for record in observation.records:
            assert record.provider_record_id is not None
            assert record.provider_record_id not in seen_ids
            seen_ids.add(record.provider_record_id)
            seen_records += 1
    assert seen_records == records == total
    assert currents == set(range(1, pages + 1))
    assert declared_pages == pages and declared_total == total


@requires_sealed
def test_all_86_pages_byte_total_and_identity_distribution():
    byte_sum = 0
    target = 0
    other = 0
    unattributed = 0
    for prefix in ("qa-latest", "qa-questions", "qa-precollect"):
        for path in _form_pages(prefix):
            raw = path.read_bytes()
            byte_sum += len(raw)
            doc = parse_json_structure(raw, limits=JsonStructureLimits())
            observation = describe_layout_page("official-paged-qa", doc)
            for record in observation.records:
                observed = record.issuer_observed
                activity_ids = observed.get("provider_company_ids") or []
                is_target = (
                    TARGET_ACTIVITY_COMPANY_ID in activity_ids
                    or observed.get("provider_company_id") == TARGET_COMPANY_ID
                    or observed.get("stock_code") == TARGET_STOCK_CODE
                )
                if is_target:
                    target += 1
                elif record.attributed:
                    other += 1
                else:
                    unattributed += 1
    assert byte_sum == 668749
    assert target == 24
    assert other == 231
    assert unattributed == 2


@requires_sealed
@pytest.mark.parametrize("name,sha,size", [
    ("qa-latest-form-01.raw",
     "416542b0c8f72400800edf69832df1bd3b48e50cf19c0019c647af445b97760b", 5119),
    ("qa-latest-form-18.raw",
     "fc1c2a8ebb7cb44b3cf6f82a5ecfa5641cf81478ed35e615c0928f36a2a389fe", 7316),
    ("qa-questions-form-01.raw",
     "509bcbcdde98e1ac46464453ed1a7a339134107b67fb5370269639e8192bb2e0", 5925),
    ("qa-precollect-form-10.raw",
     "784217fbfdddc06cd53235b3bef8159250b1d4209761092577d35ebb0f313234", 3871),
])
def test_four_representative_pages_keep_their_exact_bytes(name, sha, size):
    raw = (SEALED_SOURCES / name).read_bytes()
    assert len(raw) == size
    assert hashlib.sha256(raw).hexdigest() == sha


@requires_sealed
@pytest.mark.parametrize("name", [
    "qa-latest-01.raw", "qa-questions-01.raw", "qa-precollect-01.raw",
])
def test_error_payload_controls_stay_non_business(name):
    raw = (SEALED_SOURCES / name).read_bytes()
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    observation = describe_layout_page("official-paged-qa", doc)
    assert observation.envelope_status == "response_is_error"
    assert observation.business_evidence is False
    assert observation.records == ()


@requires_sealed
def test_precollect_36395_answer_and_question_replay_from_the_frozen_page():
    raw = (SEALED_SOURCES / "qa-precollect-form-10.raw").read_bytes()
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    observation = describe_layout_page("official-paged-qa", doc)
    record = next(item for item in observation.records
                  if item.provider_record_id == 36395)
    assert record.issuer_observed["provider_company_id"] == TARGET_COMPANY_ID
    assert record.issuer_observed["stock_code"] == TARGET_STOCK_CODE
    assert "answer" in record.text_fields
    # No speaker field exists on the frozen record; nothing may invent one.
    assert "speaker" not in {name for name in record.times}
    assert record.times["crtTime"] == "2026-09-04 18:55:49"
    assert record.times["updTime"] == "2026-09-10 15:19:54"


@requires_sealed
def test_documented_wrong_pointer_stays_the_other_company():
    """latest-01 /datas/0/records/2 is 清溢 (2508409), never 中微 (2508385)."""
    raw = (SEALED_SOURCES / "qa-latest-form-01.raw").read_bytes()
    doc = parse_json_structure(raw, limits=JsonStructureLimits())
    observation = describe_layout_page("official-paged-qa", doc)
    record = observation.records[2]
    assert record.provider_record_id == 2508409
    assert record.issuer_observed["provider_activity_company_id"] == 57808
    assert record.issuer_observed["provider_company_id"] == 152341
    assert TARGET_ACTIVITY_COMPANY_ID not in (
        record.issuer_observed["provider_company_ids"] or [])
