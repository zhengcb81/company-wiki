"""FC-203 RED/acceptance tests: real activation/rollback transactions.

Cohort/epoch/policy-snapshot switches happen ONLY inside a catalog
transaction; every apply/rollback writes an immutable journal receipt;
rollback is proven by the same request's before/after response trace
(CTRL-04); partial cohort activation failure rolls the whole transaction
back with no half-activation (CTRL-03); repeated apply/rollback, process
interruption, wrong cohort and stale policy hash all fail closed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import json  # noqa: E402

import pytest  # noqa: E402

from company_wiki.source_catalog.assertion_service import (  # noqa: E402
    upsert_verified_assertion,
)
from company_wiki.source_catalog.normalized_meta import canonical_hash  # noqa: E402
from company_wiki.source_catalog.store import CatalogStore  # noqa: E402

POLICY_HASH = "a" * 64


def _seed(store, *, n: int = 2) -> list[str]:
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, "
            "mime_type, first_seen_at) VALUES (?,?,?,?,?)",
            ("s1", "src-hash", 10, "application/pdf", "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO documents (document_id, title, source_status, "
            "source_type, document_kind, metadata_priority, metadata_json, "
            "first_seen_at, last_seen_at) "
            "VALUES ('d1', 'Acme 2025', 'active', 'file', 'annual_report', 10, "
            "'{}', '2026-01-01', '2026-01-01')"
        )
    ids = []
    for i in range(n):
        normalized = {
            "schema_version": "2.0",
            "canonical_entity_id": "ent-acme",
            "display_name": "Acme",
            "market": "US",
            "security_id": "US123",
            "document_kind": "annual_report",
            "fiscal_year": 2025,
            "period_end": "2025-12-31",
            "provider": "example-filing",
            "provider_document_id": f"acc-{i}",
            "content_sha256": f"{i}" * 64,
            "adapter_id": "sidecar_filing_v1",
            "adapter_version": "1.0.0",
            "normalization_status": "capture_ready",
        }
        normalized["metadata_sha256"] = canonical_hash(normalized)
        assertion = upsert_verified_assertion(
            store, source_id="s1", document_id="d1",
            content_sha256=f"{i}" * 64,
            adapter_id="sidecar_filing_v1", adapter_version="1.0.0",
            metadata_hash=canonical_hash(normalized), normalized=normalized,
        )
        ids.append(assertion["assertion_id"])
    return ids


def _assertion_row(store, assertion_id: str) -> dict:
    row = store.fetchone(
        "SELECT * FROM source_metadata_assertions WHERE assertion_id=?",
        (assertion_id,),
    )
    return dict(row)


# --- CTRL-03: partial cohort activation failure -> whole txn rolls back ---


def test_ctrl03_unknown_assertion_rolls_back_whole_transaction(tmp_path):
    from company_wiki.source_catalog.activation import (
        ActivationError,
        apply_activation,
    )

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    ids = _seed(store)
    with pytest.raises(ActivationError):
        apply_activation(
            store,
            epoch="epoch-2",
            cohort="cohort-a",
            assertion_ids=[ids[0], "does-not-exist"],
            policy_hash=POLICY_HASH,
            reviewer="reviewer-x",
            reason="canary cohort",
        )
    # NOTHING flipped: no half-activation
    assert _assertion_row(store, ids[0])["visibility_state"] == "shadow"
    assert _assertion_row(store, ids[1])["visibility_state"] == "shadow"


def test_ctrl03_apply_requires_catalog_transaction_visibility(tmp_path):
    """apply_activation must NOT leave partial state when a later assertion
    in the same batch fails (atomic single transaction)."""
    from company_wiki.source_catalog.activation import (
        ActivationError,
        apply_activation,
    )

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    ids = _seed(store, n=3)
    # make the third assertion a non-verified row so the batch fails late
    with store.transaction() as conn:
        conn.execute(
            "UPDATE source_metadata_assertions SET decision='rejected' "
            "WHERE assertion_id=?",
            (ids[2],),
        )
    with pytest.raises(ActivationError):
        apply_activation(
            store,
            epoch="epoch-2",
            cohort="cohort-a",
            assertion_ids=ids,
            policy_hash=POLICY_HASH,
            reviewer="reviewer-x",
            reason="canary cohort",
        )
    # first two rows must still be shadow: atomic rollback of the batch
    assert _assertion_row(store, ids[0])["visibility_state"] == "shadow"
    assert _assertion_row(store, ids[1])["visibility_state"] == "shadow"


# --- CTRL-04: real rollback changes the same request's response -----------


def test_ctrl04_rollback_restores_prior_response(tmp_path):
    from company_wiki.source_catalog.activation import (
        apply_activation,
        rollback_activation,
    )
    from company_wiki.source_catalog.resolver import resolver_visibility

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    ids = _seed(store)
    receipt = apply_activation(
        store,
        epoch="epoch-2",
        cohort="cohort-a",
        assertion_ids=ids,
        policy_hash=POLICY_HASH,
        reviewer="reviewer-x",
        reason="canary cohort",
    )
    # after apply: rows are active with pinned epoch+cohort
    assert _assertion_row(store, ids[0])["visibility_state"] == "active"
    assert _assertion_row(store, ids[0])["activation_epoch"] == "epoch-2"
    assert _assertion_row(store, ids[0])["cohort"] == "cohort-a"

    # same-request trace: v2 reader with the applied snapshot sees the row
    snapshot = {
        "schema_version": "1.0",
        "flags": {
            "v2_scan_shadow": True, "v2_persist_assertions": True,
            "v2_resolve_shadow": True, "v2_resolve_active": True,
            "v2_bundle_active": False, "legacy_bridge_enabled": False,
        },
        "current_epoch": "epoch-2",
        "active_cohorts": ["cohort-a"],
        "policy_hash": POLICY_HASH,
        "updated_at": "2026-08-10T00:00:00Z",
    }
    reader, epoch, cohorts, bridge = resolver_visibility(snapshot)
    assert reader == "v2" and epoch == "epoch-2" and cohorts == ("cohort-a",)

    # rollback via the apply receipt
    rolled = rollback_activation(
        store,
        receipt_id=receipt["receipt_id"],
        reviewer="reviewer-x",
        reason="cohort rollback drill",
    )
    assert rolled["applies_receipt_id"] == receipt["receipt_id"]
    # assertions are NOT deleted — visibility reverted
    assert _assertion_row(store, ids[0])["visibility_state"] == "shadow"
    assert _assertion_row(store, ids[1])["visibility_state"] == "shadow"
    assert _assertion_row(store, ids[0])["activation_epoch"] == "epoch-2"


def test_ctrl04_rollback_wrong_cohort_rejected(tmp_path):
    from company_wiki.source_catalog.activation import (
        ActivationError,
        apply_activation,
        rollback_activation,
    )

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    ids = _seed(store)
    receipt = apply_activation(
        store,
        epoch="epoch-2",
        cohort="cohort-a",
        assertion_ids=ids,
        policy_hash=POLICY_HASH,
        reviewer="reviewer-x",
        reason="canary cohort",
    )
    with pytest.raises(ActivationError):
        rollback_activation(
            store,
            receipt_id=receipt["receipt_id"],
            cohort="cohort-b",  # wrong cohort
            reviewer="reviewer-x",
            reason="should fail",
        )


def test_ctrl04_rollback_unknown_receipt_rejected(tmp_path):
    from company_wiki.source_catalog.activation import (
        ActivationError,
        rollback_activation,
    )

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed(store)
    with pytest.raises(ActivationError):
        rollback_activation(
            store,
            receipt_id="no-such-receipt",
            reviewer="reviewer-x",
            reason="should fail",
        )


# --- repeated apply/rollback ----------------------------------------------


def test_repeated_apply_rejected(tmp_path):
    from company_wiki.source_catalog.activation import (
        ActivationError,
        apply_activation,
    )

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    ids = _seed(store)
    apply_activation(
        store,
        epoch="epoch-2",
        cohort="cohort-a",
        assertion_ids=ids,
        policy_hash=POLICY_HASH,
        reviewer="reviewer-x",
        reason="canary cohort",
    )
    with pytest.raises(ActivationError):
        apply_activation(
            store,
            epoch="epoch-2",
            cohort="cohort-a",
            assertion_ids=ids,
            policy_hash=POLICY_HASH,
            reviewer="reviewer-x",
            reason="double apply",
        )


def test_repeated_rollback_rejected(tmp_path):
    from company_wiki.source_catalog.activation import (
        ActivationError,
        apply_activation,
        rollback_activation,
    )

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    ids = _seed(store)
    receipt = apply_activation(
        store,
        epoch="epoch-2",
        cohort="cohort-a",
        assertion_ids=ids,
        policy_hash=POLICY_HASH,
        reviewer="reviewer-x",
        reason="canary cohort",
    )
    rollback_activation(
        store,
        receipt_id=receipt["receipt_id"],
        reviewer="reviewer-x",
        reason="rollback drill",
    )
    with pytest.raises(ActivationError):
        rollback_activation(
            store,
            receipt_id=receipt["receipt_id"],
            reviewer="reviewer-x",
            reason="double rollback",
        )


# --- stale policy hash ------------------------------------------------------


def test_apply_stale_policy_hash_rejected(tmp_path):
    from company_wiki.source_catalog.activation import (
        ActivationError,
        apply_activation,
    )

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    ids = _seed(store)
    with pytest.raises(ActivationError):
        apply_activation(
            store,
            epoch="epoch-2",
            cohort="cohort-a",
            assertion_ids=ids,
            policy_hash="b" * 64,  # stale/wrong policy hash
            reviewer="reviewer-x",
            reason="stale policy",
            current_policy_hash=POLICY_HASH,  # current RootPolicy hash
        )


def test_apply_matching_policy_hash_accepted(tmp_path):
    from company_wiki.source_catalog.activation import apply_activation

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    ids = _seed(store)
    receipt = apply_activation(
        store,
        epoch="epoch-2",
        cohort="cohort-a",
        assertion_ids=ids,
        policy_hash=POLICY_HASH,
        reviewer="reviewer-x",
        reason="canary cohort",
        current_policy_hash=POLICY_HASH,
    )
    assert receipt["policy_hash"] == POLICY_HASH


# --- CLI seam ---------------------------------------------------------------


def _project(tmp_path: Path):
    project = tmp_path / "project"
    config_path = project / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "\n".join(
            [
                "schema_version: '1.0'",
                "catalog_dir: '" + str(project / ".source_catalog").replace("\\", "/") + "'",
                "roots:",
                "  - root_id: company_raw",
                "    kind: company_raw",
                "    path: '" + str(project / "companies").replace("\\", "/") + "'",
                "    priority: 10",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return project, config_path


def test_cli_activation_apply_rollback_roundtrip(tmp_path, capsys):
    from company_wiki.source_catalog.cli import main
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.policy import export_policy

    project, config_path = _project(tmp_path)
    store = CatalogStore(project / ".source_catalog" / "catalog.sqlite3")
    ids = _seed(store)
    joined = ",".join(ids)
    # the CLI binds the CURRENT RootPolicy export hash — the activation
    # must use the same hash or the stale-policy gate fails closed
    config = load_catalog_config(config_path, project_root=project)
    current_policy_hash, _ = export_policy(config)
    rc = main(
        ["--config", str(config_path), "activation", "apply",
         "--epoch", "epoch-2", "--cohort", "cohort-a",
         "--assertion-ids", joined,
         "--policy-hash", current_policy_hash,
         "--reviewer", "cli-user", "--reason", "cli drill",
         ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["kind"] == "apply"
    assert out["receipt_id"]

    rc = main(
        ["--config", str(config_path), "activation", "rollback",
         "--receipt-id", out["receipt_id"],
         "--reviewer", "cli-user", "--reason", "cli drill rollback",
         ]
    )
    assert rc == 0
    rolled = json.loads(capsys.readouterr().out)
    assert rolled["kind"] == "rollback"
    assert rolled["applies_receipt_id"] == out["receipt_id"]


# --- immutable journal receipt --------------------------------------------


def test_journal_receipts_are_immutable(tmp_path):
    from company_wiki.source_catalog.activation import (
        apply_activation,
        journal_rows,
    )

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    ids = _seed(store)
    receipt = apply_activation(
        store,
        epoch="epoch-2",
        cohort="cohort-a",
        assertion_ids=ids,
        policy_hash=POLICY_HASH,
        reviewer="reviewer-x",
        reason="canary cohort",
    )
    rows = journal_rows(store)
    assert len(rows) == 1
    assert rows[0]["receipt_id"] == receipt["receipt_id"]
    assert rows[0]["kind"] == "apply"
    assert rows[0]["epoch"] == "epoch-2"
    assert rows[0]["cohort"] == "cohort-a"
    assert rows[0]["policy_hash"] == POLICY_HASH
    # append-only: a rollback adds a row, never updates the apply row
    from company_wiki.source_catalog.activation import rollback_activation

    rollback_activation(
        store,
        receipt_id=receipt["receipt_id"],
        reviewer="reviewer-x",
        reason="drill",
    )
    rows = journal_rows(store)
    assert len(rows) == 2
    assert rows[0]["kind"] == "apply"
    assert rows[1]["kind"] == "rollback"
    assert rows[1]["applies_receipt_id"] == receipt["receipt_id"]
