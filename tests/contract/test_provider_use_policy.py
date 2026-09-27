"""G1e content-rights decisions on a synthetic provider, never live content."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from company_wiki.source_catalog.acquisition import DownloadCandidate, DownloadReceipt
from company_wiki.source_catalog.authorization import build_download_authorization
from company_wiki.source_catalog.provider_use_policy import (
    ACTIONS,
    ProviderUsePolicy,
    ProviderUsePolicyError,
    authorize_transcript_fetch,
    load_provider_use_policy,
    validate_transcript_fetch_result,
)
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.store import canonical_json


def _payload(*, provider: str = "fixture_provider", host: str = "fixtures.invalid") -> dict:
    value = {
        "schema_version": "provider-use-policy/1",
        "policy_id": "offline-contract-v1",
        "rules": [
            {
                "provider_id": provider,
                "origin_host": host,
                "path_prefix": "/transcripts",
                "content_class": "earnings_call_transcript",
                "rights_evidence_ref": "offline fixture policy only",
                "rights_evidence_sha256": hashlib.sha256(b"fixture-rights").hexdigest(),
                "reviewer": "contract-test",
                "reviewed_at": "2026-09-01",
                "valid_from": "2026-09-01",
                "valid_until": "2026-09-30",
                "permitted_actions": sorted(ACTIONS),
                "retention_scope": "company_wiki_local",
                "export_scope": "stockwiki_readonly_excerpt",
                "revoked": False,
            }
        ],
    }
    value["policy_sha256"] = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return value


def _decide(policy: ProviderUsePolicy, **changes):
    args = {
        "provider_id": "fixture_provider",
        "source_url": "https://fixtures.invalid/transcripts/2026/q2.html",
        "content_class": "earnings_call_transcript",
        "action": "retain_original",
        "on_date": "2026-09-27",
    }
    args.update(changes)
    return policy.decide(**args)


def test_verified_policy_allows_only_scoped_fixture_actions(tmp_path):
    payload = _payload()
    path = tmp_path / "rights.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    policy = load_provider_use_policy(path)
    assert _decide(policy).allowed
    assert _decide(policy, action="derive_text").allowed
    assert _decide(
        policy, action="export_excerpt", export_target="stockwiki_readonly_excerpt"
    ).allowed
    assert not _decide(policy, action="export_excerpt").allowed
    assert not _decide(policy, action="export_excerpt", export_target="public_web").allowed
    assert not _decide(
        policy, source_url="https://fixtures.invalid/transcripts-extra/q2.html"
    ).allowed
    assert not _decide(policy, source_url="https://other.invalid/transcripts/q2.html").allowed
    assert not _decide(
        policy, source_url="https://fixtures.invalid/transcripts/%2e%2e/private"
    ).allowed


def test_policy_load_fails_closed_for_missing_corrupt_or_changed_bytes(tmp_path):
    path = tmp_path / "rights.json"
    with pytest.raises(ProviderUsePolicyError, match="unavailable"):
        load_provider_use_policy(path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ProviderUsePolicyError, match="corrupt"):
        load_provider_use_policy(path)
    payload = _payload()
    payload["rules"][0]["origin_host"] = "changed.invalid"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ProviderUsePolicyError, match="hash mismatch"):
        load_provider_use_policy(path)
    path.write_bytes(b" " * (1024 * 1024 + 1))
    with pytest.raises(ProviderUsePolicyError, match="byte limit"):
        load_provider_use_policy(path)


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"permitted_actions": ["retain_original", "retain_original"]}, "permitted_actions"),
        ({"permitted_actions": [1]}, "permitted_actions"),
        ({"valid_until": "2026-08-31"}, "out of order"),
        ({"origin_host": "fixtures.invalid.evil.com"}, "hash mismatch"),
        ({"revoked": "false"}, "boolean"),
    ],
)
def test_invalid_policy_rule_rejected(change, error):
    payload = deepcopy(_payload())
    payload["rules"][0].update(change)
    if error != "hash mismatch":
        payload["policy_sha256"] = hashlib.sha256(
            canonical_json({key: value for key, value in payload.items() if key != "policy_sha256"}).encode("utf-8")
        ).hexdigest()
    with pytest.raises(ProviderUsePolicyError, match=error):
        ProviderUsePolicy.from_dict(payload)


def test_revocation_expiry_and_overlapping_rules_deny():
    payload = _payload()
    policy = ProviderUsePolicy.from_dict(payload)
    assert _decide(policy, on_date="2026-10-01").reason == "rule_inactive"
    assert _decide(policy, action="unknown_action").reason == "unknown_action"

    payload["rules"][0]["revoked"] = True
    payload["policy_sha256"] = hashlib.sha256(
        canonical_json({key: value for key, value in payload.items() if key != "policy_sha256"}).encode("utf-8")
    ).hexdigest()
    assert _decide(ProviderUsePolicy.from_dict(payload)).reason == "rule_inactive"

    payload = _payload()
    overlapping = deepcopy(payload["rules"][0])
    overlapping["path_prefix"] = "/transcripts/2026"
    payload["rules"].append(overlapping)
    payload["policy_sha256"] = hashlib.sha256(
        canonical_json({key: value for key, value in payload.items() if key != "policy_sha256"}).encode("utf-8")
    ).hexdigest()
    assert _decide(ProviderUsePolicy.from_dict(payload)).reason == "missing_or_ambiguous_rule"


@pytest.mark.parametrize("host", ["www.fool.com", "seekingalpha.com", "sub.seekingalpha.com"])
def test_site_prohibitions_cannot_be_overridden_by_local_policy(host):
    payload = _payload(provider="fixture_provider", host=host)
    policy = ProviderUsePolicy.from_dict(payload)
    decision = _decide(policy, source_url=f"https://{host}/transcripts/x")
    assert not decision.allowed
    assert decision.reason == "provider_site_automation_blocked"


def _fetch_inputs():
    request = SourceRequest(
        entity="Acme Inc.",
        market="US",
        security_id="ACME",
        document_kind="investor_call_transcript",
        fiscal_year=2026,
        fiscal_period="Q2",
        as_of_date="2026-09-27",
        allow_download=True,
    )
    candidate = DownloadCandidate(
        candidate_id="fixture-provider-doc-1",
        provider="fixture_provider",
        provider_document_id="doc-1",
        market="US",
        entity="Acme Inc.",
        title="Acme 2026 Q2 Earnings Call",
        source_url="https://fixtures.invalid/transcripts/2026/q2.html",
        document_kind="investor_call_transcript",
        filing_date="2026-09-20",
        fiscal_year=2026,
        fiscal_period="Q2",
        remote_size=100,
        adapter_payload_json=json.dumps({"market": "US", "security_id": "ACME"}),
    )
    authorization = build_download_authorization(
        request_id=request.request_id,
        gap_plan_hash="a" * 64,
        policy_hash="b" * 64,
        provider="fixture_provider",
        allowed_accessions=("doc-1",),
        max_items=1,
        max_bytes=100,
        expires_at="2026-09-27T23:00:00Z",
    )
    return {
        "request": request,
        "candidate": candidate,
        "authorization": authorization,
        "plan_hash": "a" * 64,
        "runtime_policy_hash": "b" * 64,
        "rights_policy": ProviderUsePolicy.from_dict(_payload()),
        "now": "2026-09-27T12:00:00Z",
    }


def test_prefetch_admission_reuses_exact_download_authorization():
    inputs = _fetch_inputs()
    allowed = authorize_transcript_fetch(**inputs)
    assert allowed.allowed
    assert allowed.rights_policy_sha256 == inputs["rights_policy"].policy_sha256
    assert allowed.download_authorization_hash == inputs["authorization"].receipt_hash
    assert allowed.request_id == inputs["request"].request_id
    assert allowed.candidate_id == inputs["candidate"].candidate_id

    assert not authorize_transcript_fetch(**{**inputs, "rights_policy": None}).allowed
    assert not authorize_transcript_fetch(**{**inputs, "plan_hash": "c" * 64}).allowed
    assert not authorize_transcript_fetch(**{**inputs, "runtime_policy_hash": "c" * 64}).allowed
    assert not authorize_transcript_fetch(**{**inputs, "now": "2026-09-28T00:00:00Z"}).allowed


def test_prefetch_admission_rejects_download_authorization_for_another_request():
    inputs = _fetch_inputs()
    authorization = build_download_authorization(
        request_id="urn:company-wiki:source-request:sha256:" + "c" * 64,
        gap_plan_hash=inputs["plan_hash"],
        policy_hash=inputs["runtime_policy_hash"],
        provider=inputs["candidate"].provider,
        allowed_accessions=(inputs["candidate"].provider_document_id,),
        max_items=1,
        max_bytes=inputs["authorization"].max_bytes,
        expires_at=inputs["authorization"].expires_at,
    )
    decision = authorize_transcript_fetch(**{**inputs, "authorization": authorization})
    assert not decision.allowed
    assert decision.reason == "authorization_request_mismatch"


def test_transcript_candidate_without_content_length_uses_authorized_stream_cap():
    inputs = _fetch_inputs()
    candidate = DownloadCandidate(
        **{**inputs["candidate"].to_dict(), "remote_size": None}
    )
    decision = authorize_transcript_fetch(**{**inputs, "candidate": candidate})
    assert decision.allowed


def test_prefetch_admission_rejects_identity_drift_and_site_block():
    inputs = _fetch_inputs()
    bad_candidate = DownloadCandidate(
        **{
            **inputs["candidate"].to_dict(),
            "adapter_payload_json": json.dumps({"market": "US", "security_id": "OTHER"}),
        }
    )
    decision = authorize_transcript_fetch(**{**inputs, "candidate": bad_candidate})
    assert decision.reason == "candidate_security_identity_missing"

    blocked_candidate = DownloadCandidate(
        **{
            **inputs["candidate"].to_dict(),
            "source_url": "https://www.fool.com/transcripts/2026/q2.html",
        }
    )
    blocked_policy = ProviderUsePolicy.from_dict(
        _payload(provider="fixture_provider", host="www.fool.com")
    )
    decision = authorize_transcript_fetch(
        **{**inputs, "candidate": blocked_candidate, "rights_policy": blocked_policy}
    )
    assert decision.reason == "provider_rights_provider_site_automation_blocked"


def _postfetch_inputs(tmp_path):
    inputs = _fetch_inputs()
    policy = inputs.pop("rights_policy")
    staging_root = tmp_path / "staging"
    staging_root.mkdir()
    body = (
        b"<html><body><p>Acme 2026Q2</p>"
        b"<p>CEO: Overseas growth.</p></body></html>"
    )
    staged_path = staging_root / "transcript.html"
    staged_path.write_bytes(body)
    receipt = DownloadReceipt(
        candidate_id=inputs["candidate"].candidate_id,
        provider=inputs["candidate"].provider,
        provider_document_id=inputs["candidate"].provider_document_id,
        source_url=inputs["candidate"].source_url,
        staged_path=str(staged_path),
        content_sha256=hashlib.sha256(body).hexdigest(),
        byte_size=len(body),
        mime_type="text/html",
        retrieved_at=inputs["now"],
        http_status=200,
        adapter_name="fixture-adapter",
        adapter_version="1.0.0",
    )
    return {
        **inputs,
        "receipt": receipt,
        "pinned_rights_policy_sha256": policy.policy_sha256,
        "current_rights_policy": policy,
        "final_url": inputs["candidate"].source_url,
        "staging_root": staging_root,
    }


def test_postfetch_validation_checks_fresh_rights_identity_and_bytes(tmp_path):
    inputs = _postfetch_inputs(tmp_path)
    valid = validate_transcript_fetch_result(**inputs)
    assert valid.allowed
    assert valid.content_sha256 == inputs["receipt"].content_sha256
    assert valid.final_url == inputs["final_url"]
    assert valid.mime_type == "text/html"
    assert valid.byte_size == inputs["receipt"].byte_size

    changed_payload = _payload()
    changed_payload["policy_id"] = "changed-policy"
    changed_payload["policy_sha256"] = hashlib.sha256(
        canonical_json(
            {key: value for key, value in changed_payload.items() if key != "policy_sha256"}
        ).encode("utf-8")
    ).hexdigest()
    changed_policy = ProviderUsePolicy.from_dict(changed_payload)
    changed = validate_transcript_fetch_result(
        **{**inputs, "current_rights_policy": changed_policy}
    )
    assert changed.reason == "provider_use_policy_changed_during_fetch"

    redirected = validate_transcript_fetch_result(
        **{**inputs, "final_url": "https://other.invalid/transcripts/2026/q2.html"}
    )
    assert redirected.reason.startswith("final_url_rights_automated_fetch_")

    blocked_redirect = validate_transcript_fetch_result(
        **{**inputs, "final_url": "https://www.fool.com/transcripts/2026/q2.html"}
    )
    assert blocked_redirect.reason.endswith("provider_site_automation_blocked")


@pytest.mark.parametrize(
    ("change", "expected_reason"),
    [
        ("tamper_bytes", "staged_file_sha256_mismatch"),
        ("too_many_bytes", "downloaded_bytes_exceed_authorized_cap"),
        ("wrong_provider_document", "download_receipt_identity_mismatch"),
        ("wrong_mime", "unsupported_transcript_mime_type"),
        ("outside_staging", "staged_file_outside_allocated_root"),
    ],
)
def test_postfetch_validation_rejects_untrusted_response(tmp_path, change, expected_reason):
    inputs = _postfetch_inputs(tmp_path)
    if change == "tamper_bytes":
        staged = Path(inputs["receipt"].staged_path)
        staged.write_bytes(b"x" * inputs["receipt"].byte_size)
    elif change == "too_many_bytes":
        over_cap = b"x" * (inputs["authorization"].max_bytes + 1)
        path = Path(inputs["receipt"].staged_path)
        path.write_bytes(over_cap)
        inputs["receipt"] = DownloadReceipt(
            **{
                **inputs["receipt"].to_dict(),
                "content_sha256": hashlib.sha256(over_cap).hexdigest(),
                "byte_size": len(over_cap),
            }
        )
    elif change == "wrong_provider_document":
        inputs["receipt"] = DownloadReceipt(
            **{**inputs["receipt"].to_dict(), "provider_document_id": "other-doc"}
        )
    elif change == "wrong_mime":
        inputs["receipt"] = DownloadReceipt(
            **{**inputs["receipt"].to_dict(), "mime_type": "application/pdf"}
        )
    else:
        outside = tmp_path / "outside.html"
        outside.write_bytes(Path(inputs["receipt"].staged_path).read_bytes())
        inputs["receipt"] = DownloadReceipt(
            **{**inputs["receipt"].to_dict(), "staged_path": str(outside)}
        )
    result = validate_transcript_fetch_result(**inputs)
    assert not result.allowed
    assert result.reason == expected_reason
