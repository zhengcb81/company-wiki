"""Bounded ROOT receipt: public synthetic evidence only, no credentials."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

PLAN = Path(__file__).resolve().parent
FF = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-ff-perf-reception')
AUTHOR = FF.parent / 'ff-matrix-efficiency'
REPORTS = Path.home() / 'AppData/Local/Temp/w7ff-root-reports'

def sha(path):
    assert 'FMP_API_KEY' not in str(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()

def metadata(repo, relative):
    root = repo / relative
    paths = [root] + (list(root.rglob('*')) if root.is_dir() else [])
    return {p.relative_to(repo).as_posix(): {'size':p.stat().st_size,
        'mtime_ns':p.stat().st_mtime_ns,'directory':p.is_dir()}
        for p in paths if p.exists()}

frozen = json.loads((PLAN/'freeze.json').read_text(encoding='utf-8'))
tree = ast.parse((FF/'tools/offline_contract_matrix/matrix_cases.py').read_text(encoding='utf-8'))
handlers = {n.name: hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest()
    for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name!='seed_all'}
assert handlers == frozen['handlers_actual']
for name, digest in frozen['readonly'].items():
    assert sha(AUTHOR/name) == digest, name
ff_main = Path('C:/Users/郑曾波/Projects/filing-fetch')
et_main = Path('C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts')
assert metadata(ff_main,'config/FMP_API_KEY.txt') == frozen['wip']['ff']
assert {**metadata(et_main,'.workbuddy-ai'),**metadata(et_main,'eval_results.json')} == frozen['wip']['et']
cwp = PLAN.parents[1]
assert {key:value for name in ['config.yaml','config/source_catalog.yaml','config/local_ocr.json']
    for key,value in metadata(cwp,name).items()} == frozen['production_metadata']
reports = sorted(REPORTS.glob('attempt-*/report.json'),key=lambda p:p.stat().st_mtime_ns)
assert len(reports) == 2
final = json.loads(reports[-1].read_text(encoding='utf-8'))
counts = {k:sum(c['result']==k for c in final['cases']) for k in ['PASS','FAIL','PARTIAL','NOT_RUN']}
assert counts == {'PASS':41,'FAIL':0,'PARTIAL':0,'NOT_RUN':0}
assert final['oracle']['findings'] == []
assert final['restore']['restored'] and final['restore']['production_metadata_unchanged']
assert final['scope']['batch_elapsed_seconds'] <= 180
assert final['scope']['case_limit_seconds'] == 30
archive = PLAN/'offline-evidence.zip'
assert not archive.exists()
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for report in reports:
        for p in sorted(report.parent.rglob('*')):
            if p.is_file():
                assert p.resolve().is_relative_to(REPORTS.resolve())
                z.write(p,p.relative_to(REPORTS).as_posix())
assert archive.stat().st_size < 8*1024*1024
proofs = final['source_proofs']
summary = {'schema':'root-w07-ff-reception/1','author_head':frozen['author_head'],
    'final_attempt':reports[-1].parent.name,'counts':counts,'scope':final['scope'],
    'restore':final['restore'],'code_binding':final['code_binding'],
    'unique_verified_proofs':sum(p.get('verified') is True for p in proofs['proofs'].values()),
    'worker_proofs':{k:len(v['proofs']) for k,v in proofs['worker_groups'].items()},
    'unchanged_case_handlers':len(handlers),'readonly_author_inputs_unchanged':True,
    'production_metadata_and_wip_preserved':True,'focused_tests':225,
    'archive':archive.name,'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),
    'paid_calls':0,'actual_supplier_reachability_proven':False,'scratch_peak_bytes':None,
    'first_root_attempt':{'counts':{'PASS':28,'PARTIAL':13,'FAIL':0,'NOT_RUN':0},
        'seconds':130.5777,'cause':'ROOT overconstrained independent logical original_locations aliases'},
    'publication_status':'pending'}
(PLAN/'acceptance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['counts','unique_verified_proofs','worker_proofs','archive_bytes']}))
