from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
TOOLS = ROOT / 'tools/offline_contract_matrix'
p = TOOLS / 'oracle.py'
s = p.read_text(encoding='utf-8-sig')
s = s.replace('from matrix_outcome import count', 'from pathlib import Path\nimport hashlib\nimport json\nfrom matrix_outcome import count, source_ref')
s = s.replace('    return findings\n', '''    if report.get("runner"):
        findings.extend(_bound_evidence(report))
    return findings
''')
s += '''
def _bound_evidence(report: dict) -> list[Finding]:
    findings = []
    scope = report.get("scope") or {}
    if (count(scope.get("network_guard_boots")) or 0) == 0 or scope.get("network_attempts_denied") != 0 or scope.get("translation_attempts") != 0:
        findings.append(Finding("unmeasured_isolation", None, "startup network/translation instrumentation missing or an attempt occurred"))
    root_value = report.get("evidence_root")
    root = Path(root_value).resolve() if root_value else None
    proofs = (report.get("source_proofs") or {}).get("proofs") or {}
    for case in report.get("cases", []):
        cid = case.get("id")
        if (case.get("actual") or {}).get("elapsed_seconds", float("inf")) > 30 and case.get("result") == "PASS":
            findings.append(Finding("case_deadline_exceeded", cid, "late case cannot PASS"))
        runs = (case.get("actual") or {}).get("runs") or []
        if case.get("result") != "PASS":
            continue
        if not runs or root is None:
            findings.append(Finding("missing_bound_evidence", cid, "PASS lacks actual request/response files"))
            continue
        for run in runs:
            request, response = {}, {}
            try:
                for kind in ("request", "response"):
                    path = (root / run[kind + "_ref"]).resolve()
                    if not path.is_relative_to(root):
                        raise ValueError("receipt path escapes attempt")
                    raw = path.read_bytes()
                    if hashlib.sha256(raw).hexdigest() != run[kind + "_sha256"]:
                        raise ValueError("receipt bytes changed")
                    payload = json.loads(raw)
                    if kind == "request":
                        request = payload
                    else:
                        response = payload
                if response != run["response"]:
                    raise ValueError("response self-claim differs from bound bytes")
            except Exception as exc:
                findings.append(Finding("invalid_bound_evidence", cid, f"{type(exc).__name__}: {exc}"))
                continue
            for kind in ("filing", "transcript"):
                row = response.get(kind) or {}
                ref = source_ref(row.get("source_ref"))
                accepted = row.get("status") in {"downloaded", "reused", "unknown_publication", "source_candidate"}
                if accepted and ref is None:
                    findings.append(Finding("missing_source_ref", cid, f"{kind} accepted without complete SourceRef"))
                if ref is None:
                    continue
                proof = proofs.get(ref["document_id"]) or {}
                expected_kind = request.get("document_kind") if kind == "filing" else "investor_call_transcript"
                if (proof.get("verified") is not True or proof.get("reference") != ref or
                    proof.get("content_sha256") != ref["content_sha256"] or proof.get("byte_size") != ref["byte_size"] or
                    proof.get("source_versions") != 1 or proof.get("original_locations") != 1 or proof.get("document_kind") != expected_kind):
                    findings.append(Finding("source_bytes_not_verified", cid, f"fresh reader/source version/original count mismatch for {kind}"))
                period = request if kind == "filing" else request.get("companion_transcript", {})
                if row.get("fiscal_year") != period.get("fiscal_year"):
                    findings.append(Finding("wrong_period", cid, f"{kind} fiscal year differs from request"))
                if kind == "filing" and period.get("fiscal_period") is not None and row.get("fiscal_period") != period.get("fiscal_period"):
                    findings.append(Finding("wrong_period", cid, "filing fiscal period differs from request"))
                if kind == "transcript" and row.get("fiscal_quarter") != period.get("fiscal_quarter"):
                    findings.append(Finding("wrong_period", cid, "transcript quarter differs from request"))
        if (case.get("expected") or {}).get("run_twice") and len(runs) >= 2:
            first, second = runs[0]["response"], runs[1]["response"]
            for kind in ("filing", "transcript"):
                ref1, ref2 = source_ref((first.get(kind) or {}).get("source_ref")), source_ref((second.get(kind) or {}).get("source_ref"))
                if ref1 and ref1 != ref2:
                    findings.append(Finding("reuse_identity_changed", cid, f"{kind} second run changed source version"))
    return findings
'''
p.write_text(s, encoding='utf-8')
p = ROOT / 'tests/test_w06_matrix_runtime.py'
s = p.read_text(encoding='utf-8') + '''

def test_absolute_case_budget_is_shared_not_reset():
    import runtime
    with patch.object(runtime.time, "monotonic", side_effect=[0, 1, 1, 2, 2, 30.1]):
        batch = runtime.Deadline(30)
        first = batch.case(30)
        second = first.case(30)
        assert second.end == 30
        import pytest
        with pytest.raises(runtime.DeadlineExceeded):
            second.remaining()

def test_expired_deadline_prevents_launch(tmp_path):
    import runtime
    import pytest
    with patch.object(runtime.subprocess, "Popen") as launch:
        with pytest.raises(runtime.DeadlineExceeded):
            runtime.run_process([sys.executable], env={}, cwd=tmp_path, deadline=runtime.Deadline(end=-1))
        launch.assert_not_called()

def test_startup_denies_network_before_import_and_records_translation(tmp_path):
    import runtime
    env = runtime.synthetic_env(tmp_path, tmp_path / "cwp", tmp_path / "et")
    fake_module = tmp_path / "translator.py"
    fake_module.write_text("class TranslatorFactory:\\n    @staticmethod\\n    def create(*args): return 'unprotected'\\n", encoding="utf-8")
    script = "import socket, translator;\\ntry: socket.create_connection(('example.invalid', 443))\\nexcept RuntimeError: pass\\ntry: translator.TranslatorFactory.create({})\\nexcept RuntimeError: pass"
    proc = runtime.run_process([sys.executable, "-B", "-c", script], env=env, cwd=tmp_path, deadline=runtime.Deadline(5))
    assert proc.returncode == 0, proc.stderr
    ops = [e["op"] for e in runtime.guard_events(tmp_path)]
    assert ops == ["guard_boot", "network_denied", "translation_attempt"]

def test_hard_deadline_reaps_child_without_long_wait(tmp_path):
    import runtime
    import pytest
    import time
    env = runtime.synthetic_env(tmp_path, tmp_path / "cwp", tmp_path / "et")
    start = time.monotonic()
    with pytest.raises(runtime.DeadlineExceeded):
        runtime.run_process([sys.executable, "-B", "-c", "import threading; threading.Event().wait()"], env=env, cwd=tmp_path, deadline=runtime.Deadline(0.2))
    assert time.monotonic() - start < 5

def test_bound_evidence_rejects_bool_only_fake_pass():
    import oracle
    report = {"schema_version":"ff-et-cwp-offline-matrix/1", "runner":{"version":"test"},
              "required_cases":["fake"], "cases":[{"id":"fake", "result":"PASS", "actual":{"elapsed_seconds":1, "real_layer_evidence":{"ff_public_cli":True}}}],
              "code_binding":{"verified":True}, "restore":{"restored":True},
              "scope":{"batch_elapsed_seconds":1, "network_guard_boots":1, "network_attempts_denied":0, "translation_attempts":0}}
    assert "missing_bound_evidence" in {f.vector for f in oracle.audit(report)}
'''
p.write_text(s, encoding='utf-8')
