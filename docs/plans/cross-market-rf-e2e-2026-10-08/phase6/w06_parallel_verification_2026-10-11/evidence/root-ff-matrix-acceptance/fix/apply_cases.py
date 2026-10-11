from pathlib import Path
HERE = Path(__file__).resolve().parent
TOOLS = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root/tools/offline_contract_matrix')
(TOOLS / 'extended_cases.py').write_text((HERE / 'extended_cases_source.py').read_text(encoding='utf-8'), encoding='utf-8')
p = TOOLS / 'matrix_cases.py'
s = p.read_text(encoding='utf-8-sig')
start = s.index('    seeds = [')
end = s.index('    for identity, kind, year', start)
s = s[:start] + '''    seeds = [(US, "annual_report", 2025, "FY", "FY", "apple_2025_annual")]
    for identity in (CN, HK, US):
        for kind, period in (("annual_report", "FY"), ("semi_annual_report", "S1"), ("quarterly_report", "Q1")):
            seeds.append((identity, kind, 2024, period, period, f"{identity.market}_2024_{kind}"))
''' + s[end:]
s = s.replace('    ctx.scan()\n', '''    from dataclasses import replace
    txt_identity = replace(US, provider="fmp", source_url="https://financialmodelingprep.com/stable/earning-call-transcript?symbol=AAPL&year=2024&quarter=2")
    ctx.env.seed_original(txt_identity, document_kind="investor_call_transcript", fiscal_year=2024,
                          fiscal_period="Q2", form_type=None, published_date="2024-07-01",
                          content=b"Synthetic original-language local TXT transcript.\\n", mime_type="text/plain", filename_hint="aapl_local_2024q2")
    ctx.scan()
''')
s = s.replace('case_id: str) -> CaseResult:\n    calls = ctx.env.calls_file(case_id)\n    ctx.write_state(scenario="success", calls_file=calls, provider_scenario="serve",', 'case_id: str, period: str | None = None) -> CaseResult:\n    calls = ctx.env.calls_file(case_id)\n    ctx.write_state(scenario="success", calls_file=calls, provider_scenario="serve",', 1)
s = s.replace('fiscal_period=None, intent="fetch_if_missing")\n    run1 = ctx.run_ff(req, case_id=case_id, run_label="run1")', 'fiscal_period=period, intent="fetch_if_missing")\n    run1 = ctx.run_ff(req, case_id=case_id, run_label="run1")', 1)
# Preserve producer failures/gaps. No expectation changes and no unseeded-kind workaround.
s = s.replace('"run1_kind": f1.get("document_kind"),', '"run1_kind": f1.get("document_kind"),\n                "run1_response": run1["response"], "run2_response": run2["response"],')
p.write_text(s, encoding='utf-8')
p = TOOLS / 'et_transcript_proxy.py'
s = p.read_text(encoding='utf-8')
s = s.replace('symbol = request.get("ticker", "SYN")', 'symbol = "WRONG" if state.get("scenario") == "wrong_symbol" else request.get("ticker", "SYN")')
s = s.replace('from tests.test_retrieval_runtime import fake_spec', 'from tests.test_retrieval_runtime import fake_spec, StallResponse')
s = s.replace('        response = FakeResponse(FMP_URL, payload, status_code=status,\n                                content_type=content_type)\n        spec = fake_spec({FMP_URL: response}, calls_file=calls_file)', '''        if scenario == "wrong_mime":
            content_type = "text/html"
        response = FakeResponse(FMP_URL, payload, status_code=status, content_type=content_type)
        if scenario == "stall":
            response = StallResponse(FMP_URL, payload, content_type=content_type, stall=(0, None), stall_in_get=True)
        elif scenario == "request_failure":
            import requests
            response = requests.RequestException("synthetic-after-GET-failure")
        spec = fake_spec({FMP_URL: response}, calls_file=calls_file)''')
p.write_text(s, encoding='utf-8')
p = TOOLS / 'fixture_provider_adapter.py'
s = p.read_text(encoding='utf-8')
s = s.replace('def _fetch(argv: list[str]) -> dict:', 'def _fetch(argv: list[str], payload: dict) -> dict:')
begin = s.index('    raw = sys.stdin.read()', s.index('def _fetch'))
end = s.index('    market = payload.get', begin)
s = s[:begin] + s[end:]
s = s.replace('    content, mime = _render_original(document_kind, title)', '''    content, mime = _render_original(document_kind, title)
    scenario = _state().get("provider_scenario")
    if scenario == "bad_mime":
        content = make_valid_html(title, "HTML cannot masquerade as PDF original")
    if scenario == "oversize":
        content += b"x" * 2048''')
s = s.replace('"content_sha256": digest,', '"content_sha256": "0" * 64 if scenario == "bad_sha" else digest,')
s = s.replace('        response = _fetch(argv[1:])', '        payload = json.loads(sys.stdin.read())\n        response = _fetch(argv[1:], payload)')
s = s.replace('entry = {"action": action,', 'entry = {"receipt_tag": _state().get("receipt_tag"), "action": action,')
s = s.replace('    except OSError:\n        pass', '    except OSError as exc:\n        raise RuntimeError("fixture invocation evidence could not be written") from exc')
p.write_text(s, encoding='utf-8')
p = TOOLS / 'run.py'
s = p.read_text(encoding='utf-8')
start = s.index('    def fixture_requests')
s = s[:start] + '''    def adapter_records(self) -> list[dict]:
        path = self.scratch / "adapter_invocations.log"
        return [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

''' + s[start:]
p.write_text(s, encoding='utf-8')
