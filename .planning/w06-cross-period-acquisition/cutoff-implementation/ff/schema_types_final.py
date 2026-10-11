"""Two malformed JSON schema types share one final boundary repair."""
from pathlib import Path
import json
import sys
ROOT=Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root")
OUT=Path(__file__).resolve().parent
mode=sys.argv[1]
assert mode in {"tests","implement"}
if mode=="tests":
    p=ROOT/"tests/test_transcript_launch_contract.py"
    data=p.read_bytes()
    nl=b"\r\n" if b"\r\n" in data else b"\n"
    old='''    ("schema_version", ["earnings-transcript-result/2"], 0, "provider_result_invalid"),'''
    new=old+'''
    ("schema_version", {"version": "earnings-transcript-result/2"}, 0, "provider_result_invalid"),'''
    assert data.count(old.encode())==1
    p.write_bytes(data.replace(old.encode(),new.encode().replace(b"\n",nl)))
else:
    assert json.loads((OUT/"schema-types-red.json").read_text(encoding="utf-8"))["exit_code"]==1
    p=ROOT/"scripts/transcript_tool_transport.py"
    data=p.read_bytes()
    nl=b"\r\n" if b"\r\n" in data else b"\n"
    old='''                result.get("schema_version") not in {
                    "earnings-transcript-result/1", "earnings-transcript-result/2",
                }'''
    new='''                result.get("schema_version") not in (
                    "earnings-transcript-result/1", "earnings-transcript-result/2",
                )'''
    oldb=old.encode().replace(b"\n",nl)
    assert data.count(oldb)==1
    p.write_bytes(data.replace(oldb,new.encode().replace(b"\n",nl)))
print("Final schema type mode complete: "+mode)
