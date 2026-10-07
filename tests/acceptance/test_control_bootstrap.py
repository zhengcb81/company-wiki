"""Regression cases for fixture isolation and honest quality checks.

G5-CWP-CHECKS retired the old control gates, so this acceptance module no
longer imports ``architecture_gate`` / ``clean_env_gate`` / ``semantic_gate``
and ``control/architecture.json`` is gone with them.  What must survive:

* fixture isolation — the migrated helper in
  ``tests/support/isolated_environment.py`` keeps API keys, dotenv and the
  network switched off for the acceptance runtime;
* honest quality — a below-threshold result is computed as a failure and can
  never be relabelled as a pass, and thresholds stay definition-only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TESTS))

from helpers.gold_evaluator import (  # noqa: E402
    evaluate,
    gold_to_perfect_predictions,
    load_gold,
)

CORPUS = TESTS / "fixtures" / "gold_corpus"


def test_migrated_isolation_helper_blocks_repository_dotenv_reload() -> None:
    from support.isolated_environment import sanitized_environment

    environment = sanitized_environment()
    for key in ("MINIMAX_API_KEY", "MIMO_API_KEY", "TAVILY_API_KEY"):
        environment.pop(key, None)
    environment["PYTHONPATH"] = str(SCRIPTS)
    code = (
        "import os, config; config._load_dotenv(); "
        "print(int('MINIMAX_API_KEY' in os.environ), int('MIMO_API_KEY' in os.environ), "
        "int('TAVILY_API_KEY' in os.environ))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "0 0 0"


def test_quality_below_threshold_is_reported_as_failure_not_success() -> None:
    gold = load_gold(CORPUS)
    perfect = gold_to_perfect_predictions(gold)
    ceiling = evaluate(perfect, gold)
    assert ceiling["all_critical_pass"] is True

    claim = next(item for item in perfect["claims"] if item.get("numeric"))
    claim["numeric"] = None
    degraded = evaluate(perfect, gold)

    assert (
        degraded["metrics"]["numeric_exactness"]
        < degraded["thresholds"]["numeric_exactness"]
    )
    assert degraded["all_critical_pass"] is False
    assert "numeric_exactness" in {
        failure["metric"] for failure in degraded["failures"]
    }


def test_thresholds_stay_definition_only_so_status_cannot_override_them() -> None:
    document = json.loads(
        (CORPUS / "expected" / "quality_metrics.json").read_text(encoding="utf-8")
    )
    serialized = json.dumps(document, ensure_ascii=False)
    for forbidden in ("actual", "status", "ready_for_canary"):
        assert f'"{forbidden}"' not in serialized, forbidden
    assert "handwritten" not in serialized


def test_acceptance_runtime_never_carries_repository_credentials() -> None:
    for name in (
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "MINIMAX_API_KEY",
        "MIMO_API_KEY",
        "TAVILY_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        assert os.environ.get(name) is None, name
    assert os.environ.get("PYTHON_DOTENV_DISABLED") == "1"
    assert os.environ.get("COMPANY_WIKI_NETWORK") == "blocked"
    assert os.environ.get("COMPANY_WIKI_REAL_LLM") == "0"
