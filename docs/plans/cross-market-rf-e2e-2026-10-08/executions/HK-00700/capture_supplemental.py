"""Bounded official supplemental captures, explicitly outside FF financial acquisition."""
from pathlib import Path
import datetime as dt, hashlib, json, time, requests, fitz
HERE=Path(__file__).resolve().parent
OUT=Path(json.loads((HERE/'before.json').read_text(encoding='utf-8'))['output_root'])
SOURCES=[
 ('interim_2026_official','https://www.tencent.com/wp-content/uploads/2026/08/E700_IR.pdf','2026-08-12','pdf'),
 ('results_2q2026','https://www.tencent.com/wp-content/uploads/2026/08/Tencent-Announces-2026-Second-Quarter-Results.pdf','2026-08-12','pdf'),
 ('presentation_2q2026','https://static.www.tencent.com/website-2026-upload/2Q26-earnings-PPT_20260812_1800-88b183.pdf','2026-08-12','pdf'),
 ('netease_2q2026','https://ir.netease.com/news-releases/news-release-details/netease-announces-second-quarter-and-interim-2026-unaudited','2026-08-20','html'),
 ('tencent_results_index','https://www.tencent.com/investors/results/',None,'html'),
 ('tencent_announcements_index','https://www.tencent.com/investors/announcements/',None,'html'),
]
receipts=[]
for name,url,pub,kind in SOURCES:
 started=time.monotonic();receipt={'name':name,'url':url,'published_date':pub,'publication_date_basis':'date printed in original PDF/release, not file mtime' if pub else 'undated official index; discovery record only, not a registered dated forecast source','route':'official supplemental direct HTTP; not FF/Dayu/CWP acquisition','max_bytes':41943040,'timeout_seconds':180,'cost_usd':'0.00','authorized_by':'MAIN explicit supplemental-capture authorization'}
 try:
  r=requests.get(url,stream=True,timeout=(15,60));r.raise_for_status();body=bytearray()
  for chunk in r.iter_content(65536):
   if time.monotonic()-started>180:raise TimeoutError('supplemental deadline')
   body.extend(chunk)
   if len(body)>41943040:raise ValueError('supplemental byte ceiling')
  p=OUT/(name+('.pdf' if kind=='pdf' else '.html'));p.write_bytes(body)
  receipt.update(status='captured',status_code=r.status_code,final_url=r.url,raw_path=str(p),sha256=hashlib.sha256(body).hexdigest(),download_bytes=len(body),content_type=r.headers.get('content-type'))
  if kind=='pdf':
   if not body.startswith(b'%PDF'):raise ValueError('Official PDF link returned non-PDF content; unavailable, not a successful PDF capture')
   pages=[{'page':i+1,'text':q.get_text()} for i,q in enumerate(fitz.open(p))]
   pp=OUT/(name+'_pages.json');pp.write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8');receipt.update(pages=len(pages),parsed_pages_path=str(pp),parser='PyMuPDF '+fitz.VersionBind,parse_route='task-local deterministic extraction; CWP Worker not run')
 except Exception as exc:receipt.update(status='unavailable',error=type(exc).__name__+': '+str(exc))
 receipt.update(timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-started)
 receipts.append(receipt);print(json.dumps(receipt,ensure_ascii=False),flush=True)
 with (HERE/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'timestamp_utc':receipt['timestamp_utc'],'agent_id':'/root/rf_hk_execution','step':'1A','action':'capture_official_supplement','tool':'requests.get streamed','input_summary':receipt,'source_url':url,'artifacts':[receipt.get('raw_path')],'outcome':receipt['status'],'error':receipt.get('error')},ensure_ascii=False)+'\n')
(HERE/'supplemental_capture_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2),encoding='utf-8')
assert sum(x.get('download_bytes',0) for x in receipts)<250*1024*1024
