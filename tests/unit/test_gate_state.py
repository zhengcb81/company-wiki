import hashlib
import json
from pathlib import Path

from gate_state import derive_state


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def passing_receipt(path: Path) -> None:
    write_json(
        path,
        {
            "work_unit": "WU-1",
            "result": "pass",
            "status": "candidate",
            "workspace_digest": "tree-123",
        },
    )


def test_pass_receipt_without_review_stays_candidate(tmp_path):
    receipt = tmp_path / "receipt.json"
    passing_receipt(receipt)
    result = derive_state(receipt)
    assert result["state"] == "candidate"


def test_matching_independent_approval_derives_verified(tmp_path):
    receipt = tmp_path / "receipt.json"
    passing_receipt(receipt)
    review = tmp_path / "review.json"
    write_json(
        review,
        {
            "receipt_sha256": sha256(receipt),
            "decision": "approved",
            "reviewer": "independent-review-task",
            "independent": True,
        },
    )
    result = derive_state(receipt, review)
    assert result["state"] == "verified"


def test_review_for_different_receipt_is_rejected(tmp_path):
    receipt = tmp_path / "receipt.json"
    passing_receipt(receipt)
    review = tmp_path / "review.json"
    write_json(
        review,
        {
            "receipt_sha256": "forged",
            "decision": "approved",
            "reviewer": "independent-review-task",
            "independent": True,
        },
    )
    result = derive_state(receipt, review)
    assert result["state"] == "rejected"
    assert "review does not bind to this receipt SHA-256" in result["violations"]


def test_failed_candidate_cannot_be_approved(tmp_path):
    receipt = tmp_path / "receipt.json"
    write_json(
        receipt,
        {
            "work_unit": "WU-1",
            "result": "fail",
            "status": "rejected",
            "workspace_digest": "tree-123",
        },
    )
    review = tmp_path / "review.json"
    write_json(
        review,
        {
            "receipt_sha256": sha256(receipt),
            "decision": "approved",
            "reviewer": "independent-review-task",
            "independent": True,
        },
    )
    assert derive_state(receipt, review)["state"] == "rejected"
