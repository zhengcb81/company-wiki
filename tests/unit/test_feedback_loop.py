"""Causal feedback across independent owner ports, exercised with no real side effects."""

from collections import Counter
import json

import pytest

from tools.feedback_loop.coordinator import advance
from tools.feedback_loop.observations import read_batch


def event(**changes):
    observation = dict(schema_version="feedback-observation/1", owner="source", origin_owner="analyst",
                       run_id="one", attempt_id="a", step_id="read", check_id="attribution",
                       expected="qualified", actual="subject-lost", evidence_ref="claim-2")
    return {**observation, **changes}


def batch(tmp_path, *rows):
    path = tmp_path / "cases.jsonl"
    path.write_bytes(b"".join((r if isinstance(r, bytes) else json.dumps(r).encode()) + b"\n" for r in rows))
    return read_batch([path])


class NativeJobs:
    """A durable get/submit host across multiple coordinator ticks."""

    def __init__(self):
        self.jobs = {}
        self.started = Counter()
        self.targets = []
        self.results = {
            "observe": {"recorded": True},
            "triage": {"decision": "repair", "issue_ref": "src/27", "generation": "fix-1"},
            "repair": {"fixed_version": "published-fix"},
            "replay": {"verdict": "verified", "verified_version": "published-fix", "evidence_ref": "consumer/replay"},
            "report": {"recorded": True},
        }
        self.lose_reply = None

    def __call__(self, owner, request):
        key, kind = request["action_id"], request["kind"]
        reply = dict(schema_version="feedback-action-result/1", action_id=key,
                     request_digest=request["request_digest"], state="absent")
        if request["method"] == "lookup":
            return self.jobs.get(key, reply)
        assert request["method"] == "submit" and key not in self.jobs
        self.targets.append((kind, owner))
        self.started[kind] += 1
        self.jobs[key] = {**reply, "state": "done", "result": self.results[kind]}
        if self.lose_reply == kind:
            self.lose_reply = None
            raise TimeoutError("lost the reply after the job was recorded")
        return self.jobs[key]


def test_same_observation_deduplicates_and_shared_repair_replays_each_origin(tmp_path):
    first = event()
    cases = batch(tmp_path, first, first, event(run_id="two", origin_owner="dashboard"),
                  event(run_id="ok", actual="qualified"), event(run_id="cost", disposition="unknown"))
    host = NativeJobs()
    first_pass = advance(cases, host)
    assert sorted(row["status"] for row in first_pass["observations"]) == ["expected", "unknown", "verified", "verified"]
    assert host.started == {"observe": 4, "triage": 2, "repair": 1, "replay": 2, "report": 2}
    assert ("replay", "dashboard") in host.targets and ("replay", "analyst") in host.targets
    assert first_pass == advance(cases, host)
    assert host.started["repair"] == 1


def test_resume_reconciles_lost_reply_and_never_restarts_repair(tmp_path):
    cases = batch(tmp_path, event())
    host = NativeJobs()
    host.lose_reply = "repair"
    assert advance(cases, host)["observations"][0]["status"] == "unknown"
    assert host.started == {"observe": 1, "triage": 1, "repair": 1}
    assert advance(cases, host)["observations"][0]["status"] == "verified"
    assert host.started == {"observe": 1, "triage": 1, "repair": 1, "replay": 1, "report": 1}


def test_partial_publication_never_triages_before_its_matching_terminal(tmp_path):
    host = NativeJobs()
    start = event(check_id="action-started", expected="started", actual="started", terminal_check_id="publication-outcome")
    deviation = event()
    other = event(attempt_id="other", check_id="publication-outcome", actual="qualified")
    partial = advance(batch(tmp_path, start, deviation, other), host)
    assert [row["status"] for row in partial["observations"]] == ["unknown", "unknown", "expected"]
    assert host.started == {"observe": 3}
    terminal = event(check_id="publication-outcome", actual="qualified")
    completed = advance(batch(tmp_path, start, deviation, other, terminal), host)
    assert [row["status"] for row in completed["observations"]] == ["expected", "verified", "expected", "expected"]
    assert host.started["triage"] == host.started["repair"] == 1


@pytest.mark.parametrize(("actual", "status"), (("listed", "expected"), ("unknown", "unknown")))
def test_legacy_start_can_gain_its_first_evidence_reference_at_completion(tmp_path, actual, status):
    owner = "stockinfo-dl-simple"
    start = event(owner=owner, check_id="action-started", expected="started", actual="started", evidence_ref=None)
    final = event(owner=owner, check_id="candidate-listing-identity", expected="listed", actual=actual)
    host = NativeJobs()
    observed = advance(batch(tmp_path, start, final), host)["observations"]
    assert [row["status"] for row in observed] == [status, status]
    assert host.started == {"observe": 2}


def test_an_in_file_result_that_conflicts_with_the_ledger_cannot_release_related_triage(tmp_path):
    host = NativeJobs()
    terminal = event(check_id="stage-outcome", actual="qualified")
    recorded = advance(batch(tmp_path, {**terminal, "evidence_ref": "other"}), host)
    assert recorded["observations"][0]["status"] == "expected"
    start = event(check_id="action-started", expected="started", actual="started", terminal_check_id="stage-outcome")
    refusal = event(actual="refused", refusal_code="source_gate")
    observed = advance(batch(tmp_path, refusal, start, terminal), host)["observations"]
    assert [(row["status"], row["step"]) for row in observed] == [
        ("unknown", "reconcile"), ("unknown", "reconcile"), ("unverified", "observe"),
    ]
    assert host.started == {"observe": 3}


def test_replay_of_old_version_cannot_close_issue(tmp_path):
    host = NativeJobs()
    host.results["replay"]["verified_version"] = "old-consumer-cache"
    assert advance(batch(tmp_path, event()), host)["observations"][0]["status"] == "unverified"
    assert host.started["report"] == 0


def test_conflicting_occurrence_is_isolated_and_bad_lines_do_not_hide_valid_observations(tmp_path):
    a = event()
    b = event(actual="another-outcome")
    host = NativeJobs()
    cases = batch(tmp_path, a, b, b"\xff", b'{"broken"', event(run_id="ok", disposition="expected"))
    result = advance(cases, host)
    assert [row["status"] for row in result["observations"]] == ["expected"]
    assert len(result["diagnostics"]) == 3
    assert host.started == {"observe": 1}


def test_expected_refusal_external_and_recurrence(tmp_path):
    host = NativeJobs()
    host.results["triage"] = {"decision": "external"}
    result = advance(batch(tmp_path, event(), event(run_id="corrupt", expected="refused", actual="refused")), host)
    assert {row["status"] for row in result["observations"]} == {"external", "expected"}
    assert host.started == {"observe": 2, "triage": 1}
    host = NativeJobs()
    host.results["replay"]["verdict"] = "regressed"
    assert advance(batch(tmp_path, event()), host)["observations"][0]["status"] == "regressed"
    assert host.started["report"] == 1


def test_marked_refusal_runs_one_durable_gate_review_before_repair(tmp_path):
    refused = event(expected="refused", actual="refused", refusal_code="owner_extent")
    cases = batch(tmp_path, refused)
    host = NativeJobs()
    review = {"decision": "narrow", "reason": "Different layout uses the same verified original",
              "evidence_ref": "source/reproductions/27"}
    host.results["triage"] = {**host.results["triage"], "gate_review": review}
    first = advance(cases, host)
    assert first["observations"][0]["status"] == "verified"
    assert first["observations"][0]["gate_review"] == review
    assert [kind for kind, _ in host.targets] == ["observe", "triage", "repair", "replay", "report"]
    assert advance(cases, host) == first
    assert host.started["triage"] == host.started["repair"] == 1


def test_marked_expected_refusal_preserves_legacy_disposition_without_removal_evidence(tmp_path):
    cases = batch(tmp_path, event(expected="refused", actual="refused", refusal_code="hash_changed"))
    host = NativeJobs()
    for gate_review in (None, {"decision": []}, {"decision": "retain", "reason": "Source bytes changed",
                                                  "evidence_ref": "source/bytes"}):
        host.jobs.clear()
        host.started.clear()
        host.results["triage"]["gate_review"] = gate_review
        assert advance(cases, host)["observations"][0]["status"] == "expected"
        assert host.started == {"observe": 1, "triage": 1}


@pytest.mark.parametrize("decision", ["repair", "fixed", "expected", "external"])
@pytest.mark.parametrize("review", [None, {"decision": "narrow"}, {
    "decision": "needs_evidence", "reason": "Cannot reproduce the refusal yet", "evidence_ref": "source/probe",
}])
def test_unexpected_refusal_needs_a_supported_review_before_resolution(tmp_path, decision, review):
    refused = event(actual="refused", refusal_code="unsupported_document_scope")
    cases = batch(tmp_path, refused)
    host = NativeJobs()
    host.results["triage"].update(decision=decision, fixed_version="published-fix", gate_review=review)

    result = advance(cases, host)

    assert result["observations"][0]["status"] == "needs_evidence"
    assert host.targets == [("observe", "analyst"), ("triage", "source")]
    assert advance(cases, host) == result


@pytest.mark.parametrize("review_decision", ["narrow", "retain"])
def test_unexpected_refusal_with_review_reuses_the_owner_repair_path(tmp_path, review_decision):
    refused = event(actual="refused", refusal_code="unsupported_document_scope")
    cases = batch(tmp_path, refused)
    host = NativeJobs()
    review = {"decision": review_decision, "reason": "Compared the valid and invalid scope",
              "evidence_ref": "source/reproductions/27"}
    host.results["triage"]["gate_review"] = review

    result = advance(cases, host)

    assert result["observations"][0]["status"] == "verified"
    assert result["observations"][0]["gate_review"] == review
    assert host.targets == [("observe", "analyst"), ("triage", "source"), ("repair", "source"),
                            ("replay", "analyst"), ("report", "source")]


def test_gate_review_waits_for_final_actual_refusal_and_ignores_malformed_tags(tmp_path):
    start = event(check_id="action-started", expected="started", actual="started", terminal_check_id="stage-outcome")
    refusal = event(expected="refused", actual="refused", refusal_code="hash_changed")
    host = NativeJobs()
    result = advance(batch(tmp_path, start, refusal), host)
    assert [item["status"] for item in result["observations"]] == ["unknown", "unknown"]
    expected = event(run_id="malformed", expected="refused", actual="refused", refusal_code={"bad": True})
    unconfirmed = event(attempt_id="other", actual="refused", refusal_code="incomplete", disposition="unknown")
    remaining = advance(batch(tmp_path, expected, unconfirmed), host)
    assert [item["status"] for item in remaining["observations"]] == ["expected", "unknown"]
    assert host.started == {"observe": 4}


def test_gate_review_checks_unknown_usage_for_the_same_attempt(tmp_path):
    refusal = event(check_id="stage-outcome", expected="refused", actual="refused",
                    refusal_code="owner_extent")
    start = event(check_id="action-started", expected="started", actual="started",
                  terminal_check_id="stage-outcome")
    usage = event(check_id="job-usage", expected="accounted", actual="unknown")
    host = NativeJobs()
    host.results["triage"]["gate_review"] = {"decision": "narrow", "reason": "False refusal reproduced",
                                             "evidence_ref": "fixture/valid-input"}
    paired = advance(batch(tmp_path, start, refusal, usage), host)
    assert [item["status"] for item in paired["observations"]] == ["expected", "unknown", "unknown"]
    assert host.started == {"observe": 3}
    another = advance(batch(tmp_path, {**refusal, "attempt_id": "new"}, usage), host)
    assert [item["status"] for item in another["observations"]] == ["verified", "unknown"]
    assert host.started["triage"] == host.started["repair"] == 1


def test_no_use_of_previous_result_for_changed_record_in_a_later_tick(tmp_path):
    host = NativeJobs()
    assert advance(batch(tmp_path, event()), host)["observations"][0]["status"] == "verified"
    changed = batch(tmp_path, event(actual="different"))
    assert advance(changed, host)["observations"][0]["status"] == "unverified"
    assert host.started == {"observe": 1, "triage": 1, "repair": 1, "replay": 1, "report": 1}


def test_wrong_initial_owner_refers_without_changing_consumer_and_circular_referral_stops(tmp_path):
    cases = batch(tmp_path, event())
    host = NativeJobs()

    def routing(owner, request):
        if request["kind"] == "triage":
            host.results["triage"] = ({"decision": "refer", "next_owner": "fetch"} if owner == "source"
                                      else {"decision": "repair", "issue_ref": "fetch/2", "generation": "one"})
        return host(owner, request)

    assert advance(cases, routing)["observations"][0]["status"] == "verified"
    assert ("repair", "fetch") in host.targets and ("replay", "analyst") in host.targets
    host = NativeJobs()

    def cycle(owner, request):
        host.results["triage"] = {"decision": "refer", "next_owner": "fetch" if owner == "source" else "source"}
        return host(owner, request)

    assert advance(cases, cycle)["observations"][0]["status"] == "unverified"
    assert host.started == {"observe": 1, "triage": 2}


def test_new_evidence_keeps_original_case_for_replay_after_a_failed_fix(tmp_path):
    host = NativeJobs()
    first = batch(tmp_path, event())
    original = next(iter(first.observations))
    host.results["replay"]["verdict"] = "regressed"
    assert advance(first, host)["observations"][0]["status"] == "regressed"
    host.results.update(triage={"decision": "repair", "issue_ref": "src/27", "generation": "fix-2"},
                        repair={"fixed_version": "fixed-again"},
                        replay={"verdict": "verified", "verified_version": "fixed-again", "evidence_ref": "second/replay"})
    requests = []

    def resumed(owner, request):
        requests.append(request)
        return host(owner, request)

    second = batch(tmp_path, event(attempt_id="after-new-evidence", original_occurrence_id=original))
    assert advance(second, resumed)["observations"][0]["status"] == "verified"
    assert next(r for r in requests if r["kind"] == "replay")["payload"]["original_occurrence_id"] == original
    assert host.started["repair"] == 2


def test_across_batches_all_dispositions_bind_before_repair(tmp_path):
    for first, second in [("expected", "deviation"), ("unknown", "deviation"), ("deviation", "expected")]:
        host = NativeJobs()
        advance(batch(tmp_path, event(disposition=first)), host)
        previous = host.started.copy()
        result = advance(batch(tmp_path, event(disposition=second)), host)
        assert result["observations"][0]["status"] == "unverified"
        assert host.started == previous


def test_usage_unknown_and_confirmed_quality_gap_for_one_native_job(tmp_path):
    host = NativeJobs()
    queries = []

    def monitored(owner, request):
        if request["kind"] == "reconcile":
            assert request["method"] == "lookup"
            queries.append(request["payload"]["observation"]["evidence_ref"])
        if request["kind"] == "replay":
            assert request["payload"]["acquisition"] == "reuse_only"
        return host(owner, request)

    cases = batch(tmp_path, event(check_id="usage", actual="unknown"), event())
    result = advance(cases, monitored)
    assert {r["status"] for r in result["observations"]} == {"unknown", "verified"}
    assert queries == ["claim-2"]
    assert host.started["reconcile"] == 0


def test_started_without_its_terminal_is_reconciled_without_dispatching_work(tmp_path):
    host = NativeJobs()
    queried = []

    def lookup(owner, request):
        if request["kind"] != "reconcile":
            return host(owner, request)
        assert request["method"] == "lookup"
        queried.append(request["payload"]["observation"]["step_id"])
        return {"schema_version": "feedback-action-result/1", "action_id": request["action_id"],
                "request_digest": request["request_digest"], "state": "done",
                "result": {"status": "cost_unknown", "evidence_ref": "ff-job/1/ffjob-123abc123abc",
                           "job_status": "succeeded", "cost_state": "unknown"}}

    start = event(check_id="action-started", expected="started", actual="started", terminal_check_id="job-outcome",
                  evidence_ref="ff-job/1/ffjob-123abc123abc")
    complete = {**start, "step_id": "other-document"}
    budget = {**start, "check_id": "budget", "expected": "metered", "actual": "metered"}
    terminal = {**complete, "check_id": "job-outcome", "expected": "terminal", "actual": "terminal"}
    cases = batch(tmp_path, start, budget, complete, terminal)
    keys = list(cases.observations)
    first = advance(cases, lookup)["observations"]
    assert first[0] == {"occurrence_id": keys[0], "disposition": "expected", "status": "unknown", "step": "reconcile",
                       "evidence_ref": "ff-job/1/ffjob-123abc123abc", "job_status": "succeeded", "cost_state": "unknown"}
    assert [row["status"] for row in first[1:]] == ["expected"] * 3
    assert queried == ["read"]
    assert host.started == {"observe": 4}
    assert advance(batch(tmp_path, start, budget, {**terminal, "step_id": "read"}), lookup)["observations"][0]["status"] == "expected"
    assert queried == ["read"]  # a separately delivered terminal closes the same original start

    changed = {**start, "step_id": "different-native-job", "evidence_ref": "ff-job/1/ffjob-456abc456abc"}
    mismatch = advance(batch(tmp_path, changed), lookup)["observations"][0]
    assert (mismatch["status"], mismatch["step"]) == ("unverified", "reconcile")
    assert queried[-1] == "different-native-job"
