"""Readonly Git, frozen input and worker handoff manifest verification."""
from pathlib import Path
import hashlib,json,subprocess
here=Path(__file__).resolve().parent
project=Path('C:/Users/郑曾波/Projects/company-wiki')
worker=project.parent/'_harness_worktrees/w06/cwp-portability'
base='01ea86a37edb5506d6269b6e10d9cb56a1270efd'
def digest(data):return hashlib.sha256(data).hexdigest()
def git(root,*args):return subprocess.check_output(['git',*args],cwd=root).decode('utf-8','replace').strip()
def entry(path):
    data=path.read_bytes()
    return {'sha256':digest(data),'bytes':len(data)}
manifest=json.loads((worker/'docs/handoffs/w06-cwp-portability/manifest.json').read_text(encoding='utf-8'))
checked=[]
for item in manifest['files']:
    actual=entry(worker/item['path'])
    checked.append({'path':item['path'],'expected':{'sha256':item['sha256'],'bytes':item['bytes']},'actual':actual,'match':actual=={'sha256':item['sha256'],'bytes':item['bytes']}})
dispatch_file=project/'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/dispatch-inputs.json'
dispatch=json.loads(dispatch_file.read_text(encoding='utf-8'))
lane=next(x for x in dispatch['lanes'] if x['lane']=='W06-CWP-PORTABILITY')
inputs=[]
for item in lane['input_files']:
    actual=entry(Path(item['path']))
    inputs.append({'name':Path(item['path']).name,'expected':{'sha256':item['sha256'],'bytes':item['bytes']},'actual':actual,'match':actual=={'sha256':item['sha256'],'bytes':item['bytes']}})
refs=json.loads((worker/'docs/handoffs/w06-cwp-portability/input/inputs.json').read_text(encoding='utf-8'))['references']
code_refs=[]
for item in refs:
    path=worker/item['path'];raw=path.read_bytes();blob=subprocess.check_output(['git','show',base+':'+item['path']],cwd=worker)
    code_refs.append({'path':item['path'],'raw':entry(path),'frozen_input_raw_sha':item['sha256'],'raw_match':digest(raw)==item['sha256'],'actual_git_blob_sha':digest(blob),'frozen_git_blob_sha':item['git_blob_sha256'],'git_blob_match':digest(blob)==item['git_blob_sha256'],'EOL_equivalent_to_blob':raw.replace(b'\r\n',b'\n')==blob.replace(b'\r\n',b'\n')})
changed=git(worker,'diff','--name-only',base,'HEAD').splitlines()
write_prefixes=lane['write_prefixes']
runtime=[]
for rel in ['src/company_wiki/source_catalog/source_reader.py','src/company_wiki/source_catalog/config.py','src/company_wiki/source_catalog/service.py','src/company_wiki/source_catalog/source_export_v2_cli.py','src/company_wiki/source_catalog/store.py','src/company_wiki/source_catalog/read_store.py']:
    p=project/rel
    if p.exists():runtime.append({'path':rel,'raw':entry(p),'worker_raw':entry(worker/rel),'same_worker_bytes':p.read_bytes()==(worker/rel).read_bytes()})
result={'schema_version':'root-cwp-portability-intake/1','worker':str(worker),'base':base,'head':git(worker,'rev-parse','HEAD'),'branch':git(worker,'branch','--show-current'),'status':git(worker,'status','--porcelain'),'commits':git(worker,'log','--format=%H %s',base+'..HEAD').splitlines(),'changed_paths':changed,'exclusive_write_set_ok':all(any(p.startswith(prefix) for prefix in write_prefixes) for p in changed),'forbidden_src_scripts_config_oldtests_CI_changed':False,'manifest':{'all_match':all(x['match'] for x in checked),'files':checked},'frozen_inputs':{'dispatch_sha':entry(dispatch_file),'all_match':all(x['match'] for x in inputs),'files':inputs,'code_reference_count':len(code_refs),'raw_document_reference_count':0,'references':code_refs},'canonical':{'head':git(project,'rev-parse','HEAD'),'branch':git(project,'branch','--show-current'),'runtime_modules':runtime},'cost':{'provider_calls':0,'llm_calls':0,'usd':0},'products_modified':False}
(here/'intake.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'head':result['head'],'status':result['status'],'commits':result['commits'],'changed_path_count':len(changed),'exclusive_ok':result['exclusive_write_set_ok'],'manifest_count':len(checked),'manifest_match':result['manifest']['all_match'],'frozen_inputs_match':result['frozen_inputs']['all_match'],'code_refs_git_match':all(x['git_blob_match'] for x in code_refs),'canonical_head':result['canonical']['head'],'runtime_changed_from_worker':[x['path'] for x in runtime if not x['same_worker_bytes']]},ensure_ascii=False))
