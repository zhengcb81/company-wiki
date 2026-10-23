"""Current limits are policy; immutable old metadata remains accounting input."""
import json

from tools.document_understanding_benchmark import phase_c_runner as runner


def test_new_policy_keeps_old_charges_and_unknown_holds(tmp_path):
    metadata = tmp_path / "metadata.json"
    usage = tmp_path / "usage.jsonl"
    policy = tmp_path / "policy.yaml"
    metadata.write_text(json.dumps({"mother_budget": {
        "prior_charged_tokens": 1_500_000, "prior_charged_micro_usd": 600_000,
        "retained_fx_hold_micro_usd": 2_000,
        "old_unknown_hold_count_already_in_baseline": 7,
        "token_limit": 2_000_000, "micro_usd_limit": 20_000_000,
    }}), encoding="utf-8")
    hold = {"kind": "native_model_charge", "mode": "live", "database": "owned/AUTO.sqlite",
            "attempt_id": "uncertain", "usage_status": "unknown",
            "charged_tokens": 60_000, "charged_micro_usd": 30_000}
    usage.write_text(json.dumps(hold) + "\n" + json.dumps(hold) + "\n", encoding="utf-8")
    policy.write_text("""schema_version: company-wiki-budget-policy/1
external_model:
  cumulative_tokens: 10000000
  cumulative_micro_usd: 20000000
company_allocation:
  enforcement: soft
  target_tokens: 150000
  target_micro_usd: 1000000
document_processing:
  max_work_units: 16000000
""", encoding="utf-8")
    before = {path: path.read_bytes() for path in (metadata, usage, policy)}
    totals = runner.mother_totals(metadata, usage, budget_policy_path=policy)
    assert totals["charged_tokens"] == 1_560_000
    assert totals["charged_micro_usd"] == 632_000
    assert totals["new_unknown_count"] == 1 and totals["prior_unknown7_retained"] == 7
    assert totals["token_limit"] == 10_000_000
    assert totals["micro_usd_limit"] == 20_000_000
    assert runner.mother_budget_fits(totals, tokens_bound=1_000_000, micro_usd_bound=100_000)
    assert not runner.mother_budget_fits(totals, tokens_bound=8_440_001, micro_usd_bound=0)
    assert not runner.mother_budget_fits(totals, tokens_bound=0, micro_usd_bound=19_368_001)
    assert {path: path.read_bytes() for path in before} == before


def test_existing_current_entry_reads_policy_instead_of_frozen_old_ceiling(tmp_path, monkeypatch):
    metadata = tmp_path / "metadata.json"
    usage = tmp_path / "usage.jsonl"
    policy = tmp_path / "policy.yaml"
    metadata.write_text(json.dumps({"mother_budget": {
        "prior_charged_tokens": 100, "prior_charged_micro_usd": 200,
        "retained_fx_hold_micro_usd": 50, "token_limit": 100,
        "micro_usd_limit": 250, "old_unknown_hold_count_already_in_baseline": 7,
    }}), encoding="utf-8")
    usage.write_text("", encoding="utf-8")
    policy.write_text("""schema_version: company-wiki-budget-policy/1
external_model: {cumulative_tokens: 900, cumulative_micro_usd: 1100}
company_allocation: {enforcement: soft, target_tokens: 2, target_micro_usd: 3}
document_processing: {max_work_units: 16000000}
""", encoding="utf-8")
    monkeypatch.setenv("COMPANY_WIKI_BUDGET_CONFIG", str(policy))
    totals = runner.mother_totals(metadata, usage)
    assert totals["charged_tokens"] == 100 and totals["charged_micro_usd"] == 250
    assert runner.mother_budget_fits(totals, tokens_bound=800, micro_usd_bound=850)
    assert not runner.mother_budget_fits(totals, tokens_bound=801, micro_usd_bound=0)
