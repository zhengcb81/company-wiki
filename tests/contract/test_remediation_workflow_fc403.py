"""FC-403 RED/acceptance tests: remediation proposal/approval workflow.

Proposal and approval are SEPARATE steps: a reviewer sees the source
bytes hash, field evidence, the diff, and the policy hash before
approving.  The approval tool only generates SHADOW assertions (never
active); activation is the Phase 2 control plane's job.  No hardcoded
`user-approved-*` reviewer strings, short receipt ids, or placeholder
policy hashes may appear in source.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.store import CatalogStore  # noqa: E402

POLICY_HASH = "a" * 64


def _seed(store: CatalogStore):
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, "
            "mime_type, first_seen_at) VALUES ('s1','h',1,'x','2026-01-01')"
        )
        conn.execute(
            "INSERT INTO documents (document_id, title, source_status, "
            "source_type, document_kind, metadata_priority, metadata_json, "
            "first_seen_at, last_seen_at) "
            "VALUES ('d1','t','active','file','k',10,'{}','2026-01-01','2026-01-01')"
        )


# --- proposal/approval separation -------------------------------------------


def test_proposal_requires_reviewer_evidence_bundle(tmp_path):
    """A proposal must carry the source bytes hash, field evidence, the
    proposed fields, and the policy hash — the reviewer's decision input."""
    from company_wiki.source_catalog.remediation import create_proposal

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store)
    proposal = create_proposal(
        store,
        source_id="s1",
        document_id="d1",
        content_sha256="c" * 64,
        field_evidence={
            "fiscal_year": {"origin": "sidecar", "source_pointer": "fiscal_year"},
            "period_end": {"origin": "official-disclosure", "source_pointer": "pdf-page-3"},
            "provider": {"origin": "sidecar", "source_pointer": "provider"},
        },
        proposed_fields={
            "fiscal_year": 2024,
            "period_end": "2024-12-31",
            "provider": "cninfo",
        },
        policy_hash=POLICY_HASH,
        proposed_by="reviewer-a",
    )
    assert proposal["status"] == "proposed"
    assert proposal["policy_hash"] == POLICY_HASH
    assert len(proposal["proposal_id"]) == 32  # full receipt id, not short
    assert proposal["evidence"]["source_bytes_sha256"] == "c" * 64


def test_proposal_placeholder_policy_hash_rejected(tmp_path):
    from company_wiki.source_catalog.remediation import (
        RemediationError,
        create_proposal,
    )

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store)
    with pytest.raises(RemediationError):
        create_proposal(
            store,
            source_id="s1",
            document_id="d1",
            content_sha256="c" * 64,
            field_evidence={
                "fiscal_year": {"origin": "sidecar", "source_pointer": "fiscal_year"},
            },
            proposed_fields={"fiscal_year": 2024},
            policy_hash="p" * 64,  # non-hex 64-char -> fail closed
            proposed_by="reviewer-a",
        )


def test_proposal_short_policy_hash_rejected(tmp_path):
    from company_wiki.source_catalog.remediation import (
        RemediationError,
        create_proposal,
    )

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store)
    with pytest.raises(RemediationError):
        create_proposal(
            store,
            source_id="s1",
            document_id="d1",
            content_sha256="c" * 64,
            field_evidence={
                "fiscal_year": {"origin": "sidecar", "source_pointer": "fiscal_year"},
            },
            proposed_fields={"fiscal_year": 2024},
            policy_hash="abc123",
            proposed_by="reviewer-a",
        )


def test_approval_requires_existing_proposal(tmp_path):
    """Approval without a matching proposal is impossible (separation)."""
    from company_wiki.source_catalog.remediation import (
        RemediationError,
        approve_proposal,
    )

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store)
    with pytest.raises(RemediationError):
        approve_proposal(
            store,
            proposal_id="no-such-proposal",
            approved_by="reviewer-b",
            policy_hash=POLICY_HASH,
        )


def test_approval_creates_shadow_assertion_only(tmp_path):
    """The approval output is a SHADOW assertion — never active; the
    Phase 2 control plane (activation) decides visibility."""
    from company_wiki.source_catalog.remediation import (
        approve_proposal,
        create_proposal,
    )

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store)
    proposal = create_proposal(
        store,
        source_id="s1",
        document_id="d1",
        content_sha256="c" * 64,
        field_evidence={
            "fiscal_year": {"origin": "sidecar", "source_pointer": "fiscal_year"},
            "period_end": {"origin": "official-disclosure", "source_pointer": "pdf-page-3"},
            "provider": {"origin": "sidecar", "source_pointer": "provider"},
        },
        proposed_fields={
            "fiscal_year": 2024,
            "period_end": "2024-12-31",
            "provider": "cninfo",
        },
        policy_hash=POLICY_HASH,
        proposed_by="reviewer-a",
    )
    approved = approve_proposal(
        store,
        proposal_id=proposal["proposal_id"],
        approved_by="reviewer-b",
        policy_hash=POLICY_HASH,
    )
    assert approved["status"] == "approved"
    assert approved["approval_id"] == proposal["proposal_id"]
    row = store.fetchone(
        "SELECT * FROM source_metadata_assertions WHERE assertion_id=?",
        (approved["assertion_id"],),
    )
    assert row is not None
    assert row["visibility_state"] == "shadow"  # activation is a separate step
    assert row["decision"] == "verified"


def test_approval_wrong_policy_hash_rejected(tmp_path):
    from company_wiki.source_catalog.remediation import (
        RemediationError,
        approve_proposal,
        create_proposal,
    )

    store = CatalogStore(tmp_path / "c.sqlite3")
    _seed(store)
    proposal = create_proposal(
        store,
        source_id="s1",
        document_id="d1",
        content_sha256="c" * 64,
        field_evidence={
            "fiscal_year": {"origin": "sidecar", "source_pointer": "fiscal_year"},
        },
        proposed_fields={"fiscal_year": 2024},
        policy_hash=POLICY_HASH,
        proposed_by="reviewer-a",
    )
    with pytest.raises(RemediationError):
        approve_proposal(
            store,
            proposal_id=proposal["proposal_id"],
            approved_by="reviewer-b",
            policy_hash="b" * 64,  # stale policy
        )


# --- no hardcoded approval patterns in source -------------------------------


def test_no_hardcoded_approval_patterns_in_source(tmp_path):
    """Source must not hardcode `user-approved-*` reviewer strings or
    placeholder policy hashes (FC-403 deletion discipline)."""
    import re

    src_dir = Path(__file__).resolve().parents[2] / "src"
    forbidden = (re.compile(r"user-approved-\d"), re.compile(r"plan-hash-\d"))
    violations = []
    for py_file in src_dir.rglob("*.py"):
        if py_file.name.startswith("test_") or py_file.name.startswith("__"):
            continue
        text = py_file.read_text(encoding="utf-8")
        for pattern in forbidden:
            if pattern.search(text):
                violations.append(f"{py_file.name}: {pattern.pattern}")
    assert violations == [], f"hardcoded approval patterns: {violations}"
