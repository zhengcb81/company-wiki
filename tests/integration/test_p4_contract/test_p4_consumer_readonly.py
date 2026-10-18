"""Card sections 5.2 / 6: the consumer manifest gate and the read-only proof.

Without ROOT's ``p4-consumer-commands/1`` no consumer process is executed: the
case is ``not_evaluated`` with a reason and the receipt stays ``partial`` -
never ``pass``.  When repositories are provided, ``HEAD`` and
``git status --porcelain`` must be identical before and after every read.
"""

from __future__ import annotations

from .support import consumer, readonly, sessionreport
from .support import constants as C
from .support import environment as E
from .support import receipt as receipt_mod


def test_p4_missing_manifest_is_not_evaluated(p4_case) -> None:
    """No ROOT manifest means not_evaluated + partial, never a pass."""
    case = p4_case()
    if E.consumer_commands_path() is not None:
        case.check("manifest_absence", "not_applicable",
                   {"reason": "a consumer manifest was provided"})
        case.settle("pass")
        return

    case.check("consumer_manifest_missing", "not_evaluated",
               {"reason": C.REQUIRE_COMMANDS_REASON})
    case.settle("not_evaluated", C.REQUIRE_COMMANDS_REASON)

    counts = {"checked": 0, "passed": 0, "failed": 0,
              "skipped": 0, "not_evaluated": 1}
    status = receipt_mod.top_level_status(counts, blocked_reason=None)
    assert status == "partial", (
        "an unevaluated consumer manifest must leave the receipt partial; "
        f"got {status!r}"
    )
    assert status != "pass" and status != "ok", (
        "not_evaluated must never be reported as a pass"
    )


def test_p4_unreasoned_skip_is_rejected(p4_case) -> None:
    """The ledger refuses a ``skip``/``not_evaluated`` that carries no reason."""
    case = p4_case()
    from .support.report import Case, LedgerError

    record = Case("p4_probe_unreasoned")
    try:
        record.check("probe", "not_evaluated", {})
    except LedgerError as exc:
        assert "requires a reason" in str(exc), (
            f"the refusal must name the missing reason; got {exc}"
        )
    else:
        raise AssertionError("a not_evaluated check without a reason must be refused")

    record.settle("pass")
    case.check("unreasoned_skip_refused", "pass",
               {"reason": "LedgerError raised as designed"})
    case.settle("pass")


def test_p4_cross_repo_readonly(p4_case) -> None:
    """Worktree, fixtures tree and consumer repos are byte-identical so far."""
    case = p4_case()
    base = readonly.baseline()
    assert base is not None, (
        "pytest_sessionstart must capture a baseline before any case runs"
    )
    delta = readonly.diff(base, readonly.current())
    case.check("cross_repo_readonly", "fail" if delta["changed"] else "pass",
               {"changed": delta["changed"]})
    assert delta["changed"] == [], (
        "the lane must not write into the worktree, fixtures or consumer repos; "
        f"changed: {delta['changed']}"
    )
    case.settle("pass")


def test_p4_read_before_after_are_identical(
    p4_case, p4_catalog_config, p4_sources, p4_consumer_specs
) -> None:
    """``HEAD`` and porcelain status survive a full reader/exporter pass."""
    case = p4_case()
    before = readonly.current()
    if p4_consumer_specs is None:
        case.check("consumer_run_readonly", "not_evaluated",
                   {"reason": C.REQUIRE_COMMANDS_REASON})
    else:
        item = p4_sources[0]
        for name, spec in p4_consumer_specs.items():
            run = consumer.run_consumer(
                spec,
                catalog=p4_catalog_config,
                document_id=item["document_id"],
                source_id=item["source_id"],
                content_sha256=item["content_sha256"],
            )
            parsed = consumer.parse_observation(run)
            case.check(f"consumer_observation::{name}",
                       "not_evaluated" if parsed.observation is None else "pass",
                       {"reason": parsed.reason, "stdout_sha256": parsed.stdout_sha256})
    after = readonly.current()
    delta = readonly.diff(before, after)
    case.check("read_only_during_consumer_run",
               "fail" if delta["changed"] else "pass",
               {"changed": delta["changed"]})
    assert delta["changed"] == [], (
        f"a read changed repository state: {delta['changed']}"
    )
    if p4_consumer_specs is None:
        case.settle("not_evaluated", C.REQUIRE_COMMANDS_REASON)
    else:
        case.settle("pass")


def test_p4_receipt_counts_match_pytest_summary(p4_case) -> None:
    """Receipt counters mirror the real session summary, not invented numbers."""
    case = p4_case()
    summary = sessionreport.pytest_summary()
    counts = receipt_mod.counts_from_pytest(summary)
    assert counts["checked"] == counts["passed"] + counts["failed"], (
        f"checked must equal passed+failed; got {counts!r}"
    )
    assert counts["failed"] == summary.get("failed", 0) + summary.get("error", 0), (
        f"failed must fold pytest failed+error; got {counts!r} vs {summary!r}"
    )
    assert counts["skipped"] == summary.get("skipped", 0), (
        f"skipped must match pytest; got {counts!r} vs {summary!r}"
    )
    assert sum(summary.values()) > 0, (
        "no pytest outcome was recorded - pytest_runtest_logreport must feed "
        "sessionreport.record_outcome"
    )
    case.check("counts_match_pytest_summary", "pass", {
        "summary": summary, "counts": counts,
    })
    case.settle("pass")


def test_p4_not_evaluated_is_not_written_as_pass(p4_case) -> None:
    """A ledger case left not_evaluated stays not_evaluated after the merge."""
    case = p4_case()
    from .support.report import LEDGER

    LEDGER.case("p4_probe_never_ran").settle(
        "not_evaluated", C.REQUIRE_COMMANDS_REASON
    )
    merged = {item["name"]: item for item in sessionreport.merged_cases()}
    probe = merged.get("p4_probe_never_ran")
    assert probe is not None, "a ledger-only case must still appear in the merge"
    assert probe["status"] == "not_evaluated", (
        f"ledger-only cases must merge as not_evaluated; got {probe['status']!r}"
    )
    assert probe["reason"], "the merged case must keep its reason"
    case.check("not_evaluated_not_promoted", "pass",
               {"reason": C.REQUIRE_COMMANDS_REASON})
    case.settle("pass")
