"""Session-level outcome collection and the final receipt write.

Honesty rules this module enforces:

* ``counts`` mirrors the real pytest summary for ``passed``/``failed``/
  ``skipped``/``checked``; ``not_evaluated`` counts *contract cases* whose
  outcome could not be evaluated (a guard test that establishes this still
  passes, which is why ``limits`` says so explicitly);
* a ``skip`` with no reason is not allowed: it is recorded as a failure and the
  session exit status becomes non-zero;
* a case the ledger calls ``pass`` while pytest reports failure is corrected to
  ``fail`` - a failure is never hidden by bookkeeping;
* at session finish the read-only baseline and the network-guard attempt log are
  re-checked (``_finish_violations``): a write after the last test, or any
  recorded ``p4_network_attempted``, makes the receipt ``fail`` and the exit
  status non-zero even though no single test could observe it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import constants as C
from . import environment as E
from . import netguard
from . import readonly
from .report import LEDGER
from .receipt import build_receipt, counts_from_pytest, write_receipt


@dataclass
class _Outcome:
    outcome: str
    reason: str | None = None


@dataclass
class _Collected:
    outcomes: dict[str, _Outcome] = field(default_factory=dict)
    unreasoned_skips: list[str] = field(default_factory=list)
    teardown_errors: set[str] = field(default_factory=set)

    def reset(self) -> None:
        self.outcomes.clear()
        self.unreasoned_skips.clear()
        self.teardown_errors.clear()


_COLLECTED = _Collected()

# pytest outcome -> contract case status.
_OUTCOME_TO_STATUS = {
    "passed": "pass",
    "failed": "fail",
    "error": "fail",
    "skipped": "skip",
}


def case_name_for(nodeid: str) -> str:
    """Contract case name for a test node: the test function name."""
    tail = nodeid.rsplit("::", 1)[-1]
    return tail.split("[", 1)[0]


def record_outcome(nodeid: str, outcome: str, reason: str | None = None) -> None:
    """Remember one pytest outcome; a skip without a reason is flagged."""
    existing = _COLLECTED.outcomes.get(nodeid)
    if existing is not None and existing.outcome == "failed":
        return
    _COLLECTED.outcomes[nodeid] = _Outcome(outcome=outcome, reason=reason)
    if outcome == "skipped" and not (reason or "").strip():
        _COLLECTED.unreasoned_skips.append(nodeid)


def record_teardown_error(nodeid: str) -> None:
    """Remember a teardown error; pytest counts it as ``error``, not ``passed``.

    The call outcome for this nodeid stays whatever it was - the terminal
    summary prints both (``1 passed, 1 error``), so ``pytest_summary`` adds the
    teardown errors on top instead of overwriting the call result.
    """
    _COLLECTED.teardown_errors.add(nodeid)


def pytest_summary() -> dict[str, int]:
    """pytest's own counters for this session."""
    summary = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
    for item in _COLLECTED.outcomes.values():
        summary[item.outcome] = summary.get(item.outcome, 0) + 1
    summary["error"] = summary.get("error", 0) + len(_COLLECTED.teardown_errors)
    return summary


def reset() -> None:
    _COLLECTED.reset()


def merged_cases() -> list[dict[str, Any]]:
    """Ledger cases (with their checks) merged onto real pytest outcomes."""
    ledger_by_name = {case.name: case for case in LEDGER.cases()}
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    for nodeid, item in _COLLECTED.outcomes.items():
        name = case_name_for(nodeid)
        if name in seen:
            continue
        seen.add(name)
        mapped = _OUTCOME_TO_STATUS.get(item.outcome, "fail")
        case = ledger_by_name.get(name)
        if case is not None:
            payload = case.to_dict()
            # pytest is the authority on failure; the ledger may only add detail.
            if mapped == "fail":
                payload["status"] = "fail"
            elif payload["status"] == "skip" and case.reason is None:
                payload["status"] = mapped
            if payload["status"] == "skip" and not payload.get("reason"):
                payload["reason"] = item.reason or "unspecified skip"
            merged.append(payload)
        else:
            merged.append({
                "name": name,
                "status": mapped,
                "reason": item.reason if mapped == "skip" else None,
                "checks": [],
            })

    # Ledger cases that never corresponded to a test are reported as not evaluated.
    for name, case in ledger_by_name.items():
        if name in seen:
            continue
        payload = case.to_dict()
        if payload["status"] == "skip" and not payload.get("reason"):
            payload["status"] = "not_evaluated"
            payload["reason"] = "case recorded without a corresponding test run"
        merged.append(payload)

    return merged


def build_session_receipt() -> dict[str, Any]:
    cases = merged_cases()
    summary = pytest_summary()
    counts = counts_from_pytest(summary)
    counts["not_evaluated"] = sum(
        1 for case in cases if case.get("status") == "not_evaluated"
    )

    limitations = list(C.LIMITATIONS)
    if counts["not_evaluated"]:
        limitations.append(
            "counts.not_evaluated counts contract cases, not pytest tests; "
            "those guard tests pass while the contract outcome stays "
            "not_evaluated."
        )
    if E.consumer_commands_path() is None:
        limitations.append(
            f"{C.ENV_CONSUMER_COMMANDS} was not set: the ROOT command manifest "
            "was unavailable, so no consumer process was executed."
        )
    if _COLLECTED.unreasoned_skips:
        limitations.append(
            "a skip without a reason was observed and recorded as a failure: "
            + ", ".join(sorted(_COLLECTED.unreasoned_skips))
        )

    receipt = build_receipt(
        cases=cases,
        counts=counts,
        catalog_path=E.catalog_config_path(),
        commands_path=E.consumer_commands_path(),
        limitations=limitations,
    )
    if _COLLECTED.unreasoned_skips:
        receipt["status"] = "fail"
    return receipt


def _finish_violations() -> list[str]:
    """Violations only visible after the last test (card 5.5.5 / section 6 last bullet).

    ``support/readonly.py`` documents that ``finalize`` re-checks the session
    baseline so a write after the last test still fails the run - that promise
    was unimplemented at review time (finding P4-R2), as was the session-scope
    reading of ``p4_network_attempted``: the guard records attempts for the
    whole session but only the deliberate probe ever read them back.  Both are
    checked here, before ``receipt.json`` is written, so this run's own receipt
    write is never mistaken for a violation.
    """
    problems: list[str] = []
    try:
        changed = readonly.verify_unchanged()
    except Exception as exc:  # noqa: BLE001 - a probe that cannot run is a finding too
        problems.append(f"finish-time read-only verification unavailable: {exc}")
    else:
        if changed:
            problems.append(
                "finish-time read-only verification found changes after the last "
                "test: " + ", ".join(changed)
            )
    attempts = netguard.attempts()
    if attempts:
        problems.append(
            "network attempts recorded by the lane guard during the session "
            f"({C.CODE_NETWORK_ATTEMPTED}): " + ", ".join(sorted(set(attempts)))
        )
    return problems


def finalize(session) -> Path | None:  # noqa: ANN001 - pytest session object
    """Write ``receipt.json`` for this run; never raise out of a pytest hook."""
    try:
        receipt = build_session_receipt()
    except Exception:  # noqa: BLE001 - a receipt must not mask the test results
        return None
    violations = _finish_violations()
    if violations:
        receipt["limitations"].extend(violations)
        receipt["status"] = "fail"
        session.exitstatus = 1
    if _COLLECTED.unreasoned_skips:
        session.exitstatus = 1
    try:
        return write_receipt(receipt)
    except OSError:
        return None
