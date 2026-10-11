"""Read-only portability intake + synthetic current-main reader E2E, no real env/keys."""
from __future__ import annotations
import copy
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
SAFE_ENV = {k:v for k,v in os.environ.items() if k.upper() in
    {'SYSTEMROOT','WINDIR','COMSPEC','PATH','TEMP','TMP','PATHEXT'}}
SAFE_HOME = Path(__file__).resolve().parent/'synthetic-reader-attempt2-owned'/'home'
if len(sys.argv)==1:
    assert not SAFE_HOME.parent.exists()
    SAFE_HOME.mkdir(parents=True)
SAFE_ENV.update(PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', HOME=str(SAFE_HOME), USERPROFILE=str(SAFE_HOME))
os.environ.clear()
os.environ.update(SAFE_ENV)
blocked_actions = []
def hygiene(event, args):
    if event in {'socket.connect','socket.getaddrinfo','socket.connect_ex'}:
        blocked_actions.append('network')
        raise RuntimeError('network forbidden in independent synthetic test')
    if event == 'open' and args and isinstance(args[0], (str,bytes)):
        name = os.path.basename(os.fsdecode(args[0])).lower()
        if name in {'.env','.env.local','credentials'} or ('api_key' in name and not name.endswith(('.py','.pyc'))):
            blocked_actions.append('credential_file')
            raise RuntimeError('credential file forbidden in independent synthetic test')
sys.addaudithook(hygiene)

HERE = Path(__file__).resolve().parent
PROJECT = Path('C:/Users/郑曾波/Projects/company-wiki')
WORKER = PROJECT.parent/'_harness_worktrees/w06/cwp-portability'
sys.path.insert(0,str(PROJECT/'src'))
import company_wiki
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
sys.path.insert(0,str(WORKER))
from tools.source_root_portability import oracle, run, report
from tools.source_root_portability.fixture_builder import build_fixture, write_config

def digest(data):
    return hashlib.sha256(data).hexdigest()
def normal(path):
    return Path(str(path).removeprefix('\\\\?\\')).resolve()
def owned(path):
    p = normal(path)
    assert HERE.resolve() in p.parents and p != HERE.resolve(), p
    assert not p.is_symlink()
    return p
def delete(path):
    owned(path)
    if Path(path).exists():
        shutil.rmtree(path)
def epath(path):
    return Path('\\\\?\\'+str(Path(path).resolve())) if os.name=='nt' else Path(path).resolve()

if len(sys.argv)>1 and sys.argv[1] in {'--child','--spy-child'}:
    config, ref_file, output = map(Path,sys.argv[2:5])
    if sys.argv[1]=='--spy-child':
        from tools.source_root_portability import consumer_spy
        # Bind observation prefix to the genuinely loaded canonical code. This
        # simulates module relocation after merge; reader bytes are never mocked.
        consumer_spy._COMPANY_WIKI_PREFIX = str(Path(company_wiki.__file__).parent)+os.sep
        rc = consumer_spy.main(['--config',str(config),'--ref-json',str(ref_file),'--out',str(output)])
        sys.exit(rc)
    cat = SourceCatalog(load_catalog_config(config))
    try:
        ref = SourceRef(**json.loads(ref_file.read_text(encoding='utf-8')))
        opened = SourceVersionReader(cat).open_version(ref,purpose='source_export')
        result = {'status':'ok','pid':os.getpid(),'read_sha256':digest(opened.data),
                  'byte_size':opened.byte_size,'binding':str(Path(company_wiki.__file__).resolve())}
    except Exception as exc:
        result = {'status':getattr(exc,'status','error'),'reason':getattr(exc,'reason',type(exc).__name__),
                  'pid':os.getpid(),'binding':str(Path(company_wiki.__file__).resolve())}
    finally:
        cat.close()
    output.write_text(json.dumps(result),encoding='utf-8')
    print(json.dumps(result))
    sys.exit(0 if result['status']=='ok' else 2)

observations = {}

scratch = epath(HERE/'synthetic-reader-attempt2-owned')
assert scratch.exists() and (scratch/'home').is_dir()
cat = None
reader_result = {'status':'RUNNING','canonical_binding':str(Path(company_wiki.__file__).resolve()),
                 'current_code_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=PROJECT,text=True).strip(),
                 'initial':'absent','source_ref_schema':'2.0','original_count':4,'provider_calls':0}
started = time.monotonic()
try:
    lake = build_fixture(scratch)
    cat = SourceCatalog(load_catalog_config(lake.config_path))
    for root_id in lake.root_dirs:
        cat.register_sources(root_id=root_id,relative_paths={d.relative_path for d in lake.docs.values() if d.root_id==root_id})
    reader = SourceVersionReader(cat)
    refs = {}
    def get_ref(doc):
        row = cat.reader.fetchone('SELECT d.document_id,d.primary_source_id AS source_id FROM documents d JOIN sources s ON s.source_id=d.primary_source_id WHERE s.content_sha256=?',(doc.content_sha256,))
        return reader.query_ref(row['document_id'],row['source_id'],doc.content_sha256)
    reads = []
    for key,doc in lake.docs.items():
        refs[key]=get_ref(doc)
        opened=reader.open_version(refs[key],purpose='source_export')
        assert digest(opened.data)==doc.content_sha256 and opened.byte_size==doc.byte_size
        facts=reader.describe_version(refs[key])
        assert facts['fiscal_year']==doc.fiscal_year and facts['document_kind']==doc.document_kind
        reads.append({'doc_key':key,'sha256':digest(opened.data),'fiscal_year':facts['fiscal_year']})
    first_policy=reader.open_version(refs['pdf'],purpose='source_export').policy_sha256
    cat.close();cat=None
    shifted=scratch/'lake_B'
    owned(lake.lake_root);owned(shifted)
    lake.lake_root.rename(shifted)
    lake.root_dirs={root_id:shifted/path.name for root_id,path in lake.root_dirs.items()}
    config=scratch/'cfg/config_lake_B.yaml'
    write_config(config,root_paths=lake.root_dirs,catalog_dir=lake.catalog_dir)
    cat=SourceCatalog(load_catalog_config(config));reader=SourceVersionReader(cat)
    for key in ('pdf','htm','txt'):
        assert digest(reader.open_version(refs[key],purpose='source_export').data)==lake.docs[key].content_sha256
    second_policy=reader.open_version(refs['pdf'],purpose='source_export').policy_sha256
    txt=lake.docs['txt'];victim=lake.root_dirs[txt.root_id]/txt.relative_path
    original_txt=victim.read_bytes();victim.unlink()
    try:
        assert digest(reader.open_version(refs['txt'],purpose='source_export').data)==txt.content_sha256
    finally:victim.write_bytes(original_txt)
    htm=lake.docs['htm'];target=lake.root_dirs[htm.root_id]/htm.relative_path
    original_html=target.read_bytes();corrupt=bytearray(original_html);corrupt[-2]^=1;target.write_bytes(corrupt)
    try:
        reader.open_version(refs['htm'],purpose='source_export')
        raise AssertionError('same-length corruption accepted')
    except AssertionError:raise
    except Exception as exc:
        corruption={'status':getattr(exc,'status',None),'reason':getattr(exc,'reason',None),'detail':getattr(exc,'detail','')}
        assert 'content_sha256_mismatch' in str(corruption)
    finally:target.write_bytes(original_html)
    old_schema=replace(refs['txt'],schema_version='1.0')
    try:
        reader.open_version(old_schema,purpose='source_export')
        raise AssertionError('unsupported ref schema accepted')
    except AssertionError:raise
    except Exception as exc:assert getattr(exc,'reason',None)=='unsupported_version'
    payload=scratch/'child-ref.json';child_out=scratch/'child-result.json'
    payload.write_text(json.dumps(asdict(refs['txt'])),encoding='utf-8')
    child=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--child',str(config),str(payload),str(child_out)],
        env=SAFE_ENV,cwd=HERE,capture_output=True,timeout=30)
    assert child.returncode==0,child.stderr.decode('utf-8','replace')[-500:]
    fresh=json.loads(child_out.read_text(encoding='utf-8'))
    assert fresh['pid']!=os.getpid() and fresh['read_sha256']==txt.content_sha256
    bad=replace(refs['txt'],byte_size=refs['txt'].byte_size+1)
    try:
        reader.open_version(bad,purpose='source_export')
        raise AssertionError('canonical reader accepted wrong ref metadata')
    except AssertionError:raise
    except Exception as exc:assert getattr(exc,'reason',None)=='source_ref_changed'
    payload.write_text(json.dumps(asdict(bad)),encoding='utf-8')
    spy=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--spy-child',str(config),str(payload),str(child_out)],
        env=SAFE_ENV,cwd=HERE,capture_output=True,timeout=30)
    spy_result=json.loads(child_out.read_text(encoding='utf-8'))
    observations['consumer_spy_replaces_wrong_ref_metadata']={'actual_exit':spy.returncode,
        'status':spy_result['status'],'input_byte_size':bad.byte_size,'actual_byte_size':spy_result['byte_size'],
        'canonical_direct_refusal':'source_ref_changed','source_layer_binding':'canonical current main preloaded',
        'audit_prefix_relocation_override_only':True}
    new_body=original_html+b'\n[SYNTHETIC] independent v2\n'
    sidecar=lake.root_dirs[htm.root_id]/htm.sidecar_relative_path
    old_sidecar=sidecar.read_bytes()
    new_meta=json.loads(old_sidecar)
    new_sha=digest(new_body)
    new_meta.update(content_sha256=new_sha,provider_document_id='synthetic-independent-htm-v2')
    target.write_bytes(new_body);sidecar.write_text(json.dumps(new_meta),encoding='utf-8')
    try:
        cat.register_sources(root_id=htm.root_id,relative_paths={htm.relative_path})
        row=cat.reader.fetchone('SELECT d.document_id,d.primary_source_id AS source_id FROM documents d JOIN sources s ON s.source_id=d.primary_source_id WHERE s.content_sha256=?',(new_sha,))
        new_ref=reader.query_ref(row['document_id'],row['source_id'],new_sha)
        new_open=reader.open_version(new_ref,purpose='source_export')
        assert digest(new_open.data)==new_sha and new_ref.content_sha256!=refs['htm'].content_sha256
        try:
            reader.open_version(refs['htm'],purpose='source_export')
            raise AssertionError('old version accepted new body')
        except AssertionError:raise
        except Exception as exc:old_outcome={'status':getattr(exc,'status',None),'reason':getattr(exc,'reason',None)}
        new_version={'status':'ok','fresh_sha':new_sha,'old_outcome':old_outcome}
    finally:
        target.write_bytes(original_html);sidecar.write_bytes(old_sidecar)
        cat.register_sources(root_id=htm.root_id,relative_paths={htm.relative_path})
    assert digest(reader.open_version(refs['htm'],purpose='source_export').data)==htm.content_sha256
    reader_result.update(status='PASS',register_query_open_reads=reads,old_ref_after_move='exact_bytes',
        policy_change_observed=first_policy!=second_policy,duplicate_fallback='exact_bytes',
        corruption=corruption,unsupported_ref_schema='named_refusal',fresh_child=fresh,
        exact_ref_metadata_guard='source_ref_changed',new_version=new_version,original_recovery='exact_bytes')
except Exception as exc:
    reader_result.update(status='HARNESS_OR_PRODUCT_FAIL',error=type(exc).__name__,detail=str(exc)[:700])
finally:
    if cat is not None:cat.close()
    delete(scratch)
    reader_result.update(seconds=round(time.monotonic()-started,3),final='absent' if not scratch.exists() else 'present')
observations['canonical_synthetic_reader_e2e']=reader_result
result={'schema_version':'root-w06-cwp-portability-independent-probes/1',
        'status':reader_result['status'],'observations':observations,
        'runtime_hygiene':{'credential_environment_inherited':False,'HOME':'synthetic-owned-home','blocked_actions':blocked_actions,
                          'actual_network_calls':0,'provider_calls':0,'LLM_calls':0,'fees_usd':0,
                          'raw_originals_accessed':0,'synthetic_files_only':True}}
(HERE/'reader-e2e-attempt2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
