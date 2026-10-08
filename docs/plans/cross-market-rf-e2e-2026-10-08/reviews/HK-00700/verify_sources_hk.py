import json,hashlib,sys,time,datetime as dt,re
from pathlib import Path
import requests,fitz
HERE=Path(__file__).resolve().parent;EX=HERE.parents[1]/'executions/HK-00700'
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
m=load(EX/'manifest.json');i=load(Path(m['output_root'])/'input.json')
receipts=[]
for s in i['sources']:
 started=time.monotonic();h=hashlib.sha256();size=0;first=b''
 try:
  with requests.get(s['url'],timeout=(15,35),stream=True) as r:
   r.raise_for_status()
   for chunk in r.iter_content(65536):
    if not first:first=chunk[:40]
    size+=len(chunk);h.update(chunk)
    if size>41943040 or time.monotonic()-started>180:raise ValueError('review bounded source read exceeded')
   receipt=dict(source_id=s['source_id'],url=s['url'],final_url=r.url,status_code=r.status_code,content_type=r.headers.get('Content-Type'),bytes=size,sha256=h.hexdigest(),captured_sha=s['capture']['snapshot_sha256'],same_bytes=h.hexdigest()==s['capture']['snapshot_sha256'],date=dt.datetime.now(dt.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-started,max_bytes=41943040,timeout_seconds=180,cost_usd='0.00')
 except Exception as e:receipt=dict(source_id=s['source_id'],url=s['url'],error=str(e),bytes=size,elapsed_seconds=time.monotonic()-started)
 receipts.append(receipt)
(HERE/'independent_live_source_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(receipts,ensure_ascii=False))
