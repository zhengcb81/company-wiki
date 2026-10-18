"""ROOT independent FF received-manifest controls; run only in owned source snapshot.
Only synthetic bytes/temporary roots. No real credentials, originals or services.
"""
import json
from pathlib import Path
import tempfile
import pytest
from test_du11_transcript_reuse_contract import FakeCWP, query_found, reader_entry, build, companion_request, filing, LOCAL_RAW
from transcript_companion import resolve_companion_transcript


def exercise():
    cases={
        "reader_after_asof": {"published":"2027-01-01"},
        "reader_invalid_publication": {"published":"not-a-date"},
        "reader_newly_unknown_publication": {"published":None},
        "reader_us_distinct_zero_prefixed_security": {"security_id":"0MSFT"},
    }
    output={}
    with tempfile.TemporaryDirectory(prefix="ff-reception-controls-") as td:
        for key,delta in cases.items():
            case=Path(td)/key;case.mkdir();tool=case/"tool.py";tool.write_text("# offline synthetic\n",encoding="utf8")
            fake=FakeCWP(queries=[query_found(LOCAL_RAW)],reader=[reader_entry(LOCAL_RAW,**delta)])
            monkeypatch=pytest.MonkeyPatch()
            try:
                transport=build(monkeypatch,fake,tool)
                result=resolve_companion_transcript(request=companion_request(),filing_handle=filing(),transport=transport)
                output[key]={k:result.get(k) for k in ("status","reason","as_of_cutoff_verified","publication_date","provider_calls")}
                output[key]["child_calls"]=fake.kinds()
            finally:
                monkeypatch.undo()
    output["owned_temp_removed"]=not Path(td).exists()
    return output


if __name__=="__main__":
    print(json.dumps(exercise()))
