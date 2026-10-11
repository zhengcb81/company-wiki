"""Apply the root-cause reception fixes only to ROOT's isolated Audit tree."""
import hashlib
from pathlib import Path

ROOT = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop-root")
PATH = ROOT / "skills/revenue-forecast-audit/scripts/pool_progress.py"
raw = PATH.read_bytes()
assert hashlib.sha256(raw).hexdigest() == "03f0d33b9233aac894d415e26406e4ccec22caa2b955adcb678856ca5836ce51"
text = raw.decode().replace("\r\n", "\n")


def replace(old, new):
    global text
    assert text.count(old) == 1, old[:100]
    text = text.replace(old, new)


replace("import json\n", "import json\nimport math\n")
replace('        require(cost is None or isinstance(cost, (int, float)),\n                "cost_usd must be a number or null")',
        '        require(cost is None or (not isinstance(cost, bool) and isinstance(cost, (int, float))\n                                 and math.isfinite(cost) and cost >= 0),\n                "cost_usd must be a finite nonnegative number or null")')
replace('                                "attempt": observation["attempt"]}\n',
        '                                "attempt": observation["attempt"],\n                                "versions_digest": new_state["effective_versions"]["digest"]}\n')
replace('    if status == "completed":\n        new_state["review_conclusions"][role] = {',
        '''    if status == "completed":
        report_ref = observation.get("report_ref")
        if not isinstance(report_ref, str) or not report_ref.strip():
            new_state["review_conclusions"][role] = None
            diagnostics.append(_diag("review_report_reference_missing",
                                     f"{role} completion lacks its report reference; not a clean conclusion"))
            return
        new_state["review_conclusions"][role] = {''')
replace('            "versions_digest": new_state["effective_versions"]["digest"],\n',
        '            "versions_digest": observation.get("versions_digest",\n                                        new_state["current_run"].get("versions_digest")),\n            "run_id": observation["run_id"],\n            "execution_attempt": new_state["current_run"]["attempt"],\n')
replace('    evidence = _bounded_text(observation.get("evidence_ref") or "unspecified",\n                             "evidence_ref")',
        '''    evidence = observation.get("evidence_ref")
    if not isinstance(evidence, str) or not evidence.strip():
        diagnostics.append(_diag("retest_evidence_missing",
                                 "retest completion without evidence leaves the obligation open"))
        return
    evidence = _bounded_text(evidence, "evidence_ref")''')
replace('        if entry["state"] == "unknown"]', '        if entry.get("cost_usd") is None]') if '        if entry["state"] == "unknown"]' in text else replace('state["possibly_paid_invocation_refs"] if entry["state"] == "unknown"]', 'state["possibly_paid_invocation_refs"] if entry.get("cost_usd") is None]')
replace('    conclusions = state["review_conclusions"]\n    missing =',
        '''    run = state.get("current_run") or {}
    if executor and (executor.get("run_id") != run.get("run_id")
                     or executor.get("attempt") != run.get("attempt")):
        reasons.append("executor_scope_mismatch")
    expert = state["role_observations"]["expert"]
    if not expert or expert.get("status") != "completed" or not expert.get("refs"):
        reasons.append("expert_not_completed")
    conclusions = state["review_conclusions"]
    missing =''')
replace('        if entry["conclusion"] not in ("PASS", "N_A"):',
        '''        if not isinstance(entry.get("report_ref"), str) or not entry["report_ref"].strip():
            reasons.append("review_report_reference_missing")
        if entry.get("run_id") != run.get("run_id") or entry.get("execution_attempt") != run.get("attempt"):
            reasons.append("review_scope_mismatch")
        if entry["conclusion"] not in ("PASS", "N_A"):''')
replace('    _HANDLERS[observation["kind"]](new_state, observation, diagnostics)',
        '''    if _observation_matches_run(new_state, observation, diagnostics):
        _HANDLERS[observation["kind"]](new_state, observation, diagnostics)''')
insert = '''def _observation_matches_run(state, observation, diagnostics):
    """Bind run events once at the reducer boundary; no identity/permission gate."""
    kind = observation["kind"]
    if kind not in ("executor_status", "review_status", "expert_status",
                    "records_status", "query_result"):
        return True
    run = state.get("current_run")
    execution_attempt = observation.get("execution_attempt", observation.get("attempt"))
    if kind == "records_status" and execution_attempt is None and run:
        execution_attempt = run["attempt"]  # Structural-only historical observation.
    if not run or observation.get("run_id") != run["run_id"] or execution_attempt != run["attempt"]:
        diagnostics.append(_diag("stale_run_observation_ignored",
                                 "observation belongs to another run/execution attempt; current slots unchanged"))
        return False
    declared_version = observation.get("versions_digest")
    if declared_version is not None and declared_version != run.get("versions_digest"):
        diagnostics.append(_diag("report_version_mismatch",
                                 "report effective version differs from its execution; not relabeled current"))
        return False
    return True


'''
replace('def _bound_diagnostics(rows):\n', insert + 'def _bound_diagnostics(rows):\n')
replace('    executor = state["role_observations"]["executor"]\n    if run is None:',
        '''    executor = state["role_observations"]["executor"]
    if run and run.get("versions_digest") != state["effective_versions"]["digest"]:
        return {"action": "rerun_same_company_after_fix",
                "why": "execution belongs to an older effective version; rerun this company, not a new sample",
                "args": {"entity_key": run["entity_key"], "run_id": run["run_id"]}}
    if run is None:''')
replace('    if nxt is None:\n        return {"action": "no_action",\n                "why": "company closeable but the pool is exhausted after it",\n                "args": {}}',
        '''    if nxt is None:
        return {"action": "select_next_company",
                "why": "apply advance_round to close the final company; pool exhaustion alone is not quality success",
                "args": {"entity_key": None, "close_current": True}}''')
replace('def write_state_atomic(path, data):', 'def write_state_atomic(path, data, *, replace_existing=True):')
replace('        os.replace(staged, path)',
        '''        if replace_existing:
            os.replace(staged, path)
        else:
            os.link(staged, path)  # Atomic create-if-absent, including concurrent init/plan.
            staged.unlink()''')
replace('    write_state_atomic(out_path, state)', '    write_state_atomic(out_path, state, replace_existing=False)')
replace('    write_state_atomic(out_path, plan)', '    write_state_atomic(out_path, plan, replace_existing=False)')
replace('    write_state_atomic(out_path, preview)', '    write_state_atomic(out_path, preview, replace_existing=False)')
replace('    state = _load_state_file(state_path)\n    observation = _read_observation(observation_path)',
        '''    require(not Path(out_path).exists(), "plan output occupied; choose a new path, never overwrite state or history")
    state = _load_state_file(state_path)
    observation = _read_observation(observation_path)''')
replace('    preview = migrate_campaign_preview(campaign_path.read_bytes(),',
        '''    require(not out_path.exists(), "migration output occupied; choose a new path, preserve all old inputs")
    preview = migrate_campaign_preview(campaign_path.read_bytes(),''')
start, end = text.index("class StateLock:"), text.index("def _read_observation(source):")
text = text[:start] + '''class StateLock:
    """Kernel file lock: process death releases it; age never steals a live lock.

    The tiny lock file stays present. Unlinking it could create two lock domains.
    `stale` remains a compatible CLI argument but no longer controls ownership.
    """

    def __init__(self, state_path, timeout=DEFAULT_LOCK_TIMEOUT, stale=DEFAULT_LOCK_STALE):
        require(isinstance(timeout, (int, float)) and not isinstance(timeout, bool)
                and math.isfinite(timeout) and timeout >= 0, "lock timeout must be finite and nonnegative")
        require(isinstance(stale, (int, float)) and math.isfinite(stale) and stale >= 0,
                "legacy lock stale argument must be finite and nonnegative")
        self.path = Path(str(state_path) + LOCK_SUFFIX)
        self.timeout = timeout
        self.stale = stale
        self._handle = None

    def acquire(self):
        require(self._handle is None, "lock already acquired")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        if self.path.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                if time.monotonic() >= deadline:
                    handle.close()
                    raise LockTimeout(f"state lock {self.path} held by another process; timeout {self.timeout}s") from None
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
                continue
            self._handle = handle
            return

    def release(self):
        handle, self._handle = self._handle, None
        if handle is not None:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False


''' + text[end:]
PATH.write_bytes(text.encode())

# Adjust only fixtures which depended on the proven incorrect protocol.
unit = ROOT / "tests/test_pool_progress.py"
body = unit.read_text(encoding="utf-8")
for value in ("unknown", "stopped"):
    body = body.replace(f'obs("query_result", role="fetch", state="{value}")',
                        f'obs("query_result", run_id="run-1", execution_attempt="initial", role="fetch", state="{value}")')
unit.write_bytes(body.encode())
cli = ROOT / "tests/test_pool_progress_cli.py"
body = cli.read_text(encoding="utf-8")
start, end = body.index("    def test_lock_timeout_then_stale_steal(self):"), body.index("\n\nclass AtomicFailureTests")
body = body[:start] + '''    def test_live_kernel_lock_times_out_then_releases(self):
        observation = self.run_started_file()
        with PP.StateLock(self.state):
            lock = Path(str(self.state) + PP.LOCK_SUFFIX)
            old = time.time() - 120
            os.utime(lock, (old, old))
            held = self.apply(observation, "evt-1", 0, "--lock-timeout", 0.1, "--lock-stale", 0.01)
            self.assertEqual(held.returncode, PP.EXIT_LOCK_TIMEOUT, held.stderr)
            self.assertEqual(json.loads(self.state.read_text(encoding="utf-8"))["revision"], 0)
        recovered = self.apply(observation, "evt-1", 0, "--lock-timeout", 2)
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertEqual(json.loads(self.state.read_text(encoding="utf-8"))["revision"], 1)
        self.assertTrue(lock.exists())  # Persistent tiny file, released OS ownership.
''' + body[end:]
cli.write_bytes(body.encode())
e2e = ROOT / "tools/run_pool_progress_e2e.py"
body = e2e.read_text(encoding="utf-8")
body = body.replace('harness.observation("query_result", role="fetch", state=',
                    'harness.observation("query_result", run_id="run-e2e-1", execution_attempt="initial", role="fetch", state=')
body = body.replace('attempt="reviewer-2", role="fetch",',
                    'attempt="reviewer-2", execution_attempt="initial", role="fetch",')
body = body.replace('expect="dispatch_expert", note="still unknown; cost stays null")',
                    'expect="reconcile_possible_charge", note="still unknown; cost stays null")')
needle = '    assert harness.state_data()["possibly_paid_invocation_refs"][0]["cost_usd"] is None\n'
assert body.count(needle) == 1
body = body.replace(needle, needle + '''    harness.apply(harness.observation("charge_reconciled", call_id="call-e2e-1",
                                      outcome="known", cost_usd=0,
                                      evidence_ref="synthetic/provider-ledger/no-charge"),
                  expect="dispatch_expert", note="only explicit synthetic ledger resolves the unknown")
''')
e2e.write_bytes(body.encode())
print("Applied causal progress, explicit evidence, unknown accounting, kernel mutex and create-only output fixes")
