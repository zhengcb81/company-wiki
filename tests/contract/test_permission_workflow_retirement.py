"""Retired proposal/approval writer cannot revive a second metadata workflow."""

import pytest

from company_wiki.source_catalog.remediation import (
    RemediationError,
    approve_proposal,
    create_proposal,
)


class NoCatalogIO:
    """Prove retirement is independent of catalog, config or credentials."""

    def __getattr__(self, name):
        raise AssertionError(f"retired writer accessed catalog: {name}")


@pytest.mark.parametrize("policy_hash", ["", "old-policy", "a" * 64])
def test_legacy_proposal_is_retired_without_catalog_write(policy_hash):
    with pytest.raises(RemediationError, match="legacy_remediation_retired"):
        create_proposal(
            NoCatalogIO(), source_id="s1", document_id="d1",
            content_sha256="c" * 64, field_evidence={}, proposed_fields={},
            policy_hash=policy_hash, proposed_by="",
        )


@pytest.mark.parametrize("actor", ["", "operator", "legacy-reviewer"])
def test_legacy_approval_cannot_mint_shadow_assertions(actor):
    with pytest.raises(RemediationError, match="legacy_remediation_retired"):
        approve_proposal(
            NoCatalogIO(), proposal_id="b" * 32,
            approved_by=actor, policy_hash="a" * 64,
        )
