"""FC-1204-a: close the small branch gaps keeping Tier-1 criticals below 95%.

Each test targets a specific measured missing line (findings 61 baseline):
admission 94 / policy 93 / restore 93 / scheduler_policy 93 /
visibility_bridge 93 -> >=95.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from company_wiki.source_catalog import CatalogConfig, RootSpec
from company_wiki.source_catalog.admission import (
    FOCUS_RELATIVE_PREFIX,
    FOCUS_ROOT_ID,
    evaluate_admission,
    processing_priority_sql,
)
from company_wiki.source_catalog.policy import export_policy
from company_wiki.source_catalog.restore import restore_asset, revert_restore
from company_wiki.source_catalog.visibility_bridge import set_visibility

# --- admission: 105, 142, 158, 201/203 ---------------------------------------


def test_processing_priority_sql_rejects_invalid_alias():
    with pytest.raises(ValueError, match="simple identifier"):
        processing_priority_sql(alias="1bad; DROP")


def test_focus_admission_rejects_path_traversal():
    decision = evaluate_admission(
        root_id=FOCUS_ROOT_ID,
        relative_path=f"{FOCUS_RELATIVE_PREFIX}/../escape.pdf",
        metadata={},
    )
    assert decision is not None and not decision.admitted


def test_focus_admission_rejects_explicit_kind_not_allowed():
    decision = evaluate_admission(
        root_id=FOCUS_ROOT_ID,
        relative_path=f"{FOCUS_RELATIVE_PREFIX}/x.txt",
        metadata={"document_kind": "personal_note"},
    )
    assert decision is not None and not decision.admitted
    assert decision.reason == "focus_policy_explicit_kind_not_allowed"


def test_focus_admission_recognizes_semi_annual_form_h1():
    decision = evaluate_admission(
        root_id=FOCUS_ROOT_ID,
        relative_path=f"{FOCUS_RELATIVE_PREFIX}/Acme半年报.pdf",
        metadata={"form_type": "H1"},
    )
    assert decision is not None
    assert decision.document_kind == "semi_annual_report"


# --- policy: 24-25 (path outside project_root redaction) ---------------------


def test_policy_export_redacts_path_outside_project_root(tmp_path: Path):
    outside = tmp_path.parent / "elsewhere"
    outside.mkdir(exist_ok=True)
    project = tmp_path / "project"
    config = CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(RootSpec("company_raw", outside, "company_raw"),),
    )
    _, policy = export_policy(config, project_root=project)
    paths = [str(root.get("path", "")) for root in policy["roots"]]
    assert paths and all("<redacted-absolute-path>" in p for p in paths)


# --- restore: 54, 62 ---------------------------------------------------------


def test_restore_asset_rejects_multi_or_spacey_document_ids():
    for doc_id in ("a,b", "a b"):
        receipt, rejection = restore_asset(
            document_id=doc_id,
            file_hash_matches=True,
            v2_complete=True,
            provenance_ok=True,
            policy_allows=True,
            reviewer="reviewer",
            reason="fix",
            original_retire_reason="old",
            policy_hash="p" * 64,
        )
        assert receipt is None
        assert "must_target_one_document_id" in rejection.reasons


def test_restore_asset_rejects_incomplete_v2_metadata():
    receipt, rejection = restore_asset(
        document_id="d1",
        file_hash_matches=True,
        v2_complete=False,
        provenance_ok=True,
        policy_allows=True,
        reviewer="reviewer",
        reason="fix",
        original_retire_reason="old",
        policy_hash="p" * 64,
    )
    assert receipt is None
    assert "v2_metadata_incomplete" in rejection.reasons


def test_restore_asset_requires_restore_reason():
    receipt, rejection = restore_asset(
        document_id="d1",
        file_hash_matches=True,
        v2_complete=True,
        provenance_ok=True,
        policy_allows=True,
        reviewer="reviewer",
        reason="",
        original_retire_reason="old",
        policy_hash="p" * 64,
    )
    assert receipt is None
    assert "restore_reason_required" in rejection.reasons


def test_restore_asset_success_path_and_revert():
    receipt, rejection = restore_asset(
        document_id="d1",
        file_hash_matches=True,
        v2_complete=True,
        provenance_ok=True,
        policy_allows=True,
        reviewer="reviewer",
        reason="fix",
        original_retire_reason="old",
        policy_hash="p" * 64,
    )
    assert receipt is not None and rejection.reasons == []
    reverted = revert_restore(receipt)
    assert reverted.reverted is True
    assert reverted.receipt_id == receipt.receipt_id


# --- scheduler_policy: 79, 93 -------------------------------------------------

def test_scheduler_policy_rejects_bad_schema_version():
    from company_wiki.source_catalog.scheduler_policy import (
        SOURCE_ONLY_SCHEDULER_POLICY_SCHEMA_VERSION,
        SourceOnlySchedulerPolicy,
        SourceOnlySchedulerPolicyError,
    )

    with pytest.raises(SourceOnlySchedulerPolicyError, match="unsupported"):
        SourceOnlySchedulerPolicy(
            schema_version="wrong-" + SOURCE_ONLY_SCHEDULER_POLICY_SCHEMA_VERSION
        )


def test_scheduler_policy_rejects_untrimmed_catalog_method():
    from company_wiki.source_catalog.scheduler_policy import (
        SourceOnlySchedulerPolicy,
        SourceOnlySchedulerPolicyError,
    )

    with pytest.raises(SourceOnlySchedulerPolicyError, match="exact text"):
        SourceOnlySchedulerPolicy().require_dispatch("scanning", " scan ")


# --- visibility_bridge: 40, 43->46 -------------------------------------------


def test_set_visibility_rejects_unknown_state():
    with pytest.raises(ValueError, match="unknown visibility state"):
        set_visibility([{"assertion_id": "a1"}], "a1", "invisible")


def test_set_visibility_only_flips_the_target_row():
    rows = [
        {"assertion_id": "a1", "visibility_state": "active"},
        {"assertion_id": "a2", "visibility_state": "active"},
    ]
    updated = set_visibility(rows, "a1", "shadow")
    assert updated[0]["visibility_state"] == "shadow"
    assert updated[1]["visibility_state"] == "active"
    # input rows untouched
    assert rows[0]["visibility_state"] == "active"
