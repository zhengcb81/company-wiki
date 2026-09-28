"""Transcript-specific composition of independent provider-use actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .provider_use_policy import ACTIONS, ProviderUsePolicy


@dataclass(frozen=True)
class TranscriptActionDecision:
    allowed: bool
    reason: str
    rights_policy_sha256: str | None
    failed_action: str | None = None
    evidence_sha256_by_action: tuple[tuple[str, str], ...] = ()


def _actions_tuple(actions: Iterable[str]) -> tuple[str, ...] | None:
    result = tuple(actions)
    if not result or len(result) != len(set(result)) or not set(result) <= ACTIONS:
        return None
    return result


def authorize_transcript_actions(
    *,
    rights_policy: ProviderUsePolicy | None,
    provider_id: str,
    source_url: str,
    actions: Iterable[str],
    on_date: str,
    export_target: str | None = None,
) -> TranscriptActionDecision:
    """Require every requested action; one allowed action never implies another."""
    if not isinstance(rights_policy, ProviderUsePolicy):
        return TranscriptActionDecision(False, "missing_provider_use_policy", None)
    requested = _actions_tuple(actions)
    if requested is None:
        return TranscriptActionDecision(
            False, "invalid_actions", rights_policy.policy_sha256
        )
    evidence: list[tuple[str, str]] = []
    for action in requested:
        decision = rights_policy.decide(
            provider_id=provider_id,
            source_url=source_url,
            content_class="earnings_call_transcript",
            action=action,
            on_date=on_date,
            export_target=export_target,
        )
        if not decision.allowed:
            return TranscriptActionDecision(
                False,
                decision.reason,
                rights_policy.policy_sha256,
                failed_action=action,
            )
        if decision.rule_evidence_sha256 is not None:
            evidence.append((action, decision.rule_evidence_sha256))
    return TranscriptActionDecision(
        True,
        "permitted",
        rights_policy.policy_sha256,
        evidence_sha256_by_action=tuple(evidence),
    )
