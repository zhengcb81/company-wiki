from pathlib import Path
import datetime, hashlib, json, os, sys, time, urllib.request
ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008'/'CN-688012'
label,url=sys.argv[1:3]
start=time.monotonic()
with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as response:
    chunks=[];total=0
    while True:
        if time.monotonic()-start>90:raise TimeoutError('90s page limit')
        chunk=response.read(65536)
        if not chunk:break
        total+=len(chunk)
        if total>4194304:raise ValueError('4MiB page limit')
        chunks.append(chunk)
    data=b''.join(chunks);status=response.status; final_url=response.url
dest=OUT/(label+'.html');dest.write_bytes(data)
meta=dict(label=label,url=url,final_url=final_url,status=status,path=str(dest),sha256=hashlib.sha256(data).hexdigest(),byte_size=total,captured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start)
(ROOT/(label+'_page_capture.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(timestamp_utc=meta['captured_at'],agent_id='rf_cn_execution',step='1A',action='actual official web page capture, content remains untrusted data',tool='urllib.request',input_summary=url,source_url=url,artifacts=[str(dest),str(ROOT/(label+'_page_capture.json'))],outcome='page bytes saved; must inspect before making claims',error=None),ensure_ascii=False)+'\n')
print(json.dumps(meta,ensure_ascii=False))
from bs4 import BeautifulSoup
soup=BeautifulSoup(data,'html.parser')
print(soup.get_text(' ',strip=True)[:12000])
print('SCRIPT LINKS '+json.dumps([s.get('src') for s in soup.find_all('script') if s.get('src')]))
