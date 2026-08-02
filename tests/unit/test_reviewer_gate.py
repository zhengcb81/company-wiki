from reviewer_gate import evaluate_review


def receipt(workspace="tree", result="pass", status="candidate"):
    return {"work_unit": "WU-1", "workspace_digest": workspace, "result": result, "status": status}


def test_independent_matching_rerun_is_approved():
    review = evaluate_review(receipt(), receipt(), "candidate-hash", "rerun-hash", "reviewer", "implementer")
    assert review["decision"] == "approved"
    assert review["independent"] is True


def test_same_reviewer_and_implementer_is_rejected():
    review = evaluate_review(receipt(), receipt(), "a", "b", "same", "same")
    assert review["decision"] == "rejected"


def test_workspace_drift_is_rejected():
    review = evaluate_review(receipt("before"), receipt("after"), "a", "b", "reviewer", "implementer")
    assert review["decision"] == "rejected"
    assert "workspace digest differs between candidate and rerun" in review["findings"]


def test_failed_rerun_is_rejected():
    review = evaluate_review(receipt(), receipt(result="fail", status="rejected"), "a", "b", "reviewer", "implementer")
    assert review["decision"] == "rejected"
