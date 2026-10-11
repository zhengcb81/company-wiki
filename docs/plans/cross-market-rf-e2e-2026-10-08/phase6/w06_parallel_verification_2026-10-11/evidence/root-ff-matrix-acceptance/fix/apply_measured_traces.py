from pathlib import Path
p = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root/tools/offline_contract_matrix/run.py')
s = p.read_text(encoding='utf-8')
s = s.replace('        req_path = self.artifacts', '''        state_path = self.env.proxy_state / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
        calls = Path(state["calls_file"]) if state.get("calls_file") else None
        et_before = self.fixture_requests(calls) if calls else 0
        adapters_before = len(self.adapter_records())
        req_path = self.artifacts''', 1)
s = s.replace('            "stderr_ref": stderr_path.name,', '''            "stderr_ref": stderr_path.name,
            "et_fixture_requests": (self.fixture_requests(calls) if calls else 0) - et_before,
            "adapter_fixture_requests": len(self.adapter_records()) - adapters_before,
            "fixture_requests": (self.fixture_requests(calls) if calls else 0) - et_before + len(self.adapter_records()) - adapters_before,
            "receipt_tag": state.get("receipt_tag"),
            "fixture_scenario": state.get("scenario"),
            "expected_original_content_sha256": __import__("hashlib").sha256(state.get("content_utf8", "").encode("utf-8")).hexdigest() if state.get("content_utf8") else None,''')
p.write_text(s, encoding='utf-8')
p = p.with_name('cli_main.py')
s = p.read_text(encoding='utf-8')
s = s.replace('            result.actual["runs"] = ctx.traces.get(cid, [])', '''            result.actual["runs"] = ctx.traces.get(cid, [])
            traces = result.actual["runs"]
            result.provider_counters["fixture_requests"] = sum(t["fixture_requests"] for t in traces)
            if result.expected.get("run_twice"):
                result.provider_counters["run2_fixture_requests"] = traces[1]["fixture_requests"] if len(traces) >= 2 else None''')
p.write_text(s, encoding='utf-8')
p = p.with_name('oracle.py')
s = p.read_text(encoding='utf-8')
s = s.replace('                period = request if kind', '''                if kind == "transcript" and run.get("expected_original_content_sha256") and row.get("status") == "downloaded" and proof.get("original_language_content_sha256") != run["expected_original_content_sha256"]:
                    findings.append(Finding("translated_or_changed_text", cid, "stored original language content differs from supplied fixture text"))
                period = request if kind''')
p.write_text(s, encoding='utf-8')
