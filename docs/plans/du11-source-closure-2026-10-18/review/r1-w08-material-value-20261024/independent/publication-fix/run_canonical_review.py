from __future__ import annotations
from pathlib import Path
import hashlib, importlib, json, os, shutil, subprocess, sys, time
root=Path.cwd().resolve()
out=Path(__file__).resolve().parent
scratch=root/".tmp-mv-canonical"
assert not scratch.exists(), "Independent test scratch must start absent"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def tree():
    pairs=[(p.relative_to(root).as_posix(),sha(p)) for p in sorted((root/"src").rglob("*.py"))]
    return {"count":len(pairs),"digest":hashlib.sha256(json.dumps(pairs).encode()).hexdigest()}
names=("narrative_business_disclosures","narrative_business_policy","narrative_reading","narrative_operating_relations")
mods=[importlib.import_module("company_wiki.source_catalog."+n) for n in names]
mods.append(importlib.import_module("company_wiki.document_understanding.decision_inventory"))
mods.append(importlib.import_module("company_wiki.automation.narrative_batch_request"))
imports={m.__name__:str(Path(m.__file__).resolve()) for m in mods}
assert all(Path(v).is_relative_to(root/"src") for v in imports.values())
paths=[Path(v) for v in imports.values()]+[root/"tests/unit/document_understanding_selection/test_reading_material_value.py",root/"tests/unit/document_understanding_selection/test_reading_decision_inventory.py",root/"tests/unit/test_narrative_scoped_runtime_recovery.py",out.parent/"test_material_binding_independent.py",out/"test_publication_semantics_independent.py",out/"test_duration_canonical_independent.py",root/"tests/unit/test_narrative_batch_request.py"]
before={p.relative_to(root).as_posix():sha(p) for p in paths}; tree_before=tree()
scopes=[str(out/"test_duration_canonical_independent.py"),"tests/unit/test_narrative_batch_request.py","tests/unit/test_narrative_scoped_runtime_recovery.py"]
command=[sys.executable,"-m","pytest","-q","-p","no:cacheprovider","--tb=short","--basetemp",str(scratch),"--junitxml",str(out/"final.xml"),*scopes]
env={**os.environ,"PYTHONPATH":str(root/"src"),"PYTHONDONTWRITEBYTECODE":"1","PYTHONIOENCODING":"utf-8"}
started=time.time()
with (out/"final-output.txt").open("w",encoding="utf-8") as log:
    result=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
after={p.relative_to(root).as_posix():sha(p) for p in paths}; tree_after=tree()
if scratch.exists():
    assert scratch.resolve().parent==root and scratch.name==".tmp-mv-canonical"
    shutil.rmtree(scratch)
receipt={"status":"PASS" if result.returncode==0 and before==after and tree_before==tree_after else "CHANGES_REQUIRED","command":command,"elapsed_seconds":round(time.time()-started,3),"returncode":result.returncode,"actual_imports":imports,"source_sha_before":before,"source_sha_after":after,"source_tree_before":tree_before,"source_tree_after":tree_after,"cleanup":{"scratch_absent_before":True,"scratch_absent_after":not scratch.exists()},"scope_limit":"Source material engineering review only. Not real annual14 coverage, formal summary or company RF audit PASS. No raw/network/model/keys access."}
(out/"final-execution.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(receipt,ensure_ascii=False,indent=2))
print((out/"final-output.txt").read_text(encoding="utf-8")[-6000:])
sys.exit(0 if receipt["status"]=="PASS" else 1)
