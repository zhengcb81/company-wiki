"""Causal feedback across independent owner ports, exercised with no real side effects."""

from collections import Counter
import json

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
