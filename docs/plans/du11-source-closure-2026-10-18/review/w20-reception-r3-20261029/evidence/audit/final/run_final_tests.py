import pathlib,subprocess,os,json,time,hashlib,shutil
repo=pathlib.Path(r'C:/Users/郑曾波/Projects/revenue-forecast-audit-w20-root-final');out=pathlib.Path(r'C:/Users/郑曾波/Projects/company-wiki/.planning/w20-reception-r3-20261029/audit');tmp=out/'final-temporary';tmp.mkdir(exist_ok=False)
expected='55c29fe5f3a9554f883156e3a4232eece04bf581'; assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==expected
runtime=['skills/revenue-forecast-audit/scripts/summary_checkpoint_observations.py','skills/revenue-forecast-audit/scripts/summary_review_packet.py','skills/revenue-forecast-audit/scripts/numeric_audit.py','skills/revenue-forecast-audit/scripts/summary_review_contracts.py','tests/test_w20_root_currency_binding.py']
def hashes():
 rows=[]
 for name in runtime:
  raw=(repo/name).read_bytes();lf=raw.replace(b'\r\n',b'\n');blob=subprocess.check_output(['git','-C',str(repo),'show',expected+':'+name]);rows.append({'path':name,'raw_sha256':hashlib.sha256(raw).hexdigest(),'lf_sha256':hashlib.sha256(lf).hexdigest(),'commit_lf_match':lf==blob.replace(b'\r\n',b'\n')})
 return rows
before=hashes();assert all(x['commit_lf_match'] for x in before)
env=dict(os.environ,TMP=str(tmp),TEMP=str(tmp),TMPDIR=str(tmp),PYTHONDONTWRITEBYTECODE='1',W20_AUDIT_REPO=str(repo));results=[]
root_old=pathlib.Path(r'C:/Users/郑曾波/Projects/company-wiki/docs/plans/du11-source-closure-2026-10-18/review')
commands=[('r1-independent7',[str(out/'run_bound_test.py'),str(repo),str(root_old/'w20-reception-20261029/evidence/audit/test_independent_expectations.py')]),('r2-typed4',[str(out/'run_bound_test.py'),str(repo),str(root_old/'w20-reception-r2-20261029/evidence/audit/test_typed_binding.py')]),('r3-guard6',[str(out/'test_root_final_guard.py')]),('w20-unit48',['-m','unittest','discover','-s','tests','-p','test_w20_*.py']),('numeric7',['-m','unittest','discover','-s','tests','-p','test_numeric_audit.py']),('du5-compat48',['-m','unittest','discover','-s','tests','-p','test_du5_*.py']),('cli11',['tests/fixtures/w20_checkpoints/run_e2e_chain.py','--work',str(tmp/'cli'),'--repo',str(repo)])]
try:
 for name,args in commands:
  cmd=[r'C:/Miniconda/python.exe','-B','-X','utf8',*args];t=time.monotonic();r=subprocess.run(cmd,cwd=repo,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=65);(out/(name+'.final.log')).write_text(r.stdout+r.stderr,encoding='utf-8');results.append({'name':name,'command':cmd,'exit_code':r.returncode,'seconds':round(time.monotonic()-t,3),'output_tail':(r.stdout+r.stderr)[-600:]})
  if r.returncode:break
finally:
 total=sum(p.stat().st_size for p in tmp.rglob('*') if p.is_file());count=sum(1 for p in tmp.rglob('*') if p.is_file());assert tmp.resolve().parent==out.resolve() and not tmp.is_symlink();shutil.rmtree(tmp)
 cleanup={'root':str(tmp),'before_exists':False,'after_exists':tmp.exists(),'restored':not tmp.exists(),'removed_files':count,'end_bytes_before_cleanup':total,'peak_bytes':None,'peak_note':'not sampled'};after=hashes();status=subprocess.check_output(['git','-C',str(repo),'status','--short'],text=True);head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip();receipt={'expected_commit':expected,'actual_head_after':head,'before_hashes':before,'after_hashes':after,'source_stable':before==after,'tracked_worktree_status_after':status,'tests':results,'cleanup':cleanup};(out/'final-tests.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'head':head,'source_stable':before==after,'status':status,'tests':results,'cleanup':cleanup},ensure_ascii=False))
