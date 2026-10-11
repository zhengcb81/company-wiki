"""ROOT's behavior regressions for the independent W05 reception findings."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import time
import unittest

from test_pool_progress import (PP, make_state, chain, obs, run_started,
                               executor_sealed, review_done, expert_report,
                               advance, current_entity)


def ready(run="current", attempt="initial"):
    state = make_state()
    return chain(state, run_started(current_entity(state), run, attempt),
                 executor_sealed(run, attempt))


class CausalBindingTests(unittest.TestCase):
    def test_old_run_completion_never_counts_for_new_run(self):
        for kind in ("executor_status", "review_status", "expert_status"):
            with self.subTest(kind=kind):
                state = ready()
                old = {"executor_status": executor_sealed("old"),
                       "review_status": review_done("old", "storage"),
                       "expert_status": expert_report("old", [])}[kind]
                result = PP.reduce_progress(state, old)["new_state"]
                self.assertEqual(result["role_observations"], state["role_observations"])
                self.assertEqual(result["review_conclusions"], state["review_conclusions"])

    def test_old_execution_attempt_never_fills_new_review_slot(self):
        state = ready(attempt="rerun-2")
        old = review_done("current", "storage", attempt="initial",
                          execution_attempt="initial")
        result = chain(state, old)
        self.assertIsNone(result["review_conclusions"]["storage"])

    def test_new_role_attempt_can_reference_same_execution(self):
        state = ready()
        new = review_done("current", "fetch", attempt="reviewer-2",
                          execution_attempt="initial")
        result = chain(state, new)
        self.assertEqual(result["review_conclusions"]["fetch"]["conclusion"], "PASS")

    def test_late_report_does_not_receive_new_version_stamp(self):
        state = ready()
        before = state["effective_versions"]["digest"]
        state = chain(state, obs("version_change", version_kind="code",
                                 refs=["new-code"], reason="behavior changed"))
        for role in PP.REVIEW_ROLES:
            state = chain(state, review_done("current", role))
        state = chain(state, expert_report("current", []))
        self.assertEqual(state["review_conclusions"]["storage"]["versions_digest"], before)
        self.assertEqual(PP.derive_next_action(state)["action"], "rerun_same_company_after_fix")
        state = chain(state, advance())
        self.assertEqual(state["clean"]["streak"], 0)

    def test_missing_report_reference_never_counts_clean(self):
        for missing in (None, "", "   "):
            with self.subTest(missing=missing):
                state = ready()
                for role in PP.REVIEW_ROLES:
                    state = chain(state, review_done("current", role, report_ref=missing))
                state = chain(state, expert_report("current", []), advance())
                self.assertEqual(state["clean"]["streak"], 0)
                self.assertNotIn(None, state["clean"]["evidence_refs"])

    def test_missing_expert_completion_never_counts_clean(self):
        state = ready()
        for role in PP.REVIEW_ROLES:
            state = chain(state, review_done("current", role))
        state = chain(state, advance())
        self.assertEqual(state["clean"]["streak"], 0)

    def test_unrelated_query_result_does_not_clear_active_writer(self):
        state = ready()
        state = chain(state, obs("review_status", run_id="current", attempt="initial",
                                 role="fetch", status="writer_unknown"))
        state = chain(state, obs("query_result", run_id="old", execution_attempt="initial",
                                 role="fetch", state="stopped"))
        self.assertEqual(state["role_observations"]["fetch"]["status"], "writer_unknown")


class UnknownAndObligationTests(unittest.TestCase):
    def test_reconciliation_without_known_amount_stays_pending(self):
        for outcome in ("unknown", "known"):
            with self.subTest(outcome=outcome):
                state = chain(make_state(), obs("charge_unknown", call_id="paid-1", ref="call-ref"),
                              obs("charge_reconciled", call_id="paid-1", outcome=outcome,
                                  cost_usd=None, evidence_ref="query-ref"))
                action = PP.derive_next_action(state)
                self.assertEqual(action["action"], "reconcile_possible_charge")
                self.assertFalse(action["args"]["resend"])

    def test_zero_is_known_only_when_actually_recorded(self):
        state = chain(make_state(), obs("charge_unknown", call_id="paid-1", ref="call-ref"),
                      obs("charge_reconciled", call_id="paid-1", outcome="known",
                          cost_usd=0, evidence_ref="provider-ledger"))
        self.assertEqual(PP.derive_next_action(state)["action"], "dispatch_executor")

    def test_invalid_amounts_never_become_reconciled(self):
        for cost in (True, -1, float("nan"), float("inf")):
            with self.subTest(cost=cost):
                state = chain(make_state(), obs("charge_unknown", call_id="paid-1", ref="call-ref"))
                with self.assertRaises(ValueError):
                    chain(state, obs("charge_reconciled", call_id="paid-1", outcome="known", cost_usd=cost))

    def test_retest_cannot_close_without_evidence(self):
        for evidence in (None, "", "   "):
            with self.subTest(evidence=evidence):
                state = make_state()
                state["required_retests"] = [{"ref": "old::P1", "done": False,
                                               "entity_key": "old", "reason": "major fix", "evidence_ref": None}]
                try:
                    result = chain(state, obs("retest_done", refs=["old::P1"], evidence_ref=evidence))
                except ValueError:
                    result = state  # Explicit input rejection is also correct.
                self.assertFalse(result["required_retests"][0]["done"])

    def test_last_company_still_has_explicit_close_action(self):
        state = ready()
        state["sampling"]["round_index"] = len(state["sampling"]["draw_order"]) - 1
        state["current_run"]["entity_key"] = current_entity(state)
        for role in PP.REVIEW_ROLES:
            state = chain(state, review_done("current", role))
        state = chain(state, expert_report("current", []))
        self.assertEqual(PP.derive_next_action(state)["action"], "select_next_company")

    def test_old_open_major_cannot_be_swallowed_by_new_clean_samples(self):
        from test_pool_progress import run_company_clean
        state = make_state(pool_name="pool_6_cn.json")
        state = chain(state, obs("finding", run_id="old-run", issue_id="P1",
                                 severity="P1", entity_key="old-company", substantive=True))
        for index in range(3):
            state = run_company_clean(state, f"new-run-{index}")
        self.assertEqual(PP.derive_next_action(state)["action"], "resume_remediation")

    def test_unknown_charge_cannot_be_counted_as_clean_by_direct_close(self):
        state = ready()
        for role in PP.REVIEW_ROLES:
            state = chain(state, review_done("current", role))
        state = chain(state, expert_report("current", []),
                      obs("charge_unknown", call_id="paid-1", ref="call-ref"), advance())
        self.assertEqual(state["clean"]["streak"], 0)


class ArtifactAndMutexTests(unittest.TestCase):
    def test_plan_never_overwrites_any_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = root / "state.json"
            observation = root / "observation.json"
            state.write_text(json.dumps(make_state()), encoding="utf-8")
            observation.write_text(json.dumps(obs("request_next")), encoding="utf-8")
            history = root / "old-plan.json"
            history.write_bytes(b"old evidence")
            for target in (state, observation, history):
                with self.subTest(target=target.name):
                    original = target.read_bytes()
                    with self.assertRaises(ValueError):
                        PP.plan_observation(state, observation, target)
                    self.assertEqual(target.read_bytes(), original)

    def test_migration_cannot_overwrite_pool_or_old_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            campaign, pool, old = [root / name for name in ("campaign.json", "pool.json", "old.json")]
            campaign.write_text("{}", encoding="utf-8")
            from test_pool_progress import fixture_bytes
            pool.write_bytes(fixture_bytes("pool_6_entities.json"))
            old.write_bytes(b"keep history")
            for target in (pool, old):
                with self.subTest(target=target.name):
                    original = target.read_bytes()
                    with self.assertRaises(ValueError):
                        PP.migrate_preview_command(campaign, pool, target)
                    self.assertEqual(target.read_bytes(), original)

    def test_live_lock_cannot_be_stolen_by_age(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.json"
            first = PP.StateLock(path, timeout=0.1, stale=0.01)
            with first:
                old = time.time() - 100
                os.utime(first.path, (old, old))
                with self.assertRaises(PP.LockTimeout):
                    PP.StateLock(path, timeout=0.1, stale=0.01).acquire()
            with PP.StateLock(path, timeout=0.1, stale=0.01):
                pass

    def test_lock_rejects_unbounded_time_values(self):
        for value in (float("nan"), float("inf"), -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PP.StateLock(Path("unused"), timeout=value)

    def test_process_death_releases_lock_without_stale_wait(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state, marker = root / "state.json", root / "ready"
            code = ("import importlib.util,time; from pathlib import Path; "
                    f"s=importlib.util.spec_from_file_location('lock_child',{str(Path(PP.__file__))!r}); "
                    "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                    f"lock=m.StateLock({str(state)!r}); lock.acquire(); "
                    f"Path({str(marker)!r}).write_text('ready'); time.sleep(15)")
            child = subprocess.Popen([sys.executable, "-B", "-c", code],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 5
                while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(marker.exists(), "actual child must hold the lock")
                child.terminate()
                child.wait(timeout=5)
                with PP.StateLock(state, timeout=0.2, stale=3600):
                    pass
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
