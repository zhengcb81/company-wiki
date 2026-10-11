"""Freeze intake's exact invalid response vectors as formal business REDs."""
from pathlib import Path

tree = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w06\ff-contract-matrix-root")
target = tree / "tests/test_w06_contract_matrix.py"
text = target.read_text(encoding="utf-8")
assert "test_wrong_downloaded_quarter_cannot_pass" not in text
text += '''


class _ControlledContext:
    def __init__(self, tmp_path, responses):
        from types import SimpleNamespace
        self.artifacts = tmp_path
        self.responses = iter(responses)
        self.env = SimpleNamespace(calls_file=lambda name: tmp_path/(name+".jsonl"))

    def write_state(self, **kwargs):
        return None

    def run_ff(self, *args, **kwargs):
        return {"response": next(self.responses), "exit_code": 0,
                "request_ref": "req.json", "response_ref": "resp.json"}

    def fixture_requests(self, path):
        return 0

    def worker_ran(self, path):
        return False


def test_wrong_downloaded_quarter_cannot_pass(tmp_path):
    import matrix_cases as cases
    ctx = _ControlledContext(tmp_path, [{"transcript": {
        "status": "downloaded", "fiscal_quarter": 2, "source_ref": {"document_id": "x"}}}])
    assert cases.case_call_wrong_quarter(ctx).result != "PASS"


def test_explicit_quarter_rejection_remains_valid_positive_control(tmp_path):
    import matrix_cases as cases
    ctx = _ControlledContext(tmp_path, [{"transcript": {
        "status": "provider_unavailable", "reason": "quarter_mismatch"}}])
    assert cases.case_call_wrong_quarter(ctx).result == "PASS"


def test_unrelated_upstream_error_cannot_prove_cutoff(tmp_path):
    import matrix_cases as cases
    ctx = _ControlledContext(tmp_path, [{"transcript": {
        "status": "upstream_error", "reason": "arbitrary_import_failure"}}])
    assert cases.case_call_past_cutoff(ctx).result != "PASS"


def test_repeated_download_without_source_ref_cannot_prove_reuse(tmp_path):
    import matrix_cases as cases
    from fixture_builder import HK
    response = {"status": "source_candidate", "filing": {
        "resolution_outcome": "downloaded_new", "download_events": 0}}
    ctx = _ControlledContext(tmp_path, [response, response])
    assert cases.case_fin_fetch(ctx, HK, "annual_report", 2026, "negative").result != "PASS"


def test_unknown_usage_even_incomplete_cannot_render_zero(tmp_path):
    import matrix_cases as cases
    ctx = _ControlledContext(tmp_path, [{"transcript": {
        "status": "upstream_error", "reason": "provider_loss",
        "provider_usage_complete": False, "provider_requests": 0}}])
    assert cases.case_err_unknown_usage(ctx).result != "PASS"


def test_empty_unbound_matrix_cannot_pass_oracle():
    report = _report([])
    report["code_binding"] = {"verified": False}
    assert not oracle_mod.passes(oracle_mod.audit(report))


def test_null_run2_counter_is_not_measured_zero():
    case = _case("unknown_reuse", expected={"run_twice": True},
                 counters={"fixture_requests": 1, "run2_fixture_requests": None})
    assert any(f.vector == "second_run_still_downloads" for f in oracle_mod.audit(_report([case])))


def test_actual_unknown_zero_not_boolean_self_declaration():
    case = _case("unknown_usage", expected={"unknown_usage": True}, actual={
        "provider_usage_complete": False, "provider_requests": 0,
        "unknown_usage_reported_as_zero": False, "calls_swallowed": False})
    assert any(f.vector == "fake_zero_cost" for f in oracle_mod.audit(_report([case])))
'''
target.write_text(text, encoding="utf-8")
print("Added exact pure/helper response/oracle business regressions plus positive quarter control.")
