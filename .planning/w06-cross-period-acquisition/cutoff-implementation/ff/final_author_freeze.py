"""Freeze final unchanged FF products and ROOT concentration receipt; no test runs."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root")
OUT=Path(__file__).resolve().parent
baseline=json.loads((OUT/"baseline.json").read_text(encoding="utf-8"))
owned=[x["path"] for x in baseline["owned"]]
env={k:os.environ[k] for k in ("SYSTEMROOT","WINDIR","PATH","TEMP","TMP") if k in os.environ}
env.update(PYTHONUTF8="1",PYTHONDONTWRITEBYTECODE="1")
def record(rel):
    p=ROOT/rel
    data=p.read_bytes()
    return {"path":rel,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}
changed=[x["path"] for x in baseline["protected"] if record(x["path"])!=x]
assert not changed
tool_path=ROOT/"docs/handoffs/w06-ff-matrix/case-authority/manifest.json"
tool_manifest=json.loads(tool_path.read_text(encoding="utf-8"))
tool_changed=[x["path"] for x in tool_manifest["files"] if record(x["path"])!=x]
assert len(tool_manifest["files"])==205 and not tool_changed
green=json.loads((OUT/"final-focused-green.json").read_text(encoding="utf-8"))
assert green["exit_code"]==0 and green["scratch_restored"]
assert all(record(x["path"])["sha256"]==x["sha256"] for x in green["files"])
assert not list(OUT.glob("s-*"))
tests_prefix=[{"path":x["path"],"original_prefix_preserved":
    hashlib.sha256((ROOT/x["path"]).read_bytes()[:x["bytes"]]).hexdigest()==x["sha256"]}
    for x in baseline["owned"][2:]]
assert all(x["original_prefix_preserved"] for x in tests_prefix)

checks={}
for label,args in [("lint-final",[sys.executable,"-B","-m","ruff","check","--no-cache",*owned]),
                   ("diff-check-final",["git","diff","--check"]),
                   ("status-final",["git","status","--short"]),
                   ("diff-stat-final",["git","diff","--stat"])]:
    r=subprocess.run(args,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    (OUT/(label+".log")).write_bytes(r.stdout)
    checks[label]={"command":args,"exit_code":r.returncode,"sha256":hashlib.sha256(r.stdout).hexdigest()}
    assert r.returncode==0,(label,r.stdout.decode(errors="replace"))
head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,env=env).decode().strip()
assert head==baseline["base"]
final_files=[record(x) for x in owned]
suite=ET.parse(OUT/"concentrated-final2.xml")
cases=suite.findall(".//testcase")
skips=[{"classname":x.get("classname"),"name":x.get("name"),"reason":x.find("skipped").get("message")}
       for x in cases if x.find("skipped") is not None]
assert len(skips)==4 and len(cases)==138
assert not suite.findall(".//failure") and not suite.findall(".//error")
root_receipt=json.loads((OUT/"concentrated-final2.json").read_text(encoding="utf-8"))
assert root_receipt["exit_code"]==0 and root_receipt["scratch_restored_absent"]
(OUT/"tracked-product-final.patch").write_bytes(subprocess.check_output(["git","diff","--",*owned],cwd=ROOT,env=env))
freeze={"schema_version":"ff-cutoff-author-freeze/2","state":"AUTHOR_FROZEN_PENDING_ROOT_REAL41",
        "head_before":baseline["base"],"head_after":head,"files":final_files,
        "protected_count":354,"protected_changed":changed,"tool_freeze_count":205,"tool_changed":tool_changed,
        "tool_manifest_sha256":hashlib.sha256(tool_path.read_bytes()).hexdigest(),
        "original_tests":tests_prefix,"final_green_test_sha_unchanged":True,
        "checks":checks,"scratch_restored":True,"real_key_reads":0,"real_provider_calls":0,"llm_calls":0,
        "root_concentrated":{"passed":134,"skipped":4,"pytest_seconds":1.90,"receipt":str(OUT/"concentrated-final2.json"),"skips":skips},
        "supersedes_author_freeze_sha256":"0574664a9634d6ea11a9fa93949c8ea8469a60d013671e97c2015e8e093fa03c"}
(OUT/"product-freeze-final.json").write_text(json.dumps(freeze,ensure_ascii=False,indent=2),encoding="utf-8")
freeze_sha=hashlib.sha256((OUT/"product-freeze-final.json").read_bytes()).hexdigest()
skip_text="\n".join(f"- `{x['name']}`: {x['reason']}" for x in skips)
report={"schema_version":"ff-cutoff-author-report/2","verdict":"AUTHOR_COMPLETE_PENDING_ROOT_REAL41",
    "worktree":str(ROOT),"head_before":baseline["base"],"head_after":head,"files":final_files,
    "product_freeze_final_sha256":freeze_sha,"evidence_directory":str(OUT),
    "business_red":{"failed":23,"passed":8,"pytest_seconds":1.09},
    "binding_red":{"failed":8,"pytest_seconds":1.03},
    "schema_types_red":{"failed":2,"passed":1,"pytest_seconds":0.95},
    "final_author_focused":{"passed":41,"deselected":77,"pytest_seconds":0.55},
    "root_concentrated":freeze["root_concentrated"],"protected_count":354,"protected_changed":[],
    "tool_freeze_count":205,"tool_changed":[],"scratch_restored":True,"real_key_reads":0,"real_provider_calls":0,"llm_calls":0,
    "still_required":["ROOT unchanged original41 real offline matrix","ROOT publication"],
    "historical_receipts_retained":["product-freeze.json","business-red","focused-green","binding-red","binding-green",
                                   "schema-type-red","schema-types-red","concentrated","concentrated-final"],
    "notes":["One existing process receipt boundary; no second production identity/raw validator.",
             "SKIP is not PASS; ROOT real matrix owns actual three-layer integration.",
             "No tools/oracle/golden/config/ET/CWP product/Git changes."]}
(OUT/"report-final.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
md=f'''# W06 cutoff result — final FF author handoff

**AUTHOR_COMPLETE_PENDING_ROOT_REAL41. Product/tests FROZEN STOP.**

Worktree: `{ROOT}`. HEAD before and after: `{head}`. No commit/merge/push/install.

## Scope and repair
Exactly two product files and three existing responsibility tests (all paths in product-freeze-final.json). ET parent delivers actual cutoff diagnostics. FF retains not_found separately from provider failure, maps only call_after_as_of / publication_after_as_of, and maps ordinary/legacy/unknown code to exact_transcript_missing. Zero candidates never implies cutoff. Actual usage/unknown counters are preserved; no retry/import on not_found.

The only production binding is at its existing child-process receipt boundary: supported /1 or /2 schema, current request ID/provider/period, strict integer zero candidate count and successful child exit. Invalid envelope yields provider_result_invalid; nonzero exit yields provider_tool_failed; real usage is retained. Nonhashable JSON schema array/object is safely rejected using constant tuple comparison. This is no extra company identity store, source read or success validator. Transport imports only shared finite vocabulary, never normalize_et_v2_result.

## TDD and final responsibility evidence
- Original behavior RED23 FAIL /8 PASS /1.09s; legitimate not_found was flattened or rejected.
- ROOT finding RED8 FAIL /1.03s: production wrong envelope/nonzero exit incorrectly claimed cutoff.
- Schema array/object RED2 FAIL /1 PASS /0.95s: actual TypeError, not import/setup error.
- Final author affected tests41 PASS /77 deselected /0.55s; test SHA matches final RED inputs. This number is unit/contract vectors, not the original41 real matrix.
- ROOT final concentrated B:134 PASS /4 SKIP /1.90s. Historical124/4 and132/4 receipts and every RED are retained.
- Final Ruff and git diff --check passed; protected354 and case-authority tool205 files byte-identical. Original contents of all three tests are preserved as exact prefix. All owned scratch restored; real key/network/provider/LLM requests0.
- Final author freeze SHA: `{freeze_sha}`. Earlier0574664 freeze remains an intermediate historical artifact.

## Four explicit SKIPs (not PASS)
{skip_text}

## ROOT next step
Run the unchanged original41 offline matrix with actual FF→ET→CWP paths. These four optional cross-project tests lack their explicit source/tool path in the isolated concentrated environment; parent real matrix owns actual three-layer integration. No further author probes or product/test edits. ROOT alone decides acceptance and publication, and creates its separate unified ET+FF freeze. Canonical evidence: `{OUT}`.
'''
(OUT/"report-final.md").write_text(md,encoding="utf-8")
handoff=ROOT/"docs/handoffs/w06-cutoff-result"
(handoff/"handoff.md").write_text(md,encoding="utf-8")
(handoff/"handoff.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
plan=ROOT/".planning/w06-cutoff-result/task_plan.md"
text=plan.read_text(encoding="utf-8")
text=text.replace("D — ROOT concrete production receipt binding finding; repair in progress.",
                  "D complete — final author FROZEN STOP; ROOT responsibility B green, real41 acceptance pending.")
text=text.replace("Seal production receipt binding counterexample RED, repair the single existing boundary, then ROOT reruns concentrated responsibility B.",
                  "ROOT runs unchanged original41 FF→ET→CWP offline matrix and owns publication; author STOP.")
text=text.replace("- [ ] Preserve RED for", "- [x] Preserve RED for")
text=text.replace("- [ ] One lightweight", "- [x] One lightweight")
text=text.replace("- [ ] Focused affected", "- [x] Focused affected")
text += f"\n## Final reception facts\n- Final concentrated B134 PASS /4 SKIP /1.90s; SKIPs are listed individually in handoff.md and are not counted as PASS.\n- Final author freeze SHA {freeze_sha}; HEAD unchanged88997b85, protected354/tool205 unchanged, no product edits after this freeze.\n"
plan.write_text(text,encoding="utf-8")
with (ROOT/".planning/w06-cutoff-result/findings.md").open("a",encoding="utf-8") as f:
    f.write("\n## ROOT receipt boundary gap and common repair\n- Test-only binding negatives did not protect the actual production receiver. Production binding checks now occur once at the existing transport boundary, retaining measured usage while rejecting unrelated/failed receipts. No extra security master or raw verification.\n"
            "- Set membership over a decoded schema field could raise for JSON array/object. Two formal negatives proved the exception; finite tuple comparison safely rejects both types. Other binding fields use direct equality and count uses strict int.\n"
            "- Final ROOT concentrated134 PASS /4 SKIP. Three explicit W07 real-ET integration negatives lack test tool path; real-CWP import/replay lacks source checkout. These optional scope tests remain SKIP, actual three-layer original41 is owned by ROOT.\n")
with (ROOT/".planning/w06-cutoff-result/progress.md").open("a",encoding="utf-8") as f:
    f.write("\n## Final author STOP\n- ROOT binding RED8 FAIL, GREEN39 PASS. Nonhashable schema array/object RED2 FAIL /1 PASS, final affected GREEN41 PASS /77 deselected /0.55s. All intermediate evidence preserved.\n"
            "- ROOT concentrated-final2:134 PASS /4 SKIP /1.90s; no optional author suite rerun. Individual SKIP reasons recorded in final handoff.\n"
            f"- Final freeze {freeze_sha}; HEAD before/after88997b85ce5be20dc3d563b5c040706590df6dbb; protected354/tool205 unchanged; final lint/diff green and all scratch restored.\n"
            "- Author product/tests frozen STOP. ROOT owns unchanged real41, acceptance and publication.\n")
paths=list(OUT.glob("*"))+list((ROOT/".planning/w06-cutoff-result").glob("*.md"))+list(handoff.glob("*"))
manifest=[{"path":str(p),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
          for p in sorted(paths) if p.is_file() and p.name not in {"manifest.json","manifest-final.json"}]
(OUT/"manifest-final.json").write_text(json.dumps({"schema_version":"ff-cutoff-evidence-manifest/2","files":manifest},ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"freeze_sha256":freeze_sha,"head_before":baseline["base"],"head_after":head,
                  "files":final_files,"protected_unchanged":354,"tool_unchanged":205,"concentrated_pass":134,"skip":4},ensure_ascii=False))
