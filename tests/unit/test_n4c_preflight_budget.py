"""The offline report must use explicit campaign limits and retain old charges."""

from __future__ import annotations

import sys

import pytest

from tools import n4c_live_preflight as preflight


@pytest.mark.parametrize(
    ("token_cap", "cost_cap", "tokens_left", "money_left"),
    [(200_000, 100_000, 19_116, 6_587),
     (200_000, 120_000, 19_116, 26_587),
     (60_000, 100_000, -120_884, 6_587)],
)
def test_report_uses_requested_limits_without_refunding_usage(
    token_cap: int, cost_cap: int, tokens_left: int, money_left: int,
) -> None:
    charged = {"charged_tokens": 180_884, "charged_micro_usd": 90_649,
               "unknown_reservations": 7, "unsettled_reservations": 0}
    before = charged.copy()
    facts = preflight.campaign_budget_facts(charged, token_cap, cost_cap)
    assert facts["current_campaign_token_cap"] == token_cap
    assert facts["current_campaign_cost_cap_micro_usd"] == cost_cap
    assert facts["tokens_remaining"] == tokens_left
    assert facts["micro_usd_remaining_after_fx_guard"] == money_left
    assert charged == before


@pytest.mark.parametrize("missing", ["--campaign-token-cap", "--campaign-cost-cap-micro-usd"])
def test_cli_requires_both_limits_before_reading_inputs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], missing: str,
) -> None:
    args = ["preflight", "--rf-root", "not-read", "--rf-head", "a" * 40,
            "--output", "not-written.json"]
    if missing != "--campaign-token-cap":
        args += ["--campaign-token-cap", "200000"]
    if missing != "--campaign-cost-cap-micro-usd":
        args += ["--campaign-cost-cap-micro-usd", "100000"]
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as error:
        preflight.main()
    assert error.value.code == 2
    stderr = capsys.readouterr().err
    assert "following arguments are required" in stderr
    assert missing in stderr
