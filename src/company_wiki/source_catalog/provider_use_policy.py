"""Fail-closed, read-only provider content-use policy for G1e sources.

This is an additional rights layer. It does not replace the existing exact
candidate DownloadAuthorization or user download authorization. No policy file
is installed by this module, so production callers have no implicit grants.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
import stat
from typing import Any, Mapping
from urllib.parse import unquote, urlsplit

from .acquisition import DownloadCandidate, DownloadReceipt
from .authorization import DownloadAuthorization, validate_download_authorization
from .resolver import SourceRequest
from .store import canonical_json


PROVIDER_USE_POLICY_SCHEMA = "provider-use-policy/1"
ACTIONS = frozenset(
    {
        "discover_metadata",
        "automated_fetch",
        "retain_original",
        "derive_text",
        "select_evidence",
        "generate_summary",
        "export_excerpt",
    }
)
_PROVIDER = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HOST = re.compile(r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$")
_POLICY_KEYS = frozenset({"schema_version", "policy_id", "rules", "policy_sha256"})
_RULE_KEYS = frozenset(
    {
        "provider_id",
        "origin_host",
        "path_prefix",
        "content_class",
        "rights_evidence_ref",
        "rights_evidence_sha256",
        "reviewer",
        "reviewed_at",
        "valid_from",
        "valid_until",
        "permitted_actions",
        "retention_scope",
        "export_scope",
        "revoked",
    }
)
# Current site terms prohibit automated harvesting. A future written license
# requires a reviewed code/policy change; a local JSON edit cannot lift this.
_BLOCKED_SITE_PROVIDERS = frozenset({"motley_fool", "seeking_alpha"})
_BLOCKED_SITE_HOSTS = frozenset({"fool.com", "seekingalpha.com"})


class ProviderUsePolicyError(ValueError):
    """The rights policy is missing, corrupt, ambiguous, or untrusted."""


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProviderUsePolicyError(f"{name} must be non-empty trimmed text")
    return value


def _date(value: Any, name: str) -> date:
    if not isinstance(value, str):
        raise ProviderUsePolicyError(f"{name} must be canonical YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ProviderUsePolicyError(f"{name} must be canonical YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ProviderUsePolicyError(f"{name} must be canonical YYYY-MM-DD")
    return parsed


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ProviderUsePolicyError(f"{name} must be lowercase SHA-256")
    return value


@dataclass(frozen=True)
class ProviderUseRule:
    provider_id: str
    origin_host: str
    path_prefix: str
    content_class: str
    rights_evidence_ref: str
    rights_evidence_sha256: str
    reviewer: str
    reviewed_at: str
    valid_from: str
    valid_until: str
    permitted_actions: frozenset[str]
    retention_scope: str
    export_scope: str
    revoked: bool

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProviderUseRule":
        if not isinstance(value, Mapping) or set(value) != _RULE_KEYS:
            raise ProviderUsePolicyError("provider use rule fields differ from schema")
        provider_id = _text(value["provider_id"], "provider_id")
        if not _PROVIDER.fullmatch(provider_id):
            raise ProviderUsePolicyError("invalid provider_id")
        host = _text(value["origin_host"], "origin_host")
        if host != host.lower() or not _HOST.fullmatch(host) or ".." in host:
            raise ProviderUsePolicyError("invalid origin_host")
        prefix = _text(value["path_prefix"], "path_prefix")
        if not prefix.startswith("/") or "//" in prefix or ".." in prefix or "?" in prefix or "#" in prefix:
            raise ProviderUsePolicyError("invalid path_prefix")
        content_class = _text(value["content_class"], "content_class")
        evidence_ref = _text(value["rights_evidence_ref"], "rights_evidence_ref")
        evidence_sha = _sha(value["rights_evidence_sha256"], "rights_evidence_sha256")
        reviewer = _text(value["reviewer"], "reviewer")
        reviewed = _date(value["reviewed_at"], "reviewed_at")
        valid_from = _date(value["valid_from"], "valid_from")
        valid_until = _date(value["valid_until"], "valid_until")
        if not reviewed <= valid_from <= valid_until:
            raise ProviderUsePolicyError("provider use rule dates are out of order")
        actions = value["permitted_actions"]
        if not isinstance(actions, list) or not all(isinstance(item, str) for item in actions):
            raise ProviderUsePolicyError("invalid permitted_actions")
        if len(actions) != len(set(actions)) or not set(actions) <= ACTIONS:
            raise ProviderUsePolicyError("invalid permitted_actions")
        if type(value["revoked"]) is not bool:
            raise ProviderUsePolicyError("revoked must be boolean")
        return cls(
            provider_id=provider_id,
            origin_host=host,
            path_prefix=prefix,
            content_class=content_class,
            rights_evidence_ref=evidence_ref,
            rights_evidence_sha256=evidence_sha,
            reviewer=reviewer,
            reviewed_at=reviewed.isoformat(),
            valid_from=valid_from.isoformat(),
            valid_until=valid_until.isoformat(),
            permitted_actions=frozenset(actions),
            retention_scope=_text(value["retention_scope"], "retention_scope"),
            export_scope=_text(value["export_scope"], "export_scope"),
            revoked=value["revoked"],
        )


@dataclass(frozen=True)
class ProviderUseDecision:
    allowed: bool
    reason: str
    policy_id: str
    policy_sha256: str
    rule_evidence_sha256: str | None = None


@dataclass(frozen=True)
class ProviderUsePolicy:
    policy_id: str
    policy_sha256: str
    rules: tuple[ProviderUseRule, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProviderUsePolicy":
        if not isinstance(value, Mapping) or set(value) != _POLICY_KEYS:
            raise ProviderUsePolicyError("provider use policy fields differ from schema")
        if value["schema_version"] != PROVIDER_USE_POLICY_SCHEMA:
            raise ProviderUsePolicyError("unsupported provider use policy schema")
        policy_id = _text(value["policy_id"], "policy_id")
        rules_input = value["rules"]
        if not isinstance(rules_input, list) or len(rules_input) > 1000:
            raise ProviderUsePolicyError("rules must be a bounded list")
        declared = _sha(value["policy_sha256"], "policy_sha256")
        try:
            computed = hashlib.sha256(
                canonical_json({key: val for key, val in value.items() if key != "policy_sha256"}).encode("utf-8")
            ).hexdigest()
        except (TypeError, ValueError) as exc:
            raise ProviderUsePolicyError("provider use policy is not canonical JSON") from exc
        if declared != computed:
            raise ProviderUsePolicyError("provider use policy hash mismatch")
        rules = tuple(ProviderUseRule.from_dict(item) for item in rules_input)
        identities = [(rule.provider_id, rule.origin_host, rule.path_prefix, rule.content_class) for rule in rules]
        if len(identities) != len(set(identities)):
            raise ProviderUsePolicyError("duplicate provider use rule")
        return cls(policy_id=policy_id, policy_sha256=declared, rules=rules)

    def decide(
        self,
        *,
        provider_id: str,
        source_url: str,
        content_class: str,
        action: str,
        on_date: str,
        export_target: str | None = None,
    ) -> ProviderUseDecision:
        def deny(reason: str) -> ProviderUseDecision:
            return ProviderUseDecision(False, reason, self.policy_id, self.policy_sha256)

        if action not in ACTIONS:
            return deny("unknown_action")
        if provider_id in _BLOCKED_SITE_PROVIDERS:
            return deny("provider_site_automation_blocked")
        if not isinstance(source_url, str):
            return deny("invalid_source_url")
        try:
            parsed = urlsplit(source_url)
            port = parsed.port
        except ValueError:
            return deny("invalid_source_url")
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or port is not None
            or parsed.query
            or parsed.fragment
            or parsed.path != unquote(parsed.path)
            or ".." in parsed.path.split("/")
        ):
            return deny("invalid_source_url")
        if any(
            parsed.hostname == host or parsed.hostname.endswith("." + host)
            for host in _BLOCKED_SITE_HOSTS
        ):
            return deny("provider_site_automation_blocked")
        try:
            at = _date(on_date, "on_date")
        except ProviderUsePolicyError:
            return deny("invalid_date")
        matches = [
            rule
            for rule in self.rules
            if rule.provider_id == provider_id
            and rule.origin_host == parsed.hostname
            and rule.content_class == content_class
            and (
                parsed.path == rule.path_prefix
                or parsed.path.startswith(rule.path_prefix.rstrip("/") + "/")
            )
        ]
        if len(matches) != 1:
            return deny("missing_or_ambiguous_rule")
        rule = matches[0]
        if rule.revoked or not (rule.valid_from <= at.isoformat() <= rule.valid_until):
            return deny("rule_inactive")
        if action not in rule.permitted_actions:
            return deny("action_not_permitted")
        if action in {"retain_original", "derive_text", "select_evidence", "generate_summary"}:
            if rule.retention_scope != "company_wiki_local":
                return deny("retention_scope_mismatch")
        if action == "export_excerpt":
            if rule.export_scope == "none" or export_target != rule.export_scope:
                return deny("export_scope_mismatch")
        return ProviderUseDecision(
            True, "permitted", self.policy_id, self.policy_sha256, rule.rights_evidence_sha256
        )


def load_provider_use_policy(path: Path) -> ProviderUsePolicy:
    """Load an already-reviewed policy; missing/corrupt/unknown fails closed."""
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(1024 * 1024 + 1)
    except OSError as exc:
        raise ProviderUsePolicyError("provider use policy unavailable") from exc
    if len(raw) > 1024 * 1024:
        raise ProviderUsePolicyError("provider use policy exceeds byte limit")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderUsePolicyError("provider use policy JSON is corrupt") from exc
    return ProviderUsePolicy.from_dict(payload)


@dataclass(frozen=True)
class TranscriptFetchAdmission:
    """Pre-network decision; an allowed result still requires post-fetch checks."""

    allowed: bool
    reason: str
    rights_policy_sha256: str | None
    download_authorization_hash: str | None
    request_id: str | None = None
    candidate_id: str | None = None


@dataclass(frozen=True)
class TranscriptFetchValidation:
    """Post-fetch proof before any transcript bytes become canonical raw."""

    allowed: bool
    reason: str
    rights_policy_sha256: str | None
    download_authorization_hash: str | None
    content_sha256: str | None = None
    final_url: str | None = None
    mime_type: str | None = None
    byte_size: int | None = None


def validate_transcript_fetch_result(
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    receipt: DownloadReceipt,
    authorization: DownloadAuthorization | None,
    plan_hash: str,
    runtime_policy_hash: str,
    pinned_rights_policy_sha256: str,
    current_rights_policy: ProviderUsePolicy | None,
    final_url: str,
    staging_root: Path,
    now: str,
) -> TranscriptFetchValidation:
    """Revalidate rights, response identity and exact staged bytes after fetch.

    ``current_rights_policy`` must be freshly loaded after the request. A
    caller must keep a denied response in private staging only, then delete it.
    This function never imports or exposes the staged bytes.
    """
    policy_hash = (
        current_rights_policy.policy_sha256
        if isinstance(current_rights_policy, ProviderUsePolicy)
        else None
    )
    authorization_hash = (
        authorization.receipt_hash
        if isinstance(authorization, DownloadAuthorization)
        else None
    )

    def deny(reason: str) -> TranscriptFetchValidation:
        return TranscriptFetchValidation(
            False, reason, policy_hash, authorization_hash,
            final_url=final_url if isinstance(final_url, str) else None,
        )

    if not isinstance(receipt, DownloadReceipt):
        return deny("invalid_download_receipt")
    if not isinstance(staging_root, Path):
        return deny("invalid_staging_root")
    if not isinstance(current_rights_policy, ProviderUsePolicy):
        return deny("missing_current_provider_use_policy")
    if current_rights_policy.policy_sha256 != pinned_rights_policy_sha256:
        return deny("provider_use_policy_changed_during_fetch")
    admission = authorize_transcript_fetch(
        request=request,
        candidate=candidate,
        authorization=authorization,
        plan_hash=plan_hash,
        runtime_policy_hash=runtime_policy_hash,
        rights_policy=current_rights_policy,
        now=now,
    )
    if not admission.allowed:
        return deny("post_fetch_" + admission.reason)
    if (
        receipt.candidate_id != candidate.candidate_id
        or receipt.provider != candidate.provider
        or receipt.provider_document_id != candidate.provider_document_id
        or receipt.source_url != candidate.source_url
    ):
        return deny("download_receipt_identity_mismatch")
    if not 200 <= receipt.http_status < 300:
        return deny("download_receipt_http_status_not_successful")
    if receipt.mime_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
        return deny("unsupported_transcript_mime_type")
    if authorization is None or receipt.byte_size > authorization.max_bytes:
        return deny("downloaded_bytes_exceed_authorized_cap")
    try:
        received_at = datetime.strptime(receipt.retrieved_at, "%Y-%m-%dT%H:%M:%SZ")
        checked_at = datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return deny("invalid_fetch_timestamp")
    if received_at > checked_at:
        return deny("download_receipt_from_future")

    try:
        root_path = staging_root.resolve(strict=True)
    except OSError:
        return deny("allocated_staging_root_unavailable")
    staged_path = Path(receipt.staged_path)
    try:
        resolved_path = staged_path.resolve(strict=True)
        resolved_path.relative_to(root_path)
    except (OSError, ValueError):
        return deny("staged_file_outside_allocated_root")
    try:
        file_stat = resolved_path.stat()
        if staged_path.is_symlink() or not stat.S_ISREG(file_stat.st_mode):
            return deny("staged_file_not_regular")
        if file_stat.st_size != receipt.byte_size:
            return deny("staged_file_size_mismatch")
        digest = hashlib.sha256()
        with resolved_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return deny("staged_file_unavailable")
    if digest.hexdigest() != receipt.content_sha256:
        return deny("staged_file_sha256_mismatch")

    for action in ("automated_fetch", "retain_original", "derive_text"):
        decision = current_rights_policy.decide(
            provider_id=candidate.provider,
            source_url=final_url,
            content_class="earnings_call_transcript",
            action=action,
            on_date=now[:10],
        )
        if not decision.allowed:
            return deny("final_url_rights_" + action + "_" + decision.reason)
    return TranscriptFetchValidation(
        True,
        "permitted",
        policy_hash,
        authorization_hash,
        receipt.content_sha256,
        final_url,
        receipt.mime_type,
        receipt.byte_size,
    )


def authorize_transcript_fetch(
    *,
    request: SourceRequest,
    candidate: DownloadCandidate,
    authorization: DownloadAuthorization | None,
    plan_hash: str,
    runtime_policy_hash: str,
    rights_policy: ProviderUsePolicy | None,
    now: str,
) -> TranscriptFetchAdmission:
    """Compose existing exact-download authorization with transcript rights.

    The caller must run this before invoking the provider. It must recheck the
    pinned rights policy and candidate identity before making bytes visible.
    """
    rights_hash = rights_policy.policy_sha256 if isinstance(rights_policy, ProviderUsePolicy) else None
    auth_hash = authorization.receipt_hash if isinstance(authorization, DownloadAuthorization) else None

    def deny(reason: str) -> TranscriptFetchAdmission:
        return TranscriptFetchAdmission(
            False,
            reason,
            rights_hash,
            auth_hash,
            request.request_id if isinstance(request, SourceRequest) else None,
            candidate.candidate_id if isinstance(candidate, DownloadCandidate) else None,
        )

    if not isinstance(request, SourceRequest) or not isinstance(candidate, DownloadCandidate):
        return deny("invalid_request_or_candidate")
    if not request.allow_download:
        return deny("download_not_authorized")
    # Transcript feeds frequently omit a trustworthy Content-Length during
    # discovery. A missing candidate.remote_size is allowed: callers must
    # send authorization.max_bytes to the bounded provider fetch, and the
    # post-fetch receipt validator enforces the actual byte count before any
    # canonical write.
    if (
        request.market != "US"
        or request.document_kind != "investor_call_transcript"
        or request.fiscal_year is None
        or request.fiscal_period not in {"Q1", "Q2", "Q3", "Q4"}
        or request.security_id is None
        or request.mode not in (None, "exact")
    ):
        return deny("request_not_exact_us_transcript")
    if (
        candidate.market != request.market
        or candidate.document_kind != request.document_kind
        or candidate.entity != request.entity
        or candidate.fiscal_year != request.fiscal_year
        or candidate.fiscal_period != request.fiscal_period
        or candidate.filing_date > request.as_of_date
        or request.provider not in (None, candidate.provider)
        or request.provider_document_id not in (None, candidate.provider_document_id)
    ):
        return deny("candidate_identity_mismatch")
    try:
        candidate_identity = json.loads(candidate.adapter_payload_json or "null")
    except json.JSONDecodeError:
        return deny("candidate_security_identity_missing")
    if (
        not isinstance(candidate_identity, dict)
        or candidate_identity.get("security_id") != request.security_id
        or candidate_identity.get("market") != request.market
    ):
        return deny("candidate_security_identity_missing")
    try:
        parsed_now = datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return deny("invalid_now")
    if parsed_now.strftime("%Y-%m-%dT%H:%M:%SZ") != now:
        return deny("invalid_now")
    if not isinstance(authorization, DownloadAuthorization):
        return deny("missing_download_authorization")
    if authorization.request_id != request.request_id:
        return deny("authorization_request_mismatch")
    if authorization.policy_hash != runtime_policy_hash:
        return deny("runtime_policy_hash_mismatch")
    download_issue = validate_download_authorization(
        authorization, candidate, plan_hash=plan_hash, now=now
    )
    if download_issue is not None:
        return deny("download_authorization_rejected")
    if not isinstance(rights_policy, ProviderUsePolicy):
        return deny("missing_provider_use_policy")
    for action in ("automated_fetch", "retain_original", "derive_text"):
        rights = rights_policy.decide(
            provider_id=candidate.provider,
            source_url=candidate.source_url,
            content_class="earnings_call_transcript",
            action=action,
            on_date=now[:10],
        )
        if not rights.allowed:
            if action == "automated_fetch":
                return deny("provider_rights_" + rights.reason)
            return deny("provider_rights_" + action + "_" + rights.reason)
    return TranscriptFetchAdmission(
        True,
        "permitted",
        rights_hash,
        auth_hash,
        request.request_id,
        candidate.candidate_id,
    )
