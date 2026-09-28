"""Fail-closed, read-only provider content-use policy.

This module owns provider rule parsing and one-action decisions only. Exact
download authorization and transcript request identity live in separate
application layers.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlsplit

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
_BLOCKED_SITE_PROVIDERS = frozenset({"motley_fool", "seeking_alpha"})
_BLOCKED_SITE_HOSTS = frozenset({"fool.com", "seekingalpha.com"})
_LOCAL_ACTIONS = frozenset(
    {"retain_original", "derive_text", "select_evidence", "generate_summary"}
)


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
        if not prefix.startswith("/") or any(
            part in prefix for part in ("//", "..", "?", "#")
        ):
            raise ProviderUsePolicyError("invalid path_prefix")
        reviewed = _date(value["reviewed_at"], "reviewed_at")
        valid_from = _date(value["valid_from"], "valid_from")
        valid_until = _date(value["valid_until"], "valid_until")
        if not reviewed <= valid_from <= valid_until:
            raise ProviderUsePolicyError("provider use rule dates are out of order")
        actions = value["permitted_actions"]
        if not isinstance(actions, list) or not all(
            isinstance(item, str) for item in actions
        ):
            raise ProviderUsePolicyError("invalid permitted_actions")
        if len(actions) != len(set(actions)) or not set(actions) <= ACTIONS:
            raise ProviderUsePolicyError("invalid permitted_actions")
        if type(value["revoked"]) is not bool:
            raise ProviderUsePolicyError("revoked must be boolean")
        return cls(
            provider_id=provider_id,
            origin_host=host,
            path_prefix=prefix,
            content_class=_text(value["content_class"], "content_class"),
            rights_evidence_ref=_text(
                value["rights_evidence_ref"], "rights_evidence_ref"
            ),
            rights_evidence_sha256=_sha(
                value["rights_evidence_sha256"], "rights_evidence_sha256"
            ),
            reviewer=_text(value["reviewer"], "reviewer"),
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


def _deny(policy: "ProviderUsePolicy", reason: str) -> ProviderUseDecision:
    return ProviderUseDecision(False, reason, policy.policy_id, policy.policy_sha256)


def _safe_https_location(source_url: object) -> tuple[str, str] | None:
    if not isinstance(source_url, str):
        return None
    try:
        parsed = urlsplit(source_url)
        port = parsed.port
    except ValueError:
        return None
    if _authority_is_unsafe(parsed, port) or _path_is_unsafe(parsed):
        return None
    hostname = parsed.hostname
    if hostname is None:
        return None
    return hostname, parsed.path


def _authority_is_unsafe(parsed: Any, port: int | None) -> bool:
    if parsed.scheme != "https" or not parsed.hostname:
        return True
    if parsed.username is not None or parsed.password is not None:
        return True
    if port is not None:
        return True
    return bool(parsed.query) or bool(parsed.fragment)


def _path_is_unsafe(parsed: Any) -> bool:
    if parsed.path != unquote(parsed.path):
        return True
    return ".." in parsed.path.split("/")


def _host_is_blocked(host: str) -> bool:
    return any(
        host == blocked or host.endswith("." + blocked)
        for blocked in _BLOCKED_SITE_HOSTS
    )


def _rule_matches(
    rule: ProviderUseRule,
    *,
    provider_id: str,
    host: str,
    path: str,
    content_class: str,
) -> bool:
    path_matches = path == rule.path_prefix or path.startswith(
        rule.path_prefix.rstrip("/") + "/"
    )
    return (
        rule.provider_id == provider_id
        and rule.origin_host == host
        and rule.content_class == content_class
        and path_matches
    )


def _active_rule_decision(
    policy: "ProviderUsePolicy",
    rule: ProviderUseRule,
    *,
    action: str,
    on_date: str,
    export_target: str | None,
) -> ProviderUseDecision:
    if not _rule_is_active(rule, on_date):
        return _deny(policy, "rule_inactive")
    if action not in rule.permitted_actions:
        return _deny(policy, "action_not_permitted")
    scope_issue = _scope_issue(rule, action, export_target)
    if scope_issue is not None:
        return _deny(policy, scope_issue)
    return ProviderUseDecision(
        True,
        "permitted",
        policy.policy_id,
        policy.policy_sha256,
        rule.rights_evidence_sha256,
    )


def _rule_is_active(rule: ProviderUseRule, on_date: str) -> bool:
    return not rule.revoked and rule.valid_from <= on_date <= rule.valid_until


def _scope_issue(
    rule: ProviderUseRule, action: str, export_target: str | None
) -> str | None:
    if action in _LOCAL_ACTIONS:
        return (
            "retention_scope_mismatch"
            if rule.retention_scope != "company_wiki_local"
            else None
        )
    if action == "export_excerpt":
        if rule.export_scope == "none" or export_target != rule.export_scope:
            return "export_scope_mismatch"
    return None


@dataclass(frozen=True)
class ProviderUsePolicy:
    policy_id: str
    policy_sha256: str
    rules: tuple[ProviderUseRule, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProviderUsePolicy":
        if not isinstance(value, Mapping) or set(value) != _POLICY_KEYS:
            raise ProviderUsePolicyError(
                "provider use policy fields differ from schema"
            )
        if value["schema_version"] != PROVIDER_USE_POLICY_SCHEMA:
            raise ProviderUsePolicyError("unsupported provider use policy schema")
        policy_id = _text(value["policy_id"], "policy_id")
        rules_input = value["rules"]
        if not isinstance(rules_input, list) or len(rules_input) > 1000:
            raise ProviderUsePolicyError("rules must be a bounded list")
        declared = _sha(value["policy_sha256"], "policy_sha256")
        try:
            encoded = canonical_json(
                {key: val for key, val in value.items() if key != "policy_sha256"}
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ProviderUsePolicyError(
                "provider use policy is not canonical JSON"
            ) from exc
        if declared != hashlib.sha256(encoded).hexdigest():
            raise ProviderUsePolicyError("provider use policy hash mismatch")
        rules = tuple(ProviderUseRule.from_dict(item) for item in rules_input)
        identities = [
            (rule.provider_id, rule.origin_host, rule.path_prefix, rule.content_class)
            for rule in rules
        ]
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
        if action not in ACTIONS:
            return _deny(self, "unknown_action")
        if provider_id in _BLOCKED_SITE_PROVIDERS:
            return _deny(self, "provider_site_automation_blocked")
        location = _safe_https_location(source_url)
        if location is None:
            return _deny(self, "invalid_source_url")
        host, path = location
        if _host_is_blocked(host):
            return _deny(self, "provider_site_automation_blocked")
        try:
            at = _date(on_date, "on_date").isoformat()
        except ProviderUsePolicyError:
            return _deny(self, "invalid_date")
        matches = [
            rule
            for rule in self.rules
            if _rule_matches(
                rule,
                provider_id=provider_id,
                host=host,
                path=path,
                content_class=content_class,
            )
        ]
        if len(matches) != 1:
            return _deny(self, "missing_or_ambiguous_rule")
        return _active_rule_decision(
            self,
            matches[0],
            action=action,
            on_date=at,
            export_target=export_target,
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
