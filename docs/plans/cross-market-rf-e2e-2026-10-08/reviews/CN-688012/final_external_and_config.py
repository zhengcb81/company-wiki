import pathlib,json,hashlib,urllib.request,time,datetime,sys,os,subprocess
H=pathlib.Path(__file__).resolve().parent;P=H.parent.parent;E=P/'executions'/'CN-688012'
M=json.loads((E/'manifest.json').read_text(encoding='utf-8'));O=pathlib.Path(M['output_root'])
def sha(b):return hashlib.sha256(b).hexdigest()
def save(n,d):(H/n).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
baseline=json.loads((P/'baseline.json').read_text(encoding='utf-8'));checks=[]
for b in baseline['config_files']:
 p=pathlib.Path(b['path']);current=sha(p.read_bytes());checks.append({**b,'current_sha256':current,'status':'PASS' if current==b['sha256'] else 'FAIL'})
save('configuration_unchanged.json',checks)
live=[]
for name,url,expected,size in [('annual','https://static.cninfo.com.cn/finalpage/2026-03-31/1225062431.PDF',M['sources'][0]['content_sha256'],9165875),('half','https://static.cninfo.com.cn/finalpage/2026-08-20/1225482884.PDF',M['sources'][1]['content_sha256'],3149962)]:
 start=time.monotonic();h=hashlib.sha256();total=0
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as r:
   status=r.status;ctype=r.headers.get('Content-Type');prefix=None
   while True:
    assert time.monotonic()-start<45,'deadline';b=r.read(65536)
    if not b:break
    if prefix is None:prefix=b[:5]
    total+=len(b);assert total<=12582912,'byte ceiling';h.update(b)
  check={'name':name,'url':url,'http_status':status,'mime':ctype,'bytes':total,'actual_sha256':h.hexdigest(),'matches_raw':h.hexdigest()==expected and total==size,'pdf_magic':prefix==b'%PDF-','elapsed_seconds':time.monotonic()-start,'status':'PASS' if h.hexdigest()==expected and total==size and prefix==b'%PDF-' else 'FAIL','cost_usd':0}
 except Exception as exc:check={'name':name,'url':url,'status':'BLOCKED','error':str(exc),'cost_usd':0}
 live.append(check)
save('official_pdf_current_sha_checks.json',live)
env=dict(os.environ,REVENUE_PUBLICATION_REGISTRY=str(O/'publications.jsonl'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
cmd=[sys.executable,'-B','C:/Users/郑曾波/Projects/revenue-forecast/scripts/publication_registry.py','audit','--result',str(O/'forecast.json'),'--result',str(O/'snapshot_v2.json')]
r=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
save('publication_registry_independent_audit.json',{'command':cmd,'registry':str(O/'publications.jsonl'),'registry_sha256':sha((O/'publications.jsonl').read_bytes()),'returncode':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode(),'status':'PASS' if r.returncode==0 else 'FAIL','runtime_sha256':sha(pathlib.Path(cmd[2]).read_bytes())})
print(json.dumps({'config':checks,'official_current_pdf':live,'registry_audit_rc':r.returncode},ensure_ascii=False))
