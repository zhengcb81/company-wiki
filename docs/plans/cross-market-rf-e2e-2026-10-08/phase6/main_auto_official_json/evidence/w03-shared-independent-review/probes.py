"""Two new W03 boundary combinations; no repeated matrix/public pipeline."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import sys
import tempfile
import time

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))
NETWORK = []
def network_blocked(*args, **kwargs):
    NETWORK.append("network")
    raise RuntimeError("offline boundary probe attempted network")
socket.socket.connect = network_blocked
socket.create_connection = network_blocked

from company_wiki.automation.narrative_selector_binding import BoundNarrativeSelector, bind_narrative_selector
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_official_json import open_verified_projection, select_verified_projection
from company_wiki.automation.models import HandlerOutcome
from company_wiki.source_catalog import narrative_evidence as policy
from integration import test_official_json_verify_handler as official
from unit import test_narrative_select_handler as raw_fixture

EVIDENCE = OUT.parent
SHARED = (
    "src/company_wiki/automation/narrative_runtime.py",
    "src/company_wiki/automation/narrative_worker_factory.py",
    "src/company_wiki/automation/narrative_select.py",
    "src/company_wiki/automation/narrative_official_json.py",
    "src/company_wiki/automation/narrative_verify.py",
    "src/company_wiki/source_catalog/narrative_retrieval.py",
    "src/company_wiki/automation/narrative_selector_binding.py",
    "src/company_wiki/source_catalog/narrative_evidence.py",
)
INDUSTRY = "Recent export licensing restrictions have tightened across the semiconductor industry."
RAW = ("Full Conference Call Transcript\n"
       "CEO: We launched a new product and expanded overseas capacity.\n"
       "CEO: " + INDUSTRY + "\n").encode()


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def all_source():
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT / "src").rglob("*.py")}


def main():
    source_before = all_source()
    shared_before = {p: source_before[p] for p in SHARED}
    public_receipt = next((EVIDENCE / "w03-public-main-reception").glob("green-public3-*.json"))
    public = json.loads(public_receipt.read_text(encoding="utf-8"))
    assert public["returncode"] == 0
    assert {p: public["after_sha"][p] for p in SHARED} == shared_before
    assert policy.NARRATIVE_SELECTOR_VERSION == "0.7.0"
    w04 = json.loads((EVIDENCE / "w04-main-reception/FINAL_SHA_RECEIPT.json").read_text(encoding="utf-8"))
    w04_source = {p: value for p, value in w04["owned_changed_sha256"].items() if p.startswith("src/")}
    assert {p: source_before[p] for p in w04_source} == w04_source
    protect = [ROOT / "tests/integration/test_w03_selector_public_node.py",
               ROOT / "tests/fixtures/narrative_real_transcript/MSFT_Q4_2026_earnings_call.txt",
               EVIDENCE / "w03-public-node-design.md", EVIDENCE / "w03-shared-main-reception/HANDOFF.md",
               EVIDENCE / "w03-shared-main-reception/source-after.json", public_receipt]
    protect += [p for p in (ROOT / "config/source_catalog.yaml", ROOT / "config.yaml") if p.exists()]
    protected_before = {str(p):sha(p) for p in protect}
    env_before = dict(os.environ)
    owned = Path(tempfile.mkdtemp(prefix="w03-independent-"))
    (owned / "keep.txt").write_bytes(b"preexisting own fixture sentinel")
    baseline = {p.relative_to(owned).as_posix():p.read_bytes() for p in owned.rglob("*") if p.is_file()}
    receipt = {"schema_version":"w03-shared-independent-review/1", "probes":[],
               "shared_before_sha256":shared_before,"w04_expected_sha256":w04_source,
               "provider_calls":0,"external_model_calls":0,"new_cost_usd":0,
               "owned_temp":str(owned),"public_receipt_path":str(public_receipt)}
    start = time.monotonic()
    def probe(name, function):
        try:
            details = function()
            value = {"name":name,"status":"pass","details":details}
        except BaseException as error:
            value = {"name":name,"status":"fail","error":repr(error)}
        receipt["probes"].append(value)
        print(json.dumps(value,ensure_ascii=False),flush=True)
    try:
        def falsey_custom():
            calls = []
            bool_calls = []
            class FalseySelector:
                def __bool__(self):
                    bool_calls.append(1)
                    return False
                def __call__(self, parsed, *, title, existing_kind="unknown"):
                    calls.append(title)
                    return policy.select_narrative_evidence(parsed,title=title,
                        existing_kind=existing_kind,selector_version="0.6.0")
            custom = FalseySelector()
            payload = raw_fixture._payload(RAW,title="Independent policy contrast",
                document_kind="earnings_call_transcript",language="en",mime_type="text/plain")
            bound = bind_narrative_selector(custom,selector_version="0.6.0")
            assert bind_narrative_selector(bound) is bound
            result = NarrativeSelectHandler(reader=raw_fixture.FakeReader(payload,RAW),
                selector=bound,selector_version="0.6.0")(raw_fixture._context(payload,lambda:None))
            assert result.outcome is HandlerOutcome.SUCCEEDED
            selected = NarrativeSelectResult.from_dict(result.result)
            assert selected.selector.version == "0.6.0"
            assert selected.evidence_spans and not any(INDUSTRY in s.raw_text for s in selected.evidence_spans)
            parsed = policy.parse_transcript_text(RAW.decode(),source_id=selected.source_ref.source_id,
                source_sha256=selected.source_ref.content_sha256,language="en",parser_version=selected.parser.version)
            new = bind_narrative_selector()(parsed,title="Independent policy contrast",existing_kind="earnings_call_transcript")
            assert any(INDUSTRY in s.raw_text for s in new.evidence_spans)
            assert calls == ["Independent policy contrast"] and bool_calls == []
            broken_calls = []
            class FalseyBroken(FalseySelector):
                def __call__(self, *args, **kwargs):
                    broken_calls.append(1)
                    raise TypeError("independent internal typeerror")
            broken = FalseyBroken()
            try:
                NarrativeSelectHandler(reader=raw_fixture.FakeReader(payload,RAW),
                    selector=broken,selector_version="0.6.0")(raw_fixture._context(payload,lambda:None))
            except TypeError as error:
                assert str(error) == "independent internal typeerror"
            else:
                raise AssertionError("internal TypeError was hidden")
            assert len(broken_calls) == 1 and bool_calls == []
            return {"actual_default":"0.7.0","actual_custom_pin":"0.6.0",
                "custom_calls":len(calls),"truthiness_calls":len(bool_calls),
                "new_industry_absent_old_present_default":True,
                "internal_typeerror_calls":len(broken_calls),"rebound_old_pin_unchanged":True}
        probe("falsey-custom-actual-legacy-policy-and-no-typeerror-retry",falsey_custom)

        def forged_bound_empty():
            calls = []
            def never_called(*args, **kwargs):
                calls.append(1)
                raise AssertionError("empty native subject invoked custom selector")
            with official.owned_catalog(owned) as (catalog,_root):
                page = official.flat_page(1)
                page["result"].update(item_total=1,page_count=1)
                page["result"]["items"][0].update(a="",q="")
                ref, original = official.import_page(catalog,page)
                projection = official.persist(catalog,[ref])
                view = open_verified_projection(catalog,projection_id=projection.projection_id,
                    expected_projection_sha256=projection.projection_sha256)
                assert view.coverage_complete and view.language is None
                forged = BoundNarrativeSelector(never_called,"unknown-policy")
                try:
                    select_verified_projection(view,title="empty real subject",selector=forged)
                except policy.NarrativeSelectorVersionError:
                    pass
                else:
                    raise AssertionError("forged unknown bound bypassed complete-empty version binding")
                valid = BoundNarrativeSelector(never_called,"0.6.0")
                selected = select_verified_projection(view,title="empty real subject",selector=valid)
                assert selected.status == "skipped_no_narrative" and selected.coverage_complete
                assert selected.evidence_spans == () and calls == []
                handler = NarrativeSelectHandler(reader=official.NoRawReader(),projection_catalog=catalog,
                    selector=valid,selector_version="0.6.0")
                result = handler(official.make_context(projection,language="unknown"))
                assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
                assert result.result["selector"]["version"] == "0.6.0"
                assert result.result["source_metadata"]["language"] == "unknown"
                assert result.result["selection"]["status"] == "skipped_no_narrative"
                assert official.SourceVersionReader(catalog).open_version(ref).data == original
                assert calls == []
            assert {p.relative_to(owned).as_posix():p.read_bytes() for p in owned.rglob("*") if p.is_file()} == baseline
            return {"coverage_complete":True,"native_language":None,"forged_unknown_bound_rejected":True,
                "actual_supported_old_handler_pin":"0.6.0","metadata_language":"unknown",
                "status":"skipped_no_narrative","custom_invocations":0,
                "owned_catalog_restored":True,"original_bytes_unchanged":True}
        probe("forged-bound-unknown-cannot-bypass-real-complete-empty-projection",forged_bound_empty)
        receipt["status"] = "pass" if all(p["status"]=="pass" for p in receipt["probes"]) else "specific_blocker"
    finally:
        source_after = all_source()
        receipt["shared_after_sha256"] = {p: source_after[p] for p in SHARED}
        receipt["all_source_unchanged"] = source_before == source_after
        receipt["all_source_count"] = len(source_before)
        receipt["w04_source_unchanged"] = {p:source_after[p] for p in w04_source} == w04_source
        receipt["protected_sha256"] = protected_before
        receipt["protected_unchanged"] = protected_before == {str(p):sha(p) for p in protect}
        receipt["environment_unchanged"] = env_before == dict(os.environ)
        receipt["network_attempts"] = len(NETWORK)
        receipt["seconds"] = time.monotonic()-start
        assert owned.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
        def retry(function,path,error):
            assert Path(path).resolve().is_relative_to(owned.resolve())
            os.chmod(path,stat.S_IWRITE|stat.S_IREAD)
            function(path)
        shutil.rmtree(owned,onexc=retry)
        receipt["owned_temp_removed"] = not owned.exists()
        (OUT/"receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        assert receipt["all_source_unchanged"] and receipt["w04_source_unchanged"] and receipt["protected_unchanged"]
        assert receipt["environment_unchanged"] and receipt["owned_temp_removed"] and not NETWORK
        print(json.dumps({"status":receipt.get("status"),"probes":len(receipt["probes"]),
            "seconds":receipt["seconds"],"source_unchanged":True,"owned_temp_removed":True,
            "external_calls":0}),flush=True)
    return 0 if receipt["status"]=="pass" else 1

if __name__ == "__main__":
    raise SystemExit(main())
