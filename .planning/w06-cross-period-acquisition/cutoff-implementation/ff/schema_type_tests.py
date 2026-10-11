"""One concrete malformed-JSON-schema counterexample; no product edit."""
from pathlib import Path
ROOT=Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root")
p=ROOT/"tests/test_transcript_launch_contract.py"
data=p.read_bytes()
nl=b"\r\n" if b"\r\n" in data else b"\n"
old='''    ("schema_version", "earnings-transcript-result/3", 0, "provider_result_invalid"),'''
new=old+'''
    ("schema_version", ["earnings-transcript-result/2"], 0, "provider_result_invalid"),'''
assert data.count(old.encode())==1
p.write_bytes(data.replace(old.encode(),new.encode().replace(b"\n",nl)))
print("Added one schema-array production counterexample.")
