"""Bounded original-byte check; producer source-facts input, never manual DB patch."""
from pathlib import Path
import datetime, hashlib, json, os, time, urllib.request
ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008'/'CN-688012'
URL='https://static.cninfo.com.cn/finalpage/2026-03-31/1225062431.PDF'
EXPECTED='d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5'
LIMIT=41943040
start=time.monotonic()
chunks=[]
with urllib.request.urlopen(urllib.request.Request(URL,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as response:
    status=response.status; final_url=response.url; headers=dict(response.headers)
    assert status==200 and final_url.startswith('https://static.cninfo.com.cn/')
    count=0
    while True:
        if time.monotonic()-start>180:raise TimeoutError('180 second deadline')
        chunk=response.read(min(65536,LIMIT-count+1))
        if not chunk:break
        count+=len(chunk)
        if count>LIMIT:raise ValueError('40 MiB ceiling exceeded')
        chunks.append(chunk)
raw=b''.join(chunks)
sha=hashlib.sha256(raw).hexdigest()
assert sha==EXPECTED and len(raw)==9165875
dest=OUT/'annual2025_https_verified.pdf'; dest.write_bytes(raw)
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
receipt=dict(url=URL,final_url=final_url,http_status=status,bytes=len(raw),sha256=sha,limits=dict(max_bytes=LIMIT,timeout_seconds=180,max_cost_usd=0),elapsed_seconds=time.monotonic()-start,observed_at=now,raw_path=str(dest),headers=headers,original_unchanged=True,purpose='verify existing annual filing source_url HTTPS equivalence, not missing filing acquisition')
(ROOT/'annual2025_https_verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
ref=json.loads((ROOT/'annual2025_raw_receipt.json').read_text(encoding='utf-8'))['source_ref']
request=dict(source_ref=ref,facts={'source_url':URL},evidence={'source_url':dict(locator='HTTPS GET original PDF; exact bytes equal existing SourceRef',value=URL,observed_sha256=sha,byte_size=len(raw),observed_at=now,receipt_path=str(ROOT/'annual2025_https_verification.json'))})
(ROOT/'requests'/'annual2025_source_facts.json').write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(timestamp_utc=now,agent_id='rf_cn_execution',step='3',action='actual bounded official HTTPS GET verifies same raw bytes before standard producer source-facts correction',tool='urllib.request',input_summary=URL,source_url=URL,artifacts=[str(dest),str(ROOT/'annual2025_https_verification.json'),str(ROOT/'requests'/'annual2025_source_facts.json')],outcome='same SHA and size; original capture retained unknown',error=None),ensure_ascii=False)+'\n')
print(json.dumps(receipt,ensure_ascii=False))
