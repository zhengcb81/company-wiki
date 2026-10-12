import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

PLAN = Path(__file__).resolve().parent
AUTHOR = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/ff-matrix-efficiency')
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-ff-perf-reception')
FF = Path('C:/Users/郑曾波/Projects/filing-fetch')
ET = Path('C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts')
CWP = PLAN.parents[1]
def sha(p):
    assert 'FMP_API_KEY' not in str(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()
def git(repo, *args):
    return subprocess.check_output(['git','-C',str(repo),*args],text=True,encoding='utf-8').strip()
def metadata(repo, relative):
    root = repo/relative
    files = [root] + (list(root.rglob('*')) if root.is_dir() else [])
    return {p.relative_to(repo).as_posix(): {'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns,'directory':p.is_dir()} for p in files if p.exists()}

handoff = json.loads((AUTHOR/'docs/handoffs/w07-ff-matrix-efficiency/handoff.json').read_text(encoding='utf-8'))
changed = []
for row in handoff['changed_files']:
    p = AUTHOR/row['path']
    raw = p.read_bytes()
    lf = raw.replace(b'\r\n',b'\n')
    matched = row['sha256'] in {sha(p), hashlib.sha256(lf).hexdigest(), hashlib.sha256(lf.replace(b'\n',b'\r\n')).hexdigest()}
    changed.append({'path':row['path'],'sha256':sha(p),'declared_sha256':row['sha256'],'matches':matched})
tree = ast.parse((AUTHOR/'tools/offline_contract_matrix/matrix_cases.py').read_text(encoding='utf-8'))
baseline = json.loads((AUTHOR/'.planning/w07-ff-matrix-efficiency/input/case-handler-baseline.json').read_text(encoding='utf-8'))
actual = {n.name:hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest() for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name!='seed_all'}
# Schema is inspected and preserved; actual source-level canonical hashes also pinned.
freeze = {'author_head':git(AUTHOR,'rev-parse','HEAD'), 'ff_main':git(FF,'rev-parse','HEAD'),'et_main':git(ET,'rev-parse','HEAD'), 'changed':changed,'handlers_actual':actual,'handlers_baseline':baseline,'wip':{'ff':metadata(FF,'config/FMP_API_KEY.txt'),'et':{**metadata(ET,'.workbuddy-ai'),**metadata(ET,'eval_results.json')}}}
for name in ['config.yaml','config/source_catalog.yaml','config/local_ocr.json']:
    freeze.setdefault('production_metadata',{}).update(metadata(CWP,name))
freeze['readonly'] = {}
for row in handoff['readonly_inputs']:
    if row['path'].startswith('input-repair'):
        continue
    p = AUTHOR/row['path']
    if p.exists():
        freeze['readonly'][row['path']] = sha(p)
inputs = AUTHOR/'.planning/w07-ff-matrix-efficiency/input'
dependency = json.loads((inputs/'dependency-manifest.json').read_text(encoding='utf-8'))
input_checks = []
for name, entry in dependency['dependencies'].items():
    oldroot = Path(entry['root'])
    for relative, row in entry['files'].items():
        assert sha(oldroot/relative) == row['sha256'], relative
    input_checks.append({'name':name,'commit':entry['commit'],'files_verified':len(entry['files'])})
freeze['fixed_dependencies'] = input_checks
target = ROOT/'.planning/w07-ff-matrix-efficiency/input'
assert not target.exists()
target.mkdir(parents=True)
for item in inputs.iterdir():
    if item.name != 'runtime' and item.is_file():
        shutil.copyfile(item,target/item.name)
for name,entry in dependency['dependencies'].items():
    oldroot = Path(entry['root'])
    # Copy only fixed manifest source and the three pinned ET test seams.
    paths = list(entry['files'])
    if name == 'et':
        paths += ['tests/__init__.py','tests/test_retrieval_runtime.py','tests/test_transcript_api.py']
    for relative in dict.fromkeys(paths):
        dest = target/'runtime'/name/relative
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(oldroot/relative,dest)
        if name == 'et' and relative.startswith('tests/'):
            blob = subprocess.check_output(['git','-C',str(ET),'show',entry['commit']+':'+relative])
            assert dest.read_bytes() == blob, relative
(PLAN/'freeze.json').write_text(json.dumps(freeze,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

tests = '''"""ROOT independent boundaries for concurrent offline matrix ownership/evidence."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools/offline_contract_matrix"))
import runtime
import cli_main
from run import Context

def test_attempt_caches_do_not_share_between_independent_batches(tmp_path):
    first = runtime.OwnedAttempt.create(tmp_path/"owned",tmp_path/"out")
    second = runtime.OwnedAttempt.create(tmp_path/"owned",tmp_path/"out")
    try:
        assert first.cache != second.cache
    finally:
        second.cleanup()
        first.cleanup()

def test_existing_cache_is_never_used_for_new_attempt(tmp_path):
    original = tmp_path/"owned"/"pc"
    original.mkdir(parents=True)
    sentinel = original/"sentinel.pyc"
    sentinel.write_bytes(b"original")
    before = {p.relative_to(original).as_posix():p.read_bytes() for p in original.rglob("*") if p.is_file()}
    attempt = runtime.OwnedAttempt.create(tmp_path/"owned",tmp_path/"out")
    try:
        env = runtime.synthetic_env(attempt.scratch,tmp_path/"cwp",tmp_path/"et",pycache_root=attempt.cache)
        active = Path(env["PYTHONPYCACHEPREFIX"]).resolve()
        assert active != original.resolve()
        (active/"new.pyc").write_bytes(b"new")
    finally:
        restore = attempt.cleanup()
    assert before == {p.relative_to(original).as_posix():p.read_bytes() for p in original.rglob("*") if p.is_file()}
    assert restore["restored"]

@pytest.mark.parametrize("first,second",[(False,True),(True,False)])
def test_colliding_document_proofs_do_not_hide_failed_worker(first,second):
    combined = {"proofs":{},"catalog_snapshot":[]}
    cli_main._merge_source_proofs(combined,{"proofs":{"same-doc":{"verified":first,"content_sha256":"a","byte_size":3}},"catalog_snapshot":[]},"g1")
    cli_main._merge_source_proofs(combined,{"proofs":{"same-doc":{"verified":second,"content_sha256":"a","byte_size":3}},"catalog_snapshot":[]},"g2")
    assert combined["proofs"]["same-doc"]["verified"] is False
    assert len(combined["worker_groups"]) == 2

def test_verified_collisions_keep_all_worker_evidence():
    combined = {"proofs":{},"catalog_snapshot":[]}
    proof = {"verified":True,"content_sha256":"a","byte_size":3,"source_versions":1,"physical_originals":1}
    for group in ("g1","g2"):
        cli_main._merge_source_proofs(combined,{"proofs":{"same-doc":proof},"catalog_snapshot":[]},group)
    assert combined["proofs"]["same-doc"]["verified"] is True
    assert set(combined["worker_groups"]) == {"g1","g2"}

def test_incompatible_verified_collision_is_not_green():
    combined = {"proofs":{},"catalog_snapshot":[]}
    for group, digest in [("g1","a"),("g2","b")]:
        cli_main._merge_source_proofs(combined,{"proofs":{"doc":{"verified":True,"content_sha256":digest,"byte_size":3}},"catalog_snapshot":[]},group)
    assert combined["proofs"]["doc"]["verified"] is False

def test_measurement_failure_still_restores_attempt(tmp_path,monkeypatch):
    monkeypatch.setattr(cli_main,"_verify_binding",lambda *a,**kw:{"verified":False})
    def broken(*a):
        raise RuntimeError("metrics unavailable")
    monkeypatch.setattr(cli_main,"cache_stats",broken)
    with pytest.raises(Exception):
        cli_main.main(["--cwp-project",str(tmp_path/"cwp"),"--et-project",str(tmp_path/"et"),"--owned-root",str(tmp_path/"owned"),"--out-root",str(tmp_path/"out")])
    assert not (tmp_path/"owned").exists()

def test_dead_child_is_reaped_after_second_communicate_error(tmp_path,monkeypatch):
    class Child:
        pid=123
        returncode=None
        waited=False
        def communicate(self,*a,**kw):
            raise RuntimeError("pipe broken")
        def kill(self):
            self.returncode=-9
        def wait(self,timeout=None):
            self.waited=True
            return self.returncode
    child=Child()
    monkeypatch.setattr(runtime.subprocess,"Popen",lambda *a,**kw:child)
    monkeypatch.setattr(runtime,"_terminate_tree",lambda proc,env:proc.kill())
    with pytest.raises(RuntimeError):
        runtime.run_process(["python"],env={},cwd=tmp_path,deadline=runtime.Deadline(1))
    assert child.waited

@pytest.mark.parametrize("kind",["missing","extra","reordered"])
def test_seed_response_cardinality_and_order_are_validated(tmp_path,monkeypatch,kind):
    from fixture_builder import Identity
    ctx=Context(ff_root=tmp_path/"ff",cwp_root=tmp_path/"cwp",et_root=tmp_path/"et",scratch=tmp_path/"scratch",out_root=tmp_path/"out")
    seeds=[(Identity("US","Apple Inc.","US:AAPL"),"annual_report",2025,"FY")]
    def fake(command,**kw):
        payload=json.loads(kw["input"])
        row={"tag":payload["requests"][0]["tag"],"request_argv":payload["requests"][0]["argv"],"exit_code":0,"response":{},"response_ref":"x","response_sha256":"a","source_ref":{},"counts":{}}
        rows=[] if kind=="missing" else [row,row] if kind=="extra" else [dict(row,tag="other")]
        return SimpleNamespace(returncode=0,stdout=json.dumps({"schema_version":"w07-seed-batch/1","requests":rows}).encode(),stderr=b"")
    monkeypatch.setattr(sys.modules["run"],"run_process",fake)
    with pytest.raises(ValueError):
        ctx.warm_seed_batch(seeds)
'''
test = ROOT/'tests/test_root_w07_matrix_boundaries.py'
assert not test.exists()
test.write_text(tests,encoding='utf-8')
print(json.dumps({'author':freeze['author_head'],'changed_matches':sum(r['matches'] for r in changed),'fixed_dependencies':input_checks,'handlers':len(actual)},ensure_ascii=False))
