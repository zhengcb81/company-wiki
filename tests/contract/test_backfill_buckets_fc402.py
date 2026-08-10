"""FC-402 RED/acceptance tests: no-guessing assertion backfill buckets.

Every filing classifies into exactly one of: eligible / needs_review /
unprovable / retired_or_conflict.  Fields may only come from sidecar /
provider metadata / official disclosure / strong identity snapshot — a
file name is at most an evidence hint and NEVER makes a document
capture-ready by itself.  The known 中国平安 / 星环科技-style failing
samples (display-name security_id, missing period proof) must stay fail
closed until evidence is completed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.backfill_v2 import (  # noqa: E402
    classify_bucket,
)


def _acq(**overrides):
    payload = {
        "security_id": "601899",
        "company_name": "Acme",
        "market": "CN",
        "form_type": "annual",
        "document_kind": "annual_report",
        "fiscal_year": 2024,
        "period_end": "2024-12-31",
        "provider": "cninfo",
        "provider_document_id": "doc-1",
        "source_url": "https://example.com/2024.pdf",
        "content_sha256": "a" * 64,
    }
    payload.update(overrides)
    return payload


# --- four-bucket classification --------------------------------------------


def test_eligible_when_all_fields_provable():
    """A document with strong identity + provable period + HTTPS source is
    eligible for capture-ready assertion."""
    bucket, missing = classify_bucket(_acq())
    assert bucket == "eligible"
    assert missing == []


def test_needs_review_when_period_not_provable():
    """Missing period_end (not provable from metadata, never guessed from
    the file name) -> needs_review, not capture-ready."""
    bucket, missing = classify_bucket(_acq(period_end=None))
    assert bucket == "needs_review"
    assert "period_end" in missing


def test_unprovable_when_identity_weak():
    """A display-name security_id (中国平安 style) can never be a strong
    identity -> unprovable until evidence is completed."""
    bucket, missing = classify_bucket(
        _acq(security_id="中国平安", company_name="中国平安")
    )
    assert bucket == "unprovable"
    assert "security_id" in missing


def test_unprovable_when_critical_field_missing():
    bucket, missing = classify_bucket(
        _acq(provider=None, source_url="not-a-url")
    )
    assert bucket == "unprovable"
    assert "provider" in missing or "source_url" in missing


def test_retired_or_conflict_when_source_conflicts():
    """A source whose content hash conflicts with an existing verified
    assertion is retired_or_conflict (never overwrite history)."""
    bucket, missing = classify_bucket(
        _acq(), existing_verified_hash="b" * 64
    )
    assert bucket == "retired_or_conflict"
    assert missing == []


def test_filename_never_makes_capture_ready():
    """A plausible file name (年度报告/年报) without any metadata evidence
    must NOT be eligible — the name is at most an evidence hint."""
    bucket, missing = classify_bucket(
        {
            "document_id": "d1",
            "title": "Acme 2024 年度报告.pdf",
            "security_id": "601899",
            "company_name": "Acme",
            "period_end": "2024-12-31",
            "provider": "cninfo",
            "source_url": "https://example.com/x.pdf",
        },
        evidence_hint_only=True,
    )
    assert bucket == "unprovable"
    assert "content_sha256" in missing


def test_all_documents_classify_into_closed_set():
    """Every combination must land in exactly one of the four buckets."""
    seen = set()
    for case in (
        _acq(),
        _acq(period_end=None),
        _acq(security_id="中国平安", company_name="中国平安"),
        _acq(provider=None),
    ):
        bucket, _ = classify_bucket(case)
        seen.add(bucket)
    assert seen <= {"eligible", "needs_review", "unprovable", "retired_or_conflict"}


def test_weak_identity_without_period_is_unprovable_not_review():
    """Guard isolation: a display-name security_id must be unprovable even
    when period_end is also missing — dropping the weak-identity branch
    would misclassify as needs_review."""
    bucket, missing = classify_bucket(
        _acq(security_id="中国平安", company_name="中国平安", period_end=None)
    )
    assert bucket == "unprovable"
    assert "security_id" in missing


def test_http_source_url_is_unprovable():
    """Guard isolation: a non-HTTPS source URL with every other field
    present must be unprovable, never eligible."""
    bucket, missing = classify_bucket(_acq(source_url="http://example.com/x.pdf"))
    assert bucket == "unprovable"
    assert "source_url" in missing
