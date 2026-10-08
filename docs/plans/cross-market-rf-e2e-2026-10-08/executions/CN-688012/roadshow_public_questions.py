"""Read observed SSE public question endpoint; no credentials/private API."""
from pathlib import Path
import datetime, hashlib, json, os, sys, time, urllib.request, urllib.parse
ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008'/'CN-688012'
url='https://roadshow.sseinfo.com/base-service/api/pub/v1/question_answer/answer_question_page'
payload=dict(pageNo=1,pageSize=200,questionTypeList=[2,3,4],activityId=40766,askTypes=[1])
stem='roadshow_public_questions'
if len(sys.argv)>1 and sys.argv[1]=='precollect':
 url='https://roadshow.sseinfo.com/base-service/api/pub/v1/activity/question_collect_activity_page'
 payload=dict(activityId=40766,pageNo=int(sys.argv[2]) if len(sys.argv)>2 else 1,pageSize=3)
 stem='roadshow_precollect_questions_page'+str(payload['pageNo'])
# Actual main app axios wrapper observed: urlencoded qs.stringify(indices:false).
body=urllib.parse.urlencode(payload,doseq=True).encode('utf-8')
start=time.monotonic()
request=urllib.request.Request(url,data=body,method='POST',headers={'Content-Type':'application/x-www-form-urlencoded','Accept-Language':'zh-CN','User-Agent':'Mozilla/5.0','Referer':'https://roadshow.sseinfo.com/activityDetails/40766'})
with urllib.request.urlopen(request,timeout=30) as response:
    raw=response.read(1048577)
    assert len(raw)<=1048576,'1MiB hard limit'
    status=response.status
dest=OUT/(stem+'.json');dest.write_bytes(raw)
meta=dict(url=url,request=payload,endpoint_basis='literal public endpoint and parameter fields inspected from actual roadshow_app_script.html',response_path=str(dest),status=status,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),elapsed_seconds=time.monotonic()-start,captured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),cost_usd=0,credentials_used=False)
(ROOT/(stem+'_receipt.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False)); parsed=json.loads(raw)
print(json.dumps({k:v for k,v in parsed.items() if k!='datas'},ensure_ascii=False))
assert parsed.get('success') is True,'Official application response failed; HTTP200 alone is not success'
for dataset in parsed.get('datas',[]):
 if isinstance(dataset,dict):
  records=dataset.get('records',[])
  print('DATASET '+json.dumps({k:v for k,v in dataset.items() if k!='records'},ensure_ascii=False))
  print('ALL_KEYS '+str(sorted({k for item in records for k in item})))
  for item in records:
   if any('中微' in str(v) or '688012' in str(v) for v in item.values()): print('CN_RECORD '+json.dumps(item,ensure_ascii=False))
with (ROOT/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(timestamp_utc=meta['captured_at'],agent_id='rf_cn_execution',step='1A',action='read publicly observed SSE roadshow endpoint',tool='urllib.request POST',input_summary=payload,source_url=url,artifacts=[str(dest)],outcome='actual response saved, company attribution not yet checked',error=None),ensure_ascii=False)+'\n')
