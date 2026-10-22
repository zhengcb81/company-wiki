from pathlib import Path
import subprocess
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
p = ROOT / "src/company_wiki/automation/narrative_run_store.py"
old = subprocess.run(["git", "show", "2f632193:" + p.relative_to(ROOT).as_posix()],
                     cwd=ROOT, check=True, stdout=subprocess.PIPE).stdout
new = p.read_bytes().replace(b"\r\n", b"\n")
a = b'''                if len(charged) != 1:
                    raise FinalOutputOwnerUnresolved("successful summary has no provable paid output owner")
                owner = charged[0]
                paid_response_json = owner.paid_response_json
                if paid_response_json is None:
                    raise FinalOutputOwnerUnresolved("successful summary has no provable paid output owner")
                try:
                    paid_pin = PaidResponsePin.from_json(paid_response_json)'''
b = b'''                if len(charged) != 1 or charged[0].paid_response_json is None:
                    raise FinalOutputOwnerUnresolved("successful summary has no provable paid output owner")
                owner = charged[0]
                try:
                    paid_pin = PaidResponsePin.from_json(owner.paid_response_json)'''
assert new.count(a) == 1
v = {"old_git_lf_sha256": hashlib.sha256(old).hexdigest(),
     "new_working_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
     "new_normalized_lf_sha256": hashlib.sha256(new).hexdigest(),
     "reverse_guard_text_equals_old_normalized_source": new.replace(a, b) == old.replace(b"\r\n", b"\n")}
assert v["reverse_guard_text_equals_old_normalized_source"]
(Path(__file__).resolve().parent / "code-equivalence.json").write_text(json.dumps(v, indent=2), encoding="utf-8")
print(json.dumps(v))
