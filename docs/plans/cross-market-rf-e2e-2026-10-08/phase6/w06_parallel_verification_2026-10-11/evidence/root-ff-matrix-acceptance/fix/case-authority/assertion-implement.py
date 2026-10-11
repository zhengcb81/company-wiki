from pathlib import Path
import ast
import pprint
FF=Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
p=FF/'tools/offline_contract_matrix/case_specs.py';text=p.read_text(encoding='utf-8')
text=text.replace('from fixture_builder import CN, HK, US','from fixture_builder import CN, HK, US\nfrom matrix_outcome import Outcome, count, filing_reused, source_ref')
method=r'''    def assertion_errors(self, case):
        """Re-evaluate fixed business meaning from bound producer responses.

        A PASS label or summary boolean cannot substitute for required outcomes.
        The oracle separately verifies these response bytes against their files.
        """
        runs=(case.get("actual") or {}).get("runs") or []
        if len(runs)!=len(self.runs):
            return ["required attempt count is not observed"]
        responses=[r.get("response") or {} for r in runs]
        first=responses[0];filing=first.get("filing") or {};transcript=first.get("transcript") or {}
        expected=self.expected();handler=self.handler.split(":")[1]
        checks=[]
        def require(ok, detail):checks.append((bool(ok),detail))
        if handler=="case_fin_local_hit":
            require(first.get("status")==expected["status"] and filing.get("resolution_outcome")=="reused_existing" and count(filing.get("download_events"))==expected["download_events"] and source_ref(filing.get("source_ref")),"local filing is not an exact zero-download source reuse")
            require(count(runs[0].get("fixture_requests"))==0,"local filing invoked fixture acquisition")
        elif handler=="case_fin_fetch":
            require(first.get("status")=="source_candidate" and filing_reused(filing,responses[1].get("filing") or {},self.runs[0].request()["document_kind"]),"new filing acquisition followed by exact source reuse is unproved")
        elif handler=="case_nonperiod":
            require(first.get("status")=="source_candidate" and filing.get("document_kind")==expected["stored_kind"] and source_ref(filing.get("source_ref")),"nonperiodic document not registered under its required kind")
        elif handler=="case_chain_a":
            second=responses[1].get("transcript") or {}
            require(transcript.get("status")=="downloaded" and source_ref(transcript.get("source_ref")) and second.get("status") in {"reused","unknown_publication"} and source_ref(second.get("source_ref"))==source_ref(transcript.get("source_ref")),"transcript download then stable source reuse is unproved")
            require(count(runs[0].get("et_fixture_requests"))==1 and count(runs[1].get("et_fixture_requests"))==0,"transcript expected 1 then 0 GETs")
        elif handler=="case_call_fy_only":
            require(transcript.get("status")==expected["status"] and transcript.get("reason")==expected["reason"],"FY-only unresolved-period diagnostic missing")
        elif handler=="case_call_past_cutoff":
            require(Outcome.observe(transcript).rejected_cutoff(),"named cutoff rejection missing")
        elif handler=="case_call_wrong_quarter":
            require(Outcome.observe(transcript).rejected_quarter() or (transcript.get("status") in {"upstream_error","provider_unavailable"} and transcript.get("reason")=="provider_identity_or_host" and count(runs[0].get("et_fixture_requests"))==1),"named quarter/provenance rejection missing")
        elif handler=="case_err_request":
            require(first.get("status")==expected["status"] and runs[0].get("exit_code")==2,"request validation failure missing")
        elif handler=="case_err_402":
            require(transcript.get("status")==expected["status"] and expected["reason_contains"] in str(transcript.get("reason")),"402 entitlement diagnostic missing")
        elif handler=="case_err_missing_creds":
            require(expected["reason_contains"] in str(transcript.get("reason")) and count(runs[0].get("fixture_requests"))==0,"credential preflight not preserved as zero-request diagnostic")
        elif handler=="case_err_unknown_usage":
            require(Outcome.observe(transcript).preserves_unknown_usage(),"unknown usage not preserved as a named null failure")
        elif handler=="case_local_txt":
            ref=source_ref(transcript.get("source_ref"))
            require(transcript.get("status") in {"reused","unknown_publication"} and ref and ref["mime_type"]=="text/plain" and count(runs[0].get("fixture_requests"))==0,"exact local TXT source reuse unproved")
        elif handler=="case_reuse_only_gap":
            require(first.get("status")!="source_candidate" and source_ref(filing.get("source_ref")) is None and count(runs[0].get("fixture_requests"))==0,"reuse-only gap acquired or accepted a source")
        elif handler in {"_negative_transcript","case_failure_then_retry"}:
            require(transcript.get("status") not in {None,"downloaded","reused","unknown_publication","not_requested"} and transcript.get("reason") in expected["reasons"] and source_ref(transcript.get("source_ref")) is None and count(runs[0].get("et_fixture_requests"))==1,"required attempted ET rejection is unproved")
            require((case.get("actual") or {}).get("worker_cleanup") is True,"owned ET worker artifacts not cleaned")
            if handler=="case_failure_then_retry":
                second=responses[1].get("transcript") or {}
                require(second.get("status")=="downloaded" and source_ref(second.get("source_ref")) and count(runs[1].get("et_fixture_requests"))==1,"successful retry after named failure unproved")
        elif handler=="filing_negative":
            code=(filing.get("upstream_cause") or {}).get("code")
            require(first.get("status")!="source_candidate" and source_ref(filing.get("source_ref")) is None and count(runs[0].get("adapter_fixture_requests")) is not None and runs[0]["adapter_fixture_requests"]>=2 and code in {"acquisition_validation_failed","acquisition_budget_exceeded"},"attempted invalid staged-original validation unproved")
        elif handler=="case_unverified_sidecar":
            require(first.get("status")!="source_candidate" and (filing.get("upstream_cause") or {}).get("code")=="local_metadata_gap","incomplete metadata diagnostic missing")
        else:
            return ["case handler has no fixed business assertions"]
        return [detail for ok,detail in checks if not ok]

'''
text=text.replace('    def execute(self,ctx):',method+'    def execute(self,ctx):')
start=text.index('_METADATA=');end=text.index('\n_SPECS=',start)
metadata=ast.literal_eval(text[start+len('_METADATA='):end]);text=text[:start]+'_METADATA='+pprint.pformat(metadata,width=105,sort_dicts=False)+text[end:]
p.write_text(text,encoding='utf-8')
p=FF/'tools/offline_contract_matrix/oracle.py';text=p.read_text(encoding='utf-8')
text=text.replace('''    if case.get("result") != "PASS":
        findings.append(Finding("case_not_passed", case_id, f"actual result {case.get('result')} cannot certify required case"))''','''    if case.get("result") != "PASS":
        findings.append(Finding("case_not_passed", case_id, f"actual result {case.get('result')} cannot certify required case"))
    else:
        for detail in spec.assertion_errors(case):
            findings.append(Finding("case_assertion_failed", case_id, detail))''')
text=text.replace('if index < len(spec.runs) and spec.runs[index].fixture() is not None:', 'if index < len(spec.runs) and (spec.runs[index].fixture() is not None or not spec.runs[index].with_fmp_key):')
p.write_text(text,encoding='utf-8')
print('Fixed assertions verify observed response meaning, not PASS labels')
